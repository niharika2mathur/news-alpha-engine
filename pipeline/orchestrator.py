# ============================================================
# pipeline/orchestrator.py – Master Pipeline Orchestrator
# Runs the complete daily workflow: Ingest → Analyze → Score → Rank
# ============================================================

import asyncio
import json
from datetime import datetime
from typing import Optional
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from config import settings
from ingestion.scraper import IngestionEngine, RawArticle
from analysis.llm_engine import LLMAnalysisEngine, ArticleIntelligence
from graph.knowledge_graph import get_graph
from graph.event_engine import EventDetectionEngine
from scoring.financial_model import (
    ScoringEngine, RankingEngine, ThemeClusterer,
    compute_financial_impact, StockScoreComponents
)

console = Console()


class PipelineOrchestrator:
    """
    Central pipeline orchestrator. Manages the end-to-end daily workflow.
    
    Pipeline stages:
    08:00 – Ingest 800+ articles from all sources
    08:10 – LLM analysis (async batch, 20 concurrent)
    08:20 – Event detection + knowledge graph propagation
    08:25 – Financial impact modeling per company
    08:30 – Scoring + ranking
    08:35 – Report generation + dashboard update
    
    Target: Complete in < 8 minutes for 800 articles.
    """

    def __init__(self):
        self.graph = get_graph()
        self.ingestion = IngestionEngine()
        self.llm = LLMAnalysisEngine()
        self.event_engine = EventDetectionEngine(self.graph)
        self.scorer = ScoringEngine()
        self.ranker = RankingEngine()
        self.clusterer = ThemeClusterer()

        # In-memory store (replace with DB in production)
        self._latest_articles: list[dict] = []
        self._latest_analyses: list[dict] = []
        self._latest_scores: dict[str, dict] = {}
        self._latest_rankings: Optional[dict] = None
        self._latest_themes: list[dict] = []

    async def run_full_pipeline(
        self,
        run_ingestion: bool = True,
        run_analysis: bool = True,
        run_scoring: bool = True,
        run_ranking: bool = True,
        max_articles: Optional[int] = None,
    ) -> dict:
        """Run complete pipeline. Returns summary stats."""
        start_time = datetime.now()
        stats = {"start_time": start_time.isoformat()}

        console.rule("[bold blue]News Alpha Engine – Daily Pipeline")
        logger.info(f"🚀 Pipeline starting at {start_time.strftime('%H:%M:%S')}")

        articles: list[RawArticle] = []
        analyses: list[ArticleIntelligence] = []

        # ═══════════════════════════════════════════════════════════════════════
        # STAGE 1: INGESTION
        # ═══════════════════════════════════════════════════════════════════════
        if run_ingestion:
            with console.status("[bold green]Stage 1: Ingesting news articles..."):
                articles = await self.ingestion.run(save_to_db=False)

            if max_articles:
                articles = articles[:max_articles]

            stats["articles_ingested"] = len(articles)
            console.print(f"[green]✓ Stage 1 complete: {len(articles)} articles ingested[/green]")

            # Convert to dict for in-memory storage
            self._latest_articles = [
                {
                    "id": i,
                    "title": a.title,
                    "content": a.content,
                    "url": a.url,
                    "source": a.source,
                    "published_at": str(a.published_at),
                    "external_id": a.external_id,
                }
                for i, a in enumerate(articles)
            ]
        else:
            articles = []
            stats["articles_ingested"] = 0

        # ═══════════════════════════════════════════════════════════════════════
        # STAGE 2: LLM ANALYSIS
        # ═══════════════════════════════════════════════════════════════════════
        if run_analysis and articles:
            console.print(f"\n[bold]Stage 2:[/bold] Analyzing {len(articles)} articles with Claude AI...")

            # Filter: skip very short articles (< 30 words)
            analyzable = [
                art for art in self._latest_articles
                if len((art.get("title", "") + art.get("content", "")).split()) >= 30
            ]
            logger.info(f"Analyzing {len(analyzable)}/{len(self._latest_articles)} articles (filtered short ones)")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("LLM Analysis", total=len(analyzable))

                batch_size = settings.LLM_BATCH_SIZE
                for i in range(0, len(analyzable), batch_size):
                    batch = analyzable[i:i + batch_size]
                    batch_results = await self.llm.analyze_batch(batch)
                    analyses.extend(batch_results)
                    progress.advance(task, len(batch))

            stats["articles_analyzed"] = len(analyses)
            stats["analysis_success"] = self.llm.stats["success"]
            stats["analysis_failed"] = self.llm.stats["failed"]

            # Save analysis results
            self._latest_analyses = [
                {
                    "article_id": a.article_id,
                    "event_type": a.event_type,
                    "sentiment": a.sentiment,
                    "bullish_score": a.bullish_score,
                    "bearish_score": a.bearish_score,
                    "net_score": a.net_score,
                    "confidence": a.confidence,
                    "companies_mentioned": a.companies_mentioned,
                    "industries_affected": a.industries_affected,
                    "key_themes": a.key_themes,
                    "catalysts": a.catalysts,
                    "risks": a.risks,
                    "second_order_effects": a.second_order_effects,
                    "revenue_impact_pct": a.revenue_impact_pct,
                    "margin_impact_bps": a.margin_impact_bps,
                    "eps_impact_pct": a.eps_impact_pct,
                    "price_impact_pct": a.price_impact_pct,
                    "full_report": self.llm.build_full_report(a, self._latest_articles[a.article_id] if a.article_id < len(self._latest_articles) else {}),
                }
                for a in analyses
            ]

            console.print(f"[green]✓ Stage 2 complete: {stats['analysis_success']} analyzed, {stats['analysis_failed']} failed[/green]")

        # ═══════════════════════════════════════════════════════════════════════
        # STAGE 3: EVENT DETECTION + PROPAGATION
        # ═══════════════════════════════════════════════════════════════════════
        if run_analysis and analyses:
            console.print("\n[bold]Stage 3:[/bold] Event detection and knowledge graph propagation...")

            propagation_results = []
            for intelligence in analyses:
                art_idx = intelligence.article_id
                if art_idx < len(self._latest_articles):
                    art = self._latest_articles[art_idx]
                    event = self.event_engine.run(
                        title=art.get("title", ""),
                        content=art.get("content", ""),
                        llm_event_type=intelligence.event_type,
                        llm_sentiment=intelligence.sentiment,
                        bullish_score=intelligence.bullish_score,
                        bearish_score=intelligence.bearish_score,
                    )
                    propagation_results.append(event)

            stats["propagations"] = len(propagation_results)
            console.print(f"[green]✓ Stage 3 complete: {len(propagation_results)} event propagations[/green]")

        # ═══════════════════════════════════════════════════════════════════════
        # STAGE 4: SCORING
        # ═══════════════════════════════════════════════════════════════════════
        if run_scoring and analyses:
            console.print("\n[bold]Stage 4:[/bold] Computing stock scores...")

            # Group analyses by company
            company_analyses: dict[str, list[ArticleIntelligence]] = {}
            for intelligence in analyses:
                for co_mention in intelligence.companies_mentioned:
                    ticker = co_mention.get("ticker", "")
                    if ticker:
                        company_analyses.setdefault(ticker, []).append(intelligence)

            # Score each company
            scores: list[StockScoreComponents] = []
            for ticker, co_analyses in company_analyses.items():
                # Compute financial impacts
                fin_impacts = [
                    compute_financial_impact(a, ticker)
                    for a in co_analyses
                ]

                score = self.scorer.score_from_analyses(
                    company_ticker=ticker,
                    analyses=co_analyses,
                    financial_impacts=fin_impacts,
                    score_date=datetime.now(),
                )
                scores.append(score)

                # Store
                self._latest_scores[ticker] = {
                    "ticker": ticker,
                    "composite_score": score.composite_score,
                    "signal": score.signal,
                    "signal_strength": score.signal_strength,
                    "article_count": score.article_count,
                    "avg_bullish": score.avg_bullish,
                    "avg_bearish": score.avg_bearish,
                    "revenue_score": score.revenue_score,
                    "margin_score": score.margin_score,
                    "industry_shift_score": score.industry_shift_score,
                    "regulatory_score": score.regulatory_score,
                    "sentiment_score": score.sentiment_score,
                    "key_catalysts": score.key_catalysts,
                }

            stats["stocks_scored"] = len(scores)
            console.print(f"[green]✓ Stage 4 complete: {len(scores)} stocks scored[/green]")

        # ═══════════════════════════════════════════════════════════════════════
        # STAGE 5: RANKING
        # ═══════════════════════════════════════════════════════════════════════
        if run_ranking and run_scoring:
            console.print("\n[bold]Stage 5:[/bold] Generating rankings...")

            scores_list = [
                StockScoreComponents(**{k: v for k, v in s.items() if k in StockScoreComponents.__dataclass_fields__})
                for s in self._latest_scores.values()
                if "composite_score" in s
            ]

            if scores_list:
                self._latest_rankings = self.ranker.rank_stocks(scores_list)
                self._latest_rankings["date"] = datetime.now().isoformat()

            # Theme clustering
            self._latest_themes = self.clusterer.cluster(self._latest_articles)

            console.print(f"[green]✓ Stage 5 complete: Rankings generated[/green]")

        # ═══════════════════════════════════════════════════════════════════════
        # STAGE 6: REPORT & SUMMARY
        # ═══════════════════════════════════════════════════════════════════════
        elapsed = (datetime.now() - start_time).total_seconds()
        stats["elapsed_seconds"] = elapsed
        stats["end_time"] = datetime.now().isoformat()

        self._print_summary(stats)
        self._save_daily_report(stats)

        return stats

    def _print_summary(self, stats: dict):
        console.rule("[bold green]Pipeline Complete")

        table = Table(title="Daily Pipeline Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Articles Ingested", str(stats.get("articles_ingested", 0)))
        table.add_row("Articles Analyzed", str(stats.get("articles_analyzed", 0)))
        table.add_row("Analysis Success", str(stats.get("analysis_success", 0)))
        table.add_row("Analysis Failed", str(stats.get("analysis_failed", 0)))
        table.add_row("Stocks Scored", str(stats.get("stocks_scored", 0)))
        table.add_row("Elapsed Time", f"{stats.get('elapsed_seconds', 0):.1f}s")

        console.print(table)

        if self._latest_rankings:
            # Bullish top 5
            console.print("\n[bold green]🐂 TOP 5 BULLISH STOCKS:[/bold green]")
            for stock in self._latest_rankings.get("bullish", [])[:5]:
                console.print(f"  #{stock['rank']} {stock['ticker']:12s} Score: {stock['composite_score']:.1f} | {stock['key_catalyst'][:60]}")

            # Bearish top 5
            console.print("\n[bold red]🐻 TOP 5 BEARISH STOCKS:[/bold red]")
            for stock in self._latest_rankings.get("bearish", [])[:5]:
                console.print(f"  #{stock['rank']} {stock['ticker']:12s} Score: {stock['composite_score']:.1f} | {stock['key_catalyst'][:60]}")

    def _save_daily_report(self, stats: dict):
        """Save daily JSON report to disk."""
        import os
        os.makedirs(settings.REPORTS_DIR, exist_ok=True)
        report_path = f"{settings.REPORTS_DIR}/report_{datetime.now().strftime('%Y%m%d')}.json"

        report = {
            "metadata": stats,
            "rankings": self._latest_rankings,
            "themes": self._latest_themes,
            "scores": self._latest_scores,
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"📁 Daily report saved to {report_path}")

    # ── Query Methods ─────────────────────────────────────────────────────────────

    def get_latest_rankings(self) -> Optional[dict]:
        return self._latest_rankings

    def get_latest_articles(
        self,
        limit: int = 20,
        source: Optional[str] = None,
        sentiment: Optional[str] = None
    ) -> list[dict]:
        result = self._latest_articles
        if source:
            result = [a for a in result if a.get("source", "").lower() == source.lower()]
        return result[:limit]

    def get_latest_themes(self) -> list[dict]:
        return self._latest_themes

    def get_stock_score(self, ticker: str) -> Optional[dict]:
        return self._latest_scores.get(ticker)

    def get_all_scores(self) -> list[dict]:
        return list(self._latest_scores.values())


