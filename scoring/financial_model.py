# ============================================================
# scoring/financial_model.py – Financial Impact & Scoring Engine
# ============================================================

from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from analysis.llm_engine import ArticleIntelligence
from graph.knowledge_graph import get_graph


# ── Financial Impact Formulas ────────────────────────────────────────────────────

@dataclass
class FinancialImpact:
    """
    Quantified financial impact on a company from a news event.
    
    Formulas:
    - Revenue impact = base_revenue × revenue_impact_pct / 100
    - Margin impact = margin_impact_bps / 10000 (convert to %)
    - EBITDA change = Revenue × margin_impact
    - EPS impact = EPS × eps_impact_pct / 100
    - Price impact = EPS_new × PE_ratio (or direct % estimate)
    """
    company_ticker: str
    article_id: int

    # Input parameters
    base_revenue: float = 0.0
    base_eps: float = 0.0
    pe_ratio: float = 20.0
    current_price: float = 0.0
    ebitda_margin: float = 15.0

    # Computed impacts
    revenue_change_cr: float = 0.0       # INR Crores
    ebitda_change_cr: float = 0.0
    eps_change: float = 0.0
    eps_new: float = 0.0
    fair_value_change: float = 0.0       # INR
    price_impact_pct: float = 0.0
    upside_downside: float = 0.0         # from current price

    # Scenario analysis
    bull_price_impact: float = 0.0
    base_price_impact: float = 0.0
    bear_price_impact: float = 0.0

    methodology_notes: str = ""


def compute_financial_impact(
    intelligence: ArticleIntelligence,
    company_ticker: str,
) -> FinancialImpact:
    """
    Compute quantified financial impact on a specific company.
    Uses LLM estimates and company fundamentals from knowledge graph.
    """
    graph = get_graph()
    co_data = graph.lookup_company(company_ticker)

    impact = FinancialImpact(company_ticker=company_ticker, article_id=intelligence.article_id)

    if not co_data:
        impact.methodology_notes = f"Company {company_ticker} not found in knowledge graph"
        return impact

    # Load fundamentals
    impact.base_revenue = co_data.get("revenue_ttm", 0) or 0
    impact.base_eps = co_data.get("eps_ttm", 0) or 0
    impact.pe_ratio = co_data.get("pe_ratio", 20) or 20
    impact.current_price = co_data.get("current_price", 0) or 0
    impact.ebitda_margin = co_data.get("ebitda_margin", 15) or 15

    rev_impact_pct = intelligence.revenue_impact_pct or 0
    margin_bps = intelligence.margin_impact_bps or 0
    eps_pct = intelligence.eps_impact_pct or 0
    direct_price_pct = intelligence.price_impact_pct or 0

    # ── Revenue Impact ───────────────────────────────────────────────────────────
    impact.revenue_change_cr = impact.base_revenue * rev_impact_pct / 100

    # ── EBITDA Impact ────────────────────────────────────────────────────────────
    # Two components: revenue change × margin + margin bps on existing revenue
    margin_change_pct = margin_bps / 10000
    impact.ebitda_change_cr = (
        impact.revenue_change_cr * (impact.ebitda_margin / 100)
        + impact.base_revenue * margin_change_pct
    )

    # ── EPS Impact ───────────────────────────────────────────────────────────────
    if eps_pct != 0:
        impact.eps_change = impact.base_eps * eps_pct / 100
    else:
        # Derive EPS impact from EBITDA assuming 35% tax + interest
        if impact.base_revenue > 0:
            net_margin = co_data.get("net_margin", 5) or 5
            pat_change = impact.ebitda_change_cr * (net_margin / (impact.ebitda_margin or 15))
            # Rough EPS change assuming shares outstanding ratio
            # EPS_impact = PAT_change / (current_EPS / net_profit_margin × revenue)
            if impact.base_eps != 0 and net_margin != 0:
                estimated_shares = (impact.base_revenue * net_margin / 100) / (impact.base_eps + 0.001)
                impact.eps_change = pat_change / (estimated_shares + 0.001)
            impact.eps_change = max(min(impact.eps_change, impact.base_eps * 0.5), impact.base_eps * -0.5)

    impact.eps_new = impact.base_eps + impact.eps_change

    # ── Price Impact ─────────────────────────────────────────────────────────────
    # Method 1: EPS × PE
    if impact.pe_ratio and impact.eps_new:
        new_price_method1 = impact.eps_new * impact.pe_ratio
        fair_value_change_1 = new_price_method1 - impact.current_price
    else:
        fair_value_change_1 = 0

    # Method 2: Direct % estimate from LLM
    fair_value_change_2 = impact.current_price * direct_price_pct / 100

    # Blend both (60% LLM direct, 40% model-based)
    if direct_price_pct != 0 and fair_value_change_1 != 0:
        impact.fair_value_change = 0.6 * fair_value_change_2 + 0.4 * fair_value_change_1
    elif direct_price_pct != 0:
        impact.fair_value_change = fair_value_change_2
    else:
        impact.fair_value_change = fair_value_change_1

    if impact.current_price > 0:
        impact.price_impact_pct = (impact.fair_value_change / impact.current_price) * 100
        impact.upside_downside = impact.fair_value_change

    # ── Scenario Analysis ─────────────────────────────────────────────────────────
    impact.bull_price_impact = impact.price_impact_pct * 1.5
    impact.base_price_impact = impact.price_impact_pct
    impact.bear_price_impact = impact.price_impact_pct * 0.5

    impact.methodology_notes = (
        f"Revenue: ₹{impact.base_revenue:,.0f}Cr × {rev_impact_pct:+.1f}% = ₹{impact.revenue_change_cr:+,.0f}Cr | "
        f"EBITDA Δ: ₹{impact.ebitda_change_cr:+,.0f}Cr | "
        f"EPS: ₹{impact.base_eps:.1f} → ₹{impact.eps_new:.1f} | "
        f"Price: ₹{impact.current_price:.0f} + ₹{impact.fair_value_change:+.1f} = "
        f"₹{impact.current_price + impact.fair_value_change:.0f} ({impact.price_impact_pct:+.1f}%)"
    )

    return impact


