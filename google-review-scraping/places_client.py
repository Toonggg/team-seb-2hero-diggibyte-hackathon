"""Google Places API (New) client and SEB branch filter."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.primaryType",
        "places.types",
        "places.rating",
        "places.userRatingCount",
        "places.reviews",
        "places.googleMapsLinks",
        "nextPageToken",
    ]
)

SWEDEN_QUERIES = [
    "SEB bank Sweden",
    "SEB Kort",
    "SEB bank Stockholm", "SEB bank Göteborg", "SEB bank Malmö",
    "SEB bank Uppsala", "SEB bank Linköping", "SEB bank Örebro",
    "SEB bank Västerås", "SEB bank Helsingborg", "SEB bank Norrköping",
    "SEB bank Jönköping", "SEB bank Umeå", "SEB bank Lund",
    "SEB bank Borås", "SEB bank Sundsvall", "SEB bank Gävle",
    "SEB bank Karlstad", "SEB bank Växjö", "SEB bank Halmstad",
    "SEB bank Eskilstuna", "SEB bank Luleå", "SEB bank Kalmar",
    "SEB bank Kristianstad", "SEB bank Skövde", "SEB bank Östersund",
    "SEB bank Visby",
]

NORDICS_BALTICS_QUERIES = [
    "SEB bank Norway", "SEB bank Denmark", "SEB bank Finland",
    "SEB bank Oslo", "SEB bank Copenhagen", "SEB bank Helsinki",
    "SEB bank Tallinn", "SEB bank Riga", "SEB bank Vilnius",
]

REGION_PRESETS = {
    "sweden": SWEDEN_QUERIES,
    "all": SWEDEN_QUERIES + NORDICS_BALTICS_QUERIES,
}

SEB_NAME_RE = re.compile(r"\bseb\b", re.IGNORECASE)
ATM_NAME_RE = re.compile(r"\b(atm|bankomat\w*|uttagsautomat|kontantautomat)\b", re.IGNORECASE)
ALLOWED_TYPES = {"bank", "finance", "corporate_office", "financial_institution"}


def is_seb_branch(place: dict) -> bool:
    """Return True if the place is an actual SEB office (excluding ATMs and other businesses)."""
    name = (place.get("displayName") or {}).get("text", "")
    if not SEB_NAME_RE.search(name) or ATM_NAME_RE.search(name):
        return False

    primary_type = (place.get("primaryType") or "").lower()
    types = {t.lower() for t in place.get("types") or []}

    if primary_type == "atm":
        return False
    if (primary_type or types) and primary_type not in ALLOWED_TYPES and not (types & ALLOWED_TYPES):
        return False
    return True


def search_places_text(
    api_key: str,
    query: str,
    max_pages: int = 3,
    language_code: str = "en",
) -> list[dict]:
    """Fetch up to 60 places (3 pages x 20) from Google Places API (New) Text Search."""
    places: list[dict] = []
    page_token: str | None = None

    for _ in range(max_pages):
        payload: dict = {"textQuery": query, "pageSize": 20, "languageCode": language_code}
        if page_token:
            payload["pageToken"] = page_token

        req = urllib.request.Request(
            PLACES_SEARCH_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Google Places API error {e.code} for '{query}': {err_body}") from e

        places.extend(data.get("places", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(0.5)

    return places
