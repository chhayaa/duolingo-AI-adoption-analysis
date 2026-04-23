"""
Property-based tests for the positioning_analysis WTP analyzer module.

Property 7: WTP detection, classification, and feature association
Property 12: Monetization model classification validity
"""

import importlib
import random

import pandas as pd
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from positioning_analysis.config import (
    WTP_POSITIVE_PATTERNS,
    WTP_NEGATIVE_PATTERNS,
    WTP_CONDITIONAL_PATTERNS,
    ASTROLOGY_FEATURE_KEYWORDS,
    ANCESTRY_FEATURE_KEYWORDS,
    ASTROLOGY_MONETIZATION_KEYWORDS,
    ANCESTRY_MONETIZATION_KEYWORDS,
    MONETIZATION_MODEL_PATTERNS,
)

# Import the module that starts with a digit via importlib
_wtp = importlib.import_module("positioning_analysis.04_wtp_analysis")
detect_wtp_signals = _wtp.detect_wtp_signals
classify_wtp_signal = _wtp.classify_wtp_signal
classify_monetization_model = _wtp.classify_monetization_model


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# All WTP patterns grouped by classification
_all_wtp_patterns = (
    [("positive_wtp", p) for p in WTP_POSITIVE_PATTERNS]
    + [("negative_wtp", p) for p in WTP_NEGATIVE_PATTERNS]
    + [("conditional_wtp", p) for p in WTP_CONDITIONAL_PATTERNS]
)

# Strategy: pick a random WTP pattern
_wtp_pattern = st.sampled_from(_all_wtp_patterns)

# Filler text that won't accidentally contain WTP or feature keywords
_safe_filler = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
    min_size=3,
    max_size=30,
)

# All feature keywords flattened: (feature_name, keyword)
_all_feature_pairs = []
for _feat, _kws in ASTROLOGY_FEATURE_KEYWORDS.items():
    for _kw in _kws:
        _all_feature_pairs.append((_feat, _kw))
for _feat, _kws in ANCESTRY_FEATURE_KEYWORDS.items():
    for _kw in _kws:
        _all_feature_pairs.append((_feat, _kw))

_feature_pair = st.sampled_from(_all_feature_pairs)

# All monetization keywords flattened across models
_all_monetization_keywords = []
for _model, _kws in MONETIZATION_MODEL_PATTERNS.items():
    for _kw in _kws:
        _all_monetization_keywords.append((_model, _kw))

_monetization_keyword = st.sampled_from(_all_monetization_keywords)


# ---------------------------------------------------------------------------
# Property 7: WTP detection, classification, and feature association
# Validates: Requirements 7.1, 7.2, 7.3
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    pattern=_wtp_pattern,
    prefix=_safe_filler,
    suffix=_safe_filler,
)
def test_wtp_detection_returns_signal(pattern, prefix, suffix):
    """Feature: positioning-analysis, Property 7: WTP detection, classification, and feature association

    **Validates: Requirements 7.1, 7.2, 7.3**

    For any review text containing a WTP keyword pattern, detect_wtp_signals
    SHALL return at least one signal.
    """
    expected_classification, wtp_keyword = pattern
    text = f"{prefix} {wtp_keyword} {suffix}"

    signals = detect_wtp_signals(text)

    assert len(signals) >= 1, (
        f"Expected at least one WTP signal for keyword {wtp_keyword!r}, got none"
    )


@settings(max_examples=100, deadline=None)
@given(
    pattern=_wtp_pattern,
    prefix=_safe_filler,
    suffix=_safe_filler,
)
def test_wtp_classification_is_valid(pattern, prefix, suffix):
    """Feature: positioning-analysis, Property 7: WTP detection, classification, and feature association

    **Validates: Requirements 7.1, 7.2, 7.3**

    Each signal's classification SHALL be one of
    {"positive_wtp", "negative_wtp", "conditional_wtp"}.
    """
    expected_classification, wtp_keyword = pattern
    text = f"{prefix} {wtp_keyword} {suffix}"

    signals = detect_wtp_signals(text)
    valid_classifications = {"positive_wtp", "negative_wtp", "conditional_wtp"}

    for sig in signals:
        assert sig["classification"] in valid_classifications, (
            f"Invalid classification {sig['classification']!r} for keyword {wtp_keyword!r}"
        )



