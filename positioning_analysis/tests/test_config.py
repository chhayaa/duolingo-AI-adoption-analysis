"""
Property-based tests for the positioning_analysis config module.
"""

from hypothesis import given, settings
from hypothesis.strategies import sampled_from

from positioning_analysis.config import APP_REGISTRY

VALID_CATEGORIES = {"astrology", "ancestry", "hybrid"}
VALID_MARKET_REGIONS = {"india", "global", "both"}


@settings(max_examples=100)
@given(entry=sampled_from(APP_REGISTRY))
def test_app_registry_entries_have_complete_structure(entry):
    """Feature: positioning-analysis, Property 1: App registry entries have complete structure

    Validates: Requirements 1.4
    """
    # name is a non-empty string
    assert isinstance(entry["name"], str) and len(entry["name"]) > 0

    # category is one of the allowed values
    assert entry["category"] in VALID_CATEGORIES

    # google_play_id is a non-empty string
    assert isinstance(entry["google_play_id"], str) and len(entry["google_play_id"]) > 0

    # apple_app_id is a non-empty string
    assert isinstance(entry["apple_app_id"], str) and len(entry["apple_app_id"]) > 0

    # web_sources is a list
    assert isinstance(entry["web_sources"], list)

    # market_region is one of the allowed values
    assert entry["market_region"] in VALID_MARKET_REGIONS

# ---------------------------------------------------------------------------
# Unit tests for config module
# Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
# ---------------------------------------------------------------------------

from positioning_analysis.config import (
    ANCESTRY_FEATURE_KEYWORDS,
    ANCESTRY_MONETIZATION_KEYWORDS,
    APPLE_STORE_COUNTRIES,
    ASTROLOGY_FEATURE_KEYWORDS,
    ASTROLOGY_MONETIZATION_KEYWORDS,
    DATA_DIR,
    HINGLISH_SENTIMENT_DICT,
    MONETIZATION_MODEL_PATTERNS,
    OUTPUT_DIR,
    OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS,
    OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS,
    REQUEST_DELAY,
    WTP_CONDITIONAL_PATTERNS,
    WTP_NEGATIVE_PATTERNS,
    WTP_POSITIVE_PATTERNS,
)


class TestAppRegistryCounts:
    """Validates: Requirements 1.1, 1.2, 1.5"""

    def test_at_least_10_astrology_apps(self):
        astrology = [e for e in APP_REGISTRY if e["category"] == "astrology"]
        assert len(astrology) >= 10

    def test_at_least_6_ancestry_apps(self):
        ancestry = [e for e in APP_REGISTRY if e["category"] == "ancestry"]
        assert len(ancestry) >= 6


class TestAppRegistryFields:
    """Validates: Requirements 1.4"""

    def test_all_entries_have_required_keys(self):
        required = {"name", "category", "google_play_id", "apple_app_id", "web_sources", "market_region"}
        for entry in APP_REGISTRY:
            assert required.issubset(entry.keys()), f"Missing keys in {entry.get('name', '?')}"

    def test_names_are_nonempty_strings(self):
        for entry in APP_REGISTRY:
            assert isinstance(entry["name"], str) and entry["name"].strip()

    def test_categories_are_valid(self):
        for entry in APP_REGISTRY:
            assert entry["category"] in VALID_CATEGORIES

    def test_google_play_ids_are_nonempty_strings(self):
        for entry in APP_REGISTRY:
            assert isinstance(entry["google_play_id"], str) and entry["google_play_id"].strip()

    def test_apple_app_ids_are_nonempty_strings(self):
        for entry in APP_REGISTRY:
            assert isinstance(entry["apple_app_id"], str) and entry["apple_app_id"].strip()

    def test_web_sources_are_lists(self):
        for entry in APP_REGISTRY:
            assert isinstance(entry["web_sources"], list)

    def test_market_regions_are_valid(self):
        for entry in APP_REGISTRY:
            assert entry["market_region"] in VALID_MARKET_REGIONS


class TestKeywordDictionaries:
    """Validates: Requirements 1.1, 1.2, 1.3"""

    def test_astrology_feature_keywords_non_empty(self):
        assert len(ASTROLOGY_FEATURE_KEYWORDS) > 0
        for key, values in ASTROLOGY_FEATURE_KEYWORDS.items():
            assert isinstance(values, list) and len(values) > 0, f"Empty list for {key}"

    def test_ancestry_feature_keywords_non_empty(self):
        assert len(ANCESTRY_FEATURE_KEYWORDS) > 0
        for key, values in ANCESTRY_FEATURE_KEYWORDS.items():
            assert isinstance(values, list) and len(values) > 0, f"Empty list for {key}"

    def test_wtp_positive_patterns_non_empty(self):
        assert len(WTP_POSITIVE_PATTERNS) > 0

    def test_wtp_negative_patterns_non_empty(self):
        assert len(WTP_NEGATIVE_PATTERNS) > 0

    def test_wtp_conditional_patterns_non_empty(self):
        assert len(WTP_CONDITIONAL_PATTERNS) > 0

    def test_astrology_monetization_keywords_non_empty(self):
        assert len(ASTROLOGY_MONETIZATION_KEYWORDS) > 0

    def test_ancestry_monetization_keywords_non_empty(self):
        assert len(ANCESTRY_MONETIZATION_KEYWORDS) > 0

    def test_monetization_model_patterns_non_empty(self):
        assert len(MONETIZATION_MODEL_PATTERNS) > 0
        for model, patterns in MONETIZATION_MODEL_PATTERNS.items():
            assert isinstance(patterns, list) and len(patterns) > 0, f"Empty patterns for {model}"

    def test_overlap_astrology_to_ancestry_keywords_non_empty(self):
        assert len(OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS) > 0

    def test_overlap_ancestry_to_astrology_keywords_non_empty(self):
        assert len(OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS) > 0


class TestHinglishSentimentDict:
    """Validates: Requirements 1.3"""

    def test_hinglish_dict_non_empty(self):
        assert len(HINGLISH_SENTIMENT_DICT) > 0

    def test_all_values_in_valid_range(self):
        for word, score in HINGLISH_SENTIMENT_DICT.items():
            assert -1.0 <= score <= 1.0, f"Score {score} for '{word}' out of range [-1.0, 1.0]"

    def test_values_are_floats_or_ints(self):
        for word, score in HINGLISH_SENTIMENT_DICT.items():
            assert isinstance(score, (int, float)), f"Non-numeric score for '{word}'"


class TestSharedConstants:
    """Validates: Requirements 1.5"""

    def test_apple_store_countries_has_minimum_entries(self):
        assert len(APPLE_STORE_COUNTRIES) >= 6

    def test_apple_store_countries_includes_required(self):
        required = {"in", "us", "gb", "au", "ca", "sg"}
        assert required.issubset(set(APPLE_STORE_COUNTRIES))

    def test_request_delay_is_positive(self):
        assert isinstance(REQUEST_DELAY, (int, float)) and REQUEST_DELAY > 0

    def test_data_dir_is_string(self):
        assert isinstance(DATA_DIR, str) and len(DATA_DIR) > 0

    def test_output_dir_is_string(self):
        assert isinstance(OUTPUT_DIR, str) and len(OUTPUT_DIR) > 0
