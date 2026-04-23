# Requirements Document

## Introduction

This document defines the requirements for a competitive analysis and positioning research pipeline for iMeUsWe. The pipeline will scrape, clean, analyze, and report on user reviews from top astrology and ancestry/family-tree apps across India and global markets. The goal is to answer three strategic questions with data-backed insights:

1. Should iMeUsWe reposition as a "family astrology" platform?
2. If yes, what should the positioning statement be?
3. What product features/use cases are necessary to deliver a product experience consistent with the positioning?

iMeUsWe is an app (Android, iOS, web) currently offering Ancestry, Communities, and Astrology features. The company has been positioned as a "lineage tech" company but is considering repositioning as a "family astrology platform" that uses family context (family tree, member profiles, family stories, life stories, communities data + birth details) to guide life decisions.

## Glossary

- **Pipeline**: The end-to-end Python data processing system that scrapes, cleans, analyzes, and reports on app review data
- **Review_Scraper**: The module responsible for collecting user reviews from app stores and web sources
- **Data_Cleaner**: The module responsible for deduplicating, normalizing, and structuring raw scraped review data
- **Sentiment_Analyzer**: The module responsible for classifying review text into positive, negative, or neutral sentiment and extracting feature-level sentiment
- **WTP_Analyzer**: The module responsible for identifying willingness-to-pay signals, pricing sentiment, and monetization insights from review text
- **Demand_Overlap_Analyzer**: The module responsible for detecting cross-category interest — astrology users wanting family context and ancestry users wanting astrology features
- **Report_Generator**: The module responsible for producing the final strategic analysis report with data-backed recommendations
- **App_Registry**: The configuration that defines which apps to scrape, their store IDs, categories, and metadata
- **Astrology_Apps**: The set of astrology apps to analyze, including Astrotalk, Co-Star, The Pattern, Kundli Software, AstroSage, Jyotish, InstaAstro, Astroyogi, and other top astrology apps in India and globally
- **Ancestry_Apps**: The set of ancestry/family-tree apps to analyze, including Ancestry.com, MyHeritage, FamilySearch, FindMyPast, 23andMe (genealogy side), and India-specific ancestry/family tree apps
- **Hybrid_Apps**: Any apps that combine astrology and family/ancestry features
- **WTP_Signal**: A textual indicator in a review that reveals willingness to pay, pricing sensitivity, or monetization preference (e.g., "worth paying for", "too expensive", "would pay for X")
- **Demand_Overlap_Signal**: A textual indicator in a review from one category that expresses interest in features from the other category
- **Feature_Mention**: A reference in a review to a specific product feature or capability
- **Review_Source**: The platform from which a review is scraped — Google Play Store, Apple App Store, or web-based review sources (Trustpilot, G2, Product Hunt, Quora, app review blogs, Twitter/X, Google-indexed Reddit content)
- **Web_Source_Type**: The specific type of publicly accessible web source — Trustpilot, G2, Product Hunt, Quora, blog, Twitter/X, or Google-indexed Reddit — none of which require API keys or approval processes

## Requirements

### Requirement 1: App Registry Configuration

**User Story:** As a researcher, I want a centralized configuration of all target apps with their store identifiers and metadata, so that the scraping pipeline knows exactly which apps to collect reviews from.

#### Acceptance Criteria

1. THE App_Registry SHALL define entries for all Astrology_Apps including Astrotalk, Co-Star, The Pattern, Kundli Software, AstroSage, Jyotish, InstaAstro, and Astroyogi
2. THE App_Registry SHALL define entries for all Ancestry_Apps including Ancestry.com, MyHeritage, FamilySearch, FindMyPast, and 23andMe
3. THE App_Registry SHALL define entries for any identified Hybrid_Apps that combine astrology and family/ancestry features
4. WHEN an app entry is defined, THE App_Registry SHALL include the app name, category (astrology, ancestry, or hybrid), Google Play package ID, Apple App Store ID, web review URL (where applicable), and market region (India, global, or both)
5. THE App_Registry SHALL include at least 10 astrology apps and at least 6 ancestry apps across India and global markets

### Requirement 2: Review Scraping — Google Play Store

**User Story:** As a researcher, I want to scrape user reviews from the Google Play Store for all target apps, so that I have Android user feedback for analysis.

#### Acceptance Criteria

