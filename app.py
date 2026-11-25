import csv
import io
import json
import os
import shutil
import threading
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List

from classifier import GTA_CITIES, SPORT_CATEGORIES, SPORT_SUB_NICHES
from database import (
    get_partners_summary,
    init_db,
    query_partners,
    sync_db_with_snapshot_and_local_outreach,
    update_partner_outreach,
)
from pipeline import (
    enrich_all_partner_followers,
    reclassify_all_partners,
    run_partners_scrape_pipeline,
)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(ROOT_DIR, "static")
SNAPSHOT_PATH = os.path.join(STATIC_DIR, "snapshot.json")
SCRAPE_LOCK = threading.Lock()

ALLOWED_CORS_ORIGINS = {
    "http://localhost:8766",
    "http://127.0.0.1:8766",
    "https://yidaw123.github.io",
}


def _clean_snapshot_partner(p: Dict[str, Any]) -> Dict[str, Any]:
    """Strip local-only outreach state from public snapshot rows so Git snapshots stay conflict-free."""
    out = dict(p)
    out["contacted"] = 0
    out["contacted_at"] = ""
    out["outreach_status"] = "not_contacted"
    out["outreach_notes"] = ""
    out["is_dismissed"] = 0
    return out


def _resolve_cors_origin(origin_header: str) -> str:
    clean = (origin_header or "").strip().rstrip("/")
    if clean in ALLOWED_CORS_ORIGINS:
        return clean
    return "http://localhost:8766"


def export_static_snapshot() -> None:
    """Writes static/snapshot.json (multi-line diff-friendly JSON) and syncs root index.html for GitHub Pages."""
    try:
        os.makedirs(STATIC_DIR, exist_ok=True)
        partners = [_clean_snapshot_partner(p) for p in query_partners(limit=5000)]
        summary = get_partners_summary()
        sub_map = {k: [t[0] for t in v] for k, v in SPORT_SUB_NICHES.items()}
        snap = {
            "sports_list": list(SPORT_CATEGORIES.keys()),
            "sub_niches_map": sub_map,
            "gta_cities": sorted(GTA_CITIES),
            "partners": partners,
            "recent_runs": summary.get("recent_runs", []),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2)
        src_idx = os.path.join(STATIC_DIR, "index.html")
        dst_idx = os.path.join(ROOT_DIR, "index.html")
        if os.path.exists(src_idx):
            shutil.copyfile(src_idx, dst_idx)
    except Exception:
        pass


def _qs_int(qs: Dict[str, List[str]], key: str, default: int, lo: int = 0, hi: int = 5000) -> int:
    try:
        return max(lo, min(hi, int(qs.get(key, [str(default)])[0])))
    except (ValueError, TypeError):
        return default


