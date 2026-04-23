"""
Review Scraper for Positioning Analysis Pipeline.

Collects user reviews from Google Play Store, Apple App Store, and public web
sources for all apps defined in the App Registry. Each source has its own
scraping function. Reviews are anonymized, normalized to a common schema,
and combined into a single DataFrame saved to data/raw_reviews.csv.

This module will be extended with Apple App Store, web source, and orchestrator
functions in subsequent tasks.
"""

import hashlib
import logging
import time

import re

import requests
from bs4 import BeautifulSoup
from google_play_scraper import Sort, reviews

from positioning_analysis.config import APPLE_STORE_COUNTRIES, REQUEST_DELAY

logger = logging.getLogger(__name__)


def _anonymize_name(name: str) -> str:
    """Anonymize a reviewer name as first initial + MD5 hash (first 8 hex chars).

    Args:
        name: The original reviewer name.

    Returns:
        Anonymized string like "J_a1b2c3d4".
    """
    if not name:
        return "X_00000000"
    first_char = name[0].upper()
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    return f"{first_char}_{digest}"


def scrape_google_play(app_entry: dict) -> list[dict]:
    """Scrape all available reviews from Google Play using google-play-scraper.

    Paginates using continuation tokens until exhausted (no count limit).
    Applies a configurable delay between batches.

    Args:
        app_entry: A dict from APP_REGISTRY with keys including
            ``name``, ``google_play_id``, ``category``, and ``market_region``.

    Returns:
        A list of review dicts conforming to the pipeline schema.
        Returns an empty list on failure.
    """
    app_name = app_entry.get("name", "Unknown")
    package_id = app_entry.get("google_play_id", "")
    category = app_entry.get("category", "")
    market_region = app_entry.get("market_region", "")

    if not package_id:
        logger.warning("No google_play_id for %s — skipping Google Play scrape.", app_name)
        return []

    all_reviews: list[dict] = []
    try:
        continuation_token = None
        batch_num = 0

        while True:
            batch_num += 1
            logger.info(
                "Fetching Google Play reviews for %s — batch %d", app_name, batch_num
            )

            result, continuation_token = reviews(
                package_id,
                lang="en",
                country="us",
                sort=Sort.NEWEST,
                count=200,
                continuation_token=continuation_token,
            )

            if not result:
                break

            for r in result:
                review_date = r.get("at")
                if review_date is not None:
                    review_date = review_date.isoformat() if hasattr(review_date, "isoformat") else str(review_date)

                all_reviews.append(
                    {
                        "review_text": r.get("content", ""),
                        "star_rating": r.get("score"),
                        "review_date": review_date,
                        "reviewer_name": _anonymize_name(r.get("userName", "")),
                        "app_name": app_name,
                        "category": category,
                        "review_source": "google_play",
                        "source_url": None,
                        "market_region": market_region,
                    }
                )

            if continuation_token is None:
                break

            time.sleep(REQUEST_DELAY)

        logger.info(
            "Scraped %d Google Play reviews for %s.", len(all_reviews), app_name
        )

    except Exception:
        logger.exception("Error scraping Google Play reviews for %s", app_name)
        return []

    return all_reviews


