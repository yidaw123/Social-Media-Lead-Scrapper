from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
from urllib.parse import urlparse

from classifier import classify_partner
from database import (
    delete_partners_by_ids,
    finish_scrape_run,
    get_all_partner_ids,
    get_stale_partners_for_refresh,
    log_scrape_run,
    query_partners,
    upsert_partner,
)
from scrapers import (
    deduplicate_and_merge_partners,
    enrich_partner_profile_deep,
    populate_partner_follower_counts,
    sanitize_stored_partner_row,
    scrape_sports_partners,
)


def audit_and_deduplicate_stored_partners() -> Dict[str, int]:
    """
    Re-validate all stored partners against current NSFW, franchise/media, North America,
    HTML/URL hygiene, sport/partner-type classification, and cross-channel deduplication rules.
    User-contacted / noted rows are never deleted unless merged into an even richer duplicate.
    """
    rows: List[Dict[str, Any]] = query_partners(limit=5000)
    valid_rows: List[Dict[str, Any]] = []
    pruned_ids: List[str] = []

    for row in rows:
        is_protected = bool(row.get("contacted") or (row.get("outreach_notes") or "").strip())
        sanitized = sanitize_stored_partner_row(row)
        if sanitized is None and not is_protected:
            pruned_ids.append(str(row["partner_id"]))
            continue
        target = sanitized if sanitized is not None else row
        valid_rows.append(classify_partner(target))

    deduped_rows, dup_ids = deduplicate_and_merge_partners(valid_rows)
    if pruned_ids:
        delete_partners_by_ids(pruned_ids, force_protected=False)
    if dup_ids:
        delete_partners_by_ids(dup_ids, force_protected=True)

    for r in deduped_rows:
        reclassified = classify_partner(r)
        upsert_partner(reclassified, force=True)

    return {
        "kept": len(deduped_rows),
        "pruned": len(pruned_ids),
        "merged_duplicates": len(dup_ids),
    }


def refresh_stale_partners(max_refresh: int = 15, min_age_days: int = 7) -> int:
    """Re-crawl follower counts and contact links for the oldest stored leads (> min_age_days)."""
    stale = get_stale_partners_for_refresh(limit=max_refresh, min_age_days=min_age_days)
    if not stale:
        return 0

    def _refresh_one(row: Dict[str, Any]) -> Dict[str, Any]:
        deep = enrich_partner_profile_deep(row)
        with_f = populate_partner_follower_counts(deep)
        return classify_partner(with_f)

    refreshed = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(_refresh_one, r) for r in stale]
        for fut in as_completed(futs):
            try:
                updated_row = fut.result()
                upsert_partner(updated_row, force=True)
                refreshed += 1
            except Exception:
                pass
    return refreshed


def run_partners_scrape_pipeline(
    max_new_yt: int = 75,
    max_new_meetup: int = 30,
    max_new_bsky: int = 20,
    max_new_eb: int = 25,
    max_new_social: int = 35,
    include_curated_orgs: bool = True,
) -> Dict[str, Any]:
    """
    Audits stored leads, runs live discovery across YouTube, Meetup, Eventbrite Toronto,
    Web-Indexed Toronto IG/TikTok, Bluesky, and curated Canadian sports org sites,
    refreshes stale leads, deduplicates across channels, and persists results in SQLite.
    """
    sources_list = ["YouTube", "Meetup", "Eventbrite Toronto", "IG/TikTok Toronto", "Bluesky"]
    if include_curated_orgs:
        sources_list.append("Canadian Sports Orgs")
    run_id = log_scrape_run(", ".join(sources_list))

    try:
        pre_audit = audit_and_deduplicate_stored_partners()
        known_ids = get_all_partner_ids()
        raw_partners, logs = scrape_sports_partners(
            existing_ids=known_ids,
            max_new_yt=max_new_yt,
            max_new_meetup=max_new_meetup,
            max_new_bsky=max_new_bsky,
            max_new_eb=max_new_eb,
            max_new_social=max_new_social,
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

        refreshed_cnt = refresh_stale_partners(max_refresh=15, min_age_days=7)
        if refreshed_cnt:
            logs.append(f"Refreshed stale: {refreshed_cnt}")

        post_audit = audit_and_deduplicate_stored_partners()
        pruned_total = pre_audit["pruned"] + post_audit["pruned"]
        merged_total = pre_audit["merged_duplicates"] + post_audit["merged_duplicates"]
        if pruned_total or merged_total:
            logs.append(f"Audit pruned {pruned_total}, merged {merged_total} dups")

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
            "active_total": post_audit["kept"],
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
    """Audit, sanitize, deduplicate, and re-apply current taxonomy/type/geo rules over all stored rows."""
    res = audit_and_deduplicate_stored_partners()
    return res["kept"]


def _strip_platform_corporate_links(row: Dict[str, Any]) -> Dict[str, Any]:
    """Remove Meetup/Eventbrite corporate social URLs accidentally captured on organizer pages."""
    cleaned = dict(row)
    for col in ("youtube_url", "instagram_url", "tiktok_url", "facebook_url", "x_url", "threads_url", "linkedin_url"):
        val = (cleaned.get(col) or "").strip()
        if not val:
            continue
        low_path = (urlparse(val).path or "").strip("/").lower()
        if low_path in ("meetup", "@meetup", "c/meetup", "user/meetup", "company/meetup", "eventbrite", "@eventbrite", "eventbritehelp"):
            cleaned[col] = ""
    return cleaned


def enrich_all_partner_followers(max_workers: int = 4) -> Dict[str, Any]:
    """
    Strip corporate handles and fetch live Instagram & TikTok follower counts
    for stored partners missing per-platform counts, updating combined audience totals & tiers.
    """
    rows: List[Dict[str, Any]] = [_strip_platform_corporate_links(r) for r in query_partners(limit=5000)]

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
