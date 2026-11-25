from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
from urllib.parse import urlparse

from classifier import classify_partner
from database import (
    finish_scrape_run,
    get_all_partner_ids,
    log_scrape_run,
    query_partners,
    upsert_partner,
)
from scrapers import populate_partner_follower_counts, scrape_sports_partners


def run_partners_scrape_pipeline(
    max_new_yt: int = 75,
    max_new_meetup: int = 30,
    max_new_bsky: int = 25,
    include_curated_orgs: bool = True,
) -> Dict[str, Any]:
    """
    Runs live discovery across YouTube, Meetup, Bluesky, and curated Canadian sports org sites,
    classifies partners strictly into Pro Candidates vs. Sports Organizations across 12 sports,
    extracts US/Canada geo and verified emails, and persists results in SQLite.
    """
    sources_list = ["YouTube", "Meetup", "Bluesky"]
    if include_curated_orgs:
        sources_list.append("Canadian Sports Orgs")
    run_id = log_scrape_run(", ".join(sources_list))

    try:
        known_ids = get_all_partner_ids()
        raw_partners, logs = scrape_sports_partners(
            existing_ids=known_ids,
            max_new_yt=max_new_yt,
            max_new_meetup=max_new_meetup,
            max_new_bsky=max_new_bsky,
            include_curated_orgs=include_curated_orgs,
        )

        new_stored = 0
        pro_candidates = 0
        sports_orgs = 0
        with_email = 0

        for raw in raw_partners:
            classified = classify_partner(raw)
            if upsert_partner(classified):
                new_stored += 1
            if classified.get("partner_type") == "sports_org":
                sports_orgs += 1
            else:
                pro_candidates += 1
            if (classified.get("business_email") or "").strip():
                with_email += 1

        summary_msg = (
            f"Scraped {len(raw_partners)} partners ({new_stored} new, "
            f"{pro_candidates} Pro Candidates, {sports_orgs} Sports Orgs, {with_email} with email) | "
            + " | ".join(logs)
        )
        finish_scrape_run(
            run_id=run_id,
            total_fetched=len(raw_partners),
            new_stored=new_stored,
            pro_candidates_found=pro_candidates,
            sports_orgs_found=sports_orgs,
            with_email_found=with_email,
            status="completed",
            log_summary=summary_msg,
        )

        return {
            "run_id": run_id,
            "total_fetched": len(raw_partners),
            "new_stored": new_stored,
            "pro_candidates": pro_candidates,
            "sports_orgs": sports_orgs,
            "with_email": with_email,
            "logs": logs,
        }
    except Exception as exc:
        finish_scrape_run(
            run_id=run_id,
            total_fetched=0,
            new_stored=0,
            pro_candidates_found=0,
            sports_orgs_found=0,
            with_email_found=0,
            status="failed",
            log_summary=f"Scrape failed: {exc}",
        )
        raise


def reclassify_all_partners() -> int:
    """Re-apply current sport taxonomy, partner type/role, tier, and geo rules over all stored rows."""
    rows: List[Dict[str, Any]] = query_partners(limit=5000)
    updated = 0
    for row in rows:
        reclassified = classify_partner(row)
        upsert_partner(reclassified, force=True)
        updated += 1
    return updated


def _strip_meetup_corporate_links(row: Dict[str, Any]) -> Dict[str, Any]:
    """Remove Meetup's own footer social URLs accidentally captured on Meetup group pages."""
    cleaned = dict(row)
    for col in ("youtube_url", "instagram_url", "tiktok_url", "facebook_url", "x_url", "threads_url", "linkedin_url"):
        val = (cleaned.get(col) or "").strip()
        if not val:
            continue
        low_path = (urlparse(val).path or "").strip("/").lower()
        if low_path in ("meetup", "@meetup", "c/meetup", "user/meetup", "company/meetup"):
            cleaned[col] = ""
    return cleaned


def enrich_all_partner_followers(max_workers: int = 4) -> Dict[str, Any]:
    """
    Strip Meetup corporate social handles and fetch live Instagram & TikTok follower counts
    for stored partners missing per-platform counts, updating combined audience totals & tiers.
    """
    rows: List[Dict[str, Any]] = [_strip_meetup_corporate_links(r) for r in query_partners(limit=5000)]

    enriched_rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(populate_partner_follower_counts, r) for r in rows]
        for fut in as_completed(futs):
            try:
                enriched_rows.append(fut.result())
            except Exception:
                pass

    with_followers = 0
    ig_enriched = 0
    tt_enriched = 0
    for r in enriched_rows:
        classified = classify_partner(r)
        upsert_partner(classified, force=True)
        if (classified.get("audience_count") or 0) > 0:
            with_followers += 1
        if (classified.get("instagram_followers") or 0) > 0:
            ig_enriched += 1
        if (classified.get("tiktok_followers") or 0) > 0:
            tt_enriched += 1

    return {
        "processed": len(enriched_rows),
        "with_followers": with_followers,
        "instagram_enriched": ig_enriched,
        "tiktok_enriched": tt_enriched,
    }