# ── APScheduler for Cron Jobs ─────────────────────────────────────────────────────

def setup_scheduler(pipeline: PipelineOrchestrator):
    """
    Set up automated daily pipeline schedule.
    Runs Monday–Friday Indian market time (IST).
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    import pytz

    IST = pytz.timezone("Asia/Kolkata")
    scheduler = AsyncIOScheduler(timezone=IST)

    # 08:00 – Full pipeline
    scheduler.add_job(
        func=lambda: asyncio.create_task(pipeline.run_full_pipeline()),
        trigger=CronTrigger(hour=8, minute=0, day_of_week="mon-fri", timezone=IST),
        id="daily_pipeline",
        name="Daily Full Pipeline",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # 12:00 – Midday update (only new articles since 8am)
    scheduler.add_job(
        func=lambda: asyncio.create_task(pipeline.run_full_pipeline(max_articles=200)),
        trigger=CronTrigger(hour=12, minute=0, day_of_week="mon-fri", timezone=IST),
        id="midday_update",
        name="Midday Update",
        replace_existing=True,
    )

    # 15:30 – EOD update
    scheduler.add_job(
        func=lambda: asyncio.create_task(pipeline.run_full_pipeline(max_articles=150)),
        trigger=CronTrigger(hour=15, minute=30, day_of_week="mon-fri", timezone=IST),
        id="eod_update",
        name="End of Day Update",
        replace_existing=True,
    )

    return scheduler
