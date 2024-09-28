from copy import deepcopy
from datetime import datetime
from itertools import chain
import json
from pathlib import Path
from os import makedirs
import os.path
import random
import re
import requests
import string
from typing import Any, Callable

import wikitextparser as wtp

from conversion.argument_conversion import *
from conversion.bracket_conversion import *
from conversion.classes import *
from conversion.my_wikitextparser import get_italics, get_sections, Italic, Section as mwtp_Section


API_URLS = {
    "starcraft": "https://liquipedia.net/starcraft/api.php",
    "starcraft2": "https://liquipedia.net/starcraft2/api.php",
}
HEADERS = {
    "Accept-Encoding": "gzip",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 EnuajBot (enuaj on Liquipedia)",
}
WIKITEXT_COMMENT_PATTERN = re.compile(r"<!--((?!-->).)*-->", re.UNICODE)
NOTE_PATTERN = re.compile(r"<sup>((?:(?!<\/sup>).)+)<\/sup>", re.UNICODE)
ASTERISK_PATTERN = re.compile(r"(\*+)(?:<\/nowiki>)?$", re.UNICODE)
RACE_OR_SECTION_COUNT_PATTERN = re.compile(r"''\(\d*\)''", re.UNICODE)
PIPE_PATTERN = re.compile(r"(.+)\{\{!\}\}(.+)", re.UNICODE)
SECTION_PATTERN = re.compile(r"^(?<!=)(={1,6})([^=\n]+?)\1", re.UNICODE)
DATE_PATTERN = re.compile(r"(?!19|20)\d{2}", re.UNICODE)
BAD_CLOSING_STROKE_TAG_PATTERN = re.compile(r"\n\|\} *<\/s>", re.UNICODE)
TO_GAMESET_PATTERN = re.compile(
    r"((?:<s>)?) *(?:'''|<b>)? *(\{\{ *?player.*?\}\}) *?((?:'''|<\/b>)?) vs. (?:'''|<b>)? *(\{\{ *?player.*?\}\}) *?((?:'''|<\/b>)?) *<br /> *on *\[\[(.+?)\]\]",
    re.UNICODE,
)
HIDDEN_ANCHOR_PATTERN = re.compile(r" *\{\{ *(?:HA|HiddenAnchor)", re.UNICODE)
FLAG_TEAM_PATTERN = re.compile(
    r"(?:^\{\{[Ff]lag\/.+?\}\}(?:\s|&nbsp;)*\b|\b(?:\s|&nbsp;)*\{\{[Ff]lag\/.+?\}\}$)", re.UNICODE
)
BR_2V2_PATTERN1 = re.compile(
    r"(?:\[\[(.+?)\]\]|(.+?)) *\{\{SC2-([PTZR])\}\} *(?:\{\{[Ff]lag\/(.*?)\}\} *)?<br *\/> *(?:\[\[(.+?)\]\]|(.+?)) *\{\{SC2-([PTZR])\}\} *(?:\{\{[Ff]lag\/(.*?)\}\})?",
    re.UNICODE,
)
BR_2V2_PATTERN2 = re.compile(
    r"(?:\{\{[Ff]lag\/(.*?)\}\} *)?\{\{SC2-([PTZR])\}\} *(?:\[\[(.+?)\]\]|(.+?)) *<br *\/> *(?:\{\{[Ff]lag\/(.*?)\}\} *)?\{\{SC2-([PTZR])\}\} *(?:\[\[(.+?)\]\]|(.+))",
    re.UNICODE,
)
MAP_PATTERN = re.compile(r"\|map(\d+)=\{\{Map", re.UNICODE)
OPPONENT_PATTERN = re.compile(r"\|opponent(\d+)=.+", re.UNICODE)
TEAM_BRACKET_TEMPLATE_SC2 = re.compile(r"\{\{[Tt]eamBracket\|sc2\}\} *", re.UNICODE)
TEAM_BRACKET_TEMPLATE = re.compile(r"\{\{[Tt]eamBracket\|(.((?!\}\}|\|).)+)\}\}", re.UNICODE)
BRACKET_MATCH_PATTERN = re.compile(r"R(\d+|x)M.+", re.UNICODE)
END_OF_PARAM_VALUE_PATTERN = re.compile(r"(?s)(\s|<!--(?:(?!-->).)+-->)+$", re.UNICODE)
PLACE_PATTERN = re.compile(r"(\d+)$", re.UNICODE)
FLAG_TEMPLATE_PATTERN = re.compile(r"^Flag/(.+)$", re.UNICODE)
LEGACY_ROUND_HEADER_PATTERN = re.compile(r"^(?:([RL])\d+|Q)$", re.UNICODE)
SCORE_ADVANTAGE_PATTERN = re.compile(
    r"<abbr title=\"Winner(?:'s|s') [bB]racket advantage of 1 (?:map|game)\"> *(\d+) *</abbr>", re.UNICODE
)
STRIKETHROUGH_PATTERN = re.compile(r"<s>((?:(?!<\/s>).)+)</s>", re.UNICODE)
NOINCLUDE_LEGACY_BRACKET_PATTERN = re.compile(
    r"\{\{<noinclude>LegacyBracket(.+?)<\/noinclude><includeonly>DisplayBracket<\/includeonly>", re.UNICODE
)
LEGACY_PLAYER_PREFIX_PATTERN = re.compile(
    r"^(R\d+[DW]\d+)(?:flag|race|win|score[23]?|team|short|literal)?$", re.UNICODE
)
LEGACY_GAME_DETAILS_PATTERN = re.compile(r"^(R\d+G\d+)details$", re.UNICODE)
PARTICIPANT_TABLE_PARTICIPANT_PATTERN = re.compile(r"^p?(\d+)$")

with open("countries.json", "r") as f:
    COUNTRIES = json.load(f)
with open("races.json", "r") as f:
    RACES = json.load(f)
SHORT_RACES = ("p", "t", "z", "r")


