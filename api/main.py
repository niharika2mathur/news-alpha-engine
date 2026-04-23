# ============================================================
# api/main.py – FastAPI REST API
# Endpoints: trigger pipeline, get rankings, query articles
# ============================================================

import asyncio
import json
from datetime import datetime, date
from typing import Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

from config import settings
from pipeline.orchestrator import PipelineOrchestrator

app = FastAPI(
    title="News Alpha Engine API",
    description="AI-powered stock market intelligence from daily news flow",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline instance
_pipeline: Optional[PipelineOrchestrator] = None
_pipeline_status = {"status": "idle", "last_run": None, "articles_processed": 0}


def get_pipeline() -> PipelineOrchestrator:
    global _pipeline
    if _pipeline is None:
        _pipeline = PipelineOrchestrator()
    return _pipeline


# ── Request/Response Models ──────────────────────────────────────────────────────

class PipelineRunRequest(BaseModel):
    run_ingestion: bool = True
    run_analysis: bool = True
    run_scoring: bool = True
    run_ranking: bool = True
    max_articles: Optional[int] = None


class AnalyzeArticleRequest(BaseModel):
    title: str
    content: str
    source: str = "Manual"
    published_at: Optional[str] = None


class CommodityShockRequest(BaseModel):
    commodity_name: str
    price_change_pct: float


# ── Health ───────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "pipeline_status": _pipeline_status
    }


# ── Pipeline Endpoints ────────────────────────────────────────────────────────────

@app.post("/pipeline/run")
async def run_pipeline(request: PipelineRunRequest, background_tasks: BackgroundTasks):
    """
    Trigger the full daily pipeline in the background.
    Returns immediately with job ID.
    """
    if _pipeline_status["status"] == "running":
        raise HTTPException(status_code=409, detail="Pipeline already running")

    job_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    background_tasks.add_task(
        _run_pipeline_task,
        request.run_ingestion,
        request.run_analysis,
        request.run_scoring,
        request.run_ranking,
        request.max_articles
    )
    return {"job_id": job_id, "status": "started", "message": "Pipeline running in background"}


async def _run_pipeline_task(ingest, analyze, score, rank, max_articles):
    global _pipeline_status
    _pipeline_status["status"] = "running"
    _pipeline_status["last_run"] = datetime.now().isoformat()
    try:
        pipe = get_pipeline()
        result = await pipe.run_full_pipeline(
            run_ingestion=ingest,
            run_analysis=analyze,
            run_scoring=score,
            run_ranking=rank,
            max_articles=max_articles,
        )
        _pipeline_status["articles_processed"] = result.get("articles_ingested", 0)
        _pipeline_status["status"] = "completed"
        logger.info(f"Pipeline completed: {result}")
    except Exception as e:
        _pipeline_status["status"] = "failed"
        _pipeline_status["error"] = str(e)
        logger.error(f"Pipeline failed: {e}")


@app.get("/pipeline/status")
async def pipeline_status():
    return _pipeline_status


# ── Rankings ──────────────────────────────────────────────────────────────────────

@app.get("/rankings/today")
async def get_today_rankings(direction: str = Query("bullish", regex="^(bullish|bearish|all)$")):
    """Get today's top-20 bullish or bearish stocks."""
    pipe = get_pipeline()
    rankings = pipe.get_latest_rankings()
    if not rankings:
        raise HTTPException(status_code=404, detail="No rankings available. Run pipeline first.")

    if direction == "all":
        return rankings
    return {
        "date": rankings.get("date"),
        "direction": direction,
        "stocks": rankings.get(direction, []),
        "summary": rankings.get("summary"),
    }


@app.get("/rankings/heatmap")
async def get_industry_heatmap():
    """Get industry-level sentiment heatmap."""
    pipe = get_pipeline()
    rankings = pipe.get_latest_rankings()
    if not rankings:
        raise HTTPException(status_code=404, detail="No data available")
    return rankings.get("industry_heatmap", {})


# ── Article Analysis ──────────────────────────────────────────────────────────────

