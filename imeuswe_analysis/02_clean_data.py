"""
Step 2: Clean and preprocess the scraped review data.
"""

import pandas as pd
import re
from config import RAW_DATA_PATH, CLEANED_DATA_PATH


def clean_text(text):
    """Clean a single text entry."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"http\S+|www\.\S+", "", text)  # Remove URLs
    text = re.sub(r"[^\w\s.,!?'-]", " ", text)  # Remove special chars
    text = re.sub(r"\n+", " ", text)  # Newlines to spaces
    text = re.sub(r"\s+", " ", text)  # Collapse whitespace
    return text.strip()


# Keywords that indicate the review is about AI/chatbot/premium features
AI_KEYWORDS = [
    "ai", "chatbot", "chat bot", "artificial intelligence", "premium",
    "subscription", "paid", "pay", "price", "expensive", "free",
    "pro version", "upgrade", "unlock", "monthly", "yearly",
    "in-app purchase", "worth", "money", "cost",
    "personalized", "reading", "horoscope", "prediction",
]


def is_relevant(text):
    """Check if review mentions AI, chatbot, or payment-related topics."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in AI_KEYWORDS)


def main():
    df = pd.read_csv(RAW_DATA_PATH)
    print(f"Loaded {len(df)} rows")

    # Clean text
    df["clean_text"] = df["text"].apply(clean_text)

    # Remove very short reviews
    df = df[df["clean_text"].str.len() > 20].copy()

    # Tag relevance — keep all reviews but flag relevant ones
    df["is_ai_payment_related"] = df["clean_text"].apply(is_relevant)

    relevant_count = df["is_ai_payment_related"].sum()
    print(f"AI/payment related reviews: {relevant_count} out of {len(df)}")

    # Keep relevant columns
    df = df[[
        "app_name", "clean_text", "score", "thumbs_up",
        "date", "is_ai_payment_related",
    ]].copy()

    # Rename for consistency with downstream scripts
    df = df.rename(columns={"app_name": "competitor_mentioned"})

    df.to_csv(CLEANED_DATA_PATH, index=False)
    print(f"Cleaned data: {len(df)} rows saved to {CLEANED_DATA_PATH}")
    print(f"\nPer-app distribution:\n{df['competitor_mentioned'].value_counts()}")


if __name__ == "__main__":
    main()
