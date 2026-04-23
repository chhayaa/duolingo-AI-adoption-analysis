"""
Property-based tests for the positioning_analysis demand overlap analyzer module.

Property 8: Bidirectional demand overlap detection
Property 9: Overlap percentage calculation correctness
"""

import importlib

import pandas as pd
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from positioning_analysis.config import (
    OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS,
    OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS,
)

# Import the module that starts with a digit via importlib
_overlap = importlib.import_module("positioning_analysis.05_demand_overlap")
detect_overlap_signals = _overlap.detect_overlap_signals
_build_overlap_summary = _overlap._build_overlap_summary


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strategy: pick a keyword that astrology users use to express ancestry interest
_astro_to_ancestry_keyword = st.sampled_from(OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS)

# Strategy: pick a keyword that ancestry users use to express astrology interest
_ancestry_to_astro_keyword = st.sampled_from(OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS)

# Filler text that won't accidentally contain overlap keywords
_safe_filler = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
    min_size=3,
    max_size=30,
).filter(
    lambda t: not any(
        kw.lower() in t.lower()
        for kw in OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS + OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS
    )
)


# ---------------------------------------------------------------------------
# Property 8: Bidirectional demand overlap detection
# Validates: Requirements 8.1, 8.2, 8.3
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    keyword=_astro_to_ancestry_keyword,
    prefix=_safe_filler,
    suffix=_safe_filler,
)
def test_astrology_review_with_ancestry_keyword_detected(keyword, prefix, suffix):
    """Feature: positioning-analysis, Property 8: Bidirectional demand overlap detection

    **Validates: Requirements 8.1, 8.2, 8.3**

    For any review text from an astrology app that contains an ancestry/family
    keyword, detect_overlap_signals SHALL return at least one signal with
    target_category == "ancestry" and a non-empty cross_feature.
    """
    text = f"{prefix} {keyword} {suffix}"

    signals = detect_overlap_signals(text, source_category="astrology")

    assert len(signals) >= 1, (
        f"Expected at least one overlap signal for astrology review with "
        f"ancestry keyword {keyword!r}, got none"
    )

    for sig in signals:
        assert sig["target_category"] == "ancestry", (
            f"Expected target_category 'ancestry', got {sig['target_category']!r}"
        )
        assert sig["cross_feature"], (
            f"Expected non-empty cross_feature, got {sig['cross_feature']!r}"
        )


@settings(max_examples=100, deadline=None)
@given(
    keyword=_ancestry_to_astro_keyword,
    prefix=_safe_filler,
    suffix=_safe_filler,
)
def test_ancestry_review_with_astrology_keyword_detected(keyword, prefix, suffix):
    """Feature: positioning-analysis, Property 8: Bidirectional demand overlap detection

    **Validates: Requirements 8.1, 8.2, 8.3**

    Symmetrically, for any review text from an ancestry app that contains an
    astrology keyword, detect_overlap_signals SHALL return at least one signal
    with target_category == "astrology" and a non-empty cross_feature.
    """
    text = f"{prefix} {keyword} {suffix}"

    signals = detect_overlap_signals(text, source_category="ancestry")

    assert len(signals) >= 1, (
        f"Expected at least one overlap signal for ancestry review with "
        f"astrology keyword {keyword!r}, got none"
    )

    for sig in signals:
        assert sig["target_category"] == "astrology", (
            f"Expected target_category 'astrology', got {sig['target_category']!r}"
        )
        assert sig["cross_feature"], (
            f"Expected non-empty cross_feature, got {sig['cross_feature']!r}"
        )


@settings(max_examples=100, deadline=None)
@given(
    keyword=_astro_to_ancestry_keyword,
    prefix=_safe_filler,
    suffix=_safe_filler,
)
def test_overlap_signal_has_required_fields(keyword, prefix, suffix):
    """Feature: positioning-analysis, Property 8: Bidirectional demand overlap detection

    **Validates: Requirements 8.1, 8.2, 8.3**

    Each signal SHALL include all required fields: signal_text,
    target_category, cross_feature.
    """
    text = f"{prefix} {keyword} {suffix}"

    signals = detect_overlap_signals(text, source_category="astrology")
    assert len(signals) >= 1

    required_keys = {"signal_text", "target_category", "cross_feature"}
    for sig in signals:
        assert required_keys.issubset(sig.keys()), (
            f"Signal missing required keys. Expected {required_keys}, "
            f"got {set(sig.keys())}"
        )


