#!/usr/bin/env python3
"""
Package scraped SEB CSV data into a shareable HTML dashboard.

Modes:
    # Single self-contained HTML file (default — easy to email/Slack)
    python3 google-review-scraping/build_dashboard.py

    # Separate data file (keeps dashboard.html small; still works via file://)
    python3 google-review-scraping/build_dashboard.py --split
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_PLACEHOLDER = "<!--__SEB_DATA_TAG__-->"


def load_csv_data(data_dir: Path) -> dict:
    with (data_dir / "seb_locations.csv").open(encoding="utf-8") as f:
        locations = list(csv.DictReader(f))
    with (data_dir / "seb_reviews.csv").open(encoding="utf-8") as f:
        reviews = list(csv.DictReader(f))

    for loc in locations:
        parts = [p.strip() for p in loc["address"].split(",") if p.strip()]
        loc["country"] = parts[-1] if parts else "Unknown"
        loc["city"] = parts[-2] if len(parts) >= 2 else ""

    return {"locations": locations, "reviews": reviews}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SEB sentiment dashboard HTML from CSV outputs.")
    parser.add_argument("--data-dir", type=Path, default=HERE / "output", help="Folder with seb_locations.csv & seb_reviews.csv.")
    parser.add_argument("--template", type=Path, default=HERE / "dashboard_template.html", help="Clean HTML template.")
    parser.add_argument("--out", type=Path, default=HERE / "dashboard.html", help="Output HTML path.")
    parser.add_argument("--split", action="store_true", help="Write data to a separate dashboard_data.js file instead of inlining.")
    args = parser.parse_args()

    payload = load_csv_data(args.data_dir)
    template = args.template.read_text(encoding="utf-8")
    if DATA_PLACEHOLDER not in template:
        raise SystemExit(f"Placeholder {DATA_PLACEHOLDER} not found in {args.template}")

    safe_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    if args.split:
        data_js = args.out.parent / "dashboard_data.js"
        data_js.write_text(f"window.SEB_DATA = {safe_json};\n", encoding="utf-8")
        tag = f'<script src="{data_js.name}"></script>'
        html = template.replace(DATA_PLACEHOLDER, tag, 1)
        args.out.write_text(html, encoding="utf-8")
        print(f"Built split dashboard: {args.out} ({len(html):,} bytes) + {data_js} ({data_js.stat().st_size:,} bytes)")
    else:
        tag = f'<script id="seb-data" type="application/json">{safe_json}</script>'
        html = template.replace(DATA_PLACEHOLDER, tag, 1)
        args.out.write_text(html, encoding="utf-8")
        print(f"Built single-file dashboard: {args.out} ({len(html):,} bytes, {len(payload['locations'])} locations, {len(payload['reviews'])} reviews)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
