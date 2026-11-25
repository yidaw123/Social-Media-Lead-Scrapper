@echo off
cd /d "%~dp0"
echo Syncing latest daily cloud-scraped Crews partner data from GitHub...
git checkout -- crews_partners.db static/snapshot.json >nul 2>&1
git pull --ff-only origin main
echo Starting Crews Sports Creator ^& Partner Scraper Dashboard on http://localhost:8766 ...
start "" "http://localhost:8766"
python app.py --port 8766
pause
