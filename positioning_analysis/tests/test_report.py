"""
Property-based tests for the positioning_analysis report generator module.

Property 10: Feature ranking is correctly ordered
"""

import importlib

from hypothesis import given, settings
from hypothesis import strategies as st

from positioning_analysis.config import ASTROLOGY_FEATURE_KEYWORDS

# Import the module that starts with a digit via importlib
_report = importlib.import_module("positioning_analysis.06_report")
_rank_category_features = _report._rank_category_features


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Pick feature names from the real ASTROLOGY_FEATURE_KEYWORDS keys
_feature_names = st.sampled_from(sorted(ASTROLOGY_FEATURE_KEYWORDS.keys()))

# Generate a single top_praised_features entry with a random avg_score
_feature_entry = st.fixed_dictionaries(
    {"feature": _feature_names, "avg_score": st.floats(min_value=-1.0, max_value=1.0)}
)

# Generate a list of unique feature entries (no duplicate feature names)
_feature_list = st.lists(
    _feature_entry,
    min_size=1,
    max_size=len(ASTROLOGY_FEATURE_KEYWORDS),
).map(
    lambda entries: list({e["feature"]: e for e in entries}.values())
)

# top_n between 1 and total number of possible features
_top_n = st.integers(min_value=1, max_value=len(ASTROLOGY_FEATURE_KEYWORDS))


# ---------------------------------------------------------------------------
# Property 10: Feature ranking is correctly ordered
# Validates: Requirements 9.3
#
# For any dataset of feature sentiment scores, the top-N ranked features
# SHALL be sorted in descending order by average sentiment score, and no
# feature outside the top-N SHALL have a higher average sentiment score
# than any feature inside the top-N.
# ---------------------------------------------------------------------------
@given(features=_feature_list, top_n=_top_n)
@settings(max_examples=100)
def test_feature_ranking_is_correctly_ordered(features, top_n):
    """Feature: positioning-analysis, Property 10: Feature ranking is correctly ordered

    **Validates: Requirements 9.3**
    """
    sentiment_summary = {"top_praised_features": features}

    ranked = _rank_category_features(sentiment_summary, "astrology", top_n)

    # 1. Result length should be min(top_n, available features)
    assert len(ranked) <= top_n

    # 2. Returned list must be sorted in descending order by avg_sentiment
    for i in range(len(ranked) - 1):
        assert ranked[i]["avg_sentiment"] >= ranked[i + 1]["avg_sentiment"], (
            f"Ranking not descending at index {i}: "
            f"{ranked[i]['avg_sentiment']} < {ranked[i + 1]['avg_sentiment']}"
        )

    # 3. No excluded feature should have a higher score than any included feature
    if ranked:
        min_included_score = ranked[-1]["avg_sentiment"]
        included_features = {r["feature"] for r in ranked}
        for entry in features:
            if entry["feature"] not in included_features:
                assert entry["avg_score"] <= min_included_score, (
                    f"Excluded feature '{entry['feature']}' has score "
                    f"{entry['avg_score']} > min included score {min_included_score}"
                )


# ===========================================================================
# Unit tests for report generator (Task 10.3)
# ===========================================================================

import json
import os
import tempfile

import pandas as pd
import pytest

from positioning_analysis.config import APP_REGISTRY

# Re-use the importlib-based import from above
load_all_data = _report.load_all_data
build_competitive_landscape = _report.build_competitive_landscape
generate_html_report = _report.generate_html_report


# ---------------------------------------------------------------------------
# Helpers – mock data builders
# ---------------------------------------------------------------------------

def _make_cleaned_reviews_csv(path: str, rows: list[dict] | None = None) -> None:
    """Write a minimal cleaned_reviews.csv."""
    if rows is None:
        rows = [
            {
                "review_id": "r1",
                "app_name": "Astrotalk",
                "category": "astrology",
                "review_text": "Great app for kundli",
                "star_rating": 4.5,
                "review_date": "2024-01-01",
                "review_source": "google_play",
                "language": "en",
                "market_region": "india",
            },
            {
                "review_id": "r2",
                "app_name": "Ancestry.com",
                "category": "ancestry",
                "review_text": "Love the family tree feature",
                "star_rating": 5.0,
                "review_date": "2024-02-01",
                "review_source": "apple_app_store",
                "language": "en",
                "market_region": "global",
            },
        ]
    pd.DataFrame(rows).to_csv(path, index=False)


