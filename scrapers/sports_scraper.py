import html as html_lib
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Discovery Seeds: Heavy Toronto / GTA & Canada + Broader North America
# Format: (query, default_sport, seed_partner_type, seed_partner_role)
# seed_partner_type is a hint ('pro_candidate', 'sports_org', or '' for auto)
# ---------------------------------------------------------------------------

YOUTUBE_SPORTS_SEEDS: List[Tuple[str, str, str, str]] = [
    # Basketball
    ("toronto pickup basketball runs", "Basketball", "pro_candidate", "Pickup Organizer"),
    ("basketball skills trainer canada", "Basketball", "pro_candidate", "Coach / Trainer"),
    ("streetball pickup basketball vlog", "Basketball", "pro_candidate", "Sports Creator / Athlete"),
    ("basketball shooting workouts drills coach", "Basketball", "pro_candidate", "Coach / Trainer"),
    ("university basketball vlog training canada", "Basketball", "pro_candidate", "University Leader"),
    ("toronto basketball rec league mens", "Basketball", "sports_org", "Rec League"),
    # Soccer
    ("toronto pickup soccer futsal", "Soccer", "pro_candidate", "Pickup Organizer"),
    ("soccer training footwork drills creator", "Soccer", "pro_candidate", "Coach / Trainer"),
    ("indoor soccer league toronto ontario", "Soccer", "sports_org", "Rec League"),
    ("adult rec soccer vlog canada", "Soccer", "pro_candidate", "Sports Creator / Athlete"),
    ("7v7 soccer tournament highlights coach", "Soccer", "pro_candidate", "Sports Creator / Athlete"),
    # Volleyball
    ("toronto beach volleyball league ashbridges", "Volleyball", "sports_org", "Rec League"),
    ("volleyball coaching drills jump serve", "Volleyball", "pro_candidate", "Coach / Trainer"),
    ("pickup indoor volleyball vlog canada", "Volleyball", "pro_candidate", "Pickup Organizer"),
    ("coed volleyball tournament vlog", "Volleyball", "pro_candidate", "Sports Creator / Athlete"),
    # Tennis & Pickleball
    ("toronto pickleball club open play", "Tennis & Pickleball", "sports_org", "Sports Club / Run Club"),
    ("pickleball tips drills coach creator", "Tennis & Pickleball", "pro_candidate", "Coach / Trainer"),
    ("tennis lessons forehand footwork canada", "Tennis & Pickleball", "pro_candidate", "Coach / Trainer"),
    ("toronto tennis club padel social", "Tennis & Pickleball", "sports_org", "Sports Club / Run Club"),
    ("college tennis vlog match play", "Tennis & Pickleball", "pro_candidate", "University Leader"),
    # Flag Football & Turf Sports
    ("toronto flag football league", "Flag Football & Turf Sports", "sports_org", "Rec League"),
    ("toronto ultimate frisbee club", "Flag Football & Turf Sports", "sports_org", "Sports Club / Run Club"),
    ("flag football quarterback route running drills", "Flag Football & Turf Sports", "pro_candidate", "Coach / Trainer"),
    ("rugby training fitness canada", "Flag Football & Turf Sports", "pro_candidate", "Sports Creator / Athlete"),
    # Hockey & Ice Sports
    ("toronto shinny beer league hockey", "Hockey & Ice Sports", "pro_candidate", "Pickup Organizer"),
    ("hockey skating skills coach canada", "Hockey & Ice Sports", "pro_candidate", "Coach / Trainer"),
    ("adult hockey league ontario", "Hockey & Ice Sports", "sports_org", "Rec League"),
    ("ball hockey dek hockey canada", "Hockey & Ice Sports", "pro_candidate", "Sports Creator / Athlete"),
    ("college hockey training vlog", "Hockey & Ice Sports", "pro_candidate", "University Leader"),
    # Running & Run Clubs
    ("toronto run club social running", "Running & Run Clubs", "sports_org", "Sports Club / Run Club"),
    ("canada marathon running vlog training", "Running & Run Clubs", "pro_candidate", "Sports Creator / Athlete"),
    ("vancouver montreal run club marathon", "Running & Run Clubs", "pro_candidate", "Sports Creator / Athlete"),
    ("trail running track workout coach", "Running & Run Clubs", "pro_candidate", "Coach / Trainer"),
    ("run crew community organizer vlog", "Running & Run Clubs", "pro_candidate", "Pickup Organizer"),
    # Baseball & Softball
    ("toronto slowpitch softball league", "Baseball & Softball", "sports_org", "Rec League"),
    ("baseball hitting pitching coach drills", "Baseball & Softball", "pro_candidate", "Coach / Trainer"),
    ("baseball vlog training canada", "Baseball & Softball", "pro_candidate", "Sports Creator / Athlete"),
    ("slowpitch softball swing tips", "Baseball & Softball", "pro_candidate", "Sports Creator / Athlete"),
    # Golf
    ("toronto golf vlog indoor simulator", "Golf", "pro_candidate", "Sports Creator / Athlete"),
    ("golf swing coach lessons canada", "Golf", "pro_candidate", "Coach / Trainer"),
    ("canada golf course vlog scramble", "Golf", "pro_candidate", "Sports Creator / Athlete"),
    ("short game putting drills golf instruction", "Golf", "pro_candidate", "Coach / Trainer"),
    # Fitness & Cross-Training
    ("toronto hyrox hybrid athlete training", "Fitness & Cross-Training", "pro_candidate", "Sports Creator / Athlete"),
    ("toronto crossfit bootcamp fitness club", "Fitness & Cross-Training", "sports_org", "Gym / Training Facility"),
    ("calisthenics outdoor workout coach canada", "Fitness & Cross-Training", "pro_candidate", "Coach / Trainer"),
    ("strength conditioning functional fitness creator", "Fitness & Cross-Training", "pro_candidate", "Sports Creator / Athlete"),
    # Combat & Martial Arts
    ("toronto boxing muay thai gym sparring", "Combat & Martial Arts", "sports_org", "Gym / Training Facility"),
    ("bjj jiu jitsu coach breakdowns canada", "Combat & Martial Arts", "pro_candidate", "Coach / Trainer"),
    ("boxing heavy bag footwork drills coach", "Combat & Martial Arts", "pro_candidate", "Coach / Trainer"),
    ("mma wrestling training vlog", "Combat & Martial Arts", "pro_candidate", "Sports Creator / Athlete"),
    # Multi-Sport & Rec Leagues
    ("toronto sport and social rec league", "Multi-Sport & Rec Leagues", "sports_org", "Rec League"),
    ("university intramurals campus recreation canada", "Multi-Sport & Rec Leagues", "sports_org", "University Network"),
    ("canadian university student athlete vlog", "Multi-Sport & Rec Leagues", "pro_candidate", "University Leader"),
    ("adult rec league dodgeball kickball", "Multi-Sport & Rec Leagues", "sports_org", "Rec League"),
]

MEETUP_SEARCH_SEEDS: List[Tuple[str, str, str]] = [
    ("basketball", "ca--on--Toronto", "Basketball"),
    ("soccer", "ca--on--Toronto", "Soccer"),
    ("volleyball", "ca--on--Toronto", "Volleyball"),
    ("pickleball", "ca--on--Toronto", "Tennis & Pickleball"),
    ("tennis", "ca--on--Toronto", "Tennis & Pickleball"),
    ("running", "ca--on--Toronto", "Running & Run Clubs"),
    ("ultimate frisbee", "ca--on--Toronto", "Flag Football & Turf Sports"),
    ("flag football", "ca--on--Toronto", "Flag Football & Turf Sports"),
    ("hockey", "ca--on--Toronto", "Hockey & Ice Sports"),
    ("softball", "ca--on--Toronto", "Baseball & Softball"),
    ("golf", "ca--on--Toronto", "Golf"),
    ("fitness bootcamp", "ca--on--Toronto", "Fitness & Cross-Training"),
    ("sports pickup", "ca--on--Toronto", "Multi-Sport & Rec Leagues"),
    ("sports", "ca--on--Mississauga", "Multi-Sport & Rec Leagues"),
    ("sports", "ca--on--Ottawa", "Multi-Sport & Rec Leagues"),
    ("sports", "ca--bc--Vancouver", "Multi-Sport & Rec Leagues"),
    ("sports", "ca--ab--Calgary", "Multi-Sport & Rec Leagues"),
    ("running", "ca--qc--Montreal", "Running & Run Clubs"),
]

BLUESKY_SEARCH_SEEDS: List[Tuple[str, str, str]] = [
    ("toronto basketball pickup", "Basketball", "pro_candidate"),
    ("toronto run club", "Running & Run Clubs", "sports_org"),
    ("pickleball coach", "Tennis & Pickleball", "pro_candidate"),
    ("soccer training futsal", "Soccer", "pro_candidate"),
    ("volleyball club league", "Volleyball", "sports_org"),
    ("boxing bjj muay thai", "Combat & Martial Arts", "pro_candidate"),
    ("hyrox fitness coach", "Fitness & Cross-Training", "pro_candidate"),
    ("golf swing coach", "Golf", "pro_candidate"),
    ("hockey skills skating", "Hockey & Ice Sports", "pro_candidate"),
    ("rec league sports", "Multi-Sport & Rec Leagues", "sports_org"),
]

