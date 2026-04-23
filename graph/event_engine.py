# ============================================================
# graph/event_engine.py – Event Detection & Impact Propagation
# ============================================================

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger

from graph.knowledge_graph import MarketKnowledgeGraph, PropagationEffect, get_graph


# ── Event Classification Rules ───────────────────────────────────────────────────

EVENT_RULES = {
    "regulation": {
        "keywords": [
            "sebi", "rbi", "regulation", "regulatory", "ministry", "government policy",
            "policy", "compliance", "ban", "mandate", "approval", "license",
            "antitrust", "cci", "dpiit", "notification", "circular", "ordinance",
            "tax", "gst", "duty", "tariff", "subsidy", "pli scheme", "import duty"
        ],
        "weight": 1.5
    },
    "demand_shock": {
        "keywords": [
            "demand surge", "demand collapse", "demand drop", "order book", "order inflow",
            "consumption", "volume growth", "sales growth", "iip", "gdp", "exports",
            "imports", "trade data", "market growth", "penetration", "adoption"
        ],
        "weight": 1.3
    },
    "supply_shock": {
        "keywords": [
            "shortage", "disruption", "supply chain", "logistics", "port", "inventory",
            "production halt", "plant shutdown", "fire", "flood", "natural disaster",
            "geopolitical", "war", "sanction", "strike", "factory accident", "force majeure"
        ],
        "weight": 1.4
    },
    "pricing_change": {
        "keywords": [
            "price hike", "price cut", "price increase", "price reduction", "tariff",
            "commodity price", "raw material", "input cost", "fuel price", "electricity",
            "steel price", "aluminium price", "oil price", "crude", "inflation", "deflation",
            "realization", "ASP", "average selling price", "MSP",
            "prices surge", "prices rise", "prices fall", "prices drop",
            "iron ore", "coking coal", "spot price", "futures price", "commodity"
        ],
        "weight": 1.2
    },
    "capacity_expansion": {
        "keywords": [
            "capex", "expansion", "new plant", "greenfield", "brownfield", "commissioning",
            "capacity addition", "new factory", "investment", "plant inauguration",
            "production ramp", "gigafactory", "semiconductor fab", "capacity utilization"
        ],
        "weight": 1.1
    },
    "corporate_action": {
        "keywords": [
            "dividend", "bonus shares", "buyback", "rights issue", "demerger", "split",
            "delisting", "ipo", "fpo", "qip", "preferential allotment", "esop",
            "promoter pledge", "promoter buying", "insider trading", "block deal", "bulk deal"
        ],
        "weight": 1.0
    },
    "merger_acquisition": {
        "keywords": [
            "merger", "acquisition", "takeover", "deal", "buyout", "stake purchase",
            "joint venture", "strategic partnership", "collaboration", "mou",
            "open offer", "delisting offer", "open offer", "cci approval"
        ],
        "weight": 1.3
    },
    "earnings": {
        "keywords": [
            "quarterly results", "q1", "q2", "q3", "q4", "earnings", "revenue", "profit",
            "ebitda", "net profit", "pat", "results", "annual results", "guidance",
            "beat estimates", "miss estimates", "margin expansion", "margin compression"
        ],
        "weight": 1.4
    },
    "analyst_action": {
        "keywords": [
            "upgrade", "downgrade", "target price", "buy rating", "sell rating",
            "hold", "overweight", "underweight", "neutral", "outperform", "underperform",
            "price target", "brokerage", "analyst", "goldman sachs", "morgan stanley",
            "nomura", "kotak", "edelweiss", "motilal", "axis capital"
        ],
        "weight": 0.9
    },
    "macro_event": {
        "keywords": [
            "fed", "fomc", "rbi monetary policy", "repo rate", "inflation data", "cpi", "wpi",
            "us fed rate", "dollar", "rupee", "forex", "fii", "dii", "fiis buying",
            "fiis selling", "global macro", "recession", "gdp growth", "budget", "fiscal"
        ],
        "weight": 1.2
    },
    "management_change": {
        "keywords": [
            "ceo", "md", "chairman", "board", "director", "resign", "appoint",
            "management change", "leadership", "cfo", "coo", "succession"
        ],
        "weight": 0.8
    },
    "product_launch": {
        "keywords": [
            "launch", "new product", "new model", "unveil", "debut", "introduce",
            "new vehicle", "new drug", "new platform", "innovation", "patent"
        ],
        "weight": 1.0
    },
}

