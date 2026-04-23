"""
Unit tests for the scraper module (01_scrape_reviews.py).

All external HTTP calls and the google-play-scraper library are mocked.
No real network requests are made.

Validates: Requirements 2.3, 2.4, 3.3, 3.4, 4.4, 4.5
"""

import importlib
import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from positioning_analysis.config import APPLE_STORE_COUNTRIES

# Module name starts with a digit — use importlib and patch.object
_scraper = importlib.import_module("positioning_analysis.01_scrape_reviews")

_anonymize_name = _scraper._anonymize_name
_build_review_dict = _scraper._build_review_dict
scrape_apple_app_store = _scraper.scrape_apple_app_store
scrape_google_play = _scraper.scrape_google_play
scrape_web_source = _scraper.scrape_web_source

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

REVIEW_SCHEMA_KEYS = {
    "review_text",
    "star_rating",
    "review_date",
    "reviewer_name",
    "app_name",
    "category",
    "review_source",
    "source_url",
    "market_region",
}


def _make_app_entry(**overrides):
    """Return a minimal app-entry dict, with optional overrides."""
    base = {
        "name": "TestApp",
        "category": "astrology",
        "google_play_id": "com.test.app",
        "apple_app_id": "123456789",
        "web_sources": [],
        "market_region": "india",
    }
    base.update(overrides)
    return base


# ===================================================================
# _anonymize_name
# ===================================================================


class TestAnonymizeName:
    """Validates: Requirements 2.3, 3.3"""

    def test_produces_expected_format(self):
        result = _anonymize_name("John")
        assert re.fullmatch(r"[A-Z]_[0-9a-f]{8}", result), f"Unexpected format: {result}"

    def test_first_char_is_uppercase_initial(self):
        assert _anonymize_name("alice")[0] == "A"
        assert _anonymize_name("Bob")[0] == "B"

    def test_deterministic(self):
        assert _anonymize_name("Jane") == _anonymize_name("Jane")

    def test_different_names_produce_different_hashes(self):
        assert _anonymize_name("Alice") != _anonymize_name("Bob")

    def test_empty_string_returns_sentinel(self):
        assert _anonymize_name("") == "X_00000000"


# ===================================================================
# scrape_google_play
# ===================================================================


class TestScrapeGooglePlay:
    """Validates: Requirements 2.3, 2.4"""

    @patch.object(_scraper, "time")
    @patch.object(_scraper, "reviews")
    def test_returns_correct_schema(self, mock_reviews, mock_time):
        mock_reviews.return_value = (
            [
                {
                    "content": "Great app!",
                    "score": 5,
                    "at": datetime(2024, 1, 15),
                    "userName": "Alice",
                }
            ],
            None,
        )

        result = scrape_google_play(_make_app_entry())

        assert len(result) == 1
        assert set(result[0].keys()) == REVIEW_SCHEMA_KEYS
        assert result[0]["review_text"] == "Great app!"
        assert result[0]["star_rating"] == 5
        assert result[0]["review_source"] == "google_play"
        assert result[0]["app_name"] == "TestApp"

    @patch.object(_scraper, "time")
    @patch.object(_scraper, "reviews")
    def test_reviewer_name_is_anonymized(self, mock_reviews, mock_time):
        mock_reviews.return_value = (
            [{"content": "Nice", "score": 4, "at": None, "userName": "Charlie"}],
            None,
        )
        result = scrape_google_play(_make_app_entry())
        assert re.fullmatch(r"[A-Z]_[0-9a-f]{8}", result[0]["reviewer_name"])

    @patch.object(_scraper, "time")
    @patch.object(_scraper, "reviews")
    def test_paginates_with_continuation_token(self, mock_reviews, mock_time):
        mock_reviews.side_effect = [
            ([{"content": "r1", "score": 3, "at": None, "userName": "A"}], "tok1"),
            ([{"content": "r2", "score": 4, "at": None, "userName": "B"}], None),
        ]
        result = scrape_google_play(_make_app_entry())
        assert len(result) == 2
        assert mock_reviews.call_count == 2

    @patch.object(_scraper, "reviews")
    def test_returns_empty_list_on_exception(self, mock_reviews):
        mock_reviews.side_effect = Exception("network error")
        assert scrape_google_play(_make_app_entry()) == []

    def test_skips_when_no_google_play_id(self):
        assert scrape_google_play(_make_app_entry(google_play_id="")) == []


# ===================================================================
# scrape_apple_app_store
# ===================================================================


