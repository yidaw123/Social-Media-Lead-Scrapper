import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# 1. Crews Multi-Sport Taxonomy (12 Sport Categories + Activity Sub-Niches)
# ---------------------------------------------------------------------------

SPORT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "Basketball": {
        "keywords": [
            ("basketball", 6), ("hoops", 5), ("streetball", 6), ("pickup basketball", 7),
            ("pickup runs", 6), ("open gym basketball", 7), ("3x3", 5), ("aau", 5),
            ("dunk", 4), ("ballislife", 5), ("point guard", 5), ("shooting guard", 5),
            ("jumper", 3), ("crossover", 4), ("three pointer", 5), ("3-point", 5),
            ("nba", 3), ("wnba", 4), ("cebl", 5), ("raptors", 4), ("bball", 5),
            ("backboard", 4), ("free throw", 4), ("layup", 4), ("varsity basketball", 6),
        ],
    },
    "Soccer": {
        "keywords": [
            ("soccer", 6), ("futsal", 6), ("pickup soccer", 7), ("footy", 6),
            ("7v7", 5), ("5v5", 5), ("11v11", 5), ("indoor turf", 5), ("turf soccer", 6),
            ("mls", 4), ("cpl", 4), ("soccer training", 6), ("soccer drills", 6),
            ("goalkeeper", 5), ("midfielder", 5), ("striker", 4), ("cleats", 4),
            ("football club", 5), ("fc", 3), ("pitch", 3), ("dribbling", 4),
            ("juggling", 3), ("free kick", 5), ("penalty kick", 5), ("co-ed soccer", 6),
        ],
    },
    "Volleyball": {
        "keywords": [
            ("volleyball", 7), ("beach volleyball", 8), ("indoor volleyball", 7),
            ("co-ed volleyball", 7), ("reverse co-ed", 6), ("vball", 6),
            ("spiking", 4), ("setter", 4), ("libero", 5), ("digging", 3),
            ("bump set spike", 6), ("ova", 4), ("sand court", 5), ("grass volleyball", 7),
            ("volleyball drills", 6), ("volleyball league", 7), ("drop-in volleyball", 7),
        ],
    },
    "Tennis & Pickleball": {
        "keywords": [
            ("pickleball", 7), ("tennis", 7), ("padel", 6), ("squash", 5),
            ("badminton", 5), ("racquet", 5), ("racket", 5), ("dink", 4),
            ("kitchen line", 5), ("pickleball club", 7), ("tennis club", 7),
            ("open play pickleball", 7), ("paddle", 3), ("forehand", 5),
            ("backhand", 5), ("serve and volley", 6), ("utr", 4), ("dupr", 5),
            ("atp", 3), ("wta", 3), ("usta", 4), ("ota", 3), ("rally", 3),
        ],
    },
    "Flag Football & Turf Sports": {
        "keywords": [
            ("flag football", 7), ("touch football", 7), ("ultimate frisbee", 7),
            ("ultimate club", 7), ("ultimate league", 7), ("disc sports", 6),
            ("frisbee", 5), ("rugby", 6), ("touch rugby", 7), ("lacrosse", 6),
            ("field hockey", 6), ("gridiron", 5), ("quarterback", 5), ("wide receiver", 5),
            ("nfl flag", 6), ("7v7 football", 6), ("turf sports", 6),
            ("combine", 3), ("40-yard", 5), ("route running", 5), ("scrum", 5),
        ],
    },
    "Hockey & Ice Sports": {
        "keywords": [
            ("hockey", 6), ("ice hockey", 7), ("shinny", 7), ("beer league", 6),
            ("ball hockey", 7), ("dek hockey", 7), ("roller hockey", 6), ("pond hockey", 7),
            ("skating", 4), ("figure skating", 6), ("rink", 5), ("arena", 3),
            ("puck", 5), ("slapshot", 6), ("hockey stick", 6), ("goalie", 4),
            ("nhl", 3), ("pwhl", 5), ("ohl", 4), ("hockey training", 6),
            ("power skating", 6), ("ice club", 5),
        ],
    },
    "Running & Run Clubs": {
        "keywords": [
            ("run club", 7), ("run crew", 7), ("running club", 7), ("running", 5),
            ("marathon", 6), ("half marathon", 6), ("half-marathon", 6), ("5k", 5),
            ("10k", 5), ("trail running", 7), ("ultra", 4), ("ultramarathon", 6),
            ("strava", 5), ("track workout", 6), ("tempo run", 6), ("long run", 5),
            ("jogging", 5), ("runner", 5), ("runners", 5), ("roadrunners", 6),
            ("crew run", 7), ("social run", 6), ("pacer", 4), ("jog", 4),
            ("parkrun", 6), ("cross country", 5),
        ],
    },
    "Baseball & Softball": {
        "keywords": [
            ("baseball", 6), ("softball", 7), ("slowpitch", 7), ("slo-pitch", 7),
            ("fastpitch", 6), ("co-ed softball", 7), ("batting cage", 6),
            ("batting", 4), ("pitching", 5), ("bullpen", 5), ("home run", 5),
            ("infield", 5), ("outfield", 5), ("catcher", 4), ("mlb", 3),
            ("blue jays", 4), ("hitting coach", 6), ("baseball training", 6),
            ("diamond", 3), ("little league", 5),
        ],
    },
    "Golf": {
        "keywords": [
            ("golf", 6), ("golfer", 6), ("golfing", 6), ("golf swing", 7),
            ("golf simulator", 7), ("indoor golf", 7), ("driving range", 6),
            ("putting", 5), ("short game", 6), ("chipping", 5), ("fairway", 5),
            ("birdie", 4), ("par 3", 5), ("tee time", 6), ("scramble", 4),
            ("pga", 4), ("lpga", 4), ("handicap", 4), ("trackman", 5), ("topgolf", 5),
        ],
    },
    "Fitness & Cross-Training": {
        "keywords": [
            ("hyrox", 7), ("crossfit", 7), ("cross-training", 6), ("hybrid athlete", 6),
            ("bootcamp", 6), ("calisthenics", 6), ("functional fitness", 6),
            ("strength training", 6), ("conditioning", 5), ("kettlebell", 5),
            ("weightlifting", 5), ("powerlifting", 5), ("olympic lifting", 6),
            ("hiit", 5), ("outdoor workout", 6), ("fitness club", 5),
            ("mobility", 4), ("pilates", 4), ("yoga", 4), ("athletic club", 5),
            ("gym", 4), ("workout", 4), ("fitness", 5),
        ],
    },
    "Combat & Martial Arts": {
        "keywords": [
            ("boxing", 6), ("kickboxing", 7), ("muay thai", 7), ("jiu jitsu", 7),
            ("jiu-jitsu", 7), ("bjj", 7), ("mma", 6), ("martial arts", 7),
            ("wrestling", 6), ("grappling", 6), ("sparring", 6), ("karate", 6),
            ("taekwondo", 6), ("judo", 6), ("self-defense", 6), ("self defense", 6),
            ("ufc", 4), ("heavy bag", 5), ("shadowboxing", 6), ("dojo", 6),
            ("octagon", 4), ("submission", 4), ("nogi", 6), ("no-gi", 6),
        ],
    },
    "Multi-Sport & Rec Leagues": {
        "keywords": [
            ("multi-sport", 7), ("multisport", 7), ("rec league", 6), ("rec leagues", 6),
            ("recreational sports", 6), ("adult sports", 6), ("sport & social", 8),
            ("sport and social", 8), ("social sports", 7), ("intramurals", 7),
            ("intramural", 6), ("campus recreation", 7), ("campus rec", 7),
            ("dodgeball", 6), ("kickball", 6), ("cornhole", 5), ("co-ed league", 6),
            ("pickup sports", 7), ("drop-in sports", 7), ("recreation", 4),
            ("athletics", 4), ("sports community", 6), ("all sports", 6),
        ],
    },
}

