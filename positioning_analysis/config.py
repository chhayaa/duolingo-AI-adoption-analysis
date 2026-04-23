"""
Configuration for Positioning Analysis Pipeline.

Central configuration defining the app registry, feature keyword dictionaries,
WTP patterns, monetization keywords, overlap keywords, Hinglish sentiment
dictionary, and shared constants used across all pipeline stages.
"""

import os

# ---------------------------------------------------------------------------
# Directory paths & constants
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
REQUEST_DELAY = 2.0  # seconds between HTTP requests
APPLE_STORE_COUNTRIES = ["in", "us", "gb", "au", "ca", "sg"]

# ---------------------------------------------------------------------------
# App Registry  (10+ astrology, 6+ ancestry)
# ---------------------------------------------------------------------------
APP_REGISTRY = [
    # ---- Astrology Apps ----
    {
        "name": "Astrotalk",
        "category": "astrology",
        "google_play_id": "com.astrotalk",
        "apple_app_id": "1474946498",
        "web_sources": [
            {"url": "https://www.trustpilot.com/review/astrotalk.com", "source_type": "trustpilot"},
        ],
        "market_region": "india",
    },
    {
        "name": "Co-Star",
        "category": "astrology",
        "google_play_id": "com.costarastrology",
        "apple_app_id": "1264782561",
        "web_sources": [
            {"url": "https://www.trustpilot.com/review/costarastrology.com", "source_type": "trustpilot"},
            {"url": "https://www.producthunt.com/products/co-star", "source_type": "producthunt"},
        ],
        "market_region": "global",
    },
    {
        "name": "The Pattern",
        "category": "astrology",
        "google_play_id": "com.thepattern.app",
        "apple_app_id": "1071750249",
        "web_sources": [],
        "market_region": "global",
    },
    {
        "name": "Kundli Software",
        "category": "astrology",
        "google_play_id": "com.ojassoft.astrology",
        "apple_app_id": "1190800038",
        "web_sources": [],
        "market_region": "india",
    },
    {
        "name": "AstroSage",
        "category": "astrology",
        "google_play_id": "com.ojassoft.astrology",
        "apple_app_id": "1215aborede",
        "web_sources": [
            {"url": "https://www.google.com/search?q=site:reddit.com+astrosage+review", "source_type": "google_reddit"},
        ],
        "market_region": "india",
    },
    {
        "name": "Jyotish - Vedic Astrology",
        "category": "astrology",
        "google_play_id": "com.vishdroid.jyotisha",
        "apple_app_id": "1456789012",
        "web_sources": [],
        "market_region": "india",
    },
    {
        "name": "InstaAstro",
        "category": "astrology",
        "google_play_id": "com.instaastro.onlineastrology",
        "apple_app_id": "1598765432",
        "web_sources": [
            {"url": "https://www.trustpilot.com/review/instaastro.com", "source_type": "trustpilot"},
        ],
        "market_region": "india",
    },
    {
        "name": "Astroyogi",
        "category": "astrology",
        "google_play_id": "com.netway.phone.advice",
        "apple_app_id": "489217434",
        "web_sources": [
            {"url": "https://www.trustpilot.com/review/astroyogi.com", "source_type": "trustpilot"},
        ],
        "market_region": "both",
    },
    {
        "name": "Sanctuary Astrology",
        "category": "astrology",
        "google_play_id": "com.sanctuaryworld.sanctuaryandroid",
        "apple_app_id": "1474702624",
        "web_sources": [
            {"url": "https://www.producthunt.com/products/sanctuary-2", "source_type": "producthunt"},
        ],
        "market_region": "global",
    },
    {
        "name": "Yodha My Astrology",
        "category": "astrology",
        "google_play_id": "com.astroid.yodha",
        "apple_app_id": "689327527",
        "web_sources": [],
        "market_region": "global",
    },
    {
        "name": "Astro Future",
        "category": "astrology",
        "google_play_id": "com.ndyuiklui",
        "apple_app_id": "1562345678",
        "web_sources": [],
        "market_region": "global",
    },
    {
        "name": "Kundli by Drik Panchang",
        "category": "astrology",
        "google_play_id": "com.drikp.core",
        "apple_app_id": "1234567890",
        "web_sources": [],
        "market_region": "india",
    },
    # ---- Ancestry / Family-Tree Apps ----
    {
        "name": "Ancestry",
        "category": "ancestry",
        "google_play_id": "com.ancestry.android.apps.ancestry",
        "apple_app_id": "364325883",
        "web_sources": [
            {"url": "https://www.trustpilot.com/review/ancestry.com", "source_type": "trustpilot"},
            {"url": "https://www.g2.com/products/ancestry/reviews", "source_type": "g2"},
        ],
        "market_region": "global",
    },
    {
        "name": "MyHeritage",
        "category": "ancestry",
        "google_play_id": "air.com.myheritage.mobile",
        "apple_app_id": "477971748",
        "web_sources": [
            {"url": "https://www.trustpilot.com/review/myheritage.com", "source_type": "trustpilot"},
            {"url": "https://www.g2.com/products/myheritage/reviews", "source_type": "g2"},
        ],
        "market_region": "global",
    },
    {
        "name": "FamilySearch",
        "category": "ancestry",
        "google_play_id": "org.familysearch.mobile",
        "apple_app_id": "459196149",
        "web_sources": [
            {"url": "https://www.google.com/search?q=site:reddit.com+familysearch+review", "source_type": "google_reddit"},
        ],
        "market_region": "global",
    },
    {
        "name": "FindMyPast",
        "category": "ancestry",
        "google_play_id": "com.findmypast.prod",
        "apple_app_id": "650532498",
        "web_sources": [
            {"url": "https://www.trustpilot.com/review/findmypast.co.uk", "source_type": "trustpilot"},
        ],
        "market_region": "global",
    },
    {
        "name": "23andMe",
        "category": "ancestry",
        "google_play_id": "com.twentythreeandme.app",
        "apple_app_id": "952516687",
        "web_sources": [
            {"url": "https://www.trustpilot.com/review/23andme.com", "source_type": "trustpilot"},
            {"url": "https://www.g2.com/products/23andme/reviews", "source_type": "g2"},
        ],
        "market_region": "global",
    },
    {
        "name": "Kuldevi - Family Tree",
        "category": "ancestry",
        "google_play_id": "com.kuldevi.familytree",
        "apple_app_id": "1587654321",
        "web_sources": [],
        "market_region": "india",
    },
    {
        "name": "BanyanTree - Family App",
        "category": "ancestry",
        "google_play_id": "com.banyantree.family",
        "apple_app_id": "1623456789",
        "web_sources": [],
        "market_region": "india",
    },
]

