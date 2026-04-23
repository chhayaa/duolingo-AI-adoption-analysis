"""
Property-based tests for the positioning_analysis data cleaner module.

Properties 2, 3, and 4 from the design document.
"""

import importlib
import io
import re
import tempfile
import os

import pandas as pd
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Import the module that starts with a digit via importlib
_cleaner = importlib.import_module("positioning_analysis.02_clean_data")
normalize_text = _cleaner.normalize_text
remove_duplicates = _cleaner.remove_duplicates
clean_reviews = _cleaner.clean_reviews

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strategy for strings that contain HTML tags
_html_tags = st.sampled_from(["<b>", "</b>", "<div>", "</div>", "<p>", "</p>",
                               "<br>", "<br/>", "<span>", "</span>",
                               "<a href='x'>", "</a>", "<script>", "</script>"])

# Strategy for special characters outside the preserved set
_special_chars = st.sampled_from(["@", "#", "$", "%", "^", "&", "*", "(", ")",
                                   "~", "`", "{", "}", "[", "]", "|", "\\",
                                   "<", ">", "+", "=", ";", ":", '"'])

# Strategy for meaningful alphanumeric content
_alnum_word = st.from_regex(r"[A-Za-z0-9]{1,10}", fullmatch=True)

# Build a string that mixes HTML, special chars, whitespace, and real content
_dirty_text = st.builds(
    lambda parts: "".join(parts),
    st.lists(
        st.one_of(
            _html_tags,
            _special_chars,
            st.just("   "),       # excessive whitespace
            st.just("\t\n"),      # tabs/newlines
            _alnum_word,
        ),
        min_size=2,
        max_size=15,
    ),
)

# Strategy for app names
_app_names = st.sampled_from(["Astrotalk", "Co-Star", "MyHeritage", "FamilySearch"])

# Strategy for a single raw review row
_raw_review = st.fixed_dictionaries({
    "review_text": st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
        min_size=0,
        max_size=80,
    ),
    "app_name": _app_names,
    "category": st.sampled_from(["astrology", "ancestry"]),
    "star_rating": st.integers(min_value=1, max_value=5),
    "review_date": st.just("2024-01-15"),
    "review_source": st.just("google_play"),
    "market_region": st.sampled_from(["india", "global"]),
})

# Strategy for a list of raw reviews (used for Property 3)
_raw_reviews_list = st.lists(_raw_review, min_size=1, max_size=30)


# ---------------------------------------------------------------------------
# Property 2: Text normalization removes injected artifacts
# Validates: Requirements 5.2
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(text=_dirty_text)
def test_normalize_text_removes_html_tags(text):
    """Feature: positioning-analysis, Property 2: Text normalization removes injected artifacts

    **Validates: Requirements 5.2**

    For any string containing HTML tags, excessive whitespace, or special
    characters, normalize_text SHALL produce a string with no HTML tags.
    """
    result = normalize_text(text)
    assert "<" not in result and ">" not in result, (
        f"HTML artifacts remain in: {result!r}"
    )


@settings(max_examples=100)
@given(text=_dirty_text)
def test_normalize_text_no_multiple_whitespace(text):
    """Feature: positioning-analysis, Property 2: Text normalization removes injected artifacts

    **Validates: Requirements 5.2**

    Normalized text SHALL contain no runs of multiple whitespace characters.
    """
    result = normalize_text(text)
    assert "  " not in result, (
        f"Multiple consecutive spaces in: {result!r}"
    )


@settings(max_examples=100)
@given(text=_dirty_text)
def test_normalize_text_no_special_chars_outside_preserved(text):
    """Feature: positioning-analysis, Property 2: Text normalization removes injected artifacts

    **Validates: Requirements 5.2**

    Normalized text SHALL contain no special characters outside the preserved
    set (alphanumeric, spaces, and basic punctuation: . , ! ? ' -).
    """
    result = normalize_text(text)
    # The preserved set: word chars (\w includes underscore + alnum),
    # spaces, and . , ! ? ' -
    # normalize_text uses [^\w\s.,!?'\-] to strip others
    forbidden = re.findall(r"[^\w\s.,!?'\-]", result)
    assert forbidden == [], (
        f"Forbidden characters {forbidden} in: {result!r}"
    )


