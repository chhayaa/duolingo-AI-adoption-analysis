"""
Step 5: Demand overlap analysis.

Scans cleaned reviews for cross-category interest signals — astrology
users wanting ancestry/family features and ancestry users wanting
astrology features.

Outputs:
    data/overlap_results.csv
    data/overlap_summary.json
"""

import json
import os
import re
from collections import Counter

import pandas as pd

from positioning_analysis.config import (
    DATA_DIR,
    OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS,
    OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS,
)

# ---------------------------------------------------------------------------
# Pre-compile keyword patterns for overlap detection
# ---------------------------------------------------------------------------
_ASTROLOGY_TO_ANCESTRY_PATTERNS: list[tuple[str, re.Pattern]] = [
    (kw, re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE))
    for kw in OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS
]

_ANCESTRY_TO_ASTROLOGY_PATTERNS: list[tuple[str, re.Pattern]] = [
    (kw, re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE))
    for kw in OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_overlap_signals(text: str, source_category: str) -> list[dict]:
    """Scan *text* for cross-category interest signals.

    If *source_category* is ``"astrology"``, look for ancestry/family
    keywords from ``OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS``.
    If *source_category* is ``"ancestry"``, look for astrology keywords
    from ``OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS``.

    Returns a list of dicts::

        [{"signal_text": str,
          "target_category": str,
          "cross_feature": str}, ...]
    """
    if not text or not isinstance(text, str):
        return []

    signals: list[dict] = []

    if source_category == "astrology":
        target_category = "ancestry"
        patterns = _ASTROLOGY_TO_ANCESTRY_PATTERNS
    elif source_category == "ancestry":
        target_category = "astrology"
        patterns = _ANCESTRY_TO_ASTROLOGY_PATTERNS
    else:
        # Unknown category — no overlap detection
        return []

    seen_keywords: set[str] = set()
    for keyword, pattern in patterns:
        if pattern.search(text):
            kw_lower = keyword.lower()
            if kw_lower in seen_keywords:
                continue
            seen_keywords.add(kw_lower)
            signals.append({
                "signal_text": keyword,
                "target_category": target_category,
                "cross_feature": keyword,
            })

    return signals


def analyze_overlap(input_path: str, csv_output: str, json_output: str) -> dict:
    """Run overlap analysis on cleaned reviews.

    Reads *input_path* (cleaned CSV), detects cross-category overlap
    signals, writes *csv_output* CSV and *json_output* summary JSON.

    Returns the summary dict.
    """
    df = pd.read_csv(input_path, encoding="utf-8", encoding_errors="replace")

    overlap_rows: list[dict] = []

    for _, row in df.iterrows():
        text = str(row.get("review_text", ""))
        category = str(row.get("category", ""))
        review_id = row.get("review_id", "")
        app_name = row.get("app_name", "")

        signals = detect_overlap_signals(text, category)

        for sig in signals:
            overlap_rows.append({
                "review_id": review_id,
                "app_name": app_name,
                "source_category": category,
                "target_category": sig["target_category"],
                "signal_text": sig["signal_text"],
                "cross_feature": sig["cross_feature"],
            })

    overlap_df = pd.DataFrame(overlap_rows)

    # Ensure output directories exist
    os.makedirs(os.path.dirname(csv_output) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(json_output) or ".", exist_ok=True)

    if overlap_df.empty:
        overlap_df = pd.DataFrame(columns=[
            "review_id", "app_name", "source_category",
            "target_category", "signal_text", "cross_feature",
        ])

    overlap_df.to_csv(csv_output, index=False, encoding="utf-8")

    # Build summary
    summary = _build_overlap_summary(df, overlap_df)

    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def _build_overlap_summary(
    cleaned_df: pd.DataFrame,
    overlap_df: pd.DataFrame,
) -> dict:
    """Build the overlap_summary.json structure.

    Calculates bidirectional overlap percentages and identifies top 10
    cross-category features from each direction.
    """
    # Count total reviews per category
    total_astrology = int((cleaned_df["category"] == "astrology").sum()) if "category" in cleaned_df.columns else 0
    total_ancestry = int((cleaned_df["category"] == "ancestry").sum()) if "category" in cleaned_df.columns else 0

    # Count unique reviews with overlap signals per direction
    if not overlap_df.empty and "source_category" in overlap_df.columns:
        astro_overlap = overlap_df[overlap_df["source_category"] == "astrology"]
        ancestry_overlap = overlap_df[overlap_df["source_category"] == "ancestry"]

        reviews_astro_to_ancestry = int(astro_overlap["review_id"].nunique())
        reviews_ancestry_to_astro = int(ancestry_overlap["review_id"].nunique())
    else:
        reviews_astro_to_ancestry = 0
        reviews_ancestry_to_astro = 0

    # Calculate percentages — guard against zero denominators
    astrology_to_ancestry_pct = (
        round(reviews_astro_to_ancestry / total_astrology * 100, 2)
        if total_astrology > 0
        else 0.0
    )
    ancestry_to_astrology_pct = (
        round(reviews_ancestry_to_astro / total_ancestry * 100, 2)
        if total_ancestry > 0
        else 0.0
    )

    # Top 10 cross-category features from each direction
    top_astro_to_ancestry = _top_cross_features(overlap_df, "astrology", 10)
    top_ancestry_to_astro = _top_cross_features(overlap_df, "ancestry", 10)

    return {
        "astrology_to_ancestry_pct": astrology_to_ancestry_pct,
        "ancestry_to_astrology_pct": ancestry_to_astrology_pct,
        "top_cross_features_astrology_to_ancestry": top_astro_to_ancestry,
        "top_cross_features_ancestry_to_astrology": top_ancestry_to_astro,
    }


def _top_cross_features(
    overlap_df: pd.DataFrame,
    source_category: str,
    top_n: int = 10,
) -> list[dict]:
    """Return the top *top_n* cross-category features for a given source category."""
    if overlap_df.empty or "source_category" not in overlap_df.columns:
        return []

    direction_df = overlap_df[overlap_df["source_category"] == source_category]
    if direction_df.empty:
        return []

    feature_counts = Counter(direction_df["cross_feature"].dropna().astype(str))
    return [
        {"feature": feat, "count": cnt}
        for feat, cnt in feature_counts.most_common(top_n)
    ]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cleaned_path = os.path.join(DATA_DIR, "cleaned_reviews.csv")
    csv_path = os.path.join(DATA_DIR, "overlap_results.csv")
    json_path = os.path.join(DATA_DIR, "overlap_summary.json")

    if not os.path.exists(cleaned_path):
        print(f"Cleaned data not found at {cleaned_path}. Run 02_clean_data.py first.")
    else:
        summary = analyze_overlap(cleaned_path, csv_path, json_path)
        print("Overlap analysis complete:")
        print(json.dumps(summary, indent=2))