def _make_sentiment_results_csv(path: str) -> None:
    pd.DataFrame([
        {
            "review_id": "r1",
            "app_name": "Astrotalk",
            "category": "astrology",
            "overall_sentiment": "positive",
            "sentiment_score": 0.8,
            "feature_mentions": json.dumps(["kundli_matching"]),
            "feature_sentiments": json.dumps([{"feature": "kundli_matching", "sentiment": "positive", "score": 0.8}]),
            "language": "en",
            "sentiment_method": "vader",
            "translated": False,
        },
    ]).to_csv(path, index=False)


def _make_sentiment_summary_json(path: str) -> None:
    summary = {
        "per_app": {
            "Astrotalk": {"avg_score": 0.6, "positive_pct": 70, "negative_pct": 10, "neutral_pct": 20, "review_count": 50},
        },
        "per_category": {
            "astrology": {"avg_score": 0.5, "positive_pct": 60, "negative_pct": 20, "neutral_pct": 20, "review_count": 100},
            "ancestry": {"avg_score": 0.4, "positive_pct": 55, "negative_pct": 25, "neutral_pct": 20, "review_count": 80},
        },
        "per_region": {
            "india": {"avg_score": 0.5, "positive_pct": 60, "negative_pct": 20, "neutral_pct": 20, "review_count": 90},
        },
        "top_praised_features": [
            {"feature": "kundli_matching", "avg_score": 0.9, "mention_count": 30},
            {"feature": "rashi", "avg_score": 0.7, "mention_count": 20},
        ],
        "top_criticized_features": [
            {"feature": "numerology", "avg_score": -0.5, "mention_count": 10},
        ],
    }
    with open(path, "w") as f:
        json.dump(summary, f)


def _make_wtp_summary_json(path: str) -> None:
    summary = {
        "per_category": {
            "astrology": {"total_reviews": 100, "reviews_with_wtp": 15, "wtp_pct": 15.0, "positive_wtp_count": 10, "negative_wtp_count": 3, "conditional_wtp_count": 2},
        },
        "per_region": {},
        "top_features_willing_to_pay": [{"feature": "kundli_matching", "positive_wtp_count": 8}],
        "top_pricing_complaints": [{"feature": "numerology", "negative_wtp_count": 3}],
        "monetization_models": {"Astrotalk": {"model": "freemium", "confidence": 0.75}},
        "cross_category_monetization": {
            "ancestry_to_astrology_wtp": {"count": 5, "features": ["kundli"]},
            "astrology_to_ancestry_wtp": {"count": 3, "features": ["family_tree"]},
        },
        "family_tree_specific_wtp": {"total_signals": 4, "positive": 3, "negative": 1, "top_features": [{"feature": "tree_export", "count": 2}]},
        "astrology_specific_wtp": {"total_signals": 10, "positive": 7, "negative": 3, "top_features": [{"feature": "kundli_matching", "count": 5}]},
    }
    with open(path, "w") as f:
        json.dump(summary, f)


def _make_overlap_summary_json(path: str) -> None:
    summary = {
        "astrology_to_ancestry_pct": 12.5,
        "ancestry_to_astrology_pct": 8.3,
        "top_cross_features_astrology_to_ancestry": [{"feature": "family_tree", "count": 10}],
        "top_cross_features_ancestry_to_astrology": [{"feature": "kundli", "count": 6}],
    }
    with open(path, "w") as f:
        json.dump(summary, f)


def _make_cleaning_summary_json(path: str) -> None:
    summary = {
        "total_collected": 200,
        "duplicates_removed": 20,
        "short_reviews_discarded": 10,
        "final_count": 170,
        "per_app_counts": {"Astrotalk": 90, "Ancestry.com": 80},
    }
    with open(path, "w") as f:
        json.dump(summary, f)


def _populate_data_dir(data_dir: str) -> None:
    """Create all mock data files in *data_dir*."""
    _make_cleaned_reviews_csv(os.path.join(data_dir, "cleaned_reviews.csv"))
    _make_sentiment_results_csv(os.path.join(data_dir, "sentiment_results.csv"))
    _make_sentiment_summary_json(os.path.join(data_dir, "sentiment_summary.json"))
    _make_wtp_summary_json(os.path.join(data_dir, "wtp_summary.json"))
    _make_overlap_summary_json(os.path.join(data_dir, "overlap_summary.json"))
    _make_cleaning_summary_json(os.path.join(data_dir, "cleaning_summary.json"))


# ---------------------------------------------------------------------------
# Tests for load_all_data
# ---------------------------------------------------------------------------