# Curated real public Toronto/GTA & Canadian Sports Organizations, Clubs & University Networks
# Each entry is live-crawled on HTTP (no synthetic or hardcoded contact fields).
CURATED_CANADIAN_ORG_SEEDS: List[Dict[str, str]] = [
    # Multi-Sport & Rec Leagues
    {"name": "JAM Sports Toronto", "url": "https://toronto.jamsports.com", "sport": "Multi-Sport & Rec Leagues", "role": "Rec League", "city": "Toronto", "prov": "Ontario"},
    {"name": "XTSC (Toronto Sport & Social)", "url": "https://www.xtsc.ca", "sport": "Multi-Sport & Rec Leagues", "role": "Rec League", "city": "Toronto", "prov": "Ontario"},
    {"name": "Ottawa Sport & Social Club", "url": "https://ottawasportandsocialclub.ca", "sport": "Multi-Sport & Rec Leagues", "role": "Rec League", "city": "Ottawa", "prov": "Ontario"},
    {"name": "Calgary Sport & Social Club", "url": "https://www.calgarysportsclub.com", "sport": "Multi-Sport & Rec Leagues", "role": "Rec League", "city": "Calgary", "prov": "Alberta"},
    {"name": "Edmonton Sport & Social Club", "url": "https://www.edmontonsportsclub.com", "sport": "Multi-Sport & Rec Leagues", "role": "Rec League", "city": "Edmonton", "prov": "Alberta"},
    {"name": "Urban Rec Vancouver", "url": "https://www.urbanrec.ca", "sport": "Multi-Sport & Rec Leagues", "role": "Rec League", "city": "Vancouver", "prov": "British Columbia"},
    {"name": "UofT Sport & Rec", "url": "https://kpe.utoronto.ca", "sport": "Multi-Sport & Rec Leagues", "role": "University Network", "city": "Toronto", "prov": "Ontario"},
    {"name": "TMU Recreation (Toronto Metropolitan University)", "url": "https://www.torontomu.ca/recreation", "sport": "Multi-Sport & Rec Leagues", "role": "University Network", "city": "Toronto", "prov": "Ontario"},
    {"name": "York University Lions Athletics & Rec", "url": "https://yorkulions.ca", "sport": "Multi-Sport & Rec Leagues", "role": "University Network", "city": "Toronto", "prov": "Ontario"},
    {"name": "Waterloo Warriors Athletics & Rec", "url": "https://athletics.uwaterloo.ca", "sport": "Multi-Sport & Rec Leagues", "role": "University Network", "city": "Waterloo", "prov": "Ontario"},
    # Basketball
    {"name": "Ontario Basketball", "url": "https://basketball.on.ca", "sport": "Basketball", "role": "Sports Organization", "city": "Toronto", "prov": "Ontario"},
    {"name": "HoopDome Toronto", "url": "https://hoopdome.com", "sport": "Basketball", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    # Soccer
    {"name": "Footy Sevens Toronto", "url": "https://www.footysevens.com", "sport": "Soccer", "role": "Rec League", "city": "Toronto", "prov": "Ontario"},
    {"name": "Ontario Soccer", "url": "https://www.ontariosoccer.net", "sport": "Soccer", "role": "Sports Organization", "city": "Vaughan", "prov": "Ontario"},
    {"name": "North Toronto Soccer Club", "url": "https://ntsoccer.com", "sport": "Soccer", "role": "Sports Club / Run Club", "city": "Toronto", "prov": "Ontario"},
    # Volleyball
    {"name": "Ontario Volleyball Association", "url": "https://www.ontariovolleyball.org", "sport": "Volleyball", "role": "Sports Organization", "city": "Toronto", "prov": "Ontario"},
    {"name": "North Beach Volleyball", "url": "https://northbeachvolleyball.com", "sport": "Volleyball", "role": "Rec League", "city": "Toronto", "prov": "Ontario"},
    {"name": "Beach Blast Toronto", "url": "https://www.beachblast.ca", "sport": "Volleyball", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    # Tennis & Pickleball
    {"name": "Fairgrounds Public Racket Club", "url": "https://visitfairgrounds.com", "sport": "Tennis & Pickleball", "role": "Sports Club / Run Club", "city": "Toronto", "prov": "Ontario"},
    {"name": "Ontario Tennis Association", "url": "https://www.tennisontario.com", "sport": "Tennis & Pickleball", "role": "Sports Organization", "city": "Toronto", "prov": "Ontario"},
    {"name": "Pickleball Ontario", "url": "https://pickleballontario.org", "sport": "Tennis & Pickleball", "role": "Sports Organization", "city": "Toronto", "prov": "Ontario"},
    {"name": "Mayfair Clubs Toronto", "url": "https://www.mayfairclubs.com", "sport": "Tennis & Pickleball", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    # Flag Football & Turf Sports
    {"name": "Toronto Ultimate Club", "url": "https://www.tuc.org", "sport": "Flag Football & Turf Sports", "role": "Sports Club / Run Club", "city": "Toronto", "prov": "Ontario"},
    {"name": "Toronto Nomads Rugby", "url": "https://www.torontonomads.com", "sport": "Flag Football & Turf Sports", "role": "Sports Club / Run Club", "city": "Toronto", "prov": "Ontario"},
    {"name": "Ontario Touch Football League", "url": "https://otfl.ca", "sport": "Flag Football & Turf Sports", "role": "Rec League", "city": "Toronto", "prov": "Ontario"},
    # Hockey & Ice Sports
    {"name": "True North Hockey Canada", "url": "https://www.truenorthhockey.com", "sport": "Hockey & Ice Sports", "role": "Rec League", "city": "Toronto", "prov": "Ontario"},
    {"name": "Hockey Toronto", "url": "https://www.hockeytoronto.com", "sport": "Hockey & Ice Sports", "role": "Rec League", "city": "Toronto", "prov": "Ontario"},
    {"name": "Canlan Sports", "url": "https://www.canlansports.com", "sport": "Hockey & Ice Sports", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    # Running & Run Clubs
    {"name": "BlackToe Running Toronto", "url": "https://www.blacktoerunning.com", "sport": "Running & Run Clubs", "role": "Sports Club / Run Club", "city": "Toronto", "prov": "Ontario"},
    {"name": "Culture Athletics", "url": "https://cultureathletics.com", "sport": "Running & Run Clubs", "role": "Sports Club / Run Club", "city": "Toronto", "prov": "Ontario"},
    {"name": "Parkdale Roadrunners", "url": "https://www.parkdaleroadrunners.com", "sport": "Running & Run Clubs", "role": "Sports Club / Run Club", "city": "Toronto", "prov": "Ontario"},
    {"name": "Canada Running Series", "url": "https://canadarunningseries.com", "sport": "Running & Run Clubs", "role": "Tournament Operator", "city": "Toronto", "prov": "Ontario"},
    {"name": "Toronto Marathon", "url": "https://www.torontomarathon.com", "sport": "Running & Run Clubs", "role": "Tournament Operator", "city": "Toronto", "prov": "Ontario"},
    # Baseball & Softball
    {"name": "Baseball Ontario", "url": "https://www.baseballontario.com", "sport": "Baseball & Softball", "role": "Sports Organization", "city": "Cambridge", "prov": "Ontario"},
    {"name": "Slo-Pitch National", "url": "https://www.slopitch.com", "sport": "Baseball & Softball", "role": "Tournament Operator", "city": "Toronto", "prov": "Ontario"},
    {"name": "Toronto Playgrounds Baseball", "url": "https://www.tpbaseball.ca", "sport": "Baseball & Softball", "role": "Sports Club / Run Club", "city": "Toronto", "prov": "Ontario"},
    # Golf
    {"name": "Golf Ontario", "url": "https://gao.ca", "sport": "Golf", "role": "Sports Organization", "city": "Uxbridge", "prov": "Ontario"},
    {"name": "Tracer Golf Toronto", "url": "https://tracergolf.ca", "sport": "Golf", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    # Fitness & Cross-Training
    {"name": "CrossFit Toronto", "url": "https://www.crossfittoronto.com", "sport": "Fitness & Cross-Training", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    {"name": "Academy of Lions", "url": "https://www.academyoflions.com", "sport": "Fitness & Cross-Training", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    {"name": "Sweat and Tonic Toronto", "url": "https://www.sweatandtonic.com", "sport": "Fitness & Cross-Training", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    {"name": "Altea Active Toronto", "url": "https://alteaactive.com", "sport": "Fitness & Cross-Training", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    # Combat & Martial Arts
    {"name": "Toronto BJJ", "url": "https://www.torontobjj.com", "sport": "Combat & Martial Arts", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    {"name": "OpenMat MMA Toronto", "url": "https://www.openmat.ca", "sport": "Combat & Martial Arts", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    {"name": "Siam No. 1 Muay Thai Toronto", "url": "https://www.siamno1.com", "sport": "Combat & Martial Arts", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
    {"name": "Cabbagetown Boxing Club", "url": "https://www.cabbagetownboxing.com", "sport": "Combat & Martial Arts", "role": "Gym / Training Facility", "city": "Toronto", "prov": "Ontario"},
]

# ---------------------------------------------------------------------------
# Exclusions & Relevance Gates
# ---------------------------------------------------------------------------

_EXCLUDED_SLUGS = (
    "espn", "tsn", "sportsnet", "bleacherreport", "houseofhighlights", "barstool",
    "overtime", "nbcsports", "cbssports", "foxsports", "skysports", "dazn",
    "draftkings", "fanduel", "betmgm", "bet365", "caesars", "prizepicks", "underdogfantasy",
    "nike", "adidas", "puma", "underarmour", "lululemon", "gymshark", "sportchek",
    "footlocker", "dickssportinggoods", "decathlon", "gatorade", "redbull",
    "nba", "nfl", "nhl", "mlb", "mls", "ufc", "wwe", "fifa", "pgatour",
    "cbcnews", "ctvnews", "globalnews", "cp24", "bbcnews", "cnn", "abcnews",
    "cbsnews", "nbcnews", "foxnews", "6ixbuzz", "blogto", "narcity",
)

_NON_TARGET_COUNTRIES = {
    "india", "pakistan", "bangladesh", "indonesia", "vietnam", "philippines",
    "nigeria", "brazil", "russia", "ukraine", "egypt", "morocco", "turkey",
    "mexico", "colombia", "argentina", "peru", "thailand", "malaysia",
}

_GAMING_OR_BETTING_RE = re.compile(
    r"\b(nba\s*2k|2k\d{2}|ea\s*fc|fifa\s*\d{2}|madden\s*\d{2}|nhl\s*\d{2}|mlb\s*the\s*show|"
    r"esports|gaming\s*channel|gamer|mycareer|mypark|parlay|sports\s*betting|betting\s*picks|sportsbook|casino|odds)\b",
    re.IGNORECASE,
)

_OFF_TOPIC_CHANNEL_RE = re.compile(
    r"\b(true crime|homicide|suicide|police misconduct|guided meditation|meditations for|anxious mind|"
    r"astrology|tarot|crypto|forex|day trading|real estate investing|asmr|"
    r"former congresswoman|congresswoman|senator|marketplace host|npr|political analyst|u\.s\. representative)\b",
    re.IGNORECASE,
)

_SPORTS_RELEVANCE_RE = re.compile(
    r"\b(basketball|hoops|streetball|soccer|futsal|footy|volleyball|beach volleyball|"
    r"tennis|pickleball|padel|squash|badminton|flag football|touch football|ultimate frisbee|"
    r"rugby|lacrosse|hockey|shinny|skating|running|run club|run crew|marathon|5k|10k|trail|"
    r"baseball|softball|slowpitch|slo-pitch|golf|hyrox|crossfit|bootcamp|calisthenics|"
    r"boxing|kickboxing|muay thai|muay|bjj|jiu-jitsu|jiu jitsu|mma|wrestling|martial arts|"
    r"dodgeball|kickball|rec league|pickup|drop-in|intramural|athletics|strava|sport|fitness|trainer)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Strict Verified Email Extraction & Platform/SaaS/Sponsor Rejection
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,10})\b")
_BAD_EMAIL_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js",
    ".woff", ".woff2", ".ttf", ".ico", ".mp4", ".mp3", ".pdf", ".json",
)
_BAD_EMAIL_DOMAINS = (
    # Social, community & link-in-bio platforms
    "youtube.com", "google.com", "gstatic.com", "linktr.ee", "beacons.ai",
    "stan.store", "hoo.be", "campsite.bio", "bio.site", "lnk.bio", "carrd.co",
    "komi.io", "solo.to", "taplink.cc", "instagram.com", "facebook.com",
    "tiktok.com", "twitter.com", "x.com", "twitch.tv", "bsky.app", "bsky.social",
    "pinterest.com", "pinterest.ca", "threads.net", "threads.com",
    "linkedin.com", "reddit.com", "strava.com", "meetup.com", "eventbrite.com",
    "eventbrite.ca",
    # Website builders, hosting, CMS, analytics, cookie/legal, music & SaaS platforms
    "wix.com", "wixpress.com", "squarespace.com", "shopify.com", "shopify.ca",
    "myshopify.com", "wordpress.org", "wordpress.com", "wpengine.com",
    "elementor.com", "godaddy.com", "bluehost.com", "cloudflare.com",
    "webflow.com", "weebly.com", "ghost.org", "ghost.io", "kajabi.com",
    "teachable.com", "gumroad.com", "skool.com", "patreon.com", "substack.com",
    "sentry.io", "mailchimp.com", "convertkit.com", "kit.com", "beehiiv.com",
    "hubspot.com", "calendly.com", "stripe.com", "paypal.com", "zendesk.com",
    "intercom.io", "termly.io", "iubenda.com", "cookiebot.com", "onetrust.com",
    "epidemicsound.com", "artlist.io", "musicbed.com", "soundstripe.com",
    "canva.com", "adobe.com", "gravatar.com", "schema.org", "w3.org",
    "amazonaws.com", "mutiny.app", "creator-spring.com", "teespring.com",
    "bonfire.com", "fourthwall.com", "redbubble.com", "etsy.com",
    # Sports league/gym SaaS platforms (never partner personal/org outreach)
    "teamsnap.com", "leagueapps.com", "courtreserve.com", "mindbodyonline.com",
    "mindbody.io", "raceroster.com", "runsignup.com", "sportsengine.com",
    "amilia.com", "ezfacility.com", "active.com", "clubready.com",
    "glofox.com", "zenplanner.com", "pushpress.com", "wodify.com",
    "opensports.net", "playyon.com", "teamlinkt.com", "sportsillustrated.com",
    # Major sports retail, gear, supplement & betting sponsor brands + affiliate trackers
    "nike.com", "adidas.com", "lululemon.com", "gymshark.com", "underarmour.com",
    "puma.com", "reebok.com", "newbalance.com", "asics.com", "hoka.com",
    "on-running.com", "runna.com", "gatorade.com", "lmnt.com", "drinklmnt.com", "whoop.com",
    "garmin.com", "fitbit.com", "oura.com", "peloton.com", "roguefitness.com",
    "wilson.com", "babolat.com", "selkirk.com", "joola.com", "taylormade.com",
    "callawaygolf.com", "titleist.com", "sportchek.ca", "runningroom.com",
    "decathlon.com", "draftkings.com", "fanduel.com", "betmgm.com", "bet365.com",
    "nordvpn.com", "betterhelp.com", "ag1.com", "drinkag1.com", "amazon.com",
    "amazon.ca", "walmart.com", "gopjn.com", "pjatr.com", "pjtra.com",
    "pntra.com", "pntrac.com", "avantlink.com", "shareasale.com", "awin1.com",
    "howl.me", "sjv.io", "pxf.io", "dpbolvw.net", "tkqlhce.com", "jdoqocy.com",
    "anrdoezrs.net",
    # Placeholders
    "example.com", "example.org", "domain.com", "email.com",
    "yourdomain.com", "yoursite.com", "company.com", "test.com", "localhost",
)

_BAD_EMAIL_LOCAL_PARTS = {
    "noreply", "no-reply", "donotreply", "do-not-reply", "mailer-daemon",
    "postmaster", "webmaster", "hostmaster", "abuse", "dmca", "privacy",
    "dataprotection", "gdpr", "security", "legal", "copyright",
    "accessibility", "unsubscribe", "notifications", "alerts", "billing",
    "accounts", "careers", "jobs", "hr", "spam", "root", "admin",
    "wordpress", "test", "user", "name", "yourname", "you", "email",
    "someone", "example", "sample", "filler", "placeholder", "sentry",
}

_PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.ca", "outlook.com", "hotmail.com",
    "icloud.com", "me.com", "live.com", "aol.com", "proton.me",
    "protonmail.com", "msn.com", "rogers.com", "shaw.ca", "telus.net",
    "bell.net", "sympatico.ca",
}

_OUTREACH_CONTEXT_RE = re.compile(
    r"\b(business|inquir\w*|collab\w*|partner\w*|sponsor\w*|management|agency|talent|media|booking|press|contact|email|reach|work with|league|register|info|join)\b",
    re.IGNORECASE,
)
_FALSE_CONTEXT_RE = re.compile(
    r"\b(music by|music license|licensed by|theme by|powered by|built by|designed by|cookie policy|privacy policy|terms of service|terms of use|affiliate program terms|website by)\b",
    re.IGNORECASE,
)

_AFFILIATE_OR_RETAIL_HOSTS = (
    "amazon.", "amzn.", "amzlink.", "geni.us", "nike.", "adidas.", "lululemon.",
    "gymshark.", "underarmour.", "sportchek.", "runningroom.", "decathlon.",
    "kit.co", "rstyle.me", "liketk.it", "patreon.com", "buymeacoffee.com",
    "ko-fi.com", "paypal.", "venmo.com", "cash.app", "discord.gg", "discord.com",
    "youtube.com", "youtu.be", "bit.ly", "tinyurl.com", "goo.gl", "twitch.tv",
    "instagram.com", "tiktok.com", "facebook.com", "fb.com", "twitter.com",
    "x.com", "bsky.app", "pinterest.", "linkedin.com", "threads.net",
    "threads.com", "reddit.com", "strava.com", "meetup.com", "eventbrite.",
    "creator-spring.com", "teespring.com", "bonfire.com", "fourthwall.com",
    "spreadshop.com", "redbubble.com", "etsy.com", "shopltk.com", "shopmy.us",
    "ltk.app", "gopjn.com", "pjatr.com", "pjtra.com", "pntra.com",
    "pntrac.com", "avantlink.com", "shareasale.com", "awin1.com", "howl.me",
    "sjv.io", "pxf.io", "dpbolvw.net", "tkqlhce.com", "jdoqocy.com",
    "anrdoezrs.net", "draftkings.", "fanduel.", "betmgm.",
)

_LINK_HUB_HOSTS = (
    "linktr.ee", "beacons.ai", "stan.store", "bio.site", "linkin.bio",
    "solo.to", "taplink.cc", "campsite.bio", "hoo.be", "msha.ke",
    "carrd.co", "direct.me", "lnk.bio", "komi.io", "allmylinks.com",
)


def _root_domain(host_or_url: str) -> str:
    s = (host_or_url or "").strip().lower()
    if "://" in s:
        s = (urlparse(s).netloc or "").lower()
    s = s.split(":")[0].lstrip(".")
    if s.startswith("www."):
        s = s[4:]
    parts = [p for p in s.split(".") if p]
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "edu", "gov") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return s


def _decode_cfemail(hex_str: str) -> str:
    """Decode Cloudflare [data-cfemail] obfuscated email addresses."""
    clean = (hex_str or "").strip()
    if len(clean) < 4 or len(clean) % 2 != 0:
        return ""
    try:
        key = int(clean[:2], 16)
        return "".join(chr(int(clean[i:i + 2], 16) ^ key) for i in range(2, len(clean), 2)).strip()
    except Exception:
        return ""


def _is_valid_outreach_email(email_addr: str) -> bool:
    el = (email_addr or "").lower().strip().strip(".,;:<>()[]\"'")
    if "@" not in el or any(el.endswith(ext) for ext in _BAD_EMAIL_EXTENSIONS):
        return False
    local, dom = el.split("@", 1)
    if not local or not dom or "." not in dom or len(local) > 64 or len(el) > 120:
        return False
    if local in _BAD_EMAIL_LOCAL_PARTS or local.startswith(("noreply", "no-reply", "donotreply")):
        return False
    if re.match(r"^\d+x$", local) or re.match(r"^[0-9a-f]{16,}$", local):
        return False
    if any(dom == bad or dom.endswith("." + bad) for bad in _BAD_EMAIL_DOMAINS):
        return False
    return True


def _extract_clean_emails(
    text: str,
    allowed_site_domain: str = "",
    require_context_for_third_party: bool = False,
    explicit_mailto: bool = False,
) -> List[str]:
    """
    Extract verified business/outreach emails while rejecting platform, SaaS,
    league-software, sports-sponsor, hex-hash, placeholder, and asset filenames.
    """
    out: List[str] = []
    if not text:
        return out
    unescaped = urllib.parse.unquote(html_lib.unescape(text))
    cleaned_src = re.sub(r"(?:\\?u003[ce]|\\?u0026|\\?u002f|mailto:)", " ", unescaped, flags=re.IGNORECASE)
    cleaned_src = re.sub(r"\s*(?:\[\s*at\s*\]|\(\s*at\s*\))\s*", "@", cleaned_src, flags=re.IGNORECASE)
    cleaned_src = re.sub(r"\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\))\s*", ".", cleaned_src, flags=re.IGNORECASE)
    allowed_root = _root_domain(allowed_site_domain) if allowed_site_domain else ""

    for m in _EMAIL_RE.finditer(cleaned_src):
        el = m.group(1).lower().strip()
        if not _is_valid_outreach_email(el):
            continue
        dom = el.split("@", 1)[1]
        dom_root = _root_domain(dom)
        if require_context_for_third_party and not explicit_mailto:
            is_own_or_personal = (
                dom in _PERSONAL_EMAIL_DOMAINS
                or dom_root in _PERSONAL_EMAIL_DOMAINS
                or (allowed_root and (dom_root == allowed_root or dom == allowed_root))
            )
            if not is_own_or_personal:
                win_start = max(0, m.start() - 140)
                win_end = min(len(cleaned_src), m.end() + 140)
                window = cleaned_src[win_start:win_end]
                if not _OUTREACH_CONTEXT_RE.search(window) or _FALSE_CONTEXT_RE.search(window):
                    continue
        if el not in out:
            out.append(el)
    return out


def _fetch_text(url: str, timeout: int = 7) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _parse_audience_count(sub_text: str) -> int:
    if not sub_text:
        return 0
    m = re.search(r"([\d.,]+)\s*([KMB])?", sub_text.strip(), re.IGNORECASE)
    if not m:
        return 0
    try:
        num = float(m.group(1).replace(",", ""))
    except ValueError:
        return 0
    suffix = (m.group(2) or "").upper()
    if suffix == "K":
        num *= 1_000
    elif suffix == "M":
        num *= 1_000_000
    elif suffix == "B":
        num *= 1_000_000_000
    return int(round(num))


def _normalize_social_url(raw_url: str, keep_query: bool = False) -> str:
    u = (raw_url or "").strip().strip(".,;:<>()[]\"'")
    if not u:
        return ""
    if not u.lower().startswith(("http://", "https://")):
        u = "https://" + u.lstrip("/")
    try:
        p = urlparse(u)
        if not p.netloc or "." not in p.netloc:
            return ""
        path = p.path.rstrip("/") or ""
        if not keep_query:
            return f"https://{p.netloc.lower()}{path}"
        return f"https://{p.netloc.lower()}{path}" + (f"?{p.query}" if p.query else "")
    except Exception:
        return ""


_ALL_SOCIAL_FIELDS = (
    "youtube_url", "instagram_url", "tiktok_url", "facebook_url", "x_url",
    "threads_url", "linkedin_url", "pinterest_url", "reddit_url",
    "strava_url", "bluesky_url", "meetup_url", "eventbrite_url",
)

_MEETUP_SKIP_PREFIXES = (
    "find", "topics", "cities", "about", "help", "login", "register",
    "lp", "blog", "pro", "apps", "privacy", "terms", "cookie",
)


def _classify_partner_links(raw_urls: List[str]) -> Dict[str, Any]:
    """Sort discovered external URLs into all 13 social/community profiles, link hubs, and website."""
    res: Dict[str, Any] = {k: "" for k in _ALL_SOCIAL_FIELDS}
    res["website"] = ""
    res["link_hubs"] = []

    for raw in raw_urls:
        norm = _normalize_social_url(raw)
        if not norm:
            continue
        try:
            host = (urlparse(norm).netloc or "").lower()
            path = (urlparse(norm).path or "").strip("/")
        except Exception:
            continue
        low_path = path.lower()
        if not path and any(
            s in host
            for s in (
                "youtube.", "instagram.", "tiktok.", "facebook.", "twitter.", "x.com",
                "threads.", "linkedin.", "pinterest.", "reddit.", "strava.", "meetup.", "bsky.",
            )
        ):
            continue

        if ("youtube.com" in host or host == "youtu.be") and not res["youtube_url"]:
            if low_path.startswith(("@", "channel/", "c/", "user/")) and low_path.strip("/") not in ("@meetup", "c/meetup", "user/meetup"):
                res["youtube_url"] = norm
        elif "instagram.com" in host and not res["instagram_url"]:
            first_seg = low_path.split("/")[0] if low_path else ""
            if first_seg != "meetup" and not any(low_path.startswith(skip) for skip in ("p/", "reel/", "explore/", "accounts/")):
                res["instagram_url"] = norm
        elif "tiktok.com" in host and not res["tiktok_url"]:
            first_seg = low_path.split("/")[0] if low_path else ""
            if first_seg != "@meetup" and not low_path.startswith(("discover/", "tag/", "music/")):
                res["tiktok_url"] = norm
        elif ("facebook.com" in host or "fb.com" in host) and not res["facebook_url"]:
            first_seg = low_path.split("/")[0] if low_path else ""
            if first_seg != "meetup" and not any(low_path.startswith(skip) for skip in ("sharer", "share.php", "privacy", "policies", "tr")):
                res["facebook_url"] = norm
        elif ("twitter.com" in host or host == "x.com" or host == "www.x.com") and not res["x_url"]:
            first_seg = low_path.split("/")[0] if low_path else ""
            if first_seg != "meetup" and not any(low_path.startswith(skip) for skip in ("intent/", "share", "search")):
                res["x_url"] = norm
        elif ("threads.net" in host or "threads.com" in host) and not res["threads_url"]:
            if "/post/" not in low_path and low_path.split("/")[0] != "@meetup":
                res["threads_url"] = norm
        elif "linkedin.com" in host and not res["linkedin_url"]:
            if low_path.startswith(("in/", "company/", "school/")) and not low_path.startswith("company/meetup"):
                res["linkedin_url"] = norm
        elif ("pinterest.com" in host or "pinterest.ca" in host) and not res["pinterest_url"]:
            if not any(low_path.startswith(skip) for skip in ("pin/", "search/", "_/", "ideas/")):
                res["pinterest_url"] = norm
        elif "reddit.com" in host and not res["reddit_url"]:
            if low_path.startswith(("u/", "user/", "r/")) and "/comments/" not in low_path:
                res["reddit_url"] = norm
        elif "strava.com" in host and not res["strava_url"]:
            if low_path.startswith(("clubs/", "athletes/")):
                res["strava_url"] = norm
        elif "bsky.app" in host and not res["bluesky_url"]:
            if low_path.startswith("profile/"):
                res["bluesky_url"] = norm
        elif "meetup.com" in host and not res["meetup_url"]:
            first_seg = low_path.split("/")[0] if low_path else ""
            if first_seg and first_seg not in _MEETUP_SKIP_PREFIXES:
                res["meetup_url"] = f"https://www.meetup.com/{path.split('/')[0]}"
        elif ("eventbrite.com" in host or "eventbrite.ca" in host) and not res["eventbrite_url"]:
            if low_path.startswith(("o/", "e/")) or (host not in ("www.eventbrite.com", "eventbrite.com", "www.eventbrite.ca", "eventbrite.ca")):
                res["eventbrite_url"] = norm
        elif any(hub in host for hub in _LINK_HUB_HOSTS):
            if norm not in res["link_hubs"]:
                res["link_hubs"].append(norm)
        elif not res["website"]:
            if not any(skip in host for skip in _AFFILIATE_OR_RETAIL_HOSTS):
                res["website"] = f"https://{host}" + (f"/{path}" if path and len(path) < 35 else "")

    return res


_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


def _parse_instagram_followers_html(raw_html: str) -> int:
    """Parse follower count from Instagram public og:description / meta HTML."""
    if not raw_html:
        return 0
    for pat in (
        r'([0-9][0-9.,]*\s*[KMB]?)\s+Followers',
        r'"edge_followed_by"\s*:\s*\{\s*"count"\s*:\s*(\d+)\s*\}',
    ):
        m = re.search(pat, raw_html, re.IGNORECASE)
        if m:
            val = _parse_audience_count(m.group(1))
            if val > 0:
                return val
    return 0


def _fetch_instagram_followers(instagram_url: str) -> int:
    if not instagram_url or "instagram.com/" not in instagram_url.lower():
        return 0
    try:
        path = (urlparse(instagram_url).path or "").strip("/")
        slug = path.split("/")[0] if path else ""
        if not slug or slug.lower() in ("p", "reel", "explore", "accounts", "meetup"):
            return 0
        url = f"https://www.instagram.com/{slug}/"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "curl/8.4.0", "Accept-Language": "en-US,en;q=0.9"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        return _parse_instagram_followers_html(body)
    except Exception:
        return 0


def _parse_tiktok_followers_html(raw_html: str) -> int:
    """Parse followerCount from TikTok mobile profile HTML."""
    if not raw_html:
        return 0
    m = re.search(r'"followerCount"\s*:\s*(\d+)', raw_html)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return 0
    return 0


def _fetch_tiktok_followers(tiktok_url: str) -> int:
    if not tiktok_url or "tiktok.com/" not in tiktok_url.lower():
        return 0
    try:
        path = (urlparse(tiktok_url).path or "").strip("/")
        handle = path.split("/")[0] if path else ""
        if not handle or handle.lower() in ("discover", "tag", "music", "@meetup"):
            return 0
        if not handle.startswith("@"):
            handle = "@" + handle
        url = f"https://www.tiktok.com/{handle}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": _MOBILE_UA, "Accept-Language": "en-US,en;q=0.9"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        return _parse_tiktok_followers_html(body)
    except Exception:
        return 0


def populate_partner_follower_counts(partner: Dict[str, Any]) -> Dict[str, Any]:
    """
    Populate per-platform follower counts (YouTube, Instagram, TikTok, Bluesky, Meetup)
    and recompute combined audience_count.
    """
    updated = dict(partner)
    prim = (updated.get("primary_platform") or "").lower()
    raw_aud = int(updated.get("audience_count") or 0)

    yt_f = int(updated.get("youtube_followers") or (raw_aud if prim == "youtube" else 0))
    ig_f = int(updated.get("instagram_followers") or 0)
    tt_f = int(updated.get("tiktok_followers") or 0)
    bs_f = int(updated.get("bluesky_followers") or (raw_aud if prim == "bluesky" else 0))
    mu_m = int(updated.get("meetup_members") or (raw_aud if prim == "meetup" else 0))

    ig_url = (updated.get("instagram_url") or "").strip()
    tt_url = (updated.get("tiktok_url") or "").strip()
    if ig_url and ig_f <= 0:
        ig_f = _fetch_instagram_followers(ig_url)
    if tt_url and tt_f <= 0:
        tt_f = _fetch_tiktok_followers(tt_url)

    total = yt_f + ig_f + tt_f + bs_f + mu_m
    updated["youtube_followers"] = yt_f
    updated["instagram_followers"] = ig_f
    updated["tiktok_followers"] = tt_f
    updated["bluesky_followers"] = bs_f
    updated["meetup_members"] = mu_m
    updated["audience_count"] = max(total, raw_aud)
    return updated


def _is_excluded_slug(name: str, handle: str) -> bool:
    slug = re.sub(r"[^a-z0-9]", "", f"{name} {handle}".lower())
    return any(ex in slug for ex in _EXCLUDED_SLUGS)


def extract_visible_text_from_html(raw_html: str) -> str:
    """Strip scripts/styles/tags from HTML so geo & email extraction only scans visible page copy."""
    if not raw_html:
        return ""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "head"]):
            tag.decompose()
        return " ".join(soup.get_text(" ", strip=True).split())[:9000]
    except Exception:
        cleaned = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html, flags=re.I | re.S)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        return " ".join(cleaned.split())[:9000]


def _extract_html_title_and_meta(raw_html: str) -> Tuple[str, str]:
    """Extract clean page <title> and meta description for curated organization pages."""
    if not raw_html:
        return "", ""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html, "html.parser")
        title_txt = (soup.title.get_text(" ", strip=True) if soup.title else "").strip()
        meta_desc = ""
        for m in soup.find_all("meta"):
            if (m.get("name") or "").lower() in ("description", "og:description") or (m.get("property") or "").lower() == "og:description":
                val = (m.get("content") or "").strip()
                if val:
                    meta_desc = val
                    break
        return title_txt[:150], meta_desc[:450]
    except Exception:
        return "", ""


_SOCIAL_URL_SCAN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:"
    r"linktr\.ee|beacons\.ai|stan\.store|bio\.site|linkin\.bio|solo\.to|taplink\.cc|"
    r"campsite\.bio|hoo\.be|msha\.ke|carrd\.co|direct\.me|lnk\.bio|komi\.io|allmylinks\.com|"
    r"youtube\.com/(?:@|channel/|c/|user/)|"
    r"instagram\.com|tiktok\.com|facebook\.com|fb\.com|twitter\.com|x\.com|threads\.net|threads\.com|"
    r"linkedin\.com|pinterest\.com|pinterest\.ca|reddit\.com|"
    r"strava\.com/(?:clubs|athletes)|bsky\.app/profile|meetup\.com|eventbrite\.(?:com|ca)"
    r")/[A-Za-z0-9._/@%+-]+",
    re.IGNORECASE,
)

_CONTACT_NAV_WORDS = (
    "contact", "about", "work-with", "partner", "sponsor", "advertise",
    "media-kit", "mediakit", "collab", "press", "inquiry", "inquiries",
    "league", "club", "join", "team",
)


def _merge_socials_into(target: Dict[str, Any], raw_urls: List[str]) -> None:
    if not raw_urls:
        return
    extra = _classify_partner_links(raw_urls)
    for k in _ALL_SOCIAL_FIELDS:
        if not target.get(k) and extra.get(k):
            target[k] = extra[k]
    for hub in extra.get("link_hubs") or []:
        if hub not in target.setdefault("link_hubs", []):
            target["link_hubs"].append(hub)
    if not target.get("website") and extra.get("website"):
        target["website"] = extra["website"]


def _parse_html_page_signals(
    raw_html: str,
    page_url: str = "",
    allowed_site_domain: str = "",
    require_context_for_third_party: bool = False,
) -> Tuple[List[str], List[str], str, List[str]]:
    """Extract verified emails (mailto/cfemail/visible text), social/community URLs, visible text, and same-site contact links."""
    visible_text = extract_visible_text_from_html(raw_html)
    emails: List[str] = []
    social_urls: List[str] = []
    nav_candidates: List[str] = []

    base_root = _root_domain(page_url) if page_url else ""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            low_href = href.lower()
            if low_href.startswith("mailto:"):
                for em in _extract_clean_emails(href, allowed_site_domain=allowed_site_domain, explicit_mailto=True):
                    if em not in emails:
                        emails.append(em)
                continue
            if _SOCIAL_URL_SCAN_RE.search(href):
                social_urls.append(href)
                continue
            if page_url and base_root:
                link_text = (a.get_text(" ", strip=True) or "").lower()
                if any(tok in low_href or tok in link_text for tok in _CONTACT_NAV_WORDS):
                    full_url = urljoin(page_url, href).split("#")[0].rstrip("/")
                    if full_url.startswith(("http://", "https://")) and _root_domain(full_url) == base_root:
                        if full_url not in nav_candidates:
                            nav_candidates.append(full_url)
        for el in soup.select("[data-cfemail]"):
            decoded = _decode_cfemail(el.get("data-cfemail", ""))
            if decoded and _is_valid_outreach_email(decoded) and decoded.lower() not in emails:
                emails.append(decoded.lower())
    except Exception:
        pass

    for em in _extract_clean_emails(
        visible_text,
        allowed_site_domain=allowed_site_domain,
        require_context_for_third_party=require_context_for_third_party,
    ):
        if em not in emails:
            emails.append(em)

    for m_href in re.findall(r'mailto:([^\s"\'<>?]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,10})', raw_html, re.IGNORECASE):
        decoded_href = urllib.parse.unquote(m_href).strip()
        if _is_valid_outreach_email(decoded_href) and decoded_href.lower() not in emails:
            emails.append(decoded_href.lower())

    for s_url in _SOCIAL_URL_SCAN_RE.findall(raw_html):
        if s_url not in social_urls:
            social_urls.append(s_url)

    return emails, social_urls, visible_text, nav_candidates


def _extract_page_signals(
    url: str,
    timeout: int = 5,
    allowed_site_domain: str = "",
    require_context_for_third_party: bool = False,
) -> Tuple[List[str], List[str], str]:
    try:
        raw_html = _fetch_text(url, timeout=timeout)
    except Exception:
        return [], [], ""
    emails, social_urls, visible_text, _ = _parse_html_page_signals(
        raw_html,
        page_url=url,
        allowed_site_domain=allowed_site_domain,
        require_context_for_third_party=require_context_for_third_party,
    )
    return emails, social_urls, visible_text


def _crawl_partner_website(
    website_url: str,
    need_email: bool = True,
    need_geo: bool = True,
) -> Tuple[List[str], List[str], str, str]:
    """
    Crawl partner homepage plus up to 4 verified contact/about/partnership subpages.
    Returns (emails, social_urls, geo_text, meta_description).
    """
    norm_home = _normalize_social_url(website_url)
    if not norm_home:
        return [], [], "", ""
    parsed_home = urlparse(norm_home)
    base_root = _root_domain(parsed_home.netloc)
    origin = f"{parsed_home.scheme}://{parsed_home.netloc}"

    emails: List[str] = []
    socials: List[str] = []
    geo_chunks: List[str] = []
    visited = set()
    meta_desc = ""

    def _absorb(page_url: str, raw_html: str) -> List[str]:
        pe, ps, pt, pnav = _parse_html_page_signals(
            raw_html,
            page_url=page_url,
            allowed_site_domain=base_root,
            require_context_for_third_party=True,
        )
        for em in pe:
            if em not in emails:
                emails.append(em)
        for su in ps:
            if su not in socials:
                socials.append(su)
        if pt:
            geo_chunks.append(pt)
        return pnav

    nav_links: List[str] = []
    home_key = norm_home.rstrip("/")
    visited.add(home_key)
    try:
        home_html = _fetch_text(norm_home, timeout=6)
        _, meta_desc = _extract_html_title_and_meta(home_html)
        nav_links = _absorb(norm_home, home_html)
    except Exception:
        pass

    if not need_email and geo_chunks and not need_geo:
        return emails, socials, "\n".join(geo_chunks)[:10000], meta_desc

    fallback_paths = (
        "/contact", "/contact-us", "/about", "/about-us",
        "/work-with-me", "/partnerships", "/sponsors", "/leagues", "/clubs",
    )
    candidates: List[str] = []
    for cand in list(nav_links) + [origin + p for p in fallback_paths]:
        ckey = cand.rstrip("/")
        if ckey not in visited and ckey not in candidates:
            candidates.append(ckey)

    subpages_checked = 0
    for sub_url in candidates:
        if subpages_checked >= 4 or (emails and not need_geo):
            break
        if emails and geo_chunks and len(socials) >= 2:
            break
        visited.add(sub_url)
        subpages_checked += 1
        try:
            sub_html = _fetch_text(sub_url, timeout=4)
            _absorb(sub_url, sub_html)
        except Exception:
            continue

    return emails, socials, "\n".join(geo_chunks)[:10000], meta_desc


def _fetch_youtube_recent_video_signals(nav_url: str, site_domain: str = "") -> Tuple[List[str], List[str], str]:
    """Check up to 2 recent video descriptions for business email, link hubs, Strava/Meetup/Eventbrite & geo."""
    if not nav_url:
        return [], [], ""
    emails: List[str] = []
    social_urls: List[str] = []
    desc_chunks: List[str] = []
    try:
        vhtml = _fetch_text(f"https://www.youtube.com{nav_url}/videos", timeout=6)
    except Exception:
        return [], [], ""

    vid_ids: List[str] = []
    for vid in re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', vhtml):
        if vid not in vid_ids:
            vid_ids.append(vid)
        if len(vid_ids) >= 2:
            break

    for vid in vid_ids:
        try:
            whtml = _fetch_text(f"https://www.youtube.com/watch?v={vid}", timeout=6)
        except Exception:
            continue
        m = re.search(r'"shortDescription":"((?:\\.|[^"\\])*)"', whtml)
        if not m:
            continue
        try:
            desc = json.loads('"' + m.group(1) + '"')
        except Exception:
            desc = ""
        if not desc:
            continue
        desc_chunks.append(desc[:2500])
        for em in _extract_clean_emails(desc, allowed_site_domain=site_domain, require_context_for_third_party=True):
            if em not in emails:
                emails.append(em)
        for su in _SOCIAL_URL_SCAN_RE.findall(desc):
            if su not in social_urls:
                social_urls.append(su)
        if emails and social_urls:
            break

    return emails, social_urls, "\n".join(desc_chunks)[:5000]


# ---------------------------------------------------------------------------
# Channel 1: YouTube Sports Creators, Pickup Hosts & Leagues
# ---------------------------------------------------------------------------

def _search_youtube_seed(
    query: str,
    default_sport: str,
    seed_partner_type: str,
    seed_partner_role: str,
) -> List[Dict[str, str]]:
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    try:
        html = _fetch_text(url, timeout=9)
    except Exception:
        return []

    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except Exception:
        return []

    found: Dict[str, Dict[str, str]] = {}

    def _add_candidate(name: str, nav_url: str, title_hint: str = "") -> None:
        if not name or not nav_url:
            return
        if not (nav_url.startswith("/@") or nav_url.startswith("/channel/")):
            return
        if _is_excluded_slug(name, nav_url):
            return
        if _GAMING_OR_BETTING_RE.search(f"{name} {title_hint}") or _OFF_TOPIC_CHANNEL_RE.search(f"{name} {title_hint}"):
            return
        if nav_url not in found:
            found[nav_url] = {
                "nav_url": nav_url,
                "name": name,
                "default_sport": default_sport,
                "seed_topic": query,
                "video_title": title_hint,
                "seed_partner_type": seed_partner_type,
                "seed_partner_role": seed_partner_role,
            }

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            vr = obj.get("videoRenderer")
            if isinstance(vr, dict):
                vtitle = "".join(r.get("text", "") for r in ((vr.get("title") or {}).get("runs") or []))
                runs = (vr.get("ownerText") or {}).get("runs") or []
                if runs:
                    name = (runs[0].get("text") or "").strip()
                    nav_url = (
                        ((runs[0].get("navigationEndpoint") or {}).get("commandMetadata") or {})
                        .get("webCommandMetadata", {})
                        .get("url", "")
                    )
                    _add_candidate(name, nav_url, vtitle)
            cr = obj.get("channelRenderer")
            if isinstance(cr, dict):
                name = ((cr.get("title") or {}).get("simpleText") or "").strip()
                nav_url = (
                    ((cr.get("navigationEndpoint") or {}).get("commandMetadata") or {})
                    .get("webCommandMetadata", {})
                    .get("url", "")
                )
                _add_candidate(name, nav_url)
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(data)
    return list(found.values())[:9]


def _fetch_youtube_partner_profile(seed: Dict[str, str]) -> Optional[Dict[str, Any]]:
    nav_url = seed["nav_url"]
    about_url = f"https://www.youtube.com{nav_url}/about"
    try:
        raw_about_html = _fetch_text(about_url, timeout=9)
    except Exception:
        return None

    m = re.search(r"var ytInitialData = (\{.*?\});</script>", raw_about_html)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except Exception:
        return None

    about: Dict[str, Any] = {}

    def find_about(obj: Any) -> None:
        if isinstance(obj, dict):
            if "aboutChannelViewModel" in obj:
                about.update(obj["aboutChannelViewModel"])
            for v in obj.values():
                find_about(v)
        elif isinstance(obj, list):
            for x in obj:
                find_about(x)

    find_about(data)
    if not about:
        return None

    country = (about.get("country") or "").strip()
    if country.lower() in _NON_TARGET_COUNTRIES:
        return None

    desc = (about.get("description") or "").strip()
    if re.search(r"[\u0900-\u097f\u0600-\u06ff\u0400-\u04ff]", f"{seed['name']} {desc}"):
        return None
    if _GAMING_OR_BETTING_RE.search(f"{seed['name']} {desc}") or _OFF_TOPIC_CHANNEL_RE.search(f"{seed['name']} {desc}"):
        return None
    if not _SPORTS_RELEVANCE_RE.search(f"{seed['name']} {desc}") and not (
        len(desc) < 40 and _SPORTS_RELEVANCE_RE.search(seed.get("video_title", ""))
    ):
        return None

    sub_text = (about.get("subscriberCountText") or "").strip()
    sub_count = _parse_audience_count(sub_text)
    is_local_or_org = (
        country.lower() == "canada"
        or seed.get("seed_partner_type") == "sports_org"
        or bool(re.search(r"\b(toronto|gta|ontario|canada|vancouver|montreal|calgary|ottawa|league|club|pickup)\b", f"{seed['name']} {desc}", re.IGNORECASE))
    )
    min_subs = 50 if is_local_or_org else 500
    if 0 < sub_count < min_subs:
        return None

    _SPONSOR_LINK_TITLE_RE = re.compile(
        r"(%\s*off|use code|promo code|discount|coupon|sponsor|affiliate)",
        re.IGNORECASE,
    )
    raw_links: List[str] = []
    for l in (about.get("links") or []):
        vm = l.get("channelExternalLinkViewModel") or {}
        url_val = (vm.get("link") or {}).get("content", "")
        title_val = (vm.get("title") or {}).get("content", "")
        if not url_val:
            continue
        if _SPONSOR_LINK_TITLE_RE.search(title_val) and not _SOCIAL_URL_SCAN_RE.match(url_val):
            continue
        raw_links.append(url_val)
    raw_links.extend(_SOCIAL_URL_SCAN_RE.findall(desc))

    socials = _classify_partner_links([u for u in raw_links if u])
    site_domain = _root_domain(socials["website"]) if socials.get("website") else ""
    emails = _extract_clean_emails(desc, allowed_site_domain=site_domain, require_context_for_third_party=False)
    extra_geo_chunks: List[str] = []

    # 1. Linktree / Beacons / Stan.store / Hoo.be / Carrd
    for hub_url in socials["link_hubs"][:2]:
        hub_emails, hub_socials, hub_text = _extract_page_signals(
            hub_url, timeout=5, allowed_site_domain=site_domain, require_context_for_third_party=False
        )
        if hub_text:
            extra_geo_chunks.append(hub_text)
        for em in hub_emails:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, hub_socials)
        if not site_domain and socials.get("website"):
            site_domain = _root_domain(socials["website"])

    # 2. Recent video descriptions when email or social coverage is still thin
    if not emails or not socials.get("website") or not socials.get("instagram_url"):
        vid_emails, vid_socials, vid_text = _fetch_youtube_recent_video_signals(nav_url, site_domain=site_domain)
        if vid_text:
            extra_geo_chunks.append(vid_text)
        for em in vid_emails:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, vid_socials)
        if not site_domain and socials.get("website"):
            site_domain = _root_domain(socials["website"])

    # 3. Deep crawl personal / org website (+ /contact, /about, /partnerships)
    if socials["website"] and (not emails or country in ("", "United States", "Canada")):
        site_emails, site_socials, site_text, _ = _crawl_partner_website(
            socials["website"],
            need_email=not bool(emails),
            need_geo=country in ("", "United States", "Canada"),
        )
        if site_text:
            extra_geo_chunks.append(site_text)
        for em in site_emails:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, site_socials)

    handle = nav_url.lstrip("/")
    slug_id = re.sub(r"[^A-Za-z0-9_-]", "_", handle)
    canonical_yt = f"https://www.youtube.com{nav_url}"

    return populate_partner_follower_counts({
        "partner_id": f"yt_{slug_id}",
        "name": seed["name"],
        "handle": handle if handle.startswith("@") else f"@{slug_id}",
        "primary_platform": "youtube",
        "profile_url": canonical_yt,
        "country": country,
        "_extra_geo_text": "\n".join(extra_geo_chunks)[:12000],
        "audience_count": sub_count,
        "youtube_followers": sub_count,
        "audience_text": sub_text or (f"{sub_count:,} subscribers" if sub_count else "YouTube Channel"),
        "default_sport": seed["default_sport"],
        "seed_topic": seed["seed_topic"],
        "seed_partner_type": seed.get("seed_partner_type", ""),
        "seed_partner_role": seed.get("seed_partner_role", ""),
        "bio": re.sub(r"\s+", " ", desc)[:600],
        "business_email": ", ".join(emails[:2]),
        "website": socials["website"] or (socials["link_hubs"][0] if socials["link_hubs"] else ""),
        "youtube_url": canonical_yt,
        "instagram_url": socials["instagram_url"],
        "tiktok_url": socials["tiktok_url"],
        "facebook_url": socials["facebook_url"],
        "x_url": socials["x_url"],
        "threads_url": socials["threads_url"],
        "linkedin_url": socials["linkedin_url"],
        "pinterest_url": socials["pinterest_url"],
        "reddit_url": socials["reddit_url"],
        "strava_url": socials["strava_url"],
        "bluesky_url": socials["bluesky_url"],
        "meetup_url": socials["meetup_url"],
        "eventbrite_url": socials["eventbrite_url"],
    })


