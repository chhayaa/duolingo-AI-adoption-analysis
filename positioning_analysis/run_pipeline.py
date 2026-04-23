"""
Pipeline orchestrator for the Positioning Analysis system.

Runs all analysis stages in order (or individual stages via CLI flags):
    scrape → clean → sentiment → wtp → overlap → report

Usage:
    python -m positioning_analysis.run_pipeline                # run all stages
    python -m positioning_analysis.run_pipeline --stage scrape # run one stage
    python -m positioning_analysis.run_pipeline --stage clean --stage sentiment
"""

import argparse
import importlib
import logging
import os
import time
import traceback

from positioning_analysis.config import APP_REGISTRY, DATA_DIR, OUTPUT_DIR

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ordered stage definitions
# ---------------------------------------------------------------------------
STAGE_ORDER = ["scrape", "clean", "sentiment", "wtp", "overlap", "report"]

# Maps stage name → dict with input files required and output files produced
STAGE_META = {
    "scrape": {
        "inputs": [],
        "outputs": [os.path.join(DATA_DIR, "raw_reviews.csv")],
    },
    "clean": {
        "inputs": [os.path.join(DATA_DIR, "raw_reviews.csv")],
        "outputs": [
            os.path.join(DATA_DIR, "cleaned_reviews.csv"),
            os.path.join(DATA_DIR, "cleaning_summary.json"),
        ],
    },
    "sentiment": {
        "inputs": [os.path.join(DATA_DIR, "cleaned_reviews.csv")],
        "outputs": [
            os.path.join(DATA_DIR, "sentiment_results.csv"),
            os.path.join(DATA_DIR, "sentiment_summary.json"),
        ],
    },
    "wtp": {
        "inputs": [os.path.join(DATA_DIR, "cleaned_reviews.csv")],
        "outputs": [
            os.path.join(DATA_DIR, "wtp_results.csv"),
            os.path.join(DATA_DIR, "wtp_summary.json"),
        ],
    },
    "overlap": {
        "inputs": [os.path.join(DATA_DIR, "cleaned_reviews.csv")],
        "outputs": [
            os.path.join(DATA_DIR, "overlap_results.csv"),
            os.path.join(DATA_DIR, "overlap_summary.json"),
        ],
    },
    "report": {
        "inputs": [],  # report handles missing files gracefully via load_all_data
        "outputs": [
            os.path.join(DATA_DIR, "competitive_landscape.json"),
            os.path.join(OUTPUT_DIR, "positioning_report.html"),
        ],
    },
}


# ---------------------------------------------------------------------------
# Stage execution helpers
# ---------------------------------------------------------------------------

def _check_inputs(stage_name: str) -> list[str]:
    """Return list of missing input files for *stage_name*."""
    meta = STAGE_META.get(stage_name, {})
    missing = [p for p in meta.get("inputs", []) if not os.path.exists(p)]
    return missing


def _run_scrape() -> None:
    mod = importlib.import_module("positioning_analysis.01_scrape_reviews")
    mod.scrape_all(APP_REGISTRY)


def _run_clean() -> None:
    mod = importlib.import_module("positioning_analysis.02_clean_data")
    mod.clean_reviews(
        os.path.join(DATA_DIR, "raw_reviews.csv"),
        os.path.join(DATA_DIR, "cleaned_reviews.csv"),
    )


def _run_sentiment() -> None:
    mod = importlib.import_module("positioning_analysis.03_sentiment_analysis")
    mod.analyze_sentiment(
        os.path.join(DATA_DIR, "cleaned_reviews.csv"),
        os.path.join(DATA_DIR, "sentiment_results.csv"),
    )


def _run_wtp() -> None:
    mod = importlib.import_module("positioning_analysis.04_wtp_analysis")
    mod.analyze_wtp(
        os.path.join(DATA_DIR, "cleaned_reviews.csv"),
        os.path.join(DATA_DIR, "wtp_results.csv"),
    )


def _run_overlap() -> None:
    mod = importlib.import_module("positioning_analysis.05_demand_overlap")
    mod.analyze_overlap(
        os.path.join(DATA_DIR, "cleaned_reviews.csv"),
        os.path.join(DATA_DIR, "overlap_results.csv"),
        os.path.join(DATA_DIR, "overlap_summary.json"),
    )