# ---------------------------------------------------------------------------
# Property 9: Overlap percentage calculation correctness
# Validates: Requirements 8.4, 8.5
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    total_astrology=st.integers(min_value=1, max_value=500),
    total_ancestry=st.integers(min_value=1, max_value=500),
    astro_overlap_reviews=st.integers(min_value=0, max_value=500),
    ancestry_overlap_reviews=st.integers(min_value=0, max_value=500),
)
def test_overlap_percentage_calculation(
    total_astrology, total_ancestry, astro_overlap_reviews, ancestry_overlap_reviews
):
    """Feature: positioning-analysis, Property 9: Overlap percentage calculation correctness

    **Validates: Requirements 8.4, 8.5**

    For any dataset of cleaned reviews with known overlap signal counts, the
    calculated overlap percentage SHALL equal
    (reviews_with_signals / total_reviews_in_category) * 100.
    """
    # Ensure overlap counts don't exceed totals
    assume(astro_overlap_reviews <= total_astrology)
    assume(ancestry_overlap_reviews <= total_ancestry)

    # Build a cleaned_df with the right number of reviews per category
    rows = []
    for i in range(total_astrology):
        rows.append({
            "review_id": f"astro_{i}",
            "app_name": "TestAstroApp",
            "category": "astrology",
            "review_text": f"astrology review {i}",
        })
    for i in range(total_ancestry):
        rows.append({
            "review_id": f"ancestry_{i}",
            "app_name": "TestAncestryApp",
            "category": "ancestry",
            "review_text": f"ancestry review {i}",
        })
    cleaned_df = pd.DataFrame(rows)

    # Build an overlap_df with the right number of overlap signals
    overlap_rows = []
    for i in range(astro_overlap_reviews):
        overlap_rows.append({
            "review_id": f"astro_{i}",
            "app_name": "TestAstroApp",
            "source_category": "astrology",
            "target_category": "ancestry",
            "signal_text": "family tree",
            "cross_feature": "family tree",
        })
    for i in range(ancestry_overlap_reviews):
        overlap_rows.append({
            "review_id": f"ancestry_{i}",
            "app_name": "TestAncestryApp",
            "source_category": "ancestry",
            "target_category": "astrology",
            "signal_text": "horoscope",
            "cross_feature": "horoscope",
        })
    overlap_df = pd.DataFrame(overlap_rows)

    if overlap_df.empty:
        overlap_df = pd.DataFrame(columns=[
            "review_id", "app_name", "source_category",
            "target_category", "signal_text", "cross_feature",
        ])

    summary = _build_overlap_summary(cleaned_df, overlap_df)

    # Expected percentages
    expected_astro_pct = round(astro_overlap_reviews / total_astrology * 100, 2)
    expected_ancestry_pct = round(ancestry_overlap_reviews / total_ancestry * 100, 2)

    assert summary["astrology_to_ancestry_pct"] == expected_astro_pct, (
        f"Astrology→Ancestry pct: expected {expected_astro_pct}, "
        f"got {summary['astrology_to_ancestry_pct']}"
    )
    assert summary["ancestry_to_astrology_pct"] == expected_ancestry_pct, (
        f"Ancestry→Astrology pct: expected {expected_ancestry_pct}, "
        f"got {summary['ancestry_to_astrology_pct']}"
    )


# ---------------------------------------------------------------------------
# Unit Tests for demand overlap analyzer
# Requirements: 8.1, 8.2, 8.4, 8.5
# ---------------------------------------------------------------------------

import pytest