class TestScrapeAppleAppStore:
    """Validates: Requirements 3.3, 3.4"""

    @staticmethod
    def _make_itunes_response(entries, status_code=200):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"feed": {"entry": entries}}
        return mock_resp

    @staticmethod
    def _make_review_entry(text="Good app", rating="5", author="Dave", updated="2024-01-01"):
        return {
            "content": {"label": text},
            "im:rating": {"label": rating},
            "author": {"name": {"label": author}},
            "updated": {"label": updated},
        }

    @patch.object(_scraper, "time")
    @patch.object(_scraper.requests, "get")
    def test_returns_correct_schema(self, mock_get, mock_time):
        entry = self._make_review_entry()
        mock_get.side_effect = [
            self._make_itunes_response([entry]),
            self._make_itunes_response([]),
        ] * len(APPLE_STORE_COUNTRIES)

        result = scrape_apple_app_store(_make_app_entry())

        assert len(result) >= 1
        for r in result:
            assert set(r.keys()) == REVIEW_SCHEMA_KEYS
            assert r["review_source"] == "apple_app_store"

    @patch.object(_scraper, "time")
    @patch.object(_scraper.requests, "get")
    def test_deduplicates_across_countries(self, mock_get, mock_time):
        entry = self._make_review_entry(text="Duplicate review", author="Eve")
        mock_get.side_effect = [
            self._make_itunes_response([entry]),
            self._make_itunes_response([]),
        ] * len(APPLE_STORE_COUNTRIES)

        result = scrape_apple_app_store(_make_app_entry())
        assert len(result) == 1

    @patch.object(_scraper, "time")
    @patch.object(_scraper.requests, "get")
    def test_unique_reviews_from_different_countries_kept(self, mock_get, mock_time):
        responses = []
        for i, country in enumerate(APPLE_STORE_COUNTRIES):
            unique_entry = self._make_review_entry(
                text=f"Review from {country}", author=f"User{i}"
            )
            responses.append(self._make_itunes_response([unique_entry]))
            responses.append(self._make_itunes_response([]))
        mock_get.side_effect = responses

        result = scrape_apple_app_store(_make_app_entry())
        assert len(result) == len(APPLE_STORE_COUNTRIES)

    @patch.object(_scraper, "time")
    @patch.object(_scraper.requests, "get")
    def test_reviewer_name_is_anonymized(self, mock_get, mock_time):
        entry = self._make_review_entry(author="Frank")
        mock_get.side_effect = [
            self._make_itunes_response([entry]),
            self._make_itunes_response([]),
        ] * len(APPLE_STORE_COUNTRIES)

        result = scrape_apple_app_store(_make_app_entry())
        for r in result:
            assert re.fullmatch(r"[A-Z]_[0-9a-f]{8}", r["reviewer_name"])

    @patch.object(_scraper, "time")
    @patch.object(_scraper.requests, "get")
    def test_continues_on_network_error_per_country(self, mock_get, mock_time):
        good_entry = self._make_review_entry(text="Good review", author="Grace")

        side_effects = []
        for i in range(len(APPLE_STORE_COUNTRIES)):
            if i == 0:
                side_effects.append(MagicMock(side_effect=Exception("timeout")))
            else:
                side_effects.append(self._make_itunes_response([good_entry]))
                side_effects.append(self._make_itunes_response([]))

        mock_get.side_effect = side_effects
        result = scrape_apple_app_store(_make_app_entry())
        assert len(result) >= 1

    def test_skips_when_no_apple_app_id(self):
        assert scrape_apple_app_store(_make_app_entry(apple_app_id="")) == []


# ===================================================================
# scrape_web_source — dispatch and error handling
# ===================================================================


