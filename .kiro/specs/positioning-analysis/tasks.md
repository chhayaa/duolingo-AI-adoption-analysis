# Implementation Plan: Positioning Analysis Pipeline

## Overview

Build a Python-based competitive analysis pipeline in a new `positioning_analysis/` directory that scrapes, cleans, analyzes, and reports on user reviews from astrology and ancestry apps. The pipeline replaces the existing `imeuswe_analysis/` codebase with a broader, multi-source system. Implementation proceeds module-by-module following the pipeline's data flow, with property-based tests and unit tests integrated alongside each module.

## Tasks

- [x] 1. Project setup and config module
  - [x] 1.1 Create project directory structure and requirements.txt
    - Create `positioning_analysis/` directory with `data/`, `output/`, and `tests/` subdirectories
    - Create `positioning_analysis/requirements.txt` with all dependencies: `google-play-scraper`, `beautifulsoup4`, `requests`, `pandas`, `nltk`, `vaderSentiment`, `googletrans==4.0.0-rc1`, `langdetect`, `plotly`, `pytest`, `hypothesis`
    - Create empty `__init__.py` files as needed
    - _Requirements: 11.5_

  - [x] 1.2 Implement config module (`config.py`)
    - Define `APP_REGISTRY` with at least 10 astrology apps (Astrotalk, Co-Star, The Pattern, Kundli Software, AstroSage, Jyotish, InstaAstro, Astroyogi, etc.) and at least 6 ancestry apps (Ancestry.com, MyHeritage, FamilySearch, FindMyPast, 23andMe, etc.) with all required fields: name, category, google_play_id, apple_app_id, web_sources, market_region
    - Define `ASTROLOGY_FEATURE_KEYWORDS` dict with all India-specific terms (kundli, mangal dosha, rashi, nakshatra, panchang, muhurat, vastu, numerology, janam_patri, dasha, gochar, remedies, pooja, gemstone, marriage_compatibility, career_prediction, health_prediction)
    - Define `ANCESTRY_FEATURE_KEYWORDS` dict with India-specific terms (gotra, vanshavali, kul_devta, family_puja, ancestral_village, caste_history, plus standard ancestry features)
    - Define `WTP_POSITIVE_PATTERNS`, `WTP_NEGATIVE_PATTERNS`, `WTP_CONDITIONAL_PATTERNS`
    - Define `ASTROLOGY_MONETIZATION_KEYWORDS`, `ANCESTRY_MONETIZATION_KEYWORDS`, `MONETIZATION_MODEL_PATTERNS`
    - Define `OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS`, `OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS`
    - Define `HINGLISH_SENTIMENT_DICT` with polarity scores for common Hindi/Hinglish sentiment words
    - Define `APPLE_STORE_COUNTRIES` list (at minimum: in, us, gb, au, ca, sg)
    - Define `REQUEST_DELAY`, `DATA_DIR`, `OUTPUT_DIR` constants
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.7, 13.1_

  - [x] 1.3 Write property test for config registry validation
    - **Property 1: App registry entries have complete structure**
    - **Validates: Requirements 1.4**

  - [x] 1.4 Write unit tests for config module
    - Verify registry has at least 10 astrology apps and 6 ancestry apps
    - Verify all entries have required fields with valid values
    - Verify all keyword dictionaries are non-empty
    - Verify HINGLISH_SENTIMENT_DICT values are in range [-1.0, 1.0]
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Checkpoint - Ensure config tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Review scraper module
  - [x] 3.1 Implement Google Play scraper (`01_scrape_reviews.py`)
    - Implement `scrape_google_play(app_entry)` using `google-play-scraper` library
    - Paginate using continuation tokens until exhausted (no count limit)
    - Extract review_text, star_rating, review_date, reviewer_name (anonymized as first initial + hash), app_name, review_source
    - Add configurable delay between batches using `REQUEST_DELAY`
    - Wrap in try/except, log errors with app name, return empty list on failure
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.2 Implement Apple App Store scraper
    - Implement `scrape_apple_app_store(app_entry)` using iTunes RSS JSON feed endpoint
    - Paginate through all available pages (up to 50 reviews per page)
    - Scrape across multiple country store codes from `APPLE_STORE_COUNTRIES` (minimum: IN, US, GB, AU, CA, SG)
    - Merge results with deduplication by (review_text, reviewer_name)
    - Extract review_text, star_rating, review_date, reviewer_name (anonymized), app_name, review_source
    - Add configurable delay, error handling per country store
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.3 Implement web source scrapers
    - Implement `scrape_web_source(app_entry, source)` dispatcher
    - Implement 7 source-specific parsers using `requests` + `BeautifulSoup4`:
      - Trustpilot: parse review cards from `/review/{company}`
      - G2: parse review sections from public product pages
      - Product Hunt: parse discussion/comment sections
      - Quora: parse answer content from public question pages
      - Blog: parse article body + comment sections
      - Twitter/X: best-effort, skip on 403/429 with no retry, attempt Nitter fallback
      - Google-indexed Reddit: Google search `site:reddit.com {app_name} review`, parse snippets + linked pages
    - Use standard HTTP requests with proper User-Agent headers, no API keys
    - Extract text content, score/rating (where available), date, source_url, source_type, app_name
    - Error handling per source: log and continue
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [x] 3.4 Implement `scrape_all` orchestrator function
    - Iterate over all apps in registry, scrape from all configured sources
    - Handle errors per-app, log failures, continue to next
    - Combine all results into a single DataFrame
    - Save to `data/raw_reviews.csv`
    - _Requirements: 2.1, 3.1, 4.1_

  - [x] 3.5 Write unit tests for scraper module
    - Test review dict schema compliance for each scraper function (mock responses)
    - Test error handling paths (network errors, empty responses, blocked requests)
    - Test reviewer name anonymization
    - Test Apple App Store multi-country deduplication
    - _Requirements: 2.3, 2.4, 3.3, 3.4, 4.4, 4.5_

