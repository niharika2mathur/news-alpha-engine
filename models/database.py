# ============================================================
# models/database.py – SQLAlchemy ORM Models + Schema
# ============================================================

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text,
    ForeignKey, JSON, Index, Enum as SAEnum, BigInteger
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# ── Enums ──────────────────────────────────────────────────────────────────────

class EventType(str, enum.Enum):
    REGULATION = "regulation"
    DEMAND_SHOCK = "demand_shock"
    SUPPLY_SHOCK = "supply_shock"
    PRICING_CHANGE = "pricing_change"
    CAPACITY_EXPANSION = "capacity_expansion"
    CORPORATE_ACTION = "corporate_action"
    MACRO_EVENT = "macro_event"
    EARNINGS = "earnings"
    ANALYST_ACTION = "analyst_action"
    MERGER_ACQUISITION = "merger_acquisition"
    MANAGEMENT_CHANGE = "management_change"
    PRODUCT_LAUNCH = "product_launch"
    UNKNOWN = "unknown"


class SentimentLabel(str, enum.Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ArticleStatus(str, enum.Enum):
    RAW = "raw"
    ANALYZED = "analyzed"
    SCORED = "scored"
    FAILED = "failed"


# ── Core Tables ─────────────────────────────────────────────────────────────────

class Sector(Base):
    """
    Top-level sector (e.g. Energy, Technology, Financials)
    """
    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    industries = relationship("Industry", back_populates="sector")


class Industry(Base):
    """
    Sub-industry under a sector
    """
    __tablename__ = "industries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    description = Column(Text)
    avg_pe_ratio = Column(Float)
    avg_pb_ratio = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    sector = relationship("Sector", back_populates="industries")
    companies = relationship("Company", back_populates="industry")
    upstream_relations = relationship(
        "IndustryRelationship",
        foreign_keys="IndustryRelationship.downstream_industry_id",
        back_populates="downstream_industry"
    )
    downstream_relations = relationship(
        "IndustryRelationship",
        foreign_keys="IndustryRelationship.upstream_industry_id",
        back_populates="upstream_industry"
    )


class IndustryRelationship(Base):
    """
    Supply chain linkage between industries.
    upstream → downstream (e.g. Steel → Auto)
    impact_coefficient: how much a 10% change in upstream affects downstream margin
    """
    __tablename__ = "industry_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    upstream_industry_id = Column(Integer, ForeignKey("industries.id"), nullable=False)
    downstream_industry_id = Column(Integer, ForeignKey("industries.id"), nullable=False)
    relationship_type = Column(String(50))   # input, output, substitute, complement
    impact_coefficient = Column(Float, default=0.3)  # 0-1
    description = Column(Text)

    upstream_industry = relationship("Industry", foreign_keys=[upstream_industry_id], back_populates="downstream_relations")
    downstream_industry = relationship("Industry", foreign_keys=[downstream_industry_id], back_populates="upstream_relations")


class Company(Base):
    """
    Listed company with financials
    """
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    ticker = Column(String(20), unique=True, nullable=False)
    bse_code = Column(String(10))
    nse_code = Column(String(20))
    industry_id = Column(Integer, ForeignKey("industries.id"))
    market_cap = Column(BigInteger)              # INR Crores
    revenue_ttm = Column(Float)                  # INR Crores
    ebitda_margin = Column(Float)                # %
    net_margin = Column(Float)                   # %
    pe_ratio = Column(Float)
    pb_ratio = Column(Float)
    eps_ttm = Column(Float)                      # INR
    debt_equity = Column(Float)
    roe = Column(Float)
    current_price = Column(Float)
    fifty_two_week_high = Column(Float)
    fifty_two_week_low = Column(Float)
    promoter_holding = Column(Float)
    fii_holding = Column(Float)
    dii_holding = Column(Float)
    is_nifty50 = Column(Boolean, default=False)
    is_sensex = Column(Boolean, default=False)
    aliases = Column(JSON)                       # list of alternative names
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    industry = relationship("Industry", back_populates="companies")
    news_mentions = relationship("NewsCompanyMention", back_populates="company")
    scores = relationship("StockScore", back_populates="company")


class Commodity(Base):
    """
    Raw material / commodity that affects industries
    """
    __tablename__ = "commodities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    symbol = Column(String(20))
    unit = Column(String(30))                    # per tonne, per barrel, etc.
    current_price = Column(Float)
    currency = Column(String(5), default="USD")
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    industry_impacts = relationship("CommodityIndustryImpact", back_populates="commodity")


class CommodityIndustryImpact(Base):
    """
    How a commodity price change propagates to an industry's margins
    """
    __tablename__ = "commodity_industry_impacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"), nullable=False)
    industry_id = Column(Integer, ForeignKey("industries.id"), nullable=False)
    cost_as_pct_revenue = Column(Float)         # % of revenue
    margin_sensitivity = Column(Float)          # bps margin change per 1% commodity change
    direction = Column(String(10))              # positive / negative
    description = Column(Text)

    commodity = relationship("Commodity", back_populates="industry_impacts")


# ── News Tables ─────────────────────────────────────────────────────────────────

class NewsArticle(Base):
    """
    Raw ingested news article
    """
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(255), unique=True)      # hash of URL
    title = Column(Text, nullable=False)
    content = Column(Text)
    summary = Column(Text)
    url = Column(Text)
    source = Column(String(100))
    author = Column(String(200))
    published_at = Column(DateTime)
    ingested_at = Column(DateTime, server_default=func.now())
    status = Column(SAEnum(ArticleStatus), default=ArticleStatus.RAW)
    language = Column(String(10), default="en")
    word_count = Column(Integer)
    is_duplicate = Column(Boolean, default=False)
    raw_metadata = Column(JSON)

    analysis = relationship("ArticleAnalysis", back_populates="article", uselist=False)
    company_mentions = relationship("NewsCompanyMention", back_populates="article")

    __table_args__ = (
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_source", "source"),
        Index("ix_articles_status", "status"),
    )


