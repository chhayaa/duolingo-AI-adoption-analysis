"""
Step 3: Sentiment analysis with multilingual support.

Uses VADER for English text, googletrans + VADER for non-English text,
a Hinglish keyword boost layer, and star-rating combination.  Extracts
feature-level sentiment using keyword dictionaries from config.

Outputs:
    data/sentiment_results.csv
    data/sentiment_summary.json
"""

import json
import os
import re

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from positioning_analysis.config import (
    ASTROLOGY_FEATURE_KEYWORDS,
    ANCESTRY_FEATURE_KEYWORDS,
    DATA_DIR,
    HINGLISH_SENTIMENT_DICT,
)

# ---------------------------------------------------------------------------
# Module-level VADER instance
# ---------------------------------------------------------------------------
_vader = SentimentIntensityAnalyzer()


# ---------------------------------------------------------------------------
# Translation helper
# ---------------------------------------------------------------------------

def translate_to_english(text: str, source_lang: str) -> tuple:
    """Translate *text* from *source_lang* to English using googletrans.

    Returns ``(translated_text, success_flag)``.  On any failure the
    original text is returned with ``False``.
    """
    if source_lang == "en":
        return text, True
    try:
        from googletrans import Translator
        translator = Translator()
        result = translator.translate(text, src=source_lang, dest="en")
        if result and result.text:
            return result.text, True
        return text, False
    except Exception:
        return text, False


# ---------------------------------------------------------------------------
# Hinglish boost
# ---------------------------------------------------------------------------

def apply_hinglish_boost(text: str, vader_score: float) -> float:
    """Apply Hinglish keyword sentiment boost on top of a VADER score.

    Scans *text* (lowered) for entries in ``HINGLISH_SENTIMENT_DICT``.
    If matches are found their average polarity is blended with the VADER
    score using a 0.3 / 0.7 weighting.
    """
    text_lower = text.lower()
    matched_scores = [
        score
        for phrase, score in HINGLISH_SENTIMENT_DICT.items()
        if phrase in text_lower
    ]
    if not matched_scores:
        return vader_score
    hinglish_avg = sum(matched_scores) / len(matched_scores)
    return 0.3 * hinglish_avg + 0.7 * vader_score


# ---------------------------------------------------------------------------
# Sentiment classification
# ---------------------------------------------------------------------------