- [x] 4. Data cleaner module
  - [x] 4.1 Implement data cleaner (`02_clean_data.py`)
    - Implement `remove_duplicates(df)` based on (review_text, app_name) pair
    - Implement `normalize_text(text)` to strip HTML tags, special characters, excessive whitespace while preserving meaningful content
    - Implement `detect_language(text)` using `langdetect` library, return ISO 639-1 code, handle exceptions by tagging as "unknown"
    - Implement `clean_reviews(input_path, output_path)` full pipeline: read raw CSV, deduplicate, normalize, detect language, discard reviews < 10 chars, assign UUIDs, output cleaned CSV with columns: review_id, app_name, category, review_text, star_rating, review_date, review_source, language, market_region
    - Produce cleaning summary JSON: total_collected, duplicates_removed, short_reviews_discarded, final_count, per_app_counts
    - Handle encoding with `utf-8, errors='replace'`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 4.2 Write property tests for data cleaner
    - **Property 2: Text normalization removes injected artifacts**
    - **Validates: Requirements 5.2**
    - **Property 3: Cleaning preserves data integrity (dedup + short removal + consistent counts)**
    - **Validates: Requirements 5.1, 5.4, 5.6**
    - **Property 4: Stage CSV outputs conform to expected schemas**
    - **Validates: Requirements 5.5, 6.5, 7.5**

  - [x] 4.3 Write unit tests for data cleaner
    - Test deduplication with known duplicate sets
    - Test normalization with HTML strings, unicode, edge cases (empty string, only whitespace)
    - Test language detection with known English and non-English samples
    - Test short review discarding (< 10 chars)
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 5. Checkpoint - Ensure cleaner tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Sentiment analyzer module
  - [x] 6.1 Implement sentiment analyzer (`03_sentiment_analysis.py`)
    - Implement `translate_to_english(text, source_lang)` using `googletrans`, return (translated_text, success_flag), handle failures gracefully
    - Implement `apply_hinglish_boost(text, vader_score)` using `HINGLISH_SENTIMENT_DICT`, weighted average: 0.3 * hinglish_boost + 0.7 * vader_score
    - Implement `classify_sentiment(text, star_rating, language)`:
      - English: VADER compound score directly
      - Non-English: translate via googletrans, then VADER; Hinglish boost for hi/mixed
      - Translation failure fallback: star-rating-only or "untranslatable" neutral
      - Combine text + star: 0.4 * text_score + 0.6 * star_score when star available
      - Thresholds: > 0.05 positive, < -0.05 negative, else neutral
    - Implement `extract_features(text, category)` using keyword dictionaries; for non-English, match on both original and translated text
    - Implement `analyze_sentiment(input_path, output_path)` full pipeline:
      - Output CSV with columns: review_id, app_name, category, overall_sentiment, sentiment_score, feature_mentions, feature_sentiments, language, sentiment_method, translated
      - Produce sentiment_summary.json with per_app, per_category, per_region stats, top_praised_features, top_criticized_features
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 6.2 Write property tests for sentiment analyzer
    - **Property 5: Sentiment output validity**
    - **Validates: Requirements 6.1, 6.2**
    - **Property 6: Feature keyword extraction detects injected features**
    - **Validates: Requirements 6.3**

  - [x] 6.3 Write unit tests for sentiment analyzer
    - Test classify_sentiment with clearly positive/negative/neutral texts
    - Test star rating combination logic
    - Test Hinglish boost application
    - Test feature extraction with known keyword matches
    - Test translation failure fallback paths
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 7. WTP analyzer module
  - [x] 7.1 Implement WTP analyzer (`04_wtp_analysis.py`)
    - Implement `detect_wtp_signals(text)` using regex patterns from config; extract surrounding sentence as context; identify associated feature via keyword matching
    - Implement `classify_wtp_signal(signal_text)` returning positive_wtp, negative_wtp, or conditional_wtp
    - Implement `classify_monetization_model(app_reviews)` using `MONETIZATION_MODEL_PATTERNS` keyword counting, return dominant model + confidence
    - Implement `analyze_cross_category_monetization(wtp_results)` to identify ancestry↔astrology WTP crossover
    - Implement `analyze_wtp(input_path, output_path)` full pipeline:
      - Output CSV with columns: review_id, app_name, category, wtp_signal_text, wtp_classification, associated_feature, market_region
      - Produce wtp_summary.json with per_category, per_region stats, top_features_willing_to_pay, top_pricing_complaints, monetization_models, cross_category_monetization, family_tree_specific_wtp, astrology_specific_wtp
    - Separately track family tree WTP vs astrology WTP signals
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 13.1, 13.2, 13.6_

  - [x] 7.2 Write property test for WTP analyzer
    - **Property 7: WTP detection, classification, and feature association**
    - **Validates: Requirements 7.1, 7.2, 7.3**
    - **Property 12: Monetization model classification validity**
    - **Validates: Requirements 13.2**

  - [x] 7.3 Write unit tests for WTP analyzer
    - Test WTP signal detection with known keyword patterns
    - Test classification of positive/negative/conditional signals
    - Test monetization model classification with mock review sets
    - Test cross-category monetization detection
    - Test family tree vs astrology WTP tracking
    - _Requirements: 7.1, 7.2, 7.3, 13.2, 13.6_

