"""Quick WTP report for iMeUsWe decision-making."""
import pandas as pd

df = pd.read_csv("data/wtp_analysis.csv")

print("=" * 60)
print("WILLINGNESS TO PAY — FULL BREAKDOWN")
print("=" * 60)

total = len(df)
willing = (df["wtp_label"] == "Willing to Pay").sum()
not_willing = (df["wtp_label"] == "Not Willing to Pay").sum()
neutral = (df["wtp_label"] == "Neutral").sum()

print(f"\nTotal reviews analyzed: {total}")
print(f"Willing to Pay:      {willing} ({willing/total*100:.1f}%)")
print(f"Not Willing to Pay:  {not_willing} ({not_willing/total*100:.1f}%)")
print(f"Neutral (no signal): {neutral} ({neutral/total*100:.1f}%)")
print(f"\nAvg WTP Score: {df['wtp_score'].mean():.4f}")

# Only AI/payment related reviews
ai_df = df[df["is_ai_payment_related"] == True]
print(f"\n{'=' * 60}")
print(f"AI/PAYMENT RELATED REVIEWS ONLY ({len(ai_df)} reviews)")
print("=" * 60)
ai_willing = (ai_df["wtp_label"] == "Willing to Pay").sum()
ai_not = (ai_df["wtp_label"] == "Not Willing to Pay").sum()
ai_neutral = (ai_df["wtp_label"] == "Neutral").sum()
print(f"Willing to Pay:      {ai_willing} ({ai_willing/len(ai_df)*100:.1f}%)")
print(f"Not Willing to Pay:  {ai_not} ({ai_not/len(ai_df)*100:.1f}%)")
print(f"Neutral:             {ai_neutral} ({ai_neutral/len(ai_df)*100:.1f}%)")
print(f"Avg WTP Score: {ai_df['wtp_score'].mean():.4f}")
print(f"Avg Sentiment: {ai_df['sentiment_score'].mean():.4f}")

# Per competitor for AI-related
print(f"\n{'=' * 60}")
print("PER COMPETITOR — AI/PAYMENT REVIEWS")
print("=" * 60)
for comp, g in ai_df.groupby("competitor_mentioned"):
    w = (g["wtp_label"] == "Willing to Pay").sum()
    nw = (g["wtp_label"] == "Not Willing to Pay").sum()
    avg_wtp = g["wtp_score"].mean()
    avg_sent = g["sentiment_score"].mean()
    print(f"  {comp:15s} | WTP={avg_wtp:+.4f} | Sentiment={avg_sent:+.4f} | Willing={w} | NotWilling={nw} | N={len(g)}")

# The key disconnect
print(f"\n{'=' * 60}")
print("THE KEY INSIGHT — SENTIMENT vs PAYMENT DISCONNECT")
print("=" * 60)
pos_sent = df[df["sentiment_label"] == "positive"]
pos_wtp = (pos_sent["wtp_label"] == "Willing to Pay").sum()
pos_nwtp = (pos_sent["wtp_label"] == "Not Willing to Pay").sum()
print(f"Among {len(pos_sent)} POSITIVE sentiment reviews:")
print(f"  Only {pos_wtp} ({pos_wtp/len(pos_sent)*100:.1f}%) are willing to pay")
print(f"  {pos_nwtp} ({pos_nwtp/len(pos_sent)*100:.1f}%) are NOT willing to pay")
print(f"\nRatio of Not-Willing to Willing: {not_willing/max(willing,1):.1f}x")
