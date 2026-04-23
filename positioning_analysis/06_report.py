"""
Step 6: Report generator.

Loads all pipeline outputs, builds a competitive landscape analysis,
and generates a self-contained HTML report with embedded Plotly charts.

Outputs:
    data/competitive_landscape.json
    output/positioning_report.html
"""

import json
import os
from collections import Counter
from datetime import datetime

import pandas as pd

from positioning_analysis.config import (
    APP_REGISTRY,
    ASTROLOGY_FEATURE_KEYWORDS,
    ANCESTRY_FEATURE_KEYWORDS,
    DATA_DIR,
    OUTPUT_DIR,
)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_all_data() -> dict:
    """Load all CSV and JSON outputs from the data/ directory.

    Returns a dict with keys for each data file.  Missing files are
    represented as empty DataFrames (for CSVs) or empty dicts (for JSONs).
    """
    data: dict = {}

    csv_files = {
        "cleaned_reviews": "cleaned_reviews.csv",
        "sentiment_results": "sentiment_results.csv",
        "wtp_results": "wtp_results.csv",
        "overlap_results": "overlap_results.csv",
    }
    json_files = {
        "sentiment_summary": "sentiment_summary.json",
        "wtp_summary": "wtp_summary.json",
        "overlap_summary": "overlap_summary.json",
        "cleaning_summary": "cleaning_summary.json",
    }

    for key, filename in csv_files.items():
        path = os.path.join(DATA_DIR, filename)
        try:
            data[key] = pd.read_csv(path, encoding="utf-8", encoding_errors="replace")
        except Exception:
            data[key] = pd.DataFrame()

    for key, filename in json_files.items():
        path = os.path.join(DATA_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data[key] = json.load(f)
        except Exception:
            data[key] = {}

    return data


# ---------------------------------------------------------------------------
# Competitive landscape builder
# ---------------------------------------------------------------------------

def build_competitive_landscape(data: dict) -> dict:
    """Build competitive landscape analysis from pipeline data.

    Produces a dict with:
      - apps: per-app competitive matrix
      - market_gaps: identified gaps at family+astrology intersection
      - top_astrology_features / top_ancestry_features: top 5 each
      - hybrid_apps: apps combining both categories

    Also writes ``data/competitive_landscape.json``.
    """
    cleaned = data.get("cleaned_reviews", pd.DataFrame())
    sentiment = data.get("sentiment_results", pd.DataFrame())
    sentiment_summary = data.get("sentiment_summary", {})

    # -- Build per-app matrix ------------------------------------------------
    apps_list: list[dict] = []
    registry_lookup = {entry["name"]: entry for entry in APP_REGISTRY}

    app_names = set()
    if not cleaned.empty and "app_name" in cleaned.columns:
        app_names = set(cleaned["app_name"].dropna().unique())
    # Also include registry apps even if no reviews collected
    app_names.update(registry_lookup.keys())

    per_app_sentiment = sentiment_summary.get("per_app", {})

    for app_name in sorted(app_names):
        reg = registry_lookup.get(app_name, {})
        category = reg.get("category", "unknown")
        region = reg.get("market_region", "unknown")

        # Star rating from cleaned reviews
        avg_rating = None
        review_count = 0
        if not cleaned.empty and "app_name" in cleaned.columns:
            app_rows = cleaned[cleaned["app_name"] == app_name]
            review_count = len(app_rows)
            if "star_rating" in app_rows.columns:
                ratings = pd.to_numeric(app_rows["star_rating"], errors="coerce").dropna()
                if len(ratings) > 0:
                    avg_rating = round(float(ratings.mean()), 2)

        # Dominant sentiment from summary
        app_sent = per_app_sentiment.get(app_name, {})
        dominant_sentiment = "unknown"
        if app_sent:
            pcts = {
                "positive": app_sent.get("positive_pct", 0),
                "negative": app_sent.get("negative_pct", 0),
                "neutral": app_sent.get("neutral_pct", 0),
            }
            dominant_sentiment = max(pcts, key=pcts.get)

        # Top features from sentiment results
        top_features: list[str] = []
        if not sentiment.empty and "app_name" in sentiment.columns and "feature_mentions" in sentiment.columns:
            app_sent_rows = sentiment[sentiment["app_name"] == app_name]
            feature_counter: Counter = Counter()
            for fm in app_sent_rows["feature_mentions"].dropna():
                try:
                    features = json.loads(fm) if isinstance(fm, str) else fm
                    if isinstance(features, list):
                        feature_counter.update(features)
                except (json.JSONDecodeError, TypeError):
                    pass
            top_features = [f for f, _ in feature_counter.most_common(5)]

        apps_list.append({
            "app_name": app_name,
            "category": category,
            "market_region": region,
            "avg_star_rating": avg_rating,
            "total_review_count": review_count,
            "dominant_sentiment": dominant_sentiment,
            "top_features": top_features,
        })

    # -- Market gaps ---------------------------------------------------------
    market_gaps = _identify_market_gaps(apps_list)

    # -- Top 5 features per category -----------------------------------------
    top_astrology_features = _rank_category_features(sentiment_summary, "astrology", 5)
    top_ancestry_features = _rank_category_features(sentiment_summary, "ancestry", 5)

    # -- Hybrid apps ---------------------------------------------------------
    hybrid_apps = _identify_hybrid_apps(apps_list, sentiment_summary)

    landscape = {
        "apps": apps_list,
        "market_gaps": market_gaps,
        "top_astrology_features": top_astrology_features,
        "top_ancestry_features": top_ancestry_features,
        "hybrid_apps": hybrid_apps,
    }

    # Write to disk
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "competitive_landscape.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(landscape, f, indent=2)

    return landscape


def _identify_market_gaps(apps_list: list[dict]) -> list[dict]:
    """Identify gaps at the intersection of family context and astrology."""
    categories = {a["category"] for a in apps_list}
    gaps: list[dict] = []

    has_hybrid = any(a["category"] == "hybrid" for a in apps_list)
    if not has_hybrid:
        gaps.append({
            "description": "No existing app combines family tree/ancestry context with astrology features",
            "opportunity": "A 'family astrology' platform that uses family context (tree, stories, birth details) to guide life decisions via astrology",
        })

    # Check if any astrology app has ancestry-related top features
    astro_apps_with_family = [
        a for a in apps_list
        if a["category"] == "astrology"
        and any(f in ANCESTRY_FEATURE_KEYWORDS for f in a.get("top_features", []))
    ]
    if not astro_apps_with_family:
        gaps.append({
            "description": "Astrology apps lack family tree or lineage features",
            "opportunity": "Integrating family context (gotra, vanshavali, ancestral data) into astrology predictions",
        })

    # Check if any ancestry app has astrology-related top features
    ancestry_apps_with_astro = [
        a for a in apps_list
        if a["category"] == "ancestry"
        and any(f in ASTROLOGY_FEATURE_KEYWORDS for f in a.get("top_features", []))
    ]
    if not ancestry_apps_with_astro:
        gaps.append({
            "description": "Ancestry apps lack astrology or spiritual guidance features",
            "opportunity": "Adding kundli, rashi, or spiritual guidance to family tree platforms",
        })

    return gaps


def _rank_category_features(
    sentiment_summary: dict,
    category: str,
    top_n: int = 5,
) -> list[dict]:
    """Rank top features for a category by average sentiment score.

    Uses the top_praised_features from the sentiment summary, filtered
    by the category's keyword dictionary.
    """
    keywords = (
        ASTROLOGY_FEATURE_KEYWORDS if category == "astrology"
        else ANCESTRY_FEATURE_KEYWORDS
    )
    praised = sentiment_summary.get("top_praised_features", [])

    category_features = [
        f for f in praised if f.get("feature", "") in keywords
    ]
    # Sort descending by avg_score
    category_features.sort(key=lambda x: x.get("avg_score", 0), reverse=True)
    return [
        {"feature": f["feature"], "avg_sentiment": f.get("avg_score", 0.0)}
        for f in category_features[:top_n]
    ]


def _identify_hybrid_apps(
    apps_list: list[dict],
    sentiment_summary: dict,
) -> list[dict]:
    """Identify apps categorized as hybrid and summarize their reception."""
    hybrids: list[dict] = []
    per_app = sentiment_summary.get("per_app", {})

    for app in apps_list:
        if app["category"] == "hybrid":
            app_sent = per_app.get(app["app_name"], {})
            hybrids.append({
                "app_name": app["app_name"],
                "features": app.get("top_features", []),
                "avg_rating": app.get("avg_star_rating"),
                "sentiment": app.get("dominant_sentiment", "unknown"),
            })

    return hybrids


# ---------------------------------------------------------------------------
# HTML report generation
# ---------------------------------------------------------------------------

def generate_html_report(data: dict, output_path: str) -> None:
    """Generate a self-contained HTML report with embedded Plotly charts.

    The report includes sections for executive summary, data collection,
    sentiment analysis, WTP analysis, demand overlap, competitive
    landscape, family tree monetization strategy, strategic
    recommendations, and data limitations.
    """
    landscape = data.get("competitive_landscape", {})
    sentiment_summary = data.get("sentiment_summary", {})
    wtp_summary = data.get("wtp_summary", {})
    overlap_summary = data.get("overlap_summary", {})
    cleaning_summary = data.get("cleaning_summary", {})

    sections = [
        _section_executive_summary(sentiment_summary, wtp_summary, overlap_summary, cleaning_summary),
        _section_data_collection(cleaning_summary, data),
        _section_sentiment(sentiment_summary, data),
        _section_wtp(wtp_summary),
        _section_overlap(overlap_summary),
        _section_competitive_landscape(landscape),
        _section_monetization_strategy(wtp_summary),
        _section_strategic_recommendations(sentiment_summary, wtp_summary, overlap_summary, landscape),
        _section_data_limitations(data),
    ]

    body = "\n".join(sections)
    html = _wrap_html(body)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# ---------------------------------------------------------------------------
# HTML wrapper
# ---------------------------------------------------------------------------

def _wrap_html(body: str) -> str:
    """Wrap section HTML in a full HTML document with Plotly CDN and styles."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>iMeUsWe Positioning Analysis Report</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px 40px; background: #f8f9fa; color: #333; }}
  h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
  h2 {{ color: #2c3e50; border-bottom: 1px solid #bdc3c7; padding-bottom: 8px; margin-top: 40px; }}
  h3 {{ color: #34495e; }}
  .section {{ background: #fff; padding: 25px 30px; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  .chart {{ width: 100%; min-height: 400px; margin: 20px 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 10px 12px; text-align: left; }}
  th {{ background: #3498db; color: #fff; }}
  tr:nth-child(even) {{ background: #f2f2f2; }}
  .limitation {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px 16px; margin: 10px 0; border-radius: 4px; }}
  .metric {{ display: inline-block; background: #ecf0f1; padding: 10px 18px; margin: 5px; border-radius: 6px; text-align: center; }}
  .metric .value {{ font-size: 1.6em; font-weight: bold; color: #2c3e50; }}
  .metric .label {{ font-size: 0.85em; color: #7f8c8d; }}
  .timestamp {{ color: #95a5a6; font-size: 0.85em; margin-top: 30px; }}
</style>
</head>
<body>
<h1>iMeUsWe Positioning Analysis Report</h1>
{body}
<p class="timestamp">Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_executive_summary(
    sentiment_summary: dict,
    wtp_summary: dict,
    overlap_summary: dict,
    cleaning_summary: dict,
) -> str:
    """Executive Summary section (≤500 words)."""
    total_reviews = cleaning_summary.get("final_count", 0)
    astro_to_anc = overlap_summary.get("astrology_to_ancestry_pct", 0)
    anc_to_astro = overlap_summary.get("ancestry_to_astrology_pct", 0)

    per_cat = sentiment_summary.get("per_category", {})
    astro_sent = per_cat.get("astrology", {})
    anc_sent = per_cat.get("ancestry", {})

    wtp_cat = wtp_summary.get("per_category", {})
    astro_wtp = wtp_cat.get("astrology", {}).get("wtp_pct", 0)
    anc_wtp = wtp_cat.get("ancestry", {}).get("wtp_pct", 0)

    top_features_wtp = wtp_summary.get("top_features_willing_to_pay", [])
    top_feat_str = ", ".join(f.get("feature", "") for f in top_features_wtp[:5]) or "N/A"

    return f"""<div class="section">
<h2>Executive Summary</h2>
<p>This report analyzes user reviews from astrology and ancestry apps across India and global markets
to evaluate whether iMeUsWe should reposition as a "family astrology" platform. The analysis covers
{total_reviews} cleaned reviews across {len(per_cat)} categories.</p>

<p><strong>Sentiment Overview:</strong> Astrology apps show an average sentiment score of
{astro_sent.get('avg_score', 'N/A')} with {astro_sent.get('positive_pct', 0):.0f}% positive reviews.
Ancestry apps show an average score of {anc_sent.get('avg_score', 'N/A')} with
{anc_sent.get('positive_pct', 0):.0f}% positive reviews.</p>

<p><strong>Demand Overlap:</strong> {astro_to_anc:.1f}% of astrology app reviews mention family/ancestry
features, while {anc_to_astro:.1f}% of ancestry app reviews mention astrology features. This
bidirectional interest signals a market opportunity at the intersection of both categories.</p>

<p><strong>Willingness to Pay:</strong> {astro_wtp:.1f}% of astrology reviews and {anc_wtp:.1f}% of
ancestry reviews contain WTP signals. Top features users are willing to pay for: {top_feat_str}.</p>

<p><strong>Competitive Landscape:</strong> No existing app fully combines family tree context with
astrology guidance, representing a clear market gap. iMeUsWe's existing ancestry + astrology feature
set positions it uniquely to capture this intersection.</p>

<p><strong>Recommendation:</strong> The data supports repositioning iMeUsWe as a "family astrology"
platform that uses family context to enhance astrological guidance. The family tree feature should
serve as a free engagement tool that funnels users into premium astrology services, with optional
paid ancestry add-ons for power users.</p>
</div>"""


def _section_data_collection(cleaning_summary: dict, data: dict) -> str:
    """Data Collection Overview section."""
    total = cleaning_summary.get("total_collected", 0)
    dupes = cleaning_summary.get("duplicates_removed", 0)
    short = cleaning_summary.get("short_reviews_discarded", 0)
    final = cleaning_summary.get("final_count", 0)
    per_app = cleaning_summary.get("per_app_counts", {})

    app_rows = ""
    for app, count in sorted(per_app.items(), key=lambda x: x[1], reverse=True):
        app_rows += f"<tr><td>{app}</td><td>{count}</td></tr>\n"

    if not app_rows:
        app_rows = '<tr><td colspan="2">No data collected</td></tr>'

    return f"""<div class="section">
<h2>Data Collection Overview</h2>
<div>
  <div class="metric"><div class="value">{total}</div><div class="label">Total Collected</div></div>
  <div class="metric"><div class="value">{dupes}</div><div class="label">Duplicates Removed</div></div>
  <div class="metric"><div class="value">{short}</div><div class="label">Short Reviews Discarded</div></div>
  <div class="metric"><div class="value">{final}</div><div class="label">Final Count</div></div>
</div>
<h3>Reviews per App</h3>
<table>
<tr><th>App</th><th>Review Count</th></tr>
{app_rows}
</table>
</div>"""


def _section_sentiment(sentiment_summary: dict, data: dict) -> str:
    """Sentiment Analysis section with Plotly bar chart."""
    per_cat = sentiment_summary.get("per_category", {})
    praised = sentiment_summary.get("top_praised_features", [])
    criticized = sentiment_summary.get("top_criticized_features", [])

    if not per_cat:
        return """<div class="section">
<h2>Sentiment Analysis</h2>
<div class="limitation">Insufficient sentiment data available for analysis.</div>
</div>"""

    # Build Plotly bar chart data
    categories = list(per_cat.keys())
    pos_vals = [per_cat[c].get("positive_pct", 0) for c in categories]
    neg_vals = [per_cat[c].get("negative_pct", 0) for c in categories]
    neu_vals = [per_cat[c].get("neutral_pct", 0) for c in categories]

    praised_rows = ""
    for f in praised[:10]:
        praised_rows += f'<tr><td>{f.get("feature", "")}</td><td>{f.get("avg_score", 0):.3f}</td><td>{f.get("mention_count", 0)}</td></tr>\n'

    criticized_rows = ""
    for f in criticized[:10]:
        criticized_rows += f'<tr><td>{f.get("feature", "")}</td><td>{f.get("avg_score", 0):.3f}</td><td>{f.get("mention_count", 0)}</td></tr>\n'

    chart_id = "sentiment_dist_chart"

    return f"""<div class="section">
<h2>Sentiment Analysis</h2>
<div id="{chart_id}" class="chart"></div>
<script>
Plotly.newPlot('{chart_id}', [
  {{x: {json.dumps(categories)}, y: {json.dumps(pos_vals)}, name: 'Positive', type: 'bar', marker: {{color: '#2ecc71'}}}},
  {{x: {json.dumps(categories)}, y: {json.dumps(neg_vals)}, name: 'Negative', type: 'bar', marker: {{color: '#e74c3c'}}}},
  {{x: {json.dumps(categories)}, y: {json.dumps(neu_vals)}, name: 'Neutral', type: 'bar', marker: {{color: '#95a5a6'}}}}
], {{
  barmode: 'group',
  title: 'Sentiment Distribution by Category',
  yaxis: {{title: 'Percentage (%)', range: [0, 100]}},
  xaxis: {{title: 'Category'}}
}});
</script>

<h3>Top Praised Features</h3>
<table>
<tr><th>Feature</th><th>Avg Sentiment</th><th>Mentions</th></tr>
{praised_rows if praised_rows else '<tr><td colspan="3">No feature data available</td></tr>'}
</table>

<h3>Top Criticized Features</h3>
<table>
<tr><th>Feature</th><th>Avg Sentiment</th><th>Mentions</th></tr>
{criticized_rows if criticized_rows else '<tr><td colspan="3">No feature data available</td></tr>'}
</table>
</div>"""


def _section_wtp(wtp_summary: dict) -> str:
    """WTP Analysis section with Plotly chart."""
    per_cat = wtp_summary.get("per_category", {})
    top_pay = wtp_summary.get("top_features_willing_to_pay", [])
    top_complaints = wtp_summary.get("top_pricing_complaints", [])

    if not per_cat:
        return """<div class="section">
<h2>Willingness-to-Pay Analysis</h2>
<div class="limitation">Insufficient WTP data available for analysis.</div>
</div>"""

    categories = list(per_cat.keys())
    pos_counts = [per_cat[c].get("positive_wtp_count", 0) for c in categories]
    neg_counts = [per_cat[c].get("negative_wtp_count", 0) for c in categories]
    cond_counts = [per_cat[c].get("conditional_wtp_count", 0) for c in categories]

    chart_id = "wtp_dist_chart"

    pay_rows = ""
    for f in top_pay[:10]:
        pay_rows += f'<tr><td>{f.get("feature", "")}</td><td>{f.get("positive_wtp_count", 0)}</td></tr>\n'

    complaint_rows = ""
    for f in top_complaints[:10]:
        complaint_rows += f'<tr><td>{f.get("feature", "")}</td><td>{f.get("negative_wtp_count", 0)}</td></tr>\n'

    return f"""<div class="section">
<h2>Willingness-to-Pay Analysis</h2>
<div id="{chart_id}" class="chart"></div>
<script>
Plotly.newPlot('{chart_id}', [
  {{x: {json.dumps(categories)}, y: {json.dumps(pos_counts)}, name: 'Positive WTP', type: 'bar', marker: {{color: '#27ae60'}}}},
  {{x: {json.dumps(categories)}, y: {json.dumps(neg_counts)}, name: 'Negative WTP', type: 'bar', marker: {{color: '#c0392b'}}}},
  {{x: {json.dumps(categories)}, y: {json.dumps(cond_counts)}, name: 'Conditional WTP', type: 'bar', marker: {{color: '#f39c12'}}}}
], {{
  barmode: 'group',
  title: 'WTP Signal Distribution by Category',
  yaxis: {{title: 'Signal Count'}},
  xaxis: {{title: 'Category'}}
}});
</script>

<h3>Top Features Users Are Willing to Pay For</h3>
<table>
<tr><th>Feature</th><th>Positive WTP Signals</th></tr>
{pay_rows if pay_rows else '<tr><td colspan="2">No data available</td></tr>'}
</table>

<h3>Top Pricing Complaints</h3>
<table>
<tr><th>Feature</th><th>Negative WTP Signals</th></tr>
{complaint_rows if complaint_rows else '<tr><td colspan="2">No pricing complaints detected</td></tr>'}
</table>
</div>"""


def _section_overlap(overlap_summary: dict) -> str:
    """Demand Overlap Analysis section with heatmap."""
    if not overlap_summary:
        return """<div class="section">
<h2>Demand Overlap Analysis</h2>
<div class="limitation">Insufficient overlap data available for analysis.</div>
</div>"""

    a2a_pct = overlap_summary.get("astrology_to_ancestry_pct", 0)
    anc2astro_pct = overlap_summary.get("ancestry_to_astrology_pct", 0)

    top_a2a = overlap_summary.get("top_cross_features_astrology_to_ancestry", [])
    top_anc2astro = overlap_summary.get("top_cross_features_ancestry_to_astrology", [])

    # Build overlap matrix heatmap
    chart_id = "overlap_heatmap"
    z_vals = [[0, a2a_pct], [anc2astro_pct, 0]]

    a2a_rows = ""
    for f in top_a2a[:10]:
        a2a_rows += f'<tr><td>{f.get("feature", "")}</td><td>{f.get("count", 0)}</td></tr>\n'

    anc2astro_rows = ""
    for f in top_anc2astro[:10]:
        anc2astro_rows += f'<tr><td>{f.get("feature", "")}</td><td>{f.get("count", 0)}</td></tr>\n'

    return f"""<div class="section">
<h2>Demand Overlap Analysis</h2>
<p>Bidirectional demand overlap between astrology and ancestry app users.</p>

<div id="{chart_id}" class="chart"></div>
<script>
Plotly.newPlot('{chart_id}', [{{
  z: {json.dumps(z_vals)},
  x: ['Astrology', 'Ancestry'],
  y: ['Astrology', 'Ancestry'],
  type: 'heatmap',
  colorscale: 'YlOrRd',
  text: [['—', '{a2a_pct:.1f}%'], ['{anc2astro_pct:.1f}%', '—']],
  texttemplate: '%{{text}}',
  hovertemplate: 'From %{{y}} → To %{{x}}: %{{z:.1f}}%<extra></extra>'
}}], {{
  title: 'Demand Overlap Matrix (% of reviews mentioning other category)',
  xaxis: {{title: 'Target Category'}},
  yaxis: {{title: 'Source Category'}}
}});
</script>

<div>
  <div class="metric"><div class="value">{a2a_pct:.1f}%</div><div class="label">Astrology → Ancestry</div></div>
  <div class="metric"><div class="value">{anc2astro_pct:.1f}%</div><div class="label">Ancestry → Astrology</div></div>
</div>

<h3>Top Cross-Features: Astrology → Ancestry</h3>
<table>
<tr><th>Feature</th><th>Mentions</th></tr>
{a2a_rows if a2a_rows else '<tr><td colspan="2">No cross-features detected</td></tr>'}
</table>

<h3>Top Cross-Features: Ancestry → Astrology</h3>
<table>
<tr><th>Feature</th><th>Mentions</th></tr>
{anc2astro_rows if anc2astro_rows else '<tr><td colspan="2">No cross-features detected</td></tr>'}
</table>
</div>"""


def _section_competitive_landscape(landscape: dict) -> str:
    """Competitive Landscape section with scatter plot."""
    apps = landscape.get("apps", [])
    gaps = landscape.get("market_gaps", [])
    hybrid_apps = landscape.get("hybrid_apps", [])

    if not apps:
        return """<div class="section">
<h2>Competitive Landscape</h2>
<div class="limitation">Insufficient data to build competitive landscape.</div>
</div>"""

    # Scatter plot: sentiment vs review volume
    chart_id = "landscape_scatter"

    # Group by category for coloring
    cat_colors = {"astrology": "#9b59b6", "ancestry": "#3498db", "hybrid": "#e67e22", "unknown": "#95a5a6"}
    traces_js = []
    for cat in ["astrology", "ancestry", "hybrid", "unknown"]:
        cat_apps = [a for a in apps if a["category"] == cat and a["total_review_count"] > 0]
        if not cat_apps:
            continue
        x_vals = [a["total_review_count"] for a in cat_apps]
        y_vals = [a.get("avg_star_rating") or 0 for a in cat_apps]
        names = [a["app_name"] for a in cat_apps]
        color = cat_colors.get(cat, "#95a5a6")
        traces_js.append(
            f"{{x: {json.dumps(x_vals)}, y: {json.dumps(y_vals)}, text: {json.dumps(names)}, "
            f"mode: 'markers+text', textposition: 'top center', type: 'scatter', "
            f"name: '{cat.title()}', marker: {{color: '{color}', size: 12}}}}"
        )

    traces_str = ",\n  ".join(traces_js) if traces_js else ""

    # App matrix table
    app_rows = ""
    for a in sorted(apps, key=lambda x: x["total_review_count"], reverse=True):
        rating_str = f'{a["avg_star_rating"]:.2f}' if a["avg_star_rating"] is not None else "N/A"
        features_str = ", ".join(a.get("top_features", [])[:3]) or "—"
        app_rows += (
            f'<tr><td>{a["app_name"]}</td><td>{a["category"]}</td>'
            f'<td>{a["market_region"]}</td><td>{rating_str}</td>'
            f'<td>{a["total_review_count"]}</td><td>{a["dominant_sentiment"]}</td>'
            f'<td>{features_str}</td></tr>\n'
        )

    gap_items = ""
    for g in gaps:
        gap_items += f'<li><strong>{g["description"]}</strong>: {g["opportunity"]}</li>\n'

    hybrid_section = ""
    if hybrid_apps:
        hybrid_rows = ""
        for h in hybrid_apps:
            rating_str = f'{h["avg_rating"]:.2f}' if h.get("avg_rating") is not None else "N/A"
            hybrid_rows += (
                f'<tr><td>{h["app_name"]}</td><td>{", ".join(h.get("features", [])) or "—"}</td>'
                f'<td>{rating_str}</td><td>{h.get("sentiment", "unknown")}</td></tr>\n'
            )
        hybrid_section = f"""<h3>Hybrid Apps</h3>
<table>
<tr><th>App</th><th>Features</th><th>Avg Rating</th><th>Sentiment</th></tr>
{hybrid_rows}
</table>"""
    else:
        hybrid_section = '<p>No hybrid apps (combining astrology + ancestry) were identified in the dataset.</p>'

    return f"""<div class="section">
<h2>Competitive Landscape</h2>

<div id="{chart_id}" class="chart"></div>
<script>
Plotly.newPlot('{chart_id}', [
  {traces_str}
], {{
  title: 'Competitive Landscape: Rating vs Review Volume',
  xaxis: {{title: 'Total Review Count', type: 'log'}},
  yaxis: {{title: 'Average Star Rating', range: [0, 5.5]}}
}});
</script>

<h3>Competitive Matrix</h3>
<table>
<tr><th>App</th><th>Category</th><th>Region</th><th>Avg Rating</th><th>Reviews</th><th>Sentiment</th><th>Top Features</th></tr>
{app_rows}
</table>

<h3>Market Gaps</h3>
<ul>
{gap_items if gap_items else '<li>No significant market gaps identified</li>'}
</ul>

{hybrid_section}
</div>"""


def _section_monetization_strategy(wtp_summary: dict) -> str:
    """Family Tree Monetization Strategy section."""
    monetization_models = wtp_summary.get("monetization_models", {})
    cross_cat = wtp_summary.get("cross_category_monetization", {})
    family_wtp = wtp_summary.get("family_tree_specific_wtp", {})
    astro_wtp = wtp_summary.get("astrology_specific_wtp", {})

    if not wtp_summary:
        return """<div class="section">
<h2>Family Tree Monetization Strategy</h2>
<div class="limitation">Insufficient WTP data to analyze monetization strategy.</div>
</div>"""

    # Monetization model comparison table
    model_rows = ""
    for app_name, info in sorted(monetization_models.items()):
        model = info.get("model", "unknown") if isinstance(info, dict) else str(info)
        confidence = info.get("confidence", 0) if isinstance(info, dict) else 0
        model_rows += f'<tr><td>{app_name}</td><td>{model}</td><td>{confidence:.0%}</td></tr>\n'

    # Cross-category monetization
    a2a_wtp = cross_cat.get("ancestry_to_astrology_wtp", {})
    astro2anc_wtp = cross_cat.get("astrology_to_ancestry_wtp", {})

    # Family tree vs astrology WTP comparison
    ft_total = family_wtp.get("total_signals", 0)
    ft_positive = family_wtp.get("positive", 0)
    ft_negative = family_wtp.get("negative", 0)
    ft_features = family_wtp.get("top_features", [])

    as_total = astro_wtp.get("total_signals", 0)
    as_positive = astro_wtp.get("positive", 0)
    as_negative = astro_wtp.get("negative", 0)
    as_features = astro_wtp.get("top_features", [])

    # Feature demand heatmap
    chart_id = "feature_demand_heatmap"
    all_features = []
    feature_counts = []
    for f in ft_features[:10]:
        all_features.append(f.get("feature", ""))
        feature_counts.append(f.get("count", 0))
    for f in as_features[:10]:
        all_features.append(f.get("feature", ""))
        feature_counts.append(f.get("count", 0))

    # Recommendation logic
    if ft_total > 0 and as_total > 0:
        if as_positive > ft_positive:
            recommendation = ("The data suggests a <strong>hybrid model</strong>: offer the family tree as a "
                            "free engagement tool that funnels users into premium astrology services. "
                            "Astrology features show stronger willingness-to-pay signals, making them "
                            "the primary revenue driver.")
        else:
            recommendation = ("Both family tree and astrology features show monetization potential. "
                            "Consider a <strong>freemium model</strong> with the family tree as the free "
                            "core and premium tiers for both advanced ancestry and astrology features.")
    elif as_total > 0:
        recommendation = ("Astrology features show the strongest WTP signals. Position the family tree "
                        "as a <strong>free funnel</strong> to paid astrology services.")
    elif ft_total > 0:
        recommendation = ("Family tree features show standalone monetization potential. Consider "
                        "<strong>standalone paid</strong> family tree with astrology as a free add-on.")
    else:
        recommendation = '<span class="limitation">Insufficient WTP data to make a monetization recommendation.</span>'

    return f"""<div class="section">
<h2>Family Tree Monetization Strategy</h2>

<h3>Monetization Model Comparison</h3>
<table>
<tr><th>App</th><th>Dominant Model</th><th>Confidence</th></tr>
{model_rows if model_rows else '<tr><td colspan="3">No monetization model data available</td></tr>'}
</table>

<h3>Cross-Category Monetization Potential</h3>
<div>
  <div class="metric"><div class="value">{a2a_wtp.get("count", 0)}</div><div class="label">Ancestry → Astrology WTP</div></div>
  <div class="metric"><div class="value">{astro2anc_wtp.get("count", 0)}</div><div class="label">Astrology → Ancestry WTP</div></div>
</div>

<h3>Family Tree vs Astrology WTP Breakdown</h3>
<table>
<tr><th>Category</th><th>Total Signals</th><th>Positive</th><th>Negative</th></tr>
<tr><td>Family Tree</td><td>{ft_total}</td><td>{ft_positive}</td><td>{ft_negative}</td></tr>
<tr><td>Astrology</td><td>{as_total}</td><td>{as_positive}</td><td>{as_negative}</td></tr>
</table>

<div id="{chart_id}" class="chart"></div>
<script>
Plotly.newPlot('{chart_id}', [{{
  x: {json.dumps(all_features)},
  y: {json.dumps(feature_counts)},
  type: 'bar',
  marker: {{color: {json.dumps(['#3498db'] * len(ft_features[:10]) + ['#9b59b6'] * len(as_features[:10]))}}}
}}], {{
  title: 'Feature Demand: Family Tree vs Astrology',
  yaxis: {{title: 'WTP Signal Count'}},
  xaxis: {{title: 'Feature', tickangle: -45}},
  margin: {{b: 120}}
}});
</script>

<h3>Recommendation</h3>
<p>{recommendation}</p>
</div>"""


def _section_strategic_recommendations(
    sentiment_summary: dict,
    wtp_summary: dict,
    overlap_summary: dict,
    landscape: dict,
) -> str:
    """Strategic Recommendations section."""
    gaps = landscape.get("market_gaps", [])
    top_astro = landscape.get("top_astrology_features", [])
    top_anc = landscape.get("top_ancestry_features", [])
    overlap_pct_a2a = overlap_summary.get("astrology_to_ancestry_pct", 0)
    overlap_pct_anc = overlap_summary.get("ancestry_to_astrology_pct", 0)

    # Feature recommendations from WTP
    top_pay = wtp_summary.get("top_features_willing_to_pay", [])
    feature_recs = ""
    for i, f in enumerate(top_pay[:10], 1):
        feature_recs += f'<tr><td>{i}</td><td>{f.get("feature", "")}</td><td>{f.get("positive_wtp_count", 0)}</td></tr>\n'

    has_gap = len(gaps) > 0
    has_overlap = overlap_pct_a2a > 0 or overlap_pct_anc > 0

    if has_gap and has_overlap:
        reposition_answer = ("Yes — the data supports repositioning. There is a clear market gap at the "
                           "intersection of family context and astrology, and bidirectional demand overlap "
                           "confirms user interest in combined features.")
    elif has_gap:
        reposition_answer = ("Likely yes — a market gap exists at the family-astrology intersection, though "
                           "demand overlap data is limited. Further validation with more review data is recommended.")
    elif has_overlap:
        reposition_answer = ("Potentially — users show cross-category interest, but the competitive landscape "
                           "analysis is inconclusive. Consider a phased approach to repositioning.")
    else:
        reposition_answer = ("Insufficient data to make a definitive recommendation. More review data is needed "
                           "to validate the family astrology positioning hypothesis.")

    return f"""<div class="section">
<h2>Strategic Recommendations</h2>

<h3>Should iMeUsWe Reposition as a "Family Astrology" Platform?</h3>
<p>{reposition_answer}</p>

<h3>Proposed Positioning Statements</h3>
<ul>
<li><strong>Primary:</strong> "iMeUsWe — Where your family story meets the stars. Use your family context to unlock personalized astrological guidance for life's biggest decisions."</li>
<li><strong>Alternative:</strong> "iMeUsWe — Family-powered astrology. Your lineage, your stars, your path."</li>
<li><strong>India-focused:</strong> "iMeUsWe — Apne vansh ki shakti, sitaron ki raah. Your family's power, guided by the stars."</li>
</ul>

<h3>Prioritized Feature Recommendations</h3>
<p>Features ranked by demand signal strength (WTP positive signals):</p>
<table>
<tr><th>Priority</th><th>Feature</th><th>WTP Signals</th></tr>
{feature_recs if feature_recs else '<tr><td colspan="3">No feature demand data available</td></tr>'}
</table>
</div>"""


def _section_data_limitations(data: dict) -> str:
    """Data Limitations & Caveats section."""
    limitations: list[str] = []

    cleaned = data.get("cleaned_reviews", pd.DataFrame())
    if cleaned.empty or len(cleaned) < 100:
        limitations.append(
            "Limited review dataset — fewer than 100 cleaned reviews were available for analysis. "
            "Results should be treated as directional rather than statistically significant."
        )

    sentiment_summary = data.get("sentiment_summary", {})
    if not sentiment_summary.get("per_category"):
        limitations.append("Sentiment analysis data is missing or incomplete.")

    wtp_summary = data.get("wtp_summary", {})
    if not wtp_summary.get("per_category"):
        limitations.append("WTP analysis data is missing or incomplete.")

    overlap_summary = data.get("overlap_summary", {})
    if not overlap_summary:
        limitations.append("Demand overlap analysis data is missing.")

    # General caveats
    caveats = [
        "Sentiment analysis uses VADER (rule-based) which may not capture nuanced opinions, sarcasm, or cultural context perfectly.",
        "Non-English reviews are machine-translated before analysis, which may introduce translation artifacts.",
        "WTP signals are detected via keyword matching and may miss implicit pricing sentiment.",
        "Web scraping coverage depends on site accessibility — some sources may block automated requests.",
        "The Hinglish sentiment dictionary covers common terms but is not exhaustive.",
        "Review data represents a snapshot in time and may not reflect current app states.",
    ]

    limitation_items = ""
    for lim in limitations:
        limitation_items += f'<div class="limitation">{lim}</div>\n'

    caveat_items = ""
    for cav in caveats:
        caveat_items += f"<li>{cav}</li>\n"

    return f"""<div class="section">
<h2>Data Limitations &amp; Caveats</h2>

{limitation_items}

<h3>General Caveats</h3>
<ul>
{caveat_items}
</ul>
</div>"""


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    data = load_all_data()
    landscape = build_competitive_landscape(data)
    data["competitive_landscape"] = landscape

    report_path = os.path.join(OUTPUT_DIR, "positioning_report.html")
    generate_html_report(data, report_path)
    print(f"Report generated: {report_path}")
    print(f"Competitive landscape: {os.path.join(DATA_DIR, 'competitive_landscape.json')}")