# ---------------------------------------------------------------------------
# Channel 2: Live Meetup Sports Organizers, Pickup Hosts & Clubs
# ---------------------------------------------------------------------------

def _search_meetup_seed(keyword: str, location: str, default_sport: str) -> List[Dict[str, Any]]:
    url = (
        f"https://www.meetup.com/find/?keywords={urllib.parse.quote(keyword)}"
        f"&location={urllib.parse.quote(location)}&source=GROUPS"
    )
    try:
        raw_html = _fetch_text(url, timeout=9)
    except Exception:
        return []

    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', raw_html)
    if not m:
        return []
    try:
        next_data = json.loads(m.group(1))
    except Exception:
        return []

    apollo = next_data.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
    out: List[Dict[str, Any]] = []
    for k, grp in apollo.items():
        if not (k.startswith("Group:") and isinstance(grp, dict)):
            continue
        name = (grp.get("name") or "").strip()
        link = (grp.get("link") or "").strip()
        desc = (grp.get("description") or "").strip()
        if not name or not link or "meetup.com/" not in link:
            continue
        if _is_excluded_slug(name, link) or _GAMING_OR_BETTING_RE.search(f"{name} {desc}"):
            continue
        if not _SPORTS_RELEVANCE_RE.search(f"{name} {desc}"):
            continue

        members = int(((grp.get("stats") or {}).get("memberCounts") or {}).get("all") or 0)
        if 0 < members < 20:
            continue

        slug = urlparse(link).path.strip("/").split("/")[0]
        if not slug:
            continue
        ctry_code = (grp.get("country") or "").lower()
        ctry = "Canada" if ctry_code == "ca" else ("United States" if ctry_code == "us" else "")
        out.append({
            "slug": slug,
            "name": name,
            "link": f"https://www.meetup.com/{slug}",
            "description": desc,
            "city": (grp.get("city") or "").strip(),
            "state": (grp.get("state") or "").strip(),
            "country": ctry,
            "members": members,
            "default_sport": default_sport,
            "seed_topic": keyword,
        })
    return out


