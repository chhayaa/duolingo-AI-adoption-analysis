"""
Step 1: Scrape Google Play Store reviews for competitor AI astrology apps.
No API keys needed — uses google-play-scraper library.

Install: pip install google-play-scraper
"""

from google_play_scraper import Sort, reviews, app
import pandas as pd
import os
import time
from config import RAW_DATA_PATH


# Competitor apps with their Google Play Store package IDs
COMPETITOR_APPS = {
    "Co-Star": "com.costarastrology",
    "The Pattern": "com.thepattern.app",
    "Nebula": "genesis.nebula",
    "Yodha": "com.astroid.yodha",
    "Yodha Daily": "com.yodhaapp.dailyhoroscope",
    "easyStars AI": "co.stellarapp.stellar",
}


def scrape_app_reviews(app_name, package_id, count=500):
    """Scrape reviews for a single app from Google Play Store."""
    all_reviews = []
    try:
        # Get app info
        app_info = app(package_id, lang="en", country="us")
        print(f"  App: {app_info.get('title', app_name)}")
        print(f"  Rating: {app_info.get('score', 'N/A')}")
        print(f"  Installs: {app_info.get('installs', 'N/A')}")

        # Scrape reviews in batches
        result, continuation_token = reviews(
            package_id,
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=count,
        )

        for r in result:
            all_reviews.append({
                "app_name": app_name,
                "package_id": package_id,
                "text": r.get("content", ""),
                "score": r.get("score", 0),
                "thumbs_up": r.get("thumbsUpCount", 0),
                "date": r.get("at", None),
                "review_id": r.get("reviewId", ""),
                "app_rating": app_info.get("score", 0),
                "app_installs": app_info.get("installs", ""),
            })

        print(f"  Scraped {len(all_reviews)} reviews")
    except Exception as e:
        print(f"  Error scraping {app_name}: {e}")

    return all_reviews


def main():
    all_results = []

    for app_name, package_id in COMPETITOR_APPS.items():
        print(f"\nScraping: {app_name} ({package_id})")
        app_reviews = scrape_app_reviews(app_name, package_id, count=500)
        all_results.extend(app_reviews)
        time.sleep(2)  # Be polite

    df = pd.DataFrame(all_results)

    if df.empty:
        print("\nNo reviews scraped. Check your internet connection.")
        return

    # Remove empty reviews
    df = df[df["text"].str.strip().str.len() > 10].copy()

    # Deduplicate
    df = df.drop_duplicates(subset=["text"], keep="first")

    os.makedirs("data", exist_ok=True)
    df.to_csv(RAW_DATA_PATH, index=False)
    print(f"\nDone! Scraped {len(df)} unique reviews. Saved to {RAW_DATA_PATH}")


if __name__ == "__main__":
    main()
