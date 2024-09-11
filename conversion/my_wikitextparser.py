from dataclasses import dataclass, field
import re


@dataclass
class Section:
    level: int
    title: str
    title_span: tuple[int, int]
    contents_span: tuple[int, int] = (-1, -1)
    children: list["Section"] = field(default_factory=list)


@dataclass
class Italic:
    text: str
    span: tuple[int, int]


SECTION_TITLE_PATTERN = re.compile(r"^(={1,6})(.+)\1", re.MULTILINE)
ITALIC_PATTERN = re.compile(r"(?<!')''(.+?)''")


def get_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    for m in SECTION_TITLE_PATTERN.finditer(text):
        section = Section(len(m.group(1)), m.group(2), m.span())
        parent_section = None
        for previous_section in reversed(sections):
            if previous_section.contents_span[0] == -1 and previous_section.level >= section.level:
                previous_section.contents_span = (previous_section.title_span[1] + 1, section.title_span[0] - 1)
            elif parent_section is None and previous_section.level == section.level - 1:
                parent_section = previous_section
                parent_section.children.append(section)
        sections.append(section)

    for section in sections:
        if section.contents_span[0] == -1:
            section.contents_span = (section.title_span[1] + 1, len(text))

    return sections


def get_italics(text: str) -> list[Italic]:
    return [Italic(m.group(1), m.span()) for m in ITALIC_PATTERN.finditer(text)]


def test_sections():
    s = """
abc

=title==

==subtitle 1==

text of 1

==subtitle 2==

test

=second title=

after

==this==
like this ''date 1''

===is===

====an====
or like this ''date 2''

=====exemple=====
fin # or is it?

====going====
no # it's not

===back===
well

==to==
ok ''ok''

=one=
then ''this is the end''
''of''
''the text''

"""
    LOOKING_FOR = "second title"

    sections = get_sections(s)
    italics = get_italics(s)

    try:
        section = next(section for section in sections if section.title == LOOKING_FOR)
    except StopIteration:
        print("Not found")
        pass
    else:
        start, end = section.contents_span
        stuff = sorted(
            (
                *((child.title_span, child) for child in section.children),
                *((it.span, it) for it in italics if start <= it.span[0] and it.span[1] <= end),
            )
        )
        i = 1
        for item in stuff:
            if isinstance(item[1], Section):
                print(f"(header of {i})", item[1].title)
            elif isinstance(item[1], Italic):
                print(i, item[1].text)
                i += 1


if __name__ == "__main__":
    test_sections()