def classify_sentiment(
    text: str,
    star_rating: float | None = None,
    language: str = "en",
) -> tuple:
    """Classify sentiment of a single review.

    Returns ``(label, score, method, translated_flag)`` where:
    * *label* – ``"positive"`` / ``"negative"`` / ``"neutral"``
    * *score* – float in ``[-1.0, 1.0]``
    * *method* – one of ``"vader"``, ``"translated_vader"``,
      ``"star_rating_only"``, ``"untranslatable"``
    * *translated_flag* – ``True`` if translation was attempted
    """
    translated_flag = False
    method = "vader"
    text_score: float | None = None

    if language == "en":
        # English – straight VADER
        text_score = _vader.polarity_scores(text)["compound"]
        method = "vader"
    else:
        # Non-English – attempt translation
        translated_text, success = translate_to_english(text, language)
        translated_flag = True

        if success:
            text_score = _vader.polarity_scores(translated_text)["compound"]
            method = "translated_vader"
            # Hinglish boost for Hindi / mixed-language reviews
            if language in ("hi", "mixed"):
                text_score = apply_hinglish_boost(text, text_score)
        else:
            # Translation failed
            if star_rating is not None:
                # Fall back to star-rating only
                method = "star_rating_only"
                text_score = None  # will be handled below
            else:
                # No star rating either – untranslatable neutral
                return ("neutral", 0.0, "untranslatable", translated_flag)

    # Star score normalisation: 1→-1.0, 3→0.0, 5→1.0
    star_score: float | None = None
    if star_rating is not None:
        try:
            star_score = (float(star_rating) - 3) / 2
        except (TypeError, ValueError):
            star_score = None

    # Combine text + star
    if text_score is not None and star_score is not None:
        combined = 0.4 * text_score + 0.6 * star_score
    elif text_score is not None:
        combined = text_score
    elif star_score is not None:
        combined = star_score
    else:
        combined = 0.0

    # Clamp to [-1, 1]
    combined = max(-1.0, min(1.0, combined))

    # Threshold
    if combined > 0.05:
        label = "positive"
    elif combined < -0.05:
        label = "negative"
    else:
        label = "neutral"

    return (label, round(combined, 4), method, translated_flag)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def extract_features(text: str, category: str, translated_text: str | None = None) -> list:
    """Extract feature mentions from *text* using keyword dictionaries.

    For non-English reviews *translated_text* can be supplied so that
    matching runs on both the original and translated versions.

    Returns a list of dicts:
    ``[{"feature_name": str, "sentiment_label": str, "sentiment_score": float}, ...]``
    """
    keywords = {}
    if category == "astrology":
        keywords = ASTROLOGY_FEATURE_KEYWORDS
    elif category == "ancestry":
        keywords = ANCESTRY_FEATURE_KEYWORDS
    else:
        # For hybrid or unknown, check both
        keywords = {**ASTROLOGY_FEATURE_KEYWORDS, **ANCESTRY_FEATURE_KEYWORDS}

    texts_to_search = [text.lower()]
    if translated_text and translated_text.lower() != text.lower():
        texts_to_search.append(translated_text.lower())

    found_features: list[dict] = []
    seen_features: set[str] = set()

    for feature_name, kw_list in keywords.items():
        for search_text in texts_to_search:
            matched = False
            for kw in kw_list:
                if kw.lower() in search_text:
                    matched = True
                    break
            if matched and feature_name not in seen_features:
                seen_features.add(feature_name)
                # Compute per-feature sentiment on the sentence containing the keyword
                sentence_score = _get_feature_sentence_sentiment(text, kw_list)
                if sentence_score > 0.05:
                    feat_label = "positive"
                elif sentence_score < -0.05:
                    feat_label = "negative"
                else:
                    feat_label = "neutral"
                found_features.append({
                    "feature_name": feature_name,
                    "sentiment_label": feat_label,
                    "sentiment_score": round(sentence_score, 4),
                })
                break  # already found in one of the texts

    return found_features


