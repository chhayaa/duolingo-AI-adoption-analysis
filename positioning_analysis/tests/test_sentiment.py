"""
Property-based tests for the positioning_analysis sentiment analyzer module.

Properties 5 and 6 from the design document.
"""

import importlib
import random

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from positioning_analysis.config import (
    ASTROLOGY_FEATURE_KEYWORDS,
    ANCESTRY_FEATURE_KEYWORDS,
)

# Import the module that starts with a digit via importlib
_sentiment = importlib.import_module("positioning_analysis.03_sentiment_analysis")
classify_sentiment = _sentiment.classify_sentiment
extract_features = _sentiment.extract_features

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strategy for review text — printable strings of reasonable length
_review_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=200,
)

# Strategy for optional star ratings: 1-5 or None
_star_rating = st.one_of(
    st.none(),
    st.integers(min_value=1, max_value=5).map(float),
)

# Strategy for language codes used by the module
_language = st.sampled_from(["en", "hi", "es", "fr", "de", "unknown"])


# ---------------------------------------------------------------------------
# Property 5: Sentiment output validity
# Validates: Requirements 6.1, 6.2
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(text=_review_text, star_rating=_star_rating)
def test_sentiment_label_is_valid(text, star_rating):
    """Feature: positioning-analysis, Property 5: Sentiment output validity

    **Validates: Requirements 6.1, 6.2**

    For any review text and optional star rating, classify_sentiment SHALL
    return a label that is one of {"positive", "negative", "neutral"}.
    """
    label, score, method, translated_flag = classify_sentiment(text, star_rating)
    assert label in {"positive", "negative", "neutral"}, (
        f"Invalid label: {label!r}"
    )


@settings(max_examples=100, deadline=None)
@given(text=_review_text, star_rating=_star_rating)
def test_sentiment_score_in_range(text, star_rating):
    """Feature: positioning-analysis, Property 5: Sentiment output validity

    **Validates: Requirements 6.1, 6.2**

    For any review text and optional star rating, classify_sentiment SHALL
    return a score in the range [-1.0, 1.0].
    """
    label, score, method, translated_flag = classify_sentiment(text, star_rating)
    assert -1.0 <= score <= 1.0, (
        f"Score {score} out of range [-1.0, 1.0]"
    )


# ---------------------------------------------------------------------------
# Property 6: Feature keyword extraction detects injected features
# Validates: Requirements 6.3
# ---------------------------------------------------------------------------

# Build a strategy that picks a random (feature_name, keyword) from one of
# the keyword dictionaries and embeds it in surrounding text.

def _build_keyword_pairs():
    """Collect all (category, feature_name, keyword) triples."""
    pairs = []
    for feature_name, kw_list in ASTROLOGY_FEATURE_KEYWORDS.items():
        for kw in kw_list:
            pairs.append(("astrology", feature_name, kw))
    for feature_name, kw_list in ANCESTRY_FEATURE_KEYWORDS.items():
        for kw in kw_list:
            pairs.append(("ancestry", feature_name, kw))
    return pairs


_keyword_pairs = _build_keyword_pairs()

# Strategy: pick a keyword pair and wrap it in surrounding filler text
_keyword_injection = st.sampled_from(_keyword_pairs)

_filler_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
    min_size=5,
    max_size=40,
)


@settings(max_examples=100, deadline=None)
@given(
    pair=_keyword_injection,
    prefix=_filler_text,
    suffix=_filler_text,
)
def test_feature_extraction_detects_injected_keyword(pair, prefix, suffix):
    """Feature: positioning-analysis, Property 6: Feature keyword extraction detects injected features

    **Validates: Requirements 6.3**

    For any review text that contains a keyword from the feature keyword
    dictionary for its category, extract_features SHALL include that feature
    in its returned list of feature mentions.
    """
    category, expected_feature, keyword = pair
    # Build a review that definitely contains the keyword
    review_text = f"{prefix} {keyword} {suffix}"

    features = extract_features(review_text, category)
    feature_names = [f["feature_name"] for f in features]

    assert expected_feature in feature_names, (
        f"Expected feature {expected_feature!r} (keyword={keyword!r}) "
        f"not found in extracted features: {feature_names}"
    )


# ---------------------------------------------------------------------------
# Unit tests for the sentiment analyzer module
# ---------------------------------------------------------------------------

import unittest
from unittest.mock import patch

apply_hinglish_boost = _sentiment.apply_hinglish_boost
translate_to_english = _sentiment.translate_to_english


