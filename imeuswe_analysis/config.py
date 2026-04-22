"""
Configuration for iMeUsWe AI Astrology Chatbot - Sentiment & WTP Analysis
"""

# Reddit API credentials (get from https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID = "YOUR_CLIENT_ID"
REDDIT_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDDIT_USER_AGENT = "imeuswe_astrology_analysis/1.0"

# Competitor apps with paid AI astrology chatbot features
COMPETITORS = [
    "Co-Star",
    "The Pattern",
    "Sanctuary",
    "Astro Future",
    "Yodha",
    "AstroSage",
]

# Search queries for Reddit scraping
SEARCH_QUERIES = [
    # Competitor-specific (paid AI astrology)
    "Co-Star premium paid",
    "Co-Star AI chatbot astrology",
    "The Pattern premium astrology",
    "Sanctuary astrology subscription",
    "paid astrology app AI",
    "astrology chatbot subscription worth it",
    "astrology app premium features",
    "AI astrology chatbot review",
    "astrology app subscription price",
    "paying for astrology app",
    # General sentiment on paid astrology AI
    "would you pay for astrology AI",
    "free vs paid astrology app",
    "astrology subscription not worth",
    "astrology app too expensive",
]

# Subreddits to search
SUBREDDITS = [
    "astrology",
    "AskAstrologers",
    "CoStarAstrology",
    "spirituality",
    "apps",
    "AndroidApps",
    "iphone",
]

# Sentiment model
SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment"

# WTP keywords
WTP_POSITIVE_KEYWORDS = [
    "worth it", "would pay", "happy to pay", "good value", "take my money",
    "fair price", "reasonable price", "gladly pay", "subscribe", "subscribed",
    "premium worth", "paid version better", "money well spent",
]

WTP_NEGATIVE_KEYWORDS = [
    "too expensive", "not worth", "overpriced", "rip off", "ripoff",
    "waste of money", "wouldn't pay", "won't pay", "refuse to pay",
    "should be free", "unsubscribed", "cancelled subscription", "canceled",
    "free alternative", "not paying", "never pay", "scam",
]

# Output paths
RAW_DATA_PATH = "data/raw_reddit_data.csv"
CLEANED_DATA_PATH = "data/cleaned_data.csv"
SENTIMENT_OUTPUT_PATH = "data/sentiment_results.csv"
WTP_OUTPUT_PATH = "data/wtp_analysis.csv"
REPORT_OUTPUT_PATH = "output/analysis_report.png"