def _get_feature_sentence_sentiment(text: str, keywords: list) -> float:
    """Find the sentence containing a keyword and return its VADER score."""
    sentences = re.split(r"[.!?]+", text)
    for sentence in sentences:
        sentence_lower = sentence.lower()
        for kw in keywords:
            if kw.lower() in sentence_lower:
                score = _vader.polarity_scores(sentence.strip())["compound"]
                return score
    # Fallback: score the whole text
    return _vader.polarity_scores(text)["compound"]


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def analyze_sentiment(input_path: str, output_path: str) -> dict:
    """Run sentiment analysis on all cleaned reviews.

    Reads *input_path* (cleaned CSV), classifies sentiment, extracts
    features, writes *output_path* CSV and ``sentiment_summary.json``.

    Returns the summary dict.
    """
    df = pd.read_csv(input_path, encoding="utf-8", encoding_errors="replace")

    results = []
    for _, row in df.iterrows():
        text = str(row.get("review_text", ""))
        star_raw = row.get("star_rating", None)
        star_rating = None
        if pd.notna(star_raw):
            try:
                star_rating = float(star_raw)
            except (TypeError, ValueError):
                star_rating = None
        language = str(row.get("language", "en"))
        category = str(row.get("category", ""))

        label, score, method, translated = classify_sentiment(
            text, star_rating, language
        )

        # Determine translated text for feature extraction
        translated_text = None
        if translated and method == "translated_vader":
            translated_text, _ = translate_to_english(text, language)

        features = extract_features(text, category, translated_text)

        feature_names = [f["feature_name"] for f in features]
        feature_sentiments = {
            f["feature_name"]: {
                "label": f["sentiment_label"],
                "score": f["sentiment_score"],
            }
            for f in features
        }

        results.append({
            "review_id": row.get("review_id", ""),
            "app_name": row.get("app_name", ""),
            "category": category,
            "overall_sentiment": label,
            "sentiment_score": score,
            "feature_mentions": json.dumps(feature_names),
            "feature_sentiments": json.dumps(feature_sentiments),
            "language": language,
            "sentiment_method": method,
            "translated": translated,
        })

    out_df = pd.DataFrame(results)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    out_df.to_csv(output_path, index=False, encoding="utf-8")

    # Build summary
    summary = _build_summary(out_df, results)

    summary_path = os.path.join(DATA_DIR, "sentiment_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def _build_summary(df: pd.DataFrame, results: list) -> dict:
    """Build the sentiment_summary.json structure."""

    def _group_stats(group_df: pd.DataFrame) -> dict:
        count = len(group_df)
        if count == 0:
            return {
                "avg_score": 0.0,
                "positive_pct": 0.0,
                "negative_pct": 0.0,
                "neutral_pct": 0.0,
                "review_count": 0,
            }
        return {
            "avg_score": round(float(group_df["sentiment_score"].mean()), 4),
            "positive_pct": round(
                float((group_df["overall_sentiment"] == "positive").sum() / count * 100), 2
            ),
            "negative_pct": round(
                float((group_df["overall_sentiment"] == "negative").sum() / count * 100), 2
            ),
            "neutral_pct": round(
                float((group_df["overall_sentiment"] == "neutral").sum() / count * 100), 2
            ),
            "review_count": count,
        }

    # Per-app
    per_app = {}
    if "app_name" in df.columns:
        for app, grp in df.groupby("app_name"):
            per_app[str(app)] = _group_stats(grp)

    # Per-category
    per_category = {}
    if "category" in df.columns:
        for cat, grp in df.groupby("category"):
            per_category[str(cat)] = _group_stats(grp)

    # Per-region – requires market_region; if missing, skip
    per_region: dict = {}
    if "market_region" in df.columns:
        for region, grp in df.groupby("market_region"):
            per_region[str(region)] = _group_stats(grp)

    # Feature aggregation
    feature_scores: dict[str, list[float]] = {}
    for row in results:
        feat_sents = json.loads(row["feature_sentiments"])
        for feat_name, info in feat_sents.items():
            feature_scores.setdefault(feat_name, []).append(info["score"])

    praised = sorted(
        [
            {
                "feature": feat,
                "avg_score": round(sum(scores) / len(scores), 4),
                "mention_count": len(scores),
            }
            for feat, scores in feature_scores.items()
            if sum(scores) / len(scores) > 0.05
        ],
        key=lambda x: x["avg_score"],
        reverse=True,
    )[:10]

    criticized = sorted(
        [
            {
                "feature": feat,
                "avg_score": round(sum(scores) / len(scores), 4),
                "mention_count": len(scores),
            }
            for feat, scores in feature_scores.items()
            if sum(scores) / len(scores) < -0.05
        ],
        key=lambda x: x["avg_score"],
    )[:10]

    return {
        "per_app": per_app,
        "per_category": per_category,
        "per_region": per_region,
        "top_praised_features": praised,
        "top_criticized_features": criticized,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cleaned_path = os.path.join(DATA_DIR, "cleaned_reviews.csv")
    sentiment_path = os.path.join(DATA_DIR, "sentiment_results.csv")

    if not os.path.exists(cleaned_path):
        print(f"Cleaned data not found at {cleaned_path}. Run 02_clean_data.py first.")
    else:
        summary = analyze_sentiment(cleaned_path, sentiment_path)
        print("Sentiment analysis complete:")
        print(json.dumps(summary, indent=2))