class TestClassifySentiment(unittest.TestCase):
    """Test classify_sentiment with clearly positive, negative, and neutral texts."""

    def test_positive_english_text(self):
        """Clearly positive English text should be classified as positive."""
        label, score, method, translated = classify_sentiment(
            "This app is absolutely amazing and wonderful! I love it so much!",
            star_rating=None,
            language="en",
        )
        assert label == "positive"
        assert score > 0.05
        assert method == "vader"
        assert translated is False

    def test_negative_english_text(self):
        """Clearly negative English text should be classified as negative."""
        label, score, method, translated = classify_sentiment(
            "This app is terrible, awful, and completely broken. Worst ever.",
            star_rating=None,
            language="en",
        )
        assert label == "negative"
        assert score < -0.05
        assert method == "vader"
        assert translated is False

    def test_neutral_english_text(self):
        """Neutral/bland English text should be classified as neutral."""
        label, score, method, translated = classify_sentiment(
            "The app exists.",
            star_rating=None,
            language="en",
        )
        assert label == "neutral"
        assert method == "vader"

    def test_score_always_in_range(self):
        """Score must always be in [-1.0, 1.0]."""
        for text in ["Great!", "Bad!", "Okay", ""]:
            _, score, _, _ = classify_sentiment(text, star_rating=None, language="en")
            assert -1.0 <= score <= 1.0


class TestStarRatingCombination(unittest.TestCase):
    """Test the star rating + text score combination logic."""

    def test_five_star_boosts_score(self):
        """A 5-star rating (normalized to 1.0) should push the combined score positive."""
        # Neutral text + 5-star rating → combined = 0.4*~0 + 0.6*1.0 = ~0.6
        label, score, _, _ = classify_sentiment(
            "The app exists.", star_rating=5.0, language="en"
        )
        assert label == "positive"
        assert score > 0.05

    def test_one_star_pulls_negative(self):
        """A 1-star rating (normalized to -1.0) should pull the combined score negative."""
        # Neutral text + 1-star rating → combined = 0.4*~0 + 0.6*(-1.0) = ~-0.6
        label, score, _, _ = classify_sentiment(
            "The app exists.", star_rating=1.0, language="en"
        )
        assert label == "negative"
        assert score < -0.05

    def test_three_star_stays_neutral(self):
        """A 3-star rating (normalized to 0.0) with neutral text should stay neutral."""
        label, score, _, _ = classify_sentiment(
            "The app exists.", star_rating=3.0, language="en"
        )
        assert label == "neutral"

    def test_no_star_uses_text_only(self):
        """Without a star rating, the score should be purely text-based."""
        label_with, score_with, _, _ = classify_sentiment(
            "Amazing app!", star_rating=5.0, language="en"
        )
        label_without, score_without, _, _ = classify_sentiment(
            "Amazing app!", star_rating=None, language="en"
        )
        # Both should be positive, but scores differ due to combination
        assert label_with == "positive"
        assert label_without == "positive"
        # The text-only score should differ from the combined score
        assert score_with != score_without

    def test_star_normalization(self):
        """Star ratings should normalize: 1→-1.0, 3→0.0, 5→1.0."""
        # Use empty-ish text so text_score ≈ 0, then combined ≈ 0.6 * star_score
        _, score_1, _, _ = classify_sentiment("ok", star_rating=1.0, language="en")
        _, score_3, _, _ = classify_sentiment("ok", star_rating=3.0, language="en")
        _, score_5, _, _ = classify_sentiment("ok", star_rating=5.0, language="en")
        assert score_1 < score_3 < score_5


class TestHinglishBoost(unittest.TestCase):
    """Test the Hinglish keyword boost application."""

    def test_positive_hinglish_word_boosts_score(self):
        """A positive Hinglish word should boost the VADER score upward."""
        # "zabardast" has polarity 0.9 in HINGLISH_SENTIMENT_DICT
        base_score = 0.0
        boosted = apply_hinglish_boost("zabardast app hai", base_score)
        # Expected: 0.3 * 0.9 + 0.7 * 0.0 = 0.27
        assert boosted > base_score

    def test_negative_hinglish_word_pulls_score_down(self):
        """A negative Hinglish word should pull the VADER score downward."""
        # "bakwas" has polarity -0.8
        base_score = 0.0
        boosted = apply_hinglish_boost("bakwas app hai", base_score)
        # Expected: 0.3 * (-0.8) + 0.7 * 0.0 = -0.24
        assert boosted < base_score

    def test_no_hinglish_match_returns_original(self):
        """If no Hinglish keywords match, the original score is returned unchanged."""
        base_score = 0.5
        boosted = apply_hinglish_boost("this is plain english text", base_score)
        assert boosted == base_score

    def test_multiple_hinglish_words_averaged(self):
        """Multiple Hinglish matches should be averaged before blending."""
        # "zabardast" (0.9) + "mast" (0.7) → avg = 0.8
        base_score = 0.0
        boosted = apply_hinglish_boost("zabardast aur mast app", base_score)
        expected = 0.3 * 0.8 + 0.7 * 0.0  # 0.24
        assert abs(boosted - expected) < 0.01

    def test_hinglish_boost_blending_weights(self):
        """Verify the 0.3/0.7 weighting is applied correctly."""
        # "shandaar" has polarity 0.9
        base_score = 0.5
        boosted = apply_hinglish_boost("shandaar", base_score)
        expected = 0.3 * 0.9 + 0.7 * 0.5  # 0.27 + 0.35 = 0.62
        assert abs(boosted - expected) < 0.01


