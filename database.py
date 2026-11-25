import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from classifier import GTA_CITIES

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crews_partners.db")

SOCIAL_PLATFORM_COLUMNS: Dict[str, str] = {
    "youtube": "youtube_url",
    "instagram": "instagram_url",
    "tiktok": "tiktok_url",
    "facebook": "facebook_url",
    "x": "x_url",
    "threads": "threads_url",
    "linkedin": "linkedin_url",
    "pinterest": "pinterest_url",
    "reddit": "reddit_url",
    "strava": "strava_url",
    "bluesky": "bluesky_url",
    "meetup": "meetup_url",
    "eventbrite": "eventbrite_url",
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            handle TEXT DEFAULT '',
            partner_type TEXT NOT NULL DEFAULT 'pro_candidate',
            partner_role TEXT DEFAULT '',
            primary_platform TEXT NOT NULL,
            profile_url TEXT NOT NULL,
            country TEXT DEFAULT '',
            province_state TEXT DEFAULT '',
            city TEXT DEFAULT '',
            audience_count INTEGER DEFAULT 0,
            audience_text TEXT DEFAULT '',
            audience_tier TEXT DEFAULT 'nano',
            youtube_followers INTEGER DEFAULT 0,
            instagram_followers INTEGER DEFAULT 0,
            tiktok_followers INTEGER DEFAULT 0,
            bluesky_followers INTEGER DEFAULT 0,
            meetup_members INTEGER DEFAULT 0,
            primary_sport TEXT NOT NULL,
            sub_niche TEXT DEFAULT '',
            secondary_sports TEXT DEFAULT '[]',
            bio TEXT DEFAULT '',
            business_email TEXT DEFAULT '',
            website TEXT DEFAULT '',
            youtube_url TEXT DEFAULT '',
            instagram_url TEXT DEFAULT '',
            tiktok_url TEXT DEFAULT '',
            facebook_url TEXT DEFAULT '',
            x_url TEXT DEFAULT '',
            threads_url TEXT DEFAULT '',
            linkedin_url TEXT DEFAULT '',
            pinterest_url TEXT DEFAULT '',
            reddit_url TEXT DEFAULT '',
            strava_url TEXT DEFAULT '',
            bluesky_url TEXT DEFAULT '',
            meetup_url TEXT DEFAULT '',
            eventbrite_url TEXT DEFAULT '',
            contacted INTEGER DEFAULT 0,
            contacted_at TEXT DEFAULT '',
            scraped_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT DEFAULT '',
            sources TEXT NOT NULL,
            total_fetched INTEGER DEFAULT 0,
            new_stored INTEGER DEFAULT 0,
            pro_candidates_found INTEGER DEFAULT 0,
            sports_orgs_found INTEGER DEFAULT 0,
            with_email_found INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            log_summary TEXT DEFAULT ''
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    # Forward-compatible migration check
    cur.execute("PRAGMA table_info(partners)")
    existing_cols = {row["name"] for row in cur.fetchall()}
    text_cols = (
        "handle", "partner_type", "partner_role", "country", "province_state", "city",
        "audience_text", "audience_tier", "sub_niche", "secondary_sports", "bio",
        "business_email", "website", "youtube_url", "instagram_url", "tiktok_url",
        "facebook_url", "x_url", "threads_url", "linkedin_url", "pinterest_url",
        "reddit_url", "strava_url", "bluesky_url", "meetup_url", "eventbrite_url",
        "contacted_at",
    )
    for col_name in text_cols:
        if col_name not in existing_cols:
            cur.execute(f"ALTER TABLE partners ADD COLUMN {col_name} TEXT DEFAULT ''")
    for int_col in (
        "contacted",
        "audience_count",
        "youtube_followers",
        "instagram_followers",
        "tiktok_followers",
        "bluesky_followers",
        "meetup_members",
    ):
        if int_col not in existing_cols:
            cur.execute(f"ALTER TABLE partners ADD COLUMN {int_col} INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


def get_setting(key: str, default: Any = None) -> Any:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except Exception:
        return default


def set_setting(key: str, value: Any) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, json.dumps(value)),
    )
    conn.commit()
    conn.close()


def get_all_partner_ids() -> set:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT partner_id FROM partners")
    found = {r["partner_id"] for r in cur.fetchall()}
    conn.close()
    return found