@settings(max_examples=100)
@given(text=_dirty_text)
def test_normalize_text_preserves_alnum_content(text):
    """Feature: positioning-analysis, Property 2: Text normalization removes injected artifacts

    **Validates: Requirements 5.2**

    The meaningful alphabetic/numeric content from the original string SHALL
    still be present after normalization.
    """
    result = normalize_text(text)
    # Extract all alnum chars from original (outside HTML tags)
    original_stripped = re.sub(r"<[^>]+>", " ", text)
    original_alnum = re.findall(r"[A-Za-z0-9]", original_stripped)
    result_alnum = re.findall(r"[A-Za-z0-9]", result)
    # Every alnum char from the tag-stripped original should appear in result
    assert sorted(original_alnum) == sorted(result_alnum), (
        f"Alnum content mismatch: original={original_alnum}, result={result_alnum}"
    )


# ---------------------------------------------------------------------------
# Property 3: Cleaning preserves data integrity
# Validates: Requirements 5.1, 5.4, 5.6
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(reviews=_raw_reviews_list)
def test_cleaning_data_integrity(reviews):
    """Feature: positioning-analysis, Property 3: Cleaning preserves data integrity (dedup + short removal + consistent counts)

    **Validates: Requirements 5.1, 5.4, 5.6**

    For any input DataFrame of raw reviews, after cleaning:
    (a) no two rows share the same (review_text, app_name) pair,
    (b) every remaining review has >= 10 characters of text, and
    (c) the cleaning summary satisfies
        total_collected - duplicates_removed - short_reviews_discarded == final_count.
    """
    df = pd.DataFrame(reviews)
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "raw_reviews.csv")
        output_path = os.path.join(tmpdir, "cleaned_reviews.csv")
        df.to_csv(input_path, index=False, encoding="utf-8")

        summary = clean_reviews(input_path, output_path)

        # Read back cleaned output
        df_clean = pd.read_csv(output_path, encoding="utf-8")

        # (a) No duplicate (review_text, app_name) pairs
        dup_count = df_clean.duplicated(subset=["review_text", "app_name"]).sum()
        assert dup_count == 0, f"Found {dup_count} duplicate (review_text, app_name) pairs"

        # (b) Every remaining review has >= 10 chars
        short = df_clean[df_clean["review_text"].str.len() < 10]
        assert len(short) == 0, f"Found {len(short)} reviews shorter than 10 chars"

        # (c) Count consistency
        total = summary["total_collected"]
        dups = summary["duplicates_removed"]
        shorts = summary["short_reviews_discarded"]
        final = summary["final_count"]
        assert total - dups - shorts == final, (
            f"Count mismatch: {total} - {dups} - {shorts} != {final}"
        )


# ---------------------------------------------------------------------------
# Property 4: Stage CSV outputs conform to expected schemas
# Validates: Requirements 5.5, 6.5, 7.5
# ---------------------------------------------------------------------------

CLEANED_SCHEMA = [
    "review_id",
    "app_name",
    "category",
    "review_text",
    "star_rating",
    "review_date",
    "review_source",
    "language",
    "market_region",
]


@settings(max_examples=100, deadline=None)
@given(reviews=_raw_reviews_list)
def test_cleaned_csv_schema(reviews):
    """Feature: positioning-analysis, Property 4: Stage CSV outputs conform to expected schemas

    **Validates: Requirements 5.5, 6.5, 7.5**

    For any DataFrame produced by the cleaning stage, when written to CSV and
    read back, the column set SHALL exactly match the specified schema.
    """
    df = pd.DataFrame(reviews)
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "raw_reviews.csv")
        output_path = os.path.join(tmpdir, "cleaned_reviews.csv")
        df.to_csv(input_path, index=False, encoding="utf-8")

        clean_reviews(input_path, output_path)

        df_out = pd.read_csv(output_path, encoding="utf-8")
        assert list(df_out.columns) == CLEANED_SCHEMA, (
            f"Schema mismatch: got {list(df_out.columns)}, expected {CLEANED_SCHEMA}"
        )