- [x] 8. Checkpoint - Ensure sentiment and WTP tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Demand overlap analyzer module
  - [x] 9.1 Implement demand overlap analyzer (`05_demand_overlap.py`)
    - Implement `detect_overlap_signals(text, source_category)`:
      - For astrology apps: scan for ancestry/family keywords from `OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS`
      - For ancestry apps: scan for astrology keywords from `OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS`
      - Return list of {signal_text, target_category, cross_feature}
    - Implement `analyze_overlap(input_path, csv_output, json_output)`:
      - Output CSV with all detected overlap signals: review_id, app_name, source_category, target_category, signal_text, cross_feature
      - Calculate bidirectional overlap percentages: (reviews_with_signals / total_reviews_in_category) * 100
      - Identify top 10 cross-category features from each direction
      - Output overlap_summary.json with astrology_to_ancestry_pct, ancestry_to_astrology_pct, top_cross_features for each direction
    - Guard against zero denominators in percentage calculations
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x] 9.2 Write property tests for demand overlap analyzer
    - **Property 8: Bidirectional demand overlap detection**
    - **Validates: Requirements 8.1, 8.2, 8.3**
    - **Property 9: Overlap percentage calculation correctness**
    - **Validates: Requirements 8.4, 8.5**

  - [x] 9.3 Write unit tests for demand overlap analyzer
    - Test overlap detection with known cross-category keywords
    - Test bidirectional detection (astrology→ancestry and ancestry→astrology)
    - Test percentage calculation with known counts
    - Test zero-denominator edge case
    - _Requirements: 8.1, 8.2, 8.4, 8.5_