def _enrich_meetup_group(grp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    link = grp["link"]
    desc = grp.get("description") or ""
    emails = _extract_clean_emails(desc, require_context_for_third_party=False)
    raw_urls = list(_SOCIAL_URL_SCAN_RE.findall(desc)) + re.findall(r"https?://[^\s)<\]\"']+", desc, re.IGNORECASE)
    extra_geo_chunks: List[str] = []

    try:
        grp_html = _fetch_text(link, timeout=7)
        pe, ps, pt, _ = _parse_html_page_signals(grp_html, page_url=link, require_context_for_third_party=True)
        for em in pe:
            if em not in emails:
                emails.append(em)
        raw_urls.extend(ps)
        if pt:
            extra_geo_chunks.append(pt[:3000])
    except Exception:
        pass

    socials = _classify_partner_links([u for u in raw_urls if u and "meetup.com" not in u.lower()])
    site_domain = _root_domain(socials["website"]) if socials.get("website") else ""

    for hub_url in socials["link_hubs"][:2]:
        he, hs, ht = _extract_page_signals(hub_url, timeout=5, allowed_site_domain=site_domain)
        if ht:
            extra_geo_chunks.append(ht)
        for em in he:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, hs)
        if not site_domain and socials.get("website"):
            site_domain = _root_domain(socials["website"])

    if socials["website"] and not emails:
        se, ss, st, _ = _crawl_partner_website(socials["website"], need_email=True, need_geo=False)
        if st:
            extra_geo_chunks.append(st)
        for em in se:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, ss)

    members = int(grp.get("members") or 0)
    slug = grp["slug"]
    return populate_partner_follower_counts({
        "partner_id": f"mu_{re.sub(r'[^A-Za-z0-9_-]', '_', slug)}",
        "name": grp["name"],
        "handle": f"meetup/{slug}",
        "primary_platform": "meetup",
        "profile_url": link,
        "country": grp.get("country") or "",
        "province_state": grp.get("state") or "",
        "city": grp.get("city") or "",
        "_extra_geo_text": "\n".join(extra_geo_chunks)[:8000],
        "audience_count": members,
        "meetup_members": members,
        "audience_text": f"{members:,} members" if members else "Meetup Group",
        "default_sport": grp["default_sport"],
        "seed_topic": grp["seed_topic"],
        "bio": re.sub(r"\s+", " ", desc)[:600],
        "business_email": ", ".join(emails[:2]),
        "website": socials["website"] or (socials["link_hubs"][0] if socials["link_hubs"] else ""),
        "youtube_url": socials["youtube_url"],
        "instagram_url": socials["instagram_url"],
        "tiktok_url": socials["tiktok_url"],
        "facebook_url": socials["facebook_url"],
        "x_url": socials["x_url"],
        "threads_url": socials["threads_url"],
        "linkedin_url": socials["linkedin_url"],
        "pinterest_url": socials["pinterest_url"],
        "reddit_url": socials["reddit_url"],
        "strava_url": socials["strava_url"],
        "bluesky_url": socials["bluesky_url"],
        "meetup_url": link,
        "eventbrite_url": socials["eventbrite_url"],
    })