1. WHEN a Google Play package ID is provided, THE Review_Scraper SHALL collect user reviews for that app from the Google Play Store
2. THE Review_Scraper SHALL collect all available reviews per app from the Google Play Store with no upper limit on review count
3. WHEN collecting a review, THE Review_Scraper SHALL extract the review text, star rating, review date, reviewer name (anonymized), app name, and Review_Source
4. IF the Google Play Store returns an error or blocks the request, THEN THE Review_Scraper SHALL log the error with the app name and continue scraping the next app
5. THE Review_Scraper SHALL respect rate limits by introducing a configurable delay between requests to the Google Play Store

### Requirement 3: Review Scraping — Apple App Store

**User Story:** As a researcher, I want to scrape user reviews from the Apple App Store for all target apps, so that I have iOS user feedback for analysis.

#### Acceptance Criteria

1. WHEN an Apple App Store ID is provided, THE Review_Scraper SHALL collect user reviews for that app from the Apple App Store
2. THE Review_Scraper SHALL collect all available reviews per app from the Apple App Store with no upper limit on review count
3. WHEN collecting a review, THE Review_Scraper SHALL extract the review text, star rating, review date, reviewer name (anonymized), app name, and Review_Source
4. IF the Apple App Store returns an error or blocks the request, THEN THE Review_Scraper SHALL log the error with the app name and continue scraping the next app
5. THE Review_Scraper SHALL respect rate limits by introducing a configurable delay between requests to the Apple App Store

### Requirement 4: Review Scraping — Web Sources

**User Story:** As a researcher, I want to scrape user reviews and discussions from publicly accessible web sources that require no API keys or approval processes (e.g., Trustpilot, G2, Product Hunt, Quora, app review blogs, Twitter/X public search, Google-indexed Reddit content), so that I capture feedback beyond app stores.

#### Acceptance Criteria

1. WHEN a web review URL is configured for an app, THE Review_Scraper SHALL collect user reviews or discussion posts from that source using only publicly accessible pages that require no API registration or approval process
2. THE Review_Scraper SHALL support the following web source types: Trustpilot public review pages, G2 public app review pages, Product Hunt public discussion and review pages, Quora public discussion threads, app review blog articles with user comments, Twitter/X public search results mentioning app names, and Google search results surfacing Reddit content without direct Reddit API access
3. THE Review_Scraper SHALL collect all available posts or reviews per web source with no upper limit on collection count
4. WHEN collecting a web review, THE Review_Scraper SHALL extract the text content, score or rating (where available), date, source URL, source type (Trustpilot, G2, Product Hunt, Quora, blog, Twitter/X, or Google-indexed Reddit), associated app name, and Review_Source
5. IF a web source returns an error or blocks the request, THEN THE Review_Scraper SHALL log the error with the source URL and source type and continue scraping the next source
6. THE Review_Scraper SHALL respect rate limits by introducing a configurable delay between requests to web sources
7. THE Review_Scraper SHALL use only standard HTTP requests with proper User-Agent headers and SHALL NOT require any API keys, OAuth tokens, or third-party service approval for web source access

### Requirement 5: Data Cleaning and Processing

**User Story:** As a researcher, I want the raw scraped data cleaned and normalized, so that downstream analysis operates on consistent, high-quality data.

#### Acceptance Criteria

1. WHEN raw review data is provided, THE Data_Cleaner SHALL remove duplicate reviews based on review text and app name
2. WHEN raw review data is provided, THE Data_Cleaner SHALL normalize text by removing HTML tags, special characters, and excessive whitespace while preserving meaningful content
3. WHEN raw review data is provided, THE Data_Cleaner SHALL detect the language of each review and tag reviews as English or non-English
4. THE Data_Cleaner SHALL discard reviews with fewer than 10 characters of meaningful text after normalization
5. WHEN cleaning is complete, THE Data_Cleaner SHALL output a structured CSV file with columns: review_id, app_name, category, review_text, star_rating, review_date, review_source, language, market_region
6. THE Data_Cleaner SHALL produce a cleaning summary log reporting total reviews collected, duplicates removed, short reviews discarded, and final review count per app

### Requirement 6: Sentiment Analysis

**User Story:** As a researcher, I want sentiment analysis performed on all cleaned reviews, so that I understand user satisfaction patterns across astrology and ancestry apps.

#### Acceptance Criteria