SPORT_SUB_NICHES: Dict[str, List[Tuple[str, List[str]]]] = {
    "Basketball": [
        ("Pickup Runs & Streetball", ["pickup", "streetball", "open gym", "runs", "park", "outdoor court"]),
        ("Basketball Training & Skills", ["training", "skills", "drills", "shooting", "handles", "ball handling", "workout", "coach"]),
        ("Men's & Co-Ed Rec Leagues", ["rec league", "men's league", "co-ed", "adult league", "division"]),
        ("Youth & AAU / Rep Basketball", ["aau", "youth", "rep", "academy", "junior", "camp"]),
        ("University & Varsity Hoops", ["university", "college", "varsity", "ncaa", "oua", "usports", "campus"]),
        ("3x3 & Tournaments", ["3x3", "3 on 3", "tournament", "classic", "showcase"]),
    ],
    "Soccer": [
        ("Pickup Soccer & Drop-In", ["pickup", "drop-in", "drop in", "casual", "open play"]),
        ("Indoor Turf & Futsal", ["futsal", "indoor", "turf", "dome", "winter soccer"]),
        ("Adult Rec & Co-Ed Leagues", ["rec", "co-ed", "coed", "adult", "social league", "mens league"]),
        ("Soccer Training & Footwork", ["training", "drills", "footwork", "skills", "coach", "conditioning"]),
        ("Youth & Academy Soccer", ["youth", "academy", "u12", "u14", "u16", "junior"]),
        ("Tournaments & 7v7 / 5v5", ["7v7", "5v5", "6v6", "tournament", "cup"]),
    ],
    "Volleyball": [
        ("Beach Volleyball", ["beach", "sand", "outdoor"]),
        ("Indoor Court & Drop-In", ["indoor", "drop-in", "drop in", "pickup", "open gym"]),
        ("Co-Ed & Adult Rec Leagues", ["co-ed", "coed", "rec", "league", "adult"]),
        ("Volleyball Coaching & Drills", ["coaching", "coach", "drills", "training", "skills", "clinic"]),
        ("Grass & Reverse Co-Ed Tournaments", ["grass", "reverse", "tournament", "classic"]),
    ],
    "Tennis & Pickleball": [
        ("Pickleball Clubs & Open Play", ["pickleball", "dink", "dupr", "open play", "paddle"]),
        ("Tennis Coaching & Match Play", ["tennis", "utr", "forehand", "backhand", "serve", "coach"]),
        ("Social Rallies & Ladders", ["ladder", "social", "mixers", "round robin", "rally"]),
        ("Padel & Racquet Sports", ["padel", "squash", "badminton", "racquet", "racket"]),
        ("Junior & Adult Clinics", ["clinic", "lesson", "camp", "junior", "beginner"]),
    ],
    "Flag Football & Turf Sports": [
        ("Flag Football Leagues & Pickup", ["flag football", "touch football", "7v7", "quarterback", "receiver"]),
        ("Ultimate Frisbee", ["ultimate", "frisbee", "disc"]),
        ("Rugby & Touch Rugby", ["rugby", "touch rugby", "scrum", "sevens"]),
        ("Lacrosse & Field Hockey", ["lacrosse", "field hockey"]),
        ("Turf Conditioning & Speed", ["speed", "agility", "combine", "conditioning", "turf"]),
    ],
    "Hockey & Ice Sports": [
        ("Shinny & Beer League Hockey", ["shinny", "beer league", "pickup", "adult hockey", "rec hockey"]),
        ("Hockey Training & Skating", ["training", "power skating", "skills", "drills", "shooting", "coach"]),
        ("Ball & Dek Hockey", ["ball hockey", "dek", "street hockey", "floor hockey"]),
        ("Figure Skating & Ice Clubs", ["figure skating", "skating club", "ice club"]),
        ("Minor & Junior Hockey", ["minor hockey", "junior", "ohl", "aaa", "academy"]),
    ],
    "Running & Run Clubs": [
        ("Social Run Clubs & Crew Runs", ["run club", "run crew", "crew run", "social", "coffee", "meetup", "community"]),
        ("Marathon & Half-Marathon Training", ["marathon", "half marathon", "half-marathon", "boston", "26.2", "13.1"]),
        ("Trail Running & Ultras", ["trail", "ultra", "ultramarathon", "mountain"]),
        ("Track Workouts & Speed", ["track", "speed", "tempo", "intervals", "400m"]),
        ("5K / 10K & Beginner Running", ["5k", "10k", "beginner", "couch to", "jog"]),
    ],
    "Baseball & Softball": [
        ("Slowpitch & Co-Ed Softball", ["slowpitch", "slo-pitch", "softball", "co-ed", "beer league"]),
        ("Baseball Training & Hitting", ["hitting", "swing", "batting", "training", "drills"]),
        ("Pitching & Catching Drills", ["pitching", "pitcher", "bullpen", "catcher", "velocity"]),
        ("Adult Rec & Amateur Leagues", ["adult league", "rec", "men's league", "amateur"]),
        ("Batting Cages & Tournaments", ["cage", "tournament", "classic", "showcase"]),
    ],
    "Golf": [
        ("Golf Swing & Instruction", ["swing", "lesson", "instruction", "coach", "fix your slice", "drills"]),
        ("Course Vlogs & Social Golf", ["vlog", "scramble", "course", "match", "9 holes", "18 holes"]),
        ("Golf Simulators & Indoor Leagues", ["simulator", "indoor", "trackman", "sim", "winter league"]),
        ("Scramble Tournaments & Outings", ["tournament", "outing", "charity", "scramble", "tour"]),
        ("Short Game & Putting", ["putting", "chipping", "short game", "wedge", "bunker"]),
    ],
    "Fitness & Cross-Training": [
        ("HYROX & Hybrid Athletics", ["hyrox", "hybrid", "sled", "erg"]),
        ("CrossFit & Functional Fitness", ["crossfit", "wod", "functional", "rx", "box"]),
        ("Outdoor Bootcamps & Calisthenics", ["bootcamp", "outdoor", "calisthenics", "park", "bodyweight"]),
        ("Strength & Athletic Conditioning", ["strength", "conditioning", "weightlifting", "powerlifting", "kettlebell"]),
        ("Mobility, Yoga & Recovery", ["mobility", "yoga", "pilates", "recovery", "sauna", "cold plunge"]),
    ],
    "Combat & Martial Arts": [
        ("Brazilian Jiu-Jitsu (BJJ) & Grappling", ["bjj", "jiu-jitsu", "jiu jitsu", "grappling", "nogi", "no-gi", "submission"]),
        ("Boxing & Kickboxing", ["boxing", "kickboxing", "heavy bag", "shadowboxing", "sweet science"]),
        ("Muay Thai & Striking", ["muay thai", "nak muay", "striking", "clinch"]),
        ("MMA & Wrestling", ["mma", "ufc", "wrestling", "cage", "mixed martial"]),
        ("Self-Defense & Sparring Clubs", ["self-defense", "self defense", "sparring", "karate", "judo", "taekwondo"]),
    ],
    "Multi-Sport & Rec Leagues": [
        ("Adult Social & Co-Ed Rec Leagues", ["social", "co-ed", "coed", "rec league", "adult sports"]),
        ("Pickup & Drop-In Sports Communities", ["pickup", "drop-in", "drop in", "meetup", "community"]),
        ("University Intramurals & Campus Rec", ["university", "intramural", "intramurals", "campus", "college", "student"]),
        ("Community Sports Hubs & Facilities", ["facility", "complex", "sports centre", "sports center", "club", "athletics"]),
        ("Dodgeball, Kickball & Social Games", ["dodgeball", "kickball", "cornhole", "spikeball", "trivia"]),
    ],
}

