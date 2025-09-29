from gevent import monkey

monkey.patch_all()

import argparse
import bottle

from bracket_join import bracket_join
from convert_navbox import NavboxConverter
from convert_team_card import convert_team_card
from conversion.convert_tournaments import convert_page, convert_wikitext
from conversion.default_option_values import BOOL_OPTIONS, STRING_OPTIONS


def enable_cors(fn):
    def _enable_cors(*args, **kwargs):
        # set CORS headers
        bottle.response.headers["Access-Control-Allow-Origin"] = "*"
        bottle.response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
        bottle.response.headers["Access-Control-Allow-Headers"] = (
            "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token"
        )

        if bottle.request.method != "OPTIONS":
            # actual request; reply with the actual response
            return fn(*args, **kwargs)

    return _enable_cors


@bottle.route("/static/<filepath:path>")
def server_static(filepath):
    return bottle.static_file(filepath, root="static")


@bottle.route("/")
@bottle.jinja2_view("templates/index")
def index() -> str:
    return {}


@bottle.route("/convert")
@bottle.jinja2_view("templates/convert")
def convert():
    return {"input_type": "wiki_and_title", "title": "", "options": {**BOOL_OPTIONS, **STRING_OPTIONS}, "open": True}


@bottle.route("/convert/result", method="POST")
@bottle.jinja2_view("templates/convert_result")
def convert_result():
    options = {
        **{key: bool(bottle.request.forms.get(key)) for key in BOOL_OPTIONS},
        **{key: bottle.request.forms.get(key) for key in STRING_OPTIONS},
    }

    input_type = bottle.request.forms.get("input_type", "")
    wiki = bottle.request.forms.get("wiki", "")
    title = bottle.request.forms.get("title", "")
    wikitext_title = bottle.request.forms.get("wikitext_title", "")
    wikitext = bottle.request.forms.get("wikitext", "")
    if (
        (input_type == "wiki_and_title" and (not wiki or not title))
        or (input_type == "wiki_and_text" and not wikitext)
        or input_type not in ("wiki_and_title", "wikitext")
    ):
        info = ""
        if input_type == "wiki_and_title":
            if not wiki:
                info = "Error: No wiki"
            if not title:
                info = "Error: No title"
        elif input_type == "wikitext":
            if not wikitext:
                info = "Error: No wikitext"
        else:
            info = 'Error: input_type should be "wiki_and_title" or "wikitext"'
        return {
            "input_type": input_type,
            "wiki": wiki,
            "title": title,
            "wikitext": wikitext,
            "wikitext_title": wikitext_title,
            "converted": "",
            "info": info,
            "options": options,
            "open": False,
        }

    if input_type == "wiki_and_title":
        converted, info, summary, wikitext = convert_page(wiki, title, options)
    elif input_type == "wikitext":
        converted, info, summary = convert_wikitext(wikitext, wikitext_title, options)

    return {
        "input_type": input_type or "wiki_and_title",
        "wiki": wiki,
        "title": title,
        "wikitext": wikitext,
        "wikitext_title": wikitext_title,
        "converted": converted,
        "info": info,
        "summary": summary,
        "options": options,
        "open": False,
    }


@bottle.route("/convert_api", method=["OPTIONS", "POST"])
@enable_cors
def convert_api():
    options = {
        **{key: bool(bottle.request.json.get(key)) for key in BOOL_OPTIONS},
        **{key: bottle.request.json.get(key) for key in STRING_OPTIONS},
    }

    # for k, v in options.items():
    #     print(k, v)

    input_type = bottle.request.json.get("input_type", "")
    wiki = bottle.request.json.get("wiki", "")
    title = bottle.request.json.get("title", "")
    wikitext_title = bottle.request.json.get("wikitext_title", "")
    wikitext = bottle.request.json.get("wikitext", "")
    if (
        (input_type == "wiki_and_title" and (not wiki or not title))
        or (input_type == "wiki_and_text" and not wikitext)
        or input_type not in ("wiki_and_title", "wikitext")
    ):
        info = ""
        if input_type == "wiki_and_title":
            if not wiki:
                info = "Error: No wiki"
            if not title:
                info = "Error: No title"
        elif input_type == "wikitext":
            if not wikitext:
                info = "Error: No wikitext"
        else:
            info = 'Error: input_type should be "wiki_and_title" or "wikitext"'
        return {
            "input_type": input_type,
            "wiki": wiki,
            "title": title,
            "wikitext": wikitext,
            "wikitext_title": wikitext_title,
            "converted": "",
            "info": info,
            "options": options,
        }

    if input_type == "wiki_and_title":
        converted, info, summary, wikitext = convert_page(wiki, title, options)
    elif input_type == "wikitext":
        converted, info, summary = convert_wikitext(wikitext, wikitext_title, options)

    return {
        "input_type": input_type,
        "wiki": wiki,
        "title": title,
        "wikitext": wikitext,
        "wikitext_title": wikitext_title,
        "converted": converted,
        "info": info,
        "summary": summary,
        "options": options,
    }