@settings(max_examples=100, deadline=None)
@given(
    pattern=_wtp_pattern,
    feature=_feature_pair,
    prefix=_safe_filler,
    suffix=_safe_filler,
)
def test_wtp_feature_association_non_null(pattern, feature, prefix, suffix):
    """Feature: positioning-analysis, Property 7: WTP detection, classification, and feature association

    **Validates: Requirements 7.1, 7.2, 7.3**

    If the text also contains a feature keyword, the signal's
    associated_feature SHALL be non-null.
    """
    expected_classification, wtp_keyword = pattern
    feature_name, feature_keyword = feature

    # Build text with both a WTP keyword and a feature keyword
    text = f"{prefix} {wtp_keyword} for {feature_keyword} {suffix}"

    signals = detect_wtp_signals(text)
    assert len(signals) >= 1, (
        f"Expected at least one WTP signal for keyword {wtp_keyword!r}, got none"
    )

    # At least one signal should have a non-null associated_feature
    features_found = [s["associated_feature"] for s in signals if s["associated_feature"] is not None]
    assert len(features_found) >= 1, (
        f"Expected at least one signal with non-null associated_feature when "
        f"feature keyword {feature_keyword!r} is present. "
        f"Signals: {signals}"
    )


# ---------------------------------------------------------------------------
# Property 12: Monetization model classification validity
# Validates: Requirements 13.2
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    keywords=st.lists(
        _monetization_keyword,
        min_size=1,
        max_size=10,
    ),
    filler=_safe_filler,
)
def test_monetization_model_classification_valid(keywords, filler):
    """Feature: positioning-analysis, Property 12: Monetization model classification validity

    **Validates: Requirements 13.2**

    For any app's review set, classify_monetization_model SHALL return one of
    {"subscription", "one_time", "freemium", "ad_supported"} and the
    confidence SHALL be in the range [0.0, 1.0].
    """
    valid_models = {"subscription", "one_time", "freemium", "ad_supported"}

    # Build a DataFrame with review_text containing monetization keywords
    review_texts = []
    for _model, kw in keywords:
        review_texts.append(f"{filler} {kw} {filler}")

    df = pd.DataFrame({"review_text": review_texts})

    model, confidence = classify_monetization_model(df)

    assert model in valid_models, (
        f"Model {model!r} not in valid set {valid_models}. "
        f"Keywords used: {[kw for _, kw in keywords]}"
    )
    assert 0.0 <= confidence <= 1.0, (
        f"Confidence {confidence} out of range [0.0, 1.0]"
    )


# ---------------------------------------------------------------------------
# Unit Tests for WTP Analyzer (Task 7.3)
# ---------------------------------------------------------------------------

import pytest

analyze_cross_category_monetization = _wtp.analyze_cross_category_monetization
_track_category_wtp = _wtp._track_category_wtp


class TestDetectWtpSignals:
    """Unit tests for detect_wtp_signals — Requirements 7.1, 7.2, 7.3."""

    def test_positive_keyword_detected(self):
        text = "This app is worth paying for the premium features."
        signals = detect_wtp_signals(text)
        assert len(signals) >= 1
        assert any(s["classification"] == "positive_wtp" for s in signals)

    def test_negative_keyword_detected(self):
        text = "This app is too expensive and not worth the money."
        signals = detect_wtp_signals(text)
        assert len(signals) >= 1
        assert any(s["classification"] == "negative_wtp" for s in signals)

    def test_conditional_keyword_detected(self):
        text = "I would pay if they add better kundli matching features."
        signals = detect_wtp_signals(text)
        assert len(signals) >= 1
        assert any(s["classification"] == "conditional_wtp" for s in signals)

    def test_no_signal_in_plain_text(self):
        text = "The app has a nice user interface and loads quickly."
        signals = detect_wtp_signals(text)
        assert signals == []

    def test_empty_text_returns_empty(self):
        assert detect_wtp_signals("") == []
        assert detect_wtp_signals(None) == []

    def test_feature_association_with_astrology_keyword(self):
        text = "I would gladly pay for better horoscope predictions."
        signals = detect_wtp_signals(text, category="astrology")
        assert len(signals) >= 1
        features = [s["associated_feature"] for s in signals if s["associated_feature"]]
        assert len(features) >= 1

    def test_feature_association_with_ancestry_keyword(self):
        text = "Worth paying for the family tree export feature."
        signals = detect_wtp_signals(text, category="ancestry")
        assert len(signals) >= 1
        features = [s["associated_feature"] for s in signals if s["associated_feature"]]
        assert len(features) >= 1

    def test_multiple_signals_in_one_text(self):
        text = "This app is worth paying for. But some features are too expensive."
        signals = detect_wtp_signals(text)
        assert len(signals) >= 2

    def test_signal_text_matches_pattern(self):
        text = "The premium version is money well spent on this app."
        signals = detect_wtp_signals(text)
        assert len(signals) >= 1
        assert any("money well spent" in s["signal_text"].lower() for s in signals)