1. WHEN a cleaned review is provided, THE Sentiment_Analyzer SHALL classify the review sentiment as positive, negative, or neutral
2. WHEN a cleaned review is provided, THE Sentiment_Analyzer SHALL assign a sentiment polarity score between -1.0 (most negative) and 1.0 (most positive)
3. WHEN a cleaned review is provided, THE Sentiment_Analyzer SHALL extract Feature_Mentions and assign sentiment to each mentioned feature
4. THE Sentiment_Analyzer SHALL aggregate sentiment scores per app, per category (astrology, ancestry, hybrid), and per market region (India, global)
5. WHEN sentiment analysis is complete, THE Sentiment_Analyzer SHALL output a CSV file with columns: review_id, app_name, category, overall_sentiment, sentiment_score, feature_mentions, feature_sentiments
6. THE Sentiment_Analyzer SHALL produce sentiment summary statistics including average sentiment per app, distribution of positive/negative/neutral per category, and top praised and criticized features per category

### Requirement 7: Willingness-to-Pay Analysis

**User Story:** As a researcher, I want to identify willingness-to-pay signals from reviews, so that I understand monetization potential for a family astrology positioning.

#### Acceptance Criteria

1. WHEN a cleaned review is provided, THE WTP_Analyzer SHALL scan for WTP_Signals using keyword patterns including "worth paying", "too expensive", "would pay", "free is enough", "premium", "subscription", "in-app purchase", and similar pricing-related phrases
2. WHEN a WTP_Signal is detected, THE WTP_Analyzer SHALL classify the signal as positive-wtp (willing to pay), negative-wtp (resistant to paying), or conditional-wtp (would pay under certain conditions)
3. THE WTP_Analyzer SHALL extract the specific feature or capability associated with each WTP_Signal where identifiable
4. THE WTP_Analyzer SHALL aggregate WTP signals per app, per category, and per market region
5. WHEN WTP analysis is complete, THE WTP_Analyzer SHALL output a CSV file with columns: review_id, app_name, category, wtp_signal_text, wtp_classification, associated_feature, market_region
6. THE WTP_Analyzer SHALL produce a WTP summary reporting the percentage of reviews containing WTP signals per category, the top features users are willing to pay for, and the top complaints about pricing per category
7. THE WTP_Analyzer SHALL include category-specific monetization keyword patterns: for astrology apps (consultation fee, per-reading charge, astrologer chat, premium predictions, detailed report) and for ancestry apps (premium tree, unlimited members, record access, DNA kit, tree export, photo storage, collaboration, shared tree)

### Requirement 8: Demand Overlap Analysis

**User Story:** As a researcher, I want to identify demand overlap between astrology and ancestry app users, so that I can evaluate whether a combined "family context + astrology" positioning has market support.

#### Acceptance Criteria

1. WHEN analyzing Astrology_Apps reviews, THE Demand_Overlap_Analyzer SHALL scan for Demand_Overlap_Signals indicating interest in family context, family tree, lineage, heritage, or generational features
2. WHEN analyzing Ancestry_Apps reviews, THE Demand_Overlap_Analyzer SHALL scan for Demand_Overlap_Signals indicating interest in astrology, horoscope, birth chart, kundli, zodiac, or spiritual guidance features
3. WHEN a Demand_Overlap_Signal is detected, THE Demand_Overlap_Analyzer SHALL record the review_id, app_name, source_category, target_category, signal_text, and the specific cross-category feature mentioned
4. THE Demand_Overlap_Analyzer SHALL calculate the percentage of astrology app reviews that mention family/ancestry features
5. THE Demand_Overlap_Analyzer SHALL calculate the percentage of ancestry app reviews that mention astrology/spiritual features
6. THE Demand_Overlap_Analyzer SHALL identify the top 10 most frequently mentioned cross-category features from each direction (astrology→ancestry and ancestry→astrology)
7. WHEN demand overlap analysis is complete, THE Demand_Overlap_Analyzer SHALL output a CSV file with all detected Demand_Overlap_Signals and a summary JSON with overlap percentages and top cross-category features

### Requirement 9: Competitive Landscape Mapping

**User Story:** As a researcher, I want a competitive landscape analysis of existing players, so that I understand where iMeUsWe would fit in the market.

#### Acceptance Criteria

1. THE Report_Generator SHALL produce a competitive landscape matrix categorizing each analyzed app by primary category (astrology, ancestry, hybrid), market region, average star rating, total review volume, and dominant sentiment
2. THE Report_Generator SHALL identify gaps in the competitive landscape where no existing app serves the intersection of family context and astrology
3. THE Report_Generator SHALL rank the top 5 most positively reviewed features across astrology apps and the top 5 across ancestry apps
4. THE Report_Generator SHALL identify any existing Hybrid_Apps and analyze their user reception, feature set, and market positioning

### Requirement 10: Strategic Report Generation