# ── Scoring Engine ───────────────────────────────────────────────────────────────

@dataclass
class StockScoreComponents:
    company_ticker: str
    score_date: datetime
    article_count: int = 0

    # Raw score inputs (each 0–10)
    revenue_score: float = 0.0
    margin_score: float = 0.0
    industry_shift_score: float = 0.0
    regulatory_score: float = 0.0
    sentiment_score: float = 0.0

    # Composite
    composite_score: float = 0.0
    momentum_score: float = 0.0
    avg_bullish: float = 0.0
    avg_bearish: float = 0.0
    net_signal: float = 0.0

    # Final
    signal: str = "neutral"
    signal_strength: float = 0.0
    rank: int = 0
    key_catalysts: list = field(default_factory=list)


class ScoringEngine:
    """
    Weighted scoring engine for individual stocks.
    
    Weights:
    - Revenue impact:   30%
    - Margin impact:    25%
    - Industry shift:   20%
    - Regulatory:       15%
    - Sentiment:        10%
    
    Final score: 0–100 (50 = neutral, >70 = bullish, <30 = bearish)
    """

    WEIGHTS = {
        "revenue": 0.30,
        "margin": 0.25,
        "industry_shift": 0.20,
        "regulatory": 0.15,
        "sentiment": 0.10,
    }

    def score_from_analyses(
        self,
        company_ticker: str,
        analyses: list[ArticleIntelligence],
        financial_impacts: list[FinancialImpact],
        score_date: Optional[datetime] = None,
    ) -> StockScoreComponents:
        """
        Aggregate multiple article analyses into a single daily stock score.
        """
        score = StockScoreComponents(
            company_ticker=company_ticker,
            score_date=score_date or datetime.now(),
            article_count=len(analyses)
        )

        if not analyses:
            return score

        # ── Revenue Score (30%) ──────────────────────────────────────────────────
        # Based on financial impact model
        if financial_impacts:
            avg_rev_impact = sum(fi.revenue_change_cr for fi in financial_impacts) / len(financial_impacts)
            avg_price_impact_pct = sum(fi.price_impact_pct for fi in financial_impacts) / len(financial_impacts)
            # Normalize: ±10% price impact → score 0–10
            revenue_raw = 5 + (avg_price_impact_pct / 2)  # 10% → 5+5=10, -10% → 5-5=0
            score.revenue_score = max(0, min(10, revenue_raw))
        else:
            # Fallback: use LLM revenue impact estimates
            avg_rev = sum(a.revenue_impact_pct for a in analyses) / len(analyses)
            revenue_raw = 5 + (avg_rev / 2)
            score.revenue_score = max(0, min(10, revenue_raw))

        # ── Margin Score (25%) ───────────────────────────────────────────────────
        avg_margin_bps = sum(a.margin_impact_bps for a in analyses) / len(analyses)
        # Normalize: ±500 bps → 0–10
        margin_raw = 5 + (avg_margin_bps / 100)  # 500bps → 10, -500bps → 0
        score.margin_score = max(0, min(10, margin_raw))

        # ── Industry Shift Score (20%) ───────────────────────────────────────────
        bullish_count = sum(1 for a in analyses if a.sentiment == "bullish")
        bearish_count = sum(1 for a in analyses if a.sentiment == "bearish")
        shift_raw = 5 + ((bullish_count - bearish_count) / len(analyses)) * 5
        score.industry_shift_score = max(0, min(10, shift_raw))

        # ── Regulatory Score (15%) ───────────────────────────────────────────────
        regulatory_articles = [a for a in analyses if a.event_type == "regulation"]
        if regulatory_articles:
            avg_bull = sum(a.bullish_score for a in regulatory_articles) / len(regulatory_articles)
            avg_bear = sum(a.bearish_score for a in regulatory_articles) / len(regulatory_articles)
            reg_raw = 5 + (avg_bull - avg_bear) / 2
        else:
            reg_raw = 5.0  # neutral if no regulatory news
        score.regulatory_score = max(0, min(10, reg_raw))

        # ── Sentiment Score (10%) ────────────────────────────────────────────────
        avg_bullish = sum(a.bullish_score for a in analyses) / len(analyses)
        avg_bearish = sum(a.bearish_score for a in analyses) / len(analyses)
        sentiment_raw = 5 + (avg_bullish - avg_bearish) / 2
        score.sentiment_score = max(0, min(10, sentiment_raw))

        score.avg_bullish = avg_bullish
        score.avg_bearish = avg_bearish

        # ── Composite Score (weighted sum → scale to 0–100) ──────────────────────
        weighted = (
            score.revenue_score * self.WEIGHTS["revenue"] +
            score.margin_score * self.WEIGHTS["margin"] +
            score.industry_shift_score * self.WEIGHTS["industry_shift"] +
            score.regulatory_score * self.WEIGHTS["regulatory"] +
            score.sentiment_score * self.WEIGHTS["sentiment"]
        )
        score.composite_score = weighted * 10  # 0–100

        # ── Net Signal ───────────────────────────────────────────────────────────
        score.net_signal = score.composite_score - 50  # positive = bullish, negative = bearish

        # ── Signal Classification ─────────────────────────────────────────────────
        if score.composite_score >= 70:
            score.signal = "bullish"
            score.signal_strength = (score.composite_score - 50) / 50
        elif score.composite_score <= 30:
            score.signal = "bearish"
            score.signal_strength = (50 - score.composite_score) / 50
        else:
            score.signal = "neutral"
            score.signal_strength = abs(score.composite_score - 50) / 50

        # ── Key Catalysts ─────────────────────────────────────────────────────────
        all_catalysts = []
        for a in analyses:
            all_catalysts.extend(a.catalysts[:2])
        score.key_catalysts = list(set(all_catalysts))[:5]

        return score

    def compute_momentum(
        self,
        company_ticker: str,
        today_score: float,
        historical_scores: list[float],   # last 5 days
    ) -> float:
        """
        Momentum = EMA-weighted trend of composite score over 5 days.
        Positive = accelerating bullish. Negative = accelerating bearish.
        """
        if not historical_scores:
            return 0.0

        # Simple linear regression slope
        n = len(historical_scores) + 1
        y = historical_scores + [today_score]
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        denominator = sum((xi - x_mean) ** 2 for xi in x)
        slope = numerator / denominator if denominator > 0 else 0

        return round(slope, 3)


