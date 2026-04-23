# 📈 News Alpha Engine
### AI-Powered Stock Market Intelligence System

> Processes **800+ daily news articles** from NSE/BSE markets into **actionable investment signals** using Claude AI, supply-chain knowledge graphs, and quantitative scoring models.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         NEWS ALPHA ENGINE                               │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  RSS Feeds   │  │  BSE Filings │  │  NewsAPI.org │  │  Web Crawl │ │
│  │  (12 feeds)  │  │  (Corporate) │  │  (5 queries) │  │  (scraper) │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
│         └─────────────────┴─────────────────┴────────────────┘         │
│                                    │ 800+ articles/day                  │
│                            ┌───────▼────────┐                          │
│                            │  Ingestion     │  Dedup · Filter · Save   │
│                            │  Engine        │  Target: < 5 min         │
│                            └───────┬────────┘                          │
│                                    │                                    │
│                            ┌───────▼────────┐                          │
│                            │  LLM Analysis  │  Claude Sonnet           │
│                            │  Engine        │  20 concurrent requests  │
│                            │                │  Batch size: 10          │
│                            └───────┬────────┘  Target: < 3 min        │
│                                    │                                    │
│              ┌─────────────────────┼─────────────────────┐            │
│              │                     │                     │            │
│     ┌────────▼──────┐    ┌─────────▼──────┐    ┌────────▼──────┐    │
│     │  Knowledge    │    │  Event         │    │  Financial    │    │
│     │  Graph        │    │  Detection     │    │  Impact       │    │
│     │  (networkx)   │    │  Engine        │    │  Model        │    │
│     └────────┬──────┘    └─────────┬──────┘    └────────┬──────┘    │
│              └─────────────────────┼─────────────────────┘            │
│                                    │                                    │
│                            ┌───────▼────────┐                          │
│                            │  Scoring &     │  5-factor weighted       │
│                            │  Ranking       │  score (0-100)           │
│                            │  Engine        │  Daily top-20 ranking    │
│                            └───────┬────────┘                          │
│                                    │                                    │
│              ┌─────────────────────┼─────────────────────┐            │
│              │                     │                     │            │
│     ┌────────▼──────┐    ┌─────────▼──────┐    ┌────────▼──────┐    │
│     │  FastAPI      │    │  Streamlit     │    │  JSON Report  │    │
│     │  REST API     │    │  Dashboard     │    │  (daily file) │    │
│     │  :8000        │    │  :8501         │    │  data/reports/│    │
│     └───────────────┘    └───────────────┘    └───────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
news-alpha-engine/
│
├── main.py                    # CLI entry point (pipeline/server/dashboard)
├── config.py                  # Central configuration (env-based)
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker container definition
├── docker-compose.yml         # Full stack: Postgres + MongoDB + Redis + API + Dashboard
├── .env.example               # Environment variables template
│
├── models/
│   ├── database.py            # SQLAlchemy ORM models (all 12 tables)
│   ├── db_session.py          # Async session factory
│   ├── knowledge_graph_seed.py # Seed data: 17 companies, 35 industries, 12 commodities
│   └── __init__.py
│
├── ingestion/
│   ├── scraper.py             # RSS + BSE + NewsAPI ingestion engine
│   └── __init__.py
│
├── analysis/
│   ├── llm_engine.py          # Claude AI analysis engine (async batch)
│   └── __init__.py
│
├── graph/
│   ├── knowledge_graph.py     # NetworkX market knowledge graph
│   ├── event_engine.py        # Event classification + impact propagation
│   └── __init__.py
│
├── scoring/
│   ├── financial_model.py     # Financial impact + scoring + ranking engine
│   └── __init__.py
│
├── api/
│   ├── main.py                # FastAPI REST API (15+ endpoints)
│   └── __init__.py
│
├── pipeline/
│   ├── orchestrator.py        # Master pipeline + APScheduler cron jobs
│   └── __init__.py
│
├── dashboard/
│   ├── app.py                 # Streamlit interactive dashboard
│   └── __init__.py
│
├── scripts/
│   ├── seed_db.py             # One-time DB seeding with knowledge graph
│   └── init.sql               # PostgreSQL extensions + performance tuning
│
├── alembic/
│   └── env.py                 # Async Alembic migration config
│
├── tests/
│   ├── test_pipeline.py       # Full test suite (50+ tests, 7 test classes)
│   └── __init__.py
│
└── data/
    ├── raw/                   # Raw ingested articles
    ├── processed/             # Analyzed articles
    └── reports/               # Daily JSON reports
