from dataclasses import dataclass

import wikitextparser as wtp


@dataclass
class Join:
    new_name: str
    changes: tuple[dict[str, str], dict[str, str]]


JOINS = {
    "Bracket/32": {
        "Bracket/16L8DSL4DSL2DSL1D": Join(
            new_name="Bracket/32U16L8DSL4DSL2DSL1D",
            changes=(
                {
                    **{f"R3M{x}": f"R4M{x}" for x in range(1, 5)},
                    **{f"R4M{x}": f"R6M{x}" for x in range(1, 3)},
                    "R5M1": "R8M1",
                },
                {
                    **{f"R1M{x}": f"R1M{x + 16}" for x in range(1, 9)},
                    **{f"R2M{x}": f"R2M{x + 8}" for x in range(1, 9)},
                    **{f"R4M{x}": f"R4M{x + 4}" for x in range(1, 5)},
                    **{f"R6M{x}": f"R6M{x + 2}" for x in range(1, 3)},
                    "R8M1": "R8M2",
                },
            ),
        )
    }
}


def bracket_join(original: str) -> str:
    parsed = wtp.parse(original)

    upper_tpl: wtp.Template | None = None
    upper_tpl_name: str = ""

    for tpl in parsed.templates:
        name = tpl.normal_name(capitalize=True)
        if name == "Bracket" and (x := tpl.get_arg("1")):
            bracket_tpl_name = x.value.strip()
            if bracket_tpl_name in JOINS:
                upper_tpl = tpl
                upper_tpl_name = bracket_tpl_name
            elif upper_tpl and bracket_tpl_name in JOINS[upper_tpl_name]:
                join = JOINS[upper_tpl_name][bracket_tpl_name]
                upper_tpl.set_arg("1", join.new_name)
                upper_changes, lower_changes = join.changes
                for arg_from, arg_to in upper_changes.items():
                    if x := upper_tpl.get_arg(arg_from):
                        x.name = arg_to
                for arg in tpl.arguments:
                    if arg.name in lower_changes:
                        upper_tpl.set_arg(lower_changes[arg.name], arg.value)
                    elif not upper_tpl.has_arg(arg.name):
                        upper_tpl.set_arg(arg.name, arg.value)

    converted = str(parsed)

    return converted