# Industry keyword mapping for direct detection from news text
INDUSTRY_KEYWORD_MAP = {
    "STEEL": ["steel", "iron ore", "coking coal", "tata steel", "jsw steel", "sail", "blast furnace", "hot rolled", "cold rolled"],
    "AUTO": ["automobile", "car", "vehicle", "suv", "hatchback", "sedan", "maruti", "tata motors", "mahindra", "hyundai", "passenger vehicle", "commercial vehicle"],
    "EV": ["electric vehicle", "ev", "battery", "lithium", "ola electric", "tata ev", "charging", "evse"],
    "PHARMA": ["pharmaceutical", "drug", "medicine", "usfda", "anda", "api", "sun pharma", "dr reddy", "cipla", "divi's", "glenmark"],
    "IT": ["tcs", "infosys", "wipro", "hcl tech", "it services", "software", "outsourcing", "digital transformation", "saas"],
    "BANK": ["bank", "banking", "nbfc", "credit", "loan", "npa", "rbi", "repo rate", "credit growth", "net interest margin", "nim"],
    "FMCG": ["fmcg", "hul", "hindustan unilever", "itc", "nestle", "dabur", "consumer goods", "fmcg volume", "rural demand"],
    "CEMENT": ["cement", "ultratech", "ambuja", "shree cement", "clinker", "blended cement", "housing demand"],
    "OGR": ["reliance", "refinery", "petroleum", "petrol", "diesel", "crude oil", "refining margin", "grim", "gnpf"],
    "POWER": ["power", "electricity", "energy", "renewable", "solar", "wind", "ntpc", "adani power", "tata power", "grid"],
    "TELCO": ["telecom", "airtel", "jio", "5g", "arpu", "subscriber", "broadband", "spectrum", "tariff hike"],
    "INFRA": ["infrastructure", "roads", "highways", "nhai", "railways", "metro", "ports", "airport", "capex"],
    "CAPGD": ["capital goods", "bhel", "siemens", "l&t", "engineering", "order wins", "defence"],
    "REALT": ["real estate", "housing", "property", "realty", "dlf", "godrej properties", "macrotech", "home loan"],
    "MINE": ["mining", "coalfields", "coal india", "vedanta", "nmdc", "iron ore", "coal production", "mining royalty"],
    "CHEM": ["chemicals", "specialty chemicals", "fine chemicals", "agrochemicals", "solvent", "pid6"],
}


@dataclass
class EventDetectionResult:
    event_type: str
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    primary_industries: list[str] = field(default_factory=list)
    secondary_industries: list[str] = field(default_factory=list)
    propagation_effects: list[PropagationEffect] = field(default_factory=list)
    commodity_shocks: list[PropagationEffect] = field(default_factory=list)


