"""Lightweight multilingual (EN + SV) sentiment baseline for local prototyping."""

from __future__ import annotations

import re

POSITIVE_WORDS = {
    # English
    "great", "helpful", "friendly", "fast", "quick", "professional", "excellent",
    "smooth", "polite", "good", "best", "kind", "easy", "recommend", "efficient",
    # Swedish
    "bra", "trevlig", "trevliga", "hjälpsam", "hjälpsamma", "snabb", "snabbt",
    "professionell", "professionella", "utmärkt", "smidigt", "bästa", "proffsigt",
    "fantastisk", "nöjd", "enkelt", "rekommenderar",
}

NEGATIVE_WORDS = {
    # English
    "bad", "slow", "rude", "terrible", "worst", "horrible", "unhelpful", "wait",
    "waiting", "queue", "closed", "impossible", "frustrating", "poor", "awful",
    "long", "never", "disappointed",
    # Swedish
    "dålig", "dåligt", "långsam", "långsamt", "otrevlig", "otrevliga", "hemskt",
    "värsta", "kö", "vänta", "väntetid", "stängt", "omöjligt", "besviken",
    "frustrerande", "uselt", "katastrof", "aldrig", "krångligt",
}


def analyze_sentiment(text: str, rating: int | None = None) -> tuple[str, float]:
    """Return (label, score) in [-1.0, 1.0] blending EN/SV keywords with star rating."""
    tokens = re.findall(r"[a-zA-ZåäöÅÄÖ]+", (text or "").lower())
    pos_hits = sum(1 for t in tokens if t in POSITIVE_WORDS)
    neg_hits = sum(1 for t in tokens if t in NEGATIVE_WORDS)
    has_lex = (pos_hits + neg_hits) > 0
    lex_score = (pos_hits - neg_hits) / (pos_hits + neg_hits) if has_lex else 0.0

    if rating is not None:
        rating_score = (rating - 3) / 2.0
        score = round(0.6 * lex_score + 0.4 * rating_score, 3) if has_lex else round(rating_score, 3)
    else:
        score = round(lex_score, 3)

    label = "positive" if score >= 0.2 else ("negative" if score <= -0.2 else "neutral")
    return label, score