def scrape_apple_app_store(app_entry: dict) -> list[dict]:
    """Scrape reviews from Apple App Store via the iTunes RSS JSON feed.

    Uses the public endpoint:
        https://itunes.apple.com/{country}/rss/customerreviews/id={id}/sortBy=mostRecent/page={page}/json

    Paginates through all available pages (up to 50 reviews per page) for each
    country in ``APPLE_STORE_COUNTRIES``. Results from all countries are merged
    and deduplicated by ``(review_text, reviewer_name)``.

    Args:
        app_entry: A dict from APP_REGISTRY with keys including
            ``name``, ``apple_app_id``, ``category``, and ``market_region``.

    Returns:
        A list of review dicts conforming to the pipeline schema.
        Returns an empty list on failure.
    """
    app_name = app_entry.get("name", "Unknown")
    apple_id = app_entry.get("apple_app_id", "")
    category = app_entry.get("category", "")
    market_region = app_entry.get("market_region", "")

    if not apple_id:
        logger.warning("No apple_app_id for %s — skipping Apple App Store scrape.", app_name)
        return []

    all_reviews: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for country in APPLE_STORE_COUNTRIES:
        page = 1
        try:
            while True:
                url = (
                    f"https://itunes.apple.com/{country}/rss/customerreviews"
                    f"/id={apple_id}/sortBy=mostRecent/page={page}/json"
                )
                logger.info(
                    "Fetching Apple App Store reviews for %s — country=%s page=%d",
                    app_name, country, page,
                )

                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                feed = data.get("feed", {})
                entries = feed.get("entry", [])

                # The first entry is often the app metadata, not a review.
                # Reviews have an "im:rating" key; filter to only those.
                review_entries = [
                    e for e in entries if "im:rating" in e
                ]

                if not review_entries:
                    break

                for entry in review_entries:
                    review_text = entry.get("content", {}).get("label", "")
                    reviewer_name_raw = entry.get("author", {}).get("name", {}).get("label", "")
                    anonymized = _anonymize_name(reviewer_name_raw)

                    dedup_key = (review_text, anonymized)
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    star_rating = None
                    try:
                        star_rating = float(entry.get("im:rating", {}).get("label", ""))
                    except (ValueError, TypeError, AttributeError):
                        pass

                    review_date = entry.get("updated", {}).get("label", None)

                    all_reviews.append(
                        {
                            "review_text": review_text,
                            "star_rating": star_rating,
                            "review_date": review_date,
                            "reviewer_name": anonymized,
                            "app_name": app_name,
                            "category": category,
                            "review_source": "apple_app_store",
                            "source_url": None,
                            "market_region": market_region,
                        }
                    )

                page += 1
                time.sleep(REQUEST_DELAY)

        except Exception:
            logger.exception(
                "Error scraping Apple App Store reviews for %s (country=%s, page=%d)",
                app_name, country, page,
            )
            # Continue to next country store on error
            continue

    logger.info("Scraped %d Apple App Store reviews for %s.", len(all_reviews), app_name)
    return all_reviews


# ---------------------------------------------------------------------------
# Common HTTP headers for web scraping
# ---------------------------------------------------------------------------
_COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _build_review_dict(
    review_text: str,
    app_name: str,
    category: str,
    source_type: str,
    market_region: str,
    source_url: str | None = None,
    star_rating: float | None = None,
    review_date: str | None = None,
    reviewer_name: str = "",
) -> dict:
    """Build a review dict conforming to the pipeline schema."""
    return {
        "review_text": review_text,
        "star_rating": star_rating,
        "review_date": review_date,
        "reviewer_name": _anonymize_name(reviewer_name),
        "app_name": app_name,
        "category": category,
        "review_source": source_type,
        "source_url": source_url,
        "market_region": market_region,
    }


# ---------------------------------------------------------------------------
# Source-specific parsers
# ---------------------------------------------------------------------------