def _scrape_meetup_sports_groups(
    existing_ids: Optional[Set[str]] = None,
    max_new_meetup: int = 30,
) -> List[Dict[str, Any]]:
    discovered: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(_search_meetup_seed, kw, loc, sp) for kw, loc, sp in MEETUP_SEARCH_SEEDS]
        for fut in as_completed(futs):
            try:
                for grp in fut.result():
                    pid = f"mu_{re.sub(r'[^A-Za-z0-9_-]', '_', grp['slug'])}"
                    if existing_ids and pid in existing_ids:
                        continue
                    discovered.setdefault(grp["slug"], grp)
            except Exception:
                pass

    targets = sorted(discovered.values(), key=lambda g: g.get("members", 0), reverse=True)[:max_new_meetup]
    results: List[Dict[str, Any]] = []
    if not targets:
        return results
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(_enrich_meetup_group, g) for g in targets]
        for fut in as_completed(futs):
            try:
                item = fut.result()
                if item:
                    results.append(item)
            except Exception:
                pass
    return results


# ---------------------------------------------------------------------------
# Channel 3: Live Bluesky Sports Creators & Communities
# ---------------------------------------------------------------------------

def _fetch_bluesky_partner(
    actor: Dict[str, Any],
    default_sport: str,
    seed_topic: str,
    seed_partner_type: str,
) -> Optional[Dict[str, Any]]:
    handle = (actor.get("handle") or "").strip()
    name = (actor.get("displayName") or handle).strip()
    bio = (actor.get("description") or "").strip()
    if not handle or _is_excluded_slug(name, handle):
        return None
    if _GAMING_OR_BETTING_RE.search(f"{name} {bio}") or _OFF_TOPIC_CHANNEL_RE.search(f"{name} {bio}"):
        return None
    if not _SPORTS_RELEVANCE_RE.search(f"{name} {bio}"):
        return None

    followers = 0
    try:
        prof_raw = _fetch_text(
            f"https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor={urllib.parse.quote(handle)}",
            timeout=5,
        )
        prof = json.loads(prof_raw)
        followers = int(prof.get("followersCount") or 0)
    except Exception:
        pass
    is_local = bool(re.search(r"\b(toronto|gta|ontario|canada|vancouver|montreal|calgary)\b", f"{name} {bio}", re.IGNORECASE))
    if 0 < followers < (50 if is_local else 150):
        return None

    emails = _extract_clean_emails(bio)
    raw_urls = re.findall(r"https?://[^\s)<\]\"']+", bio, re.IGNORECASE)
    socials = _classify_partner_links(raw_urls)
    extra_geo_chunks: List[str] = []
    site_domain = _root_domain(socials["website"]) if socials.get("website") else ""

    for hub_url in socials["link_hubs"][:2]:
        he, hs, ht = _extract_page_signals(hub_url, timeout=4, allowed_site_domain=site_domain)
        if ht:
            extra_geo_chunks.append(ht)
        for em in he:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, hs)
        if not site_domain and socials.get("website"):
            site_domain = _root_domain(socials["website"])

    if socials["website"] and not emails:
        se, ss, st, _ = _crawl_partner_website(socials["website"], need_email=True, need_geo=True)
        if st:
            extra_geo_chunks.append(st)
        for em in se:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, ss)

    bsky_url = f"https://bsky.app/profile/{handle}"
    slug_id = re.sub(r"[^A-Za-z0-9_.-]", "_", handle)
    return populate_partner_follower_counts({
        "partner_id": f"bsky_{slug_id}",
        "name": name,
        "handle": f"@{handle}",
        "primary_platform": "bluesky",
        "profile_url": bsky_url,
        "country": "",
        "_extra_geo_text": "\n".join(extra_geo_chunks)[:8000],
        "audience_count": followers,
        "bluesky_followers": followers,
        "audience_text": f"{followers:,} followers" if followers else "Bluesky Profile",
        "default_sport": default_sport,
        "seed_topic": seed_topic,
        "seed_partner_type": seed_partner_type,
        "bio": re.sub(r"\s+", " ", bio)[:600],
        "business_email": ", ".join(emails[:2]),
        "website": socials["website"] or (socials["link_hubs"][0] if socials["link_hubs"] else ""),
        "youtube_url": socials["youtube_url"],
        "instagram_url": socials["instagram_url"],
        "tiktok_url": socials["tiktok_url"],
        "facebook_url": socials["facebook_url"],
        "x_url": socials["x_url"],
        "threads_url": socials["threads_url"],
        "linkedin_url": socials["linkedin_url"],
        "pinterest_url": socials["pinterest_url"],
        "reddit_url": socials["reddit_url"],
        "strava_url": socials["strava_url"],
        "bluesky_url": bsky_url,
        "meetup_url": socials["meetup_url"],
        "eventbrite_url": socials["eventbrite_url"],
    })


