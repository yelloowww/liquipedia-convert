from dataclasses import dataclass
from typing import Callable

import wikitextparser as wtp


@dataclass
class Join:
    new_name: str
    original_template_changes: dict[str, str]
    other_template_changes: dict[int | tuple[int, ...], dict[str, Callable]]
    reorder: tuple[str] | None = None


JOINS = {
    ("Bracket/32", "Bracket/16L8DSL4DSL2DSL1D"): Join(
        new_name="Bracket/32U16L8DSL4DSL2DSL1D",
        original_template_changes={
            **{f"R3M{x}": f"R4M{x}" for x in range(1, 5)},
            **{f"R4M{x}": f"R6M{x}" for x in range(1, 3)},
            "R5M1": "R8M1",
        },
        other_template_changes={
            1: {
                **{f"R1M{x}": f"R1M{x + 16}" for x in range(1, 9)},
                **{f"R2M{x}": f"R2M{x + 8}" for x in range(1, 9)},
                **{f"R4M{x}": f"R4M{x + 4}" for x in range(1, 5)},
                **{f"R6M{x}": f"R6M{x + 2}" for x in range(1, 3)},
                "R8M1": "R8M2",
            },
        },
    ),
    ("Bracket/16-2Q", "Bracket/16-2Q", "Bracket/16-2Q", "Bracket/16-2Q", "Bracket/8"): Join(
        new_name="Bracket/64",
        original_template_changes={
            "qualifiedHeader": None,
        },
        other_template_changes={
            **{
                i: {
                    **{f"R1M{x}": f"R1M{x + i * 8}" for x in range(1, 9)},
                    **{f"R2M{x}": f"R2M{x + i * 4}" for x in range(1, 5)},
                    **{f"R3M{x}": f"R3M{x + i * 2}" for x in range(1, 3)},
                }
                for i in range(1, 4)
            },
            4: {
                "R1M1header": "R4M1header",
                "R2M1header": "R5M1header",
                "R3M1header": "R6M1header",
                **{f"R1M{x}": f"R4M{x}" for x in range(1, 5)},
                **{f"R2M{x}": f"R5M{x}" for x in range(1, 3)},
                "R3M1": "R6M1",
            },
        },
        reorder=(
            *(f"R{r}M1header" for r in range(1, 7)),
            *(f"R{r}M{x}" for r in range(1, 7) for x in range(1, 2 ** (6 - r) + 1)),
        ),
    ),
    ("Bracket/16-2Q", "Bracket/16-2Q", "Bracket/16-2Q", "Bracket/16-2Q"): Join(
        new_name="Bracket/64",
        original_template_changes={
            "qualifiedHeader": None,
        },
        other_template_changes={
            **{
                i: {
                    **{f"R1M{x}": f"R1M{x + i * 8}" for x in range(1, 9)},
                    **{f"R2M{x}": f"R2M{x + i * 4}" for x in range(1, 5)},
                    **{f"R3M{x}": f"R3M{x + i * 2}" for x in range(1, 3)},
                }
                for i in range(1, 4)
            }
        },
        reorder=(
            *(f"R{r}M1header" for r in range(1, 7)),
            *(f"R{r}M{x}" for r in range(1, 4) for x in range(1, 2 ** (6 - r) + 1)),
        ),
    ),
}


def bracket_join(original: str) -> str:
    parsed = wtp.parse(original)

    brackets = [tpl for tpl in parsed.templates if tpl.normal_name(capitalize=True) == "Bracket" and tpl.get_arg("1")]
    while len(brackets) > 1:
        bracket_names = [tpl.get_arg("1").value.strip() for tpl in brackets]
        for names, join in JOINS.items():
            if tuple(bracket_names[: len(names)]) == names:
                apply_join(join, brackets[: len(names)])
                brackets = brackets[len(names) :]
                break
        else:
            brackets = brackets[1:]

    converted = str(parsed)

    return converted


def apply_join(join: Join, brackets: list[wtp.Template]) -> None:
    brackets[0].set_arg("1", join.new_name)

    for arg_from, arg_to in join.original_template_changes.items():
        if x := brackets[0].get_arg(arg_from):
            if arg_to is None:
                brackets[0].del_arg(arg_from)
            else:
                x.name = arg_to

    for i, bracket in enumerate(brackets[1:], start=1):
        if changes := join.other_template_changes.get(i):
            for arg in bracket.arguments:
                if arg.name in changes:
                    arg_to = changes[arg.name]
                    if isinstance(arg_to, Callable):
                        arg_to = arg_to(i)
                    brackets[0].set_arg(arg_to, arg.value)
                elif not brackets[0].has_arg(arg.name):
                    brackets[0].set_arg(arg.name, arg.value)

    if join.reorder:
        for arg in join.reorder:
            if x := brackets[0].get_arg(arg):
                val = x.value
                brackets[0].del_arg(arg)
                brackets[0].set_arg(arg, val)