class TestClassifyWtpSignal:
    """Unit tests for classify_wtp_signal — Requirements 7.1, 7.2."""

    def test_positive_classification(self):
        assert classify_wtp_signal("worth paying") == "positive_wtp"
        assert classify_wtp_signal("good value") == "positive_wtp"
        assert classify_wtp_signal("money well spent") == "positive_wtp"

    def test_negative_classification(self):
        assert classify_wtp_signal("too expensive") == "negative_wtp"
        assert classify_wtp_signal("waste of money") == "negative_wtp"
        assert classify_wtp_signal("overpriced") == "negative_wtp"

    def test_conditional_classification(self):
        assert classify_wtp_signal("would pay if") == "conditional_wtp"
        assert classify_wtp_signal("might pay") == "conditional_wtp"
        assert classify_wtp_signal("depends on price") == "conditional_wtp"

    def test_empty_string_defaults_to_positive(self):
        assert classify_wtp_signal("") == "positive_wtp"

    def test_case_insensitive(self):
        assert classify_wtp_signal("WORTH PAYING") == "positive_wtp"
        assert classify_wtp_signal("Too Expensive") == "negative_wtp"


class TestClassifyMonetizationModel:
    """Unit tests for classify_monetization_model — Requirements 13.2."""

    def test_subscription_dominant(self):
        reviews = pd.DataFrame({
            "review_text": [
                "I love the monthly subscription plan.",
                "The yearly subscription is a great deal.",
                "I renewed my annual plan today.",
            ]
        })
        model, confidence = classify_monetization_model(reviews)
        assert model == "subscription"
        assert 0.0 < confidence <= 1.0

    def test_freemium_dominant(self):
        reviews = pd.DataFrame({
            "review_text": [
                "The free version is great but the premium upgrade is worth it.",
                "Basic free features are good, in-app purchase for more.",
                "I like the free version but want the premium upgrade.",
            ]
        })
        model, confidence = classify_monetization_model(reviews)
        assert model == "freemium"
        assert 0.0 < confidence <= 1.0

    def test_ad_supported_dominant(self):
        reviews = pd.DataFrame({
            "review_text": [
                "Too many ads in this app, please remove ads.",
                "I wish there was an ad-free version.",
                "The ads are annoying, too many ads everywhere.",
            ]
        })
        model, confidence = classify_monetization_model(reviews)
        assert model == "ad_supported"
        assert 0.0 < confidence <= 1.0

    def test_no_keywords_returns_unknown(self):
        reviews = pd.DataFrame({
            "review_text": [
                "Nice app with good features.",
                "I enjoy using this application.",
            ]
        })
        model, confidence = classify_monetization_model(reviews)
        assert model == "unknown"
        assert confidence == 0.0

    def test_empty_reviews(self):
        reviews = pd.DataFrame({"review_text": pd.Series([], dtype=str)})
        model, confidence = classify_monetization_model(reviews)
        assert model == "unknown"
        assert confidence == 0.0