- [x] 10. Report generator module
  - [x] 10.1 Implement report generator (`06_report.py`)
    - Implement `load_all_data()` to load all CSV and JSON outputs from data/ directory; handle missing files gracefully
    - Implement `build_competitive_landscape(data)`:
      - Build competitive matrix: app → {category, region, avg_rating, review_count, sentiment, top_features}
      - Identify market gaps at the intersection of family context and astrology
      - Rank top 5 features for astrology and ancestry apps
      - Identify hybrid apps and analyze their reception
      - Output `data/competitive_landscape.json`
    - Implement `generate_html_report(data, output_path)`:
      - Self-contained HTML with embedded Plotly charts via CDN
      - Sections: Executive Summary (≤500 words), Data Collection Overview, Sentiment Analysis, WTP Analysis, Demand Overlap Analysis, Competitive Landscape, Family Tree Monetization Strategy, Strategic Recommendations, Data Limitations & Caveats
      - Family Tree Monetization Strategy section: monetization model comparison table, cross-category monetization potential, family tree WTP breakdown, standalone vs free-funnel vs hybrid recommendation
      - Strategic Recommendations: repositioning answer, positioning statements, prioritized feature recommendations
      - Visualizations: sentiment distribution bar charts, WTP signal distribution charts, demand overlap matrix/heatmap, competitive landscape scatter plot, feature demand heatmap
      - Note data limitations where data is insufficient
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 12.4, 13.3, 13.4, 13.5_

  - [x] 10.2 Write property test for report generator
    - **Property 10: Feature ranking is correctly ordered**
    - **Validates: Requirements 9.3**

  - [x] 10.3 Write unit tests for report generator
    - Test load_all_data with mock data files
    - Test competitive landscape building with mock data
    - Test HTML report contains all expected sections
    - Test handling of missing/empty data files
    - _Requirements: 9.1, 10.1, 10.7_

- [ ] 11. Checkpoint - Ensure report tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Pipeline orchestrator and CSV round-trip
  - [x] 12.1 Implement pipeline orchestrator (`run_pipeline.py`)
    - Implement `run_stage(stage_name)` to run a single pipeline stage, return True on success
    - Implement `run_pipeline(stages)` to run all or specified stages in order: scrape → clean → sentiment → wtp → overlap → report
    - CLI with `argparse`: `--stage` flag accepting scrape, clean, sentiment, wtp, overlap, report
    - Log stage name, duration, and output file paths on completion
    - Catch unhandled exceptions per stage: log error with traceback, mark as skipped, continue
    - Handle missing input files: log warning and skip stage
    - Print final summary: stages completed, stages skipped, total reviews processed, output file locations
    - Create `data/` and `output/` directories if they don't exist
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [x] 12.2 Write CSV round-trip property test
    - **Property 11: CSV round-trip preserves data**
    - **Validates: Requirements 12.1, 12.3**

  - [x] 12.3 Write unit tests for pipeline orchestrator
    - Test CLI argument parsing for --stage flags
    - Test stage execution order
    - Test error handling (missing files, failed stages)
    - Test summary output
    - _Requirements: 11.1, 11.3, 11.4, 11.6_

- [x] 13. Integration tests and final wiring
  - [x] 13.1 Write integration tests
    - Test full pipeline dry run on a small synthetic dataset verifying all stages connect
    - Test report output is valid HTML containing all expected sections
    - _Requirements: 11.1, 10.1, 12.4_

- [x] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation between major modules
- Property tests validate the 12 universal correctness properties from the design using Hypothesis
- Unit tests validate specific examples and edge cases using pytest
- All code is Python, targeting the `positioning_analysis/` directory
- The existing `imeuswe_analysis/` directory is left untouched; the new pipeline replaces it