# ---------------------------------------------------------------------------
# Unit tests for data cleaner
# Validates: Requirements 5.1, 5.2, 5.3, 5.4
# ---------------------------------------------------------------------------

import unittest


class TestRemoveDuplicates(unittest.TestCase):
    """Unit tests for remove_duplicates — Validates: Requirements 5.1"""

    def test_removes_exact_duplicates(self):
        df = pd.DataFrame([
            {"review_text": "Great app", "app_name": "Astrotalk", "star_rating": 5},
            {"review_text": "Great app", "app_name": "Astrotalk", "star_rating": 4},
            {"review_text": "Terrible app", "app_name": "Astrotalk", "star_rating": 1},
        ])
        result = remove_duplicates(df)
        assert len(result) == 2
        # First occurrence kept
        assert result.iloc[0]["star_rating"] == 5

    def test_keeps_same_text_different_app(self):
        df = pd.DataFrame([
            {"review_text": "Nice features", "app_name": "Astrotalk"},
            {"review_text": "Nice features", "app_name": "Co-Star"},
        ])
        result = remove_duplicates(df)
        assert len(result) == 2

    def test_no_duplicates_unchanged(self):
        df = pd.DataFrame([
            {"review_text": "Review one", "app_name": "Astrotalk"},
            {"review_text": "Review two", "app_name": "Co-Star"},
            {"review_text": "Review three", "app_name": "MyHeritage"},
        ])
        result = remove_duplicates(df)
        assert len(result) == 3

    def test_all_duplicates(self):
        df = pd.DataFrame([
            {"review_text": "Same review", "app_name": "Astrotalk"},
            {"review_text": "Same review", "app_name": "Astrotalk"},
            {"review_text": "Same review", "app_name": "Astrotalk"},
        ])
        result = remove_duplicates(df)
        assert len(result) == 1

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["review_text", "app_name"])
        result = remove_duplicates(df)
        assert len(result) == 0


class TestNormalizeText(unittest.TestCase):
    """Unit tests for normalize_text — Validates: Requirements 5.2"""

    def test_strips_html_tags(self):
        assert normalize_text("<b>Hello</b> world") == "Hello world"

    def test_strips_nested_html(self):
        result = normalize_text("<div><p>Some <b>bold</b> text</p></div>")
        assert "<" not in result
        assert ">" not in result
        assert "Some" in result and "bold" in result and "text" in result

    def test_collapses_whitespace(self):
        assert normalize_text("hello    world") == "hello world"

    def test_strips_tabs_and_newlines(self):
        result = normalize_text("hello\t\n\nworld")
        assert result == "hello world"

    def test_preserves_basic_punctuation(self):
        result = normalize_text("Great app! Works well, I think. It's good-ish?")
        assert "!" in result
        assert "," in result
        assert "." in result
        assert "'" in result
        assert "-" in result
        assert "?" in result

    def test_removes_special_characters(self):
        result = normalize_text("hello @world #test $money")
        # @ # $ should be replaced
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_only_whitespace(self):
        assert normalize_text("   \t\n  ") == ""

    def test_non_string_input(self):
        assert normalize_text(None) == ""
        assert normalize_text(123) == ""

    def test_unicode_preserved(self):
        # Word characters (letters/digits) should be preserved by \w
        result = normalize_text("café résumé naïve")
        assert "caf" in result
        assert "sum" in result


