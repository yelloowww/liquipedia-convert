import re
from typing import Any

import wikitextparser as wtp


FILE_PATTERN = re.compile(r"\[\[File:([^\|\]]+)(?:\|(x?\d+px))?.*?\]\]")
NAVBOXCHILDNAME_PATTERN = re.compile(r"(\{\{NavBoxChild[^\n]*)\n(\|name=)")
BULLET_PATTERN = re.compile(r"\{\{ *(?:[tT]emplate:)?• *\}\}")
WIKITEXT_COMMENT_PATTERN = re.compile(r"<!--((?!-->).)*-->", re.DOTALL)
FLATLIST_TEMPLATE_PATTERN = re.compile(r"\{\{ *(?:[tT]emplate:)?(?:[eE]nd)?[fF]latlist *\}\}")
SERIES_ROW_START_PATTERN = re.compile(r"(\{\{ *(?:[tT]emplate:)?(?:[sS]eriesNavBoxRow) *)")


class NavboxConverter:
    def __init__(self, text: str, title: str, options: dict[str, Any]) -> None:
        self.text = text
        self.title = title
        self.options = options

    def convert(self) -> tuple[str, str, str]:
        self.info: str = ""
        self.summary: str = ""
        self.counter: int = 0
        self.max_depth: int = 0

        parsed = wtp.parse(self.text)

        changes: list[tuple[int, int, str]] = []
        skip_before = 0
        start = -1
        for tpl in parsed.templates:
            name = tpl.normal_name(capitalize=True)
            if name not in ("Navbox", "Navbox/old"):
                continue

            start, end = tpl.span
            if start < skip_before:
                continue
            skip_before = end

            self.max_depth = 0
            new_text = self.navbox_text(tpl, 0)
            if self.max_depth == 1:
                new_text = "\n".join(line.removeprefix("\t") for line in new_text.split("\n"))
                new_text = NAVBOXCHILDNAME_PATTERN.sub(r"\1\2", new_text)
            changes.append((start, end, new_text))

            self.counter += 1

        # Apply changes
        converted = self.text
        for start, end, new_text in sorted(changes, reverse=True):
            converted = f"{converted[:start]}{new_text}{converted[end:]}"

        if self.counter:
            self.summary = f"Convert navbox ({self.counter}x)"
        else:
            self.summary = ""

        return converted, self.info, self.summary

    def navbox_text(self, tpl: wtp.Template, depth: int = 0, child_name: str = "") -> str:
        title = ""
        if x := tpl.get_arg("title"):
            title = clean_arg_value(x)

        image = ""
        image_size = ""
        if (x := tpl.get_arg("image")) and (m := FILE_PATTERN.fullmatch(clean_arg_value(x))):
            image = m[1]
            if m[2]:
                image_size = m[2]

        children = []

        if (x := tpl.get_arg("above")) and (val := clean_arg_value(x)):
            children.append(self.navbox_child_with_items_text("", [val], depth + 1, centered=True))

        self.append_children(tpl, children, depth, lambda i: f"group{i}", lambda i: f"list{i}")
        self.append_children(tpl, children, depth, lambda i: f"col{i}header", lambda i: f"col{i}")

        if (x := tpl.get_arg("below")) and (val := clean_arg_value(x)):
            children.append(self.navbox_child_with_items_text("", [val], depth + 1, centered=True))

        text = "{{NavBox"
        if depth > 0:
            text += "Child"
        elif self.title:
            if self.title.startswith("Template:"):
                text += f'\n|template={self.title.removeprefix("Template:")}'
            else:
                self.info += f'<div class="warning">⚠️ Page is not in the Template namespace</div>'
        if child_name:
            text += f"\n|name={child_name}"
        if title:
            text += f"\n|title={title}"
        if image:
            text += f"\n|image={image}"
        if image_size:
            text += f"\n|imagesize={image_size}"

        for i, child in enumerate(children, start=1):
            if depth == 0:
                text += "\n"
            text += f"\n|child{i}={ident(child)}"

        text += "\n}}"

        self.max_depth = max(depth, self.max_depth)

        return text

    def append_children(self, tpl, children, depth, title_fn, contents_fn):
        for i in range(0, 100):
            title = None
            x_title = tpl.get_arg(title_fn(i))
            x_contents = tpl.get_arg(contents_fn(i))
            if not x_title and not x_contents:
                continue
            if x_title:
                title = clean_arg_value(x_title)
            if x_contents:
                appended = False
                if x_contents.templates:
                    subtpl_names = tuple(subtpl.normal_name(capitalize=True) for subtpl in x_contents.templates)
                    if subtpl_names[0] == "Flatlist":
                        if "SeriesNavBoxRow" in subtpl_names:
                            subtpl = x_contents.templates[subtpl_names.index("SeriesNavBoxRow")]
                            child = SERIES_ROW_START_PATTERN.sub(rf"\1|newVersion=true|name={title}", str(subtpl))
                            children.append(child)
                        else:
                            lists = x_contents.get_lists()
                            if lists:
                                items = [s for item in lists[0].items if (s := item.strip())]
                                if not items and (sublists := lists[0].sublists()):
                                    items = sublists[0].items
                            else:
                                items = [FLATLIST_TEMPLATE_PATTERN.sub("", clean_arg_value(x_contents)).strip()]
                            children.append(self.navbox_child_with_items_text(title, items, depth + 1))
                        appended = True
                    elif subtpl_names[0] in ("Navbox", "Navbox/old", "Navbox subgroup"):
                        children.append(self.navbox_text(x_contents.templates[0], depth + 1, title))
                        appended = True
                    elif all(subtpl_name == "•" for subtpl_name in subtpl_names):
                        items = [item.strip() for item in BULLET_PATTERN.split(x_contents.value)]
                        children.append(self.navbox_child_with_items_text(title, items, depth + 1))
                        appended = True
                if not appended and (val := clean_arg_value(x_contents)) != "":
                    children.append(self.navbox_child_with_items_text(title, [val], depth + 1))
            i += 1

    def navbox_child_with_items_text(
        self, child_name: str, items: list[str], depth: int = 0, centered: bool = False
    ) -> str:
        items = [s for item in items if (s := item.strip())]

        text = "{{NavBoxChild"
        if not items:
            text += "|allowEmpty=1"
        if centered:
            text += "|center=1"
        if child_name:
            text += f"\n|name={child_name}"

        needs_named_args = any("=" in item for item in items)
        for i, item in enumerate(items, start=1):
            text += "\n|"
            if needs_named_args:
                text += f"{i}="
            text += item.strip()

        text += "\n}}"

        self.max_depth = max(depth, self.max_depth)

        return text


def ident(text: str) -> str:
    *first, last = text.split("\n")
    if first:
        return "\n\t".join(first) + "\n" + last
    return last


def clean_arg_value(arg) -> str:
    value = arg.value if arg else ""
    value = WIKITEXT_COMMENT_PATTERN.sub("", value)
    value = value.strip()
    return value