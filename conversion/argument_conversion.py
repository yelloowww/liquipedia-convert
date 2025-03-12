from itertools import takewhile


def _wrap_arguments(args: dict[str, str | int | None]) -> tuple[str, dict[str, str | int | None]]:
    try:
        part_count = 1 + max(takewhile(lambda x: isinstance(x, int), args.values()))
    except ValueError:
        part_count = 1
    return (part_count, args)


PRIZE_POOL_START_ARGUMENTS = _wrap_arguments(
    {
        # Cutoff arguments
        "localcurrency": 1,
        "(\\d*)points": 1,
        # Other arguments
        "cutafter": "cutafter",
        "tier": "tier",
        "tiertype": "tiertype",
        "series": "series",
        "tournament(\\d*)": "tournament\\1",
        "tournament name": "tournament name",
        "matchGroupId(\\d*)": "matchGroupId\\1",
        "storeLpdb": "storeLpdb",
        "storeTournament": "storeTournament",
        "lpdb_prefix": "lpdb_prefix",
        "importLimit": None,
        "award": None,
        "\\d+": None,
    }
)
PRIZE_POOL_SLOT_ARGUMENTS = _wrap_arguments(
    {
        # Cutoff arguments
        "localprize": 1,
        "(\\d*)points": 1,
        # Other arguments
        "place": "place",
        "count": "count",
        "usdprize": "usdprize",
        "award": "award",
        "date": "date",
        "(?:flag|race|link)?\\d+(?:p[12])?": None,
        "team\\d+(?:p[12])?": None,
        "lastvs(?:flag|race|link|score)?\\d+(?:p[12])?": None,
        "lastvs\\d+(?:flag|race|link|score)?": None,
        "lastscore\\d+": None,
        "woto\\d+": None,
        "wofrom\\d+": None,
        "wdl\\d+": None,
        "date\\d+": None,
        "usdprize\\d+": None,
        "localprize\\d+": None,
    }
)
MATCH_SUMMARY_ARGUMENTS = _wrap_arguments(
    {
        # Cutoff arguments
        "(?:flag|race|link|map|win)?\\d+": 1,
        "vetoes": 1,
        "veto\\d+": 1,
        # Other arguments
        "bestof": "bestof",
        "date": "date",
        "twitch": "twitch",
        "lrthread": "lrthread",
        "preview": "preview",
        "interview": "interview",
        "recap": "recap",
        "stream": "stream",
        "comment": "comment",
        "width": None,
        "vod": "vod",
        "vodgame(\\d+)": "vodgame\\1",
    }
)
MATCH_LIST_ARGUMENTS = _wrap_arguments(
    {
        "id": "id",
        "1": "title",
        "title": "title",
        "hide": "collapsed",
        "width": "width",
        "vod": None,
    }
)
MATCH_MAPS_ARGUMENTS = _wrap_arguments(
    {
        # Cutoff arguments
        "player[12](?:flag|race)?": 1,
        "p[12]score": 1,
        "map\\d+(?:win)?": 2,
        "map\\d+p[12]race": 2,
        "veto(player)?(\\d+)": 2,
        # Other arguments
        "date": "date",
        "finished": "finished",
        "winner": "winner",
        "walkover": "walkover",
        "twitch(\\d*)": "twitch\\1",
        "afreeca": "afreeca",
        "douyu": "douyu",
        "stream": "stream",
        "trovo": "trovo",
        "lrthread": "lrthread",
        "preview": "preview",
        "interview": "interview",
        "recap": "recap",
        "review": "review",
        "comment": "comment",
        "bestof": "bestof",
        "vod": "vod",
        "vodgame(\\d+)": "vodgame\\1",
    }
)
MATCH_MAPS_TEAM_ARGUMENTS = _wrap_arguments(
    {
        # Cutoff arguments
        "(?:team|score)[12]": 1,
        # Other arguments
        "date": "date",
        "finished": "finished",
        "winner": "winner",
        "walkover": "walkover",
        "twitch(\\d*)": "twitch\\1",
        "afreeca": "afreeca",
        "douyu": "douyu",
        "stream": "stream",
        "trovo": "trovo",
        "lrthread": "lrthread",
        "preview": "preview",
        "interview": "interview",
        "recap": "recap",
        "review": "review",
        "comment": "comment",
        "bestof": "bestof",
        "vod": "vod",
    }
)
BRACKET_ARGUMENTS = _wrap_arguments(
    {
        "hideroundtitles": "hideRoundTitles",
        "noDuplicateCheck": "noDuplicateCheck",
        "column-width": None,
        "(?:[RL](\\d+)|Q)": None,
        "[12]": None,
        "R\\d+[DW]\\d+(?:flag|race|win|score[23]?|team|short|literal)?": None,
        "R\\d+G\\d+details": None,
        "id|type": None,
    }
)
BRACKET_MATCH_SUMMARY_ARGUMENTS = _wrap_arguments(
    {
        # Cutoff arguments
        "map\\d+(?:win)?": 1,
        "map\\d+p[12]race": 1,
        "veto(player)?(\\d+)": 1,
        "win(\\d+)": 1,
        # Other arguments
        "bestof": None,
        "date": "date",
        "finished": "finished",
        "winner": "winner",
        "twitch(\\d*)": "twitch\\1",
        "afreeca": "afreeca",
        "afreecatv": "afreecatv",
        "dailymotion": "dailymotion",
        "douyu": "douyu",
        "trovo": "trovo",
        "youtube": "youtube",
        "lrthread": "lrthread",
        "preview(\\d*)": "preview\\1",
        "interview(\\d*)": "interview\\1",
        "recap": "recap",
        "replay": "replay",
        "review": "review",
        "stream": "stream",
        "comment": "comment",
        "vod": "vod",
        "vodgame(\\d+)": "vodgame\\1",
    }
)
TEAM_MATCH_ARGUMENTS = _wrap_arguments(
    {
        # Cutoff arguments
        "team[12](?:short|literal)?": 1,
        "teamwin": 1,
        "map\\d+(?:win)?": 1,
        "(m\\d+|ace\\d?|2v2)p[12](?:flag|race|link|score)?": 1,
        "(m\\d+|ace\\d?)t[12]p\\d+(?:flag|race|link)?": 1,
        "(m\\d+|ace\\d?)(?:map|win|walkover)": 1,
        "2v2": 1,
        "vod(\\d+)": 1,
        "vodgame(\\d+)": 1,
        "m(\\d+)vod": 1,
        # Other arguments
        **{
            x: x
            for x in (
                "bestof",
                "date",
                "stream",
                "twitch",
                "twitch2",
                "trovo",
                "afreeca",
                "afreecatv",
                "dailymotion",
                "douyu",
                "smashcast",
                "youtube",
                "walkover",
                "finished",
                "preview",
                "review",
                "lrthread",
                "vod",
                "interview",
                "recap",
                "comment",
            )
        },
        "width": None,
        "vod": "vod",
    }
)