# Pre-compile whole-word regexes for sport keywords
_SPORT_KEYWORD_REGEX: Dict[str, "re.Pattern[str]"] = {}
for _smeta in SPORT_CATEGORIES.values():
    for _kw, _w in _smeta["keywords"]:
        if _kw not in _SPORT_KEYWORD_REGEX:
            _SPORT_KEYWORD_REGEX[_kw] = re.compile(r"\b" + re.escape(_kw) + r"(?:s|es)?\b", re.IGNORECASE)


def _kw_in(kw: str, text: str) -> bool:
    return bool(_SPORT_KEYWORD_REGEX[kw].search(text))


def score_sport_categories(
    title_text: str,
    combined_lower: str,
    default_sport: Optional[str] = None,
) -> Tuple[str, List[str], List[Tuple[str, int]]]:
    """Score title & bio text across the 12 Sport Categories."""
    scores: List[Tuple[str, int]] = []
    for sport_name, meta in SPORT_CATEGORIES.items():
        sc = 0
        for kw, weight in meta["keywords"]:
            if _kw_in(kw, title_text):
                sc += weight * 2
            elif _kw_in(kw, combined_lower):
                sc += weight
        if sc > 0:
            scores.append((sport_name, sc))

    scores.sort(key=lambda x: x[1], reverse=True)
    specific_scores = [(s, v) for s, v in scores if s != "Multi-Sport & Rec Leagues" and v >= 4]
    multi_score = next((v for s, v in scores if s == "Multi-Sport & Rec Leagues"), 0)

    # Multi-Sport wins when explicit multi-sport / rec-league terms match strongly or 3+ distinct sports appear alongside multi-sport framing
    explicit_multisport = bool(
        re.search(
            r"\b(multi[- ]?sport|sport\s*(?:&|and)\s*social|intramurals?|campus rec(?:reation)?|social sports|dodgeball|kickball|all sports)\b",
            f"{title_text} {combined_lower}",
            re.IGNORECASE,
        )
    )
    distinct_sports_count = sum(1 for s, v in scores if s != "Multi-Sport & Rec Leagues" and v >= 5)

    if explicit_multisport and (multi_score >= 10 or distinct_sports_count >= 2):
        primary = "Multi-Sport & Rec Leagues"
        secondary = [s for s, v in scores if s != primary and v >= 5][:2]
    elif distinct_sports_count >= 3 and multi_score >= 6:
        primary = "Multi-Sport & Rec Leagues"
        secondary = [s for s, v in scores if s != primary and v >= 5][:2]
    elif specific_scores:
        primary = specific_scores[0][0]
        secondary = [s for s, v in scores if s != primary and v >= 5][:2]
    elif default_sport in SPORT_CATEGORIES:
        primary = default_sport
        secondary = [s for s, v in scores if s != primary and v >= 5][:2]
    elif scores:
        primary = scores[0][0]
        secondary = [s for s, v in scores[1:3] if v >= 5]
    else:
        primary = "Multi-Sport & Rec Leagues"
        secondary = []

    return primary, secondary, scores


def detect_sport_sub_niche(primary_sport: str, title_text: str, combined_lower: str) -> str:
    """Assign the best matching activity sub-niche within the primary sport."""
    options = SPORT_SUB_NICHES.get(primary_sport) or []
    if not options:
        return "General Community"

    best_name = options[0][0]
    best_score = 0
    title_low = (title_text or "").lower()
    for label, kws in options:
        sc = 0
        for kw in kws:
            pat = r"\b" + re.escape(kw) + r"(?:s|es)?\b"
            if re.search(pat, title_low):
                sc += 3
            elif re.search(pat, combined_lower):
                sc += 1
        if sc > best_score:
            best_score = sc
            best_name = label
    return best_name