def _scrape_bluesky_sports_partners(
    existing_ids: Optional[Set[str]] = None,
    max_new_bsky: int = 25,
) -> List[Dict[str, Any]]:
    candidates: Dict[str, Tuple[Dict[str, Any], str, str, str]] = {}
    for query, default_sport, seed_ptype in BLUESKY_SEARCH_SEEDS:
        try:
            url = f"https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors?q={urllib.parse.quote(query)}&limit=12"
            raw = _fetch_text(url, timeout=6)
            actors = json.loads(raw).get("actors") or []
            for a in actors:
                h = (a.get("handle") or "").strip()
                if not h:
                    continue
                pid = f"bsky_{re.sub(r'[^A-Za-z0-9_.-]', '_', h)}"
                if existing_ids and pid in existing_ids:
                    continue
                txt = f"{a.get('displayName', '')} {a.get('description', '')}"
                if (
                    h not in candidates
                    and _SPORTS_RELEVANCE_RE.search(txt)
                    and not _GAMING_OR_BETTING_RE.search(txt)
                    and not _OFF_TOPIC_CHANNEL_RE.search(txt)
                ):
                    candidates[h] = (a, default_sport, query, seed_ptype)
        except Exception:
            continue

    results: List[Dict[str, Any]] = []
    if not candidates:
        return results
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [
            ex.submit(_fetch_bluesky_partner, a, sp, q, pt)
            for a, sp, q, pt in list(candidates.values())[:max_new_bsky]
        ]
        for fut in as_completed(futs):
            try:
                item = fut.result()
                if item:
                    results.append(item)
            except Exception:
                pass
    return results


