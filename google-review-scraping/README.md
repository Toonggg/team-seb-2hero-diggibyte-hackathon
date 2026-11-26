# Google Review Scraping (SEB Locations)

Collects Google ratings and reviews for SEB bank locations across Sweden, the Nordics, and the Baltics using the **Google Places API (New)**, and prepares them for sentiment analysis in Databricks.

## Files

- `run.sh` — One-command runner that fetches fresh CSVs and packages the shareable `dashboard.html`.
- `fetch_seb_reviews.py` — Main CLI script: loads `.env`, fetches places (or mock data), aggregates branch stats, and exports CSVs.
- `places_client.py` — Google Places API (New) Text Search client, region query presets, and SEB branch filter (excludes ATMs/unrelated places).
- `sentiment.py` — Lightweight local EN/SV sentiment baseline (for quick checks before running Databricks AI functions).
- `mock_data.json` — Sample Places API payload for testing with `--mock` (no API key needed).
- `databricks_sentiment.sql` — Databricks SQL pipeline (`ai_analyze_sentiment` + `ai_classify`) to scale multilingual sentiment & topic analysis.
- `dashboard_template.html` & `build_dashboard.py` — Packages `output/*.csv` into either a **single self-contained `dashboard.html`** (default, ready to email/Slack) or a **split** `dashboard.html` + `dashboard_data.js` (`--split`, works over `file://`).
- `dashboard.html` — Built single-file demo dashboard with KPIs, sentiment-over-time confidence bands, interactive Esri map, review-score heatmap, and sortable branch table.
- `favicon.png` — Custom Nordic bank + map pin + review star icon (also inlined into `dashboard.html`).
- `output/` *(gitignored)* — Generated `seb_locations.csv` and `seb_reviews.csv`.

## Usage

Add `GOOGLE_PLACES_API_KEY` to `.env` in the repo root (see `.env.example`), then run:

```bash
# Fetch fresh data for the entire region + build shareable single-file dashboard.html
./google-review-scraping/run.sh

# Rebuild dashboard.html from existing CSVs and open it
./google-review-scraping/run.sh --skip-fetch --open

# Dry-run without calling the API
./google-review-scraping/run.sh --mock
```