class TestScrapeWebSource:
    """Validates: Requirements 4.4, 4.5

    scrape_web_source dispatches via _SOURCE_PARSERS dict, so we patch
    the dict entries directly rather than the module-level functions.
    """

    def _patch_parser(self, source_type, **kwargs):
        """Return a context-manager that patches _SOURCE_PARSERS[source_type]."""
        mock_fn = MagicMock(**kwargs)
        return patch.dict(_scraper._SOURCE_PARSERS, {source_type: mock_fn}), mock_fn

    def test_dispatches_to_trustpilot(self):
        app = _make_app_entry()
        source = {"url": "https://www.trustpilot.com/review/test.com", "source_type": "trustpilot"}
        ctx, mock_fn = self._patch_parser("trustpilot", return_value=[{"review_text": "tp"}])
        with ctx:
            result = scrape_web_source(app, source)
            mock_fn.assert_called_once_with(app, source)
            assert result == [{"review_text": "tp"}]

    def test_dispatches_to_g2(self):
        app = _make_app_entry()
        source = {"url": "https://www.g2.com/products/test/reviews", "source_type": "g2"}
        ctx, mock_fn = self._patch_parser("g2", return_value=[{"review_text": "g2"}])
        with ctx:
            result = scrape_web_source(app, source)
            mock_fn.assert_called_once_with(app, source)
            assert result == [{"review_text": "g2"}]

    def test_dispatches_to_producthunt(self):
        app = _make_app_entry()
        source = {"url": "https://www.producthunt.com/products/test", "source_type": "producthunt"}
        ctx, mock_fn = self._patch_parser("producthunt", return_value=[])
        with ctx:
            scrape_web_source(app, source)
            mock_fn.assert_called_once_with(app, source)

    def test_dispatches_to_blog(self):
        app = _make_app_entry()
        source = {"url": "https://blog.example.com/review", "source_type": "blog"}
        ctx, mock_fn = self._patch_parser("blog", return_value=[])
        with ctx:
            scrape_web_source(app, source)
            mock_fn.assert_called_once_with(app, source)

    def test_dispatches_to_twitter(self):
        app = _make_app_entry()
        source = {"url": "https://twitter.com/search?q=test", "source_type": "twitter"}
        ctx, mock_fn = self._patch_parser("twitter", return_value=[])
        with ctx:
            scrape_web_source(app, source)
            mock_fn.assert_called_once_with(app, source)

    def test_dispatches_to_google_reddit(self):
        app = _make_app_entry()
        source = {"url": "https://www.google.com/search?q=site:reddit.com+test", "source_type": "google_reddit"}
        ctx, mock_fn = self._patch_parser("google_reddit", return_value=[])
        with ctx:
            scrape_web_source(app, source)
            mock_fn.assert_called_once_with(app, source)

    def test_returns_empty_list_for_unknown_source_type(self):
        result = scrape_web_source(
            _make_app_entry(),
            {"url": "https://example.com", "source_type": "unknown_platform"},
        )
        assert result == []

    def test_returns_empty_list_on_parser_exception(self):
        app = _make_app_entry()
        source = {"url": "https://www.trustpilot.com/review/test.com", "source_type": "trustpilot"}
        ctx, _ = self._patch_parser("trustpilot", side_effect=RuntimeError("boom"))
        with ctx:
            result = scrape_web_source(app, source)
            assert result == []


# ===================================================================
# _build_review_dict — schema compliance
# ===================================================================


class TestBuildReviewDict:
    """Validates: Requirements 2.3, 3.3, 4.4"""

    def test_schema_keys(self):
        d = _build_review_dict(
            review_text="Hello",
            app_name="TestApp",
            category="astrology",
            source_type="trustpilot",
            market_region="india",
        )
        assert set(d.keys()) == REVIEW_SCHEMA_KEYS

    def test_reviewer_name_anonymized(self):
        d = _build_review_dict(
            review_text="Hello",
            app_name="TestApp",
            category="astrology",
            source_type="g2",
            market_region="global",
            reviewer_name="Zara",
        )
        assert re.fullmatch(r"[A-Z]_[0-9a-f]{8}", d["reviewer_name"])

    def test_optional_fields_default_to_none(self):
        d = _build_review_dict(
            review_text="Hello",
            app_name="TestApp",
            category="ancestry",
            source_type="blog",
            market_region="india",
        )
        assert d["star_rating"] is None
        assert d["review_date"] is None
        assert d["source_url"] is None


# ===================================================================
# Error handling — network errors return empty lists
# ===================================================================


class TestErrorHandling:
    """Validates: Requirements 2.4, 3.4, 4.5"""

    @patch.object(_scraper, "reviews")
    def test_google_play_network_error(self, mock_reviews):
        mock_reviews.side_effect = ConnectionError("DNS failure")
        assert scrape_google_play(_make_app_entry()) == []

    @patch.object(_scraper.requests, "get")
    def test_apple_store_all_countries_fail(self, mock_get):
        mock_get.side_effect = ConnectionError("no internet")
        result = scrape_apple_app_store(_make_app_entry())
        assert isinstance(result, list)

    def test_web_source_unknown_type_returns_empty(self):
        result = scrape_web_source(
            _make_app_entry(),
            {"url": "https://x.com", "source_type": "nonexistent"},
        )
        assert result == []