def _scrape_trustpilot(app_entry: dict, source: dict) -> list[dict]:
    """Parse review cards from Trustpilot public review pages.

    Trustpilot pages contain review cards with star ratings, dates, and text.
    Paginates through available pages.
    """
    app_name = app_entry.get("name", "Unknown")
    category = app_entry.get("category", "")
    market_region = app_entry.get("market_region", "")
    base_url = source.get("url", "")
    results: list[dict] = []

    if not base_url:
        return results

    page = 1
    try:
        while True:
            url = f"{base_url}?page={page}"
            logger.info("Scraping Trustpilot for %s — page %d", app_name, page)

            resp = requests.get(url, headers=_COMMON_HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning(
                    "Trustpilot returned %d for %s page %d — stopping.",
                    resp.status_code, app_name, page,
                )
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            # Trustpilot review cards are in article tags or divs with
            # data-service-review-rating attribute
            review_cards = soup.find_all(
                "article", attrs={"data-service-review-card-paper": True}
            )
            if not review_cards:
                # Fallback: look for divs with review content
                review_cards = soup.find_all(
                    "div", attrs={"data-service-review-rating": True}
                )

            if not review_cards:
                break

            for card in review_cards:
                # Extract rating from star image alt or data attribute
                star_rating = None
                rating_el = card.find(attrs={"data-service-review-rating": True})
                if rating_el:
                    try:
                        star_rating = float(rating_el["data-service-review-rating"])
                    except (ValueError, KeyError):
                        pass

                # Extract review text
                text_el = card.find(
                    "p", attrs={"data-service-review-text-typography": True}
                )
                if not text_el:
                    text_el = card.find("p", class_=re.compile(r"review.*text", re.I))
                review_text = text_el.get_text(strip=True) if text_el else ""

                if not review_text:
                    continue

                # Extract date
                review_date = None
                time_el = card.find("time")
                if time_el and time_el.get("datetime"):
                    review_date = time_el["datetime"]

                # Extract reviewer name
                reviewer_name = ""
                name_el = card.find(
                    attrs={"data-consumer-name-typography": True}
                )
                if not name_el:
                    name_el = card.find("span", class_=re.compile(r"consumer.*name", re.I))
                if name_el:
                    reviewer_name = name_el.get_text(strip=True)

                results.append(
                    _build_review_dict(
                        review_text=review_text,
                        app_name=app_name,
                        category=category,
                        source_type="trustpilot",
                        market_region=market_region,
                        source_url=url,
                        star_rating=star_rating,
                        review_date=review_date,
                        reviewer_name=reviewer_name,
                    )
                )

            page += 1
            time.sleep(REQUEST_DELAY)

    except Exception:
        logger.exception("Error scraping Trustpilot for %s", app_name)

    logger.info("Scraped %d Trustpilot reviews for %s.", len(results), app_name)
    return results


def _scrape_g2(app_entry: dict, source: dict) -> list[dict]:
    """Parse review sections from G2 public product pages.

    G2 review pages contain structured review cards with star ratings,
    pros/cons sections, and dates.
    """
    app_name = app_entry.get("name", "Unknown")
    category = app_entry.get("category", "")
    market_region = app_entry.get("market_region", "")
    base_url = source.get("url", "")
    results: list[dict] = []

    if not base_url:
        return results

    page = 1
    try:
        while True:
            url = f"{base_url}?page={page}" if page > 1 else base_url
            logger.info("Scraping G2 for %s — page %d", app_name, page)

            resp = requests.get(url, headers=_COMMON_HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning(
                    "G2 returned %d for %s page %d — stopping.",
                    resp.status_code, app_name, page,
                )
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            # G2 reviews are in divs with itemprop="review" or similar
            review_divs = soup.find_all("div", itemprop="review")
            if not review_divs:
                review_divs = soup.find_all(
                    "div", class_=re.compile(r"review-content|paper--white", re.I)
                )

            if not review_divs:
                break

            for div in review_divs:
                # Extract rating
                star_rating = None
                rating_el = div.find("meta", itemprop="ratingValue")
                if rating_el:
                    try:
                        star_rating = float(rating_el.get("content", ""))
                    except (ValueError, TypeError):
                        pass
                if star_rating is None:
                    stars_el = div.find("div", class_=re.compile(r"star", re.I))
                    if stars_el:
                        stars_text = stars_el.get("title", "") or stars_el.get_text(strip=True)
                        match = re.search(r"(\d+(?:\.\d+)?)", stars_text)
                        if match:
                            try:
                                star_rating = float(match.group(1))
                            except ValueError:
                                pass

                # Extract review text — combine pros, cons, and overall
                text_parts = []
                for section_class in [
                    "review-likes", "review-dislikes", "review-body",
                    "review-comment", "review-text",
                ]:
                    section = div.find(
                        "div", class_=re.compile(section_class, re.I)
                    )
                    if section:
                        text_parts.append(section.get_text(strip=True))

                # Fallback: itemprop reviewBody
                if not text_parts:
                    body_el = div.find(attrs={"itemprop": "reviewBody"})
                    if body_el:
                        text_parts.append(body_el.get_text(strip=True))

                review_text = " ".join(text_parts).strip()
                if not review_text:
                    continue

                # Extract date
                review_date = None
                date_el = div.find("time")
                if date_el and date_el.get("datetime"):
                    review_date = date_el["datetime"]
                elif date_el:
                    review_date = date_el.get_text(strip=True)

                # Extract reviewer name
                reviewer_name = ""
                name_el = div.find(attrs={"itemprop": "author"})
                if name_el:
                    reviewer_name = name_el.get_text(strip=True)

                results.append(
                    _build_review_dict(
                        review_text=review_text,
                        app_name=app_name,
                        category=category,
                        source_type="g2",
                        market_region=market_region,
                        source_url=url,
                        star_rating=star_rating,
                        review_date=review_date,
                        reviewer_name=reviewer_name,
                    )
                )

            page += 1
            time.sleep(REQUEST_DELAY)

    except Exception:
        logger.exception("Error scraping G2 for %s", app_name)

    logger.info("Scraped %d G2 reviews for %s.", len(results), app_name)
    return results


def _scrape_producthunt(app_entry: dict, source: dict) -> list[dict]:
    """Parse discussion/comment sections from Product Hunt product pages."""
    app_name = app_entry.get("name", "Unknown")
    category = app_entry.get("category", "")
    market_region = app_entry.get("market_region", "")
    url = source.get("url", "")
    results: list[dict] = []

    if not url:
        return results

    try:
        logger.info("Scraping Product Hunt for %s", app_name)
        resp = requests.get(url, headers=_COMMON_HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(
                "Product Hunt returned %d for %s — skipping.", resp.status_code, app_name
            )
            return results

        soup = BeautifulSoup(resp.text, "html.parser")

        # Product Hunt comments/discussions are in various div structures
        comment_divs = soup.find_all(
            "div", class_=re.compile(r"comment|discussion|review", re.I)
        )
        if not comment_divs:
            # Fallback: look for paragraphs within main content area
            main_content = soup.find("main") or soup.find("div", id="__next")
            if main_content:
                comment_divs = main_content.find_all("div", recursive=False)

        for div in comment_divs:
            text = div.get_text(strip=True)
            # Filter out very short or navigation-like text
            if not text or len(text) < 20:
                continue

            # Extract date if available
            review_date = None
            time_el = div.find("time")
            if time_el and time_el.get("datetime"):
                review_date = time_el["datetime"]

            # Extract commenter name
            reviewer_name = ""
            name_el = div.find("a", class_=re.compile(r"user|author|name", re.I))
            if name_el:
                reviewer_name = name_el.get_text(strip=True)

            results.append(
                _build_review_dict(
                    review_text=text,
                    app_name=app_name,
                    category=category,
                    source_type="producthunt",
                    market_region=market_region,
                    source_url=url,
                    review_date=review_date,
                    reviewer_name=reviewer_name,
                )
            )

        time.sleep(REQUEST_DELAY)

    except Exception:
        logger.exception("Error scraping Product Hunt for %s", app_name)

    logger.info("Scraped %d Product Hunt posts for %s.", len(results), app_name)
    return results


def _scrape_quora(app_entry: dict, source: dict) -> list[dict]:
    """Parse answer content from public Quora question pages."""
    app_name = app_entry.get("name", "Unknown")
    category = app_entry.get("category", "")
    market_region = app_entry.get("market_region", "")
    url = source.get("url", "")
    results: list[dict] = []

    if not url:
        return results

    try:
        logger.info("Scraping Quora for %s", app_name)
        resp = requests.get(url, headers=_COMMON_HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(
                "Quora returned %d for %s — skipping.", resp.status_code, app_name
            )
            return results

        soup = BeautifulSoup(resp.text, "html.parser")

        # Quora answers are in spans with class containing "q-text"
        # or in divs with class "Answer"
        answer_divs = soup.find_all(
            "div", class_=re.compile(r"Answer|answer_content", re.I)
        )
        if not answer_divs:
            answer_divs = soup.find_all(
                "span", class_=re.compile(r"q-text|CssComponent", re.I)
            )

        for div in answer_divs:
            text = div.get_text(strip=True)
            if not text or len(text) < 20:
                continue

            # Extract author name
            reviewer_name = ""
            author_el = div.find_previous(
                "a", class_=re.compile(r"user|author", re.I)
            )
            if author_el:
                reviewer_name = author_el.get_text(strip=True)

            # Extract date
            review_date = None
            date_el = div.find("span", class_=re.compile(r"date|time", re.I))
            if date_el:
                review_date = date_el.get_text(strip=True)

            results.append(
                _build_review_dict(
                    review_text=text,
                    app_name=app_name,
                    category=category,
                    source_type="quora",
                    market_region=market_region,
                    source_url=url,
                    review_date=review_date,
                    reviewer_name=reviewer_name,
                )
            )

        time.sleep(REQUEST_DELAY)

    except Exception:
        logger.exception("Error scraping Quora for %s", app_name)

    logger.info("Scraped %d Quora answers for %s.", len(results), app_name)
    return results


def _scrape_blog(app_entry: dict, source: dict) -> list[dict]:
    """Parse article body and comment sections from blog pages."""
    app_name = app_entry.get("name", "Unknown")
    category = app_entry.get("category", "")
    market_region = app_entry.get("market_region", "")
    url = source.get("url", "")
    results: list[dict] = []

    if not url:
        return results

    try:
        logger.info("Scraping blog for %s: %s", app_name, url)
        resp = requests.get(url, headers=_COMMON_HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(
                "Blog returned %d for %s — skipping.", resp.status_code, app_name
            )
            return results

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract article body
        article = soup.find("article") or soup.find(
            "div", class_=re.compile(r"post-content|article-body|entry-content", re.I)
        )
        if article:
            # Get paragraphs from the article
            paragraphs = article.find_all("p")
            article_text = " ".join(
                p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
            )
            if article_text and len(article_text) >= 20:
                # Extract article date
                review_date = None
                time_el = soup.find("time")
                if time_el and time_el.get("datetime"):
                    review_date = time_el["datetime"]
                meta_date = soup.find("meta", property="article:published_time")
                if meta_date and not review_date:
                    review_date = meta_date.get("content")

                # Extract author
                reviewer_name = ""
                author_el = soup.find(attrs={"rel": "author"}) or soup.find(
                    "meta", attrs={"name": "author"}
                )
                if author_el:
                    reviewer_name = (
                        author_el.get("content", "") or author_el.get_text(strip=True)
                    )

                results.append(
                    _build_review_dict(
                        review_text=article_text,
                        app_name=app_name,
                        category=category,
                        source_type="blog",
                        market_region=market_region,
                        source_url=url,
                        review_date=review_date,
                        reviewer_name=reviewer_name,
                    )
                )

        # Extract comments section
        comments_section = soup.find(
            "div", class_=re.compile(r"comments|disqus|discuss", re.I)
        ) or soup.find("section", class_=re.compile(r"comments", re.I))

        if comments_section:
            comment_divs = comments_section.find_all(
                "div", class_=re.compile(r"comment-body|comment-content|comment-text", re.I)
            )
            if not comment_divs:
                comment_divs = comments_section.find_all("li")

            for comment in comment_divs:
                text = comment.get_text(strip=True)
                if not text or len(text) < 20:
                    continue

                comment_date = None
                time_el = comment.find("time")
                if time_el and time_el.get("datetime"):
                    comment_date = time_el["datetime"]

                commenter = ""
                name_el = comment.find(
                    class_=re.compile(r"author|commenter|name", re.I)
                )
                if name_el:
                    commenter = name_el.get_text(strip=True)

                results.append(
                    _build_review_dict(
                        review_text=text,
                        app_name=app_name,
                        category=category,
                        source_type="blog",
                        market_region=market_region,
                        source_url=url,
                        review_date=comment_date,
                        reviewer_name=commenter,
                    )
                )

        time.sleep(REQUEST_DELAY)

    except Exception:
        logger.exception("Error scraping blog for %s", app_name)

    logger.info("Scraped %d blog items for %s.", len(results), app_name)
    return results


def _scrape_twitter(app_entry: dict, source: dict) -> list[dict]:
    """Best-effort scrape of Twitter/X content.

    Twitter has aggressive anti-bot measures. If the primary URL returns
    403 or 429, we skip immediately with no retry. As a fallback, we
    attempt scraping via Nitter (open-source Twitter frontend).
    """
    app_name = app_entry.get("name", "Unknown")
    category = app_entry.get("category", "")
    market_region = app_entry.get("market_region", "")
    url = source.get("url", "")
    results: list[dict] = []

    if not url:
        return results

    def _parse_tweets(soup: BeautifulSoup, page_url: str) -> list[dict]:
        """Extract tweet-like content from a parsed page."""
        parsed: list[dict] = []
        # Try common tweet container selectors
        tweet_divs = soup.find_all(
            "div", class_=re.compile(r"tweet-content|timeline-item|tweet-body", re.I)
        )
        if not tweet_divs:
            tweet_divs = soup.find_all("article")

        for div in tweet_divs:
            text = div.get_text(strip=True)
            if not text or len(text) < 10:
                continue

            tweet_date = None
            time_el = div.find("time")
            if time_el and time_el.get("datetime"):
                tweet_date = time_el["datetime"]
            elif time_el:
                tweet_date = time_el.get("title") or time_el.get_text(strip=True)

            author = ""
            author_el = div.find("a", class_=re.compile(r"username|fullname", re.I))
            if author_el:
                author = author_el.get_text(strip=True)

            parsed.append(
                _build_review_dict(
                    review_text=text,
                    app_name=app_name,
                    category=category,
                    source_type="twitter",
                    market_region=market_region,
                    source_url=page_url,
                    review_date=tweet_date,
                    reviewer_name=author,
                )
            )
        return parsed

    # Attempt primary Twitter URL
    try:
        logger.info("Attempting Twitter scrape for %s: %s", app_name, url)
        resp = requests.get(url, headers=_COMMON_HEADERS, timeout=15)

        if resp.status_code in (403, 429):
            logger.warning(
                "Twitter returned %d for %s — skipping (no retry).",
                resp.status_code, app_name,
            )
        elif resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            results.extend(_parse_tweets(soup, url))
        else:
            logger.warning(
                "Twitter returned %d for %s.", resp.status_code, app_name
            )

    except Exception:
        logger.exception("Error scraping Twitter for %s", app_name)

    # Nitter fallback if primary yielded nothing
    if not results:
        nitter_url = url.replace("twitter.com", "nitter.net").replace("x.com", "nitter.net")
        if nitter_url != url:
            try:
                logger.info("Attempting Nitter fallback for %s: %s", app_name, nitter_url)
                resp = requests.get(nitter_url, headers=_COMMON_HEADERS, timeout=15)

                if resp.status_code in (403, 429):
                    logger.warning(
                        "Nitter returned %d for %s — skipping.",
                        resp.status_code, app_name,
                    )
                elif resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    results.extend(_parse_tweets(soup, nitter_url))
                else:
                    logger.warning(
                        "Nitter returned %d for %s.", resp.status_code, app_name
                    )

            except Exception:
                logger.exception("Error scraping Nitter fallback for %s", app_name)

    logger.info("Scraped %d Twitter/Nitter posts for %s.", len(results), app_name)
    return results


def _scrape_google_reddit(app_entry: dict, source: dict) -> list[dict]:
    """Scrape Google-indexed Reddit content.

    Uses Google search with ``site:reddit.com {app_name} review`` to find
    relevant Reddit discussions, then parses the Google result snippets and
    attempts to scrape the linked Reddit pages for full content.
    """
    app_name = app_entry.get("name", "Unknown")
    category = app_entry.get("category", "")
    market_region = app_entry.get("market_region", "")
    source_url = source.get("url", "")
    results: list[dict] = []

    # Build Google search URL
    if source_url and "google.com/search" in source_url:
        search_url = source_url
    else:
        query = f"site:reddit.com {app_name} review"
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"

    try:
        logger.info("Searching Google for Reddit content about %s", app_name)
        resp = requests.get(search_url, headers=_COMMON_HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(
                "Google search returned %d for %s — skipping.",
                resp.status_code, app_name,
            )
            return results

        soup = BeautifulSoup(resp.text, "html.parser")

        # Parse Google search result snippets
        search_results = soup.find_all("div", class_="g")
        if not search_results:
            # Fallback: broader search for result containers
            search_results = soup.find_all(
                "div", class_=re.compile(r"tF2Cxc|MjjYud", re.I)
            )

        reddit_urls: list[str] = []

        for result in search_results:
            # Extract snippet text
            snippet_el = result.find("span", class_=re.compile(r"aCOpRe|st", re.I))
            if not snippet_el:
                snippet_el = result.find("div", class_=re.compile(r"VwiC3b", re.I))

            snippet_text = snippet_el.get_text(strip=True) if snippet_el else ""

            # Extract link
            link_el = result.find("a", href=True)
            link_url = link_el["href"] if link_el else ""

            if snippet_text and len(snippet_text) >= 20:
                results.append(
                    _build_review_dict(
                        review_text=snippet_text,
                        app_name=app_name,
                        category=category,
                        source_type="google_reddit",
                        market_region=market_region,
                        source_url=link_url or search_url,
                        reviewer_name="reddit_user",
                    )
                )

            # Collect Reddit URLs for deeper scraping
            if link_url and "reddit.com" in link_url:
                reddit_urls.append(link_url)

        time.sleep(REQUEST_DELAY)

        # Attempt to scrape linked Reddit pages for more content
        for reddit_url in reddit_urls[:5]:  # Limit to first 5 links
            try:
                logger.info("Scraping Reddit page: %s", reddit_url)
                reddit_resp = requests.get(
                    reddit_url, headers=_COMMON_HEADERS, timeout=30
                )
                if reddit_resp.status_code != 200:
                    continue

                reddit_soup = BeautifulSoup(reddit_resp.text, "html.parser")

                # Parse Reddit comments — look for comment body divs
                comment_divs = reddit_soup.find_all(
                    "div", class_=re.compile(r"comment|md|usertext-body", re.I)
                )
                if not comment_divs:
                    # Try finding paragraphs in the main content
                    comment_divs = reddit_soup.find_all(
                        "p", class_=re.compile(r"md", re.I)
                    )

                for comment in comment_divs:
                    text = comment.get_text(strip=True)
                    if not text or len(text) < 20:
                        continue

                    results.append(
                        _build_review_dict(
                            review_text=text,
                            app_name=app_name,
                            category=category,
                            source_type="google_reddit",
                            market_region=market_region,
                            source_url=reddit_url,
                            reviewer_name="reddit_user",
                        )
                    )

                time.sleep(REQUEST_DELAY)

            except Exception:
                logger.exception("Error scraping Reddit page: %s", reddit_url)
                continue

    except Exception:
        logger.exception("Error in Google-Reddit search for %s", app_name)

    logger.info("Scraped %d Google-Reddit items for %s.", len(results), app_name)
    return results


# ---------------------------------------------------------------------------
# Web source dispatcher
# ---------------------------------------------------------------------------

# Map source_type strings to their parser functions
_SOURCE_PARSERS = {
    "trustpilot": _scrape_trustpilot,
    "g2": _scrape_g2,
    "producthunt": _scrape_producthunt,
    "quora": _scrape_quora,
    "blog": _scrape_blog,
    "twitter": _scrape_twitter,
    "google_reddit": _scrape_google_reddit,
}


def scrape_web_source(app_entry: dict, source: dict) -> list[dict]:
    """Scrape reviews/posts from a web source using requests + BeautifulSoup.

    Dispatches to source-specific parsers based on ``source["source_type"]``.
    Each parser returns a list of review dicts conforming to the pipeline schema.

    Args:
        app_entry: A dict from APP_REGISTRY with keys including
            ``name``, ``category``, and ``market_region``.
        source: A dict with ``url`` and ``source_type`` keys. The
            ``source_type`` must be one of: trustpilot, g2, producthunt,
            quora, blog, twitter, google_reddit.

    Returns:
        A list of review dicts. Returns an empty list if the source type
        is unrecognized or if scraping fails.
    """
    source_type = source.get("source_type", "")
    app_name = app_entry.get("name", "Unknown")

    parser = _SOURCE_PARSERS.get(source_type)
    if parser is None:
        logger.warning(
            "Unknown source_type '%s' for %s — skipping.", source_type, app_name
        )
        return []

    try:
        return parser(app_entry, source)
    except Exception:
        logger.exception(
            "Unhandled error scraping %s for %s", source_type, app_name
        )
        return []


# ---------------------------------------------------------------------------
# Orchestrator — scrape all apps from all sources
# ---------------------------------------------------------------------------

import os

import pandas as pd

from positioning_analysis.config import DATA_DIR


def scrape_all(registry: list[dict]) -> pd.DataFrame:
    """Scrape reviews for every app in *registry* from all configured sources.

    For each app the function calls:
      1. ``scrape_google_play``
      2. ``scrape_apple_app_store``
      3. ``scrape_web_source`` for every entry in the app's ``web_sources``

    Errors are handled per-app so that a failure for one app does not prevent
    the remaining apps from being scraped.  All collected reviews are combined
    into a single :class:`~pandas.DataFrame` and saved to
    ``{DATA_DIR}/raw_reviews.csv``.

    Args:
        registry: A list of app-entry dicts (typically ``APP_REGISTRY`` from
            ``config.py``).

    Returns:
        A :class:`~pandas.DataFrame` containing all scraped reviews.  Returns
        an empty ``DataFrame`` if no reviews were collected.
    """
    all_reviews: list[dict] = []

    for app_entry in registry:
        app_name = app_entry.get("name", "Unknown")
        logger.info("--- Scraping reviews for %s ---", app_name)

        # Google Play
        try:
            gp_reviews = scrape_google_play(app_entry)
            all_reviews.extend(gp_reviews)
            logger.info("  Google Play: %d reviews", len(gp_reviews))
        except Exception:
            logger.exception("  Failed to scrape Google Play for %s", app_name)

        # Apple App Store
        try:
            apple_reviews = scrape_apple_app_store(app_entry)
            all_reviews.extend(apple_reviews)
            logger.info("  Apple App Store: %d reviews", len(apple_reviews))
        except Exception:
            logger.exception("  Failed to scrape Apple App Store for %s", app_name)

        # Web sources
        for source in app_entry.get("web_sources", []):
            source_type = source.get("source_type", "unknown")
            try:
                web_reviews = scrape_web_source(app_entry, source)
                all_reviews.extend(web_reviews)
                logger.info("  %s: %d reviews", source_type, len(web_reviews))
            except Exception:
                logger.exception(
                    "  Failed to scrape %s for %s", source_type, app_name
                )

    logger.info("Total reviews collected across all apps: %d", len(all_reviews))

    df = pd.DataFrame(all_reviews)

    # Ensure the data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    output_path = os.path.join(DATA_DIR, "raw_reviews.csv")
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Saved raw reviews to %s", output_path)

    return df
