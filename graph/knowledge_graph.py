# ============================================================
# graph/knowledge_graph.py – Market Knowledge Graph Engine
# Builds and queries the industry/company/commodity network
# ============================================================

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Optional
import networkx as nx
from loguru import logger

from models.knowledge_graph_seed import (
    SECTORS, INDUSTRIES, COMPANIES, COMMODITIES,
    INDUSTRY_RELATIONSHIPS, COMMODITY_INDUSTRY_IMPACTS
)


# ── Graph Node Types ─────────────────────────────────────────────────────────────

NODE_COMPANY = "company"
NODE_INDUSTRY = "industry"
NODE_SECTOR = "sector"
NODE_COMMODITY = "commodity"

EDGE_MEMBER_OF = "member_of"         # company → industry
EDGE_INPUT = "input"                 # upstream industry → downstream
EDGE_OUTPUT = "output"               # industry → end market
EDGE_COMPETITION = "competition"     # industry ↔ industry (substitutes)
EDGE_CREDIT = "credit"               # bank → real estate, etc.
EDGE_COMMODITY_IMPACT = "commodity_input"  # commodity → industry


@dataclass
class PropagationEffect:
    target: str          # industry or company name
    target_type: str     # industry / company
    direction: str       # positive / negative / neutral
    magnitude: float     # 0–10
    mechanism: str       # explanation
    hop: int             # 1=direct, 2=second-order, 3=third-order
    path: list[str] = field(default_factory=list)


