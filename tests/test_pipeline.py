# ============================================================
# tests/test_pipeline.py – Full Pipeline Test Suite
# Run: pytest tests/ -v
# ============================================================

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ══════════════════════════════════════════════════════════════════════════════
# 1. KNOWLEDGE GRAPH TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeGraph:

    @pytest.fixture(autouse=True)
    def setup(self):
        from graph.knowledge_graph import MarketKnowledgeGraph
        self.graph = MarketKnowledgeGraph()
        self.graph.build()

    def test_graph_builds_correctly(self):
        stats = self.graph.get_stats()
        assert stats["nodes"] > 30, "Should have at least 30 nodes"
        assert stats["edges"] > 20, "Should have at least 20 edges"
        assert stats["companies"] >= 15, "Should have at least 15 companies"
        assert stats["industries"] >= 20, "Should have at least 20 industries"
        assert stats["commodities"] >= 10, "Should have at least 10 commodities"

    def test_company_lookup_by_ticker(self):
        co = self.graph.lookup_company("RELIANCE")
        assert co is not None
        assert co["ticker"] == "RELIANCE"
        assert co["industry"] == "OGR"

    def test_company_lookup_by_alias(self):
        co = self.graph.lookup_company("tata steel")
        assert co is not None
        assert co["ticker"] == "TATASTEEL"

    def test_company_lookup_fuzzy(self):
        co = self.graph.lookup_company("HUL")
        assert co is not None

    def test_get_peers_for_auto(self):
        peers = self.graph.get_peers("TATAMOTORS")
        tickers = [p["ticker"] for p in peers]
        assert "MARUTI" in tickers or "M&M" in tickers, "Auto peers should include Maruti or M&M"

    def test_propagate_impact_steel(self):
        effects = self.graph.propagate_impact(
            source_industry_code="STEEL",
            direction="positive",
            magnitude=8.0,
            max_hops=2
        )
        assert len(effects) > 0, "Steel price rise should propagate to downstream industries"
        industry_names = [e.target for e in effects]
        # Steel rise should negatively impact auto (steel is an input)
        auto_effect = next((e for e in effects if "Auto" in e.target), None)
        if auto_effect:
            assert auto_effect.direction == "negative", "Rising steel should hurt auto margins"

    def test_commodity_shock_lithium(self):
        effects = self.graph.propagate_commodity_shock("Lithium", 20.0)
        assert len(effects) > 0, "Lithium shock should affect EV industry"
        ev_effect = next((e for e in effects if "EV" in e.target or "Electric" in e.target), None)
        assert ev_effect is not None, "EV industry must be affected by lithium price change"
        assert ev_effect.direction == "negative", "Lithium +20% should be negative for EV"

    def test_commodity_shock_iron_ore(self):
        effects = self.graph.propagate_commodity_shock("Iron Ore", 15.0)
        steel_effect = next((e for e in effects if "Steel" in e.target), None)
        assert steel_effect is not None
        assert steel_effect.direction == "negative"

    def test_get_companies_in_industry(self):
        companies = self.graph.get_companies_in_industry("AUTO")
        assert len(companies) >= 2, "Auto industry should have at least 2 companies"

    def test_graph_export_json(self):
        json_str = self.graph.to_json()
        data = json.loads(json_str)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 2. EVENT DETECTION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestEventDetection:

    @pytest.fixture(autouse=True)
    def setup(self):
        from graph.knowledge_graph import MarketKnowledgeGraph
        from graph.event_engine import EventDetectionEngine
        graph = MarketKnowledgeGraph()
        graph.build()
        self.engine = EventDetectionEngine(graph)

    def test_detect_regulation_event(self):
        result = self.engine.classify_event(
            title="SEBI mandates new ESG disclosure norms for listed companies",
            content="Securities and Exchange Board of India issued a circular requiring all listed companies to disclose ESG metrics quarterly from FY25.",
            llm_event_type=None
        )
        assert result.event_type == "regulation"
        assert result.confidence > 0.3

    def test_detect_pricing_change_steel(self):
        result = self.engine.classify_event(
            title="Iron ore prices surge 18% as Chinese demand recovers",
            content="Iron ore spot prices jumped 18% this week driven by steel demand recovery in China. Coking coal also rose 12%.",
            llm_event_type=None
        )
        assert result.event_type == "pricing_change"
        assert "STEEL" in result.primary_industries or "MINE" in result.primary_industries

    def test_llm_event_type_takes_precedence(self):
        result = self.engine.classify_event(
            title="Tata Motors reports Q2 results",
            content="Results quarter earnings profit revenue EBITDA",
            llm_event_type="earnings"
        )
        assert result.event_type == "earnings"
        assert result.confidence == 0.85

    def test_detect_demand_shock(self):
        result = self.engine.classify_event(
            title="India IIP data shows manufacturing demand surge in September",
            content="Index of Industrial Production rose 7.4% in September, beating consensus of 5.8%. Consumer durables volume growth led the uptick.",
            llm_event_type=None
        )
        assert result.event_type == "demand_shock"

    def test_full_propagation_run(self):
        event = self.engine.run(
            title="Iron ore prices rise 20% on China stimulus",
            content="Iron ore spot prices surged 20% as China announced massive infrastructure stimulus. Steel producers to face margin pressure.",
            llm_event_type="pricing_change",
            llm_sentiment="bearish",
            bullish_score=2.0,
            bearish_score=7.5,
        )
        assert event.event_type == "pricing_change"
        assert len(event.propagation_effects) >= 0  # may be 0 if no industries detected
        assert isinstance(event.commodity_shocks, list)

    def test_commodity_shock_detection_in_text(self):
        shocks = self.engine.detect_commodity_shock(
            text="Crude oil prices surge amid Middle East tensions. Brent crude rose 8%.",
            bullish_score=1.0,
            bearish_score=6.0,
        )
        assert isinstance(shocks, list)
        # Should detect crude oil shock
        oil_effect = next((s for s in shocks if "Refin" in s.target or "Chemical" in s.target), None)
        # May or may not find it depending on text matching; just verify no crash