class EventDetectionEngine:
    """
    Rule-based event classification combined with LLM-provided event type.
    Triggers appropriate impact propagation through the knowledge graph.
    """

    def __init__(self, graph: Optional[MarketKnowledgeGraph] = None):
        self.graph = graph or get_graph()

    def classify_event(self, title: str, content: str, llm_event_type: str = None) -> EventDetectionResult:
        """
        Classify event type from text. LLM classification takes precedence,
        rule-based is used for validation and industry detection.
        """
        text = (title + " " + content).lower()

        # Score each event type
        scores = {}
        all_matched = {}
        for event_type, config in EVENT_RULES.items():
            matched = [kw for kw in config["keywords"] if kw in text]
            if matched:
                scores[event_type] = len(matched) * config["weight"]
                all_matched[event_type] = matched

        # Pick best from rule-based
        rule_event = max(scores, key=scores.get) if scores else "unknown"
        rule_confidence = min(scores.get(rule_event, 0) / 5, 1.0)

        # Use LLM event type if provided (higher confidence)
        if llm_event_type and llm_event_type != "unknown":
            final_event = llm_event_type
            final_confidence = 0.85
        else:
            final_event = rule_event
            final_confidence = rule_confidence

        # Detect affected industries from text
        primary_industries, secondary_industries = self._detect_industries(text)

        return EventDetectionResult(
            event_type=final_event,
            confidence=final_confidence,
            matched_keywords=all_matched.get(final_event, [])[:5],
            primary_industries=primary_industries,
            secondary_industries=secondary_industries,
        )

    def _detect_industries(self, text: str) -> tuple[list[str], list[str]]:
        """Detect which industries are mentioned in text."""
        primary = []
        secondary = []
        for ind_code, keywords in INDUSTRY_KEYWORD_MAP.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches >= 2:
                primary.append(ind_code)
            elif matches == 1:
                secondary.append(ind_code)
        return primary[:3], secondary[:5]

    def propagate(
        self,
        event: EventDetectionResult,
        direction: str,      # positive / negative
        magnitude: float,    # 0–10
    ) -> list[PropagationEffect]:
        """
        Run impact propagation from detected primary industries.
        Returns all downstream effects sorted by magnitude.
        """
        all_effects: list[PropagationEffect] = []

        for ind_code in event.primary_industries:
            effects = self.graph.propagate_impact(
                source_industry_code=ind_code,
                direction=direction,
                magnitude=magnitude,
                max_hops=3,
                attenuation=0.4
            )
            all_effects.extend(effects)

        # Deduplicate: keep highest magnitude per target industry
        seen: dict[str, PropagationEffect] = {}
        for effect in all_effects:
            key = effect.target
            if key not in seen or effect.magnitude > seen[key].magnitude:
                seen[key] = effect

        return sorted(seen.values(), key=lambda e: e.magnitude, reverse=True)

    def detect_commodity_shock(self, text: str, bullish_score: float, bearish_score: float) -> list[PropagationEffect]:
        """
        Detect commodity price changes in news and simulate margin impact.
        """
        text_lower = text.lower()
        shocks = []

        commodity_signals = [
            ("iron ore", "Iron Ore", True),
            ("coking coal", "Coking Coal", True),
            ("crude oil", "Crude Oil (Brent)", True),
            ("brent", "Crude Oil (Brent)", True),
            ("lithium", "Lithium", True),
            ("aluminium", "Aluminium", True),
            ("copper", "Copper", True),
            ("natural gas", "Natural Gas", True),
            ("urea", "Urea", True),
            ("palm oil", "Palm Oil", True),
        ]

        # Determine price direction from sentiment context
        price_rising_words = ["surge", "spike", "rise", "increase", "higher", "up", "rally", "jump", "gain"]
        price_falling_words = ["fall", "drop", "decline", "lower", "down", "crash", "plunge", "cut", "reduce"]

        price_rising = any(w in text_lower for w in price_rising_words)
        price_falling = any(w in text_lower for w in price_falling_words)

        for keyword, commodity_name, _ in commodity_signals:
            if keyword in text_lower:
                # Estimate % change from bullish/bearish score
                if price_rising and not price_falling:
                    price_change = bullish_score * 1.5   # rough estimate
                elif price_falling and not price_rising:
                    price_change = -bearish_score * 1.5
                else:
                    continue

                if abs(price_change) < 1:
                    continue

                effects = self.graph.propagate_commodity_shock(commodity_name, price_change)
                shocks.extend(effects)
                logger.debug(f"Commodity shock: {commodity_name} {price_change:+.1f}% → {len(effects)} effects")

        return shocks

    def run(
        self,
        title: str,
        content: str,
        llm_event_type: str,
        llm_sentiment: str,
        bullish_score: float,
        bearish_score: float,
    ) -> EventDetectionResult:
        """
        Full event processing pipeline:
        1. Classify event
        2. Detect industries
        3. Propagate impact
        4. Simulate commodity shocks
        """
        event = self.classify_event(title, content, llm_event_type)

        direction = "positive" if llm_sentiment == "bullish" else "negative"
        magnitude = max(bullish_score, bearish_score)

        event.propagation_effects = self.propagate(event, direction, magnitude)
        event.commodity_shocks = self.detect_commodity_shock(
            title + " " + content, bullish_score, bearish_score
        )

        logger.debug(
            f"Event: {event.event_type} | Industries: {event.primary_industries} | "
            f"Propagations: {len(event.propagation_effects)}"
        )
        return event


# ── Example Propagation Chains (for documentation / testing) ─────────────────────

EXAMPLE_CHAINS = {
    "lithium_ev_auto": {
        "trigger": "Lithium prices surge 20%",
        "chain": [
            "Lithium ↑20% → EV battery cost ↑ (~25% of EV cost) → EV margin compression -300bps",
            "EV margin compression → EV manufacturers (Ola Electric, Tata EV) bearish",
            "EV cost pressure → ICE auto demand supported (competitive substitute) → Maruti bullish",
            "Lithium shortage → Mining companies (if domestic) bullish"
        ]
    },
    "steel_auto_capgd": {
        "trigger": "Steel prices rise 15%",
        "chain": [
            "Steel ↑15% → Auto material cost ↑ (~18% of BOM) → Auto margin -150bps",
            "Steel ↑15% → Capital goods input cost ↑ → L&T, BHEL margin -100bps",
            "Steel ↑15% → Infrastructure project cost ↑ → Project IRR compression",
            "Steel ↑15% → JSW Steel, Tata Steel revenue/margin boost → Bullish"
        ]
    },
    "rbi_rate_cut": {
        "trigger": "RBI cuts repo rate 25bps",
        "chain": [
            "Rate cut → Borrowing costs fall → Real estate affordability improves → DLF, Godrej bullish",
            "Rate cut → NIM pressure on banks → HDFC, ICICI near-term bearish",
            "Rate cut → Housing demand stimulus → Cement, Steel demand improves",
            "Rate cut → Auto loan rates fall → Passenger vehicle demand supports"
        ]
    }
}