# ---------------------------------------------------------------------------
# Astrology Feature Keywords  (India-specific terms included)
# ---------------------------------------------------------------------------
ASTROLOGY_FEATURE_KEYWORDS = {
    "kundli": ["kundli", "kundali", "kundli matching", "kundali matching", "gun milan"],
    "mangal_dosha": ["mangal dosha", "manglik", "mangal dosh"],
    "rashi": ["rashi", "rashifal", "rashi bhavishya"],
    "nakshatra": ["nakshatra", "birth star", "janma nakshatra"],
    "panchang": ["panchang", "panchangam", "tithi", "hindu calendar"],
    "muhurat": ["muhurat", "muhurta", "shubh muhurat", "auspicious time"],
    "vastu": ["vastu", "vastu shastra", "vastu tips"],
    "numerology": ["numerology", "ank jyotish", "lucky number"],
    "janam_patri": ["janam patri", "janam patrika", "birth chart", "janampatri"],
    "dasha": ["dasha", "mahadasha", "antardasha", "vimshottari"],
    "gochar": ["gochar", "transit", "grah gochar", "planetary transit"],
    "remedies": ["remedies", "upay", "totke", "upaay"],
    "pooja": ["pooja", "puja", "havan", "homam"],
    "gemstone": ["gemstone", "ratna", "neelam", "pukhraj", "gemstone recommendation"],
    "marriage_compatibility": ["marriage compatibility", "vivah", "shaadi", "rishta"],
    "career_prediction": ["career prediction", "career horoscope", "job prediction"],
    "health_prediction": ["health prediction", "health horoscope", "arogya"],
    "horoscope": ["horoscope", "daily horoscope", "weekly horoscope", "monthly horoscope"],
    "zodiac": ["zodiac", "zodiac sign", "sun sign", "moon sign"],
    "tarot": ["tarot", "tarot reading", "tarot card"],
}

# ---------------------------------------------------------------------------
# Ancestry Feature Keywords  (India-specific terms included)
# ---------------------------------------------------------------------------
ANCESTRY_FEATURE_KEYWORDS = {
    "gotra": ["gotra", "gotra matching"],
    "vanshavali": ["vanshavali", "vansh", "family lineage"],
    "kul_devta": ["kul devta", "kul devi", "family deity", "ishtadev"],
    "family_puja": ["family puja traditions", "kul parampara", "family rituals"],
    "ancestral_village": ["ancestral village", "mool gaon", "native place", "hometown"],
    "caste_history": ["caste", "jati", "jati history", "caste history", "varna"],
    "family_tree": ["family tree", "pedigree", "genealogy", "family chart"],
    "dna_testing": ["dna test", "dna kit", "genetic testing", "ethnicity estimate"],
    "historical_records": ["historical records", "census", "birth records", "death records"],
    "photo_storage": ["photo storage", "family photos", "photo album", "memories"],
    "family_stories": ["family stories", "life stories", "family history", "oral history"],
    "migration_history": ["migration", "immigration", "emigration", "diaspora"],
}

# ---------------------------------------------------------------------------
# WTP (Willingness-to-Pay) Patterns
# ---------------------------------------------------------------------------
WTP_POSITIVE_PATTERNS = [
    "worth paying",
    "worth the price",
    "worth the money",
    "would pay",
    "happy to pay",
    "gladly pay",
    "good value",
    "fair price",
    "reasonable price",
    "take my money",
    "money well spent",
    "paid version better",
    "premium worth",
    "subscribed",
    "great investment",
    "value for money",
    "paisa vasool",
    "worth every penny",
    "best purchase",
    "would recommend premium",
    "worth subscribing",
]

