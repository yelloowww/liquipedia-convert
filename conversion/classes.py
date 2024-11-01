from dataclasses import dataclass, field
from functools import cached_property

from conversion.countries import COUNTRIES
from conversion.races import RACES


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

    @cached_property
    def clean_flag(self):
        flag = self.flag.lower()
        return COUNTRIES.get(flag, flag)

    @cached_property
    def clean_race(self):
        race = self.race.lower()
        return RACES.get(race, race)


@dataclass(slots=True)
class Section:
    title: str
    participants: list[Participant] = field(default_factory=list)


@dataclass(slots=True)
class MatchPlayer:
    name: str = ""
    link: str = ""
    flag: str = ""
    race: str = ""


@dataclass(slots=True)
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


@dataclass(slots=True)
class PlayerSearchResult:
    found: bool = False
    offrace: bool = False


@dataclass(slots=True)
class MatchSummaryEntry:
    span: tuple[int]
    has_set_map: bool
    players: tuple[str]
    texts: list[str]
    moved: bool = False
    grouped: bool = False


@dataclass(slots=True)
class TeamMatchEntry:
    span: tuple[int]
    has_set_map: bool
    teams: tuple[str]
    text: str
    moved: bool = False
    grouped: bool = False


@dataclass(slots=True)
class Prize:
    value: str = ""


class UsdPrize(Prize):
    FIELD_NAME = "usdprize"


class LocalPrize(Prize):
    FIELD_NAME = "localprize"


@dataclass(slots=True)
class ExternalCupListRow:
    number: str = ""
    date: str = ""
    winner_prize: Prize | None = None
    runnerup_prize: Prize | None = None


@dataclass(slots=True)
class ExternalCupList:
    local_currency: str = ""
    prefix: str = ""
    rows: list[ExternalCupListRow] = field(default_factory=list)


@dataclass(slots=True)
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


@dataclass(slots=True)
class BestofMove:
    destination: str
    source: str | None = None