class TestDetectOverlapSignals:
    """Unit tests for detect_overlap_signals — Requirements 8.1, 8.2."""

    # -- Astrology → Ancestry direction (Req 8.1) --

    def test_astrology_review_detects_family_tree_keyword(self):
        """An astrology review mentioning 'family tree' should produce an ancestry signal."""
        signals = detect_overlap_signals(
            "I love this horoscope app but wish it had a family tree feature",
            source_category="astrology",
        )
        assert len(signals) >= 1
        assert any(s["cross_feature"] == "family tree" for s in signals)
        assert all(s["target_category"] == "ancestry" for s in signals)

    def test_astrology_review_detects_ancestry_keyword(self):
        """An astrology review mentioning 'ancestry' should produce an ancestry signal."""
        signals = detect_overlap_signals(
            "Would be great if this app also explored ancestry connections",
            source_category="astrology",
        )
        assert len(signals) >= 1
        assert any(s["cross_feature"] == "ancestry" for s in signals)

    def test_astrology_review_detects_india_specific_keyword(self):
        """An astrology review mentioning 'gotra' should produce an ancestry signal."""
        signals = detect_overlap_signals(
            "Can you add gotra information to the kundli report?",
            source_category="astrology",
        )
        assert len(signals) >= 1
        assert any(s["cross_feature"] == "gotra" for s in signals)

    def test_astrology_review_multiple_keywords(self):
        """Multiple ancestry keywords in one astrology review should each be detected."""
        signals = detect_overlap_signals(
            "I want family tree and genealogy features in my astrology app",
            source_category="astrology",
        )
        features = {s["cross_feature"] for s in signals}
        assert "family tree" in features
        assert "genealogy" in features

    # -- Ancestry → Astrology direction (Req 8.2) --

    def test_ancestry_review_detects_horoscope_keyword(self):
        """An ancestry review mentioning 'horoscope' should produce an astrology signal."""
        signals = detect_overlap_signals(
            "It would be nice to see horoscope data for my ancestors",
            source_category="ancestry",
        )
        assert len(signals) >= 1
        assert any(s["cross_feature"] == "horoscope" for s in signals)
        assert all(s["target_category"] == "astrology" for s in signals)

    def test_ancestry_review_detects_kundli_keyword(self):
        """An ancestry review mentioning 'kundli' should produce an astrology signal."""
        signals = detect_overlap_signals(
            "Please add kundli matching for family members",
            source_category="ancestry",
        )
        assert len(signals) >= 1
        assert any(s["cross_feature"] == "kundli" for s in signals)

    def test_ancestry_review_detects_zodiac_keyword(self):
        """An ancestry review mentioning 'zodiac' should produce an astrology signal."""
        signals = detect_overlap_signals(
            "Would love to see zodiac signs for each family member",
            source_category="ancestry",
        )
        assert len(signals) >= 1
        assert any(s["cross_feature"] == "zodiac" for s in signals)

    # -- Edge cases --

    def test_empty_text_returns_no_signals(self):
        """Empty text should return an empty list."""
        assert detect_overlap_signals("", "astrology") == []

    def test_none_text_returns_no_signals(self):
        """None text should return an empty list."""
        assert detect_overlap_signals(None, "astrology") == []

    def test_unknown_category_returns_no_signals(self):
        """An unknown source category should return an empty list."""
        signals = detect_overlap_signals(
            "family tree and horoscope are great",
            source_category="unknown",
        )
        assert signals == []

    def test_no_cross_keywords_returns_empty(self):
        """Text with no cross-category keywords should return an empty list."""
        signals = detect_overlap_signals(
            "This app is really good and I use it every day",
            source_category="astrology",
        )
        assert signals == []

    def test_case_insensitive_detection(self):
        """Keywords should be detected regardless of case."""
        signals = detect_overlap_signals(
            "I want FAMILY TREE features",
            source_category="astrology",
        )
        assert len(signals) >= 1
        assert any(s["cross_feature"] == "family tree" for s in signals)