# ---------------------------------------------------------------------------
# Channel 4: Curated Live-Crawled Toronto/GTA & Canadian Sports Organizations
# ---------------------------------------------------------------------------

def _crawl_curated_org(seed: Dict[str, str]) -> Optional[Dict[str, Any]]:
    url = seed["url"]
    emails, social_urls, page_text, meta_desc = _crawl_partner_website(url, need_email=True, need_geo=True)
    if not page_text and not meta_desc and not emails and not social_urls:
        return None

    socials = _classify_partner_links(social_urls)
    for hub_url in socials["link_hubs"][:1]:
        he, hs, _ = _extract_page_signals(hub_url, timeout=4, allowed_site_domain=_root_domain(url))
        for em in he:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, hs)

    host_slug = re.sub(r"[^A-Za-z0-9_-]", "_", _root_domain(url) or seed["name"].lower())
    bio_src = meta_desc or page_text[:450]
    return populate_partner_follower_counts({
        "partner_id": f"org_{host_slug}",
        "name": seed["name"],
        "handle": _root_domain(url),
        "primary_platform": "website",
        "profile_url": url,
        "country": "Canada",
        "province_state": seed.get("prov", "Ontario"),
        "city": seed.get("city", "Toronto"),
        "_extra_geo_text": page_text[:6000],
        "audience_count": 0,
        "audience_text": seed.get("role", "Sports Organization"),
        "default_sport": seed["sport"],
        "seed_topic": seed["sport"],
        "seed_partner_type": "sports_org",
        "seed_partner_role": seed.get("role", "Sports Organization"),
        "bio": re.sub(r"\s+", " ", bio_src)[:550],
        "business_email": ", ".join(emails[:2]),
        "website": url,
        "youtube_url": socials["youtube_url"],
        "instagram_url": socials["instagram_url"],
        "tiktok_url": socials["tiktok_url"],
        "facebook_url": socials["facebook_url"],
        "x_url": socials["x_url"],
        "threads_url": socials["threads_url"],
        "linkedin_url": socials["linkedin_url"],
        "pinterest_url": socials["pinterest_url"],
        "reddit_url": socials["reddit_url"],
        "strava_url": socials["strava_url"],
        "bluesky_url": socials["bluesky_url"],
        "meetup_url": socials["meetup_url"],
        "eventbrite_url": socials["eventbrite_url"],
    })


