# Crews — Sports Creator & Partner Scraper

Standalone creator, pickup organizer, and local sports organization discovery & outreach dashboard built for **Crews** (*"Find your crew. Play your game."* — 60% social discovery / player matching, 40% organized sports activities & events), preparing for a lean grassroots launch in **Toronto / GTA, Canada**.

## Key Capabilities

1. **Multi-Sport Coverage Across 12 Sports (`classifier.py`)**
   - `Basketball`
   - `Soccer`
   - `Volleyball`
   - `Tennis & Pickleball`
   - `Flag Football & Turf Sports`
   - `Hockey & Ice Sports`
   - `Running & Run Clubs`
   - `Baseball & Softball`
   - `Golf`
   - `Fitness & Cross-Training`
   - `Combat & Martial Arts`
   - `Multi-Sport & Rec Leagues`

2. **Strict Two-Sided Partner Separation**
   - **Pro Candidates (`pro_candidate`)**: Individual athletes, sports creators, coaches/trainers, pickup organizers, and university leaders targeted for the Founding Pro / Regular Pro referral program.
   - **Sports Organizations (`sports_org`)**: Rec leagues, sports & run clubs, gyms/training facilities, university networks, and tournament operators.

3. **Live Multi-Channel Discovery & Deep Email Verification (`scrapers/sports_scraper.py`)**
   - Discovers partners across **YouTube**, **Meetup**, **Bluesky**, and **curated Toronto/GTA & Canadian sports organization websites**.
   - Deep-crawls YouTube `/about` pages, recent video descriptions, Linktree/Beacons/Stan.store/Hoo.be/Carrd bio hubs, and organization `/contact`, `/about`, `/partnerships`, `/leagues`, and `/clubs` pages.
   - Decodes Cloudflare `data-cfemail` and `[at]`/`[dot]` obfuscations while strictly filtering out platform, SaaS, league-software (`TeamSnap`, `LeagueApps`, `CourtReserve`), sports-sponsor, placeholder, and asset emails.
   - Tracks 13 social & community links: **YouTube, Instagram, TikTok, Facebook, X / Twitter, Threads, LinkedIn, Pinterest, Reddit, Strava, Bluesky, Meetup, and Eventbrite**.

4. **Toronto / GTA & US/Canada Geo Filtering (`database.py`, `static/`)**
   - Dedicated **Toronto / GTA (Launch Market)** quick filter alongside cascading **Country -> Province / State -> City** searchable dropdowns restricted cleanly to **United States & Canada**.

5. **Outreach Workflow with Branch.io Attribution**
   - Per-row **Contacted** toggle persisted in SQLite (`crews_partners.db`) locally and `localStorage` in static GitHub Pages snapshot mode (`static/snapshot.json` + root `index.html`).
   - Editable **Email Template Modal** with two presets (**Founding Pro Partner** with `{{branch_link}}` merge tag and **Sports Organization / League**), live preview, clipboard copy, `mailto:` launcher, and auto-mark Contacted toggle.
   - Filtered CSV export (`crews_sports_partners.csv`) and twice-daily GitHub Actions workflow (`.github/workflows/daily_scrape.yml`).

## Quick Start

```powershell
pip install -r requirements.txt

# Start the Web Dashboard on http://localhost:8766
python app.py
```

Run a standalone CLI scrape & snapshot export:

```powershell
python app.py --scrape-only
```

Run unit tests:

```powershell
python -m unittest test_classifier.py -v
```
