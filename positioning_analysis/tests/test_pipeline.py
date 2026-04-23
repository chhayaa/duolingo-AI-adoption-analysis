"""
Unit tests for the pipeline orchestrator (run_pipeline.py).

Validates: Requirements 11.1, 11.3, 11.4, 11.6
"""

import argparse
from unittest.mock import patch, MagicMock

import pytest

from positioning_analysis.run_pipeline import (
    run_stage,
    run_pipeline,
    STAGE_ORDER,
    main,
)


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestCLIParsing:
    """Validates: Requirements 11.4"""

    def test_stage_flag_produces_correct_args(self):
        """--stage scrape should produce args.stage == ['scrape']."""
        with patch("argparse.ArgumentParser.parse_args",
                   return_value=argparse.Namespace(stage=["scrape"])):
            with patch("positioning_analysis.run_pipeline.run_pipeline") as mock_rp:
                main()
                mock_rp.assert_called_once_with(stages=["scrape"])

    def test_no_stage_flag_runs_all_stages(self):
        """Omitting --stage should pass stages=None (run all)."""
        with patch("argparse.ArgumentParser.parse_args",
                   return_value=argparse.Namespace(stage=None)):
            with patch("positioning_analysis.run_pipeline.run_pipeline") as mock_rp:
                main()
                mock_rp.assert_called_once_with(stages=None)

    def test_multiple_stage_flags(self):
        """--stage clean --stage sentiment should pass both."""
        with patch("argparse.ArgumentParser.parse_args",
                   return_value=argparse.Namespace(stage=["clean", "sentiment"])):
            with patch("positioning_analysis.run_pipeline.run_pipeline") as mock_rp:
                main()
                mock_rp.assert_called_once_with(stages=["clean", "sentiment"])


# ---------------------------------------------------------------------------
# run_stage
# ---------------------------------------------------------------------------

class TestRunStage:
    """Validates: Requirements 11.1, 11.3"""

    def test_unknown_stage_returns_false(self):
        assert run_stage("nonexistent_stage") is False

    def test_missing_input_files_returns_false(self):
        """Stage 'clean' requires raw_reviews.csv — should return False when missing."""
        with patch("positioning_analysis.run_pipeline._check_inputs",
                   return_value=["data/raw_reviews.csv"]):
            assert run_stage("clean") is False

    def test_successful_stage_returns_true(self):
        """When the runner succeeds and inputs exist, run_stage returns True."""
        with patch("positioning_analysis.run_pipeline._check_inputs", return_value=[]):
            with patch("positioning_analysis.run_pipeline._STAGE_RUNNERS",
                       {"scrape": MagicMock()}):
                assert run_stage("scrape") is True

    def test_stage_exception_returns_false(self):
        """If the stage runner raises, run_stage catches it and returns False."""
        def boom():
            raise RuntimeError("stage exploded")

        with patch("positioning_analysis.run_pipeline._check_inputs", return_value=[]):
            with patch("positioning_analysis.run_pipeline._STAGE_RUNNERS",
                       {"scrape": boom}):
                assert run_stage("scrape") is False


# ---------------------------------------------------------------------------
# run_pipeline
# ---------------------------------------------------------------------------

class TestRunPipeline:
    """Validates: Requirements 11.1, 11.3, 11.6"""

    @patch("positioning_analysis.run_pipeline.run_stage")
    @patch("os.makedirs")
    def test_runs_stages_in_correct_order(self, _makedirs, mock_run_stage):
        """Stages should execute in STAGE_ORDER when no filter is given."""
        mock_run_stage.return_value = True

        run_pipeline(stages=None)

        called_stages = [call.args[0] for call in mock_run_stage.call_args_list]
        assert called_stages == STAGE_ORDER

    @patch("positioning_analysis.run_pipeline.run_stage")
    @patch("os.makedirs")
    def test_returns_summary_dict_with_completed_and_skipped(self, _makedirs, mock_run_stage):
        """Summary dict must contain 'completed' and 'skipped' lists."""
        mock_run_stage.return_value = True

        summary = run_pipeline(stages=None)

        assert "completed" in summary
        assert "skipped" in summary
        assert isinstance(summary["completed"], list)
        assert isinstance(summary["skipped"], list)

    @patch("positioning_analysis.run_pipeline.run_stage")
    @patch("os.makedirs")
    def test_all_stages_succeed_populates_completed(self, _makedirs, mock_run_stage):
        mock_run_stage.return_value = True

        summary = run_pipeline(stages=None)

        assert summary["completed"] == STAGE_ORDER
        assert summary["skipped"] == []

    @patch("positioning_analysis.run_pipeline.run_stage")
    @patch("os.makedirs")
    def test_failed_stage_goes_to_skipped_and_continues(self, _makedirs, mock_run_stage):
        """A failed stage should appear in 'skipped', and subsequent stages still run."""
        def side_effect(name):
            return name != "sentiment"

        mock_run_stage.side_effect = side_effect

        summary = run_pipeline(stages=None)

        assert "sentiment" in summary["skipped"]
        assert "sentiment" not in summary["completed"]
        # All stages were still attempted
        assert len(summary["completed"]) + len(summary["skipped"]) == len(STAGE_ORDER)

    @patch("positioning_analysis.run_pipeline.run_stage")
    @patch("os.makedirs")
    def test_summary_contains_total_reviews_and_output_files(self, _makedirs, mock_run_stage):
        mock_run_stage.return_value = True

        summary = run_pipeline(stages=None)

        assert "total_reviews_processed" in summary
        assert "output_files" in summary
        assert isinstance(summary["total_reviews_processed"], int)
        assert isinstance(summary["output_files"], list)

    @patch("positioning_analysis.run_pipeline.run_stage")
    @patch("os.makedirs")
    def test_filtered_stages_preserve_canonical_order(self, _makedirs, mock_run_stage):
        """Passing stages=['report', 'clean'] should run them in canonical order."""
        mock_run_stage.return_value = True

        run_pipeline(stages=["report", "clean"])

        called_stages = [call.args[0] for call in mock_run_stage.call_args_list]
        assert called_stages == ["clean", "report"]
