#!/usr/bin/env bash
# Fetch fresh SEB Google Reviews CSVs and package them into a shareable HTML dashboard.
#
# Usage:
#   ./google-review-scraping/run.sh                 # Full region (Sweden + Nordics + Baltics) -> dashboard.html
#   ./google-review-scraping/run.sh --region sweden # Sweden only -> dashboard.html
#   ./google-review-scraping/run.sh --skip-fetch    # Rebuild dashboard.html from existing CSVs
#   ./google-review-scraping/run.sh --split         # Output dashboard.html + separate dashboard_data.js
#   ./google-review-scraping/run.sh --open          # Open dashboard.html in your browser when done

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REGION="all"
SKIP_FETCH=false
MOCK=false
SPLIT=false
OPEN_BROWSER=false
OUT_HTML="${SCRIPT_DIR}/dashboard.html"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region)     REGION="$2"; shift 2 ;;
    --skip-fetch) SKIP_FETCH=true; shift ;;
    --mock)       MOCK=true; shift ;;
    --split)      SPLIT=true; shift ;;
    --out)        OUT_HTML="$2"; shift 2 ;;
    --open)       OPEN_BROWSER=true; shift ;;
    -h|--help)
      sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $1 (use --help for usage)" >&2
      exit 1
      ;;
  esac
done

cd "${REPO_ROOT}"

if [[ "${SKIP_FETCH}" == false ]]; then
  echo "==> [1/2] Fetching SEB Google reviews (region: ${REGION})..."
  if [[ "${MOCK}" == true ]]; then
    python3 "${SCRIPT_DIR}/fetch_seb_reviews.py" --mock
  else
    python3 "${SCRIPT_DIR}/fetch_seb_reviews.py" --region "${REGION}"
  fi
else
  echo "==> [1/2] Skipping fetch — using existing CSVs in google-review-scraping/output/"
fi

echo "==> [2/2] Building shareable dashboard..."
BUILD_ARGS=(--out "${OUT_HTML}")
if [[ "${SPLIT}" == true ]]; then
  BUILD_ARGS+=(--split)
fi
python3 "${SCRIPT_DIR}/build_dashboard.py" "${BUILD_ARGS[@]}"

echo ""
echo "Done! Shareable dashboard ready at:"
echo "  ${OUT_HTML}"

if [[ "${OPEN_BROWSER}" == true ]]; then
  open "${OUT_HTML}" 2>/dev/null || xdg-open "${OUT_HTML}" 2>/dev/null || true
fi