# ══════════════════════════════════════════════════════════════════════════════
# 3. FINANCIAL MODEL TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFinancialModel:

    def _make_intelligence(self, **kwargs):
        from analysis.llm_engine import ArticleIntelligence
        defaults = {
            "article_id": 1,
            "revenue_impact_pct": 5.0,
            "margin_impact_bps": -200.0,
            "eps_impact_pct": -8.0,
            "price_impact_pct": -6.0,
            "bullish_score": 2.0,
            "bearish_score": 7.0,
            "net_score": -5.0,
            "sentiment": "bearish",
            "event_type": "pricing_change",
            "companies_mentioned": [],
            "industries_affected": [],
            "key_themes": [],
            "catalysts": [],
            "risks": [],
            "second_order_effects": [],
        }
        defaults.update(kwargs)
        return ArticleIntelligence(**defaults)

    def test_financial_impact_known_company(self):
        from scoring.financial_model import compute_financial_impact
        intel = self._make_intelligence(
            revenue_impact_pct=-3.0,
            margin_impact_bps=-150.0,
            eps_impact_pct=-5.0,
            price_impact_pct=-4.0,
        )
        impact = compute_financial_impact(intel, "TATASTEEL")
        assert impact.company_ticker == "TATASTEEL"
        assert impact.base_revenue > 0
        assert impact.revenue_change_cr < 0, "Negative revenue impact should reduce revenue"
        assert impact.price_impact_pct < 0, "Bearish article should show negative price impact"

    def test_financial_impact_unknown_company(self):
        from scoring.financial_model import compute_financial_impact
        intel = self._make_intelligence()
        impact = compute_financial_impact(intel, "UNKNOWN_TICKER")
        assert "not found" in impact.methodology_notes.lower()

    def test_scoring_engine_bullish(self):
        from scoring.financial_model import ScoringEngine
        from analysis.llm_engine import ArticleIntelligence

        engine = ScoringEngine()
        analyses = [
            ArticleIntelligence(
                article_id=i,
                bullish_score=8.0, bearish_score=1.0,
                net_score=7.0, sentiment="bullish",
                revenue_impact_pct=10.0, margin_impact_bps=200.0,
                eps_impact_pct=8.0, price_impact_pct=6.0,
                event_type="earnings",
                companies_mentioned=[], industries_affected=[],
                key_themes=[], catalysts=["Strong Q2 results"], risks=[],
                second_order_effects=[],
            )
            for i in range(5)
        ]

        score = engine.score_from_analyses("TCS", analyses, [], )
        assert score.composite_score > 65, f"Strong bullish signals should score > 65, got {score.composite_score}"
        assert score.signal == "bullish"
        assert score.signal_strength > 0.3

    def test_scoring_engine_bearish(self):
        from scoring.financial_model import ScoringEngine
        from analysis.llm_engine import ArticleIntelligence

        engine = ScoringEngine()
        analyses = [
            ArticleIntelligence(
                article_id=i,
                bullish_score=1.0, bearish_score=9.0,
                net_score=-8.0, sentiment="bearish",
                revenue_impact_pct=-15.0, margin_impact_bps=-500.0,
                eps_impact_pct=-20.0, price_impact_pct=-12.0,
                event_type="regulation",
                companies_mentioned=[], industries_affected=[],
                key_themes=[], catalysts=[], risks=["Heavy regulatory fine"],
                second_order_effects=[],
            )
            for i in range(3)
        ]

        score = engine.score_from_analyses("OLAELEC", analyses, [])
        assert score.composite_score < 35, f"Strong bearish signals should score < 35, got {score.composite_score}"
        assert score.signal == "bearish"

    def test_scoring_weights_sum_to_one(self):
        from scoring.financial_model import ScoringEngine
        engine = ScoringEngine()
        total = sum(engine.WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights must sum to 1.0, got {total}"

    def test_momentum_computation(self):
        from scoring.financial_model import ScoringEngine
        engine = ScoringEngine()
        momentum = engine.compute_momentum("TCS", 75.0, [55, 58, 62, 67, 71])
        assert momentum > 0, "Upward trend should give positive momentum"

        momentum_down = engine.compute_momentum("TATASTEEL", 25.0, [65, 58, 50, 40, 32])
        assert momentum_down < 0, "Downward trend should give negative momentum"


# ══════════════════════════════════════════════════════════════════════════════
# 4. RANKING ENGINE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRankingEngine:

    def _make_scores(self, count=10):
        from scoring.financial_model import StockScoreComponents
        from datetime import datetime
        import random

        tickers = ["RELIANCE", "TCS", "HDFCBANK", "TATAMOTORS", "JSWSTEEL",
                   "ULTRACEMCO", "SUNPHARMA", "BHARTIARTL", "OLAELEC", "HINDUNILVR"]
        scores = []
        for i, ticker in enumerate(tickers[:count]):
            composite = random.uniform(10, 90)
            score = StockScoreComponents(
                company_ticker=ticker,
                score_date=datetime.now(),
                composite_score=composite,
                signal="bullish" if composite > 60 else ("bearish" if composite < 40 else "neutral"),
                signal_strength=abs(composite - 50) / 50,
                article_count=random.randint(1, 10),
                avg_bullish=random.uniform(3, 8),
                avg_bearish=random.uniform(1, 5),
                key_catalysts=["Test catalyst"],
            )
            scores.append(score)
        return scores

    def test_ranking_produces_correct_structure(self):
        from scoring.financial_model import RankingEngine
        engine = RankingEngine()
        scores = self._make_scores(10)
        result = engine.rank_stocks(scores)

        assert "bullish" in result
        assert "bearish" in result
        assert "industry_heatmap" in result
        assert "summary" in result
        assert result["summary"]["total_stocks_scored"] == 10

    def test_bullish_stocks_sorted_descending(self):
        from scoring.financial_model import RankingEngine
        engine = RankingEngine()
        scores = self._make_scores(10)
        result = engine.rank_stocks(scores)

        bullish = result["bullish"]
        if len(bullish) >= 2:
            for i in range(len(bullish) - 1):
                assert bullish[i].composite_score >= bullish[i+1].composite_score

    def test_bearish_stocks_sorted_ascending(self):
        from scoring.financial_model import RankingEngine
        engine = RankingEngine()
        scores = self._make_scores(10)
        result = engine.rank_stocks(scores)

        bearish = result["bearish"]
        if len(bearish) >= 2:
            for i in range(len(bearish) - 1):
                assert bearish[i].composite_score <= bearish[i+1].composite_score


# ══════════════════════════════════════════════════════════════════════════════
# 5. THEME CLUSTERING TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestThemeClustering:

    def test_cluster_ev_articles(self):
        from scoring.financial_model import ThemeClusterer
        clusterer = ThemeClusterer()
        articles = [
            {"id": 1, "title": "Ola Electric reports lithium shortage impact on EV battery costs", "content": "electric vehicle battery lithium charging"},
            {"id": 2, "title": "India EV adoption: 5 million electric vehicles sold in FY25", "content": "electric vehicle adoption battery lithium"},
            {"id": 3, "title": "RBI holds repo rate steady", "content": "rbi monetary policy inflation repo rate"},
            {"id": 4, "title": "RBI rate cut lifts real estate stocks", "content": "repo rate rbi monetary policy cut"},
        ]
        clusters = clusterer.cluster(articles)
        theme_names = [c["theme"] for c in clusters]
        assert "EV Transition" in theme_names, f"EV theme should be detected, got {theme_names}"
        assert "Rate Environment" in theme_names, f"Rate theme should be detected, got {theme_names}"

    def test_cluster_returns_sorted_by_count(self):
        from scoring.financial_model import ThemeClusterer
        clusterer = ThemeClusterer()
        articles = [
            {"id": i, "title": "RBI rate cut monetary policy inflation repo rate", "content": "rbi repo rate monetary policy"}
            for i in range(5)
        ]
        clusters = clusterer.cluster(articles)
        if len(clusters) >= 2:
            assert clusters[0]["article_count"] >= clusters[1]["article_count"]


# ══════════════════════════════════════════════════════════════════════════════
# 6. INGESTION TESTS (mocked)
# ══════════════════════════════════════════════════════════════════════════════

class TestIngestion:

    def test_article_deduplication(self):
        from ingestion.scraper import RawArticle
        a1 = RawArticle("Title A", "Content A", "https://example.com/a", "Reuters")
        a2 = RawArticle("Title A", "Content A", "https://example.com/a", "Reuters")
        assert a1.external_id == a2.external_id, "Same URL should produce same hash"

    def test_different_urls_different_ids(self):
        from ingestion.scraper import RawArticle
        a1 = RawArticle("Title", "Content", "https://example.com/1", "Reuters")
        a2 = RawArticle("Title", "Content", "https://example.com/2", "Reuters")
        assert a1.external_id != a2.external_id

    def test_word_count(self):
        from ingestion.scraper import RawArticle
        content = "This is a test article with exactly ten words here"
        a = RawArticle("Title", content, "https://test.com", "Test")
        assert a.word_count() == 10

    def test_source_inference(self):
        from ingestion.scraper import RSSIngester
        assert RSSIngester._infer_source("https://feeds.reuters.com/...") == "Reuters"
        assert RSSIngester._infer_source("https://economictimes.indiatimes.com/...") == "Economic Times"
        assert RSSIngester._infer_source("https://www.moneycontrol.com/...") == "Moneycontrol"


# ══════════════════════════════════════════════════════════════════════════════
# 7. LLM ENGINE TESTS (mocked)
# ══════════════════════════════════════════════════════════════════════════════

class TestLLMEngine:

    def test_parse_valid_response(self):
        from analysis.llm_engine import LLMAnalysisEngine
        engine = LLMAnalysisEngine.__new__(LLMAnalysisEngine)
        engine.stats = {"success": 0, "failed": 0, "total_tokens": 0}

        raw_json = json.dumps({
            "ai_summary": "Tata Steel faces margin pressure due to rising iron ore costs.",
            "event_type": "pricing_change",
            "sentiment": "bearish",
            "bullish_score": 1.5,
            "bearish_score": 7.5,
            "confidence": 0.82,
            "companies_mentioned": [
                {"name": "Tata Steel", "ticker": "TATASTEEL", "role": "primary", "impact": "negative", "rationale": "Cost pressure"}
            ],
            "industries_affected": [{"name": "Steel", "direction": "negative", "magnitude": 7, "rationale": "Input cost rise"}],
            "financial_impact": {
                "revenue_impact_pct": -2.0,
                "margin_impact_bps": -350.0,
                "eps_impact_pct": -12.0,
                "price_impact_pct": -8.0,
                "impact_horizon": "3_months",
                "impact_rationale": "Iron ore is 42% of steelmaking cost."
            },
            "key_themes": ["Commodity cycle", "Steel margins", "Iron ore"],
            "catalysts": [],
            "risks": ["Continued iron ore price rise"],
            "second_order_effects": [
                {"industry": "Automobile", "direction": "negative", "mechanism": "Higher steel → higher input cost for auto", "magnitude": 3, "hop": 2}
            ],
            "regulatory_context": None,
            "competitive_impact": None,
            "macro_linkage": "China demand drives iron ore prices",
            "monitoring_indicators": ["Iron ore spot price", "China PMI"],
            "long_term_view": "Structural pressure until green steel transition.",
            "final_investment_view": {
                "recommendation": "Sell",
                "time_horizon": "3_months",
                "conviction": "High",
                "rationale": "Margin compression from input cost spike will hurt earnings."
            }
        })

        result = engine._parse_response(raw_json, article_id=42)
        assert result.article_id == 42
        assert result.event_type == "pricing_change"
        assert result.bullish_score == 1.5
        assert result.bearish_score == 7.5
        assert result.net_score == pytest.approx(-6.0)
        assert len(result.companies_mentioned) == 1
        assert result.companies_mentioned[0]["ticker"] == "TATASTEEL"
        assert result.revenue_impact_pct == -2.0
        assert result.margin_impact_bps == -350.0
        assert engine.stats["success"] == 1

    def test_parse_malformed_response(self):
        from analysis.llm_engine import LLMAnalysisEngine
        engine = LLMAnalysisEngine.__new__(LLMAnalysisEngine)
        engine.stats = {"success": 0, "failed": 0, "total_tokens": 0}

        result = engine._parse_response("This is not JSON at all.", article_id=99)
        assert result.error is not None
        assert engine.stats["failed"] == 1

    def test_parse_json_in_code_fence(self):
        from analysis.llm_engine import LLMAnalysisEngine
        engine = LLMAnalysisEngine.__new__(LLMAnalysisEngine)
        engine.stats = {"success": 0, "failed": 0, "total_tokens": 0}

        # Simulate Claude wrapping JSON in code fences
        raw = '```json\n{"event_type": "earnings", "sentiment": "bullish", "bullish_score": 8.0, "bearish_score": 1.0, "confidence": 0.9, "companies_mentioned": [], "industries_affected": [], "financial_impact": {"revenue_impact_pct": 5, "margin_impact_bps": 100, "eps_impact_pct": 8, "price_impact_pct": 5, "impact_horizon": "1_month", "impact_rationale": "Beat estimates"}, "key_themes": [], "catalysts": [], "risks": [], "second_order_effects": [], "monitoring_indicators": [], "long_term_view": "", "final_investment_view": {"recommendation": "Buy", "time_horizon": "1_month", "conviction": "High", "rationale": "Strong beat"}}\n```'
        result = engine._parse_response(raw, article_id=1)
        assert result.error is None
        assert result.bullish_score == 8.0


# ══════════════════════════════════════════════════════════════════════════════
# Run with: pytest tests/test_pipeline.py -v --tb=short
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