@app.post("/analyze/article")
async def analyze_article(request: AnalyzeArticleRequest):
    """
    Analyze a single news article on-demand.
    Returns full structured investment report.
    """
    from analysis.llm_engine import LLMAnalysisEngine

    engine = LLMAnalysisEngine()
    article = {
        "id": -1,
        "title": request.title,
        "content": request.content,
        "source": request.source,
        "published_at": request.published_at or datetime.now().isoformat(),
    }

    intelligence = await engine.analyze_article(article)

    if intelligence.error:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {intelligence.error}")

    report = engine.build_full_report(intelligence, article)

    return {
        "intelligence": {
            "event_type": intelligence.event_type,
            "sentiment": intelligence.sentiment,
            "bullish_score": intelligence.bullish_score,
            "bearish_score": intelligence.bearish_score,
            "net_score": intelligence.net_score,
            "confidence": intelligence.confidence,
            "companies_mentioned": intelligence.companies_mentioned,
            "industries_affected": intelligence.industries_affected,
            "financial_impact": {
                "revenue_impact_pct": intelligence.revenue_impact_pct,
                "margin_impact_bps": intelligence.margin_impact_bps,
                "eps_impact_pct": intelligence.eps_impact_pct,
                "price_impact_pct": intelligence.price_impact_pct,
            },
            "second_order_effects": intelligence.second_order_effects,
        },
        "full_report": report,
    }


# ── Knowledge Graph ───────────────────────────────────────────────────────────────

@app.get("/graph/company/{ticker}")
async def get_company_info(ticker: str):
    """Get company data, industry, and peers from knowledge graph."""
    from graph.knowledge_graph import get_graph
    graph = get_graph()

    co = graph.lookup_company(ticker.upper())
    if not co:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    ind_code = co.get("industry", "")
    peers = graph.get_peers(ticker.upper())
    companies_in_ind = graph.get_companies_in_industry(ind_code)

    return {
        "company": dict(co),
        "industry_code": ind_code,
        "peers": [dict(p) for p in peers[:10]],
        "industry_peers_count": len(companies_in_ind),
    }


@app.post("/graph/commodity-shock")
async def simulate_commodity_shock(request: CommodityShockRequest):
    """
    Simulate a commodity price shock and return margin impact across industries.
    """
    from graph.knowledge_graph import get_graph
    graph = get_graph()

    effects = graph.propagate_commodity_shock(request.commodity_name, request.price_change_pct)

    return {
        "commodity": request.commodity_name,
        "price_change_pct": request.price_change_pct,
        "impact_direction": "negative" if request.price_change_pct > 0 else "positive",
        "affected_industries": [
            {
                "industry": e.target,
                "direction": e.direction,
                "magnitude": e.magnitude,
                "mechanism": e.mechanism,
                "hop": e.hop,
                "propagation_path": e.path,
            }
            for e in effects[:20]
        ]
    }


@app.get("/graph/stats")
async def graph_stats():
    """Knowledge graph statistics."""
    from graph.knowledge_graph import get_graph
    return get_graph().get_stats()


# ── News Feed ─────────────────────────────────────────────────────────────────────

@app.get("/news/latest")
async def get_latest_news(
    limit: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    sentiment: Optional[str] = Query(None, regex="^(bullish|bearish|neutral)$")
):
    """Get latest analyzed news articles."""
    pipe = get_pipeline()
    articles = pipe.get_latest_articles(limit=limit, source=source, sentiment=sentiment)
    return {"articles": articles, "count": len(articles)}


@app.get("/news/themes")
async def get_themes():
    """Get theme clusters from today's news."""
    pipe = get_pipeline()
    return {"themes": pipe.get_latest_themes()}


# ── Stock Scoring ─────────────────────────────────────────────────────────────────

@app.get("/score/{ticker}")
async def get_stock_score(ticker: str):
    """Get today's score and signal for a specific stock."""
    pipe = get_pipeline()
    score = pipe.get_stock_score(ticker.upper())
    if not score:
        raise HTTPException(status_code=404, detail=f"No score found for {ticker}. Run pipeline first.")
    return score


@app.get("/scores/all")
async def get_all_scores():
    """Get all scored stocks for today."""
    pipe = get_pipeline()
    return {"scores": pipe.get_all_scores()}