def upsert_partner(partner: Dict[str, Any], force: bool = False) -> bool:
    """Insert or update a partner row by partner_id. Returns True if newly inserted."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, country, province_state, city FROM partners WHERE partner_id = ?",
        (partner["partner_id"],),
    )
    existing = cur.fetchone()
    now_iso = datetime.now(timezone.utc).isoformat()

    secondary_json = (
        json.dumps(partner.get("secondary_sports", []))
        if isinstance(partner.get("secondary_sports"), list)
        else str(partner.get("secondary_sports", "[]"))
    )

    country_val = (partner.get("country") or "").strip()
    if existing and not country_val and not force:
        country_val = (existing["country"] or "").strip()

    is_us_ca = country_val in ("United States", "Canada")
    prov_val = (partner.get("province_state") or "").strip() if is_us_ca else ""
    city_val = (partner.get("city") or "").strip() if is_us_ca else ""

    if existing and not force and is_us_ca:
        if not prov_val:
            prov_val = (existing["province_state"] or "").strip()
        if not city_val:
            city_val = (existing["city"] or "").strip()

    ptype = partner.get("partner_type")
    if ptype not in ("pro_candidate", "sports_org"):
        ptype = "pro_candidate"

    yt_f = int(partner.get("youtube_followers") or 0)
    ig_f = int(partner.get("instagram_followers") or 0)
    tt_f = int(partner.get("tiktok_followers") or 0)
    bs_f = int(partner.get("bluesky_followers") or 0)
    mu_m = int(partner.get("meetup_members") or 0)
    aud_c = int(partner.get("audience_count") or 0)

    if existing:
        if force:
            aud_expr = "?"
            yt_expr = "?"
            ig_expr = "?"
            tt_expr = "?"
            bs_expr = "?"
            mu_expr = "?"
            str_expr = lambda col: "?"
            follower_params = (aud_c, yt_f, ig_f, tt_f, bs_f, mu_m)
        else:
            aud_expr = "CASE WHEN ? > 0 THEN ? ELSE audience_count END"
            yt_expr = "CASE WHEN ? > 0 THEN ? ELSE youtube_followers END"
            ig_expr = "CASE WHEN ? > 0 THEN ? ELSE instagram_followers END"
            tt_expr = "CASE WHEN ? > 0 THEN ? ELSE tiktok_followers END"
            bs_expr = "CASE WHEN ? > 0 THEN ? ELSE bluesky_followers END"
            mu_expr = "CASE WHEN ? > 0 THEN ? ELSE meetup_members END"
            str_expr = lambda col: f"COALESCE(NULLIF(?, ''), {col})"
            follower_params = (aud_c, aud_c, yt_f, yt_f, ig_f, ig_f, tt_f, tt_f, bs_f, bs_f, mu_m, mu_m)

        cur.execute(
            f"""
            UPDATE partners SET
                name = ?,
                handle = ?,
                partner_type = ?,
                partner_role = ?,
                primary_platform = ?,
                profile_url = ?,
                country = ?,
                province_state = ?,
                city = ?,
                audience_count = {aud_expr},
                youtube_followers = {yt_expr},
                instagram_followers = {ig_expr},
                tiktok_followers = {tt_expr},
                bluesky_followers = {bs_expr},
                meetup_members = {mu_expr},
                audience_text = ?,
                audience_tier = ?,
                primary_sport = ?,
                sub_niche = ?,
                secondary_sports = ?,
                bio = {str_expr('bio')},
                business_email = {str_expr('business_email')},
                website = {str_expr('website')},
                youtube_url = {str_expr('youtube_url')},
                instagram_url = {str_expr('instagram_url')},
                tiktok_url = {str_expr('tiktok_url')},
                facebook_url = {str_expr('facebook_url')},
                x_url = {str_expr('x_url')},
                threads_url = {str_expr('threads_url')},
                linkedin_url = {str_expr('linkedin_url')},
                pinterest_url = {str_expr('pinterest_url')},
                reddit_url = {str_expr('reddit_url')},
                strava_url = {str_expr('strava_url')},
                bluesky_url = {str_expr('bluesky_url')},
                meetup_url = {str_expr('meetup_url')},
                eventbrite_url = {str_expr('eventbrite_url')},
                scraped_at = ?
            WHERE partner_id = ?
            """,
            (
                partner.get("name", ""),
                partner.get("handle", ""),
                ptype,
                partner.get("partner_role", ""),
                partner.get("primary_platform", "youtube"),
                partner.get("profile_url", ""),
                country_val,
                prov_val,
                city_val,
                *follower_params,
                partner.get("audience_text", ""),
                partner.get("audience_tier", "nano"),
                partner.get("primary_sport", "Multi-Sport & Rec Leagues"),
                partner.get("sub_niche", ""),
                secondary_json,
                partner.get("bio", ""),
                partner.get("business_email", ""),
                partner.get("website", ""),
                partner.get("youtube_url", ""),
                partner.get("instagram_url", ""),
                partner.get("tiktok_url", ""),
                partner.get("facebook_url", ""),
                partner.get("x_url", ""),
                partner.get("threads_url", ""),
                partner.get("linkedin_url", ""),
                partner.get("pinterest_url", ""),
                partner.get("reddit_url", ""),
                partner.get("strava_url", ""),
                partner.get("bluesky_url", ""),
                partner.get("meetup_url", ""),
                partner.get("eventbrite_url", ""),
                now_iso,
                partner["partner_id"],
            ),
        )
        conn.commit()
        conn.close()
        return False

    cur.execute(
        """
        INSERT INTO partners (
            partner_id, name, handle, partner_type, partner_role, primary_platform, profile_url,
            country, province_state, city, audience_count, audience_text, audience_tier,
            youtube_followers, instagram_followers, tiktok_followers, bluesky_followers, meetup_members,
            primary_sport, sub_niche, secondary_sports, bio, business_email, website,
            youtube_url, instagram_url, tiktok_url, facebook_url, x_url, threads_url,
            linkedin_url, pinterest_url, reddit_url, strava_url, bluesky_url,
            meetup_url, eventbrite_url, contacted, contacted_at, scraped_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            partner["partner_id"],
            partner.get("name", ""),
            partner.get("handle", ""),
            ptype,
            partner.get("partner_role", ""),
            partner.get("primary_platform", "youtube"),
            partner.get("profile_url", ""),
            country_val,
            prov_val,
            city_val,
            aud_c,
            partner.get("audience_text", ""),
            partner.get("audience_tier", "nano"),
            yt_f,
            ig_f,
            tt_f,
            bs_f,
            mu_m,
            partner.get("primary_sport", "Multi-Sport & Rec Leagues"),
            partner.get("sub_niche", ""),
            secondary_json,
            partner.get("bio", ""),
            partner.get("business_email", ""),
            partner.get("website", ""),
            partner.get("youtube_url", ""),
            partner.get("instagram_url", ""),
            partner.get("tiktok_url", ""),
            partner.get("facebook_url", ""),
            partner.get("x_url", ""),
            partner.get("threads_url", ""),
            partner.get("linkedin_url", ""),
            partner.get("pinterest_url", ""),
            partner.get("reddit_url", ""),
            partner.get("strava_url", ""),
            partner.get("bluesky_url", ""),
            partner.get("meetup_url", ""),
            partner.get("eventbrite_url", ""),
            1 if partner.get("contacted") else 0,
            partner.get("contacted_at", ""),
            now_iso,
        ),
    )
    conn.commit()
    conn.close()
    return True


