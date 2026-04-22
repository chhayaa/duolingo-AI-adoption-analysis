"""
Step 3: Sentiment analysis using the review star ratings + keyword-based NLP.
Fast approach that doesn't need a GPU — uses the actual review scores from
Google Play (1-5 stars) combined with text-based sentiment keywords for nuance.
"""

import pandas as pd
import numpy as np
import re
from config import CLEANED_DATA_PATH, SENTIMENT_OUTPUT_PATH

# Sentiment keyword lists for fine-tuning beyond star ratings
POSITIVE_WORDS = {
    "love", "amazing", "great", "awesome", "excellent", "best", "perfect",
    "helpful", "accurate", "beautiful", "fantastic", "wonderful", "enjoy",
    "recommend", "useful", "good", "nice", "happy", "insightful", "cool",
    "fun", "interesting", "reliable", "impressive", "intuitive",
}

NEGATIVE_WORDS = {
    "hate", "terrible", "worst", "awful", "horrible", "useless", "scam",
    "waste", "annoying", "frustrating", "disappointing", "broken", "fake",
    "trash", "garbage", "stupid", "boring", "crash", "crashes", "bug",
    "buggy", "slow", "spam", "misleading", "ripoff", "rip-off", "sucks",
    "poor", "bad", "ugly", "confusing", "inaccurate", "unreliable",
}


def compute_sentiment(row):
    """
    Compute sentiment using star rating (primary) + text keywords (secondary).
    Returns: label, score (-1 to +1), confidence (0 to 1)
    """
    text = str(row.get("clean_text", "")).lower()
    star_rating = row.get("score", 3)

    # Base score from star rating: 1 star = -1.0, 3 stars = 0.0, 5 stars = +1.0
    base_score = (star_rating - 3) / 2.0

    # Text-based adjustment
    words = set(re.findall(r'\b\w+\b', text))
    pos_count = len(words & POSITIVE_WORDS)
    neg_count = len(words & NEGATIVE_WORDS)

    text_adjustment = 0.0
    if pos_count + neg_count > 0:
        text_adjustment = (pos_count - neg_count) / (pos_count + neg_count) * 0.2

    # Combined score
    final_score = np.clip(base_score + text_adjustment, -1.0, 1.0)

    # Label
    if final_score > 0.1:
        label = "positive"
    elif final_score < -0.1:
        label = "negative"
    else:
        label = "neutral"

    # Confidence based on how extreme the score is
    confidence = abs(final_score)

    return label, round(final_score, 4), round(confidence, 4)


def main():
    df = pd.read_csv(CLEANED_DATA_PATH)
    print(f"Running sentiment analysis on {len(df)} rows...")

    results = df.apply(compute_sentiment, axis=1)
    df["sentiment_label"] = [r[0] for r in results]
    df["sentiment_score"] = [r[1] for r in results]
    df["sentiment_confidence"] = [r[2] for r in results]

    df.to_csv(SENTIMENT_OUTPUT_PATH, index=False)

    print(f"\nSentiment analysis complete! Saved to {SENTIMENT_OUTPUT_PATH}")
    print(f"\nSentiment distribution:\n{df['sentiment_label'].value_counts()}")
    print(f"Average sentiment score: {df['sentiment_score'].mean():.4f}")

    # Per-competitor breakdown
    print("\n--- Sentiment by Competitor ---")
    for comp, group in df.groupby("competitor_mentioned"):
        avg = group["sentiment_score"].mean()
        print(f"  {comp}: avg_sentiment={avg:.4f}, N={len(group)}")


if __name__ == "__main__":
    main()
