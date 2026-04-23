# ============================================================
# dashboard/app.py – Streamlit Interactive Dashboard
# Real-time market intelligence visualization
# ============================================================

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import sys
import os

# Must be first Streamlit command
import streamlit as st
st.set_page_config(
    page_title="News Alpha Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Styling ───────────────────────────────────────────────────────────────────────

BULL_COLOR = "#00C853"
BEAR_COLOR = "#D50000"
NEUTRAL_COLOR = "#1565C0"
BG_DARK = "#0E1117"
CARD_BG = "#1E2130"

st.markdown("""
<style>
    .metric-card {
        background: #1E2130;
        border-radius: 12px;
        padding: 16px 20px;
        border-left: 4px solid;
        margin-bottom: 12px;
    }
    .bull-card { border-color: #00C853; }
    .bear-card { border-color: #D50000; }
    .neutral-card { border-color: #1565C0; }
    .stock-row { 
        display: flex; justify-content: space-between; 
        padding: 8px 0; border-bottom: 1px solid #2D3250;
    }
    .signal-badge {
        padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;
    }
    .bull-badge { background: #00C85320; color: #00C853; }
    .bear-badge { background: #D5000020; color: #D50000; }
    .section-header { font-size: 20px; font-weight: 700; margin: 20px 0 12px; }
</style>
""", unsafe_allow_html=True)


# ── Helper Functions ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_latest_report():
    """Load the most recent daily report JSON."""
    reports_dir = "data/reports"
    if not os.path.exists(reports_dir):
        return None

    report_files = sorted([
        f for f in os.listdir(reports_dir) if f.startswith("report_") and f.endswith(".json")
    ], reverse=True)

    if not report_files:
        return None

    with open(os.path.join(reports_dir, report_files[0])) as f:
        return json.load(f)


def get_demo_data():
    """Generate demo data when no real data is available."""
    return {
        "metadata": {"articles_ingested": 847, "articles_analyzed": 812, "elapsed_seconds": 234},
        "rankings": {
            "date": datetime.now().isoformat(),
            "bullish": [
                {"rank": 1, "ticker": "RELIANCE", "company_name": "Reliance Industries", "composite_score": 82.5, "signal": "bullish", "signal_strength": 0.65, "price_impact_pct": 4.2, "article_count": 8, "key_catalyst": "New green energy capex of ₹75,000 Cr announced", "industry": "OGR"},
                {"rank": 2, "ticker": "TCS", "company_name": "TCS", "composite_score": 78.3, "signal": "bullish", "signal_strength": 0.57, "price_impact_pct": 3.1, "article_count": 5, "key_catalyst": "Record $3.2B deal win in BFSI segment", "industry": "IT"},
                {"rank": 3, "ticker": "ULTRACEMCO", "company_name": "UltraTech Cement", "composite_score": 76.1, "signal": "bullish", "signal_strength": 0.52, "price_impact_pct": 2.8, "article_count": 4, "key_catalyst": "Govt infrastructure spend ₹11.1L Cr – cement demand surge", "industry": "CEMENT"},
                {"rank": 4, "ticker": "BHARTIARTL", "company_name": "Bharti Airtel", "composite_score": 73.8, "signal": "bullish", "signal_strength": 0.48, "price_impact_pct": 2.3, "article_count": 6, "key_catalyst": "ARPU up 12% on tariff hike; subscriber adds beat estimates", "industry": "TELCO"},
                {"rank": 5, "ticker": "SUNPHARMA", "company_name": "Sun Pharmaceuticals", "composite_score": 71.4, "signal": "bullish", "signal_strength": 0.43, "price_impact_pct": 1.9, "article_count": 3, "key_catalyst": "USFDA approves key specialty drug – $500M market opportunity", "industry": "PHARMA"},
                {"rank": 6, "ticker": "LT", "company_name": "Larsen & Toubro", "composite_score": 69.9, "signal": "bullish", "signal_strength": 0.40, "price_impact_pct": 1.7, "article_count": 4, "key_catalyst": "₹8,500 Cr defence order win for ship systems", "industry": "CAPGD"},
                {"rank": 7, "ticker": "HDFCBANK", "company_name": "HDFC Bank", "composite_score": 67.2, "signal": "bullish", "signal_strength": 0.34, "price_impact_pct": 1.4, "article_count": 7, "key_catalyst": "NIM stable at 3.4%; credit growth 16% YoY beats estimates", "industry": "BANK"},
            ],
            "bearish": [
                {"rank": 1, "ticker": "TATASTEEL", "company_name": "Tata Steel", "composite_score": 22.1, "signal": "bearish", "signal_strength": 0.56, "price_impact_pct": -5.3, "article_count": 6, "key_catalyst": "UK Port Talbot closure costs £1.3B; EU steel overcapacity fears", "industry": "STEEL"},
                {"rank": 2, "ticker": "OLAELEC", "company_name": "Ola Electric", "composite_score": 25.4, "signal": "bearish", "signal_strength": 0.49, "price_impact_pct": -4.1, "article_count": 4, "key_catalyst": "Lithium prices +18%; battery cost impact -350 bps on margins", "industry": "EV"},
                {"rank": 3, "ticker": "JSWSTEEL", "company_name": "JSW Steel", "composite_score": 28.7, "signal": "bearish", "signal_strength": 0.43, "price_impact_pct": -3.2, "article_count": 5, "key_catalyst": "Iron ore prices surge; coking coal +12% – margin compression", "industry": "STEEL"},
                {"rank": 4, "ticker": "HINDUNILVR", "company_name": "Hindustan Unilever", "composite_score": 31.5, "signal": "bearish", "signal_strength": 0.37, "price_impact_pct": -2.8, "article_count": 3, "key_catalyst": "Palm oil +15% hurts food margins; rural demand slowdown", "industry": "FMCG"},
                {"rank": 5, "ticker": "TATAMOTORS", "company_name": "Tata Motors", "composite_score": 33.8, "signal": "bearish", "signal_strength": 0.32, "price_impact_pct": -2.1, "article_count": 5, "key_catalyst": "JLR supply chain disruption; steel cost headwinds -180bps margin", "industry": "AUTO"},
            ],
            "industry_heatmap": {
                "IT": {"avg_score": 71.2, "count": 5, "signal": "bullish"},
                "BANK": {"avg_score": 65.8, "count": 6, "signal": "bullish"},
                "CEMENT": {"avg_score": 72.1, "count": 3, "signal": "bullish"},
                "PHARMA": {"avg_score": 68.5, "count": 4, "signal": "bullish"},
                "TELCO": {"avg_score": 70.3, "count": 2, "signal": "bullish"},
                "CAPGD": {"avg_score": 67.9, "count": 4, "signal": "bullish"},
                "STEEL": {"avg_score": 25.4, "count": 3, "signal": "bearish"},
                "EV": {"avg_score": 28.1, "count": 2, "signal": "bearish"},
                "FMCG": {"avg_score": 38.7, "count": 4, "signal": "bearish"},
                "AUTO": {"avg_score": 35.2, "count": 3, "signal": "bearish"},
                "OGR": {"avg_score": 78.5, "count": 2, "signal": "bullish"},
                "REALT": {"avg_score": 55.3, "count": 2, "signal": "neutral"},
            },
            "summary": {
                "total_stocks_scored": 47,
                "bullish_count": 22,
                "bearish_count": 15,
                "neutral_count": 10,
                "market_breadth": "22/47 bullish (46.8%)"
            }
        },
        "themes": [
            {"theme": "Infra Push", "article_count": 42},
            {"theme": "Rate Environment", "article_count": 38},
            {"theme": "EV Transition", "article_count": 31},
            {"theme": "IT Spending", "article_count": 28},
            {"theme": "Steel/Metals Cycle", "article_count": 25},
            {"theme": "Pharma Regulatory", "article_count": 19},
            {"theme": "FMCG Demand", "article_count": 16},
            {"theme": "Renewable Energy", "article_count": 22},
        ]
    }


# ── Main Dashboard ────────────────────────────────────────────────────────────────

def main():
    # ── Sidebar ───────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/stock-market.png", width=60)
        st.title("News Alpha Engine")
        st.caption("AI Market Intelligence System")
        st.divider()

        page = st.radio(
            "Navigation",
            ["📊 Daily Dashboard", "🐂 Top Bullish", "🐻 Top Bearish",
             "🌡️ Industry Heatmap", "🔍 Article Analyzer", "🕸️ Knowledge Graph"],
            label_visibility="collapsed"
        )

        st.divider()
        st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %H:%M IST')}")

        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        use_demo = st.toggle("Use Demo Data", value=True)

    # Load data
    if use_demo:
        data = get_demo_data()
    else:
        data = load_latest_report()
        if not data:
            st.warning("No report data found. Run the pipeline first or enable demo mode.")
            data = get_demo_data()

    rankings = data.get("rankings", {})
    metadata = data.get("metadata", {})
    themes = data.get("themes", [])

    # ── Page Router ───────────────────────────────────────────────────────────────

    if "Dashboard" in page:
        render_dashboard(rankings, metadata, themes)
    elif "Bullish" in page:
        render_ranked_stocks(rankings.get("bullish", []), "bullish")
    elif "Bearish" in page:
        render_ranked_stocks(rankings.get("bearish", []), "bearish")
    elif "Heatmap" in page:
        render_heatmap(rankings.get("industry_heatmap", {}))
    elif "Analyzer" in page:
        render_article_analyzer()
    elif "Knowledge" in page:
        render_knowledge_graph()


def render_dashboard(rankings: dict, metadata: dict, themes: list):
    st.title("📊 Daily Market Intelligence Dashboard")
    st.caption(f"Report Date: {datetime.now().strftime('%A, %d %B %Y')}")

    # ── KPI Row ───────────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    summary = rankings.get("summary", {})

    with c1:
        st.metric("Articles Processed", f"{metadata.get('articles_ingested', 0):,}")
    with c2:
        st.metric("Articles Analyzed", f"{metadata.get('articles_analyzed', 0):,}")
    with c3:
        st.metric("Stocks Scored", summary.get("total_stocks_scored", 0))
    with c4:
        st.metric("🐂 Bullish", summary.get("bullish_count", 0),
                  delta=f"+{summary.get('bullish_count', 0)}")
    with c5:
        st.metric("🐻 Bearish", summary.get("bearish_count", 0),
                  delta=f"-{summary.get('bearish_count', 0)}", delta_color="inverse")

    st.divider()

    # ── Two-Column Layout ─────────────────────────────────────────────────────────
    col_bull, col_bear = st.columns(2)

    with col_bull:
        st.markdown("### 🐂 Top Bullish Stocks")
        bullish = rankings.get("bullish", [])
        for stock in bullish[:7]:
            score_bar = stock["composite_score"] / 100
            st.markdown(f"""
            <div class="metric-card bull-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-weight:700; font-size:16px;">#{stock['rank']} {stock['ticker']}</span>
                        <span style="color:#aaa; font-size:12px; margin-left:8px;">{stock['company_name']}</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:#00C853; font-weight:bold; font-size:18px;">{stock['composite_score']:.0f}</span>
                        <span style="color:#00C853; font-size:12px;"> / 100</span>
                    </div>
                </div>
                <div style="font-size:12px; color:#aaa; margin-top:6px;">{stock['key_catalyst'][:80]}...</div>
                <div style="margin-top:8px; display:flex; gap:10px;">
                    <span style="color:#00C853; font-size:12px;">📈 +{stock.get('price_impact_pct', 0):.1f}%</span>
                    <span style="color:#aaa; font-size:12px;">📰 {stock['article_count']} articles</span>
                    <span style="color:#aaa; font-size:12px;">🏭 {stock['industry']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_bear:
        st.markdown("### 🐻 Top Bearish Stocks")
        bearish = rankings.get("bearish", [])
        for stock in bearish[:7]:
            st.markdown(f"""
            <div class="metric-card bear-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-weight:700; font-size:16px;">#{stock['rank']} {stock['ticker']}</span>
                        <span style="color:#aaa; font-size:12px; margin-left:8px;">{stock['company_name']}</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:#D50000; font-weight:bold; font-size:18px;">{stock['composite_score']:.0f}</span>
                        <span style="color:#D50000; font-size:12px;"> / 100</span>
                    </div>
                </div>
                <div style="font-size:12px; color:#aaa; margin-top:6px;">{stock['key_catalyst'][:80]}...</div>
                <div style="margin-top:8px; display:flex; gap:10px;">
                    <span style="color:#D50000; font-size:12px;">📉 {stock.get('price_impact_pct', 0):.1f}%</span>
                    <span style="color:#aaa; font-size:12px;">📰 {stock['article_count']} articles</span>
                    <span style="color:#aaa; font-size:12px;">🏭 {stock['industry']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── Theme Bubbles ──────────────────────────────────────────────────────────────
    st.markdown("### 🗞️ Today's Market Themes")
    if themes:
        df_themes = pd.DataFrame(themes)
        fig = px.treemap(
            df_themes,
            path=["theme"],
            values="article_count",
            color="article_count",
            color_continuous_scale=["#1565C0", "#00C853"],
            title="Theme Clusters by Article Volume"
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(t=40, b=0, l=0, r=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Mini Heatmap ──────────────────────────────────────────────────────────────
    st.markdown("### 🌡️ Industry Heatmap (Snapshot)")
    heatmap = rankings.get("industry_heatmap", {})
    if heatmap:
        df = pd.DataFrame([
            {"Industry": k, "Score": v["avg_score"], "Signal": v["signal"], "Count": v["count"]}
            for k, v in heatmap.items()
        ])
        df = df.sort_values("Score", ascending=False)

        fig = px.bar(
            df, x="Industry", y="Score",
            color="Score",
            color_continuous_scale=["#D50000", "#FFA000", "#00C853"],
            range_color=[0, 100],
            text="Score",
        )
        fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        fig.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.5)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(14,17,23,0.5)",
            height=350,
            showlegend=False,
            margin=dict(t=20, b=40),
            yaxis=dict(range=[0, 110]),
            xaxis_title="",
            yaxis_title="Composite Score (0–100)",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_ranked_stocks(stocks: list, direction: str):
    color = BULL_COLOR if direction == "bullish" else BEAR_COLOR
    emoji = "🐂" if direction == "bullish" else "🐻"
    st.title(f"{emoji} Top {direction.capitalize()} Stocks")

    if not stocks:
        st.info("No data available. Run the pipeline first.")
        return

    # Signal strength chart
    df = pd.DataFrame(stocks)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["ticker"], y=df["composite_score"],
        marker_color=color,
        text=df["composite_score"].round(1),
        textposition="outside",
        name="Composite Score"
    ))
    fig.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.4)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,17,23,0.5)",
        height=320,
        margin=dict(t=20, b=40),
        showlegend=False,
        yaxis=dict(range=[0, 110]),
        xaxis_title="",
        yaxis_title="Composite Score",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detailed table
    st.dataframe(
        df[["rank", "ticker", "company_name", "composite_score", "signal_strength",
            "price_impact_pct", "article_count", "key_catalyst"]].rename(columns={
            "rank": "Rank", "ticker": "Ticker", "company_name": "Company",
            "composite_score": "Score", "signal_strength": "Strength",
            "price_impact_pct": "Price Impact %", "article_count": "Articles",
            "key_catalyst": "Key Catalyst"
        }),
        use_container_width=True,
        hide_index=True,
    )