def set_partner_contacted(partner_id: str, contacted: bool) -> Dict[str, Any]:
    """Mark or unmark a partner as Contacted in SQLite."""
    now_iso = datetime.now(timezone.utc).isoformat() if contacted else ""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE partners SET contacted = ?, contacted_at = ? WHERE partner_id = ?",
        (1 if contacted else 0, now_iso, partner_id),
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return {
        "partner_id": partner_id,
        "contacted": bool(contacted),
        "contacted_at": now_iso,
        "updated": updated > 0,
    }


def query_partners(
    partner_type: Optional[str] = None,
    sport: Optional[str] = None,
    sub_niche: Optional[str] = None,
    social_platform: Optional[str] = None,
    tier: Optional[str] = None,
    contact_filter: Optional[str] = None,
    contacted_filter: Optional[str] = None,
    country: Optional[str] = None,
    province_state: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 2000,
) -> List[Dict[str, Any]]:
    """Query partners filtered by partner type, sport, activity sub-niche, platform, tier, outreach status, geo, and keyword."""
    conn = get_connection()
    cur = conn.cursor()

    clauses: List[str] = ["1=1"]
    params: List[Any] = []

    if partner_type and partner_type in ("pro_candidate", "sports_org"):
        clauses.append("partner_type = ?")
        params.append(partner_type)

    if sport and sport != "all":
        clauses.append("primary_sport = ?")
        params.append(sport)

    if sub_niche and sub_niche != "all":
        clauses.append("sub_niche = ?")
        params.append(sub_niche)

    if social_platform and social_platform in SOCIAL_PLATFORM_COLUMNS:
        col = SOCIAL_PLATFORM_COLUMNS[social_platform]
        clauses.append(f"COALESCE({col}, '') != ''")

    if tier and tier != "all":
        if tier == "micro_mid":
            clauses.append("audience_tier IN ('micro', 'mid')")
        else:
            clauses.append("audience_tier = ?")
            params.append(tier)

    if contact_filter == "has_email":
        clauses.append("COALESCE(business_email, '') != ''")
    elif contact_filter == "has_contact":
        clauses.append("(COALESCE(business_email, '') != '' OR COALESCE(website, '') != '')")

    if contacted_filter == "contacted":
        clauses.append("COALESCE(contacted, 0) = 1")
    elif contacted_filter == "not_contacted":
        clauses.append("COALESCE(contacted, 0) = 0")

    if country and country != "all":
        if country == "Toronto / GTA":
            placeholders = ", ".join("?" for _ in GTA_CITIES)
            clauses.append(f"country = 'Canada' AND province_state = 'Ontario' AND city IN ({placeholders})")
            params.extend(sorted(GTA_CITIES))
        elif country == "North America":
            clauses.append("country IN ('Canada', 'United States')")
        elif country == "Other":
            clauses.append("COALESCE(country, '') NOT IN ('Canada', 'United States')")
        else:
            clauses.append("country = ?")
            params.append(country)

    if province_state and province_state != "all":
        clauses.append("province_state = ?")
        params.append(province_state)

    if city and city != "all":
        clauses.append("city = ?")
        params.append(city)

    if search and search.strip():
        q = f"%{search.strip()}%"
        clauses.append(
            "(name LIKE ? OR handle LIKE ? OR partner_role LIKE ? OR primary_sport LIKE ? OR sub_niche LIKE ? "
            "OR bio LIKE ? OR business_email LIKE ? OR website LIKE ? "
            "OR country LIKE ? OR province_state LIKE ? OR city LIKE ?)"
        )
        params.extend([q] * 11)

    where_sql = " AND ".join(clauses)
    sql = f"""
        SELECT * FROM partners
        WHERE {where_sql}
        ORDER BY
            (CASE WHEN COALESCE(business_email, '') != '' THEN 0 ELSE 1 END) ASC,
            audience_count DESC
        LIMIT ?
    """
    params.append(limit)
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        try:
            r["secondary_sports"] = json.loads(r.get("secondary_sports") or "[]")
        except Exception:
            r["secondary_sports"] = []
    conn.close()
    return rows


