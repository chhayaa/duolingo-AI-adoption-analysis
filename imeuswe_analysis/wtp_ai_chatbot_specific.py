"""
Refined WTP analysis — isolating reviews that specifically mention
AI chatbot features (not just general astrology app reviews).
"""
import pandas as pd
import re

df = pd.read_csv("data/wtp_analysis.csv")

# Keywords that specifically indicate AI CHATBOT discussion
AI_CHATBOT_KEYWORDS = [
    "ai chat", "chatbot", "chat bot", "ai astrologer", "ai reading",
    "ai feature", "ai generated", "artificial intelligence",
    "ask ai", "ai response", "ai answer", "talk to ai",
    "ai prediction", "ai horoscope", "ai assistant",
    "personalized ai", "ai advice", "bot", "gpt",
    "machine learning", "automated reading",
]

# Keywords for PAYMENT specifically
PAYMENT_KEYWORDS = [
    "pay", "paid", "premium", "subscription", "subscribe",
    "price", "cost", "expensive", "cheap", "free", "money",
    "worth", "purchase", "buy", "billing", "charge", "refund",
    "trial", "cancel", "monthly", "yearly", "annual",
    "in-app", "unlock", "upgrade",
]


def has_ai_chatbot_mention(text):
    text_lower = str(text).lower()
    return any(kw in text_lower for kw in AI_CHATBOT_KEYWORDS)


def has_payment_mention(text):
    text_lower = str(text).lower()
    return any(kw in text_lower for kw in PAYMENT_KEYWORDS)


# Tag reviews
df["mentions_ai_chatbot"] = df["clean_text"].apply(has_ai_chatbot_mention)
df["mentions_payment"] = df["clean_text"].apply(has_payment_mention)

# Three categories
ai_chatbot_reviews = df[df["mentions_ai_chatbot"]]
payment_reviews = df[df["mentions_payment"]]
ai_AND_payment = df[df["mentions_ai_chatbot"] & df["mentions_payment"]]
general_astrology = df[~df["mentions_ai_chatbot"] & ~df["mentions_payment"]]

print("=" * 65)
print("REFINED ANALYSIS: AI CHATBOT vs GENERAL ASTROLOGY vs PAYMENT")
print("=" * 65)

print(f"\nTotal reviews: {len(df)}")
print(f"Reviews mentioning AI/chatbot:     {len(ai_chatbot_reviews)} ({len(ai_chatbot_reviews)/len(df)*100:.1f}%)")
print(f"Reviews mentioning payment/price:  {len(payment_reviews)} ({len(payment_reviews)/len(df)*100:.1f}%)")
print(f"Reviews mentioning BOTH:           {len(ai_AND_payment)} ({len(ai_AND_payment)/len(df)*100:.1f}%)")
print(f"General astrology (neither):       {len(general_astrology)} ({len(general_astrology)/len(df)*100:.1f}%)")


def print_category_stats(name, subset):
    if len(subset) == 0:
        print(f"\n  {name}: No reviews found")
        return
    avg_sent = subset["sentiment_score"].mean()
    avg_wtp = subset["wtp_score"].mean()
    willing = (subset["wtp_label"] == "Willing to Pay").sum()
    not_willing = (subset["wtp_label"] == "Not Willing to Pay").sum()
    print(f"\n--- {name} ({len(subset)} reviews) ---")
    print(f"  Avg Sentiment:  {avg_sent:+.4f} ({'Positive' if avg_sent > 0 else 'Negative'})")
    print(f"  Avg WTP Score:  {avg_wtp:+.4f} ({'Willing' if avg_wtp > 0 else 'Resistant'})")
    print(f"  Willing to Pay:     {willing} ({willing/len(subset)*100:.1f}%)")
    print(f"  Not Willing to Pay: {not_willing} ({not_willing/len(subset)*100:.1f}%)")

    # Star rating breakdown
    if "score" in subset.columns:
        avg_stars = subset["score"].mean()
        print(f"  Avg Star Rating: {avg_stars:.2f}/5")


print_category_stats("AI CHATBOT specific reviews", ai_chatbot_reviews)
print_category_stats("PAYMENT specific reviews", payment_reviews)
print_category_stats("AI CHATBOT + PAYMENT (both)", ai_AND_payment)
print_category_stats("General astrology (no AI/payment mention)", general_astrology)

# Show actual AI chatbot review samples
print(f"\n{'=' * 65}")
print("SAMPLE AI CHATBOT REVIEWS (what people actually say)")
print("=" * 65)
if len(ai_chatbot_reviews) > 0:
    samples = ai_chatbot_reviews.nlargest(5, "thumbs_up") if "thumbs_up" in ai_chatbot_reviews.columns else ai_chatbot_reviews.head(5)
    for _, row in samples.iterrows():
        text = str(row["clean_text"])[:200]
        label = row["sentiment_label"]
        wtp = row["wtp_label"]
        app = row["competitor_mentioned"]
        print(f"\n  [{app}] Sentiment={label}, WTP={wtp}")
        print(f"  \"{text}...\"")

# Show AI+Payment reviews
if len(ai_AND_payment) > 0:
    print(f"\n{'=' * 65}")
    print("REVIEWS MENTIONING BOTH AI CHATBOT AND PAYMENT")
    print("=" * 65)
    for _, row in ai_AND_payment.head(10).iterrows():
        text = str(row["clean_text"])[:250]
        label = row["sentiment_label"]
        wtp = row["wtp_label"]
        app = row["competitor_mentioned"]
        print(f"\n  [{app}] Sentiment={label}, WTP={wtp}")
        print(f"  \"{text}\"")

# Final verdict
print(f"\n{'=' * 65}")
print("VERDICT FOR iMeUsWe PAID AI ASTROLOGY CHATBOT")
print("=" * 65)
if len(ai_AND_payment) > 0:
    combo_wtp = ai_AND_payment["wtp_score"].mean()
    combo_sent = ai_AND_payment["sentiment_score"].mean()
    print(f"\nBased on {len(ai_AND_payment)} reviews that discuss BOTH AI chatbot AND payment:")
    print(f"  WTP Score:  {combo_wtp:+.4f}")
    print(f"  Sentiment:  {combo_sent:+.4f}")
    if combo_wtp < 0:
        print("\n  CONCLUSION: Users discussing AI chatbot + payment lean AGAINST paying.")
        print("  Recommendation: Freemium model — free basic AI chat, paid deep features.")
    else:
        print("\n  CONCLUSION: Users discussing AI chatbot + payment show SOME willingness.")
        print("  Recommendation: A paid tier could work, but keep a free entry point.")
elif len(ai_chatbot_reviews) > 0:
    ai_wtp = ai_chatbot_reviews["wtp_score"].mean()
    print(f"\nBased on {len(ai_chatbot_reviews)} AI chatbot reviews (no overlap with payment):")
    print(f"  WTP Score: {ai_wtp:+.4f}")
    print("\n  Not enough data on AI chatbot + payment overlap.")
    print("  Recommendation: Run a user survey within iMeUsWe app for direct signal.")
else:
    print("\n  Very few AI chatbot-specific reviews found in competitor data.")
    print("  The market for paid AI astrology chatbots is still nascent.")
    print("  Recommendation: First-mover advantage possible, but validate with your own users.")