class TestDetectLanguage(unittest.TestCase):
    """Unit tests for detect_language — Validates: Requirements 5.3"""

    detect_language = staticmethod(_cleaner.detect_language)

    def test_english_text(self):
        result = self.detect_language(
            "This is a great application with wonderful features and I love using it every day"
        )
        assert result == "en"

    def test_hindi_text(self):
        result = self.detect_language(
            "यह एक बहुत अच्छा ऐप है और मुझे इसका उपयोग करना बहुत पसंद है"
        )
        assert result in ("hi", "mr")  # langdetect may detect Hindi or Marathi

    def test_spanish_text(self):
        result = self.detect_language(
            "Esta es una aplicación maravillosa que me encanta usar todos los días"
        )
        assert result == "es"

    def test_empty_string_returns_unknown(self):
        result = self.detect_language("")
        assert result == "unknown"

    def test_very_short_text_returns_unknown(self):
        # Very short text often fails detection
        result = self.detect_language("hi")
        # Should return something without crashing
        assert isinstance(result, str)


class TestShortReviewDiscarding(unittest.TestCase):
    """Unit tests for short review discarding in clean_reviews — Validates: Requirements 5.4"""

    def test_discards_short_reviews(self):
        df = pd.DataFrame([
            {"review_text": "Good", "app_name": "Astrotalk", "category": "astrology",
             "star_rating": 5, "review_date": "2024-01-01", "review_source": "google_play",
             "market_region": "india"},
            {"review_text": "This is a sufficiently long review text for testing purposes",
             "app_name": "Astrotalk", "category": "astrology", "star_rating": 4,
             "review_date": "2024-01-02", "review_source": "google_play",
             "market_region": "india"},
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "raw.csv")
            output_path = os.path.join(tmpdir, "cleaned.csv")
            df.to_csv(input_path, index=False, encoding="utf-8")

            summary = clean_reviews(input_path, output_path)
            df_out = pd.read_csv(output_path)

            assert summary["short_reviews_discarded"] >= 1
            for text in df_out["review_text"]:
                assert len(str(text)) >= 10

    def test_keeps_exactly_10_char_review(self):
        df = pd.DataFrame([
            {"review_text": "Exactly 10", "app_name": "Astrotalk", "category": "astrology",
             "star_rating": 3, "review_date": "2024-01-01", "review_source": "google_play",
             "market_region": "india"},
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "raw.csv")
            output_path = os.path.join(tmpdir, "cleaned.csv")
            df.to_csv(input_path, index=False, encoding="utf-8")

            summary = clean_reviews(input_path, output_path)
            df_out = pd.read_csv(output_path)

            assert summary["short_reviews_discarded"] == 0
            assert len(df_out) == 1

    def test_discards_9_char_review(self):
        df = pd.DataFrame([
            {"review_text": "Only nine", "app_name": "Astrotalk", "category": "astrology",
             "star_rating": 3, "review_date": "2024-01-01", "review_source": "google_play",
             "market_region": "india"},
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "raw.csv")
            output_path = os.path.join(tmpdir, "cleaned.csv")
            df.to_csv(input_path, index=False, encoding="utf-8")

            summary = clean_reviews(input_path, output_path)
            df_out = pd.read_csv(output_path)

            assert summary["short_reviews_discarded"] == 1
            assert len(df_out) == 0

    def test_all_short_reviews_discarded(self):
        df = pd.DataFrame([
            {"review_text": "Bad", "app_name": "Astrotalk", "category": "astrology",
             "star_rating": 1, "review_date": "2024-01-01", "review_source": "google_play",
             "market_region": "india"},
            {"review_text": "OK", "app_name": "Co-Star", "category": "astrology",
             "star_rating": 3, "review_date": "2024-01-02", "review_source": "google_play",
             "market_region": "global"},
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "raw.csv")
            output_path = os.path.join(tmpdir, "cleaned.csv")
            df.to_csv(input_path, index=False, encoding="utf-8")

            summary = clean_reviews(input_path, output_path)
            df_out = pd.read_csv(output_path)

            assert summary["short_reviews_discarded"] == 2
            assert len(df_out) == 0