def _scrape_curated_canadian_orgs(existing_ids: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    targets = []
    for seed in CURATED_CANADIAN_ORG_SEEDS:
        host_slug = re.sub(r"[^A-Za-z0-9_-]", "_", _root_domain(seed["url"]) or seed["name"].lower())
        pid = f"org_{host_slug}"
        if existing_ids and pid in existing_ids:
            continue
        targets.append(seed)

    results: List[Dict[str, Any]] = []
    if not targets:
        return results
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_crawl_curated_org, s) for s in targets]
        for fut in as_completed(futs):
            try:
                item = fut.result()
                if item:
                    results.append(item)
            except Exception:
                pass
    return results


# ---------------------------------------------------------------------------
# Deep Enrichment & Orchestrator
# ---------------------------------------------------------------------------

def enrich_partner_profile_deep(partner: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-crawl website contact/about/partnership subpages, link hubs, and recent YouTube videos."""
    updated = dict(partner)
    emails = [
        em.strip().lower()
        for em in (updated.get("business_email") or "").split(",")
        if _is_valid_outreach_email(em)
    ]
    site = (updated.get("website") or "").strip()
    site_domain = _root_domain(site) if site else ""
    socials: Dict[str, Any] = {k: updated.get(k, "") for k in _ALL_SOCIAL_FIELDS}
    socials["website"] = site
    socials["link_hubs"] = [site] if any(h in site.lower() for h in _LINK_HUB_HOSTS) else []
    extra_geo_chunks: List[str] = []

    country = (updated.get("country") or "").strip()
    need_geo = country in ("", "United States", "Canada") and not (updated.get("city") and updated.get("province_state"))

    for hub_url in list(socials["link_hubs"])[:2]:
        he, hs, ht = _extract_page_signals(hub_url, timeout=5, allowed_site_domain=site_domain)
        if ht:
            extra_geo_chunks.append(ht)
        for em in he:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, hs)
        if socials.get("website") and socials["website"] != hub_url:
            site = socials["website"]
            site_domain = _root_domain(site)

    if site and not any(h in site.lower() for h in _LINK_HUB_HOSTS):
        se, ss, st, _ = _crawl_partner_website(site, need_email=not bool(emails), need_geo=need_geo)
        if st:
            extra_geo_chunks.append(st)
        for em in se:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, ss)

    yt_url = (updated.get("youtube_url") or "").strip()
    if yt_url and (not emails or not updated.get("instagram_url") or need_geo):
        nav_url = urlparse(yt_url).path
        ve, vs, vt = _fetch_youtube_recent_video_signals(nav_url, site_domain=site_domain)
        if vt:
            extra_geo_chunks.append(vt)
        for em in ve:
            if em not in emails:
                emails.append(em)
        _merge_socials_into(socials, vs)

    updated["business_email"] = ", ".join(emails[:2])
    if socials.get("website"):
        updated["website"] = socials["website"]
    for k in _ALL_SOCIAL_FIELDS:
        if socials.get(k):
            updated[k] = socials[k]
    if extra_geo_chunks:
        updated["_extra_geo_text"] = "\n".join(extra_geo_chunks)[:12000]
    return updated


def scrape_sports_partners(
    existing_ids: Optional[Set[str]] = None,
    max_new_yt: int = 75,
    max_new_meetup: int = 30,
    max_new_bsky: int = 25,
    include_curated_orgs: bool = True,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Discover Toronto/GTA, Canadian & North American sports creators, pickup organizers,
    and local sports organizations across YouTube, Meetup, Bluesky, and curated live org sites.
    """
    partners: List[Dict[str, Any]] = []
    logs: List[str] = []

    # 1. YouTube discovery across all 12 sports (round-robin across sports for even coverage)
    seed_by_nav: Dict[str, Dict[str, str]] = {}
    with ThreadPoolExecutor(max_workers=8) as search_exec:
        futs = [
            search_exec.submit(_search_youtube_seed, q, sp, pt, pr)
            for q, sp, pt, pr in YOUTUBE_SPORTS_SEEDS
        ]
        for fut in as_completed(futs):
            try:
                for item in fut.result():
                    nav = item["nav_url"]
                    slug_id = re.sub(r"[^A-Za-z0-9_-]", "_", nav.lstrip("/"))
                    pid = f"yt_{slug_id}"
                    if existing_ids and pid in existing_ids:
                        continue
                    seed_by_nav.setdefault(nav, item)
            except Exception:
                pass

    by_sport: Dict[str, List[Dict[str, str]]] = {}
    for item in seed_by_nav.values():
        by_sport.setdefault(item["default_sport"], []).append(item)

    new_yt_seeds: List[Dict[str, str]] = []
    idx = 0
    while len(new_yt_seeds) < max_new_yt:
        added = False
        for sp_items in by_sport.values():
            if idx < len(sp_items):
                new_yt_seeds.append(sp_items[idx])
                added = True
                if len(new_yt_seeds) >= max_new_yt:
                    break
        if not added:
            break
        idx += 1

    yt_results: List[Dict[str, Any]] = []
    if new_yt_seeds:
        with ThreadPoolExecutor(max_workers=8) as prof_exec:
            futs = [prof_exec.submit(_fetch_youtube_partner_profile, s) for s in new_yt_seeds]
            for fut in as_completed(futs):
                try:
                    p = fut.result()
                    if p:
                        yt_results.append(p)
                except Exception:
                    pass
    partners.extend(yt_results)
    logs.append(f"YouTube: {len(yt_results)} profiles")

    # 2. Meetup + Bluesky + Curated Toronto/Canadian Org websites concurrently
    with ThreadPoolExecutor(max_workers=3) as chan_exec:
        fut_mu = chan_exec.submit(_scrape_meetup_sports_groups, existing_ids, max_new_meetup)
        fut_bs = chan_exec.submit(_scrape_bluesky_sports_partners, existing_ids, max_new_bsky)
        fut_org = (
            chan_exec.submit(_scrape_curated_canadian_orgs, existing_ids)
            if include_curated_orgs
            else None
        )

        try:
            mu_res = fut_mu.result()
            partners.extend(mu_res)
            logs.append(f"Meetup: {len(mu_res)} sports groups")
        except Exception as exc:
            logs.append(f"Meetup error: {exc}")

        try:
            bs_res = fut_bs.result()
            partners.extend(bs_res)
            logs.append(f"Bluesky: {len(bs_res)} profiles")
        except Exception as exc:
            logs.append(f"Bluesky error: {exc}")

        if fut_org is not None:
            try:
                org_res = fut_org.result()
                partners.extend(org_res)
                logs.append(f"Canadian Orgs: {len(org_res)} crawled")
            except Exception as exc:
                logs.append(f"Canadian Orgs error: {exc}")

    return partners, logs