# ---------------------------------------------------------------------------
# 2. Strict Partner Type Separation: pro_candidate vs. sports_org
# ---------------------------------------------------------------------------

_ORG_STRONG_RE = re.compile(
    r"\b(rec leagues?|sports? leagues?|softball leagues?|soccer leagues?|basketball leagues?|"
    r"volleyball leagues?|beer leagues?|sport\s*(?:&|and)\s*social|athletic club|public racket club|"
    r"tennis club|pickleball club|run club|running club|run crew|roadrunners|association|federation|"
    r"sportsplex|complex|training center|training centre|academy|dojo|boxing club|fitness club|"
    r"crossfit|athletics|intramurals?|campus rec(?:reation)?|recreation department|"
    r"jcc|ymca|ywca|community cent(?:re|er)|recreation cent(?:re|er)|"
    r"tournament\s*(?:operator|series|organizer)|tournaments|race series|running series|"
    r"operations|organization|council|non-?profit|inc\.|ltd\.|llc)\b",
    re.IGNORECASE,
)

_SOLO_CREATOR_PERSONA_RE = re.compile(
    r"(?:\b(?:guy|girl|bro|dad|mom|vlog|vlogs|vlogger|pov|diaries)\b|"
    r"\bfrom\s+a\s+[\w\s]{0,25}player\b|\bsharing\s+my\s+journey\b|\bmy\s+journey\b|"
    r"\bsubscribe\s+for\b|\bshorts\s*&\s*more\b|\blifelong\s+[\w\s]{0,20}junkie\b)",
    re.IGNORECASE,
)

_INDIVIDUAL_PICKUP_HOST_CUE_RE = re.compile(
    r"(?:\bhosted\s+by\b|\borganized\s+by\b|\brun\s+by\b|\bhead\s+organizer\b|"
    r"\bmessage\s+[A-Z][a-z]{2,}\b|\bi\s+host\b|\bdm\s+me\b)",
    re.IGNORECASE,
)

_PRO_STRONG_RE = re.compile(
    r"\b(creator|youtuber|youtube channel|tiktoker|vlog|vlogs|influencer|athlete|"
    r"coach|trainer|instructor|skills trainer|pickup organizer|drop-in host|open gym host|"
    r"game host|captain|varsity athlete|student[- ]athlete|d1|d2|ncaa|oua|u sports|"
    r"my channel|i coach|i train|i play|i host|daily drills|tutorials|tips & drills)\b",
    re.IGNORECASE,
)

_PICKUP_HOST_RE = re.compile(
    r"\b(pickup|drop-?in|open gym|casual games|weekly run|sunday run|shinny)\b",
    re.IGNORECASE,
)

_UNI_LEADER_RE = re.compile(
    r"\b(university|college|varsity|campus|intramural|student|uoft|tmu|ryerson|yorku|waterloo|western|queens|mcgill|ubc)\b",
    re.IGNORECASE,
)


