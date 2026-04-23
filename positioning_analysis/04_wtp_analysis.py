"""
Step 4: Willingness-to-Pay (WTP) analysis.

Scans cleaned reviews for pricing-related signals, classifies them as
positive / negative / conditional WTP, identifies associated features,
classifies monetization models per app, and detects cross-category
monetization potential.

Outputs:
    data/wtp_results.csv
    data/wtp_summary.json
"""

import json
import os
import re
from collections import Counter

import pandas as pd

from positioning_analysis.config import (
    ANCESTRY_FEATURE_KEYWORDS,
    ANCESTRY_MONETIZATION_KEYWORDS,
    ASTROLOGY_FEATURE_KEYWORDS,
    ASTROLOGY_MONETIZATION_KEYWORDS,
    DATA_DIR,
    MONETIZATION_MODEL_PATTERNS,
    WTP_CONDITIONAL_PATTERNS,
    WTP_NEGATIVE_PATTERNS,
    WTP_POSITIVE_PATTERNS,
)

# ---------------------------------------------------------------------------
# Pre-compile regex patterns for WTP detection
# ---------------------------------------------------------------------------
_ALL_WTP_PATTERNS: list[tuple[str, re.Pattern]] = []
for _pat in WTP_POSITIVE_PATTERNS:
    _ALL_WTP_PATTERNS.append(("positive_wtp", re.compile(re.escape(_pat), re.IGNORECASE)))
for _pat in WTP_NEGATIVE_PATTERNS:
    _ALL_WTP_PATTERNS.append(("negative_wtp", re.compile(re.escape(_pat), re.IGNORECASE)))
