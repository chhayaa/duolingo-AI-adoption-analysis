"""
Step 5: Visualize results — sentiment distribution, WTP analysis,
competitor comparison, and the key insight for iMeUsWe pricing decisions.
"""

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — saves to file only
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from config import WTP_OUTPUT_PATH, REPORT_OUTPUT_PATH


def main():
    df = pd.read_csv(WTP_OUTPUT_PATH)
    os.makedirs("output", exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(
        "iMeUsWe AI Astrology Chatbot — Paid Feature Viability Analysis\n"
        "(Based on Competitor Sentiment & WTP from Reddit)",
        fontsize=14, fontweight="bold",
    )

    # 1. Overall Sentiment Distribution
    ax1 = axes[0, 0]
    sent_counts = df["sentiment_label"].value_counts()
    colors_sent = {"positive": "#2ecc71", "neutral": "#3498db", "negative": "#e74c3c"}
    sent_counts.plot(
        kind="bar",
        ax=ax1,
        color=[colors_sent.get(x, "#95a5a6") for x in sent_counts.index],
    )
    ax1.set_title("Overall Sentiment Distribution")
    ax1.set_xlabel("Sentiment")
    ax1.set_ylabel("Count")
    ax1.tick_params(axis="x", rotation=0)

    # 2. WTP Distribution
    ax2 = axes[0, 1]
    wtp_counts = df["wtp_label"].value_counts()
    colors_wtp = {
        "Willing to Pay": "#2ecc71",
        "Neutral": "#3498db",
        "Not Willing to Pay": "#e74c3c",
    }
    wtp_counts.plot(
        kind="bar",
        ax=ax2,
        color=[colors_wtp.get(x, "#95a5a6") for x in wtp_counts.index],
    )
    ax2.set_title("Willingness to Pay Distribution")
    ax2.set_xlabel("WTP Category")
    ax2.set_ylabel("Count")
    ax2.tick_params(axis="x", rotation=15)

    # 3. Sentiment vs WTP by Competitor
    ax3 = axes[1, 0]
    comp_stats = df.groupby("competitor_mentioned").agg(
        avg_sentiment=("sentiment_score", "mean"),
        avg_wtp=("wtp_score", "mean"),
        count=("wtp_score", "count"),
    ).reset_index()
    # Only show competitors with enough data
    comp_stats = comp_stats[comp_stats["count"] >= 5]
    if not comp_stats.empty:
        x = range(len(comp_stats))
        width = 0.35
        ax3.bar(
            [i - width / 2 for i in x],
            comp_stats["avg_sentiment"],
            width,
            label="Avg Sentiment",
            color="#3498db",
        )
        ax3.bar(
            [i + width / 2 for i in x],
            comp_stats["avg_wtp"],
            width,
            label="Avg WTP",
            color="#e67e22",
        )
        ax3.set_xticks(list(x))
        ax3.set_xticklabels(comp_stats["competitor_mentioned"], rotation=30, ha="right")
        ax3.set_title("Sentiment vs WTP by Competitor")
        ax3.legend()
        ax3.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
    else:
        ax3.text(0.5, 0.5, "Not enough per-competitor data", ha="center", va="center")
        ax3.set_title("Sentiment vs WTP by Competitor")

    # 4. Key Insight Summary Box
    ax4 = axes[1, 1]
    ax4.axis("off")
    avg_sent = df["sentiment_score"].mean()
    avg_wtp = df["wtp_score"].mean()
    total_n = len(df)
    wtp_willing = (df["wtp_label"] == "Willing to Pay").sum()
    wtp_not = (df["wtp_label"] == "Not Willing to Pay").sum()

    summary = (
        f"KEY FINDINGS FOR iMeUsWe\n"
        f"{'='*40}\n\n"
        f"Total data points analyzed: {total_n}\n\n"
        f"Avg Sentiment Score: {avg_sent:+.4f}\n"
        f"  → {'Positive' if avg_sent > 0 else 'Negative'} overall feeling\n"
        f"     about paid AI astrology chatbots\n\n"
        f"Avg WTP Score: {avg_wtp:+.4f}\n"
        f"  → {'Users show willingness to pay' if avg_wtp > 0 else 'Users resist paying'}\n\n"
        f"Willing to Pay: {wtp_willing} ({wtp_willing/total_n*100:.1f}%)\n"
        f"Not Willing:    {wtp_not} ({wtp_not/total_n*100:.1f}%)\n\n"
        f"{'='*40}\n"
        f"RECOMMENDATION:\n"
        f"{'Consider a freemium model with limited free chats' if avg_wtp < 0 else 'Market shows readiness for paid tier'}\n"
        f"{'and premium unlock, rather than full paywall.' if avg_wtp < 0 else 'A subscription model could work.'}"
    )
    ax4.text(
        0.05, 0.95, summary,
        transform=ax4.transAxes, fontsize=10,
        verticalalignment="top", fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="#f0f0f0", alpha=0.8),
    )

    plt.tight_layout()
    plt.savefig(REPORT_OUTPUT_PATH, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Report saved to {REPORT_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