class TestLoadAllData:
    """Tests for load_all_data — Requirements 9.1, 10.1."""

    def test_returns_expected_keys_with_data(self, monkeypatch, tmp_path):
        """load_all_data returns dict with all expected CSV and JSON keys."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)
        _populate_data_dir(data_dir)

        monkeypatch.setattr(_report, "DATA_DIR", data_dir)
        result = load_all_data()

        expected_keys = {
            "cleaned_reviews",
            "sentiment_results",
            "wtp_results",
            "overlap_results",
            "sentiment_summary",
            "wtp_summary",
            "overlap_summary",
            "cleaning_summary",
        }
        assert expected_keys == set(result.keys())

    def test_returns_expected_keys_when_files_missing(self, monkeypatch, tmp_path):
        """load_all_data returns dict with all keys even when no files exist."""
        data_dir = str(tmp_path / "empty_data")
        os.makedirs(data_dir)

        monkeypatch.setattr(_report, "DATA_DIR", data_dir)
        result = load_all_data()

        # CSV keys should be empty DataFrames
        for csv_key in ("cleaned_reviews", "sentiment_results", "wtp_results", "overlap_results"):
            assert isinstance(result[csv_key], pd.DataFrame)
            assert result[csv_key].empty

        # JSON keys should be empty dicts
        for json_key in ("sentiment_summary", "wtp_summary", "overlap_summary", "cleaning_summary"):
            assert isinstance(result[json_key], dict)
            assert result[json_key] == {}

    def test_loads_csv_data_correctly(self, monkeypatch, tmp_path):
        """load_all_data correctly reads CSV content."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)
        _populate_data_dir(data_dir)

        monkeypatch.setattr(_report, "DATA_DIR", data_dir)
        result = load_all_data()

        cleaned = result["cleaned_reviews"]
        assert not cleaned.empty
        assert "app_name" in cleaned.columns
        assert "Astrotalk" in cleaned["app_name"].values

    def test_loads_json_data_correctly(self, monkeypatch, tmp_path):
        """load_all_data correctly reads JSON content."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)
        _populate_data_dir(data_dir)

        monkeypatch.setattr(_report, "DATA_DIR", data_dir)
        result = load_all_data()

        assert result["sentiment_summary"]["per_app"]["Astrotalk"]["avg_score"] == 0.6
        assert result["cleaning_summary"]["final_count"] == 170


# ---------------------------------------------------------------------------
# Tests for build_competitive_landscape
# ---------------------------------------------------------------------------

class TestBuildCompetitiveLandscape:
    """Tests for build_competitive_landscape — Requirements 9.1, 10.1."""

    def test_produces_valid_structure(self, monkeypatch, tmp_path):
        """build_competitive_landscape returns dict with required top-level keys."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)
        monkeypatch.setattr(_report, "DATA_DIR", data_dir)

        _populate_data_dir(data_dir)
        monkeypatch.setattr(_report, "DATA_DIR", data_dir)
        data = load_all_data()
        landscape = build_competitive_landscape(data)

        assert "apps" in landscape
        assert "market_gaps" in landscape
        assert "top_astrology_features" in landscape
        assert "top_ancestry_features" in landscape
        assert "hybrid_apps" in landscape

    def test_apps_list_contains_registry_entries(self, monkeypatch, tmp_path):
        """All APP_REGISTRY apps appear in the landscape apps list."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)
        _populate_data_dir(data_dir)
        monkeypatch.setattr(_report, "DATA_DIR", data_dir)

        data = load_all_data()
        landscape = build_competitive_landscape(data)

        app_names_in_landscape = {a["app_name"] for a in landscape["apps"]}
        for entry in APP_REGISTRY:
            assert entry["name"] in app_names_in_landscape

    def test_app_entry_has_required_fields(self, monkeypatch, tmp_path):
        """Each app entry in the landscape has the expected fields."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)
        _populate_data_dir(data_dir)
        monkeypatch.setattr(_report, "DATA_DIR", data_dir)

        data = load_all_data()
        landscape = build_competitive_landscape(data)

        required_fields = {"app_name", "category", "market_region", "avg_star_rating", "total_review_count", "dominant_sentiment", "top_features"}
        for app in landscape["apps"]:
            assert required_fields.issubset(set(app.keys()))

    def test_writes_json_to_disk(self, monkeypatch, tmp_path):
        """build_competitive_landscape writes competitive_landscape.json."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)
        _populate_data_dir(data_dir)
        monkeypatch.setattr(_report, "DATA_DIR", data_dir)

        data = load_all_data()
        build_competitive_landscape(data)

        json_path = os.path.join(data_dir, "competitive_landscape.json")
        assert os.path.exists(json_path)
        with open(json_path) as f:
            saved = json.load(f)
        assert "apps" in saved

    def test_handles_empty_data(self, monkeypatch, tmp_path):
        """build_competitive_landscape works with empty DataFrames/dicts."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)
        monkeypatch.setattr(_report, "DATA_DIR", data_dir)

        data = {
            "cleaned_reviews": pd.DataFrame(),
            "sentiment_results": pd.DataFrame(),
            "sentiment_summary": {},
            "wtp_summary": {},
            "overlap_summary": {},
            "cleaning_summary": {},
        }
        landscape = build_competitive_landscape(data)

        assert isinstance(landscape["apps"], list)
        # Should still include registry apps even with no review data
        assert len(landscape["apps"]) >= len(APP_REGISTRY)