for _pat in WTP_CONDITIONAL_PATTERNS:
    _ALL_WTP_PATTERNS.append(("conditional_wtp", re.compile(re.escape(_pat), re.IGNORECASE)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_sentence(text: str, match_start: int, match_end: int) -> str:
    """Return the sentence surrounding a regex match position."""
    # Split on sentence boundaries and find the one containing the match
    sentences = re.split(r"(?<=[.!?])\s+", text)
    pos = 0
    for sentence in sentences:
        sent_start = text.find(sentence, pos)
        if sent_start == -1:
            sent_start = pos
        sent_end = sent_start + len(sentence)
        if sent_start <= match_start < sent_end:
            return sentence.strip()
        pos = sent_end
    # Fallback: return the whole text
    return text.strip()


def _identify_feature(sentence: str, category: str | None = None) -> str | None:
    """Identify a feature mentioned in *sentence* via keyword matching.

    Checks both astrology and ancestry keyword dicts (or just the
    relevant one when *category* is provided).
    """
    sentence_lower = sentence.lower()
    keyword_dicts: list[dict[str, list[str]]] = []
    if category in (None, "astrology"):
        keyword_dicts.append(ASTROLOGY_FEATURE_KEYWORDS)
    if category in (None, "ancestry"):
        keyword_dicts.append(ANCESTRY_FEATURE_KEYWORDS)
    # Also check both for hybrid / unknown
    if category not in (None, "astrology", "ancestry"):
        keyword_dicts = [ASTROLOGY_FEATURE_KEYWORDS, ANCESTRY_FEATURE_KEYWORDS]

    for kw_dict in keyword_dicts:
        for feature_name, kw_list in kw_dict.items():
            for kw in kw_list:
                if kw.lower() in sentence_lower:
                    return feature_name
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_wtp_signals(text: str, category: str | None = None) -> list[dict]:
    """Scan *text* for WTP signal patterns from config.

    For each match, extracts the surrounding sentence as context and
    attempts to identify the associated feature via keyword matching.

    Returns a list of dicts::

        [{"signal_text": str,
          "classification": str,
          "associated_feature": str | None}, ...]
    """
    if not text or not isinstance(text, str):
        return []

    signals: list[dict] = []
    seen_spans: set[tuple[int, int]] = set()

    for classification, pattern in _ALL_WTP_PATTERNS:
        for match in pattern.finditer(text):
            span = (match.start(), match.end())
            if span in seen_spans:
                continue
            seen_spans.add(span)

            sentence = _extract_sentence(text, match.start(), match.end())
            feature = _identify_feature(sentence, category)

            signals.append({
                "signal_text": match.group(),
                "classification": classification,
                "associated_feature": feature,
            })

    return signals


def classify_wtp_signal(signal_text: str) -> str:
    """Classify a single signal phrase as positive_wtp, negative_wtp, or conditional_wtp.

    Checks the phrase against the three pattern lists from config.
    Falls back to ``"positive_wtp"`` if no list matches (shouldn't happen
    when called with text from ``detect_wtp_signals``).
    """
    if not signal_text:
        return "positive_wtp"

    text_lower = signal_text.lower()

    # Check conditional first (some conditional patterns overlap with positive)
    for pat in WTP_CONDITIONAL_PATTERNS:
        if pat.lower() in text_lower:
            return "conditional_wtp"
    for pat in WTP_NEGATIVE_PATTERNS:
        if pat.lower() in text_lower:
            return "negative_wtp"
    for pat in WTP_POSITIVE_PATTERNS:
        if pat.lower() in text_lower:
            return "positive_wtp"

    return "positive_wtp"


def classify_monetization_model(app_reviews: pd.DataFrame) -> tuple[str, float]:
    """Classify the dominant monetization model for an app's reviews.

    Counts keyword matches for each model in ``MONETIZATION_MODEL_PATTERNS``.
    Returns ``(dominant_model, confidence)`` where confidence is
    ``max_count / total_count``.  If no keywords match, returns
    ``("unknown", 0.0)``.
    """
    model_counts: dict[str, int] = {model: 0 for model in MONETIZATION_MODEL_PATTERNS}

    review_texts = app_reviews["review_text"].dropna().astype(str)
    combined_text = " ".join(review_texts).lower()

    for model, keywords in MONETIZATION_MODEL_PATTERNS.items():
        for kw in keywords:
            count = combined_text.count(kw.lower())
            model_counts[model] += count

    total_count = sum(model_counts.values())
    if total_count == 0:
        return ("unknown", 0.0)

    dominant_model = max(model_counts, key=model_counts.get)  # type: ignore[arg-type]
    confidence = model_counts[dominant_model] / total_count
    return (dominant_model, round(confidence, 4))


def analyze_cross_category_monetization(wtp_results: pd.DataFrame) -> dict:
    """Identify ancestry↔astrology WTP crossover.

    Cross-references WTP signals with category-specific monetization
    keywords to find:
    - ancestry users willing to pay for astrology features
    - astrology users willing to pay for ancestry features

    Returns::

        {
            "ancestry_to_astrology_wtp": {"count": int, "features": [str]},
            "astrology_to_ancestry_wtp": {"count": int, "features": [str]},
        }
    """
    a2a_count = 0  # ancestry → astrology
    a2a_features: list[str] = []
    s2a_count = 0  # astrology → ancestry
    s2a_features: list[str] = []

    if wtp_results.empty:
        return {
            "ancestry_to_astrology_wtp": {"count": 0, "features": []},
            "astrology_to_ancestry_wtp": {"count": 0, "features": []},
        }

    for _, row in wtp_results.iterrows():
        category = str(row.get("category", ""))
        signal_text = str(row.get("wtp_signal_text", "")).lower()
        classification = str(row.get("wtp_classification", ""))

        # Only consider positive or conditional WTP signals for crossover
        if classification not in ("positive_wtp", "conditional_wtp"):
            continue

        if category == "ancestry":
            # Check if signal mentions astrology monetization keywords
            for kw in ASTROLOGY_MONETIZATION_KEYWORDS:
                if kw.lower() in signal_text:
                    a2a_count += 1
                    a2a_features.append(kw)
                    break
            else:
                # Also check associated feature
                feature = str(row.get("associated_feature", ""))
                if feature and feature in ASTROLOGY_FEATURE_KEYWORDS:
                    a2a_count += 1
                    a2a_features.append(feature)

        elif category == "astrology":
            # Check if signal mentions ancestry monetization keywords
            for kw in ANCESTRY_MONETIZATION_KEYWORDS:
                if kw.lower() in signal_text:
                    s2a_count += 1
                    s2a_features.append(kw)
                    break
            else:
                feature = str(row.get("associated_feature", ""))
                if feature and feature in ANCESTRY_FEATURE_KEYWORDS:
                    s2a_count += 1
                    s2a_features.append(feature)

    return {
        "ancestry_to_astrology_wtp": {
            "count": a2a_count,
            "features": list(set(a2a_features)),
        },
        "astrology_to_ancestry_wtp": {
            "count": s2a_count,
            "features": list(set(s2a_features)),
        },
    }


# ---------------------------------------------------------------------------
# Category-specific WTP tracking helpers
# ---------------------------------------------------------------------------

def _track_category_wtp(
    wtp_rows: list[dict],
    monetization_keywords: list[str],
    feature_keywords: dict[str, list[str]],
) -> dict:
    """Build category-specific WTP stats (family_tree or astrology).

    Uses *monetization_keywords* to filter relevant signals and
    *feature_keywords* to identify top features.
    """
    total = 0
    positive = 0
    negative = 0
    feature_counter: Counter = Counter()

    all_kw_lower = [kw.lower() for kw in monetization_keywords]
    # Also flatten feature keywords for matching
    all_feature_kw: dict[str, list[str]] = {}
    for feat, kws in feature_keywords.items():
        all_feature_kw[feat] = [k.lower() for k in kws]

    for row in wtp_rows:
        signal_lower = str(row.get("wtp_signal_text", "")).lower()
        feature = row.get("associated_feature")
        classification = row.get("wtp_classification", "")

        # Check if this signal is relevant to the category
        is_relevant = False
        for kw in all_kw_lower:
            if kw in signal_lower:
                is_relevant = True
                break

        if not is_relevant and feature:
            # Check if the associated feature belongs to this category
            if feature in feature_keywords:
                is_relevant = True

        if not is_relevant:
            continue

        total += 1
        if classification == "positive_wtp":
            positive += 1
        elif classification == "negative_wtp":
            negative += 1

        if feature:
            feature_counter[feature] += 1

    top_features = [
        {"feature": feat, "count": cnt}
        for feat, cnt in feature_counter.most_common(10)
    ]

    return {
        "total_signals": total,
        "positive": positive,
        "negative": negative,
        "top_features": top_features,
    }


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def analyze_wtp(input_path: str, output_path: str) -> dict:
    """Run WTP analysis on all cleaned reviews.

    Reads *input_path* (cleaned CSV), detects WTP signals, classifies
    them, writes *output_path* CSV and ``wtp_summary.json``.

    Returns the summary dict.
    """
    df = pd.read_csv(input_path, encoding="utf-8", encoding_errors="replace")

    wtp_rows: list[dict] = []

    for _, row in df.iterrows():
        text = str(row.get("review_text", ""))
        category = str(row.get("category", ""))
        review_id = row.get("review_id", "")
        app_name = row.get("app_name", "")
        market_region = row.get("market_region", "")

        signals = detect_wtp_signals(text, category)

        for sig in signals:
            wtp_rows.append({
                "review_id": review_id,
                "app_name": app_name,
                "category": category,
                "wtp_signal_text": sig["signal_text"],
                "wtp_classification": sig["classification"],
                "associated_feature": sig["associated_feature"],
                "market_region": market_region,
            })

    wtp_df = pd.DataFrame(wtp_rows)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if wtp_df.empty:
        wtp_df = pd.DataFrame(columns=[
            "review_id", "app_name", "category", "wtp_signal_text",
            "wtp_classification", "associated_feature", "market_region",
        ])

    wtp_df.to_csv(output_path, index=False, encoding="utf-8")

    # Build summary
    summary = _build_wtp_summary(df, wtp_df, wtp_rows)

    summary_path = os.path.join(DATA_DIR, "wtp_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def _build_wtp_summary(
    cleaned_df: pd.DataFrame,
    wtp_df: pd.DataFrame,
    wtp_rows: list[dict],
) -> dict:
    """Build the wtp_summary.json structure."""

    # --- per_category ---
    per_category: dict = {}
    if "category" in cleaned_df.columns:
        for cat in cleaned_df["category"].dropna().unique():
            cat_str = str(cat)
            total_reviews = int((cleaned_df["category"] == cat_str).sum())
            if not wtp_df.empty and "category" in wtp_df.columns:
                cat_wtp = wtp_df[wtp_df["category"] == cat_str]
                reviews_with_wtp = int(cat_wtp["review_id"].nunique())
                pos_count = int((cat_wtp["wtp_classification"] == "positive_wtp").sum())
                neg_count = int((cat_wtp["wtp_classification"] == "negative_wtp").sum())
                cond_count = int((cat_wtp["wtp_classification"] == "conditional_wtp").sum())
            else:
                reviews_with_wtp = 0
                pos_count = neg_count = cond_count = 0

            wtp_pct = round(reviews_with_wtp / total_reviews * 100, 2) if total_reviews > 0 else 0.0
            per_category[cat_str] = {
                "total_reviews": total_reviews,
                "reviews_with_wtp": reviews_with_wtp,
                "wtp_pct": wtp_pct,
                "positive_wtp_count": pos_count,
                "negative_wtp_count": neg_count,
                "conditional_wtp_count": cond_count,
            }

    # --- per_region ---
    per_region: dict = {}
    if "market_region" in cleaned_df.columns:
        for region in cleaned_df["market_region"].dropna().unique():
            region_str = str(region)
            total_reviews = int((cleaned_df["market_region"] == region_str).sum())
            if not wtp_df.empty and "market_region" in wtp_df.columns:
                region_wtp = wtp_df[wtp_df["market_region"] == region_str]
                reviews_with_wtp = int(region_wtp["review_id"].nunique())
            else:
                reviews_with_wtp = 0

            wtp_pct = round(reviews_with_wtp / total_reviews * 100, 2) if total_reviews > 0 else 0.0
            per_region[region_str] = {
                "total_reviews": total_reviews,
                "reviews_with_wtp": reviews_with_wtp,
                "wtp_pct": wtp_pct,
            }

    # --- top features willing to pay ---
    pos_feature_counter: Counter = Counter()
    neg_feature_counter: Counter = Counter()
    for row in wtp_rows:
        feature = row.get("associated_feature")
        if not feature:
            continue
        if row["wtp_classification"] == "positive_wtp":
            pos_feature_counter[feature] += 1
        elif row["wtp_classification"] == "negative_wtp":
            neg_feature_counter[feature] += 1

    top_features_willing = [
        {"feature": feat, "positive_wtp_count": cnt}
        for feat, cnt in pos_feature_counter.most_common(10)
    ]
    top_pricing_complaints = [
        {"feature": feat, "negative_wtp_count": cnt}
        for feat, cnt in neg_feature_counter.most_common(10)
    ]

    # --- monetization models per app ---
    monetization_models: dict = {}
    if not cleaned_df.empty and "app_name" in cleaned_df.columns:
        for app_name in cleaned_df["app_name"].dropna().unique():
            app_reviews = cleaned_df[cleaned_df["app_name"] == app_name]
            model, confidence = classify_monetization_model(app_reviews)
            monetization_models[str(app_name)] = {
                "model": model,
                "confidence": confidence,
            }

    # --- cross-category monetization ---
    cross_cat = analyze_cross_category_monetization(wtp_df)

    # --- family tree specific WTP ---
    family_tree_wtp = _track_category_wtp(
        wtp_rows,
        ANCESTRY_MONETIZATION_KEYWORDS,
        ANCESTRY_FEATURE_KEYWORDS,
    )

    # --- astrology specific WTP ---
    astrology_wtp = _track_category_wtp(
        wtp_rows,
        ASTROLOGY_MONETIZATION_KEYWORDS,
        ASTROLOGY_FEATURE_KEYWORDS,
    )

    return {
        "per_category": per_category,
        "per_region": per_region,
        "top_features_willing_to_pay": top_features_willing,
        "top_pricing_complaints": top_pricing_complaints,
        "monetization_models": monetization_models,
        "cross_category_monetization": cross_cat,
        "family_tree_specific_wtp": family_tree_wtp,
        "astrology_specific_wtp": astrology_wtp,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cleaned_path = os.path.join(DATA_DIR, "cleaned_reviews.csv")
    wtp_path = os.path.join(DATA_DIR, "wtp_results.csv")

    if not os.path.exists(cleaned_path):
        print(f"Cleaned data not found at {cleaned_path}. Run 02_clean_data.py first.")
    else:
        summary = analyze_wtp(cleaned_path, wtp_path)
        print("WTP analysis complete:")
        print(json.dumps(summary, indent=2))