# ── Ranking Engine ────────────────────────────────────────────────────────────────

@dataclass
class StockRank:
    rank: int
    ticker: str
    company_name: str
    composite_score: float
    signal: str
    signal_strength: float
    price_impact_pct: float
    article_count: int
    key_catalyst: str
    industry: str


class RankingEngine:
    """
    Ranks all scored stocks daily.
    Produces Top-20 Bullish, Top-20 Bearish, and Industry Heatmap.
    """

    def rank_stocks(self, scores: list[StockScoreComponents]) -> dict:
        """
        Generate daily rankings from scored stocks.
        Returns: {
            "bullish": [StockRank],
            "bearish": [StockRank],
            "neutral": [StockRank],
            "industry_heatmap": {...},
        }
        """
        graph = get_graph()

        bullish = [s for s in scores if s.signal == "bullish"]
        bearish = [s for s in scores if s.signal == "bearish"]
        neutral = [s for s in scores if s.signal == "neutral"]

        # Sort bullish by composite score descending
        bullish.sort(key=lambda s: s.composite_score, reverse=True)
        # Sort bearish by composite score ascending (most bearish first)
        bearish.sort(key=lambda s: s.composite_score, reverse=False)

        def to_rank(score_list: list[StockScoreComponents], direction: str) -> list[StockRank]:
            ranked = []
            for i, s in enumerate(score_list[:20]):
                co = graph.lookup_company(s.company_ticker) or {}
                ranked.append(StockRank(
                    rank=i + 1,
                    ticker=s.company_ticker,
                    company_name=co.get("name", s.company_ticker),
                    composite_score=round(s.composite_score, 2),
                    signal=s.signal,
                    signal_strength=round(s.signal_strength, 3),
                    price_impact_pct=round(s.avg_bullish - s.avg_bearish, 2),
                    article_count=s.article_count,
                    key_catalyst=s.key_catalysts[0] if s.key_catalysts else "",
                    industry=co.get("industry", ""),
                ))
            return ranked

        # Industry Heatmap
        industry_scores: dict[str, list[float]] = {}
        for s in scores:
            co = graph.lookup_company(s.company_ticker) or {}
            ind = co.get("industry", "UNKNOWN")
            industry_scores.setdefault(ind, []).append(s.composite_score)

        heatmap = {
            ind: {
                "avg_score": round(sum(v) / len(v), 2),
                "count": len(v),
                "signal": "bullish" if sum(v) / len(v) > 55 else ("bearish" if sum(v) / len(v) < 45 else "neutral")
            }
            for ind, v in industry_scores.items()
        }

        return {
            "date": datetime.now().isoformat(),
            "bullish": to_rank(bullish, "bullish"),
            "bearish": to_rank(bearish, "bearish"),
            "neutral": [s.company_ticker for s in neutral[:10]],
            "industry_heatmap": heatmap,
            "summary": {
                "total_stocks_scored": len(scores),
                "bullish_count": len(bullish),
                "bearish_count": len(bearish),
                "neutral_count": len(neutral),
                "market_breadth": f"{len(bullish)}/{len(scores)} bullish ({len(bullish)/max(len(scores),1)*100:.1f}%)"
            }
        }