def get_partners_summary() -> Dict[str, Any]:
    """Return KPI counts, all 13 platform counts, tier counts, US/CA geo options, and 12-sport breakdown."""
    conn = get_connection()
    cur = conn.cursor()

    gta_placeholders = ", ".join("?" for _ in GTA_CITIES)
    gta_params = sorted(GTA_CITIES)

    cur.execute(
        f"""
        SELECT
            COUNT(*) as total_partners,
            SUM(CASE WHEN partner_type = 'pro_candidate' THEN 1 ELSE 0 END) as pro_candidates,
            SUM(CASE WHEN partner_type = 'sports_org' THEN 1 ELSE 0 END) as sports_orgs,
            SUM(CASE WHEN COALESCE(business_email, '') != '' THEN 1 ELSE 0 END) as with_email,
            SUM(CASE WHEN COALESCE(contacted, 0) = 1 THEN 1 ELSE 0 END) as contacted_count,
            SUM(CASE WHEN country = 'Canada' AND province_state = 'Ontario' AND city IN ({gta_placeholders}) THEN 1 ELSE 0 END) as toronto_gta,
            SUM(CASE WHEN country = 'Canada' THEN 1 ELSE 0 END) as canada_count,
            SUM(CASE WHEN country IN ('Canada', 'United States') THEN 1 ELSE 0 END) as north_america,
            SUM(CASE WHEN audience_tier IN ('micro', 'mid') THEN 1 ELSE 0 END) as micro_mid_tier,
            SUM(CASE WHEN COALESCE(youtube_url, '') != '' THEN 1 ELSE 0 END) as on_youtube,
            SUM(CASE WHEN COALESCE(instagram_url, '') != '' THEN 1 ELSE 0 END) as on_instagram,
            SUM(CASE WHEN COALESCE(tiktok_url, '') != '' THEN 1 ELSE 0 END) as on_tiktok,
            SUM(CASE WHEN COALESCE(facebook_url, '') != '' THEN 1 ELSE 0 END) as on_facebook,
            SUM(CASE WHEN COALESCE(x_url, '') != '' THEN 1 ELSE 0 END) as on_x,
            SUM(CASE WHEN COALESCE(threads_url, '') != '' THEN 1 ELSE 0 END) as on_threads,
            SUM(CASE WHEN COALESCE(linkedin_url, '') != '' THEN 1 ELSE 0 END) as on_linkedin,
            SUM(CASE WHEN COALESCE(pinterest_url, '') != '' THEN 1 ELSE 0 END) as on_pinterest,
            SUM(CASE WHEN COALESCE(reddit_url, '') != '' THEN 1 ELSE 0 END) as on_reddit,
            SUM(CASE WHEN COALESCE(strava_url, '') != '' THEN 1 ELSE 0 END) as on_strava,
            SUM(CASE WHEN COALESCE(bluesky_url, '') != '' THEN 1 ELSE 0 END) as on_bluesky,
            SUM(CASE WHEN COALESCE(meetup_url, '') != '' THEN 1 ELSE 0 END) as on_meetup,
            SUM(CASE WHEN COALESCE(eventbrite_url, '') != '' THEN 1 ELSE 0 END) as on_eventbrite,
            SUM(CASE WHEN audience_tier = 'nano' THEN 1 ELSE 0 END) as tier_nano,
            SUM(CASE WHEN audience_tier = 'micro' THEN 1 ELSE 0 END) as tier_micro,
            SUM(CASE WHEN audience_tier = 'mid' THEN 1 ELSE 0 END) as tier_mid,
            SUM(CASE WHEN audience_tier = 'macro' THEN 1 ELSE 0 END) as tier_macro,
            SUM(CASE WHEN audience_tier = 'mega' THEN 1 ELSE 0 END) as tier_mega
        FROM partners
        """,
        gta_params,
    )
    kpi_row = cur.fetchone()
    kpis = {
        "total_partners": (kpi_row["total_partners"] or 0) if kpi_row else 0,
        "pro_candidates": (kpi_row["pro_candidates"] or 0) if kpi_row else 0,
        "sports_orgs": (kpi_row["sports_orgs"] or 0) if kpi_row else 0,
        "with_email": (kpi_row["with_email"] or 0) if kpi_row else 0,
        "contacted_count": (kpi_row["contacted_count"] or 0) if kpi_row else 0,
        "toronto_gta": (kpi_row["toronto_gta"] or 0) if kpi_row else 0,
        "canada_count": (kpi_row["canada_count"] or 0) if kpi_row else 0,
        "north_america": (kpi_row["north_america"] or 0) if kpi_row else 0,
        "micro_mid_tier": (kpi_row["micro_mid_tier"] or 0) if kpi_row else 0,
        "on_youtube": (kpi_row["on_youtube"] or 0) if kpi_row else 0,
        "on_instagram": (kpi_row["on_instagram"] or 0) if kpi_row else 0,
        "on_tiktok": (kpi_row["on_tiktok"] or 0) if kpi_row else 0,
        "on_facebook": (kpi_row["on_facebook"] or 0) if kpi_row else 0,
        "on_x": (kpi_row["on_x"] or 0) if kpi_row else 0,
        "on_threads": (kpi_row["on_threads"] or 0) if kpi_row else 0,
        "on_linkedin": (kpi_row["on_linkedin"] or 0) if kpi_row else 0,
        "on_pinterest": (kpi_row["on_pinterest"] or 0) if kpi_row else 0,
        "on_reddit": (kpi_row["on_reddit"] or 0) if kpi_row else 0,
        "on_strava": (kpi_row["on_strava"] or 0) if kpi_row else 0,
        "on_bluesky": (kpi_row["on_bluesky"] or 0) if kpi_row else 0,
        "on_meetup": (kpi_row["on_meetup"] or 0) if kpi_row else 0,
        "on_eventbrite": (kpi_row["on_eventbrite"] or 0) if kpi_row else 0,
    }
    tier_counts = {
        "nano": (kpi_row["tier_nano"] or 0) if kpi_row else 0,
        "micro": (kpi_row["tier_micro"] or 0) if kpi_row else 0,
        "mid": (kpi_row["tier_mid"] or 0) if kpi_row else 0,
        "macro": (kpi_row["tier_macro"] or 0) if kpi_row else 0,
        "mega": (kpi_row["tier_mega"] or 0) if kpi_row else 0,
    }

    cur.execute(
        """
        SELECT DISTINCT country, province_state, city
        FROM partners
        WHERE country IN ('United States', 'Canada')
        """
    )
    provinces_by_country: Dict[str, set] = {"United States": set(), "Canada": set()}
    cities_by_country: Dict[str, set] = {"United States": set(), "Canada": set()}
    cities_by_province: Dict[str, set] = {}
    all_provinces: set = set()
    all_cities: set = set()
    for row in cur.fetchall():
        ctry = (row["country"] or "").strip()
        prov = (row["province_state"] or "").strip()
        city_val = (row["city"] or "").strip()
        if prov:
            provinces_by_country.setdefault(ctry, set()).add(prov)
            all_provinces.add(prov)
        if city_val:
            cities_by_country.setdefault(ctry, set()).add(city_val)
            all_cities.add(city_val)
            if prov:
                cities_by_province.setdefault(prov, set()).add(city_val)

    geo_options = {
        "provinces_by_country": {k: sorted(v) for k, v in provinces_by_country.items()},
        "cities_by_country": {k: sorted(v) for k, v in cities_by_country.items()},
        "cities_by_province": {k: sorted(v) for k, v in cities_by_province.items()},
        "all_provinces": sorted(all_provinces),
        "all_cities": sorted(all_cities),
    }

    cur.execute(
        """
        SELECT
            primary_sport,
            COUNT(*) as total_partners,
            SUM(CASE WHEN partner_type = 'pro_candidate' THEN 1 ELSE 0 END) as pro_candidates,
            SUM(CASE WHEN partner_type = 'sports_org' THEN 1 ELSE 0 END) as sports_orgs,
            SUM(CASE WHEN COALESCE(business_email, '') != '' THEN 1 ELSE 0 END) as with_email,
            SUM(CASE WHEN COALESCE(instagram_url, '') != '' THEN 1 ELSE 0 END) as on_instagram,
            SUM(CASE WHEN COALESCE(tiktok_url, '') != '' THEN 1 ELSE 0 END) as on_tiktok,
            SUM(CASE WHEN COALESCE(strava_url, '') != '' THEN 1 ELSE 0 END) as on_strava,
            SUM(CASE WHEN COALESCE(meetup_url, '') != '' THEN 1 ELSE 0 END) as on_meetup
        FROM partners
        GROUP BY primary_sport
        ORDER BY total_partners DESC, with_email DESC
        """
    )
    sport_breakdown = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM scrape_runs ORDER BY id DESC LIMIT 5")
    recent_runs = [dict(r) for r in cur.fetchall()]

    conn.close()
    return {
        "kpis": kpis,
        "tier_counts": tier_counts,
        "geo_options": geo_options,
        "sport_breakdown": sport_breakdown,
        "recent_runs": recent_runs,
    }


def log_scrape_run(sources: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO scrape_runs (started_at, sources, status) VALUES (?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), sources, "running"),
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(run_id or 0)


def finish_scrape_run(
    run_id: int,
    total_fetched: int,
    new_stored: int,
    pro_candidates_found: int,
    sports_orgs_found: int,
    with_email_found: int,
    status: str,
    log_summary: str,
) -> None:
    if not run_id:
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE scrape_runs SET
            finished_at = ?,
            total_fetched = ?,
            new_stored = ?,
            pro_candidates_found = ?,
            sports_orgs_found = ?,
            with_email_found = ?,
            status = ?,
            log_summary = ?
        WHERE id = ?
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            total_fetched,
            new_stored,
            pro_candidates_found,
            sports_orgs_found,
            with_email_found,
            status,
            log_summary,
            run_id,
        ),
    )
    conn.commit()
    conn.close()