def classify_partner_type(partner: Dict[str, Any]) -> Tuple[str, str]:
    """
    Strictly separate partners into:
      1) 'pro_candidate' (Individual athletes, creators, coaches, pickup organizers, university leaders)
      2) 'sports_org'    (Rec leagues, clubs, gyms, university networks, tournament operators)
    Returns (partner_type, partner_role).
    """
    name = (partner.get("name") or "").strip()
    bio = (partner.get("bio") or "").strip()
    handle = (partner.get("handle") or "").strip()
    website = (partner.get("website") or "").lower()
    linkedin = (partner.get("linkedin_url") or "").lower()
    meetup = (partner.get("meetup_url") or "").lower()
    primary_platform = (partner.get("primary_platform") or "").lower()
    seed_type = (partner.get("seed_partner_type") or "").strip()
    seed_role = (partner.get("seed_partner_role") or "").strip()

    text = f"{name}\n{handle}\n{bio}"

    if primary_platform == "website" or str(partner.get("partner_id") or "").startswith("org_"):
        if seed_type != "pro_candidate":
            aud_txt = (partner.get("audience_text") or "").strip()
            valid_org_roles = {
                "Rec League", "Sports Club / Run Club", "Gym / Training Facility",
                "University Network", "Tournament Operator", "Sports Organization",
            }
            low_t = text.lower()
            if seed_role and seed_type == "sports_org":
                role = seed_role
            elif aud_txt in valid_org_roles:
                role = aud_txt
            elif re.search(r"\b(university|college|campus rec|intramural|varsity|lions|blues|bold|warriors)\b", low_t):
                role = "University Network"
            elif re.search(r"\b(tournament|tournaments|classic|showcase|series|marathon|open championship)\b", low_t):
                role = "Tournament Operator"
            elif re.search(r"\b(gym|dojo|academy|studio|fitness|crossfit|training cent|simulator|facilities|facility|athletic club|bjj|boxing|muay thai|mma)\b", low_t):
                role = "Gym / Training Facility"
            elif re.search(r"\b(league|leagues|sport\s*(?:&|and)\s*social|beer league|slo-?pitch)\b", low_t):
                role = "Rec League"
            elif re.search(r"\b(club|crew|roadrunners|runners|racket club)\b", low_t):
                role = "Sports Club / Run Club"
            else:
                role = "Sports Organization"
            return "sports_org", role

    org_score = 0
    pro_score = 0

    if seed_type == "sports_org":
        org_score += 2
    elif seed_type == "pro_candidate":
        pro_score += 2

    org_hits = len(_ORG_STRONG_RE.findall(text))
    pro_hits = len(_PRO_STRONG_RE.findall(text))
    org_score += org_hits * 3
    pro_score += pro_hits * 3

    if "/company/" in linkedin or "/school/" in linkedin:
        org_score += 4
    elif "/in/" in linkedin:
        pro_score += 3

    if re.search(r"\b(jcc|ymca|ywca|community cent(?:re|er)|recreation cent(?:re|er))\b", f"{text} {handle}", re.IGNORECASE):
        org_score += 8

    is_solo_persona = bool(_SOLO_CREATOR_PERSONA_RE.search(text)) and not re.search(
        r"\b(registration|register now|divisions?|standings|now expanding|sanctioned)\b",
        text,
        re.IGNORECASE,
    )
    if is_solo_persona:
        pro_score += 7

    if primary_platform in ("youtube", "instagram", "tiktok"):
        pro_score += 2
    elif primary_platform == "meetup":
        # Meetup groups only classify as individual Pickup Organizers when an explicit solo host cue is present
        has_facility_or_org = bool(
            re.search(
                r"\b(league|association|federation|academy|gym|athletics|sport\s*(?:&|and)\s*social|club|jcc|ymca|community|meetup\s+group)\b",
                f"{name} {handle}",
                re.IGNORECASE,
            )
        )
        if _PICKUP_HOST_RE.search(text) and _INDIVIDUAL_PICKUP_HOST_CUE_RE.search(text) and not has_facility_or_org:
            pro_score += 4
        else:
            org_score += 4
    elif primary_platform == "eventbrite":
        if re.search(r"\b(head coach|coach\s+[a-z]+|trainer|instructor)\b", text, re.IGNORECASE) and not re.search(
            r"\b(club|league|association|academy|inc|ltd)\b", name, re.IGNORECASE
        ):
            pro_score += 4
        else:
            org_score += 2

    if "official" in name.lower() or "ontario" in name.lower() and re.search(r"\b(association|federation|golf|baseball|tennis|volleyball|pickleball|soccer|basketball)\b", name, re.IGNORECASE):
        org_score += 4

    if not is_solo_persona and re.search(
        r"\b(club|league|academy|gym|studio|association|federation|athletics|network|tournaments?|series|marathon|combine)\b",
        name,
        re.IGNORECASE,
    ):
        org_score += 3

    if re.search(r"\b(with\s+[A-Z][a-z]+|by\s+[A-Z][a-z]+|coach\s+[A-Z][a-z]+)\b", text):
        pro_score += 2

    # First-person singular strongly indicates an individual creator / coach / pickup organizer
    if re.search(
        r"(?:\bi\s+am\b|\bi['’]m\b|\bmy\s+name\s+is\b|\bmy\s+channel\b|\bfollow\s+my\b|"
        r"\bjoin\s+me\b|\bdocument\s+that\s+journey\b|\b28-year-old\s+creator\b|\bpersonal\s+trainer\b)",
        bio,
        re.IGNORECASE,
    ):
        pro_score += 6

    if org_score > pro_score:
        partner_type = "sports_org"
    else:
        partner_type = "pro_candidate"

    # Assign specific partner_role
    low = text.lower()
    if partner_type == "sports_org":
        if seed_role and seed_type == "sports_org":
            role = seed_role
        elif re.search(r"\b(university|college|campus rec|intramural|varsity|uoft|tmu|yorku|uwaterloo)\b", low):
            role = "University Network"
        elif re.search(r"\b(tournament|tournaments|classic|showcase|series|cup|open championship)\b", low):
            role = "Tournament Operator"
        elif re.search(r"\b(gym|dojo|academy|studio|fitness|crossfit|training cent|simulator|facilities|facility|athletic club|bjj|boxing|muay thai|jcc|ymca|ywca|community cent|recreation cent)\b", low):
            role = "Gym / Training Facility"
        elif re.search(r"\b(league|leagues|sport\s*(?:&|and)\s*social|beer league|slo-?pitch)\b", low):
            role = "Rec League"
        elif re.search(r"\b(club|crew|roadrunners|runners|group|meetup)\b", low) or meetup:
            role = "Sports Club / Run Club"
        else:
            role = "Sports Organization"
    else:
        if seed_role and seed_type == "pro_candidate":
            role = seed_role
        elif re.search(r"\b(coach|coaching|trainer|instructor|lessons|swing coach|skills coach)\b", name.lower()):
            role = "Coach / Trainer"
        elif _UNI_LEADER_RE.search(low) and re.search(r"\b(captain|president|varsity athlete|student[- ]athlete|ncaa|oua|u sports)\b", low):
            role = "University Leader"
        elif _PICKUP_HOST_RE.search(low) and (
            meetup
            or re.search(r"\b(organizer|host|captain|weekly|sunday|saturday|tuesday|thursday|drop-?in|open gym)\b", low)
        ):
            role = "Pickup Organizer"
        elif re.search(r"\b(coach|trainer|instructor|lessons|swing coach|skills coach|coaching)\b", low):
            role = "Coach / Trainer"
        else:
            role = "Sports Creator / Athlete"

    return partner_type, role


# ---------------------------------------------------------------------------
# 3. US & Canada-Only City / Province-State / Country Geo Extraction
# ---------------------------------------------------------------------------

US_STATE_ABBR_TO_NAME: Dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

CA_PROV_ABBR_TO_NAME: Dict[str, str] = {
    "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba",
    "NB": "New Brunswick", "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia", "NT": "Northwest Territories", "NU": "Nunavut",
    "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec",
    "SK": "Saskatchewan", "YT": "Yukon",
}

US_STATE_NAME_SET = set(US_STATE_ABBR_TO_NAME.values())
CA_PROV_NAME_SET = set(CA_PROV_ABBR_TO_NAME.values())

GTA_CITIES = {
    "Toronto", "Mississauga", "Brampton", "Markham", "Vaughan",
    "Richmond Hill", "Oakville", "Burlington", "Pickering", "Ajax",
    "Whitby", "Oshawa", "Milton", "Newmarket", "Aurora",
}

TORONTO_BOROUGHS = {
    "Scarborough": "Toronto",
    "North York": "Toronto",
    "Etobicoke": "Toronto",
    "East York": "Toronto",
    "York": "Toronto",
    "Willowdale": "Toronto",
    "Downtown Toronto": "Toronto",
    "Liberty Village": "Toronto",
    "Leslieville": "Toronto",
    "Yorkville": "Toronto",
    "Unionville": "Markham",
    "Thornhill": "Vaughan",
}