# ── Theme Clustering ─────────────────────────────────────────────────────────────

class ThemeClusterer:
    """
    Groups related news articles by theme using keyword overlap.
    For production: use sentence transformers + KMeans clustering.
    """

    THEME_DEFINITIONS = {
        "EV Transition": ["electric vehicle", "ev", "lithium", "battery", "charging", "ola electric"],
        "Rate Environment": ["rbi", "repo rate", "interest rate", "monetary policy", "inflation"],
        "Steel/Metals Cycle": ["steel", "iron ore", "coking coal", "metal", "commodity"],
        "IT Spending": ["it services", "tcs", "infosys", "tech spending", "ai adoption", "deal win"],
        "Pharma Regulatory": ["usfda", "drug approval", "anda", "warning letter", "regulatory"],
        "Infra Push": ["infrastructure", "road", "railway", "port", "capex", "government spending"],
        "FMCG Demand": ["fmcg", "rural demand", "urban consumption", "volume growth", "price hike"],
        "Banking NPA": ["npa", "provisioning", "credit cost", "asset quality", "stressed assets"],
        "Renewable Energy": ["solar", "wind", "renewable", "green hydrogen", "energy transition"],
        "PLI Scheme": ["pli", "production linked incentive", "manufacturing", "atma nirbhar"],
    }

    def cluster(self, articles: list[dict]) -> list[dict]:
        """
        Assign theme labels to articles. An article can belong to multiple themes.
        """
        clusters: dict[str, list[int]] = {t: [] for t in self.THEME_DEFINITIONS}

        for i, article in enumerate(articles):
            text = (article.get("title", "") + " " + article.get("content", "")).lower()
            for theme, keywords in self.THEME_DEFINITIONS.items():
                if sum(1 for kw in keywords if kw in text) >= 2:
                    clusters[theme].append(article.get("id", i))

        result = []
        for theme, article_ids in clusters.items():
            if article_ids:
                result.append({
                    "theme": theme,
                    "article_count": len(article_ids),
                    "article_ids": article_ids,
                })

        result.sort(key=lambda x: x["article_count"], reverse=True)
        return result
