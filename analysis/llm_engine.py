# ============================================================
# analysis/llm_engine.py – Claude-powered Article Analysis
# Processes 800+ articles using async batching for <3 min
# ============================================================

import asyncio
import json
import re
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

import anthropic
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

# ── Output Schema ────────────────────────────────────────────────────────────────

@dataclass
class ArticleIntelligence:
    """Structured output from LLM analysis of one news article."""
    article_id: int
    ai_summary: str = ""
    event_type: str = "unknown"
    sentiment: str = "neutral"
    bullish_score: float = 0.0      # 0–10
    bearish_score: float = 0.0      # 0–10
    net_score: float = 0.0
    confidence: float = 0.5

    # Financial impact
    revenue_impact_pct: float = 0.0
    margin_impact_bps: float = 0.0
    eps_impact_pct: float = 0.0
    price_impact_pct: float = 0.0

    # Entities
    companies_mentioned: list = field(default_factory=list)
    industries_affected: list = field(default_factory=list)
    key_themes: list = field(default_factory=list)
    catalysts: list = field(default_factory=list)
    risks: list = field(default_factory=list)
    second_order_effects: list = field(default_factory=list)

    # Full structured report
    full_report: dict = field(default_factory=dict)
    raw_llm_output: str = ""
    error: Optional[str] = None


# ── Prompt Templates ─────────────────────────────────────────────────────────────

ANALYSIS_SYSTEM_PROMPT = """You are a senior equity research analyst and quantitative strategist at a top-tier hedge fund covering Indian equity markets (NSE/BSE). 

Your expertise includes:
- Fundamental analysis (P&L, balance sheet, cash flow modelling)
- Sector dynamics and supply chain propagation
- Macro-to-micro linkages
- Event-driven investing and alpha generation from news flow

You analyze news articles and produce STRUCTURED, QUANTIFIED investment intelligence.

SCORING SCALE:
- Bullish Score: 0 (no positive impact) to 10 (extremely bullish)  
- Bearish Score: 0 (no negative impact) to 10 (extremely bearish)
- These are INDEPENDENT — a regulation can score 4 bullish (creates new market) AND 6 bearish (cost burden)

EVENT TYPES (pick exactly one):
regulation | demand_shock | supply_shock | pricing_change | capacity_expansion | 
corporate_action | macro_event | earnings | analyst_action | merger_acquisition | 
management_change | product_launch | unknown

INDIAN MARKET CONTEXT:
- Primary companies: Nifty 50, Sensex 30, Nifty Midcap 150
- Regulators: SEBI, RBI, MoF, DPIIT, CCI
- Key sectors: IT, Banking, Auto, Pharma, Energy, FMCG, Metals, Cement, Infra
- Currency: INR (₹)

OUTPUT FORMAT: You MUST return a valid JSON object. No prose before or after JSON."""

ANALYSIS_USER_PROMPT = """Analyze this Indian market news article and return a complete structured JSON report.

ARTICLE:
Title: {title}
Source: {source}
Published: {published_at}
Content: {content}

Return EXACTLY this JSON (all fields required, no omissions):

{{
  "ai_summary": "2-3 sentence factual summary of the key news event",
  
  "event_type": "<one of: regulation|demand_shock|supply_shock|pricing_change|capacity_expansion|corporate_action|macro_event|earnings|analyst_action|merger_acquisition|management_change|product_launch|unknown>",
  
  "sentiment": "<bullish|bearish|neutral>",
  
  "bullish_score": <0.0–10.0>,
  "bearish_score": <0.0–10.0>,
  "confidence": <0.0–1.0>,
  
  "companies_mentioned": [
    {{
      "name": "Company Name",
      "ticker": "NSE_TICKER_OR_EMPTY",
      "role": "<primary|secondary|competitor|supplier|customer>",
      "impact": "<positive|negative|neutral>",
      "rationale": "Why this company is affected"
    }}
  ],
  
  "industries_affected": [
    {{
      "name": "Industry Name",
      "direction": "<positive|negative|neutral>",
      "magnitude": <1–10>,
      "rationale": "Why"
    }}
  ],
  
  "financial_impact": {{
    "revenue_impact_pct": <number, e.g. -5.0 means 5% revenue decline>,
    "margin_impact_bps": <basis points, e.g. -150 means 150 bps margin compression>,
    "eps_impact_pct": <% EPS change estimate>,
    "price_impact_pct": <estimated % stock price impact, can be positive or negative>,
    "impact_horizon": "<immediate|3_months|6_months|12_months>",
    "impact_rationale": "Quantitative reasoning for the financial estimates"
  }},
  
  "key_themes": ["theme1", "theme2", "theme3"],
  
  "catalysts": [
    "Specific bullish catalyst 1",
    "Specific bullish catalyst 2"
  ],
  
  "risks": [
    "Specific risk or bearish factor 1",
    "Specific risk or bearish factor 2"
  ],
  
  "second_order_effects": [
    {{
      "industry": "Downstream Industry Name",
      "direction": "<positive|negative|neutral>",
      "mechanism": "How the primary event propagates to this industry",
      "magnitude": <1–10>,
      "hop": <1 = direct, 2 = second-order, 3 = third-order>
    }}
  ],
  
  "regulatory_context": "Regulatory body involved and policy implications if applicable, else null",
  
  "competitive_impact": "Impact on competitive dynamics and market share, else null",
  
  "macro_linkage": "Connection to macro themes (RBI policy, USD/INR, global commodities), else null",
  
  "monitoring_indicators": [
    "KPI or data point to watch for confirmation",
    "Next catalyst or event to monitor"
  ],
  
  "long_term_view": "Strategic 12-24 month implication for primary company/industry",
  
  "final_investment_view": {{
    "recommendation": "<Strong Buy|Buy|Hold|Sell|Strong Sell|No Action>",
    "time_horizon": "<1_week|1_month|3_months|6_months>",
    "conviction": "<High|Medium|Low>",
    "rationale": "Concise investment thesis (2–3 sentences)"
  }}
}}"""