US_CA_MAJOR_CITIES: Dict[str, Tuple[str, str]] = {
    # Canada (Heavy Toronto / GTA + major metros)
    "Toronto": ("Ontario", "Canada"),
    "Scarborough": ("Ontario", "Canada"),
    "North York": ("Ontario", "Canada"),
    "Etobicoke": ("Ontario", "Canada"),
    "East York": ("Ontario", "Canada"),
    "Downtown Toronto": ("Ontario", "Canada"),
    "Mississauga": ("Ontario", "Canada"),
    "Brampton": ("Ontario", "Canada"),
    "Markham": ("Ontario", "Canada"),
    "Vaughan": ("Ontario", "Canada"),
    "Richmond Hill": ("Ontario", "Canada"),
    "Oakville": ("Ontario", "Canada"),
    "Burlington": ("Ontario", "Canada"),
    "Pickering": ("Ontario", "Canada"),
    "Ajax": ("Ontario", "Canada"),
    "Whitby": ("Ontario", "Canada"),
    "Oshawa": ("Ontario", "Canada"),
    "Milton": ("Ontario", "Canada"),
    "Newmarket": ("Ontario", "Canada"),
    "Aurora": ("Ontario", "Canada"),
    "Hamilton": ("Ontario", "Canada"),
    "Cambridge": ("Ontario", "Canada"),
    "Ottawa": ("Ontario", "Canada"),
    "Waterloo": ("Ontario", "Canada"),
    "Kitchener": ("Ontario", "Canada"),
    "Guelph": ("Ontario", "Canada"),
    "Vancouver": ("British Columbia", "Canada"),
    "Burnaby": ("British Columbia", "Canada"),
    "Surrey": ("British Columbia", "Canada"),
    "Kelowna": ("British Columbia", "Canada"),
    "Montreal": ("Quebec", "Canada"),
    "Montréal": ("Quebec", "Canada"),
    "Quebec City": ("Quebec", "Canada"),
    "Québec City": ("Quebec", "Canada"),
    "Calgary": ("Alberta", "Canada"),
    "Edmonton": ("Alberta", "Canada"),
    "Canmore": ("Alberta", "Canada"),
    "Winnipeg": ("Manitoba", "Canada"),
    "Halifax": ("Nova Scotia", "Canada"),
    "Saskatoon": ("Saskatchewan", "Canada"),
    "Regina": ("Saskatchewan", "Canada"),
    # United States (unambiguous metro names)
    "New York": ("New York", "United States"),
    "Brooklyn": ("New York", "United States"),
    "Los Angeles": ("California", "United States"),
    "San Diego": ("California", "United States"),
    "San Francisco": ("California", "United States"),
    "San Jose": ("California", "United States"),
    "Sacramento": ("California", "United States"),
    "Fresno": ("California", "United States"),
    "Chicago": ("Illinois", "United States"),
    "Houston": ("Texas", "United States"),
    "San Antonio": ("Texas", "United States"),
    "Dallas": ("Texas", "United States"),
    "Fort Worth": ("Texas", "United States"),
    "El Paso": ("Texas", "United States"),
    "Austin": ("Texas", "United States"),
    "Philadelphia": ("Pennsylvania", "United States"),
    "Pittsburgh": ("Pennsylvania", "United States"),
    "Tucson": ("Arizona", "United States"),
    "Phoenix": ("Arizona", "United States"),
    "Seattle": ("Washington", "United States"),
    "Spokane": ("Washington", "United States"),
    "Denver": ("Colorado", "United States"),
    "Boston": ("Massachusetts", "United States"),
    "Detroit": ("Michigan", "United States"),
    "Grand Rapids": ("Michigan", "United States"),
    "Minneapolis": ("Minnesota", "United States"),
    "Atlanta": ("Georgia", "United States"),
    "Miami": ("Florida", "United States"),
    "Tampa": ("Florida", "United States"),
    "Orlando": ("Florida", "United States"),
    "Jacksonville": ("Florida", "United States"),
    "Raleigh": ("North Carolina", "United States"),
    "Charlotte": ("North Carolina", "United States"),
    "Nashville": ("Tennessee", "United States"),
    "Knoxville": ("Tennessee", "United States"),
    "Chattanooga": ("Tennessee", "United States"),
    "Memphis": ("Tennessee", "United States"),
    "Las Vegas": ("Nevada", "United States"),
    "Salt Lake City": ("Utah", "United States"),
    "Indianapolis": ("Indiana", "United States"),
    "Columbus": ("Ohio", "United States"),
    "Cleveland": ("Ohio", "United States"),
    "Cincinnati": ("Ohio", "United States"),
    "Baltimore": ("Maryland", "United States"),
    "Louisville": ("Kentucky", "United States"),
    "Kansas City": ("Missouri", "United States"),
    "St. Louis": ("Missouri", "United States"),
    "Oklahoma City": ("Oklahoma", "United States"),
    "Albuquerque": ("New Mexico", "United States"),
    "Omaha": ("Nebraska", "United States"),
    "Boise": ("Idaho", "United States"),
    "Des Moines": ("Iowa", "United States"),
    "Anchorage": ("Alaska", "United States"),
    "Honolulu": ("Hawaii", "United States"),
}

_FALSE_CITY_WORDS = {
    "in", "at", "from", "the", "our", "my", "and", "for", "with", "near",
    "based", "home", "best", "top", "free", "new", "all", "on", "to", "welcome",
    "service", "services", "serving", "youtube", "instagram", "tiktok",
    "facebook", "twitch", "twitter", "bluesky", "channel", "subscribe", "video",
    "videos", "tips", "tricks", "shop", "store", "link", "links", "email",
    "contact", "about", "more", "copyright", "privacy", "terms", "policy",
    "login", "sign", "menu", "search", "skip", "content",
    # Sports false-positives
    "basketball", "soccer", "volleyball", "tennis", "pickleball", "hockey",
    "running", "baseball", "softball", "golf", "fitness", "boxing", "rugby",
    "league", "leagues", "club", "clubs", "pickup", "training", "coach",
    "coaching", "athletics", "sports", "sport", "team", "teams", "tournament",
    "crew", "crews", "register", "schedule", "events", "meetup", "eventbrite",
    "strava", "games", "play", "player", "players", "gym", "arena", "turf",
    "court", "field", "track", "marathon", "fitness", "bootcamp",
    "virtual", "clinic", "clinics", "online", "remote", "workshop", "workshops",
    "seminar", "seminars", "webinar",
}

_BAD_ANYWHERE_CITY_WORDS = {
    "building", "suite", "ste", "street", "avenue", "ave", "blvd", "boulevard",
    "road", "rd", "drive", "dr", "lane", "ln", "floor", "tower", "plaza",
    "llc", "inc", "corp", "ltd", "box", "po", "tatnall", "times", "centre", "center",
    "country", "club", "resort", "academy", "university", "college", "school",
}

