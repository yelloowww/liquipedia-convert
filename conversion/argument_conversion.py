PRIZE_POOL_START_ARGUMENTS = [
    {
        "localcurrency": "localcurrency",
        "points": "points",
        "cutafter": "cutafter",
        "\\d+": None,
    }
]
PRIZE_POOL_SLOT_ARGUMENTS = [
    {
        "place": "place",
        "usdprize": "usdprize",
        "localprize": "localprize1",
        "points": "points",
        "(?:flag|race|link)?\\d+": None,
        "team\\d+": None,
        "lastvs(?:flag|race|link|score)?\\d+": None,
        "lastscore\\d+": None,
        "woto\\d+": None,
        "wofrom\\d+": None,
        "wdl\\d+": None,
        "date": None,
        "date\\d+": None,
    }
]
PRIZE_POOL_SLOT_TEAM_ARGUMENTS = [
    {
        "place": "place",
        "usdprize": "usdprize",
        "localprize": "localprize1",
        "points": "points",
        "lastvs\\d+": None,
        "lastvsscore\\d+": None,
        "lastscore\\d+": None,
    }
]
MATCH_SUMMARY_ARGUMENTS = [
    {
        "bestof": "bestof",
        "date": "date",
        "twitch": "twitch",
        "lrthread": "lrthread",
        "preview": "preview",
        "interview": "interview",
        "recap": "recap",
        "stream": "stream",
        "comment": "comment",
        "(?:flag|race|link|map|win)?\\d+": None,
        "vetoes": None,
        "veto\\d+": None,
        "width": None,
    },
    {
        "vod": "vod",
        "vodgame(\\d+)": "vodgame\\1",
    },
]
MATCH_LIST_ARGUMENTS = [
    {
        "id": "id",
        "1": "title",
        "title": "title",
        "hide": "collapsed",
        "width": "width",
        "vod": None,
    }
]
MATCH_MAPS_ARGUMENTS = [
    {
        "date": "date",
        "finished": "finished",
        "winner": "winner",
        "walkover": "walkover",
        "twitch": "twitch",
        "stream": "stream",
        "lrthread": "lrthread",
        "preview": "preview",
        "interview": "interview",
        "recap": "recap",
        "review": "review",
        "comment": "comment",
        "player[12](?:flag|race)?": None,
        "p[12]score": None,
        "map\\d+(?:win)?": None,
        "map\\d+p[12]race": None,
        "bestof": ("bestof", lambda m, ignore_bestof, vodgames_processed: not ignore_bestof),
    },
    {
        "vod": "vod",
        "vodgame(\\d+)": (
            "vodgame\\1",
            lambda m, ignore_bestof, vodgames_processed: int(m.group(1)) not in vodgames_processed,
        ),
    },
]
MATCH_MAPS_TEAM_ARGUMENTS = [
    {
        "date": "date",
        "finished": "finished",
        "winner": "winner",
        "walkover": "walkover",
        "twitch": "twitch",
        "stream": "stream",
        "lrthread": "lrthread",
        "preview": "preview",
        "interview": "interview",
        "recap": "recap",
        "review": "review",
        "comment": "comment",
        "(?:team|score)[12]": None,
    },
    {
        "vod": "vod",
    },
]
BRACKET_ARGUMENTS = [
    {
        "hideroundtitles": "hideRoundTitles",
        "column-width": None,
        "[RL](\\d+)": None,
        "[12]": None,
        "R\\d+[DW]\\d+(?:flag|race|win|score[23]?|team|short|literal)?": None,
        "R\\d+G\\d+details": None,
        "id|type": None,
    }
]
BRACKET_MATCH_SUMMARY_ARGUMENTS = [
    {
        "date": "date",
        "finished": "finished",
        "winner": "winner",
        "twitch(\\d+)?": "twitch\\1",
        "afreeca": "afreeca",
        "afreecatv": "afreecatv",
        "dailymotion": "dailymotion",
        "douyu": "douyu",
        "youtube": "youtube",
        "lrthread": "lrthread",
        "preview": "preview",
        "interview": "interview",
        "recap": "recap",
        "review": "review",
        "stream": "stream",
        "comment": "comment",
        "map\\d+(?:win)?": None,
        "map\\d+p[12]race": None,
        "veto(player)?(\\d+)": None,
        "bestof": None,
    },
    {
        "vod": "vod",
        "vodgame(\\d+)": None,
    },
]
TEAM_MATCH_ARGUMENTS = [
    {
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
        "team[12](?:short|literal)?": None,
        "teamwin": None,
        "map\\d+(?:win)?": None,
        "(m\\d+|ace\\d?|2v2)p[12](?:flag|race|link)?": None,
        "(m\\d+|ace\\d?)t[12]p\\d+(?:flag|race|link)?": None,
        "(m\\d+|ace\\d?)(?:map|win|walkover)": None,
        "2v2": None,
        "vod(\\d+)": None,
        "vodgame(\\d+)": None,
        "m(\\d+)vod": None,
        "width": None,
    },
    {
        "vod": "vod",
    },
]
