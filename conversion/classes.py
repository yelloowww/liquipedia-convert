from dataclasses import dataclass, field


@dataclass
class Participant:
    name: str = ""
    link: str = ""
    flag: str = ""
    race: str = ""
    team: str = ""
    dq: bool = False
    notes: list[str] = field(default_factory=list)
    comments: str = ""


@dataclass
class Section:
    title: str
    participants: list[Participant] = field(default_factory=list)


@dataclass
class MatchPlayer:
    name: str = ""
    link: str = ""
    flag: str = ""
    race: str = ""


@dataclass
class PrizePoolPlayer:
    name: str = ""
    link: str = ""
    flag: str = ""
    race: str = ""
    team: str = ""
    lastscore: str = ""
    lastvs: str = ""
    lastvslink: str = ""
    lastvsflag: str = ""
    lastvsrace: str = ""
    lastvsscore: str = ""
    wdl: str = ""
    woto: str = ""
    wofrom: str = ""
    date: str = ""


@dataclass
class PlayerSearchResult:
    found: bool = False
    offrace: bool = False


@dataclass
class MatchSummaryEntry:
    span: tuple[int]
    has_set_map: bool
    players: tuple[str]
    texts: list[str]
    moved: bool = False
    grouped: bool = False


@dataclass
class TeamMatchEntry:
    span: tuple[int]
    has_set_map: bool
    teams: tuple[str]
    text: str
    moved: bool = False
    grouped: bool = False


@dataclass
class Prize:
    value: str = ""


class UsdPrize(Prize):
    FIELD_NAME = "usdprize"


class LocalPrize(Prize):
    FIELD_NAME = "localprize"


@dataclass
class ExternalCupListRow:
    number: str = ""
    date: str = ""
    winner_prize: Prize | None = None
    runnerup_prize: Prize | None = None


@dataclass
class ExternalCupList:
    local_currency: str = ""
    prefix: str = ""
    rows: list[ExternalCupListRow] = field(default_factory=list)


@dataclass
class Match:
    bestof: int | None = None
    bestof_is_set: bool = False
    header: str | None = None
    texts: list[str] = field(default_factory=list)

    def header_string(self):
        return self.header + "\n" if self.header is not None else ""

    def string(self):
        s = "{{Match"
        if self.bestof_is_set:
            s += f"|bestof={self.bestof}"
        s += "\n" + "\n".join(self.texts)
        s += "\n}}"
        return s


@dataclass
class BestofMove:
    destination: str
    source: str | None = None
