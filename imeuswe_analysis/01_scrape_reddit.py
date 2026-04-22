"""
Step 1: Scrape Reddit for competitor AI astrology chatbot discussions.
Collects posts + comments about paid astrology AI features from relevant subreddits.
"""

import praw
import pandas as pd
import os
import time
from config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT,
    SEARCH_QUERIES, SUBREDDITS, COMPETITORS, RAW_DATA_PATH,
)


def init_reddit():
    """Initialize Reddit API client."""
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )


def scrape_posts(reddit, query, subreddit_name, limit=100):
    """Scrape posts matching a query from a subreddit."""
    results = []
    try:
        subreddit = reddit.subreddit(subreddit_name)
        for post in subreddit.search(query, limit=limit, sort="relevance"):
            # Collect the post
            results.append({
                "type": "post",
                "subreddit": subreddit_name,
                "query": query,
                "title": post.title,
                "text": post.selftext,
                "score": post.score,
                "num_comments": post.num_comments,
                "created_utc": post.created_utc,
                "author": str(post.author) if post.author else "[deleted]",
                "url": post.url,
                "post_id": post.id,
            })

            # Collect top-level comments
            post.comments.replace_more(limit=0)
            for comment in post.comments.list()[:20]:
                if comment.body and comment.body != "[deleted]":
                    results.append({
                        "type": "comment",
                        "subreddit": subreddit_name,
                        "query": query,
                        "title": post.title,
                        "text": comment.body,
                        "score": comment.score,
                        "num_comments": 0,
                        "created_utc": comment.created_utc,
                        "author": str(comment.author) if comment.author else "[deleted]",
                        "url": post.url,
                        "post_id": post.id,
                    })
    except Exception as e:
        print(f"  Error scraping r/{subreddit_name} for '{query}': {e}")
    return results


def main():
    reddit = init_reddit()
    all_results = []

    total_queries = len(SEARCH_QUERIES) * len(SUBREDDITS)
    current = 0

    for query in SEARCH_QUERIES:
        for sub in SUBREDDITS:
            current += 1
            print(f"[{current}/{total_queries}] Scraping r/{sub} for: '{query}'")
            posts = scrape_posts(reddit, query, sub, limit=100)
            all_results.extend(posts)
            print(f"  Found {len(posts)} items")
            time.sleep(1)  # Rate limiting

    df = pd.DataFrame(all_results)

    # Deduplicate by text content
    df = df.drop_duplicates(subset=["text"], keep="first")
    df = df[df["text"].str.strip().str.len() > 10]  # Remove empty/tiny posts

    os.makedirs("data", exist_ok=True)
    df.to_csv(RAW_DATA_PATH, index=False)
    print(f"\nDone! Scraped {len(df)} unique items. Saved to {RAW_DATA_PATH}")


if __name__ == "__main__":
    main()