class Converter:
    def __init__(self, text: str, title: str, options: dict[str, Any]) -> str:
        self.text = text
        self.title = title
        self.options = options
        self.participants: dict[str, Participant] = {}

    def convert(self) -> tuple[str, str]:
        self.preprocess_text()

        self.info: str = ""
        self.parsed = wtp.parse(self.text)

        # Alternatives
        if self.options["convert_very_old_team_matches"]:
            return self.convert_very_old_team_matches(), self.info
        if self.options["convert_very_old_player_matches_v1"]:
            return self.convert_very_old_player_matches_v2(), self.info
        if self.options["convert_very_old_player_matches_v2"]:
            return self.convert_very_old_player_matches_v2(), self.info

        return self.convert_standard(), self.info

    def preprocess_text(self) -> None:
        if self.options["convert_very_old_player_matches_v1"] or self.options["convert_very_old_player_matches_v2"]:
            self.text = BAD_CLOSING_STROKE_TAG_PATTERN.sub("</s>\n|}", self.text)

            def replace_gamesets(m):
                winner = ""
                skip = m.group(1)
                if not skip:
                    if m.group(3):
                        winner = "1"
                    if m.group(5):
                        if winner:
                            print("Two winners in", m.group(0))
                        else:
                            winner = "2"
                text = f"{{{{GameSet|{m.group(2)}|{m.group(4)}|map={m.group(6)}|win={winner}"
                if skip:
                    text += "|skip=true"
                text += "}}"
                return text

            self.text = TO_GAMESET_PATTERN.sub(replace_gamesets, self.text)

        self.text = NOINCLUDE_LEGACY_BRACKET_PATTERN.sub("{{LegacyBracketDisplay\\1", self.text)

    def convert_standard(self) -> str:
        # Populated in conversion functions
        self.not_converted_arguments: set[tuple[str, str]] = set()
        self.changes: list[tuple[int, int, str]] = []
        self.match_summaries: list[MatchSummaryEntry] = []
        self.team_matches: list[TeamMatchEntry] = []
        self.prize_pool_tables_processed: int = 0
        self.storage_to_enable: bool = False

        # Get match summaries
        for tpl in self.parsed.templates:
            name = tpl.normal_name(capitalize=True)
            if name == "MatchSummary" and (ms_result := self.convert_match_summary(tpl)):
                self.match_summaries.append(MatchSummaryEntry(*ms_result))

        # Get aliases from the form options
        self.get_aliases_from_options()

        # Get team matches
        for tpl in self.parsed.templates:
            name = tpl.normal_name(capitalize=True)
            if name in ("TeamMatch", "TeamMatch/Code", "TeamMatchCompact", "ProleagueMatchNL") and (
                tm_result := self.convert_team_match(tpl)
            ):
                self.team_matches.append(TeamMatchEntry(*tm_result))

        # Group match summaries of a section into a matchlist (if enabled)
        if self.options["group_matches_of_section"]:
            self.group_match_summaries()

        # Group team matches of a section into a matchlist (if enabled)
        if self.options["group_team_matches_of_section"]:
            self.group_team_matches()

        # Parse templates (Pass 1)
        self.single_match_ids = []
        for tpl in self.parsed.templates:
            name = tpl.normal_name(capitalize=True)

            match name:
                case "SingleMatch":
                    if x := tpl.get_arg("id"):
                        self.single_match_ids.append(clean_arg_value(x))
                case "Bracket" | "LegacyBracket" | "LegacyBracketDisplay":
                    if (x1 := tpl.get_arg("1")) and clean_arg_value(x1) == "Bracket/2" and (x := tpl.get_arg("id")):
                        self.single_match_ids.append(clean_arg_value(x))

        # For the second pass, we mix tables and templates
        parsed_tables_and_templates = sorted(self.parsed.tables + self.parsed.templates, key=lambda obj: obj.span)

        # Parse tables and templates (Pass 2)
        self.prize_pool_text = ""
        self.prize_pool_start_pos = -1
        self.prize_texts = []
        self.match_list_text = ""
        self.match_list_start_pos = -1
        self.match_texts = []
        self.participant_table_span = (-1, -1)
        for tbl_or_tpl in parsed_tables_and_templates:
            if isinstance(tbl_or_tpl, wtp.Table) and not self.options["participant_table_do_not_convert"]:
                self.pass2_for_table(tbl_or_tpl)
            elif isinstance(tbl_or_tpl, wtp.Template):
                self.pass2_for_template(tbl_or_tpl)

        # Convert match summaries that have not been moved or grouped
        for ms_entry in self.match_summaries:
            if ms_entry.grouped:
                # Do nothing
                pass
            elif ms_entry.moved:
                self.changes.append((*ms_entry.span, ""))
            else:
                mid = generate_id()
                new_text = f"{{{{SingleMatch|id={mid}" + "\n|M1={{Match\n" + "\n".join(ms_entry.texts) + "\n}}\n}}"
                self.changes.append((*ms_entry.span, new_text))

        # Convert team matches that have not been moved or grouped
        for tm_entry in self.team_matches:
            if tm_entry.grouped:
                # Do nothing
                pass
            elif tm_entry.moved:
                self.changes.append((*tm_entry.span, ""))
            else:
                mid = generate_id()
                new_text = f"{{{{SingleMatch|id={mid}" + "\n" + "|M1={{Match\n" + tm_entry.text + "\n}}\n}}"
                self.changes.append((*tm_entry.span, new_text))

        # Enable storage if needed
        if self.storage_to_enable:
            self.info += "⚠️ Storage to enable\n"
            for tpl in self.parsed.templates:
                name = tpl.normal_name(capitalize=True)
                if (
                    name in ("LPDB storage", "SMW storage")
                    and (x := tpl.get_arg("1"))
                    and clean_arg_value(x) in ("no", "false")
                ):
                    self.changes.append((*tpl.span, "{{HDB}}"))

        # Apply changes
        converted = self.text
        for start, end, new_text in sorted(self.changes, reverse=True):
            converted = f"{converted[:start]}{new_text}{converted[end:]}"

        if self.not_converted_arguments:
            self.info += f"⚠️ Arguments not converted: {len(self.not_converted_arguments)} "
            self.info += str(sorted(self.not_converted_arguments))

        return converted

    def pass2_for_table(self, tbl: wtp.Table) -> None:
        if table_result := self.convert_table_to_participant_table(tbl):
            self.changes.append((*tbl.span, table_result))
            self.participant_table_span = tbl.span

    def pass2_for_template(self, tpl: wtp.Template) -> None:
        name = tpl.normal_name(capitalize=True)

        if not self.options["prize_pool_table_do_not_convert"]:
            match name:
                case "Prize pool start":
                    texts = self.arguments_to_texts(PRIZE_POOL_START_ARGUMENTS, tpl)
                    if self.options["import_limit"] == "fixed":
                        texts.append(f"|importLimit={self.options['import_limit_fixed_val']}")
                    elif self.options["import_limit"] == "guess":
                        texts.append(f"|importLimit=%@%£%$%")
                    self.prize_pool_text = "{{SoloPrizePool" + "".join(texts) + "\n"
                    self.prize_pool_start_pos = tpl.span[0]
                    self.prize_texts = []
                    self.prize_pool_max_placement = 0
                case "Prize pool slot":
                    if pps_result := self.convert_prize_pool_slot(tpl):
                        self.prize_texts.append(pps_result)
                case "LegacyPrizePoolEnd":
                    prize_pool_end_pos = tpl.span[1]
                    if self.options["import_limit"] == "guess":
                        self.prize_pool_text = self.prize_pool_text.replace(
                            "%@%£%$%", str(self.prize_pool_max_placement)
                        )
                    self.prize_pool_text += "\n".join(f"|{slot_text}" for slot_text in self.prize_texts)
                    self.prize_pool_text += "\n}}"
                    self.changes.append((self.prize_pool_start_pos, prize_pool_end_pos, self.prize_pool_text))

                case "Prize pool start team":
                    texts = self.arguments_to_texts(PRIZE_POOL_START_ARGUMENTS, tpl)
                    if self.options["import_limit"] == "fixed":
                        texts.append(f"|importLimit={self.options['import_limit_fixed_val']}")
                    elif self.options["import_limit"] == "guess":
                        texts.append(f"|importLimit=%@%£%$%")
                    self.prize_pool_text = "{{TeamPrizePool" + "".join(texts) + "\n"
                    self.prize_pool_start_pos = tpl.span[0]
                    self.prize_texts = []
                    self.prize_pool_max_placement = 0
                case "Prize pool slot team":
                    if ppst_result := self.convert_prize_pool_slot_team(tpl):
                        self.prize_texts.append(ppst_result)
                case "LegacyPrizePoolEnd team":
                    prize_pool_end_pos = tpl.span[1]
                    if self.options["import_limit"] == "guess":
                        self.prize_pool_text = self.prize_pool_text.replace(
                            "%@%£%$%", str(self.prize_pool_max_placement)
                        )
                    self.prize_pool_text += "\n".join(f"|{slot_text}" for slot_text in self.prize_texts)
                    self.prize_pool_text += "\n}}"
                    self.changes.append((self.prize_pool_start_pos, prize_pool_end_pos, self.prize_pool_text))

        match name:
            case "Legacy Match list start":
                texts = self.arguments_to_texts(MATCH_LIST_ARGUMENTS, tpl)
                self.match_list_text = "{{Matchlist" + "".join(texts) + "\n"
                self.match_list_start_pos = tpl.span[0]
                self.match_texts = []
                self.match_list_id = clean_arg_value(tpl.get_arg("id"))
                self.match_list_comments = []
                self.match_maps_prev_bestof = None
                if (x := tpl.get_arg("vod")) and (vod := clean_arg_value(x)):
                    self.match_list_vod = vod
                    self.info += (
                        f"⚠️ vod in Match list start {self.match_list_id} moved to the first match of the list\n"
                    )
                else:
                    self.match_list_vod = None
            case "Match maps":
                if mm_result := self.convert_match_maps(tpl):
                    self.match_texts.append(mm_result)
            case "Match maps team":
                if mmt_result := self.convert_match_maps_team(tpl):
                    self.match_texts.append(mmt_result)
            case "Match list comment":
                self.info += "⚠️ Match list comment may be lost\n"
                self.match_list_comments.append(clean_arg_value(tpl.get_arg("1")))
            case "Match list end":
                match_list_end_pos = tpl.span[1]
                self.match_list_text += "\n".join(
                    f"|M{i}={match_text}" for i, match_text in enumerate(self.match_texts, start=1)
                )
                self.match_list_text += "\n}}"
                if self.match_list_comments:
                    self.match_list_text += "\n" + " ".join(self.match_list_comments)
                if self.match_list_vod:
                    self.info += "⚠️ ... No match to move the VOD to\n"
                self.changes.append((self.match_list_start_pos, match_list_end_pos, self.match_list_text))

            case "LegacyBracket" | "LegacyBracketDisplay":
                if bracket_result := self.convert_bracket(tpl):
                    self.changes.append((*tpl.span, bracket_result))

            case "ExternalCupList":
                if self.options["external_cup_list_convert"] and (list_result := self.convert_external_cup_list(tpl)):
                    self.changes.append((*tpl.span, list_result))

            case "StorePlayerLink":
                self.add_participant_from_player_template(tpl)
            case "Player":
                # Do not process templates already processed as part of a participant table
                if tpl.span[0] < self.participant_table_span[0] or tpl.span[1] > self.participant_table_span[1]:
                    self.add_participant_from_player_template(tpl)
            case "ParticipantTable" | "ParticipantSection":
                participants = self.add_participants_from_participant_table(tpl)
                if self.options["participant_table_convert_first_to_qualified_prize_pool_table"]:
                    prize_pool_table = self.prize_pool_table_from_sections([Section("", participants)])
                    self.changes.append((*tpl.span, prize_pool_table))

            case _:
                if "TeamBracket" in name or name in ("IPTLBracket", "TeSLBracket"):
                    name = name.replace("TeamBracket", "Bracket")
                    if team_bracket_result := self.convert_team_bracket(tpl, name):
                        self.changes.append((*tpl.span, team_bracket_result))

    def get_aliases_from_options(self) -> None:
        self.tm_player_aliases = {}
        if self.options["team_match_player_aliases"]:
            self.tm_player_aliases = {
                (name, flag, race): link
                for name, flag, race, link in (
                    line.split("|") for line in self.options["team_match_player_aliases"].replace("\r", "").split("\n")
                )
            }
        self.team_aliases = {}
        if self.options["team_aliases"]:
            self.team_aliases = {
                name: new_name
                for name, new_name in (
                    line.split("|") for line in self.options["team_aliases"].replace("\r", "").split("\n")
                )
            }

    def group_match_summaries(self) -> None:
        sections = get_sections(self.text)
        italics = get_italics(self.text)
        try:
            section = next(
                section for section in sections if section.title == self.options["group_matches_of_section"]
            )
        except StopIteration:
            print(f"Section {self.options['group_matches_of_section']} not found")
        else:
            start, end = section.contents_span
            stuff = sorted(
                (
                    *((child.title_span, child) for child in section.children),
                    *((it.span, it) for it in italics),
                    *(
                        (ms_entry.span, ms_entry)
                        for ms_entry in self.match_summaries
                        if start <= ms_entry.span[0] and ms_entry.span[1] <= end
                    ),
                )
            )

            mid = generate_id()
            new_text = f"{{{{Matchlist|id={mid}" + "\n"
            i = 1
            date = ""
            for item in stuff:
                if isinstance(item[1], mwtp_Section):
                    if HIDDEN_ANCHOR_PATTERN.search(item[1].title) is None:
                        new_text += f"|M{i}header={item[1].title}" + "\n"
                    date = ""
                elif isinstance(item[1], Italic):
                    if DATE_PATTERN.search(item[1].text):
                        date = item[1].text
                elif isinstance(item[1], MatchSummaryEntry):
                    new_text += f"|M{i}={{{{Match" + "\n"
                    if date:
                        new_text += f"|date={date}" + "\n"
                    new_text += "\n".join(item[1].texts) + "\n}}\n"
                    item[1].grouped = True
                    i += 1
            new_text += "}}\n"
            self.changes.append((*section.contents_span, new_text))

    def group_team_matches(self) -> None:
        sections = get_sections(self.text)
        italics = get_italics(self.text)
        target_sections = (s.strip() for s in self.options["group_team_matches_of_section"].split(","))
        mode = self.options["group_team_matches_mode"] or "single"

        for target_section in target_sections:
            try:
                section = next(section for section in sections if section.title == target_section)
            except StopIteration:
                print(f"Section {target_section} not found")
            else:
                start, end = section.contents_span
                stuff = sorted(
                    (
                        *((child.title_span, child) for child in section.children),
                        *((it.span, it) for it in italics),
                        *(
                            (tm_entry.span, tm_entry)
                            for tm_entry in self.team_matches
                            if start <= tm_entry.span[0] and tm_entry.span[1] <= end
                        ),
                    )
                )

                mid = generate_id()
                if mode == "single":
                    new_text = f"{{{{Matchlist|id={mid}"
                    if self.options["group_team_matches_width"]:
                        new_text += f"|width={self.options['group_team_matches_width']}"
                    if self.options["group_team_matches_uncollapsed"]:
                        new_text += "|collapsed=false"
                    new_text += "\n"
                elif mode == "multiple":
                    new_text = ""
                section_text = ""
                i = 1
                date = ""
                for item in stuff:
                    if isinstance(item[1], mwtp_Section):
                        if mode == "single":
                            if HIDDEN_ANCHOR_PATTERN.search(item[1].title) is None:
                                new_text += f"|M{i}header={item[1].title}" + "\n"
                        elif mode == "multiple":
                            if not new_text:
                                new_text += "{{Box|start|padding=4em}}\n"
                            elif section_text:
                                # Close the matchlist
                                section_text += "}}\n"
                                new_text += section_text
                                new_text += "{{Box|break|padding=4em}}\n"
                            new_text += "\n" + f"{'=' * item[1].level}{item[1].title}{'=' * item[1].level}" + "\n"
                            mid = generate_id()
                            section_text = f"{{{{Matchlist|id={mid}|collapsed=false"
                            if self.options["group_team_matches_width"]:
                                section_text += f"|width={self.options['group_team_matches_width']}"
                            section_text += "\n"
                            i = 1
                        date = ""
                    elif isinstance(item[1], Italic):
                        if DATE_PATTERN.search(item[1].text):
                            date = item[1].text
                    elif isinstance(item[1], TeamMatchEntry):
                        match_text = f"|M{i}={{{{Match" + "\n"
                        if date:
                            match_text += f"|date={date}" + "\n"
                        match_text += item[1].text + "\n}}\n"
                        if mode == "single":
                            new_text += match_text
                        elif mode == "multiple":
                            section_text += match_text
                        item[1].grouped = True
                        i += 1
                if mode == "single":
                    new_text += "}}\n"
                elif mode == "multiple" and section_text:
                    section_text += "}}\n"
                    new_text += section_text
                    new_text += "{{Box|end}}\n"

                self.changes.append((*section.contents_span, new_text))

    def convert_table_to_participant_table(self, table: wtp.Table) -> None:
        sections: list[Section] = [Section("")]
        has_a_player = False
        has_a_teampart_tpl = False
        has_a_race_cell = False
        has_race_count = False
        has_section_count = False
        notes = set()
        players_with_asterisk = {}

        if table.tables or not (rows := table.data(span=True)):
            return None

        cells = table.cells(span=False)
        two_cols_per_race = False
        if max(len(row) for row in rows) > 4:
            if any(c.get_attr("colspan") != "2" for c in cells[0]):
                return None
            two_cols_per_race = True
            table_races = [SHORT_RACES[x // 2] for x in range(8)]
        else:
            table_races = list(SHORT_RACES)

        for row, col, c in ((row, col, c) for row, row_cells in enumerate(cells) for col, c in enumerate(row_cells)):
            val = c.value.strip()
            if not val:
                continue
            if colspan := c.get_attr("colspan") and (row != 0 or not two_cols_per_race):
                # Clean up: remove section count
                if RACE_OR_SECTION_COUNT_PATTERN.search(val):
                    val = RACE_OR_SECTION_COUNT_PATTERN.sub("", val).strip()
                    has_section_count = True
                sections.append(Section(val))

            if not has_a_race_cell:
                for link in c.wikilinks:
                    if link.title in (f"File:{x}icon.png" for x in "PTZR"):
                        has_a_race_cell = True
                        break

            p = Participant(race=table_races[col])
            for tpl in c.templates:
                name = tpl.normal_name(capitalize=True)
                if name in ("TeamPart", "TeamIcon"):
                    has_a_teampart_tpl = True
                    p.team = clean_arg_value(tpl.get_arg("1"))
                elif name in ("Player", "Playersp"):
                    if x := tpl.get_arg("1"):
                        p.name = clean_arg_value(x)
                        if m := PIPE_PATTERN.match(p.name):
                            p.link, p.name = m.groups()
                    if x := tpl.get_arg("flag"):
                        p.flag = clean_arg_value(x)
                    if x := tpl.get_arg("race"):
                        p.race = clean_arg_value(x)
                    if x := tpl.get_arg("link"):
                        p.link = clean_arg_value(x)
                elif m := FLAG_TEMPLATE_PATTERN.match(name):
                    p.flag = m.group(1)
                    if c.wikilinks:
                        link = c.wikilinks[0]
                        if link.text is not None:
                            p.name = link.text.strip()
                            p.link = link.title.strip()
                        else:
                            p.name = link.title.strip()
                    else:
                        p.name = c.plain_text().strip().removeprefix("|").lstrip()
                elif name == "RaceColorClass" or name == "RaceIconSmall":
                    race = clean_arg_value(tpl.get_arg("1"))[0].lower()
                    race = RACES.get(race, race)
                    race_index = col * 2 if two_cols_per_race else col
                    if race == "r" and "Unknown" in val:
                        table_races[race_index] = "u"
                    else:
                        table_races[race_index] = race
                    if RACE_OR_SECTION_COUNT_PATTERN.search(val):
                        has_race_count = True
                    has_a_race_cell = True
                elif name in ("P", "T", "Z", "R"):
                    race = name.lower()
                    race = RACES.get(race, race)
                    race_index = col * 2 if two_cols_per_race else col
                    if race == "r" and "Unknown" in val:
                        table_races[race_index] = "u"
                    else:
                        table_races[race_index] = race
                    has_a_race_cell = True
            if not p.name:
                del p
                continue
            has_a_player = True
            if "<s>" in val:
                p.dq = True
                if m := STRIKETHROUGH_PATTERN.match(p.name):
                    p.name = m.group(1)
                    if p.link == p.name:
                        p.link = ""
            if notes_m := NOTE_PATTERN.findall(val):
                p.notes = list(chain.from_iterable(n.split(",") for n in notes_m))
                notes |= set(p.notes)
            if m := ASTERISK_PATTERN.search(val):
                players_with_asterisk[p.name] = len(m.group(1))
            sections[-1].participants.append(p)

        # Exit the function if the table is not a participant table
        if not ((has_a_teampart_tpl and has_a_player) or has_a_race_cell):
            return None

        # This is a valid participant table
        self.prize_pool_tables_processed += 1

        # If this is the first table and the user has decided not to convert it, then we exit early
        if self.options["participant_table_do_not_convert_first"] and self.prize_pool_tables_processed == 1:
            return None

        for section in sections:
            self.participants |= {p.name: p for p in section.participants}
        if table.comments:
            self.info += "⚠️ Comments in participant table will be lost\n"

        # Set the note property for players with one or more asterisks
        if players_with_asterisk:
            self.info += "⚠️ Asterisks converted to notes in participant table\n"
            for name, asterisk_count in players_with_asterisk.items():
                n = asterisk_count
                while str(n) in notes:
                    n += 1
                self.participants[name].notes.append(str(n))

        if (
            self.options["participant_table_convert_first_to_qualified_prize_pool_table"]
            and self.prize_pool_tables_processed == 1
        ):
            return self.prize_pool_table_from_sections(sections)

        return self.participants_table_from_sections(sections, has_race_count, has_section_count)

    def participants_table_from_sections(
        self, sections: list[Section], enable_count: bool = False, enable_section_count: bool = False
    ) -> str:
        has_a_non_empty_team = any(p.team for section in sections for p in section.participants)

        result = "{{ParticipantTable"
        if enable_count:
            result += "|count=1"
        if enable_section_count:
            result += "|showCountBySection=1"
        result += "\n"
        for section in sections:
            if section.title:
                result += f"|{{{{ParticipantSection|title={section.title}\n"
            for i, p in enumerate(section.participants, start=1):
                result += f"|{p.name}"
                if p.link:
                    result += f"|p{i}link={p.link}"
                if self.options["player_details"]:
                    result += f"|p{i}flag={p.flag}|p{i}race={p.race}"
                if self.options["team_details"] and has_a_non_empty_team:
                    result += f'|p{i}team={p.team or ""}'
                if p.dq:
                    result += f"|p{i}dq=1"
                if p.notes:
                    result += f"|p{i}note={','.join(p.notes)}"
                result += "\n"
            if section.title:
                result += "}}\n"
        result += "}}"
        return result

    def prize_pool_table_from_sections(self, sections: list[Section]) -> str:
        participants = tuple(p for section in sections for p in section.participants)
        qualifies_to = self.title[: self.title.rfind("/")] if "/" in self.title else ""
        result = f"{{{{SoloPrizePool|importLimit={len(participants)}|qualifies={qualifies_to}" + "\n"
        result += "|{{Slot|qualified=1\n"
        for p in participants:
            result += f" |{{{{Opponent|{p.name}"
            if p.link:
                result += f"|link={p.link}"
            if self.options["prize_pool_opponent_details"]:
                result += f"|flag={p.flag}|race={p.race}"
                result += f'|team={p.team or ""}'
            result += "}}\n"
        result += "}}\n}}"
        return result

    def convert_prize_pool_slot(self, tpl: wtp.Template) -> str | None:
        texts: list[str] = []

        texts = self.arguments_to_texts(PRIZE_POOL_SLOT_ARGUMENTS, tpl)

        if self.options["prize_pool_opponent_details"] or self.options["prize_pool_opponent_last_results"]:
            detail_texts: list[str] = []
            i = 1
            date = None
            if x := tpl.get_arg("date"):
                date = clean_arg_value(x)
            while x := tpl.get_arg(str(i)):
                player = PrizePoolPlayer(name=clean_arg_value(x))
                if m := PIPE_PATTERN.match(player.name):
                    player.link, player.name = m.groups()
                if x := tpl.get_arg(f"link{i}"):
                    player.link = clean_arg_value(x)
                if self.options["prize_pool_opponent_details"]:
                    if x := tpl.get_arg(f"flag{i}"):
                        player.flag = clean_arg_value(x)
                    if x := tpl.get_arg(f"race{i}"):
                        player.race = clean_arg_value(x)
                    if x := tpl.get_arg(f"team{i}"):
                        player.team = clean_arg_value(x)
                if self.options["prize_pool_opponent_last_results"]:
                    if x := tpl.get_arg(f"lastscore{i}"):
                        player.lastscore = clean_arg_value(x)
                    if x := tpl.get_arg(f"lastvs{i}"):
                        player.lastvs = clean_arg_value(x)
                    if x := tpl.get_arg(f"lastvslink{i}"):
                        player.lastvslink = clean_arg_value(x)
                    if x := tpl.get_arg(f"lastvsflag{i}"):
                        player.lastvsflag = clean_arg_value(x)
                    if x := tpl.get_arg(f"lastvsrace{i}"):
                        player.lastvsrace = clean_arg_value(x)
                    if x := tpl.get_arg(f"lastvsscore{i}"):
                        player.lastvsscore = clean_arg_value(x)
                    if x := tpl.get_arg(f"woto{i}"):
                        player.woto = clean_arg_value(x)
                    if x := tpl.get_arg(f"wofrom{i}"):
                        player.wofrom = clean_arg_value(x)
                    if x := tpl.get_arg(f"wdl{i}"):
                        player.wdl = clean_arg_value(x)
                    if x := tpl.get_arg(f"date{i}"):
                        player.date = clean_arg_value(x)
                if player.name:
                    text = f"|{{{{Opponent|{player.name}"
                    if self.options["prize_pool_opponent_details"]:
                        text += f"|flag={player.flag}|race={player.race}"
                    if player.link:
                        text += f"|link={player.link}"
                    if self.options["prize_pool_opponent_details"]:
                        if player.team:
                            text += f"|team={player.team}"
                    if self.options["prize_pool_opponent_last_results"]:
                        if player.wdl:
                            text += f"|wdl={player.wdl}"
                        elif player.lastvs:
                            if player.lastvslink:
                                text += f"|lastvs={player.lastvslink}"
                            else:
                                text += f"|lastvs={player.lastvs}"
                            if player.woto:
                                text += f"|lastvsscore=L-W"
                            elif player.wofrom:
                                text += f"|lastvsscore=W-L"
                            elif player.lastscore and player.lastvsscore:
                                text += f"|lastvsscore={player.lastscore}-{player.lastvsscore}"
                        if player.date or date:
                            text += f"|date={player.date or date}"
                    text += "}}"
                    detail_texts.append(text)
                i += 1
            if len(detail_texts) > 1:
                # Insert a new line if there are multiple players in the slot
                texts += [f"\n {text}" for text in detail_texts]
            elif detail_texts:
                texts.append(detail_texts[0])

        if (
            (x := tpl.get_arg("place"))
            and (m := PLACE_PATTERN.search(clean_arg_value(x)))
            and (place := int(m.group(0))) > self.prize_pool_max_placement
        ):
            self.prize_pool_max_placement = place

        return "{{Slot" + "".join(texts) + "}}"

    def convert_prize_pool_slot_team(self, tpl: wtp.Template) -> str | None:
        texts: list[str] = []

        texts = self.arguments_to_texts(PRIZE_POOL_SLOT_TEAM_ARGUMENTS, tpl)

        if self.options["prize_pool_opponent_details"]:
            detail_texts: list[str] = []
            i = 1
            while x := tpl.get_arg(str(i)):
                team_name = clean_arg_value(x)
                if team_name:
                    text = f"|{{{{Opponent|{team_name}}}}}"
                    detail_texts.append(text)
                i += 1
            if len(detail_texts) > 1:
                # Insert a new line if there are multiple players in the slot
                texts += [f"\n {text}" for text in detail_texts]
            elif detail_texts:
                texts.append(detail_texts[0])

        if (
            (x := tpl.get_arg("place"))
            and (m := PLACE_PATTERN.search(clean_arg_value(x)))
            and (place := int(m.group(0))) > self.prize_pool_max_placement
        ):
            self.prize_pool_max_placement = place

        return "{{Slot" + "".join(texts) + "}}"

    def convert_match_summary(self, tpl: wtp.Template) -> list[str] | None:
        players = [MatchPlayer(), MatchPlayer()]
        texts: list[str] = []

        for i, player in enumerate(players, start=1):
            if x := tpl.get_arg(str(i)):
                player.name = clean_arg_value(x)
            if x := tpl.get_arg(f"link{i}"):
                player.link = clean_arg_value(x)
            if x := tpl.get_arg(f"flag{i}"):
                player.flag = clean_arg_value(x)
            if x := tpl.get_arg(f"race{i}"):
                player.race = clean_arg_value(x)
            if player.name:
                found, offrace = self.look_for_player(player)
                text = f"|opponent{i}={{{{1Opponent|{player.name}"
                if not found:
                    text += f"|flag={player.flag}|race={player.race}"
                elif offrace:
                    text += f"|race={player.race}"
                text += "}}"
                texts.append(text)

        start_texts, end_texts = self.arguments_to_texts(MATCH_SUMMARY_ARGUMENTS, tpl)
        texts += start_texts

        if not tpl.get_arg("bestof"):
            texts.append("|bestof=3")

        i = 1
        has_set_map = False
        while True:
            x = tpl.get_arg(f"map{i}")
            if x:
                map_ = clean_arg_value(x)
                if m := PIPE_PATTERN.match(map_):
                    map_, map_display_name = m.groups()
                else:
                    map_display_name = ""
                if map_ in ("TBD", "TBA"):
                    map_ = ""
                if map_:
                    has_set_map = True
            else:
                map_ = ""
                map_display_name = ""
            x_win = tpl.get_arg(f"win{i}")
            if x or x_win:
                winner = clean_arg_value(x_win)
                winner = "" if winner == "0" else winner
                text = f"|map{i}={{{{Map|map={map_}"
                if map_display_name:
                    text += f"|mapDisplayName={map_display_name}"
                text += f"|winner={winner}}}}}"
                texts.append()
                i += 1
            else:
                break

        veto_index = 1
        if x := tpl.get_arg("veto1"):
            texts.append(f"|veto1={clean_arg_value(x)}|vetoplayer1=1")
            veto_index = 2
        if x := tpl.get_arg("veto2"):
            texts.append(f"|veto{veto_index}={clean_arg_value(x)}|vetoplayer{veto_index}=2")

        texts += end_texts

        return tpl.span, has_set_map, players, texts

    def convert_team_match(self, tpl: wtp.Template, opponents: tuple[str] | None = None) -> str | None:
        self.tm_args = clean_arguments(tpl)

        # Get players
        self.tm_has_set_map = False
        self.tm_opponent_has_tbd = [False, False]
        maps: list[str] = []
        self.tm_players: list[dict[str, MatchPlayer]] = [{}, {}]
        game_index = 1
        for i in range(1, 101):
            if (
                self.tm_args.get(f"m{i}win")
                or self.tm_args.get(f"m{i}p1")
                or self.tm_args.get(f"m{i}map")
                or self.tm_args.get(f"m{i}p2")
            ):
                maps.append(self.convert_team_match_helper(f"m{i}", str(i), game_index))
                game_index += 1

        if (
            self.tm_args.get(f"acewin")
            or self.tm_args.get(f"acep1")
            or self.tm_args.get(f"acemap")
            or self.tm_args.get(f"acep2")
        ):
            maps.append(self.convert_team_match_helper(f"ace", "ace", game_index))
            game_index += 1
        for i in range(1, 4):
            if (
                self.tm_args.get(f"ace{i}win")
                or self.tm_args.get(f"ace{i}p1")
                or self.tm_args.get(f"ace{i}map")
                or self.tm_args.get(f"ace{i}p2")
            ):
                maps.append(self.convert_team_match_helper(f"ace{i}", f"ace{i}", game_index))
                game_index += 1
            else:
                break

        # Get opponents (if not given as argument)
        if not opponents:
            opponents = tuple(
                FLAG_TEAM_PATTERN.sub(
                    "",
                    self.tm_args.get(f"team{i}")
                    or self.tm_args.get(f"team{i}short")
                    or self.tm_args.get(f"team{i}literal")
                    or "",
                )
                for i in range(1, 3)
            )
        opponents = tuple(self.team_aliases.get(opponent.lower(), opponent) for opponent in opponents)
        opponent_texts = []
        for i, opponent in enumerate(opponents, start=1):
            opp_players = find_players(wtp.parse(opponent))
            if 0 < len(opp_players) < 5:
                # For teams that are actually 1, 2, 3 or 4 player templates
                opponent = "&".join(sorted(player.name for player in opp_players))

            opponent_text = f"{{{{TeamOpponent|{opponent}"
            if self.options["team_match_add_player_lists"]:
                players_text = ""
                for j, player in enumerate(self.tm_players[i - 1].values(), start=1):
                    players_text += f"|p{j}={player.name}"
                    if player.link and player.link != player.name:
                        players_text += f"|p{j}link={player.link}"
                    players_text += f"|p{j}flag={player.flag}"
                    players_text += f"|p{j}race={player.race}"
                if not players_text and self.tm_opponent_has_tbd[i - 1]:
                    players_text = "|p1=TBD"
                if players_text:
                    opponent_text += f"|players={{{{Players{players_text}}}}}"
            if score := self.tm_args.get(f"team{i}score"):
                opponent_text += f"|score={score}"
            opponent_text += "}}"
            opponent_texts.append(opponent_text)

        start_texts, end_texts = self.arguments_to_texts(TEAM_MATCH_ARGUMENTS, tpl)

        text = ""
        if start_texts:
            text += "\n".join(start_texts) + "\n"
        if self.options["team_match_enable_dateheader"]:
            text += f"|dateheader=true" + "\n"
        text += f"|opponent1={opponent_texts[0]}" + "\n"
        text += f"|opponent2={opponent_texts[1]}"
        if winner := self.tm_args.get("teamwin"):
            text += "\n" + f"|winner={winner}"
        if maps:
            text += "\n" + "\n".join(f"|map{i}={text}" for i, text in enumerate(maps, start=1))
        if end_texts:
            text += "\n" + "\n".join(end_texts)
        return tpl.span, self.tm_has_set_map, tuple(opp.lower() for opp in opponents), text

    def convert_team_match_helper(self, prefix: str, original_game_index: str, game_index: int) -> str:
        text = ""
        for j in range(1, 3):
            player_prefixes = [f"{prefix}p{j}"]
            if self.tm_args.get("2v2") == original_game_index:
                player_prefixes.append(f"2v2p{j}")
            else:
                player_prefixes += [f"{prefix}t{j}p{k}" for k in range(2, 5)]

            for k, player_prefix in enumerate(player_prefixes, start=1):
                player = MatchPlayer()
                player.name = self.tm_args.get(player_prefix, "")
                player.link = self.tm_args.get(f"{player_prefix}link", "")
                if player.link in ("false", "true"):
                    player.link = ""
                player.flag = self.tm_args.get(f"{player_prefix}flag", "")
                player.race = self.tm_args.get(f"{player_prefix}race", "").lower()
                if k == 1 and not player.name:
                    player.name = "TBD"

                is_archon = False
                if k == 1 and self.options["team_match_plus_for_archon"] and " + " in player.name:
                    players = [MatchPlayer(name, "", "", player.race) for name in player.name.split(" + ")]
                    is_archon = True
                elif (
                    k == 1
                    and self.options["team_match_br_for_2v2"]
                    and (
                        (j == 1 and (m := BR_2V2_PATTERN1.match(player.name)))
                        or (j == 2 and (m := BR_2V2_PATTERN2.match(player.name)))
                    )
                ):
                    if j == 1:
                        players = [
                            MatchPlayer(m.group(1) or m.group(2), "", m.group(4) or "", (m.group(3) or "").lower()),
                            MatchPlayer(m.group(5) or m.group(6), "", m.group(8) or "", (m.group(7) or "").lower()),
                        ]
                    elif j == 2:
                        players = [
                            MatchPlayer(m.group(3) or m.group(4), "", m.group(1) or "", (m.group(2) or "").lower()),
                            MatchPlayer(m.group(7) or m.group(8), "", m.group(5) or "", (m.group(6) or "").lower()),
                        ]
                else:
                    players = [player]
                for k_increment, player in enumerate(players):
                    if player.name:
                        # Look for an alias
                        if (ptuple := (player.name, player.flag, player.race)) in self.tm_player_aliases:
                            print(
                                f"Alias {self.tm_player_aliases[ptuple]} for {player.name} (flag={player.flag}, race={player.race})"
                            )
                            player.link = self.tm_player_aliases[ptuple]

                        offrace = (
                            player.name in self.tm_players[j - 1]
                            and player.race != self.tm_players[j - 1][player.name].race
                        )
                        if player.name == "TBD":
                            self.tm_opponent_has_tbd[j - 1] = True
                        elif player.name not in self.tm_players[j - 1]:
                            self.tm_players[j - 1][player.name] = player
                        elif self.tm_players[j - 1][player.name].flag == "" and player.flag != "":
                            self.tm_players[j - 1][player.name].flag = player.flag
                        text += f"|t{j}p{k + k_increment}={player.link or player.name}"
                        if player.race and (offrace or player.name == "TBD") and not is_archon:
                            text += f"|t{j}p{k}race={player.race}"
                if is_archon:
                    text += f"|opponent{j}archon=true|opponent{j}race={players[0].race}"
            if self.options["team_match_make_duos_archons"] and len(player_prefixes) == 2:
                text += f"|opponent{j}archon=true|opponent{j}race={players[0].race}"

        map = self.tm_args.get(f"{prefix}map") or ""
        if m := PIPE_PATTERN.match(map):
            map = m.group(2)
        if map in ("TBD", "TBA"):
            map = ""
        if map:
            self.tm_has_set_map = True
        winner = self.tm_args.get(f"{prefix}win")

        text = f"{{{{Map{text}|map={map}|winner={winner}"
        if (
            vod := self.tm_args.get(f"vod{game_index}")
            or self.tm_args.get(f"vodgame{game_index}")
            or self.tm_args.get(f"m{game_index}vod")
        ):
            text += f"|vod={vod}"
        if walkover := self.tm_args.get(f"{prefix}walkover"):
            text += f"|walkover={walkover}"
        text += "}}"

        return text

    def convert_match_maps(self, tpl: wtp.Template) -> str | None:
        players = [MatchPlayer(), MatchPlayer()]
        texts: list[str] = []
        scores = ["", ""]

        info_id_text = f"[Matchlist {self.match_list_id}][M{len(self.match_texts) + 1}]"
        if tpl.comments:
            self.info += f"⚠️ {info_id_text} Comments will be lost\n"

        # Parse maps first
        map_texts = []
        map_scores = [0, 0]
        vodgames_processed = []
        has_a_non_empty_map = False
        i = 1
        while True:
            x = tpl.get_arg(f"map{i}")
            x_win = tpl.get_arg(f"map{i}win")
            if x or x_win:
                map_ = clean_arg_value(x)
                if m := PIPE_PATTERN.match(map_):
                    map_, map_display_name = m.groups()
                else:
                    map_display_name = ""
                if map_ == "Unknown":
                    map_ = ""
                map_winner = clean_arg_value(x_win)
                map_text = f"|map{i}={{{{Map|map={map_}"
                if map_display_name:
                    map_text += f"|mapDisplayName={map_display_name}"
                map_text += f"|winner={map_winner}"
                map_has_race = False
                for j in (1, 2):
                    if x := tpl.get_arg(f"map{i}p{j}race"):
                        map_has_race = True
                        map_text += f"|t{j}p1race={clean_arg_value(x)}"
                x_vod = tpl.get_arg(f"vodgame{i}")
                if vod := clean_arg_value(x_vod):
                    map_text += f"|vod={vod}"
                    vodgames_processed.append(i)
                map_text += "}}"
                map_texts.append(map_text)
                if map_ or vod or map_has_race:
                    has_a_non_empty_map = True
                if map_winner in ("1", "2"):
                    map_scores[int(map_winner) - 1] += 1
                i += 1
            else:
                break

        # Parse players
        for i, player in enumerate(players, start=1):
            if x := tpl.get_arg(f"player{i}"):
                player.name = clean_arg_value(x)
            if x := tpl.get_arg(f"player{i}flag"):
                player.flag = clean_arg_value(x)
            if x := tpl.get_arg(f"player{i}race"):
                player.race = clean_arg_value(x)
            if x := tpl.get_arg(f"p{i}score"):
                scores[i - 1] = clean_arg_value(x)
            if player.name:
                text = f"|opponent{i}={{{{1Opponent|{player.name}"
                if self.options["match_maps_player_details"] == "remove_if_stored":
                    found, offrace = self.look_for_player(player)
                    if not found:
                        text += f"|flag={player.flag}|race={player.race}"
                    elif offrace:
                        text += f"|race={player.race}"
                elif self.options["match_maps_player_details"] == "keep":
                    if tpl.get_arg(f"player{i}flag"):
                        text += f"|flag={player.flag}"
                    if tpl.get_arg(f"player{i}race"):
                        text += f"|race={player.race}"
                if scores[i - 1]:
                    text += f"|score={scores[i - 1]}"
                    if map_texts and str(map_scores[i - 1]) != scores[i - 1]:
                        self.info += f"⚠️ {info_id_text} Discrepancy between map score and score ({player.name})\n"
                elif map_texts and not has_a_non_empty_map and sum(map_scores) > 0:
                    scores[i - 1] = str(map_scores[i - 1])
                    text += f"|score={scores[i - 1]}"
                text += "}}"
                texts.append(text)

        # Is it a walkover?
        is_walkover = clean_arg_value(tpl.get_arg("walkover")) in ("1", "2") or set(scores) == {"W", "L"}

        # Guess bestof (if enabled)
        bestof = None
        bestof_text_inserted = False
        if not is_walkover and self.options["match_maps_guess_bestof"]:
            try:
                num_scores = [int(score) for score in scores] if any(scores) else map_scores
            except:
                pass
            else:
                if num_scores[0] == num_scores[1]:
                    self.info += (
                        f"⚠️ {info_id_text} bestof cannot be guessed for score {'-'.join(str(n) for n in num_scores)}\n"
                    )
                else:
                    bestof = max(num_scores) * 2 - 1
                    if bestof != self.match_maps_prev_bestof:
                        texts.insert(0, f"|bestof={bestof}")
                        bestof_text_inserted = True
                        if self.match_maps_prev_bestof is not None:
                            self.info += (
                                f"⚠️ {info_id_text} Change of bestof from {self.match_maps_prev_bestof} to {bestof}\n"
                            )
                        self.match_maps_prev_bestof = bestof

        # If bestof is set, we do not copy the winner/bestof arguments
        ignore_list = []
        if bestof or is_walkover:
            ignore_list.append("winner")
        if bestof_text_inserted:
            ignore_list.append("bestof")
        for i in vodgames_processed:
            ignore_list.append(f"vodgame{i}")
        start_texts, mid_texts, end_texts = self.arguments_to_texts(MATCH_MAPS_ARGUMENTS, tpl, ignore_list)
        # Add "dateheader=true" after a "date=" argument
        for x_texts in (start_texts, mid_texts, end_texts):
            if (index := next((i for i, e in enumerate(x_texts) if e.startswith("|date=")), None)) is not None:
                x_texts.insert(index + 1, "|dateheader=true")
                break
        # Add vod from Match list start if there is one
        if self.match_list_vod:
            if (x := tpl.get_arg("vod")) and clean_arg_value(x):
                match_list_vod_arg = f"vodgame{max(vodgames_processed) + 1}"
            else:
                match_list_vod_arg = "vod"
            start_texts.append(f"|{match_list_vod_arg}={self.match_list_vod}")
            self.match_list_vod = None

        texts = start_texts + texts + mid_texts

        if map_texts and (has_a_non_empty_map or sum(map_scores) == 0):
            texts += map_texts

        texts += end_texts

        return "{{Match\n" + "\n".join(texts) + "\n}}"

    def convert_match_maps_team(self, tpl: wtp.Template) -> str | None:
        teams = ["", ""]
        texts: list[str] = []
        scores = ["", ""]

        info_id_text = f"[Matchlist {self.match_list_id}][M{len(self.match_texts) + 1}]"
        if tpl.comments:
            self.info += f"⚠️ {info_id_text} Comments will be lost\n"

        for i in range(1, 3):
            if x := tpl.get_arg(f"team{i}"):
                teams[i - 1] = clean_arg_value(x)
            if x := tpl.get_arg(f"score{i}"):
                scores[i - 1] = clean_arg_value(x)

        # Guess bestof (if enabled)
        bestof = None
        bestof_text_inserted = False
        if self.options["match_maps_guess_bestof"]:
            try:
                num_scores = [int(score) for score in scores]
            except:
                pass
            else:
                if num_scores[0] == num_scores[1]:
                    self.info += f"⚠️ {info_id_text} bestof cannot be guessed for score {'-'.join(scores)}\n"
                else:
                    bestof = max(num_scores) * 2 - 1
                    if bestof != self.match_maps_prev_bestof:
                        texts.insert(0, f"|bestof={bestof}")
                        bestof_text_inserted = True
                        if self.match_maps_prev_bestof is not None:
                            self.info += (
                                f"⚠️ {info_id_text} Change of bestof from {self.match_maps_prev_bestof} to {bestof}\n"
                            )
                        self.match_maps_prev_bestof = bestof

        ignore_list = []
        if bestof:
            ignore_list.append("winner")
        if bestof_text_inserted:
            ignore_list.append("bestof")
        start_texts, end_texts = self.arguments_to_texts(MATCH_MAPS_TEAM_ARGUMENTS, tpl, ignore_list)
        texts += start_texts

        if x := tpl.get_arg("details"):
            try:
                btm_tpl = next(t for t in x.templates if t.normal_name(capitalize=True) == "BracketTeamMatch")
            except StopIteration:
                print(f"No BracketTeamMatch in details for {teams[0]} vs {teams[1]}")
                for i in range(1, 3):
                    if teams[i - 1]:
                        text = f"|opponent{i}={{{{TeamOpponent|{teams[i - 1]}"
                        if scores[i - 1]:
                            text += f"|score={scores[i - 1]}"
                        text += "}}"
                        texts.append(text)
            else:
                *_, details_text = self.convert_team_match(btm_tpl, teams)
                texts.append(details_text)

        texts += end_texts

        return "{{Match\n" + "\n".join(texts) + "\n}}"

    def convert_bracket(self, tpl: wtp.Template) -> str | None:
        bracket_name = clean_arg_value(tpl.get_arg("1"))
        legacy_bracket_name = clean_arg_value(tpl.get_arg("2"))
        id_ = clean_arg_value(tpl.get_arg("id"))

        if not bracket_name or not legacy_bracket_name:
            self.info += f"⚠️ [Bracket {id_}] Empty argument 1 or 2\n"
            return None

        if legacy_bracket_name in BRACKET_NEW_NAMES and bracket_name != BRACKET_NEW_NAMES[legacy_bracket_name]:
            self.info += (
                f"⚠️ [Bracket {id_}] Mismatch between {bracket_name} and legacy bracket {legacy_bracket_name}\n"
            )

        if self.options["bracket_identify_by_arg_1"]:
            if bracket_name in BRACKET_LEGACY_NAMES:
                legacy_bracket_name = BRACKET_LEGACY_NAMES[bracket_name]
            else:
                self.info += f"⚠️ [Bracket {id_}] Bracket {bracket_name} unknown\n"
                return None

        if legacy_bracket_name not in BRACKETS:
            self.info += f'⚠️ [Bracket {id_}] Bracket "{legacy_bracket_name}" unknown\n'
            return None

        conversion = BRACKETS[legacy_bracket_name]
        bracket_texts = self.arguments_to_texts(BRACKET_ARGUMENTS, tpl)
        unknown_args = []
        for x in tpl.arguments:
            arg_name = x.name.strip()
            if m := LEGACY_ROUND_HEADER_PATTERN.match(arg_name):
                if legacy_bracket_name in ROUND_HEADERS and arg_name in ROUND_HEADERS[legacy_bracket_name]:
                    new_arg = ROUND_HEADERS[legacy_bracket_name][arg_name]
                    new_value = clean_arg_value(x).replace("'''", "")
                    if isinstance(new_arg, tuple):
                        bracket_texts += [f"|{new_arg_name}={new_value}" for new_arg_name in new_arg]
                    else:
                        bracket_texts.append(f"|{new_arg}={new_value}")
                else:
                    unknown_args.append(arg_name)
            elif (
                (m := LEGACY_PLAYER_PREFIX_PATTERN.match(arg_name))
                or (m := LEGACY_GAME_DETAILS_PATTERN.match(arg_name))
            ) and m.group(1) not in LEGACY_PLAYER_AND_GAME_PREFIXES[legacy_bracket_name]:
                unknown_args.append(arg_name)
        if unknown_args:
            self.info += f"⚠️ [Bracket {id_}] Argument(s) unknown ({len(unknown_args)}): {', '.join(unknown_args)}\n"
        # Used for start-of-round breaks
        prev_arguments = {x2.name.strip(): x1 for x1, x2 in zip(tpl.arguments, tpl.arguments[1:])}

        prev_round_number = ""
        prev_bestof = None
        for match_id, (*player_prefixes, game_prefix) in conversion.items():
            players = [MatchPlayer(), MatchPlayer()]
            match_texts0 = []
            match_texts1 = []
            scores = ["", ""]
            scores2 = ["", ""]
            scores3 = ["", ""]
            wins = ["", ""]

            round_number = BRACKET_MATCH_PATTERN.match(match_id).group(1)
            if round_number != prev_round_number:
                prev_bestof = None

            for i, (player, prefix) in enumerate(zip(players, player_prefixes), start=1):
                comments = ""
                if x := tpl.get_arg(prefix):
                    if x.comments:
                        comments = "".join(
                            comment.string
                            for comment in x.comments
                            if "\n" not in x.string[len(x.name) + 2 : x.comments[0].span[0] - x.span[0]]
                        )
                    player.name = clean_arg_value(x)
                if x := tpl.get_arg(f"{prefix}flag"):
                    player.flag = clean_arg_value(x)
                if x := tpl.get_arg(f"{prefix}race"):
                    player.race = clean_arg_value(x)
                if x := tpl.get_arg(f"{prefix}score"):
                    scores[i - 1] = clean_arg_value(x)
                if x := tpl.get_arg(f"{prefix}score2"):
                    scores2[i - 1] = clean_arg_value(x)
                if x := tpl.get_arg(f"{prefix}score3"):
                    scores3[i - 1] = clean_arg_value(x)
                if x := tpl.get_arg(f"{prefix}win"):
                    wins[i - 1] = clean_arg_value(x)
                if player.name:
                    text = f"|opponent{i}={{{{1Opponent|{player.name}"
                    if self.options["bracket_details"] == "remove_if_stored":
                        found, offrace = self.look_for_player(player)
                        if not found:
                            text += f"|flag={player.flag}|race={player.race}"
                        elif offrace:
                            text += f"|race={player.race}"
                    elif self.options["bracket_details"] == "keep":
                        if tpl.get_arg(f"{prefix}flag"):
                            text += f"|flag={player.flag}"
                        if tpl.get_arg(f"{prefix}race"):
                            text += f"|race={player.race}"
                    if scores[i - 1]:
                        if m := SCORE_ADVANTAGE_PATTERN.match(scores[i - 1]):
                            scores[i - 1] = m.group(1)
                            text += f"|score={scores[i - 1]}|advantage=1"
                        else:
                            text += f"|score={scores[i - 1]}"
                    if scores2[i - 1]:
                        text += f"|score2={scores2[i - 1]}"
                    if scores3[i - 1]:
                        text += f"|score3={scores3[i - 1]}"
                    text += "}}"
                    if comments:
                        self.info += f"⚠️ [Bracket {id_}][{match_id}] Comments moved to the end of the line\n"
                        text += f" {comments}"
                    match_texts1.append(text)

            # Removing matches where the score is Q, to mean qualification
            if scores[0] in ("Q", "", "-") and scores[1] == "Q" and bracket_name.endswith("Q"):
                continue

            bestof = None
            bestof_text_inserted = False
            if (
                self.options["bracket_guess_bestof"]
                and all(score == "" for score in scores2)
                and all(score == "" for score in scores3)
            ):
                try:
                    num_scores = [int(score) for score in scores]
                except:
                    pass
                else:
                    if num_scores[0] == num_scores[1]:
                        self.info += (
                            f"⚠️ [Bracket {id_}][{match_id}] bestof cannot be guessed for score {'-'.join(scores)}\n"
                        )
                    else:
                        bestof = max(num_scores) * 2 - 1
                        if bestof != prev_bestof:
                            match_texts0.append(f"|bestof={bestof}")
                            bestof_text_inserted = True
                            if prev_bestof is not None:
                                self.info += (
                                    f"⚠️ [Bracket {id_}][{match_id}] Change of bestof from {prev_bestof} to {bestof}\n"
                                )
                            prev_bestof = bestof

            if "W" not in scores:
                if wins[0] and not wins[1]:
                    if wins[0] != "1":
                        self.info += f"⚠️ In {id_}_{match_id}, {player_prefixes[0]}win={wins[0]}\n"
                    if players[1].name == "BYE":
                        match_texts1.append("|walkover=1")
                    elif bestof is None:
                        match_texts1.append("|winner=1")
                elif wins[1] and not wins[0]:
                    if wins[1] != "1":
                        self.info += f"⚠️ In {id_}_{match_id}, {player_prefixes[1]}win={wins[1]}\n"
                    if players[0].name == "BYE":
                        match_texts1.append("|walkover=2")
                    elif bestof is None:
                        match_texts1.append("|winner=2")
                else:
                    # Either no winner or two winners (!)
                    pass

            if self.options["bracket_override_with_match_summary"] and (ms_texts := self.find_match_summary(players)):
                match_texts1 = ms_texts
            elif (
                not self.options["bracket_do_not_convert_details"]
                and (x := tpl.get_arg(f"{game_prefix}details"))
                and x.templates
            ):
                summary_tpl = x.templates[0]
                for other_tpl in x.templates[1:]:
                    if other_tpl.span[0] > summary_tpl.span[1]:
                        self.info += f"⚠️ Multiple templates in {game_prefix}details\n"
                        break
                if summary_tpl.normal_name(capitalize=True) != "BracketMatchSummary":
                    self.info += f"⚠️ Template in {game_prefix}details is not BracketMatchSummary\n"
                summary_texts, summary_end_texts = self.arguments_to_texts(
                    BRACKET_MATCH_SUMMARY_ARGUMENTS, summary_tpl
                )

                if any("advantage" in s for s in summary_texts):
                    self.info += f"⚠️ Possible advantage in {game_prefix}\n"

                map_texts = []
                vodgames_moved_to_map = []
                i = 1
                while True:
                    x = summary_tpl.get_arg(f"map{i}")
                    x_win = summary_tpl.get_arg(f"map{i}win")
                    if x or x_win:
                        map_ = clean_arg_value(x)
                        if m := PIPE_PATTERN.match(map_):
                            map_, map_display_name = m.groups()
                        else:
                            map_display_name = ""
                        if map_ == "Unknown":
                            map_ = ""
                        x_vod = summary_tpl.get_arg(f"vodgame{i}")
                        map_text = f"|map{i}={{{{Map|map={map_}"
                        if map_display_name:
                            map_text += f"|mapDisplayName={map_display_name}"
                        winner = clean_arg_value(x_win)
                        map_text += f"|winner={winner}"
                        map_has_race = False
                        for j in (1, 2):
                            if x := summary_tpl.get_arg(f"map{i}p{j}race"):
                                map_has_race = True
                                map_text += f"|t{j}p1race={clean_arg_value(x)}"
                        if (map_ or winner or map_has_race) and (vod := clean_arg_value(x_vod)):
                            map_text += f"|vod={vod}"
                            vodgames_moved_to_map.append(i)
                        map_text += "}}"
                        map_texts.append(map_text)
                        i += 1
                    else:
                        break

                i = 1
                while True:
                    x = summary_tpl.get_arg(f"veto{i}")
                    x_player = summary_tpl.get_arg(f"vetoplayer{i}")
                    if x or x_player:
                        map_texts.append(
                            f"|veto{i}={clean_arg_value(x)} |vetoplayer{i}={clean_arg_value(x_player)}"
                        )
                        i += 1
                    else:
                        break

                match_texts1 += summary_texts
                match_texts1 += map_texts
                match_texts1 += summary_end_texts
                match_texts1 = [
                    text
                    for text in match_texts1
                    if not any(text.startswith(f"|vodgame{i}=") for i in vodgames_moved_to_map)
                ]

                if bestof := clean_arg_value(summary_tpl.get_arg("bestof")):
                    if bestof_text_inserted:
                        match_texts0 = [text for text in match_texts0 if not text.startswith("|bestof")]
                    match_texts0.insert(0, f"|bestof={bestof}")
                    try:
                        prev_bestof = int(bestof)
                    except:
                        self.info += f"⚠️ [Bracket {id_}][{match_id}] Existing bestof is not a decimal integer value\n"
            elif not self.options["bracket_do_not_move_match_summary"] and (
                ms_texts := self.find_match_summary(players)
            ):
                match_texts1 = ms_texts

            if match_texts1:
                # Add an empty line between rounds
                if round_number != prev_round_number:
                    for suffix in ("", "flag", "race"):
                        if (
                            (a := f"{player_prefixes[0]}{suffix}") in prev_arguments
                            and "\n" in (prev_arg := prev_arguments[a].value)
                            and (m := END_OF_PARAM_VALUE_PATTERN.search(prev_arg))
                        ):
                            bracket_texts.append(remove_start_and_end_newlines(m.group(0).rstrip("\t ")))
                            break
                    else:
                        if prev_round_number:
                            bracket_texts.append("")

                match_text = "{{Match"
                if match_texts0:
                    if not match_texts0[0].startswith("|bestof"):
                        match_text += "\n"
                    match_text += "\n".join(match_texts0)
                match_text += "\n" + "\n".join(match_texts1) + "\n}}"
                bracket_texts.append(f"|{match_id}={match_text}")

            prev_round_number = round_number

        if no_duplicate_check := bool((x := tpl.get_arg("noDuplicateCheck")) and clean_arg_value(x)):
            self.storage_to_enable = True
        if tpl.normal_name() == "LegacyBracketDisplay" or no_duplicate_check:
            template_name = "<includeonly>Display</includeonly>Bracket"
        else:
            template_name = "Bracket"

        result = f"{{{{{template_name}|{bracket_name}|id={id_}"
        if self.options["bracket_match_width"]:
            result += f"|matchWidth={self.options['bracket_match_width']}"
        elif x := tpl.get_arg("column-width"):
            result += f"|matchWidth={clean_arg_value(x)}"
        result += "\n" + "\n".join(bracket_texts) + "\n}}"
        return result

    def convert_team_bracket(self, tpl: wtp.Template, legacy_name: str) -> str | None:
        if legacy_name in BRACKETS:
            conversion = BRACKETS[legacy_name]
        else:
            return None

        if x := tpl.get_arg("1"):
            bracket_name = clean_arg_value(x)
        else:
            return None

        id_ = clean_arg_value(tpl.get_arg("id"))
        if bracket_name != BRACKET_NEW_NAMES[legacy_name]:
            self.info += f"⚠️ [Bracket {id_}] Mismatch between {bracket_name} and legacy bracket {legacy_name}\n"

        bracket_texts = self.arguments_to_texts(BRACKET_ARGUMENTS, tpl)

        last_match_id = next(reversed(conversion))
        prev_round_number = ""
        prev_bestof = None
        for match_id, (*team_prefixes, game_prefix) in conversion.items():
            teams = ["", ""]
            match_texts0: list[str] = []
            match_texts1: list[str] = []
            reset_match_texts: list[str] = []
            scores = ["", ""]
            scores2 = ["", ""]
            scores3 = ["", ""]
            wins = ["", ""]

            round_number = BRACKET_MATCH_PATTERN.match(match_id).group(1)
            if round_number != prev_round_number:
                prev_bestof = None

            for i, prefix in enumerate(team_prefixes, start=1):
                if (
                    (x := tpl.get_arg(f"{prefix}team"))
                    or (x := tpl.get_arg(f"{prefix}short"))
                    or (x := tpl.get_arg(f"{prefix}literal"))
                    or (x := tpl.get_arg(prefix))
                ):
                    teams[i - 1] = clean_arg_value(x).replace("'''", "")
                    teams[i - 1] = TEAM_BRACKET_TEMPLATE_SC2.sub("", teams[i - 1])
                    teams[i - 1] = TEAM_BRACKET_TEMPLATE.sub("\\1", teams[i - 1])
                    if teams[i - 1].lower() in self.team_aliases:
                        teams[i - 1] = self.team_aliases[teams[i - 1].lower()]
                if x := tpl.get_arg(f"{prefix}score"):
                    scores[i - 1] = clean_arg_value(x)
                if x := tpl.get_arg(f"{prefix}score2"):
                    scores2[i - 1] = clean_arg_value(x)
                if x := tpl.get_arg(f"{prefix}score3"):
                    scores3[i - 1] = clean_arg_value(x)
                if x := tpl.get_arg(f"{prefix}win"):
                    wins[i - 1] = clean_arg_value(x)

            bestof = None
            if (
                self.options["bracket_guess_bestof"]
                and all(score == "" for score in scores2)
                and all(score == "" for score in scores3)
            ):
                try:
                    num_scores = [int(score) for score in scores]
                except:
                    pass
                else:
                    bestof = max(num_scores) * 2 - 1
                    if bestof != prev_bestof:
                        match_texts0.append(f"|bestof={bestof}")
                        if prev_bestof is not None:
                            self.info += (
                                f"⚠️ [Bracket {id_}][{match_id}] Change of bestof from {prev_bestof} to {bestof}\n"
                            )
                        prev_bestof = bestof

            if wins[0] and not wins[1]:
                if teams[1] == "BYE":
                    match_texts1.append("|walkover=1")
                elif bestof is None:
                    match_texts1.append("|winner=1")
            elif wins[1] and not wins[0]:
                if teams[0] == "BYE":
                    match_texts1.append("|walkover=2")
                elif bestof is None:
                    match_texts1.append("|winner=2")
            else:
                # Either no winner or two winners (!)
                pass

            score_texts = ["", ""]
            for i in range(0, 2):
                if scores[i]:
                    score_texts[i] += f"|score={scores[i]}"
                if scores2[i]:
                    score_texts[i] += f"|score2={scores2[i]}"
                if scores3[i - 1]:
                    score_texts[i] += f"|score3={scores3[i]}"

            if self.options["bracket_override_with_team_match"] and (tm_text := self.find_team_match(teams)):
                match_texts1 = [tm_text]
                if match_id == last_match_id and (tm_text := self.find_team_match(teams)):
                    reset_match_texts = [tm_text]
            elif (
                not self.options["bracket_do_not_convert_details"]
                and (x := tpl.get_arg(f"{game_prefix}details"))
                and x.templates
            ):
                team_match_subtemplates = [
                    t for t in x.templates if t.normal_name(capitalize=True) in ("BracketTeamMatch", "TeamMatch")
                ]
                if not team_match_subtemplates:
                    print(f"No BracketTeamMatch in details for {teams[0]} vs {teams[1]}")
                    for i in range(1, 3):
                        if teams[i - 1]:
                            if teams[i - 1].lower() == "bye":
                                text = f"|opponent{i}={{{{LiteralOpponent|BYE"
                            else:
                                text = f"|opponent{i}={{{{TeamOpponent|{teams[i - 1]}"
                            if score_texts[i - 1]:
                                text += score_texts[i - 1]
                            text += "}}"
                            match_texts1.append(text)
                else:

                    def _add_scores(m):
                        opponent_index = int(m.group(1)) - 1
                        return f"{m.group(0)[:-2]}{score_texts[opponent_index]}{m.group(0)[-2:]}"

                    # Convert the first TeamMatch
                    _, has_set_map, _, details_text = self.convert_team_match(team_match_subtemplates[0], teams)
                    # Is there more?
                    if match_id == last_match_id and len(team_match_subtemplates) == 2:
                        # Bracket reset in the finals
                        *_, reset_details_text = self.convert_team_match(team_match_subtemplates[1], teams)
                        reset_match_texts.append(reset_details_text)
                    elif len(team_match_subtemplates) > 1:
                        # Multiple TeamMatches
                        def _helper(details_text: str, match_number: int, map_offset: int, keep_opponent_lines: bool):
                            new_lines = []
                            first_map_seen = False
                            for line in details_text.split("\n"):
                                if m := MAP_PATTERN.match(line):
                                    # map_number = int(m.group(1)) + map_offset
                                    map_number = map_offset + 1
                                    if not first_map_seen:
                                        new_lines.append(f"|subgroup{map_number}header=Match {match_number}")
                                        first_map_seen = True
                                    new_lines.append(
                                        MAP_PATTERN.sub(f"|map{map_number}={{{{Map|subgroup={map_number}", line)
                                    )
                                    map_offset += 1
                                elif keep_opponent_lines or not line.startswith("|opponent"):
                                    new_lines.append(line)
                            return "\n".join(new_lines), map_offset

                        details_text, map_offset = _helper(details_text, 1, 0, True)
                        for match_number, subtpl in enumerate(team_match_subtemplates[1:], start=2):
                            *_, additional_details_text = self.convert_team_match(subtpl, teams)
                            additional_details_text, map_offset = _helper(
                                additional_details_text, match_number, map_offset, False
                            )
                            details_text += "\n" + additional_details_text

                        details_text = OPPONENT_PATTERN.sub(_add_scores, details_text)
                    elif not has_set_map:
                        details_text = OPPONENT_PATTERN.sub(_add_scores, details_text)

                    match_texts1.append(details_text)
            elif not self.options["bracket_do_not_move_team_match"] and (tm_text := self.find_team_match(teams)):
                match_texts1 = [tm_text]
                if match_id == last_match_id and (tm_text := self.find_team_match(teams)):
                    reset_match_texts = [tm_text]
            else:
                for i in range(1, 3):
                    if teams[i - 1]:
                        if teams[i - 1].lower() == "bye":
                            text = f"|opponent{i}={{{{LiteralOpponent|BYE"
                        else:
                            text = f"|opponent{i}={{{{TeamOpponent|{teams[i - 1]}"
                        if score_texts[i - 1]:
                            text += score_texts[i - 1]
                        text += "}}"
                        match_texts1.append(text)

            if match_texts1:
                match_text = "{{Match\n"
                if match_texts0:
                    match_text += "\n".join(match_texts0) + "\n"
                match_text += "\n".join(match_texts1) + "\n}}"
                bracket_texts.append(f"|{match_id}={match_text}")
            if reset_match_texts:
                reset_match_text = "{{Match\n" + "\n".join(reset_match_texts) + "\n}}"
                bracket_texts.append(f"|RxMBR={reset_match_text}")

            prev_round_number = round_number

        result = f"{{{{Bracket|{bracket_name}|id={id_}"
        if self.options["bracket_match_width"]:
            result += f"|matchWidth={self.options['bracket_match_width']}"
        elif x := tpl.get_arg("column-width"):
            result += f"|matchWidth={clean_arg_value(x)}"
        result += "\n" + "\n".join(bracket_texts) + "\n}}"
        return result

    def look_for_player(self, player: MatchPlayer) -> tuple[bool, bool]:
        # found, is_offrace
        flag = player.flag.lower()
        flag = COUNTRIES.get(flag, flag)
        race = player.race.lower()
        race = RACES.get(race, race)

        if player.name in self.participants:
            participant = self.participants[player.name]

            p_flag = participant.flag.lower()
            p_flag = COUNTRIES.get(p_flag, p_flag)
            if flag and (flag != p_flag):
                return False, False

            p_race = participant.race.lower()
            p_race = RACES.get(p_race, p_race)
            is_offrace = race and (race != p_race)
            return True, is_offrace

        return False, False

    def find_match_summary(self, players: list[MatchPlayer]):
        for i, ms_entry in enumerate(self.match_summaries):
            if (
                not (ms_entry.moved or ms_entry.grouped)
                and (ms_entry.has_set_map or not self.options["bracket_do_not_move_no_map_match_summary"])
                and all(player.name == ms_player.name for player, ms_player in zip(players, ms_entry.players))
            ):
                self.match_summaries[i].moved = True
                return ms_entry.texts

    def find_team_match(self, teams: list[str]):
        for i, tm_entry in enumerate(self.team_matches):
            if (
                not (tm_entry.moved or tm_entry.grouped)
                and (tm_entry.has_set_map or not self.options["bracket_do_not_move_no_map_team_match"])
                and all(team.lower() == tm_team.lower() for team, tm_team in zip(teams, tm_entry.teams))
            ):
                self.team_matches[i].moved = True
                return tm_entry.text

    def arguments_to_texts(
        self,
        wrapped_arguments: tuple[int, dict[str, str | int | None]],
        tpl: wtp.Template,
        ignore_list: list[str] | None = None,
        append_empty_strings: bool = False,
    ) -> list[str] | list[list[str]]:
        part_count, arguments = wrapped_arguments
        ignore_list = ignore_list or []
        texts = [[] for _ in range(part_count)]
        part = 0

        for x in tpl.arguments:
            found = False
            arg_name = x.name.strip()
            for from_arg, to_arg in arguments.items():
                if re.match(rf"^{from_arg}$", arg_name):
                    if isinstance(to_arg, int):
                        part = to_arg
                    elif arg_name not in ignore_list and to_arg is not None:
                        value = clean_arg_value(x)
                        if value or append_empty_strings:
                            texts[part].append(f"|{re.sub(from_arg, to_arg, arg_name)}={value}")
                    found = True
                    break
            if not found:
                self.not_converted_arguments.add((tpl.normal_name(), x.name))

        if part_count > 1:
            return texts
        return texts[0]

    def convert_external_cup_list(self, tpl: wtp.Template) -> str | None:
        cup_list = ExternalCupList()
        cup_list.local_currency = clean_arg_value(tpl.get_arg("localcurrency"))
        cup_list.prefix = clean_arg_value(tpl.get_arg("prefix"))
        i = 1
        while x := tpl.get_arg(str(i)):
            row_tpl = x.templates[0]
            if row_tpl.normal_name(capitalize=True) == "ExternalCupList/Row":
                row = ExternalCupListRow()
                row.number = clean_arg_value(row_tpl.get_arg("number"))
                row.date = clean_arg_value(row_tpl.get_arg("date"))
                for field in ("winner", "runnerup"):
                    if x := row_tpl.get_arg(field):
                        opp_tpl = x.templates[0]
                        if opp_tpl.normal_name() == "1Opponent":
                            if x := opp_tpl.get_arg("localprize"):
                                setattr(row, f"{field}_prize", LocalPrize(clean_arg_value(x)))
                            if x := opp_tpl.get_arg("prize"):
                                setattr(row, f"{field}_prize", UsdPrize(clean_arg_value(x)))
                cup_list.rows.append(row)
            i += 1

        if not cup_list.rows:
            return None

        new_text = "{{Box|start|padding=2em|padding-bottom=1em}}\n"
        pp_texts = []
        id_count = len(self.single_match_ids)
        for i, row in enumerate(cup_list.rows):
            mid = self.single_match_ids[i] if i < id_count else ""
            pp_text = f"{{{{SoloPrizePool"
            if cup_list.local_currency:
                pp_text += f"|localcurrency={cup_list.local_currency}"
            pp_text += f"|id={mid}" + "\n"
            for field in ("winner", "runnerup"):
                if prize := getattr(row, f"{field}_prize"):
                    pp_text += f"|{{{{Slot|{prize.FIELD_NAME}={prize.value}}}}}" + "\n"
            pp_text += "}}\n"
            pp_texts.append(pp_text)
        new_text += "{{Box|break|padding=2em|padding-bottom=1em}}\n".join(pp_texts)
        new_text += "{{Box|end}}"

        return new_text

    def add_participant_from_player_template(self, tpl: wtp.Template) -> None:
        p = Participant()
        if x := tpl.get_arg("1"):
            p.name = clean_arg_value(x)
        if not p.name:
            del p
            return
        if x := tpl.get_arg("link"):
            p.link = clean_arg_value(x)
            if p.link in ("false", "true"):
                p.link = ""

        default_p = self.participants.get(p.name, None)
        if x := tpl.get_arg("flag"):
            p.flag = clean_arg_value(x)
        if not p.flag and default_p:
            p.flag = default_p.flag
        if x := tpl.get_arg("race"):
            p.race = clean_arg_value(x)
        if not p.race and default_p:
            p.race = default_p.race
        self.participants[p.name] = p

    def add_participants_from_participant_table(self, tpl: wtp.Template) -> list[Participant]:
        participants: list[Participant] = []
        try:
            i = min(
                int(m.group(1))
                for x in tpl.arguments
                if (m := PARTICIPANT_TABLE_PARTICIPANT_PATTERN.match(x.name.strip()))
            )
        except ValueError:
            i = 1
        while (x := tpl.get_arg(str(i))) or (x := tpl.get_arg(f"p{i}")):
            p = Participant(name=clean_arg_value(x))
            if not p.name:
                del p
                i += 1
                continue
            if x := tpl.get_arg(f"p{i}link"):
                p.link = clean_arg_value(x)
                if p.link in ("false", "true"):
                    p.link = ""
            if x := tpl.get_arg(f"p{i}flag"):
                p.flag = clean_arg_value(x)
            if x := tpl.get_arg(f"p{i}race"):
                p.race = clean_arg_value(x)
            self.participants[p.name] = p
            participants.append(p)
            i += 1
        return participants

    def convert_very_old_team_matches(self):
        teams: list[str] = []
        subgroup = 0
        maps: list[str] = []
        gameset_players = [set(), set()]
        players: list[dict[str, MatchPlayer]] = [{}, {}]
        scores = [0, 0]
        subgroup_scores = [0, 0]

        match_texts: list[str] = []

        for tpl in self.parsed.templates:
            name = tpl.normal_name(capitalize=True)
            if name in ("Team", "TeamShort", "Team2", "Team2Short"):
                if len(teams) == 2:
                    # Update score after last subgroup
                    if subgroup_scores[0] > subgroup_scores[1]:
                        scores[0] += 1
                    elif subgroup_scores[1] > subgroup_scores[0]:
                        scores[1] += 1

                    match_text = "{{Match\n"
                    for i, team_players in enumerate(players):
                        match_text += f"|opponent{i + 1}={{{{TeamOpponent|{teams[i]}|players={{{{Players"
                        for j, player in enumerate(team_players.values(), start=1):
                            match_text += f"|p{j}={player.name}"
                            if player.link:
                                match_text += f"|p{j}link={player.link}"
                            match_text += f"|p{j}flag={player.flag}|p{j}race={player.race}"
                        match_text += f"}}}}|score={scores[i]}}}}}\n"
                    if scores[0] > scores[1]:
                        winner = "1"
                    elif scores[1] > scores[0]:
                        winner = "2"
                    else:
                        winner = ""
                    match_text += f"|winner={winner}" + "\n"
                    match_text += "\n".join(f"|map{i}={map_text}" for i, map_text in enumerate(maps, start=1))
                    match_text += "\n}}"
                    match_texts.append(match_text)

                    # reset
                    teams = []
                    subgroup = 0
                    maps = []
                    players = [{}, {}]
                    scores = [0, 0]
                    subgroup_scores = [0, 0]
                teams.append(clean_arg_value(tpl.get_arg("1")))

            elif name == "GameSet":
                opponents = [tpl.get_arg("1"), tpl.get_arg("2")]

                prev_gameset_players = deepcopy(gameset_players)
                gameset_players = [set(), set()]

                map_texts = []
                for i, opp in enumerate(opponents):
                    j = 1
                    for opp_tpl in opp.templates:
                        opp_tpl_name = opp_tpl.normal_name(capitalize=True)
                        if opp_tpl_name == "Player":
                            player = MatchPlayer()
                            if x := opp_tpl.get_arg("1"):
                                player.name = clean_arg_value(x)
                            if x := opp_tpl.get_arg("link"):
                                player.link = clean_arg_value(x)
                                if player.link in ("false", "true"):
                                    player.link = ""
                            if x := opp_tpl.get_arg("flag"):
                                player.flag = clean_arg_value(x)
                            if x := opp_tpl.get_arg("race"):
                                player.race = clean_arg_value(x)
                            if player.name:
                                offrace = player.name in players[i] and player.race != players[i][player.name].race
                                if player.name not in players[i]:
                                    players[i][player.name] = player
                                gameset_players[i].add(player.name)
                                text = f"|t{i + 1}p{j}={player.name}"
                                if offrace:
                                    text += f"|t{i + 1}p{j}race={player.race}"
                                map_texts.append(text)
                            j += 1

                if gameset_players != prev_gameset_players:
                    subgroup += 1
                    if subgroup_scores[0] > subgroup_scores[1]:
                        scores[0] += 1
                    elif subgroup_scores[1] > subgroup_scores[0]:
                        scores[1] += 1
                    subgroup_scores = [0, 0]

                if x := tpl.get_arg("map"):
                    map_texts.append(f"|map={clean_arg_value(x)}")
                skip = False
                if x := tpl.get_arg("skip"):
                    if clean_arg_value(x):
                        skip = True
                        map_texts.append("|winner=skip")
                if not skip and (x := tpl.get_arg("win")):
                    winner = clean_arg_value(x)
                    map_texts.append(f"|winner={winner}")
                    if winner in ("1", "2"):
                        subgroup_scores[int(winner) - 1] += 1

                map_text = f"{{{{Map|subgroup={subgroup}" + "".join(map_texts) + "}}"
                maps.append(map_text)

        if len(teams) == 2:
            # Update score after last subgroup
            if subgroup_scores[0] > subgroup_scores[1]:
                scores[0] += 1
            elif subgroup_scores[1] > subgroup_scores[0]:
                scores[1] += 1

            match_text = "{{Match\n"
            for i, team_players in enumerate(players):
                match_text += f"|opponent{i + 1}={{{{TeamOpponent|{teams[i]}|players={{{{Players"
                for j, player in enumerate(team_players.values(), start=1):
                    match_text += f"|p{j}={player.name}"
                    if player.link:
                        match_text += f"|p{j}link={player.link}"
                    match_text += f"|p{j}flag={player.flag}|p{j}race={player.race}"
                match_text += f"}}}}|score={scores[i]}}}}}\n"
            if scores[0] > scores[1]:
                winner = "1"
            elif scores[1] > scores[0]:
                winner = "2"
            else:
                winner = ""
            match_text += f"|winner={winner}" + "\n"
            match_text += "\n".join(f"|map{i}={map_text}" for i, map_text in enumerate(maps, start=1))
            match_text += "\n}}"
            match_texts.append(match_text)

        # Replace text
        # Assuming the text to replace is between the start of the first table and the end of the last table
        mid = generate_id()
        new_text = f"{{{{Matchlist|id={mid}" + "\n"
        new_text += "\n\n".join(f"|M{i}={match_text}" for i, match_text in enumerate(match_texts, start=1))
        new_text += "\n}}"
        start, end = self.parsed.tables[0].span[0], self.parsed.tables[-1].span[1]
        return f"{self.text[:start]}{new_text}{self.text[end:]}"

    def convert_very_old_player_matches_v1(self):
        players: list[MatchPlayer] = []
        maps: list[str] = []
        scores = [0, 0]

        match_texts: list[str] = []

        for tbl in self.parsed.tables:
            # reset
            players = []
            maps = []
            scores = [0, 0]

            for tpl in tbl.templates:
                name = tpl.normal_name(capitalize=True)

                if name in ("Player", "Playersp") and not isinstance(tpl.parent(), wtp.Template):
                    player = MatchPlayer()
                    if x := tpl.get_arg("1"):
                        player.name = clean_arg_value(x)
                        if player.name.startswith("[[") and player.name.endswith("]]"):
                            player.name = player.name.removeprefix("[[").removesuffix("]]")
                    if x := tpl.get_arg("link"):
                        player.link = clean_arg_value(x)
                        if player.link in ("false", "true"):
                            player.link = ""
                    if x := tpl.get_arg("flag"):
                        player.flag = clean_arg_value(x)
                    if x := tpl.get_arg("race"):
                        player.race = clean_arg_value(x)
                    if player.name:
                        players.append(player)

                elif name == "GameSet":
                    gameset_opponents = [tpl.get_arg("1"), tpl.get_arg("2")]

                    map_texts = []
                    for i, opp in enumerate(gameset_opponents):
                        j = 1
                        for opp_tpl in opp.templates:
                            opp_tpl_name = opp_tpl.normal_name(capitalize=True)
                            if opp_tpl_name == "Player":
                                player = MatchPlayer()
                                if x := opp_tpl.get_arg("1"):
                                    player.name = clean_arg_value(x)
                                if x := opp_tpl.get_arg("race"):
                                    player.race = clean_arg_value(x)
                                if player.name:
                                    if i < len(players):
                                        if player.name != players[i].name:
                                            print(f"Warning: player is {player.name}, expected was {players[i].name}")
                                        offrace = player.race != players[i].race
                                    else:
                                        offrace = False
                                    if offrace:
                                        text = f"|race{i + 1}={player.race}"
                                        map_texts.append(text)
                                j += 1

                    if x := tpl.get_arg("map"):
                        map_texts.append(f"|map={clean_arg_value(x)}")
                    skip = False
                    if x := tpl.get_arg("skip"):
                        if clean_arg_value(x):
                            skip = True
                            map_texts.append("|winner=skip")
                    if not skip and (x := tpl.get_arg("win")):
                        winner = clean_arg_value(x)
                        map_texts.append(f"|winner={winner}")
                        if winner in ("1", "2"):
                            scores[int(winner) - 1] += 1

                    map_text = "{{Map" + "".join(map_texts) + "}}"
                    maps.append(map_text)

            # end
            if len(players) != 2:
                print("Error: Number of players is {len(players)}, not 2")
                continue

            comment = ""
            last_line_of_last_cell = str(tbl.cells()[-1][-1]).split("\n")[-1]
            if not last_line_of_last_cell.startswith("#"):
                comment = last_line_of_last_cell

            match_text = "{{Match\n"
            for i, player in enumerate(players):
                match_text += f"|opponent{i + 1}={{{{1Opponent|{player.name}"
                if player.link:
                    match_text += f"|link={player.link}"
                match_text += f"|flag={player.flag}|race={player.race}"
                match_text += f"|score={scores[i]}}}}}\n"
            if scores[0] > scores[1]:
                winner = "1"
            elif scores[1] > scores[0]:
                winner = "2"
            else:
                winner = ""
            match_text += f"|winner={winner}" + "\n"
            match_text += "\n".join(f"|map{i}={map_text}" for i, map_text in enumerate(maps, start=1)) + "\n"
            if comment:
                match_text += f"|comment={comment}" + "\n"
            match_text += "}}"
            match_texts.append((tbl.span, match_text))

        # Replace text
        sections = get_sections(self.text)
        italics = get_italics(self.text)
        try:
            section = next(
                section for section in sections if section.title == self.options["group_matches_of_section"]
            )
        except StopIteration:
            print(f"Section {self.options['group_matches_of_section']} not found")
            # Assuming the text to replace is between the start of the first table and the end of the last table
            mid = generate_id()
            new_text = f"{{{{Matchlist|id={mid}" + "\n"
            new_text += "\n\n".join(
                f"|M{i}={match_text_entry[1]}" for i, match_text_entry in enumerate(match_texts, start=1)
            )
            new_text += "\n}}"
            if len(self.parsed.tables) > 0:
                start, end = self.parsed.tables[0].span[0], self.parsed.tables[-1].span[1]
                return f"{self.text[:start]}{new_text}{self.text[end:]}"
            return "<!-- No table detected -->"
        else:
            start, end = section.contents_span
            stuff = sorted(
                (
                    *((child.title_span, child) for child in section.children),
                    *((it.span, it) for it in italics),
                    *(
                        match_text_entry
                        for match_text_entry in match_texts
                        if start <= match_text_entry[0][0] and match_text_entry[0][1] <= end
                    ),
                )
            )

            new_text = ""
            date = ""
            i = 1
            section_text = ""
            for item in stuff:
                if isinstance(item[1], mwtp_Section):
                    if new_text and section_text:
                        # Close the matchlist
                        section_text += "}}\n"
                        new_text += section_text
                    new_text += "\n" + f"{'=' * item[1].level}{item[1].title}{'=' * item[1].level}" + "\n"
                    mid = generate_id()
                    section_text = f"{{{{Matchlist|id={mid}|collapsed=false" + "\n"
                    date = ""
                    i = 1
                elif isinstance(item[1], Italic):
                    if DATE_PATTERN.search(item[1].text):
                        date = item[1].text
                elif isinstance(item[1], str):
                    section_text += "\n" + f"|M{i}={item[1]}" + "\n"
                    i += 1
            if section_text:
                section_text += "}}\n"
                new_text += section_text
            return f"{self.text[:start]}{new_text}{self.text[end:]}"

    def convert_very_old_player_matches_v2(self):
        changes = []
        for tbl in self.parsed.tables:
            maps: list[str] = []
            prev_gameset_players = []
            gameset_players = []
            scores = [0, 0]

            match_texts: list[str] = []

            for tpl in tbl.templates:
                name = tpl.normal_name(capitalize=True)
                if name == "GameSet":
                    opponents = [tpl.get_arg("1"), tpl.get_arg("2")]
                    map_texts = []

                    gameset_players = []
                    for i, opp in enumerate(opponents):
                        for opp_tpl in opp.templates:
                            opp_tpl_name = opp_tpl.normal_name(capitalize=True)
                            if opp_tpl_name in ("Player", "Playersp"):
                                player = MatchPlayer()
                                if x := opp_tpl.get_arg("1"):
                                    player.name = clean_arg_value(x)
                                if x := opp_tpl.get_arg("link"):
                                    player.link = clean_arg_value(x)
                                    if player.link in ("false", "true"):
                                        player.link = ""
                                if x := opp_tpl.get_arg("flag"):
                                    player.flag = clean_arg_value(x)
                                if x := opp_tpl.get_arg("race"):
                                    player.race = clean_arg_value(x)
                                if player.name:
                                    gameset_players.append(player)

                    if prev_gameset_players:
                        if all(
                            p.name == prev_p.name and p.link == prev_p.link
                            for p, prev_p in zip(gameset_players, prev_gameset_players)
                        ):
                            for i, (p, prev_p) in enumerate(zip(gameset_players, prev_gameset_players)):
                                if p.race != prev_p.race:
                                    map_texts.append(f"|race{i + 1}={p.race}")
                        else:
                            match_text = "{{Match\n"
                            for i, player in enumerate(prev_gameset_players):
                                match_text += f"|opponent{i + 1}={{{{1Opponent|{player.name}"
                                if player.link:
                                    match_text += f"|link={player.link}"
                                match_text += f"|flag={player.flag}|race={player.race}"
                                match_text += f"|score={scores[i]}}}}}\n"
                            if scores[0] > scores[1]:
                                winner = "1"
                            elif scores[1] > scores[0]:
                                winner = "2"
                            else:
                                winner = ""
                            match_text += f"|winner={winner}" + "\n"
                            match_text += "\n".join(f"|map{i}={map_text}" for i, map_text in enumerate(maps, start=1))
                            match_text += "\n}}"
                            match_texts.append(match_text)

                            prev_gameset_players = deepcopy(gameset_players)
                            maps = []
                            scores = [0, 0]
                    else:
                        prev_gameset_players = deepcopy(gameset_players)

                    if x := tpl.get_arg("map"):
                        map_texts.append(f"|map={clean_arg_value(x)}")
                    skip = False
                    if x := tpl.get_arg("skip"):
                        if clean_arg_value(x):
                            skip = True
                            map_texts.append("|winner=skip")
                    if not skip and (x := tpl.get_arg("win")):
                        winner = clean_arg_value(x)
                        map_texts.append(f"|winner={winner}")
                        if winner in ("1", "2"):
                            scores[int(winner) - 1] += 1

                    map_text = "{{Map" + "".join(map_texts) + "}}"
                    maps.append(map_text)

            # Close the last match
            if prev_gameset_players:
                match_text = "{{Match\n"
                for i, player in enumerate(prev_gameset_players):
                    match_text += f"|opponent{i + 1}={{{{1Opponent|{player.name}"
                    if player.link:
                        match_text += f"|link={player.link}"
                    match_text += f"|flag={player.flag}|race={player.race}"
                    match_text += f"|score={scores[i]}}}}}\n"
                if scores[0] > scores[1]:
                    winner = "1"
                elif scores[1] > scores[0]:
                    winner = "2"
                else:
                    winner = ""
                match_text += f"|winner={winner}" + "\n"
                match_text += "\n".join(f"|map{i}={map_text}" for i, map_text in enumerate(maps, start=1))
                match_text += "\n}}"
                match_texts.append(match_text)

            # Add change to list
            mid = generate_id()
            new_text = f"{{{{Matchlist|id={mid}" + "\n"
            new_text += "\n\n".join(f"|M{i}={match_text}" for i, match_text in enumerate(match_texts, start=1))
            new_text += "\n}}"
            changes.append((*tbl.span, new_text))

        # Sort changes
        changes = sorted(changes, reverse=True)

        print("Before")
        print("\n".join(f"({change[:-1]})" for change in changes))

        # Clean changes: remove changes with nested changes
        new_changes = []
        for i, (start, end, new_text) in enumerate(changes):
            for other_start, other_end, _ in changes[:i]:
                if start < other_start and other_end < end:
                    # Found a nested change
                    break
            else:
                new_changes.append((start, end, new_text))
        changes = new_changes

        print("After")
        print("\n".join(f"({change[:-1]})" for change in changes))

        # Apply changes
        converted = self.text
        for start, end, new_text in changes:
            converted = f"{converted[:start]}{new_text}{converted[end:]}"

        return converted


def clean_arg_value(arg) -> str:
    value = arg.value if arg else ""
    value = WIKITEXT_COMMENT_PATTERN.sub("", value)
    value = value.strip()
    return value


def clean_arguments(tpl: wtp.Template) -> dict[str, str]:
    return {x.name.strip(): clean_arg_value(x) for x in tpl.arguments}


def generate_id(length=10, chars=string.ascii_letters + string.digits) -> str:
    return "".join(random.SystemRandom().choice(chars) for _ in range(length))


def find_players(parsed: wtp.WikiText) -> list[MatchPlayer]:
    players: list[MatchPlayer] = []
    for tpl in parsed.templates:
        tpl_name = tpl.normal_name(capitalize=True)
        if tpl_name in ("Player", "Player2", "Playersp"):
            player = MatchPlayer()
            if x := tpl.get_arg("1"):
                player.name = clean_arg_value(x)
            if x := tpl.get_arg("link"):
                player.link = clean_arg_value(x)
                if player.link in ("false", "true"):
                    player.link = ""
            if x := tpl.get_arg("flag"):
                player.flag = clean_arg_value(x)
            if x := tpl.get_arg("race"):
                player.race = clean_arg_value(x)
            players.append(player)
    return players


def remove_start_and_end_newlines(text: str) -> str:
    if text.startswith("\r\n"):
        text = text.removeprefix("\r\n")
    elif text.startswith("\n"):
        text = text.removeprefix("\n")
    if text.endswith("\r\n"):
        text = text.removesuffix("\r\n")
    elif text.endswith("\n"):
        text = text.removesuffix("\n")
    return text


def convert_page(wiki: str, title: str, options: dict[str, Any]) -> tuple[str, str, str]:
    title = title.replace("_", " ")

    cache_folder = Path(__file__).parent.parent / "cache" / wiki
    makedirs(cache_folder, exist_ok=True)
    cache_title = re.sub(r"[\\/\?\"]", "_", title)
    p = cache_folder / cache_title

    info_cache = ""
    if not options["ignore_cache"] and p.exists() and p.is_file():
        info_cache += f"Getting cached content ({datetime.fromtimestamp(os.path.getmtime(p)).isoformat()})"
        text: str | None = p.read_text(encoding="utf-8")
    else:
        info_cache += "Getting content from the API"
        text = get_liquipedia_page_content(wiki, title)
        if text:
            p.write_text(text, encoding="utf-8")

    if text:
        converted, info = Converter(text, title, options).convert()
        return converted, info_cache + "\n" + info, text

    return "", f"Error while getting {title} from wiki {wiki}", ""


def convert_wikitext(text: str, title: str, options: dict[str, Any]) -> tuple[str, str]:
    if text:
        return Converter(text, title, options).convert()

    return "", f"Error: no wikitext"


def get_liquipedia_page_content(wiki: str, title: str) -> str | None:
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
    }

    response = requests.get(API_URLS[wiki], headers=HEADERS, params=params)
    data = response.json()

    page_data = data["query"]["pages"]
    page_id = list(page_data.keys())[0]

    if page_id == "-1":
        print("Page not found")
        return None

    revision_data = page_data[page_id]["revisions"][0]
    content = revision_data["*"]

    return content


if __name__ == "__main__":
    wiki = "starcraft2"
    title = "The Foreign Hope"
    text = convert_page(wiki, title, {})
    if text:
        print(text)