_AMBIGUOUS_STATE_ABBRS = {"IN", "OR", "ME", "OH", "HI", "OK", "ON", "DE", "LA", "PA"}

_CITY_ABBR_RE = re.compile(
    r"\b([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){0,2}),\s*("
    + "|".join(sorted(list(US_STATE_ABBR_TO_NAME.keys()) + list(CA_PROV_ABBR_TO_NAME.keys())))
    + r")\b(?![a-z])"
)

_ALL_PROV_STATE_NAMES = sorted(
    list(US_STATE_NAME_SET | CA_PROV_NAME_SET),
    key=len,
    reverse=True,
)
_CITY_FULL_RE = re.compile(
    r"\b([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){0,2}),\s*("
    + "|".join(re.escape(n) for n in _ALL_PROV_STATE_NAMES)
    + r")\b"
)
_STANDALONE_PROV_RE = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in _ALL_PROV_STATE_NAMES) + r")\b"
)
_MAJOR_CITY_RE = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in sorted(US_CA_MAJOR_CITIES.keys(), key=len, reverse=True)) + r")\b"
)


def is_toronto_gta(city: str, province_state: str, country: str) -> bool:
    return country == "Canada" and province_state == "Ontario" and city in GTA_CITIES


def _normalize_city_name(city: str) -> str:
    clean = " ".join((city or "").strip().split())
    if clean and (clean.islower() or clean.isupper()):
        clean = clean.title()
    if clean in TORONTO_BOROUGHS:
        return TORONTO_BOROUGHS[clean]
    if clean in ("Montréal",):
        return "Montreal"
    if clean in ("Québec City",):
        return "Quebec City"
    return clean


def _normalize_country_name(country: str) -> str:
    raw = (country or "").strip()
    low = raw.lower()
    if low in ("us", "usa", "u.s.", "u.s.a.", "united states", "united states of america"):
        return "United States"
    if low in ("ca", "can", "canada"):
        return "Canada"
    return raw


def _is_valid_city_candidate(candidate: str) -> bool:
    clean = " ".join((candidate or "").strip().split())
    if len(clean) < 3 or len(clean) > 28:
        return False
    if any(ch.isdigit() for ch in clean):
        return False
    words = [w.strip(".,'").lower() for w in clean.split() if w.strip(".,'")]
    if not words or len(words) > 3:
        return False
    if len(words) >= 2 and len(set(words)) < len(words):
        return False
    if words[0] in _FALSE_CITY_WORDS or words[-1] in _FALSE_CITY_WORDS:
        return False
    if all(w in _FALSE_CITY_WORDS for w in words):
        return False
    if any(w in _BAD_ANYWHERE_CITY_WORDS for w in words):
        return False
    if clean in US_STATE_NAME_SET or clean in CA_PROV_NAME_SET:
        return False
    return True


def _resolve_region(region_code_or_name: str, allowed_country: str) -> Tuple[str, str]:
    if region_code_or_name in US_STATE_ABBR_TO_NAME:
        prov, ctry = US_STATE_ABBR_TO_NAME[region_code_or_name], "United States"
    elif region_code_or_name in CA_PROV_ABBR_TO_NAME:
        prov, ctry = CA_PROV_ABBR_TO_NAME[region_code_or_name], "Canada"
    elif region_code_or_name in US_STATE_NAME_SET:
        prov, ctry = region_code_or_name, "United States"
    elif region_code_or_name in CA_PROV_NAME_SET:
        prov, ctry = region_code_or_name, "Canada"
    else:
        return "", ""
    if allowed_country and allowed_country != ctry:
        return "", ""
    return prov, ctry


def _scan_text_for_us_ca_geo(text: str, allowed_country: str) -> Tuple[str, str, str]:
    if not text:
        return "", "", ""

    for m in _CITY_ABBR_RE.finditer(text):
        city_cand, code = m.group(1).strip(), m.group(2).strip()
        if not _is_valid_city_candidate(city_cand):
            continue
        norm_city = _normalize_city_name(city_cand.title() if city_cand.isupper() else city_cand)
        if code in _AMBIGUOUS_STATE_ABBRS and norm_city not in US_CA_MAJOR_CITIES:
            tail = text[m.end():m.end() + 18]
            if re.match(r"^\s+[A-Za-z]{2,}", tail) and not re.match(r"^\s+(?:Canada|USA|United\s+States)\b", tail, re.I):
                continue
        prov, ctry = _resolve_region(code, allowed_country)
        if prov:
            return norm_city, prov, ctry

    for m in _CITY_FULL_RE.finditer(text):
        city_cand, state_full = m.group(1).strip(), m.group(2).strip()
        if not _is_valid_city_candidate(city_cand):
            continue
        prov, ctry = _resolve_region(state_full, allowed_country)
        if prov:
            norm_city = _normalize_city_name(city_cand.title() if city_cand.isupper() else city_cand)
            return norm_city, prov, ctry

    for m in _MAJOR_CITY_RE.finditer(text):
        city_name = m.group(1)
        if city_name == "New York" and text[m.end():m.end() + 6].lower() == " times":
            continue
        prov, ctry = US_CA_MAJOR_CITIES[city_name]
        if allowed_country and allowed_country != ctry:
            continue
        return _normalize_city_name(city_name), prov, ctry

    # Greater Toronto Area / GTA explicit mention
    if (not allowed_country or allowed_country == "Canada") and re.search(
        r"\b(Greater Toronto Area|GTA)\b", text
    ):
        return "Toronto", "Ontario", "Canada"

    for m in _STANDALONE_PROV_RE.finditer(text):
        prov, ctry = _resolve_region(m.group(1), allowed_country)
        if prov:
            return "", prov, ctry

    return "", "", ""


def _has_ca_tld(website: str, business_email: str) -> bool:
    for val in (website or "", business_email or ""):
        s = val.strip().lower()
        if not s:
            continue
        if "://" in s:
            host = (urlparse(s).netloc or "").split(":")[0]
            if host.endswith(".ca"):
                return True
        elif "@" in s:
            dom = s.split("@", 1)[1].split(",")[0].strip()
            if dom.endswith(".ca"):
                return True
    return False


