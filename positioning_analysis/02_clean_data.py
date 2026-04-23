"""
Step 2: Clean and preprocess the scraped review data.

Reads raw_reviews.csv produced by the scraper, deduplicates, normalises text,
detects language, discards short reviews, assigns UUIDs, and writes
cleaned_reviews.csv plus a cleaning_summary.json.
"""

import json
import os
import re
import uuid

import pandas as pd
from langdetect import detect, LangDetectException

from positioning_analysis.config import DATA_DIR


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate reviews based on (review_text, app_name) pair."""
    return df.drop_duplicates(subset=["review_text", "app_name"], keep="first")


def normalize_text(text: str) -> str:
    """Strip HTML tags, special characters, excessive whitespace.

    Preserves alphanumeric characters, spaces, and basic punctuation
    (.,!?'-).
    """
    if not isinstance(text, str):
        return ""
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Replace special characters – keep alphanumeric, spaces, basic punctuation
    text = re.sub(r"[^\w\s.,!?'\-]", " ", text)
    # Collapse multiple whitespace to single space
    text = re.sub(r"\s+", " ", text)
    # Strip leading/trailing whitespace
    return text.strip()


def detect_language(text: str) -> str:
    """Detect language using langdetect. Returns ISO 639-1 code.

    Returns ``"unknown"`` when detection fails or text is too short.
    """
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"
    except Exception:  # pragma: no cover – safety net
        return "unknown"


# ---------------------------------------------------------------------------
# Main cleaning pipeline
# ---------------------------------------------------------------------------


def clean_reviews(input_path: str, output_path: str) -> dict:
    """Full cleaning pipeline.

    1. Read raw CSV (utf-8, errors='replace')
    2. Deduplicate on (review_text, app_name)
    3. Normalise text
    4. Detect language
    5. Discard reviews < 10 chars after normalisation
    6. Assign UUIDs
    7. Write cleaned CSV and cleaning summary JSON

    Returns the cleaning summary dict.
    """
    # 1. Read raw data
    df = pd.read_csv(input_path, encoding="utf-8", encoding_errors="replace")
    total_collected = len(df)

    # 2. Deduplicate
    df = remove_duplicates(df)
    duplicates_removed = total_collected - len(df)

    # 3. Normalise text
    df = df.copy()
    df["review_text"] = df["review_text"].apply(normalize_text)

    # 4. Discard short reviews (< 10 chars)
    before_short = len(df)
    df = df[df["review_text"].str.len() >= 10].copy()
    short_reviews_discarded = before_short - len(df)

    # 5. Detect language
    df["language"] = df["review_text"].apply(detect_language)

    # 6. Assign UUIDs
    df["review_id"] = [str(uuid.uuid4()) for _ in range(len(df))]

    # 7. Build output DataFrame with required columns
    output_columns = [
        "review_id",
        "app_name",
        "category",
        "review_text",
        "star_rating",
        "review_date",
        "review_source",
        "language",
        "market_region",
    ]
    # Ensure all expected columns exist (fill missing with empty string)
    for col in output_columns:
        if col not in df.columns:
            df[col] = ""

    df_out = df[output_columns]
    df_out.to_csv(output_path, index=False, encoding="utf-8")

    # Per-app counts
    per_app_counts = df_out["app_name"].value_counts().to_dict()

    final_count = len(df_out)

    summary = {
        "total_collected": total_collected,
        "duplicates_removed": duplicates_removed,
        "short_reviews_discarded": short_reviews_discarded,
        "final_count": final_count,
        "per_app_counts": per_app_counts,
    }

    # Write summary JSON
    summary_path = os.path.join(DATA_DIR, "cleaning_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    raw_path = os.path.join(DATA_DIR, "raw_reviews.csv")
    cleaned_path = os.path.join(DATA_DIR, "cleaned_reviews.csv")

    if not os.path.exists(raw_path):
        print(f"Raw data not found at {raw_path}. Run 01_scrape_reviews.py first.")
    else:
        summary = clean_reviews(raw_path, cleaned_path)
        print("Cleaning complete:")
        print(json.dumps(summary, indent=2))