# ── LLM Client ───────────────────────────────────────────────────────────────────

class LLMAnalysisEngine:
    """
    High-throughput async LLM analysis using Claude.
    Processes 800+ articles via concurrent batch requests.
    Target: < 3 minutes for full daily run.
    
    Performance strategy:
    - Batch size: 10 articles
    - Concurrent batches: 20 (200 parallel inflight)
    - Semaphore: 50 concurrent Claude calls
    - Retry: exponential backoff on rate limits
    """

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENT)
        self.model = settings.LLM_MODEL
        self.stats = {"success": 0, "failed": 0, "total_tokens": 0}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError))
    )
    async def _call_claude(self, title: str, content: str, source: str,
                           published_at: str, article_id: int) -> ArticleIntelligence:
        """Single article analysis via Claude API."""
        async with self.semaphore:
            prompt = ANALYSIS_USER_PROMPT.format(
                title=title,
                source=source,
                published_at=published_at,
                content=content[:3000]   # cap context per article
            )

            message = await self.client.messages.create(
                model=self.model,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                system=ANALYSIS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            raw = message.content[0].text
            self.stats["total_tokens"] += message.usage.input_tokens + message.usage.output_tokens

            return self._parse_response(raw, article_id)

    def _parse_response(self, raw: str, article_id: int) -> ArticleIntelligence:
        """Parse and validate LLM JSON response."""
        result = ArticleIntelligence(article_id=article_id, raw_llm_output=raw)

        try:
            # Extract JSON (may be wrapped in code fences)
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError("No JSON found in response")

            data = json.loads(match.group())

            result.ai_summary = data.get("ai_summary", "")
            result.event_type = data.get("event_type", "unknown")
            result.sentiment = data.get("sentiment", "neutral")
            result.bullish_score = float(data.get("bullish_score", 0))
            result.bearish_score = float(data.get("bearish_score", 0))
            result.net_score = result.bullish_score - result.bearish_score
            result.confidence = float(data.get("confidence", 0.5))

            fin = data.get("financial_impact", {})
            result.revenue_impact_pct = float(fin.get("revenue_impact_pct", 0))
            result.margin_impact_bps = float(fin.get("margin_impact_bps", 0))
            result.eps_impact_pct = float(fin.get("eps_impact_pct", 0))
            result.price_impact_pct = float(fin.get("price_impact_pct", 0))

            result.companies_mentioned = data.get("companies_mentioned", [])
            result.industries_affected = data.get("industries_affected", [])
            result.key_themes = data.get("key_themes", [])
            result.catalysts = data.get("catalysts", [])
            result.risks = data.get("risks", [])
            result.second_order_effects = data.get("second_order_effects", [])
            result.full_report = data

            self.stats["success"] += 1

        except Exception as e:
            logger.error(f"Parse error for article {article_id}: {e}")
            result.error = str(e)
            self.stats["failed"] += 1

        return result

    async def analyze_article(self, article) -> ArticleIntelligence:
        """Analyze a single article (NewsArticle ORM object or dict)."""
        if isinstance(article, dict):
            aid = article.get("id", 0)
            title = article.get("title", "")
            content = article.get("content", "") or article.get("summary", "")
            source = article.get("source", "")
            pub = str(article.get("published_at", datetime.now()))
        else:
            aid = article.id
            title = article.title
            content = article.content or article.summary or ""
            source = article.source
            pub = str(article.published_at or datetime.now())

        try:
            return await self._call_claude(title, content, source, pub, aid)
        except Exception as e:
            logger.error(f"Analysis failed for article {aid}: {e}")
            result = ArticleIntelligence(article_id=aid)
            result.error = str(e)
            self.stats["failed"] += 1
            return result

    async def analyze_batch(self, articles: list) -> list[ArticleIntelligence]:
        """Analyze a batch of articles concurrently."""
        tasks = [self.analyze_article(art) for art in articles]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def analyze_all(self, articles: list, batch_size: int = None) -> list[ArticleIntelligence]:
        """
        Main entry point: analyze all articles with progress tracking.
        Uses chunked execution to avoid overwhelming the API.
        """
        batch_size = batch_size or settings.LLM_BATCH_SIZE
        start = datetime.now()
        logger.info(f"🧠 Starting LLM analysis of {len(articles)} articles "
                    f"(batch_size={batch_size}, max_concurrent={settings.LLM_MAX_CONCURRENT})")

        results = []
        total_batches = (len(articles) + batch_size - 1) // batch_size

        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            batch_num = i // batch_size + 1
            logger.info(f"  Batch {batch_num}/{total_batches} ({len(batch)} articles)...")

            batch_results = await self.analyze_batch(batch)
            results.extend(batch_results)

            # Brief pause between batches to respect rate limits
            if i + batch_size < len(articles):
                await asyncio.sleep(0.5)

        elapsed = (datetime.now() - start).seconds
        logger.info(
            f"✅ Analysis complete in {elapsed}s | "
            f"Success: {self.stats['success']} | Failed: {self.stats['failed']} | "
            f"Tokens: {self.stats['total_tokens']:,}"
        )
        return results

    def build_full_report(self, intelligence: ArticleIntelligence, article) -> dict:
        """
        Build the complete structured investment report in the mandated format.
        """
        data = intelligence.full_report
        if not data:
            return {}

        title = getattr(article, "title", article.get("title", "")) if not isinstance(article, dict) else article.get("title", "")
        source = getattr(article, "source", article.get("source", "")) if not isinstance(article, dict) else article.get("source", "")

        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": self.model,
                "confidence": intelligence.confidence,
            },

            # ① News Identification
            "news_identification": {
                "title": title,
                "source": source,
                "event_type": intelligence.event_type,
                "published_at": str(getattr(article, "published_at", "")),
            },

            # ② Executive Summary
            "executive_summary": intelligence.ai_summary,

            # ③ Bullish / Bearish Score
            "scoring": {
                "bullish_score": intelligence.bullish_score,
                "bearish_score": intelligence.bearish_score,
                "net_score": intelligence.net_score,
                "sentiment": intelligence.sentiment,
                "signal_strength": abs(intelligence.net_score) / 10,
            },

            # ④ Actionable Takeaways
            "actionable_takeaways": {
                "recommendation": data.get("final_investment_view", {}).get("recommendation", "Hold"),
                "conviction": data.get("final_investment_view", {}).get("conviction", "Low"),
                "time_horizon": data.get("final_investment_view", {}).get("time_horizon", "1_month"),
                "rationale": data.get("final_investment_view", {}).get("rationale", ""),
                "catalysts": intelligence.catalysts,
                "risks": intelligence.risks,
            },

            # ⑤ Industry Structure Analysis
            "industry_structure": {
                "industries_affected": intelligence.industries_affected,
                "competitive_impact": data.get("competitive_impact"),
            },

            # ⑥ Financial Impact Analysis
            "financial_impact": {
                "revenue_impact_pct": intelligence.revenue_impact_pct,
                "margin_impact_bps": intelligence.margin_impact_bps,
                "eps_impact_pct": intelligence.eps_impact_pct,
                "price_impact_pct": intelligence.price_impact_pct,
                "impact_horizon": data.get("financial_impact", {}).get("impact_horizon", "3_months"),
                "impact_rationale": data.get("financial_impact", {}).get("impact_rationale", ""),
            },

            # ⑦ Competitive Position vs Peers
            "competitive_position": {
                "companies_mentioned": intelligence.companies_mentioned,
                "market_share_impact": data.get("competitive_impact"),
            },

            # ⑧ Relative Stock Positioning
            "relative_stock_positioning": {
                "primary_companies": [
                    c for c in intelligence.companies_mentioned if c.get("role") == "primary"
                ],
                "beneficiaries": [
                    c for c in intelligence.companies_mentioned if c.get("impact") == "positive"
                ],
                "losers": [
                    c for c in intelligence.companies_mentioned if c.get("impact") == "negative"
                ],
            },

            # ⑨ Second-Order Industry Effects
            "second_order_effects": intelligence.second_order_effects,

            # ⑩ Input/Output Pricing Impact
            "pricing_impact": {
                "supply_chain_effects": [
                    e for e in intelligence.second_order_effects if e.get("hop") == 1
                ],
                "downstream_effects": [
                    e for e in intelligence.second_order_effects if e.get("hop", 1) > 1
                ],
                "macro_linkage": data.get("macro_linkage"),
            },

            # ⑪ Stock Price Impact Model
            "price_impact_model": {
                "estimated_price_impact_pct": intelligence.price_impact_pct,
                "methodology": "EPS × PE multiple compression/expansion",
                "eps_change_pct": intelligence.eps_impact_pct,
                "pe_change_estimate": intelligence.price_impact_pct - intelligence.eps_impact_pct,
            },

            # ⑫ Long-Term Strategic Implications
            "long_term_implications": data.get("long_term_view", ""),

            # ⑬ Final Investment View
            "final_investment_view": data.get("final_investment_view", {}),

            # ⑭ Key Data Points
            "key_data_points": intelligence.key_themes,

            # ⑮ Monitoring Indicators
            "monitoring_indicators": data.get("monitoring_indicators", []),

            # Regulatory context (bonus field)
            "regulatory_context": data.get("regulatory_context"),
        }
        return report