@bottle.route("/bracket_join")
@bottle.route("/bracket_join", method="POST")
@bottle.jinja2_view("templates/bracket_join")
def page_bracket_join():
    original = bottle.request.forms.original or ""

    converted = bracket_join(original)

    return {"original": original, "converted": converted}


@bottle.route("/team_card_conversion")
@bottle.route("/team_card_conversion", method="POST")
@bottle.jinja2_view("templates/team_card_conversion")
def page_team_card_conversion():
    original = bottle.request.forms.original or ""

    converted = convert_team_card(original)

    return {"original": original, "converted": converted}


@bottle.route("/navbox_conversion")
@bottle.route("/navbox_conversion", method="POST")
@bottle.jinja2_view("templates/navbox_conversion")
def page_navbox_conversion():
    original = bottle.request.forms.original or ""
    page_title = bottle.request.forms.title or ""

    converted, info, _ = convert_navbox(original, page_title, {}) if original else ("", "", "")

    return {"original": original, "page_title": page_title, "converted": converted, "info": info}


@bottle.route("/navbox_conversion_api", method=["OPTIONS", "POST"])
@enable_cors
def convert_api():
    options = {
        **{key: bool(bottle.request.json.get(key, value)) for key, value in BOOL_OPTIONS.items()},
        **{key: bottle.request.json.get(key, value) for key, value in STRING_OPTIONS.items()},
    }

    # for k, v in options.items():
    #     print(k, v)

    input_type = bottle.request.json.get("input_type", "")
    wiki = bottle.request.json.get("wiki", "")
    title = bottle.request.json.get("title", "")
    wikitext_title = bottle.request.json.get("wikitext_title", "")
    wikitext = bottle.request.json.get("wikitext", "")
    if (
        (input_type == "wiki_and_title" and (not wiki or not title))
        or (input_type == "wiki_and_text" and not wikitext)
        or input_type not in ("wiki_and_title", "wikitext")
    ):
        info = ""
        if input_type == "wiki_and_title":
            if not wiki:
                info = "Error: No wiki"
            if not title:
                info = "Error: No title"
        elif input_type == "wikitext":
            if not wikitext:
                info = "Error: No wikitext"
        else:
            info = 'Error: input_type should be "wiki_and_title" or "wikitext"'
        return {
            "input_type": input_type,
            "wiki": wiki,
            "title": title,
            "wikitext": wikitext,
            "wikitext_title": wikitext_title,
            "converted": "",
            "info": info,
            "options": options,
        }

    if input_type == "wiki_and_title":
        converted, info, summary, wikitext = convert_page(wiki, title, convert_navbox, options)
    elif input_type == "wikitext":
        converted, info, summary = convert_wikitext(wikitext, wikitext_title, convert_navbox, options)

    return {
        "input_type": input_type,
        "wiki": wiki,
        "title": title,
        "wikitext": wikitext,
        "wikitext_title": wikitext_title,
        "converted": converted,
        "info": info,
        "summary": summary,
        "options": options,
    }


def convert_navbox(text, title, options) -> tuple[str, str, str]:
    return NavboxConverter(text, title, options).convert()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="liquipedia-convert")
    parser.add_argument("-p", "--port", type=int, default=1234)
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args()

    bottle.run(host="0.0.0.0", port=args.port, debug=args.debug)
