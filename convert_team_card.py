from dataclasses import dataclass

import wikitextparser as wtp


@dataclass
class TeamCardPlayer:
    name: str = ""
    link: str = ""
    flag: str = ""
    race: str = ""
    team: str = ""


def convert_team_card(original: str) -> str:
    parsed = wtp.parse(original)

    changes: list[tuple[int, int, str]] = []

    # 0: header
    # 1: players
    state = 0
    start = -1
    for tbl in parsed.tables:
        start_row = 0

        if state == 0:
            cell0 = tbl.cells(row=0, column=0)
            team_name = ""
            if cell0.templates:
                for tpl in cell0.templates:
                    name = tpl.normal_name(capitalize=True)
                    if name in ("Team", "TeamPart") and (x := tpl.get_arg("1")):
                        team_name = x.value.strip()
                        break
            if not team_name:
                team_name = cell0.value.strip()
            start = tbl.span[0]
            state = 1
            start_row = 1

        if state == 1:
            players = []
            cells = tbl.cells(span=False)[start_row:]
            for row, col, c in (
                (row, col, c) for row, row_cells in enumerate(cells) for col, c in enumerate(row_cells)
            ):
                player = TeamCardPlayer()
                for tpl in c.templates:
                    name = tpl.normal_name(capitalize=True)
                    if name in ("Player", "Playersp", "InlinePlayer"):
                        if x := tpl.get_arg("1"):
                            player.name = x.value.strip()
                        if x := tpl.get_arg("link"):
                            player.link = x.value.strip()
                        if x := tpl.get_arg("flag"):
                            player.flag = x.value.strip()
                        if x := tpl.get_arg("race"):
                            player.race = x.value.strip()
                    elif name in ("TeamPart", "TeamShort"):
                        if x := tpl.get_arg("1"):
                            player.team = x.value.strip()
                if player.name:
                    players.append(player)
                else:
                    del player
            new_text = "{{TeamCard\n"
            new_text += f"|team={team_name}" + "\n"
            for i, player in enumerate(players, start=1):
                if player.name:
                    new_text += f"|{player.name}"
                if player.link:
                    new_text += f"|p{i}link={player.link}"
                if player.flag:
                    new_text += f"|p{i}flag={player.flag}"
                if player.race:
                    new_text += f"|p{i}race={player.race}"
                if player.team:
                    new_text += f"|p{i}team={player.team}"
                new_text += "\n"
            new_text += "}}"
            changes.append((start, tbl.span[1], new_text))
            state = 0

    # Apply changes
    converted = original
    for start, end, new_text in sorted(changes, reverse=True):
        converted = f"{converted[:start]}{new_text}{converted[end:]}"

    return converted