def _run_report() -> None:
    mod = importlib.import_module("positioning_analysis.06_report")
    data = mod.load_all_data()
    landscape = mod.build_competitive_landscape(data)
    data["competitive_landscape"] = landscape
    mod.generate_html_report(data, os.path.join(OUTPUT_DIR, "positioning_report.html"))


_STAGE_RUNNERS = {
    "scrape": _run_scrape,
    "clean": _run_clean,
    "sentiment": _run_sentiment,
    "wtp": _run_wtp,
    "overlap": _run_overlap,
    "report": _run_report,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_stage(stage_name: str) -> bool:
    """Run a single pipeline stage by name.

    Returns ``True`` on success, ``False`` on failure or skip.
    """
    if stage_name not in _STAGE_RUNNERS:
        logger.error("Unknown stage: %s", stage_name)
        return False

    # Check for missing input files
    missing = _check_inputs(stage_name)
    if missing:
        for path in missing:
            logger.warning(
                "Stage '%s' skipped — missing input file: %s", stage_name, path
            )
        return False

    logger.info("=== Starting stage: %s ===", stage_name)
    start = time.time()

    try:
        _STAGE_RUNNERS[stage_name]()
    except Exception:
        logger.error(
            "Stage '%s' failed with unhandled exception:\n%s",
            stage_name,
            traceback.format_exc(),
        )
        return False

    duration = time.time() - start
    outputs = STAGE_META.get(stage_name, {}).get("outputs", [])
    existing_outputs = [p for p in outputs if os.path.exists(p)]

    logger.info(
        "=== Stage '%s' completed in %.1fs ===", stage_name, duration
    )
    for out_path in existing_outputs:
        logger.info("  Output: %s", out_path)

    return True


def run_pipeline(stages: list[str] | None = None) -> dict:
    """Run all (or specified) pipeline stages in canonical order.

    Args:
        stages: Optional list of stage names to run.  If ``None``, all
            stages are run in order.

    Returns:
        A summary dict with completed, skipped, total_reviews_processed,
        and output_files.
    """
    # Ensure directories exist
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if stages is None:
        stages_to_run = list(STAGE_ORDER)
    else:
        # Preserve canonical order for the requested stages
        stages_to_run = [s for s in STAGE_ORDER if s in stages]

    completed: list[str] = []
    skipped: list[str] = []

    pipeline_start = time.time()

    for stage_name in stages_to_run:
        success = run_stage(stage_name)
        if success:
            completed.append(stage_name)
        else:
            skipped.append(stage_name)

    pipeline_duration = time.time() - pipeline_start

    # Count total reviews processed (from cleaned CSV if available)
    total_reviews = 0
    cleaned_path = os.path.join(DATA_DIR, "cleaned_reviews.csv")
    if os.path.exists(cleaned_path):
        try:
            import pandas as pd
            total_reviews = len(pd.read_csv(cleaned_path))
        except Exception:
            pass

    # Collect output file locations
    output_files: list[str] = []
    for stage_name in completed:
        for out_path in STAGE_META.get(stage_name, {}).get("outputs", []):
            if os.path.exists(out_path):
                output_files.append(out_path)

    # Print final summary
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  Stages completed : {len(completed)} — {', '.join(completed) if completed else 'none'}")
    print(f"  Stages skipped   : {len(skipped)} — {', '.join(skipped) if skipped else 'none'}")
    print(f"  Total reviews    : {total_reviews}")
    print(f"  Total duration   : {pipeline_duration:.1f}s")
    print(f"  Output files     :")
    for fp in output_files:
        print(f"    {fp}")
    print("=" * 60)

    return {
        "completed": completed,
        "skipped": skipped,
        "total_reviews_processed": total_reviews,
        "output_files": output_files,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Positioning Analysis pipeline.",
    )
    parser.add_argument(
        "--stage",
        action="append",
        choices=STAGE_ORDER,
        help="Run a specific stage (can be repeated). Omit to run all stages.",
    )
    args = parser.parse_args()

    run_pipeline(stages=args.stage)


if __name__ == "__main__":
    main()
