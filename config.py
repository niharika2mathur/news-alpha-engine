# ============================================================
# config.py – Central Configuration (Pydantic v2 compatible)
# ============================================================

from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    APP_NAME: str = "News Alpha Engine"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── LLM ──────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.1
    LLM_BATCH_SIZE: int = 10
    LLM_MAX_CONCURRENT: int = 20

    # ── Databases ─────────────────────────────────────────────
    POSTGRES_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/newsalpha"
    MONGODB_URL: str = "mongodb://localhost:27017/newsalpha"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── News APIs ─────────────────────────────────────────────
    NEWSAPI_KEY: str = ""
    ALPHAVANTAGE_KEY: str = ""
    BSE_API_URL: str = "https://api.bseindia.com/BseIndiaAPI/api"
    NSE_API_URL: str = "https://www.nseindia.com/api"

    # ── RSS Feeds ─────────────────────────────────────────────
    RSS_FEEDS: list[str] = [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/INbusinessNews",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms",
        "https://www.moneycontrol.com/rss/marketreports.xml",
        "https://www.moneycontrol.com/rss/business.xml",
        "https://www.livemint.com/rss/markets",
        "https://www.livemint.com/rss/companies",
        "https://www.business-standard.com/rss/markets-106.rss",
        "https://www.business-standard.com/rss/economy-policy-10106.rss",
        "https://feeds.feedburner.com/ndtvprofit-latest",
        "https://www.financialexpress.com/market/feed/",
    ]

    # ── Scoring Weights ───────────────────────────────────────
    WEIGHT_REVENUE: float = 0.30
    WEIGHT_MARGIN: float = 0.25
    WEIGHT_INDUSTRY_SHIFT: float = 0.20
    WEIGHT_REGULATORY: float = 0.15
    WEIGHT_SENTIMENT: float = 0.10

    # ── Pipeline Schedule (cron, IST) ─────────────────────────
    INGESTION_CRON: str = "0 8 * * 1-5"
    ANALYSIS_CRON: str = "10 8 * * 1-5"
    SCORING_CRON: str = "20 8 * * 1-5"
    RANKING_CRON: str = "30 8 * * 1-5"
    DASHBOARD_CRON: str = "35 8 * * 1-5"

    # ── Paths ─────────────────────────────────────────────────
    DATA_DIR: str = "data"
    RAW_DIR: str = "data/raw"
    PROCESSED_DIR: str = "data/processed"
    REPORTS_DIR: str = "data/reports"


settings = Settings()