# ---------------------------------------------------------------------------
# Tests for generate_html_report
# ---------------------------------------------------------------------------

_EXPECTED_SECTION_HEADINGS = [
    "Executive Summary",
    "Data Collection Overview",
    "Sentiment Analysis",
    "Willingness-to-Pay Analysis",
    "Demand Overlap Analysis",
    "Competitive Landscape",
    "Family Tree Monetization Strategy",
    "Strategic Recommendations",
    "Data Limitations",
]


class TestGenerateHtmlReport:
    """Tests for generate_html_report — Requirements 10.1, 10.7."""

    def _build_full_data(self, monkeypatch, tmp_path) -> dict:
        """Helper: load mock data and build landscape."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)
        _populate_data_dir(data_dir)
        monkeypatch.setattr(_report, "DATA_DIR", data_dir)

        data = load_all_data()
        data["competitive_landscape"] = build_competitive_landscape(data)
        return data

    def test_html_contains_all_section_headings(self, monkeypatch, tmp_path):
        """The generated HTML contains all 9 expected section headings."""
        data = self._build_full_data(monkeypatch, tmp_path)
        output_path = str(tmp_path / "report.html")
        generate_html_report(data, output_path)

        with open(output_path, "r", encoding="utf-8") as f:
            html = f.read()

        for heading in _EXPECTED_SECTION_HEADINGS:
            assert heading in html, f"Missing section heading: {heading}"

    def test_html_contains_plotly_script(self, monkeypatch, tmp_path):
        """The HTML output includes the Plotly CDN script tag."""
        data = self._build_full_data(monkeypatch, tmp_path)
        output_path = str(tmp_path / "report.html")
        generate_html_report(data, output_path)

        with open(output_path, "r", encoding="utf-8") as f:
            html = f.read()

        assert "plotly" in html.lower()
        assert "cdn.plot.ly" in html or "plotly-latest.min.js" in html

    def test_html_is_valid_document(self, monkeypatch, tmp_path):
        """The HTML output starts with DOCTYPE and contains html/head/body tags."""
        data = self._build_full_data(monkeypatch, tmp_path)
        output_path = str(tmp_path / "report.html")
        generate_html_report(data, output_path)

        with open(output_path, "r", encoding="utf-8") as f:
            html = f.read()

        assert html.strip().startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html

    def test_handles_empty_data_gracefully(self, monkeypatch, tmp_path):
        """generate_html_report does not crash with empty data."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)
        monkeypatch.setattr(_report, "DATA_DIR", data_dir)

        data = {
            "cleaned_reviews": pd.DataFrame(),
            "sentiment_results": pd.DataFrame(),
            "sentiment_summary": {},
            "wtp_summary": {},
            "overlap_summary": {},
            "cleaning_summary": {},
            "competitive_landscape": {
                "apps": [],
                "market_gaps": [],
                "top_astrology_features": [],
                "top_ancestry_features": [],
                "hybrid_apps": [],
            },
        }
        output_path = str(tmp_path / "empty_report.html")
        # Should not raise
        generate_html_report(data, output_path)

        assert os.path.exists(output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            html = f.read()
        assert "<!DOCTYPE html>" in html

    def test_creates_output_directory(self, monkeypatch, tmp_path):
        """generate_html_report creates the output directory if it doesn't exist."""
        data = {
            "cleaned_reviews": pd.DataFrame(),
            "sentiment_results": pd.DataFrame(),
            "sentiment_summary": {},
            "wtp_summary": {},
            "overlap_summary": {},
            "cleaning_summary": {},
            "competitive_landscape": {"apps": [], "market_gaps": [], "top_astrology_features": [], "top_ancestry_features": [], "hybrid_apps": []},
        }
        nested_path = str(tmp_path / "new_dir" / "sub" / "report.html")
        generate_html_report(data, nested_path)
        assert os.path.exists(nested_path)