def render_heatmap(heatmap: dict):
    st.title("🌡️ Industry Sentiment Heatmap")

    df = pd.DataFrame([
        {"Industry": k, "Score": v["avg_score"], "Articles": v["count"],
         "Signal": v["signal"]}
        for k, v in heatmap.items()
    ])

    fig = go.Figure(go.Treemap(
        labels=df["Industry"],
        values=df["Articles"],
        parents=[""] * len(df),
        customdata=df[["Score", "Signal"]],
        texttemplate="<b>%{label}</b><br>Score: %{customdata[0]:.0f}<br>%{customdata[1]}",
        marker=dict(
            colors=df["Score"],
            colorscale=[[0, "#D50000"], [0.5, "#FFA000"], [1, "#00C853"]],
            cmin=0, cmid=50, cmax=100,
            colorbar=dict(title="Score")
        ),
    ))
    fig.update_layout(height=600, margin=dict(t=20, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    st.dataframe(
        df.sort_values("Score", ascending=False).reset_index(drop=True),
        use_container_width=True
    )


def render_article_analyzer():
    st.title("🔍 On-Demand Article Analyzer")
    st.caption("Paste any news article to get instant AI investment analysis")

    title = st.text_input("Article Title", placeholder="e.g. RBI cuts repo rate by 25bps amid softening inflation")
    content = st.text_area("Article Content", height=200,
                           placeholder="Paste the full article text here...")
    source = st.text_input("Source", value="Manual Input")

    if st.button("🧠 Analyze with AI", type="primary", use_container_width=True):
        if not title or not content:
            st.error("Please provide both title and content")
            return

        with st.spinner("Analyzing article with Claude AI..."):
            try:
                import requests
                resp = requests.post(
                    "http://localhost:8000/analyze/article",
                    json={"title": title, "content": content, "source": source},
                    timeout=60
                )
                if resp.status_code == 200:
                    result = resp.json()
                    intel = result["intelligence"]
                    report = result["full_report"]

                    # Score display
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("🐂 Bullish Score", f"{intel['bullish_score']:.1f}/10")
                    with c2:
                        st.metric("🐻 Bearish Score", f"{intel['bearish_score']:.1f}/10")
                    with c3:
                        sentiment = intel["sentiment"].upper()
                        color_map = {"BULLISH": "green", "BEARISH": "red", "NEUTRAL": "blue"}
                        st.metric("Sentiment", sentiment)

                    st.divider()

                    # Report sections
                    with st.expander("📋 Executive Summary", expanded=True):
                        st.write(report.get("executive_summary", ""))

                    with st.expander("💹 Financial Impact"):
                        fi = report.get("financial_impact", {})
                        st.json(fi)

                    with st.expander("🏭 Industry Effects"):
                        effects = report.get("second_order_effects", [])
                        if effects:
                            df = pd.DataFrame(effects)
                            st.dataframe(df, use_container_width=True)

                    with st.expander("🎯 Investment View"):
                        view = report.get("final_investment_view", {})
                        st.json(view)

                    with st.expander("📊 Full Report (JSON)"):
                        st.json(report)
                else:
                    st.error(f"API error: {resp.status_code} – {resp.text}")
            except Exception as e:
                st.error(f"Could not connect to API. Make sure the server is running.\nError: {e}")
                st.info("Start the API server with: `uvicorn api.main:app --port 8000`")


def render_knowledge_graph():
    st.title("🕸️ Market Knowledge Graph")
    st.caption("Industry supply chain relationships and commodity impacts")

    from app.graph.knowledge_graph import get_graph
    graph = get_graph()
    stats = graph.get_stats()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Nodes", stats["nodes"])
    c2.metric("Companies", stats["companies"])
    c3.metric("Industries", stats["industries"])
    c4.metric("Edges", stats["edges"])

    st.divider()

    # Commodity shock simulator
    st.markdown("### 🛢️ Commodity Price Shock Simulator")
    col1, col2 = st.columns([2, 1])
    with col1:
        commodity = st.selectbox("Commodity", [
            "Iron Ore", "Coking Coal", "Crude Oil (Brent)", "Lithium",
            "Aluminium", "Copper", "Natural Gas", "Urea", "Palm Oil"
        ])
    with col2:
        price_change = st.slider("Price Change %", -30, 30, 10)

    if st.button("🔮 Simulate Shock", type="primary"):
        effects = graph.propagate_commodity_shock(commodity, price_change)

        if effects:
            df = pd.DataFrame([{
                "Industry": e.target,
                "Direction": e.direction,
                "Magnitude": e.magnitude,
                "Hop": e.hop,
                "Mechanism": e.mechanism[:100] + "..."
            } for e in effects[:15]])

            colors = df["Direction"].map({"positive": BULL_COLOR, "negative": BEAR_COLOR, "neutral": NEUTRAL_COLOR})

            fig = px.bar(
                df, x="Industry", y="Magnitude",
                color="Direction",
                color_discrete_map={"positive": BULL_COLOR, "negative": BEAR_COLOR, "neutral": NEUTRAL_COLOR},
                title=f"{commodity} {price_change:+.0f}% → Industry Impact Propagation",
                text="Magnitude"
            )
            fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(14,17,23,0.5)",
                height=350, margin=dict(t=50, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info(f"No impact found for {commodity}. Check commodity name.")


if __name__ == "__main__":
    main()