```

---

## ⚡ Quick Start

### Option A: Docker (Recommended)
```bash
# 1. Clone and configure
git clone <repo>
cd news-alpha-engine
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# 2. Start all services
docker-compose up -d

# 3. Seed the database (first time only)
docker exec newsalpha_api python scripts/seed_db.py

# 4. Run the pipeline manually
docker exec newsalpha_api python main.py pipeline

# Access:
# API:       http://localhost:8000/docs
# Dashboard: http://localhost:8501
```

### Option B: Local Development
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start infrastructure
docker-compose up -d postgres mongodb redis

# 3. Configure environment
cp .env.example .env
# Set ANTHROPIC_API_KEY, POSTGRES_URL, etc.

# 4. Initialize database
python scripts/seed_db.py

# 5. Run pipeline
python main.py pipeline

# 6. Start API (separate terminal)
python main.py server

# 7. Start dashboard (separate terminal)
python main.py dashboard
```

---

## 🕐 Daily Pipeline Schedule (IST)

| Time  | Stage             | Description                          | Duration |
|-------|-------------------|--------------------------------------|----------|
| 08:00 | Ingestion         | Fetch 800+ articles from all sources | ~3 min   |
| 08:10 | LLM Analysis      | Claude analyzes each article          | ~4 min   |
| 08:20 | Event Detection   | Classify events, propagate impact    | ~30 sec  |
| 08:25 | Financial Model   | Compute revenue/EPS/price impact     | ~30 sec  |
| 08:30 | Scoring & Ranking | Generate daily top-20 lists          | ~10 sec  |
| 08:35 | Dashboard Update  | Refresh Streamlit dashboard          | instant  |
| 12:00 | Midday Update     | 200 new articles since morning       | ~2 min   |
| 15:30 | EOD Update        | Post-market news                     | ~2 min   |

**Total daily pipeline runtime: < 8 minutes for 800+ articles**

---

## 🧠 LLM Analysis Output Format

Each article is analyzed into this structured JSON:

```json
{
  "ai_summary": "JSW Steel faces margin headwinds as iron ore rises 18%...",
  "event_type": "pricing_change",
  "sentiment": "bearish",
  "bullish_score": 1.5,
  "bearish_score": 8.0,
  "confidence": 0.87,
  "companies_mentioned": [
    { "name": "JSW Steel", "ticker": "JSWSTEEL", "role": "primary",
      "impact": "negative", "rationale": "Iron ore is 42% of production cost" }
  ],
  "industries_affected": [
    { "name": "Steel", "direction": "negative", "magnitude": 8, "rationale": "Input cost shock" }
  ],
  "financial_impact": {
    "revenue_impact_pct": 0,
    "margin_impact_bps": -420,
    "eps_impact_pct": -18,
    "price_impact_pct": -12,
    "impact_horizon": "3_months",
    "impact_rationale": "Iron ore ×42% cost share → EBITDA margin -420bps → EPS -18%"
  },
  "second_order_effects": [
    { "industry": "Automobile", "direction": "negative", "hop": 2,
      "mechanism": "Steel ↑ → Auto input cost ↑ → Auto margin compression",
      "magnitude": 3.2 }
  ],
  "final_investment_view": {
    "recommendation": "Sell",
    "time_horizon": "3_months",
    "conviction": "High",
    "rationale": "Iron ore spike will compress EBITDA 400+ bps; EPS estimate cuts likely."
  }
}
```

---

## 📊 Scoring Formula

```
Composite Score (0–100) = 
    Revenue Impact Score  × 30%   +
    Margin Impact Score   × 25%   +
    Industry Shift Score  × 20%   +
    Regulatory Score      × 15%   +
    Sentiment Score       × 10%

Signal Classification:
  > 70 → BULLISH  (Strong Buy / Buy)
  < 30 → BEARISH  (Sell / Strong Sell)
  else → NEUTRAL  (Hold)
```

---

## 🕸️ Knowledge Graph

The market knowledge graph contains:

