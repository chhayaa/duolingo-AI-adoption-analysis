"""
Step 4: Willingness-to-Pay (WTP) Analysis.
Scores each post/comment on whether users express willingness or refusal to pay
for AI astrology chatbot features.
"""

import pandas as pd
from config import (
    SENTIMENT_OUTPUT_PATH, WTP_OUTPUT_PATH,
    WTP_POSITIVE_KEYWORDS, WTP_NEGATIVE_KEYWORDS,
)


def compute_wtp_score(text):
    """
    Compute a WTP score for a text.
    Positive = willing to pay, Negative = not willing to pay.
    Range: roughly -1 to +1.
    """
    text_lower = text.lower()
    pos_hits = sum(1 for kw in WTP_POSITIVE_KEYWORDS if kw in text_lower)
    neg_hits = sum(1 for kw in WTP_NEGATIVE_KEYWORDS if kw in text_lower)
    total = pos_hits + neg_hits
    if total == 0:
        return 0.0  # Neutral / no WTP signal
    return (pos_hits - neg_hits) / total


def classify_wtp(score):
    if score > 0.1:
        return "Willing to Pay"
    elif score < -0.1:
        return "Not Willing to Pay"
    return "Neutral"


def main():
    df = pd.read_csv(SENTIMENT_OUTPUT_PATH)
    print(f"Running WTP analysis on {len(df)} rows...")

    df["wtp_score"] = df["clean_text"].apply(lambda x: compute_wtp_score(str(x)))
    df["wtp_label"] = df["wtp_score"].apply(classify_wtp)

    df.to_csv(WTP_OUTPUT_PATH, index=False)

    print(f"\nWTP Analysis complete! Saved to {WTP_OUTPUT_PATH}")
    print(f"\nWTP Distribution:\n{df['wtp_label'].value_counts()}")
    print(f"Average WTP Score: {df['wtp_score'].mean():.4f}")

    # Per-competitor breakdown
    print("\n--- WTP by Competitor ---")
    for comp, group in df.groupby("competitor_mentioned"):
        avg_wtp = group["wtp_score"].mean()
        avg_sent = group["sentiment_score"].mean()
        print(f"  {comp}: WTP={avg_wtp:.4f}, Sentiment={avg_sent:.4f}, N={len(group)}")


if __name__ == "__main__":
    main()
