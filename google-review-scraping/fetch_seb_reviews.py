#!/usr/bin/env python3
"""CLI entrypoint to fetch SEB Google reviews, score sentiment, and export CSVs."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from places_client import REGION_PRESETS, is_seb_branch, search_places_text
from sentiment import analyze_sentiment

HERE = Path(__file__).resolve().parent


def load_dotenv(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def process_places(places: list[dict], filter_seb_only: bool = True) -> tuple[list[dict], list[dict], dict]:
    seen_ids: set[str] = set()
    locations, reviews_out = [], []
    stats = {"raw": len(places), "duplicates": 0, "filtered": 0}

    for place in places:
        place_id = place.get("id")
        if not place_id:
            continue
        if place_id in seen_ids:
            stats["duplicates"] += 1
            continue
        seen_ids.add(place_id)

        if filter_seb_only and not is_seb_branch(place):
            stats["filtered"] += 1
            continue

        name = (place.get("displayName") or {}).get("text", "")
        address = place.get("formattedAddress", "")
        loc = place.get("location") or {}
        reviews = place.get("reviews", [])

        counts = {"positive": 0, "neutral": 0, "negative": 0}
        scores, ratings = [], []

        for idx, rev in enumerate(reviews, start=1):
            rev_rating = rev.get("rating")
            text_obj = rev.get("originalText") or rev.get("text") or {}
            rev_text = text_obj.get("text", "").strip()
            label, score = analyze_sentiment(rev_text, rev_rating)

            counts[label] += 1
            scores.append(score)
            if rev_rating is not None:
                ratings.append(rev_rating)

            reviews_out.append({
                "place_id": place_id,
                "location_name": name,
                "address": address,
                "review_index": idx,
                "author": (rev.get("authorAttribution") or {}).get("displayName", ""),
                "publish_time": rev.get("publishTime", ""),
                "language": text_obj.get("languageCode", ""),
                "review_rating": rev_rating,
                "review_text": rev_text,
                "sentiment_label": label,
                "sentiment_score": score,
            })

        locations.append({
            "place_id": place_id,
            "location_name": name,
            "address": address,
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
            "primary_type": place.get("primaryType", ""),
            "reviews_uri": (place.get("googleMapsLinks") or {}).get("reviewsUri", ""),
            "google_avg_rating": place.get("rating"),
            "google_total_reviews": place.get("userRatingCount", 0),
            "sampled_reviews_count": len(reviews),
            "sampled_avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "avg_sentiment_score": round(sum(scores) / len(scores), 3) if scores else None,
            "positive_reviews": counts["positive"],
            "neutral_reviews": counts["neutral"],
            "negative_reviews": counts["negative"],
        })

    return locations, reviews_out, stats


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_summary(locations: list[dict]) -> None:
    print(f"\n{'Location':<20} {'Address':<36} {'Avg':>5} {'Total':>6} {'Sent':>7} {'Pos/Neu/Neg':>12}")
    print("-" * 92)
    for row in sorted(locations, key=lambda r: (r["google_avg_rating"] or 0), reverse=True):
        avg = f"{row['google_avg_rating']:.2f}" if row["google_avg_rating"] is not None else "N/A"
        sent = f"{row['avg_sentiment_score']:+.2f}" if row["avg_sentiment_score"] is not None else "N/A"
        pos_neu_neg = f"{row['positive_reviews']}/{row['neutral_reviews']}/{row['negative_reviews']}"
        print(
            f"{row['location_name'][:19]:<20} {row['address'][:35]:<36} "
            f"{avg:>5} {row['google_total_reviews']:>6} {sent:>7} {pos_neu_neg:>12}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch SEB branch Google reviews & sentiment.")
    parser.add_argument("--region", choices=sorted(REGION_PRESETS), default="sweden")
    parser.add_argument("--queries", nargs="+", default=None, help="Custom queries (overrides --region).")
    parser.add_argument("--max-pages", type=int, default=3, help="Pages per query (max 3).")
    parser.add_argument("--no-filter", action="store_true", help="Keep ATMs & non-SEB results.")
    parser.add_argument("--output-dir", type=Path, default=HERE / "output")
    parser.add_argument("--mock", action="store_true", help="Run using mock_data.json.")
    args = parser.parse_args()

    load_dotenv(Path(".env"))

    if args.mock:
        raw_places = json.loads((HERE / "mock_data.json").read_text(encoding="utf-8"))
    else:
        api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
        if not api_key:
            print("Error: set GOOGLE_PLACES_API_KEY in .env or run with --mock.", file=sys.stderr)
            return 1
        queries = args.queries or REGION_PRESETS[args.region]
        raw_places = []
        for q in queries:
            found = search_places_text(api_key, q, max_pages=args.max_pages)
            print(f"{q}: {len(found)} places")
            raw_places.extend(found)

    locations, reviews, stats = process_places(raw_places, filter_seb_only=not args.no_filter)
    write_csv(args.output_dir / "seb_locations.csv", locations)
    write_csv(args.output_dir / "seb_reviews.csv", reviews)

    print(f"\nProcessed {stats['raw']} raw ({stats['duplicates']} dupes, {stats['filtered']} filtered).")
    print_summary(locations)
    print(f"\nSaved {len(locations)} locations and {len(reviews)} reviews to {args.output_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