| Entity | Count | Description |
|--------|-------|-------------|
| Companies | 17 | Tata Motors, RIL, TCS, JSW Steel, HDFC Bank, etc. |
| Industries | 35 | Auto, Steel, IT, Banking, Pharma, Cement, etc. |
| Sectors | 11 | Energy, Materials, Financials, Technology, etc. |
| Commodities | 12 | Iron Ore, Crude Oil, Lithium, Copper, etc. |
| Relationships | 20+ | Supply-chain impact coefficients |

**Example propagation chain:**
```
Iron Ore ↑20%
  → Steel margins ↓420bps (direct, impact=0.45)
  → Auto input costs ↑ (hop=2, impact=0.45×0.18)
  → Capital Goods costs ↑ (hop=2, impact=0.45×0.15)
  → Real Estate costs ↑ (hop=2, impact=0.45×0.12)
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | System health + pipeline status |
| `POST` | `/pipeline/run` | Trigger pipeline (async) |
| `GET`  | `/pipeline/status` | Current pipeline status |
| `GET`  | `/rankings/today?direction=bullish` | Top-20 bullish stocks |
| `GET`  | `/rankings/today?direction=bearish` | Top-20 bearish stocks |
| `GET`  | `/rankings/heatmap` | Industry sentiment heatmap |
| `POST` | `/analyze/article` | Analyze a single article on-demand |
| `GET`  | `/graph/company/{ticker}` | Company + peers from knowledge graph |
| `POST` | `/graph/commodity-shock` | Simulate commodity price shock |
| `GET`  | `/graph/stats` | Knowledge graph statistics |
| `GET`  | `/news/latest` | Latest analyzed articles |
| `GET`  | `/news/themes` | Today's theme clusters |
| `GET`  | `/score/{ticker}` | Today's score for a stock |
| `GET`  | `/scores/all` | All daily stock scores |

---

## ⚡ Performance: 800 Articles in < 3 Minutes

```python
# Async batch processing architecture:

# 800 articles ÷ batch_size(10) = 80 batches
# 80 batches × max_concurrent(20) = up to 20 batches running in parallel
# Each Claude call: ~2-4 seconds
# Total: 80 batches / 20 concurrent × 3s avg = ~12s per wave
# 800 articles total time: ~2.5 minutes

# Key techniques:
# 1. asyncio.Semaphore(20) — limits concurrent Claude calls
# 2. asyncio.gather() — true parallel execution within batch
# 3. Exponential backoff retry for rate limits (tenacity)
# 4. Input truncation to 3000 chars per article (token efficiency)
# 5. Filtering: skip articles < 30 words before LLM call
```

---

## 🧪 Running Tests

```bash
# Full test suite
pytest tests/ -v

# Specific test class
pytest tests/test_pipeline.py::TestKnowledgeGraph -v

# With coverage
pytest tests/ -v --cov=. --cov-report=html

# Just graph tests (no API needed)
pytest tests/test_pipeline.py::TestKnowledgeGraph tests/test_pipeline.py::TestEventDetection -v
```

---

## 📋 15-Section Investment Report Format

Each analyzed article generates a full report:

1. **News Identification** — Source, date, event type
2. **Executive Summary** — 2-3 sentence AI summary
3. **Bullish/Bearish Score** — Quantified 0-10 scores
4. **Actionable Takeaways** — Buy/Sell recommendation + catalysts
5. **Industry Structure Analysis** — Competitive dynamics
6. **Financial Impact Analysis** — Revenue, EBITDA, EPS estimates
7. **Competitive Position vs Peers** — Winners vs losers
8. **Relative Stock Positioning** — Primary vs secondary beneficiaries
9. **Second-Order Industry Effects** — Propagation chain
10. **Input/Output Pricing Impact** — Commodity linkages
11. **Stock Price Impact Model** — EPS × PE methodology
12. **Long-Term Strategic Implications** — 12-24 month view
13. **Final Investment View** — Rec + conviction + time horizon
14. **Key Data Points** — Themes and facts
15. **Monitoring Indicators** — KPIs to track

---

## 🛡️ Production Considerations

- **API keys**: Rotate monthly, use AWS Secrets Manager or Vault
- **Rate limits**: Claude Sonnet: 4,000 requests/min (Tier 4). Semaphore(20) is safe.
- **DB indexes**: Covered indexes on `published_at`, `source`, `status`
- **Caching**: Redis TTL=300s for rankings and heatmap endpoints
- **Monitoring**: Loguru → ELK stack or CloudWatch
- **Cost estimate**: 800 articles × 4000 tokens avg × $3/MTok ≈ **$9.60/day**