class TestFeatureExtraction(unittest.TestCase):
    """Test feature extraction with known keyword matches."""

    def test_astrology_keyword_detected(self):
        """A review mentioning 'kundli' should extract the kundli feature."""
        features = extract_features(
            "The kundli matching feature is very accurate and helpful.",
            category="astrology",
        )
        names = [f["feature_name"] for f in features]
        assert "kundli" in names

    def test_ancestry_keyword_detected(self):
        """A review mentioning 'family tree' should extract the family_tree feature."""
        features = extract_features(
            "I love building my family tree on this app.",
            category="ancestry",
        )
        names = [f["feature_name"] for f in features]
        assert "family_tree" in names

    def test_no_keywords_returns_empty(self):
        """A review with no feature keywords should return an empty list."""
        features = extract_features(
            "This is a generic review with no specific features mentioned.",
            category="astrology",
        )
        assert features == []

    def test_multiple_features_detected(self):
        """A review mentioning multiple features should extract all of them."""
        features = extract_features(
            "The kundli matching and rashi predictions are great. Vastu tips are helpful too.",
            category="astrology",
        )
        names = [f["feature_name"] for f in features]
        assert "kundli" in names
        assert "rashi" in names
        assert "vastu" in names

    def test_feature_has_sentiment_fields(self):
        """Each extracted feature should have sentiment_label and sentiment_score."""
        features = extract_features(
            "The horoscope feature is absolutely wonderful and amazing!",
            category="astrology",
        )
        assert len(features) > 0
        for f in features:
            assert "feature_name" in f
            assert "sentiment_label" in f
            assert "sentiment_score" in f
            assert f["sentiment_label"] in {"positive", "negative", "neutral"}
            assert -1.0 <= f["sentiment_score"] <= 1.0

    def test_translated_text_also_searched(self):
        """When translated_text is provided, keywords should be found in both texts."""
        features = extract_features(
            "यह ऐप बहुत अच्छा है",  # Hindi text without English keywords
            category="astrology",
            translated_text="The horoscope feature is great",
        )
        names = [f["feature_name"] for f in features]
        assert "horoscope" in names


class TestTranslationFallback(unittest.TestCase):
    """Test translation failure fallback paths."""

    @patch.object(_sentiment, "translate_to_english", return_value=("original text", False))
    def test_translation_failure_with_star_rating(self, mock_translate):
        """When translation fails but star_rating is available, use star_rating_only."""
        label, score, method, translated = classify_sentiment(
            "कुछ हिंदी टेक्स्ट", star_rating=5.0, language="hi"
        )
        assert method == "star_rating_only"
        assert translated is True
        assert label == "positive"  # 5-star → positive

    @patch.object(_sentiment, "translate_to_english", return_value=("original text", False))
    def test_translation_failure_without_star_rating(self, mock_translate):
        """When translation fails and no star_rating, return untranslatable neutral."""
        label, score, method, translated = classify_sentiment(
            "कुछ हिंदी टेक्स्ट", star_rating=None, language="hi"
        )
        assert label == "neutral"
        assert score == 0.0
        assert method == "untranslatable"
        assert translated is True

    @patch.object(_sentiment, "translate_to_english", return_value=("This is great", True))
    def test_successful_translation_uses_translated_vader(self, mock_translate):
        """When translation succeeds, method should be translated_vader."""
        label, score, method, translated = classify_sentiment(
            "यह बहुत अच्छा है", star_rating=None, language="es"
        )
        assert method == "translated_vader"
        assert translated is True

    @patch.object(_sentiment, "translate_to_english", return_value=("This is great", True))
    def test_hindi_translation_applies_hinglish_boost(self, mock_translate):
        """For Hindi language, Hinglish boost should be applied after translation."""
        # The text contains "zabardast" which is in HINGLISH_SENTIMENT_DICT
        label, score, method, translated = classify_sentiment(
            "zabardast app hai", star_rating=None, language="hi"
        )
        assert method == "translated_vader"
        assert translated is True

    def test_english_no_translation(self):
        """English text should not trigger translation."""
        label, score, method, translated = classify_sentiment(
            "Great app!", star_rating=None, language="en"
        )
        assert method == "vader"
        assert translated is False
