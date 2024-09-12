from gevent import monkey

monkey.patch_all()

import argparse
import bottle

from bracket_join import bracket_join
from convert_team_card import convert_team_card
from conversion.convert_tournaments import convert_page, convert_wikitext


# Dict values are default values
BOOL_OPTIONS = {
    "ignore_cache": False,
    "prize_pool_table_do_not_convert": False,
    "prize_pool_opponent_details": False,
    "prize_pool_opponent_last_results": False,
    "participant_table_do_not_convert": False,
    "participant_table_do_not_convert_first": False,
    "participant_table_convert_first_to_qualified_prize_pool_table": False,
    "player_details": True,
    "team_details": True,
    "bracket_do_not_convert_details": False,
    "bracket_guess_bestof": True,
    "bracket_override_with_team_match": False,
    "bracket_do_not_move_team_match": False,
    "bracket_do_not_move_no_map_team_match": False,
    "match_maps_guess_bestof": True,
    "team_match_add_player_lists": False,
    "team_match_plus_for_archon": False,
    "team_match_br_for_2v2": False,
    "team_match_make_duos_archons": False,
    "group_team_matches_uncollapsed": False,
    "team_match_enable_dateheader": False,
    "bracket_override_with_match_summary": False,
    "bracket_do_not_move_match_summary": False,
    "bracket_do_not_move_no_map_match_summary": False,
    "external_cup_list_convert": False,
    "convert_very_old_team_matches": False,
    "convert_very_old_player_matches_v1": False,
    "convert_very_old_player_matches_v2": False,
}
STRING_OPTIONS = {
    "import_limit": "guess",
    "import_limit_fixed_val": "",
    "bracket_match_width": "",
    "bracket_details": "remove_if_stored",
    "group_matches_of_section": "",
    "group_team_matches_of_section": "",
    "group_team_matches_mode": "",
    "group_team_matches_width": "",
    "team_match_player_aliases": "",
    "team_aliases": "",
}


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
        converted, info, wikitext = convert_page(wiki, title, options)
    elif input_type == "wikitext":
        converted, info = convert_wikitext(wikitext, wikitext_title, options)

    return {
        "input_type": input_type or "wiki_and_title",
        "wiki": wiki,
        "title": title,
        "wikitext": wikitext,
        "wikitext_title": wikitext_title,
        "converted": converted,
        "info": info,
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
        converted, info, wikitext = convert_page(wiki, title, options)
    elif input_type == "wikitext":
        converted, info = convert_wikitext(wikitext, wikitext_title, options)

    return {
        "input_type": input_type,
        "wiki": wiki,
        "title": title,
        "wikitext": wikitext,
        "wikitext_title": wikitext_title,
        "converted": converted,
        "info": info,
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="liquipedia-convert")
    parser.add_argument("-p", "--port", type=int, default=1234)
    args = parser.parse_args()

    bottle.run(host="0.0.0.0", port=args.port, debug=True)