**User Story:** As a researcher, I want a comprehensive strategic report that answers the three positioning questions with data-backed insights, so that iMeUsWe leadership can make an informed repositioning decision.

#### Acceptance Criteria

1. THE Report_Generator SHALL produce an HTML report containing all analysis results, visualizations, and strategic recommendations
2. THE Report_Generator SHALL include a section answering "Should iMeUsWe reposition as a family astrology platform?" with supporting data from sentiment analysis, WTP analysis, and demand overlap analysis
3. THE Report_Generator SHALL include a section proposing positioning statement options for website and marketing channels, grounded in the language and themes found in positive user reviews
4. THE Report_Generator SHALL include a section recommending product features and use cases necessary to deliver a product experience consistent with the proposed positioning, prioritized by demand signal strength
5. THE Report_Generator SHALL include data visualizations: sentiment distribution charts per category, WTP signal distribution charts, demand overlap Venn diagram or matrix, competitive landscape map, and feature demand heatmap
6. THE Report_Generator SHALL include an executive summary of no more than 500 words at the top of the report
7. IF insufficient data is collected for any analysis dimension, THEN THE Report_Generator SHALL note the data limitation and qualify the corresponding recommendation accordingly
8. THE Report_Generator SHALL include a section analyzing family tree monetization strategy — whether to monetize family tree standalone, use it as a free funnel to paid astrology, or offer a hybrid model — with data from WTP signals, monetization model comparison, and cross-category monetization potential

### Requirement 11: Pipeline Orchestration

**User Story:** As a researcher, I want a single entry point to run the entire pipeline end-to-end, so that I can execute the full analysis with one command.

#### Acceptance Criteria

1. THE Pipeline SHALL execute all stages in order: scraping, cleaning, sentiment analysis, WTP analysis, demand overlap analysis, and report generation
2. WHEN a stage completes, THE Pipeline SHALL log the stage name, duration, and output file paths
3. IF a stage fails, THEN THE Pipeline SHALL log the error, skip the failed stage, and continue with subsequent stages using available data
4. THE Pipeline SHALL accept a command-line flag to run individual stages independently (e.g., `--stage scrape`, `--stage clean`, `--stage sentiment`, `--stage wtp`, `--stage overlap`, `--stage report`)
5. THE Pipeline SHALL store all intermediate data in a `data/` directory and all final outputs in an `output/` directory
6. WHEN the full pipeline completes, THE Pipeline SHALL print a summary of stages completed, stages skipped, total reviews processed, and output file locations

### Requirement 12: Data Export and Serialization

**User Story:** As a researcher, I want all intermediate and final data exported in standard formats, so that I can perform additional analysis in external tools.

#### Acceptance Criteria

1. THE Pipeline SHALL export all tabular data as CSV files with UTF-8 encoding and proper header rows
2. THE Pipeline SHALL export summary statistics and metadata as JSON files
3. WHEN a CSV file is written, THE Pipeline SHALL validate that the file can be re-read and parsed without errors (round-trip property)
4. THE Pipeline SHALL export the final report as a self-contained HTML file with embedded styles and visualizations

### Requirement 13: Monetization Model Analysis

**User Story:** As a researcher, I want to understand how astrology and ancestry apps monetize their features, so that I can determine whether iMeUsWe's family tree should be monetized standalone or used as a free funnel to paid astrology features.

#### Acceptance Criteria

1. THE WTP_Analyzer SHALL include ancestry-specific monetization keyword patterns including "premium tree", "unlimited members", "family tree export", "photo storage", "record access", "DNA kit", "collaboration", "shared tree", "tree size limit", "upgrade to add more", "premium features", "family group", and similar ancestry monetization phrases
2. THE WTP_Analyzer SHALL classify each app's dominant monetization model as one of: subscription, one-time purchase, freemium (free core + paid add-ons), or ad-supported, based on WTP signal patterns in reviews
3. THE Report_Generator SHALL include a monetization model comparison section showing how astrology apps monetize vs how ancestry apps monetize, with the dominant model per app
4. THE Report_Generator SHALL include analysis of whether ancestry/family tree users express willingness to pay for spiritual/astrology add-on features (cross-category monetization potential)
5. THE Report_Generator SHALL include a recommendation on whether iMeUsWe's family tree feature is better positioned as a standalone paid feature or as a free context-gathering tool that funnels users into paid astrology features, supported by WTP signal data from both categories
6. THE WTP_Analyzer SHALL separately track and report WTP signals for family tree specific features (tree creation, member management, photo/story storage, tree sharing, tree export) vs astrology features (readings, predictions, consultations, reports)