class TestAnalyzeCrossCategoryMonetization:
    """Unit tests for analyze_cross_category_monetization — Requirements 13.6."""

    def test_ancestry_to_astrology_crossover(self):
        wtp_df = pd.DataFrame({
            "category": ["ancestry"],
            "wtp_signal_text": ["would pay for premium predictions and detailed report"],
            "wtp_classification": ["positive_wtp"],
            "associated_feature": [None],
        })
        result = analyze_cross_category_monetization(wtp_df)
        assert result["ancestry_to_astrology_wtp"]["count"] >= 1

    def test_astrology_to_ancestry_crossover(self):
        wtp_df = pd.DataFrame({
            "category": ["astrology"],
            "wtp_signal_text": ["would pay for premium tree and family tree export"],
            "wtp_classification": ["positive_wtp"],
            "associated_feature": [None],
        })
        result = analyze_cross_category_monetization(wtp_df)
        assert result["astrology_to_ancestry_wtp"]["count"] >= 1

    def test_negative_wtp_excluded_from_crossover(self):
        wtp_df = pd.DataFrame({
            "category": ["ancestry"],
            "wtp_signal_text": ["premium predictions are a scam"],
            "wtp_classification": ["negative_wtp"],
            "associated_feature": [None],
        })
        result = analyze_cross_category_monetization(wtp_df)
        assert result["ancestry_to_astrology_wtp"]["count"] == 0

    def test_empty_dataframe(self):
        wtp_df = pd.DataFrame(columns=[
            "category", "wtp_signal_text", "wtp_classification", "associated_feature"
        ])
        result = analyze_cross_category_monetization(wtp_df)
        assert result["ancestry_to_astrology_wtp"]["count"] == 0
        assert result["astrology_to_ancestry_wtp"]["count"] == 0

    def test_result_structure(self):
        wtp_df = pd.DataFrame(columns=[
            "category", "wtp_signal_text", "wtp_classification", "associated_feature"
        ])
        result = analyze_cross_category_monetization(wtp_df)
        assert "ancestry_to_astrology_wtp" in result
        assert "astrology_to_ancestry_wtp" in result
        assert "count" in result["ancestry_to_astrology_wtp"]
        assert "features" in result["ancestry_to_astrology_wtp"]


class TestTrackCategoryWtp:
    """Unit tests for _track_category_wtp — family tree vs astrology WTP tracking.

    Requirements 13.6: Separately track family tree WTP vs astrology WTP signals.
    """

    def test_family_tree_wtp_tracking(self):
        wtp_rows = [
            {
                "wtp_signal_text": "worth paying for premium tree features",
                "wtp_classification": "positive_wtp",
                "associated_feature": "family_tree",
            },
            {
                "wtp_signal_text": "too expensive for record access",
                "wtp_classification": "negative_wtp",
                "associated_feature": "historical_records",
            },
        ]
        result = _track_category_wtp(
            wtp_rows,
            ANCESTRY_MONETIZATION_KEYWORDS,
            ANCESTRY_FEATURE_KEYWORDS,
        )
        assert result["total_signals"] >= 1
        assert result["positive"] >= 0
        assert result["negative"] >= 0
        assert isinstance(result["top_features"], list)

    def test_astrology_wtp_tracking(self):
        wtp_rows = [
            {
                "wtp_signal_text": "worth paying for premium predictions",
                "wtp_classification": "positive_wtp",
                "associated_feature": "horoscope",
            },
            {
                "wtp_signal_text": "consultation fee is too expensive",
                "wtp_classification": "negative_wtp",
                "associated_feature": None,
            },
        ]
        result = _track_category_wtp(
            wtp_rows,
            ASTROLOGY_MONETIZATION_KEYWORDS,
            ASTROLOGY_FEATURE_KEYWORDS,
        )
        assert result["total_signals"] >= 1
        assert isinstance(result["top_features"], list)

    def test_empty_rows(self):
        result = _track_category_wtp(
            [],
            ANCESTRY_MONETIZATION_KEYWORDS,
            ANCESTRY_FEATURE_KEYWORDS,
        )
        assert result["total_signals"] == 0
        assert result["positive"] == 0
        assert result["negative"] == 0
        assert result["top_features"] == []

    def test_irrelevant_signals_excluded(self):
        wtp_rows = [
            {
                "wtp_signal_text": "nice app with good design",
                "wtp_classification": "positive_wtp",
                "associated_feature": None,
            },
        ]
        result = _track_category_wtp(
            wtp_rows,
            ANCESTRY_MONETIZATION_KEYWORDS,
            ANCESTRY_FEATURE_KEYWORDS,
        )
        assert result["total_signals"] == 0