class ArticleAnalysis(Base):
    """
    LLM analysis output for each article
    """
    __tablename__ = "article_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("news_articles.id"), unique=True, nullable=False)
    analyzed_at = Column(DateTime, server_default=func.now())

    # Summary & Classification
    ai_summary = Column(Text)
    event_type = Column(SAEnum(EventType))
    sentiment = Column(SAEnum(SentimentLabel))

    # Raw Scores (–10 to +10)
    bullish_score = Column(Float, default=0.0)
    bearish_score = Column(Float, default=0.0)
    net_score = Column(Float, default=0.0)      # bullish – bearish magnitude
    confidence = Column(Float, default=0.5)     # 0–1

    # Financial Impact
    revenue_impact_pct = Column(Float)          # %
    margin_impact_bps = Column(Float)           # basis points
    eps_impact_pct = Column(Float)              # %
    price_impact_pct = Column(Float)            # estimated stock price move %

    # Structured output from LLM
    companies_mentioned = Column(JSON)          # list of {name, ticker, role}
    industries_affected = Column(JSON)          # list of industry names
    key_themes = Column(JSON)                   # list of theme strings
    catalysts = Column(JSON)                    # list of catalyst strings
    risks = Column(JSON)                        # list of risk strings
    second_order_effects = Column(JSON)         # downstream industry effects
    full_report = Column(JSON)                  # complete structured report
    raw_llm_output = Column(Text)               # raw LLM response for debugging

    article = relationship("NewsArticle", back_populates="analysis")
    industry_effects = relationship("IndustryEffect", back_populates="analysis")


class NewsCompanyMention(Base):
    """
    Junction: which companies are mentioned in which articles
    """
    __tablename__ = "news_company_mentions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("news_articles.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    mention_type = Column(String(50))           # primary, secondary, competitor
    sentiment_for_company = Column(SAEnum(SentimentLabel))
    impact_score = Column(Float)

    article = relationship("NewsArticle", back_populates="company_mentions")
    company = relationship("Company", back_populates="news_mentions")

    __table_args__ = (
        Index("ix_mentions_article_company", "article_id", "company_id"),
    )


class IndustryEffect(Base):
    """
    Second-order propagation effect on downstream industries
    """
    __tablename__ = "industry_effects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("article_analyses.id"), nullable=False)
    industry_id = Column(Integer, ForeignKey("industries.id"), nullable=False)
    effect_type = Column(String(50))            # direct, propagated
    direction = Column(String(20))              # positive, negative, neutral
    magnitude = Column(Float)                   # 0–10
    description = Column(Text)
    hop = Column(Integer, default=1)            # 1=direct, 2=second-order, etc.

    analysis = relationship("ArticleAnalysis", back_populates="industry_effects")


# ── Scoring Tables ──────────────────────────────────────────────────────────────

class StockScore(Base):
    """
    Daily aggregated score per stock
    """
    __tablename__ = "stock_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    score_date = Column(DateTime, nullable=False)
    computed_at = Column(DateTime, server_default=func.now())

    # Component scores (each 0–10 scaled)
    revenue_score = Column(Float, default=0.0)
    margin_score = Column(Float, default=0.0)
    industry_shift_score = Column(Float, default=0.0)
    regulatory_score = Column(Float, default=0.0)
    sentiment_score = Column(Float, default=0.0)

    # Composite
    composite_score = Column(Float, default=0.0)    # weighted sum
    momentum_score = Column(Float, default=0.0)     # 5-day trend
    article_count = Column(Integer, default=0)
    avg_bullish = Column(Float, default=0.0)
    avg_bearish = Column(Float, default=0.0)

    # Signal
    signal = Column(SAEnum(SentimentLabel))
    signal_strength = Column(Float)                 # 0–1
    rank = Column(Integer)                          # daily rank

    company = relationship("Company", back_populates="scores")

    __table_args__ = (
        Index("ix_scores_date_company", "score_date", "company_id", unique=True),
        Index("ix_scores_composite", "composite_score"),
    )


class DailyRanking(Base):
    """
    Top-N bullish / bearish stocks for each day
    """
    __tablename__ = "daily_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rank_date = Column(DateTime, nullable=False)
    direction = Column(String(20))              # bullish / bearish
    rank = Column(Integer)
    company_id = Column(Integer, ForeignKey("companies.id"))
    composite_score = Column(Float)
    key_catalyst = Column(Text)
    article_count = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_rankings_date_direction", "rank_date", "direction"),
    )


class ThemeCluster(Base):
    """
    Thematic grouping of related articles
    """
    __tablename__ = "theme_clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_date = Column(DateTime, nullable=False)
    theme_name = Column(String(200))
    theme_description = Column(Text)
    article_ids = Column(JSON)                  # list of article IDs
    company_ids = Column(JSON)
    industry_ids = Column(JSON)
    avg_score = Column(Float)
    article_count = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


# ── Schema DDL (for reference) ──────────────────────────────────────────────────
SCHEMA_SQL = """
-- Run this to create all tables
-- Then seed with knowledge graph data

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for fuzzy text search

-- Full-text search index on articles
CREATE INDEX IF NOT EXISTS ix_articles_fts ON news_articles 
    USING gin(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,'')));
"""