WTP_NEGATIVE_PATTERNS = [
    "too expensive",
    "not worth",
    "overpriced",
    "rip off",
    "ripoff",
    "waste of money",
    "wouldn't pay",
    "won't pay",
    "refuse to pay",
    "should be free",
    "unsubscribed",
    "cancelled subscription",
    "canceled subscription",
    "free alternative",
    "not paying",
    "never pay",
    "scam",
    "money grab",
    "daylight robbery",
    "too costly",
    "highway robbery",
    "loot",
    "paisa barbaad",
]

WTP_CONDITIONAL_PATTERNS = [
    "would pay if",
    "might pay",
    "could pay",
    "pay only if",
    "worth it if",
    "would subscribe if",
    "depends on price",
    "if the price",
    "if they add",
    "if it had",
    "would consider paying",
    "maybe worth",
    "on the fence",
    "need more features to justify",
]

# ---------------------------------------------------------------------------
# Monetization Keywords (category-specific)
# ---------------------------------------------------------------------------
ASTROLOGY_MONETIZATION_KEYWORDS = [
    "consultation fee",
    "per-reading charge",
    "astrologer chat",
    "premium predictions",
    "detailed report",
    "premium horoscope",
    "paid consultation",
    "chat with astrologer",
    "per minute charge",
    "call charge",
    "wallet recharge",
]

ANCESTRY_MONETIZATION_KEYWORDS = [
    "premium tree",
    "unlimited members",
    "family tree export",
    "photo storage",
    "record access",
    "DNA kit",
    "collaboration",
    "shared tree",
    "tree size limit",
    "upgrade to add more",
    "premium features",
    "family group",
]

MONETIZATION_MODEL_PATTERNS = {
    "subscription": ["subscription", "monthly", "yearly", "annual plan", "renew"],
    "one_time": ["one-time", "lifetime", "single purchase"],
    "freemium": ["free version", "basic free", "premium upgrade", "in-app purchase"],
    "ad_supported": ["too many ads", "remove ads", "ad-free"],
}

# ---------------------------------------------------------------------------
# Demand Overlap Keywords (cross-category interest signals)
# ---------------------------------------------------------------------------
# Keywords that indicate astrology users wanting ancestry/family features
OVERLAP_ASTROLOGY_TO_ANCESTRY_KEYWORDS = [
    "family tree",
    "family history",
    "ancestry",
    "lineage",
    "heritage",
    "genealogy",
    "forefathers",
    "ancestors",
    "generational",
    "family roots",
    "vanshavali",
    "gotra",
    "kul",
    "pitru",
    "pitru dosha",
    "family karma",
    "past life family",
]

# Keywords that indicate ancestry users wanting astrology/spiritual features
OVERLAP_ANCESTRY_TO_ASTROLOGY_KEYWORDS = [
    "astrology",
    "horoscope",
    "birth chart",
    "kundli",
    "zodiac",
    "spiritual",
    "star sign",
    "rashi",
    "nakshatra",
    "jyotish",
    "planetary",
    "cosmic",
    "vedic",
    "karma",
    "destiny",
    "fate",
    "muhurat",
]

# ---------------------------------------------------------------------------
# Hinglish Sentiment Dictionary
# Maps common Hindi/Hinglish sentiment words to polarity scores (-1.0 to 1.0).
# Used as a boost layer on top of VADER for translated reviews.
# ---------------------------------------------------------------------------
HINGLISH_SENTIMENT_DICT = {
    # Positive
    "bahut accha": 0.8,
    "paisa vasool": 0.9,
    "zabardast": 0.9,
    "mast": 0.7,
    "kamaal": 0.8,
    "shandaar": 0.9,
    "behtareen": 0.9,
    "lajawab": 0.9,
    "mazaa aa gaya": 0.8,
    "accha hai": 0.6,
    "badhiya": 0.7,
    "shandar": 0.9,
    "jabardast": 0.9,
    "sahi hai": 0.5,
    "tagda": 0.7,
    "kadak": 0.7,
    "dhansu": 0.8,
    "jhakkas": 0.8,
    "first class": 0.8,
    "top class": 0.8,
    # Negative
    "bekar": -0.7,
    "bakwas": -0.8,
    "ghatiya": -0.9,
    "faltu": -0.6,
    "wahiyat": -0.8,
    "tatti": -0.9,
    "ganda": -0.7,
    "time waste": -0.7,
    "pagal bana rahe": -0.8,
    "dhoka": -0.9,
    "kaam ka nahi": -0.6,
    "bekaar": -0.7,
    "paisa barbaad": -0.9,
    "loot": -0.8,
    "chori": -0.8,
    "fraud": -0.9,
    "jhooth": -0.8,
    "ghatia": -0.9,
    "bura": -0.6,
    "kharab": -0.7,
    # Neutral / mild
    "theek hai": 0.1,
    "chalta hai": 0.1,
    "thik thak": 0.0,
}
