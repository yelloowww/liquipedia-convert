# If there are cutoff arguments, they should be at the start of the dict, with value "True".
PRIZE_POOL_START_ARGUMENTS = {
    "localcurrency": "localcurrency",
    "points": "points",
    "cutafter": "cutafter",
    "\\d+": None,
}
PRIZE_POOL_SLOT_ARGUMENTS = {
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
PRIZE_POOL_SLOT_TEAM_ARGUMENTS = {
    "place": "place",
    "usdprize": "usdprize",
    "localprize": "localprize1",
    "points": "points",
    "lastvs\\d+": None,
    "lastvsscore\\d+": None,
    "lastscore\\d+": None,
}
MATCH_SUMMARY_ARGUMENTS = {
    # Cutoff arguments
    "(?:flag|race|link|map|win)?\\d+": True,
    "vetoes": True,
    "veto\\d+": True,
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
MATCH_LIST_ARGUMENTS = {
    "id": "id",
    "1": "title",
    "title": "title",
    "hide": "collapsed",
    "width": "width",
    "vod": None,
}
MATCH_MAPS_ARGUMENTS = {
    # Cutoff arguments
    "player[12](?:flag|race)?": True,
    "p[12]score": True,
    "map\\d+(?:win)?": True,
    "map\\d+p[12]race": True,
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
    "bestof": ("bestof", lambda m, ignore_bestof, vodgames_processed: not ignore_bestof),
    "vod": "vod",
    "vodgame(\\d+)": (
        "vodgame\\1",
        lambda m, ignore_bestof, vodgames_processed: int(m.group(1)) not in vodgames_processed,
    ),
}
MATCH_MAPS_TEAM_ARGUMENTS = {
    # Cutoff arguments
    "(?:team|score)[12]": True,
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
    "bestof": ("bestof", lambda m, ignore_bestof: not ignore_bestof),
    "vod": "vod",
}
BRACKET_ARGUMENTS = {
    "hideroundtitles": "hideRoundTitles",
    "column-width": None,
    "(?:[RL](\\d+)|Q)": None,
    "[12]": None,
    "R\\d+[DW]\\d+(?:flag|race|win|score[23]?|team|short|literal)?": None,
    "R\\d+G\\d+details": None,
    "id|type": None,
}
BRACKET_MATCH_SUMMARY_ARGUMENTS = {
    # Cutoff arguments
    "map\\d+(?:win)?": True,
    "map\\d+p[12]race": True,
    "veto(player)?(\\d+)": True,
    "vodgame(\\d+)": True,
    "bestof": None,
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
    "vod": "vod",
}
TEAM_MATCH_ARGUMENTS = {
    # Cutoff arguments
    "team[12](?:short|literal)?": True,
    "teamwin": True,
    "map\\d+(?:win)?": True,
    "(m\\d+|ace\\d?|2v2)p[12](?:flag|race|link)?": True,
    "(m\\d+|ace\\d?)t[12]p\\d+(?:flag|race|link)?": True,
    "(m\\d+|ace\\d?)(?:map|win|walkover)": True,
    "2v2": True,
    "vod(\\d+)": True,
    "vodgame(\\d+)": True,
    "m(\\d+)vod": True,
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