class TestBuildOverlapSummary:
    """Unit tests for _build_overlap_summary — Requirements 8.4, 8.5."""

    def test_percentage_calculation_known_counts(self):
        """Verify percentage = (overlap_reviews / total_reviews) * 100 with known values."""
        # 100 astrology reviews, 10 with overlap → 10%
        # 50 ancestry reviews, 5 with overlap → 10%
        cleaned_rows = (
            [{"review_id": f"a{i}", "category": "astrology"} for i in range(100)]
            + [{"review_id": f"b{i}", "category": "ancestry"} for i in range(50)]
        )
        cleaned_df = pd.DataFrame(cleaned_rows)

        overlap_rows = (
            [
                {
                    "review_id": f"a{i}",
                    "source_category": "astrology",
                    "target_category": "ancestry",
                    "signal_text": "family tree",
                    "cross_feature": "family tree",
                    "app_name": "TestApp",
                }
                for i in range(10)
            ]
            + [
                {
                    "review_id": f"b{i}",
                    "source_category": "ancestry",
                    "target_category": "astrology",
                    "signal_text": "horoscope",
                    "cross_feature": "horoscope",
                    "app_name": "TestApp",
                }
                for i in range(5)
            ]
        )
        overlap_df = pd.DataFrame(overlap_rows)

        summary = _build_overlap_summary(cleaned_df, overlap_df)

        assert summary["astrology_to_ancestry_pct"] == 10.0
        assert summary["ancestry_to_astrology_pct"] == 10.0

    def test_percentage_calculation_fractional(self):
        """Verify fractional percentages are rounded to 2 decimal places."""
        # 3 astrology reviews, 1 with overlap → 33.33%
        cleaned_df = pd.DataFrame(
            [{"review_id": f"a{i}", "category": "astrology"} for i in range(3)]
        )
        overlap_df = pd.DataFrame(
            [
                {
                    "review_id": "a0",
                    "source_category": "astrology",
                    "target_category": "ancestry",
                    "signal_text": "family tree",
                    "cross_feature": "family tree",
                    "app_name": "TestApp",
                }
            ]
        )

        summary = _build_overlap_summary(cleaned_df, overlap_df)

        assert summary["astrology_to_ancestry_pct"] == round(1 / 3 * 100, 2)

    def test_zero_denominator_astrology(self):
        """When there are zero astrology reviews, percentage should be 0.0 (no division error)."""
        cleaned_df = pd.DataFrame(
            [{"review_id": "b0", "category": "ancestry"}]
        )
        overlap_df = pd.DataFrame(
            columns=[
                "review_id", "app_name", "source_category",
                "target_category", "signal_text", "cross_feature",
            ]
        )

        summary = _build_overlap_summary(cleaned_df, overlap_df)

        assert summary["astrology_to_ancestry_pct"] == 0.0

    def test_zero_denominator_ancestry(self):
        """When there are zero ancestry reviews, percentage should be 0.0 (no division error)."""
        cleaned_df = pd.DataFrame(
            [{"review_id": "a0", "category": "astrology"}]
        )
        overlap_df = pd.DataFrame(
            columns=[
                "review_id", "app_name", "source_category",
                "target_category", "signal_text", "cross_feature",
            ]
        )

        summary = _build_overlap_summary(cleaned_df, overlap_df)

        assert summary["ancestry_to_astrology_pct"] == 0.0

    def test_zero_denominator_both_categories(self):
        """When there are zero reviews in both categories, both percentages should be 0.0."""
        cleaned_df = pd.DataFrame(columns=["review_id", "category"])
        overlap_df = pd.DataFrame(
            columns=[
                "review_id", "app_name", "source_category",
                "target_category", "signal_text", "cross_feature",
            ]
        )

        summary = _build_overlap_summary(cleaned_df, overlap_df)

        assert summary["astrology_to_ancestry_pct"] == 0.0
        assert summary["ancestry_to_astrology_pct"] == 0.0

    def test_empty_overlap_df(self):
        """When no overlap signals exist, percentages should be 0.0 and top features empty."""
        cleaned_df = pd.DataFrame(
            [{"review_id": f"a{i}", "category": "astrology"} for i in range(10)]
            + [{"review_id": f"b{i}", "category": "ancestry"} for i in range(10)]
        )
        overlap_df = pd.DataFrame(
            columns=[
                "review_id", "app_name", "source_category",
                "target_category", "signal_text", "cross_feature",
            ]
        )

        summary = _build_overlap_summary(cleaned_df, overlap_df)

        assert summary["astrology_to_ancestry_pct"] == 0.0
        assert summary["ancestry_to_astrology_pct"] == 0.0
        assert summary["top_cross_features_astrology_to_ancestry"] == []
        assert summary["top_cross_features_ancestry_to_astrology"] == []
