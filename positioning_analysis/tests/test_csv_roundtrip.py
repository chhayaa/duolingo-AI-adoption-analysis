"""
Property-based test for CSV round-trip preservation.

Property 11 from the design document.
"""

import os
import tempfile

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies — generate DataFrames matching the cleaned review schema
# ---------------------------------------------------------------------------

# Non-empty text that avoids CSV-breaking edge cases but exercises variety
_review_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters="\x00",
    ),
    min_size=10,
    max_size=120,
)

_review_row = st.fixed_dictionaries({
    "review_id": st.uuids().map(str),
    "app_name": st.sampled_from([
        "Astrotalk", "Co-Star", "The Pattern", "Kundli Software",
        "AstroSage", "MyHeritage", "FamilySearch", "Ancestry",
    ]),
    "category": st.sampled_from(["astrology", "ancestry", "hybrid"]),
    "review_text": _review_text,
    "star_rating": st.integers(min_value=1, max_value=5),
    "review_date": st.dates().map(str),
    "review_source": st.sampled_from([
        "google_play", "apple_app_store", "trustpilot", "g2", "web",
    ]),
    "language": st.sampled_from(["en", "hi", "es", "unknown"]),
    "market_region": st.sampled_from(["india", "global", "both"]),
})

_review_dataframe = st.lists(_review_row, min_size=1, max_size=30).map(pd.DataFrame)

EXPECTED_COLUMNS = [
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


# ---------------------------------------------------------------------------
# Property 11: CSV round-trip preserves data
# Validates: Requirements 12.1, 12.3
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(df=_review_dataframe)
def test_csv_roundtrip_preserves_data(df):
    """Feature: positioning-analysis, Property 11: CSV round-trip preserves data

    **Validates: Requirements 12.1, 12.3**

    For any valid DataFrame produced by the pipeline, writing it to CSV with
    UTF-8 encoding and reading it back SHALL produce a DataFrame with identical
    column names, identical row count, and equivalent cell values (accounting
    for type coercion of None/NaN).
    """
    # Ensure string columns are consistently typed before writing
    str_cols = [
        "review_id", "app_name", "category", "review_text",
        "review_source", "language", "market_region", "review_date",
    ]
    df_write = df.copy()
    for col in str_cols:
        df_write[col] = df_write[col].astype(str)

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "roundtrip.csv")

        # Write with UTF-8 encoding
        df_write.to_csv(csv_path, index=False, encoding="utf-8")

        # Read back, keeping string columns as strings
        df_read = pd.read_csv(
            csv_path,
            encoding="utf-8",
            dtype={c: str for c in str_cols},
            keep_default_na=False,
        )

        # Identical column names
        assert list(df_read.columns) == list(df_write.columns), (
            f"Column mismatch: wrote {list(df_write.columns)}, read {list(df_read.columns)}"
        )

        # Identical row count
        assert len(df_read) == len(df_write), (
            f"Row count mismatch: wrote {len(df_write)}, read {len(df_read)}"
        )

        # Equivalent cell values (check_dtype=False to allow type coercion)
        pd.testing.assert_frame_equal(
            df_write.reset_index(drop=True),
            df_read.reset_index(drop=True),
            check_dtype=False,
        )
