"""
Integration tests for the Positioning Analysis pipeline.

Verifies that all pipeline stages (clean → sentiment → wtp → overlap → report)
connect end-to-end on a small synthetic dataset, and that the final HTML report
is valid and contains all expected sections.

Validates: Requirements 11.1, 10.1, 12.4
"""

import importlib
import json
import os
import tempfile

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Synthetic review data
# ---------------------------------------------------------------------------

SYNTHETIC_REVIEWS = [
    # Astrology apps — positive sentiment, WTP positive, overlap (family tree)
    {
        "review_text": "Astrotalk is amazing! The kundli matching feature is worth paying for. I wish it had a family tree feature too.",
        "star_rating": 5,
        "review_date": "2024-01-15",
        "reviewer_name": "A_abc123",
        "app_name": "Astrotalk",
        "category": "astrology",
        "review_source": "google_play",
        "source_url": None,
        "market_region": "india",
    },
    {
        "review_text": "Co-Star daily horoscope is good value for money. Would love ancestry and lineage insights.",
        "star_rating": 4,
        "review_date": "2024-02-10",
        "reviewer_name": "B_def456",
        "app_name": "Co-Star",
        "category": "astrology",
        "review_source": "google_play",
        "source_url": None,
        "market_region": "global",
    },
    {
        "review_text": "Too expensive for basic rashi predictions. The app is overpriced.",
        "star_rating": 2,
        "review_date": "2024-03-05",
        "reviewer_name": "C_ghi789",
        "app_name": "AstroSage",
        "category": "astrology",
        "review_source": "google_play",
        "source_url": None,
        "market_region": "india",
    },
    {
        "review_text": "Decent panchang and muhurat features. Nothing special but works fine.",
        "star_rating": 3,
        "review_date": "2024-01-20",
        "reviewer_name": "D_jkl012",
        "app_name": "Kundli Software",
        "category": "astrology",
        "review_source": "apple_app_store",
        "source_url": None,
        "market_region": "india",
    },
    {
        "review_text": "The Pattern app is great for zodiac compatibility. Would pay if they added family history.",
        "star_rating": 4,
        "review_date": "2024-04-12",
        "reviewer_name": "E_mno345",
        "app_name": "The Pattern",
        "category": "astrology",
        "review_source": "google_play",
        "source_url": None,
        "market_region": "global",
    },
    # Ancestry apps — mixed sentiment, WTP signals, overlap (horoscope/astrology)
    {
        "review_text": "Ancestry.com family tree builder is worth every penny. Wish it had horoscope features for family members.",
        "star_rating": 5,
        "review_date": "2024-02-20",
        "reviewer_name": "F_pqr678",
        "app_name": "Ancestry",
        "category": "ancestry",
        "review_source": "google_play",
        "source_url": None,
        "market_region": "global",
    },
    {
        "review_text": "MyHeritage DNA test is a scam. Too expensive and the family tree feature is limited.",
        "star_rating": 1,
        "review_date": "2024-03-15",
        "reviewer_name": "G_stu901",
        "app_name": "MyHeritage",
        "category": "ancestry",
        "review_source": "trustpilot",
        "source_url": "https://trustpilot.com/review/myheritage.com",
        "market_region": "global",
    },
    {
        "review_text": "FamilySearch is free and has great genealogy records. Would love kundli or birth chart integration.",
        "star_rating": 4,
        "review_date": "2024-01-25",
        "reviewer_name": "H_vwx234",
        "app_name": "FamilySearch",
        "category": "ancestry",
        "review_source": "google_play",
        "source_url": None,
        "market_region": "global",
    },
    {
        "review_text": "Good for gotra matching and vanshavali tracking. Subscribed to premium.",
        "star_rating": 4,
        "review_date": "2024-05-01",
        "reviewer_name": "I_yza567",
        "app_name": "Kuldevi - Family Tree",
        "category": "ancestry",
        "review_source": "google_play",
        "source_url": None,
        "market_region": "india",
    },
    {
        "review_text": "BanyanTree app is okay for photo storage but not worth the subscription price. Should be free.",
        "star_rating": 2,
        "review_date": "2024-04-18",
        "reviewer_name": "J_bcd890",
        "app_name": "BanyanTree - Family App",
        "category": "ancestry",
        "review_source": "google_play",
        "source_url": None,
        "market_region": "india",
    },
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def pipeline_dirs():
    """Create temp directories for DATA_DIR and OUTPUT_DIR, write synthetic
    raw_reviews.csv, and monkeypatch config paths so all modules use them."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = os.path.join(tmpdir, "data")
        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Write synthetic raw_reviews.csv
        raw_df = pd.DataFrame(SYNTHETIC_REVIEWS)
        raw_path = os.path.join(data_dir, "raw_reviews.csv")
        raw_df.to_csv(raw_path, index=False, encoding="utf-8")

        yield {
            "data_dir": data_dir,
            "output_dir": output_dir,
            "raw_path": raw_path,
            "tmpdir": tmpdir,
        }


def _patch_data_dir(monkeypatch, data_dir, output_dir):
    """Monkeypatch DATA_DIR and OUTPUT_DIR across all pipeline modules."""
    modules_to_patch = [
        "positioning_analysis.config",
        "positioning_analysis.02_clean_data",
        "positioning_analysis.03_sentiment_analysis",
        "positioning_analysis.04_wtp_analysis",
        "positioning_analysis.05_demand_overlap",
        "positioning_analysis.06_report",
        "positioning_analysis.run_pipeline",
    ]
    for mod_name in modules_to_patch:
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "DATA_DIR"):
                monkeypatch.setattr(mod, "DATA_DIR", data_dir)
            if hasattr(mod, "OUTPUT_DIR"):
                monkeypatch.setattr(mod, "OUTPUT_DIR", output_dir)
        except ImportError:
            pass

    # Build a fully patched copy of STAGE_META with temp dir paths
    from positioning_analysis.run_pipeline import STAGE_META

    def _remap(p):
        basename = os.path.basename(p)
        parent = os.path.basename(os.path.dirname(p))
        if parent == "data":
            return os.path.join(data_dir, basename)
        if parent == "output":
            return os.path.join(output_dir, basename)
        return p

    patched_meta = {}
    for stage_name, meta in STAGE_META.items():
        patched_meta[stage_name] = {
            "inputs": [_remap(p) for p in meta.get("inputs", [])],
            "outputs": [_remap(p) for p in meta.get("outputs", [])],
        }

    monkeypatch.setattr(
        "positioning_analysis.run_pipeline.STAGE_META",
        patched_meta,
    )


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestFullPipelineDryRun:
    """Test full pipeline dry run on synthetic data (skip scrape).

    Validates: Requirements 11.1, 10.1, 12.4
    """

    def test_pipeline_stages_connect(self, pipeline_dirs, monkeypatch):
        """Run clean → sentiment → wtp → overlap → report on synthetic data
        and verify each stage produces expected output files."""
        data_dir = pipeline_dirs["data_dir"]
        output_dir = pipeline_dirs["output_dir"]

        _patch_data_dir(monkeypatch, data_dir, output_dir)

        from positioning_analysis.run_pipeline import run_pipeline

        # Run all stages except scrape (we already have raw_reviews.csv)
        result = run_pipeline(stages=["clean", "sentiment", "wtp", "overlap", "report"])

        # Verify stages completed
        assert "clean" in result["completed"], "clean stage should complete"
        assert "sentiment" in result["completed"], "sentiment stage should complete"
        assert "wtp" in result["completed"], "wtp stage should complete"
        assert "overlap" in result["completed"], "overlap stage should complete"
        assert "report" in result["completed"], "report stage should complete"

        # Verify expected output files exist
        expected_data_files = [
            "cleaned_reviews.csv",
            "cleaning_summary.json",
            "sentiment_results.csv",
            "sentiment_summary.json",
            "wtp_results.csv",
            "wtp_summary.json",
            "overlap_results.csv",
            "overlap_summary.json",
            "competitive_landscape.json",
        ]
        for fname in expected_data_files:
            fpath = os.path.join(data_dir, fname)
            assert os.path.exists(fpath), f"Expected data file missing: {fname}"

        report_path = os.path.join(output_dir, "positioning_report.html")
        assert os.path.exists(report_path), "HTML report should be generated"

    def test_cleaned_reviews_valid(self, pipeline_dirs, monkeypatch):
        """Verify cleaned_reviews.csv has expected columns and rows."""
        data_dir = pipeline_dirs["data_dir"]
        output_dir = pipeline_dirs["output_dir"]
        _patch_data_dir(monkeypatch, data_dir, output_dir)

        from positioning_analysis.run_pipeline import run_pipeline
        run_pipeline(stages=["clean"])

        cleaned_path = os.path.join(data_dir, "cleaned_reviews.csv")
        df = pd.read_csv(cleaned_path)

        expected_cols = {
            "review_id", "app_name", "category", "review_text",
            "star_rating", "review_date", "review_source",
            "language", "market_region",
        }
        assert expected_cols.issubset(set(df.columns))
        assert len(df) > 0, "Should have cleaned reviews"
        assert len(df) <= len(SYNTHETIC_REVIEWS), "Should not have more rows than input"

    def test_cleaning_summary_valid(self, pipeline_dirs, monkeypatch):
        """Verify cleaning_summary.json has expected keys."""
        data_dir = pipeline_dirs["data_dir"]
        output_dir = pipeline_dirs["output_dir"]
        _patch_data_dir(monkeypatch, data_dir, output_dir)

        from positioning_analysis.run_pipeline import run_pipeline
        run_pipeline(stages=["clean"])

        summary_path = os.path.join(data_dir, "cleaning_summary.json")
        with open(summary_path) as f:
            summary = json.load(f)

        assert "total_collected" in summary
        assert "duplicates_removed" in summary
        assert "short_reviews_discarded" in summary
        assert "final_count" in summary
        assert summary["total_collected"] == len(SYNTHETIC_REVIEWS)


class TestReportHTMLValidity:
    """Test that the generated HTML report is valid and contains all sections.

    Validates: Requirements 10.1, 12.4
    """

    def test_report_is_valid_html(self, pipeline_dirs, monkeypatch):
        """Verify the HTML report starts with DOCTYPE and has html/head/body tags."""
        data_dir = pipeline_dirs["data_dir"]
        output_dir = pipeline_dirs["output_dir"]
        _patch_data_dir(monkeypatch, data_dir, output_dir)

        from positioning_analysis.run_pipeline import run_pipeline
        run_pipeline(stages=["clean", "sentiment", "wtp", "overlap", "report"])

        report_path = os.path.join(output_dir, "positioning_report.html")
        with open(report_path, encoding="utf-8") as f:
            html = f.read()

        assert html.strip().startswith("<!DOCTYPE html>"), "Report should start with DOCTYPE"
        assert "<html" in html, "Report should contain <html> tag"
        assert "<head>" in html, "Report should contain <head> tag"
        assert "<body>" in html, "Report should contain <body> tag"
        assert "</html>" in html, "Report should contain closing </html> tag"

    def test_report_contains_all_sections(self, pipeline_dirs, monkeypatch):
        """Verify the HTML report contains all expected section headings."""
        data_dir = pipeline_dirs["data_dir"]
        output_dir = pipeline_dirs["output_dir"]
        _patch_data_dir(monkeypatch, data_dir, output_dir)

        from positioning_analysis.run_pipeline import run_pipeline
        run_pipeline(stages=["clean", "sentiment", "wtp", "overlap", "report"])

        report_path = os.path.join(output_dir, "positioning_report.html")
        with open(report_path, encoding="utf-8") as f:
            html = f.read()

        expected_sections = [
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
        for section in expected_sections:
            assert section in html, f"Report should contain section: {section}"

    def test_report_contains_plotly_cdn(self, pipeline_dirs, monkeypatch):
        """Verify the HTML report includes the Plotly CDN script tag."""
        data_dir = pipeline_dirs["data_dir"]
        output_dir = pipeline_dirs["output_dir"]
        _patch_data_dir(monkeypatch, data_dir, output_dir)

        from positioning_analysis.run_pipeline import run_pipeline
        run_pipeline(stages=["clean", "sentiment", "wtp", "overlap", "report"])

        report_path = os.path.join(output_dir, "positioning_report.html")
        with open(report_path, encoding="utf-8") as f:
            html = f.read()

        assert "plotly" in html.lower(), "Report should reference Plotly"

    def test_report_self_contained_styles(self, pipeline_dirs, monkeypatch):
        """Verify the HTML report has embedded styles."""
        data_dir = pipeline_dirs["data_dir"]
        output_dir = pipeline_dirs["output_dir"]
        _patch_data_dir(monkeypatch, data_dir, output_dir)

        from positioning_analysis.run_pipeline import run_pipeline
        run_pipeline(stages=["clean", "sentiment", "wtp", "overlap", "report"])

        report_path = os.path.join(output_dir, "positioning_report.html")
        with open(report_path, encoding="utf-8") as f:
            html = f.read()

        assert "<style>" in html, "Report should have embedded styles"