def extract_partner_location(
    name: str,
    bio: str,
    country: str = "",
    extra_text: str = "",
    website: str = "",
    business_email: str = "",
) -> Tuple[str, str, str]:
    """
    Extract (city, province_state, country) ONLY for United States and Canada partners.
    Partners outside United States / Canada keep only their country with empty city & province_state.
    """
    norm_country = _normalize_country_name(country)
    if norm_country and norm_country not in ("United States", "Canada"):
        return "", "", norm_country

    primary_text = f"{name or ''}\n{bio or ''}"
    city, prov, inferred_country = _scan_text_for_us_ca_geo(primary_text, norm_country)

    if extra_text and (not city or not prov):
        allowed = norm_country or inferred_country
        ex_city, ex_prov, ex_country = _scan_text_for_us_ca_geo(extra_text, allowed)
        if ex_city and ex_prov:
            if not prov or ex_prov == prov:
                city, prov = ex_city, ex_prov
                inferred_country = inferred_country or ex_country
        elif ex_prov and not prov:
            prov = ex_prov
            inferred_country = inferred_country or ex_country

    if not norm_country and not inferred_country and _has_ca_tld(website, business_email):
        inferred_country = "Canada"

    final_country = norm_country or inferred_country
    if final_country not in ("United States", "Canada"):
        return "", "", final_country
    return city, prov, final_country


# ---------------------------------------------------------------------------
# 4. Audience Tiers & Top-Level Partner Classification
# ---------------------------------------------------------------------------

def compute_audience_tier(count: int) -> str:
    """Bucket a partner's audience / member count into outreach tiers."""
    if count >= 1_000_000:
        return "mega"
    if count >= 500_000:
        return "macro"
    if count >= 100_000:
        return "mid"
    if count >= 10_000:
        return "micro"
    return "nano"


def classify_partner(partner: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify a discovered sports creator, pickup organizer, or local sports organization:
      - primary_sport (1 of 12 Sport Categories) + sub_niche + secondary_sports
      - partner_type ('pro_candidate' or 'sports_org') + partner_role
      - audience_tier ('nano' .. 'mega')
      - US/Canada-only (city, province_state, country)
    """
    name = (partner.get("name") or "").strip()
    bio = (partner.get("bio") or "").strip()
    seed_topic = (partner.get("seed_topic") or "").strip()
    combined = f"{name} {bio} {seed_topic}".lower()

    primary_sport, secondary_sports, _ = score_sport_categories(
        f"{name} {seed_topic}",
        combined,
        partner.get("default_sport"),
    )
    sub_niche = detect_sport_sub_niche(primary_sport, f"{name} {seed_topic}", combined)
    partner_type, partner_role = classify_partner_type(partner)

    raw_aud = int(partner.get("audience_count") or 0)
    prim_plat = (partner.get("primary_platform") or "").lower()
    yt_f = int(partner.get("youtube_followers") or (raw_aud if prim_plat == "youtube" else 0))
    ig_f = int(partner.get("instagram_followers") or (raw_aud if prim_plat == "instagram" else 0))
    tt_f = int(partner.get("tiktok_followers") or (raw_aud if prim_plat == "tiktok" else 0))
    bs_f = int(partner.get("bluesky_followers") or (raw_aud if prim_plat == "bluesky" else 0))
    mu_m = int(partner.get("meetup_members") or (raw_aud if prim_plat == "meetup" else 0))
    total_followers = yt_f + ig_f + tt_f + bs_f + mu_m
    audience_count = max(total_followers, raw_aud)
    audience_tier = compute_audience_tier(audience_count)

    aud_text = (partner.get("audience_text") or "").strip()
    generic_role_labels = {
        "", "Rec League", "Sports Club / Run Club", "Gym / Training Facility",
        "University Network", "Tournament Operator", "Sports Organization",
        "YouTube Channel", "Bluesky Profile", "Meetup Group", "Eventbrite Organizer",
    }
    if audience_count > 0 and aud_text in generic_role_labels:
        aud_text = f"{audience_count:,} followers"

    existing_city = _normalize_city_name(partner.get("city") or "")
    existing_prov = (partner.get("province_state") or "").strip()
    if existing_prov in CA_PROV_ABBR_TO_NAME:
        existing_prov = CA_PROV_ABBR_TO_NAME[existing_prov]
    elif existing_prov in US_STATE_ABBR_TO_NAME:
        existing_prov = US_STATE_ABBR_TO_NAME[existing_prov]
    existing_country = _normalize_country_name(partner.get("country") or "")

    has_structured_loc = (
        existing_country in ("United States", "Canada")
        and bool(existing_city)
        and _is_valid_city_candidate(existing_city)
        and bool(existing_prov)
        and (
            str(partner.get("partner_id") or "").startswith(("org_", "mu_", "eb_", "ig_", "tt_"))
            or prim_plat in ("website", "meetup", "eventbrite", "instagram", "tiktok")
        )
    )

    if has_structured_loc:
        city, province_state, country = existing_city, existing_prov, existing_country
    else:
        city, province_state, country = extract_partner_location(
            name=name,
            bio=bio,
            country=partner.get("country") or "",
            extra_text=partner.get("_extra_geo_text") or "",
            website=partner.get("website") or "",
            business_email=partner.get("business_email") or "",
        )
        if country in ("United States", "Canada"):
            if not city and existing_city and _is_valid_city_candidate(existing_city):
                city = existing_city
            if not province_state and existing_prov:
                province_state = existing_prov
        else:
            city = ""
            province_state = ""

    # Enforce canonical province/state when city is an unambiguous major metro (e.g., prevents 'Toronto, British Columbia')
    if country in ("United States", "Canada") and city in US_CA_MAJOR_CITIES:
        canon_prov, canon_ctry = US_CA_MAJOR_CITIES[city]
        if canon_ctry == country:
            province_state = canon_prov

    cleaned = {
        k: v
        for k, v in partner.items()
        if k not in ("_extra_geo_text", "seed_partner_type", "seed_partner_role", "default_sport", "seed_topic")
    }
    return {
        **cleaned,
        "partner_type": partner_type,
        "partner_role": partner_role,
        "country": country,
        "province_state": province_state,
        "city": city,
        "primary_sport": primary_sport,
        "sub_niche": sub_niche,
        "secondary_sports": secondary_sports,
        "audience_count": audience_count,
        "audience_text": aud_text,
        "audience_tier": audience_tier,
        "youtube_followers": yt_f,
        "instagram_followers": ig_f,
        "tiktok_followers": tt_f,
        "bluesky_followers": bs_f,
        "meetup_members": mu_m,
    }
