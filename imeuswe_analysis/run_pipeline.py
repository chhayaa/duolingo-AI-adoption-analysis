"""
Master script to run the full analysis pipeline.
Usage: python run_pipeline.py
"""

import subprocess
import sys

STEPS = [
    ("01_scrape_reviews.py", "Scraping Google Play Store reviews for competitor apps"),
    ("02_clean_data.py", "Cleaning and preprocessing data"),
    ("03_sentiment_analysis.py", "Running sentiment analysis"),
    ("04_wtp_analysis.py", "Computing Willingness-to-Pay scores"),
    ("05_visualize.py", "Generating visualizations and report"),
]


def main():
    print("=" * 60)
    print("iMeUsWe AI Astrology Chatbot — Full Analysis Pipeline")
    print("=" * 60)

    for script, description in STEPS:
        print(f"\n{'='*60}")
        print(f"STEP: {description}")
        print(f"Running: {script}")
        print("=" * 60)

        result = subprocess.run(
            [sys.executable, script],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"\nERROR: {script} failed with return code {result.returncode}")
            print("Fix the issue and re-run the pipeline.")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE!")
    print("Check output/analysis_report.png for the final report.")
    print("=" * 60)


if __name__ == "__main__":
    main()