class MarketKnowledgeGraph:
    """
    Directed graph representing:
    - Company → Industry (membership)
    - Industry → Industry (supply chain inputs/outputs)
    - Commodity → Industry (cost driver)
    - Sector → Industry (hierarchy)

    Supports:
    - Industry lookup for a company
    - Impact propagation (BFS with attenuation)
    - Company peer identification
    - Supply chain shock simulation
    """

    def __init__(self):
        self.G = nx.DiGraph()
        self._company_index: dict[str, str] = {}   # name/alias → company_id
        self._ticker_index: dict[str, dict] = {}   # ticker → company data
        self._industry_index: dict[str, dict] = {} # code → industry data
        self._built = False

    def build(self):
        """Construct graph from seed data."""
        logger.info("🏗️  Building Market Knowledge Graph...")

        # ── Add Sector nodes ────────────────────────────────────────────────────
        for s in SECTORS:
            self.G.add_node(
                f"sector:{s['code']}",
                node_type=NODE_SECTOR,
                name=s["name"],
                code=s["code"]
            )

        # ── Add Industry nodes ───────────────────────────────────────────────────
        for ind in INDUSTRIES:
            node_id = f"industry:{ind['code']}"
            self.G.add_node(
                node_id,
                node_type=NODE_INDUSTRY,
                name=ind["name"],
                code=ind["code"],
                avg_pe=ind.get("avg_pe", 20.0)
            )
            self._industry_index[ind["code"]] = ind
            self._industry_index[ind["name"].lower()] = ind

            # Edge: Sector → Industry
            self.G.add_edge(
                f"sector:{ind['sector']}",
                node_id,
                edge_type=EDGE_MEMBER_OF
            )

        # ── Add Company nodes ────────────────────────────────────────────────────
        for co in COMPANIES:
            node_id = f"company:{co['ticker']}"
            self.G.add_node(
                node_id,
                node_type=NODE_COMPANY,
                **{k: v for k, v in co.items() if k != "aliases"}
            )
            self._ticker_index[co["ticker"]] = co

            # Register aliases for NLP lookup
            for alias in co.get("aliases", []):
                self._company_index[alias.lower()] = node_id
            self._company_index[co["name"].lower()] = node_id
            self._company_index[co["ticker"].lower()] = node_id

            # Edge: Company → Industry
            if co.get("industry"):
                self.G.add_edge(
                    node_id,
                    f"industry:{co['industry']}",
                    edge_type=EDGE_MEMBER_OF
                )

        # ── Add Industry Relationship edges ──────────────────────────────────────
        for rel in INDUSTRY_RELATIONSHIPS:
            up = f"industry:{rel['upstream']}"
            dn = f"industry:{rel['downstream']}"
            if up in self.G and dn in self.G:
                self.G.add_edge(
                    up, dn,
                    edge_type=rel.get("type", EDGE_INPUT),
                    impact=rel["impact"],
                    direction=rel["direction"],
                    description=rel.get("desc", "")
                )

        # ── Add Commodity nodes ──────────────────────────────────────────────────
        for com in COMMODITIES:
            node_id = f"commodity:{com['symbol']}"
            self.G.add_node(
                node_id,
                node_type=NODE_COMMODITY,
                **com
            )

        # ── Add Commodity → Industry edges ───────────────────────────────────────
        for ci in COMMODITY_INDUSTRY_IMPACTS:
            # Find commodity node
            commodity_node = None
            for com in COMMODITIES:
                if com["name"] == ci["commodity"]:
                    commodity_node = f"commodity:{com['symbol']}"
                    break
            industry_node = f"industry:{ci['industry']}"

            if commodity_node and commodity_node in self.G and industry_node in self.G:
                self.G.add_edge(
                    commodity_node,
                    industry_node,
                    edge_type=EDGE_COMMODITY_IMPACT,
                    cost_pct=ci["cost_pct"],
                    sensitivity=ci["sensitivity"],
                    direction=ci["direction"]
                )

        self._built = True
        logger.info(
            f"✅ Graph built: {self.G.number_of_nodes()} nodes, "
            f"{self.G.number_of_edges()} edges"
        )

    def lookup_company(self, name_or_ticker: str) -> Optional[dict]:
        """Fuzzy lookup: find company data by name, alias, or ticker."""
        key = name_or_ticker.lower().strip()

        # Exact match
        node_id = self._company_index.get(key)
        if node_id and node_id in self.G:
            return self.G.nodes[node_id]

        # Partial match
        for alias, nid in self._company_index.items():
            if key in alias or alias in key:
                if nid in self.G:
                    return self.G.nodes[nid]

        return None

    def get_industry_of_company(self, ticker: str) -> Optional[str]:
        """Return industry code for a company ticker."""
        node_id = f"company:{ticker}"
        if node_id not in self.G:
            return None
        co_data = self.G.nodes[node_id]
        return co_data.get("industry")

    def get_peers(self, ticker: str) -> list[dict]:
        """Return all companies in the same industry."""
        ind_code = self.get_industry_of_company(ticker)
        if not ind_code:
            return []
        industry_node = f"industry:{ind_code}"
        peers = []
        for node, data in self.G.nodes(data=True):
            if data.get("node_type") == NODE_COMPANY and data.get("industry") == ind_code:
                if data.get("ticker") != ticker:
                    peers.append(data)
        return peers

    def propagate_impact(
        self,
        source_industry_code: str,
        direction: str,        # "positive" or "negative"
        magnitude: float,      # 0–10
        max_hops: int = 3,
        attenuation: float = 0.4   # each hop reduces impact by this factor
    ) -> list[PropagationEffect]:
        """
        BFS propagation: starting from a source industry,
        compute cascading effects on downstream industries.

        Example:
        Iron ore price spike (magnitude=8, direction=negative)
        → Steel margins compress (hop=1, magnitude=8*0.45=3.6)
        → Auto cost rises (hop=2, magnitude=3.6*0.18=0.65)
        → Real Estate rises (hop=2, magnitude=3.6*0.12=0.43)
        """
        source_node = f"industry:{source_industry_code}"
        if source_node not in self.G:
            logger.warning(f"Industry {source_industry_code} not found in graph")
            return []

        effects: list[PropagationEffect] = []
        visited = {source_node}
        queue = [(source_node, magnitude, 1, [source_industry_code])]

        while queue:
            current_node, current_mag, hop, path = queue.pop(0)
            if hop > max_hops:
                continue

            # Traverse all outgoing edges
            for _, neighbor, edge_data in self.G.out_edges(current_node, data=True):
                if neighbor in visited:
                    continue
                if self.G.nodes[neighbor].get("node_type") != NODE_INDUSTRY:
                    continue

                visited.add(neighbor)
                edge_impact = edge_data.get("impact", 0.3)
                edge_dir = edge_data.get("direction", "-")
                edge_type = edge_data.get("edge_type", "input")

                # Compute propagated magnitude
                prop_mag = current_mag * edge_impact

                # Determine propagated direction
                if edge_dir == "-":
                    # Negative input relationship: cost increase → margin compression
                    prop_direction = "negative" if direction == "positive" else "positive"
                else:
                    prop_direction = direction

                neighbor_name = self.G.nodes[neighbor].get("name", neighbor)
                neighbor_code = self.G.nodes[neighbor].get("code", "")

                mechanism = self._build_mechanism(
                    current_node, neighbor, edge_data, direction, prop_direction, prop_mag
                )

                effect = PropagationEffect(
                    target=neighbor_name,
                    target_type=NODE_INDUSTRY,
                    direction=prop_direction,
                    magnitude=round(prop_mag, 2),
                    mechanism=mechanism,
                    hop=hop,
                    path=path + [neighbor_code]
                )
                effects.append(effect)

                # Continue propagating if magnitude is still meaningful
                if prop_mag > 0.5 and hop < max_hops:
                    queue.append((neighbor, prop_mag * attenuation, hop + 1, path + [neighbor_code]))

        # Sort by magnitude descending
        effects.sort(key=lambda e: e.magnitude, reverse=True)
        return effects

    def propagate_commodity_shock(
        self,
        commodity_name: str,
        price_change_pct: float   # e.g. +20 means 20% price rise
    ) -> list[PropagationEffect]:
        """
        Simulate a commodity price shock and compute margin impact across industries.
        Returns PropagationEffect list with financial magnitudes.
        """
        effects = []
        for ci in COMMODITY_INDUSTRY_IMPACTS:
            if commodity_name.lower() in ci["commodity"].lower():
                ind_code = ci["industry"]
                # Margin impact = price_change_pct × cost_as_pct_revenue / 100 × -1 (for cost increase)
                margin_impact_bps = price_change_pct * ci["cost_pct"] / 100 * (-1 if price_change_pct > 0 else 1) * 100
                direction = "negative" if price_change_pct > 0 else "positive"
                magnitude = abs(margin_impact_bps) / 50  # normalize to 0–10

                ind_name = self._industry_index.get(ind_code, {}).get("name", ind_code)
                effects.append(PropagationEffect(
                    target=ind_name,
                    target_type=NODE_INDUSTRY,
                    direction=direction,
                    magnitude=min(magnitude, 10),
                    mechanism=f"{commodity_name} {'+' if price_change_pct > 0 else ''}{price_change_pct:.1f}% "
                              f"→ {ci['cost_pct']}% of {ind_name} cost → "
                              f"{margin_impact_bps:.0f} bps margin {'compression' if direction == 'negative' else 'expansion'}",
                    hop=1,
                    path=[commodity_name, ind_code]
                ))

                # Further propagate from this industry
                sub_effects = self.propagate_impact(
                    ind_code,
                    direction=direction,
                    magnitude=min(magnitude, 10),
                    max_hops=2
                )
                for se in sub_effects:
                    se.hop += 1
                effects.extend(sub_effects)

        return effects

    def get_companies_in_industry(self, industry_code: str) -> list[dict]:
        """Return all companies in a given industry."""
        return [
            data for _, data in self.G.nodes(data=True)
            if data.get("node_type") == NODE_COMPANY
            and data.get("industry") == industry_code
        ]

    def to_json(self) -> str:
        """Export graph as JSON for visualization."""
        nodes = []
        for nid, data in self.G.nodes(data=True):
            nodes.append({"id": nid, **data})
        edges = []
        for src, tgt, data in self.G.edges(data=True):
            edges.append({"source": src, "target": tgt, **data})
        return json.dumps({"nodes": nodes, "edges": edges}, default=str)

    def _build_mechanism(self, src, tgt, edge_data, in_dir, out_dir, magnitude) -> str:
        src_name = self.G.nodes[src].get("name", src)
        tgt_name = self.G.nodes[tgt].get("name", tgt)
        edge_type = edge_data.get("edge_type", "input")
        desc = edge_data.get("description", "")
        return (
            f"{src_name} ({in_dir}) → [{edge_type}] → "
            f"{tgt_name} ({out_dir}, magnitude={magnitude:.1f}). "
            f"{desc}"
        )

    def get_stats(self) -> dict:
        return {
            "nodes": self.G.number_of_nodes(),
            "edges": self.G.number_of_edges(),
            "companies": sum(1 for _, d in self.G.nodes(data=True) if d.get("node_type") == NODE_COMPANY),
            "industries": sum(1 for _, d in self.G.nodes(data=True) if d.get("node_type") == NODE_INDUSTRY),
            "commodities": sum(1 for _, d in self.G.nodes(data=True) if d.get("node_type") == NODE_COMMODITY),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────────
_graph_instance: Optional[MarketKnowledgeGraph] = None

def get_graph() -> MarketKnowledgeGraph:
    global _graph_instance
    if _graph_instance is None or not _graph_instance._built:
        _graph_instance = MarketKnowledgeGraph()
        _graph_instance.build()
    return _graph_instance
