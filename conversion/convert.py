from datetime import datetime
from pathlib import Path
from os import makedirs
import os.path
import re
import requests
from typing import Any, Callable


API_URLS = {
    "starcraft": "https://liquipedia.net/starcraft/api.php",
    "starcraft2": "https://liquipedia.net/starcraft2/api.php",
}
HEADERS = {
    "Accept-Encoding": "gzip",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 EnuajBot (enuaj on Liquipedia)",
}


def convert_page(wiki: str, title: str, converter: Callable, options: dict[str, Any]) -> tuple[str, str, str, str]:
    title = title.replace("_", " ")

    cache_folder = Path(__file__).parent.parent / "cache" / wiki
    makedirs(cache_folder, exist_ok=True)
    cache_title = re.sub(r"[\\/\?\":\*]", "_", title)
    p = cache_folder / cache_title

    info_cache = ""
    if not options["ignore_cache"] and p.exists() and p.is_file():
        cache_timestamp = os.path.getmtime(p)
        info_cache += f"Getting cached content ({datetime.fromtimestamp(cache_timestamp).isoformat()})"
        text: str | None = p.read_text(encoding="utf-8")
        if datetime.now().timestamp() - cache_timestamp > 3600:
            info_cache += '<div class="warning">⚠️ Cache is more than 1-hour old</div>'
    else:
        cache_timestamp = None
        info_cache += "Getting content from the API"
        text = get_liquipedia_page_content(wiki, title)
        if text:
            p.write_text(text, encoding="utf-8")

    if text:
        converted, info, summary = converter(text, title, options)
        return converted, info_cache + ("" if info_cache.endswith("</div>") else "\n") + info, summary, text

    return "", f"Error while getting {title} from wiki {wiki}", "", ""


def convert_wikitext(text: str, title: str, converter: Callable, options: dict[str, Any]) -> tuple[str, str, str]:
    if text:
        return converter(text, title, options)

    return "", f"Error: no wikitext", ""


def get_liquipedia_page_content(wiki: str, title: str) -> str | None:
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
    }

    response = requests.get(API_URLS[wiki], headers=HEADERS, params=params)
    if response.status_code == 200:
        data = response.json()

        page_data = data["query"]["pages"]
        page_id = list(page_data.keys())[0]

        if page_id == "-1":
            print("Page not found")
            return None

        revision_data = page_data[page_id]["revisions"][0]
        content = revision_data["*"]

        return content

    return None