def _csv_safe(value: Any) -> Any:
    """Neutralize spreadsheet formula injection on exported CSV cells."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _cors_headers(self) -> None:
        origin = _resolve_cors_origin(self.headers.get("Origin", ""))
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8", errors="ignore")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            index_path = os.path.join(STATIC_DIR, "index.html")
            if not os.path.exists(index_path):
                index_path = os.path.join(ROOT_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.end_headers()
                self.wfile.write(content)
            else:
                self._send_json({"error": "Dashboard UI not found"}, 404)
            return

        if path.startswith("/static/"):
            rel_name = os.path.basename(path)
            file_path = os.path.join(STATIC_DIR, rel_name)
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    content = f.read()
                ctype = (
                    "text/css"
                    if rel_name.endswith(".css")
                    else "application/javascript"
                    if rel_name.endswith(".js")
                    else "application/json"
                    if rel_name.endswith(".json")
                    else "text/plain"
                )
                self.send_response(200)
                self.send_header("Content-Type", f"{ctype}; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.end_headers()
                self.wfile.write(content)
                return

        if path == "/api/health":
            self._send_json({"status": "ok", "app": "crews-sports-partner-scraper"})
            return

        if path == "/api/partners/summary":
            summary = get_partners_summary()
            summary["sports_list"] = list(SPORT_CATEGORIES.keys())
            summary["sub_niches_map"] = {k: [t[0] for t in v] for k, v in SPORT_SUB_NICHES.items()}
            summary["gta_cities"] = sorted(GTA_CITIES)
            self._send_json(summary)
            return

        if path == "/api/partners":
            partners = query_partners(
                partner_type=qs.get("partner_type", ["all"])[0],
                sport=qs.get("sport", ["all"])[0],
                sub_niche=qs.get("sub_niche", ["all"])[0],
                social_platform=qs.get("social_platform", ["all"])[0],
                tier=qs.get("tier", ["all"])[0],
                contact_filter=qs.get("contact_filter", ["all"])[0],
                contacted_filter=qs.get("contacted_filter", ["all"])[0],
                country=qs.get("country", ["all"])[0],
                province_state=qs.get("province_state", ["all"])[0],
                city=qs.get("city", ["all"])[0],
                search=qs.get("search", [""])[0],
                limit=_qs_int(qs, "limit", 2000, 1, 5000),
            )
            self._send_json({"partners": partners, "count": len(partners)})
            return

        if path == "/api/partners/export.csv":
            partners = query_partners(
                partner_type=qs.get("partner_type", ["all"])[0],
                sport=qs.get("sport", ["all"])[0],
                sub_niche=qs.get("sub_niche", ["all"])[0],
                social_platform=qs.get("social_platform", ["all"])[0],
                tier=qs.get("tier", ["all"])[0],
                contact_filter=qs.get("contact_filter", ["all"])[0],
                contacted_filter=qs.get("contacted_filter", ["all"])[0],
                country=qs.get("country", ["all"])[0],
                province_state=qs.get("province_state", ["all"])[0],
                city=qs.get("city", ["all"])[0],
                search=qs.get("search", [""])[0],
                limit=5000,
            )
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "Partner ID", "Name", "Handle", "Partner Type", "Partner Role",
                    "Primary Platform", "City", "Province / State", "Country",
                    "Total Followers", "YouTube Subscribers", "Instagram Followers",
                    "TikTok Followers", "Bluesky Followers", "Meetup Members",
                    "Audience Tier", "Sport Category", "Activity / Sub-Niche",
                    "Verified Email", "Contacted", "Outreach Status", "Outreach Notes", "Contacted At",
                    "Website / Link Hub", "YouTube URL", "Instagram URL", "TikTok URL", "Facebook URL",
                    "X / Twitter URL", "Threads URL", "LinkedIn URL", "Pinterest URL",
                    "Reddit URL", "Strava URL", "Bluesky URL", "Meetup URL", "Eventbrite URL",
                    "Bio",
                ]
            )
            for p in partners:
                ptype_label = "Sports Organization" if p.get("partner_type") == "sports_org" else "Pro Candidate"
                writer.writerow(
                    [_csv_safe(v) for v in [
                        p.get("partner_id"),
                        p.get("name"),
                        p.get("handle"),
                        ptype_label,
                        p.get("partner_role"),
                        p.get("primary_platform"),
                        p.get("city"),
                        p.get("province_state"),
                        p.get("country"),
                        p.get("audience_count"),
                        p.get("youtube_followers") or 0,
                        p.get("instagram_followers") or 0,
                        p.get("tiktok_followers") or 0,
                        p.get("bluesky_followers") or 0,
                        p.get("meetup_members") or 0,
                        p.get("audience_tier"),
                        p.get("primary_sport"),
                        p.get("sub_niche"),
                        p.get("business_email"),
                        "Yes" if p.get("contacted") else "No",
                        p.get("outreach_status") or ("contacted" if p.get("contacted") else "not_contacted"),
                        p.get("outreach_notes") or "",
                        p.get("contacted_at") or "",
                        p.get("website"),
                        p.get("youtube_url"),
                        p.get("instagram_url"),
                        p.get("tiktok_url"),
                        p.get("facebook_url"),
                        p.get("x_url"),
                        p.get("threads_url"),
                        p.get("linkedin_url"),
                        p.get("pinterest_url"),
                        p.get("reddit_url"),
                        p.get("strava_url"),
                        p.get("bluesky_url"),
                        p.get("meetup_url"),
                        p.get("eventbrite_url"),
                        p.get("bio"),
                    ]]
                )
            csv_bytes = output.getvalue().encode("utf-8-sig")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="crews_sports_partners.csv"')
            self.send_header("Content-Length", str(len(csv_bytes)))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        origin = (self.headers.get("Origin") or "").strip().rstrip("/")
        if origin and origin not in ALLOWED_CORS_ORIGINS:
            self._send_json({"error": "Origin not allowed"}, 403)
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        if path == "/api/scrape-partners":
            if not SCRAPE_LOCK.acquire(blocking=False):
                self._send_json({"error": "A sports partner scrape is already running — please wait."}, 409)
                return
            try:
                max_yt = max(10, min(150, int(body.get("max_new_yt") or 75)))
                max_mu = max(5, min(60, int(body.get("max_new_meetup") or 30)))
                max_bs = max(5, min(60, int(body.get("max_new_bsky") or 20)))
                max_eb = max(5, min(60, int(body.get("max_new_eb") or 25)))
                max_sc = max(5, min(80, int(body.get("max_new_social") or 35)))
                res = run_partners_scrape_pipeline(
                    max_new_yt=max_yt,
                    max_new_meetup=max_mu,
                    max_new_bsky=max_bs,
                    max_new_eb=max_eb,
                    max_new_social=max_sc,
                    include_curated_orgs=bool(body.get("include_curated_orgs", True)),
                )
                export_static_snapshot()
            finally:
                SCRAPE_LOCK.release()
            self._send_json(res)
            return

        if path in ("/api/partners/contacted", "/api/partners/outreach"):
            pid = str(body.get("partner_id") or "").strip()
            if not pid:
                self._send_json({"error": "partner_id is required"}, 400)
                return
            contacted_arg = body["contacted"] if "contacted" in body else None
            status_arg = body.get("outreach_status")
            notes_arg = body.get("outreach_notes") if "outreach_notes" in body else None
            dismissed_arg = body.get("is_dismissed") if "is_dismissed" in body else None
            res = update_partner_outreach(
                partner_id=pid,
                outreach_status=status_arg,
                contacted=bool(contacted_arg) if contacted_arg is not None else None,
                outreach_notes=notes_arg,
                is_dismissed=bool(dismissed_arg) if dismissed_arg is not None else None,
            )
            if not res.get("updated"):
                self._send_json({"error": "Partner not found"}, 404)
                return
            self._send_json(res)
            return

        if path == "/api/reclassify":
            count = reclassify_all_partners()
            export_static_snapshot()
            self._send_json({"status": "reclassified", "count": count})
            return

        self._send_json({"error": "Not found"}, 404)


def run_server(port: int = 8766) -> None:
    init_db()
    sync_db_with_snapshot_and_local_outreach(SNAPSHOT_PATH)
    summary = get_partners_summary()
    if summary["kpis"]["total_partners"] == 0:
        print("Database is empty — running initial live Crews sports partner scrape...")
        res = run_partners_scrape_pipeline()
        export_static_snapshot()
        print(
            f"Initial scrape finished: fetched {res['total_fetched']} partners "
            f"({res['pro_candidates']} Pro Candidates, {res['sports_orgs']} Sports Orgs, "
            f"{res['with_email']} with email)."
        )

    ThreadingHTTPServer.allow_reuse_address = os.name != "nt"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    except OSError as exc:
        print(f"Could not start on port {port} ({exc}). Is the dashboard already running? Try --port 8767.")
        return
    print(f"Crews Sports Creator & Partner Scraper Dashboard running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Crews Sports Creator & Partner Scraper Dashboard")
    parser.add_argument("--port", type=int, default=8766, help="Port to run the web dashboard on")
    parser.add_argument("--scrape-only", action="store_true", help="Run live sports partner scrape, update snapshot, and exit")
    parser.add_argument("--reclassify", action="store_true", help="Audit, deduplicate & reclassify all stored partners, update snapshot, and exit")
    parser.add_argument("--enrich-followers", action="store_true", help="Fetch live Instagram & TikTok follower counts for stored partners and exit")
    args = parser.parse_args()

    init_db()
    sync_db_with_snapshot_and_local_outreach(SNAPSHOT_PATH)
    if args.enrich_followers:
        res = enrich_all_partner_followers()
        export_static_snapshot()
        print(json.dumps(res, indent=2))
    elif args.reclassify:
        count = reclassify_all_partners()
        export_static_snapshot()
        print(json.dumps({"reclassified": count}, indent=2))
    elif args.scrape_only:
        res = run_partners_scrape_pipeline()
        export_static_snapshot()
        print(json.dumps(res, indent=2))
    else:
        run_server(port=args.port)
