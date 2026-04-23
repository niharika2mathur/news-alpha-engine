#!/usr/bin/env python3
# ============================================================
# scripts/seed_db.py – Seed PostgreSQL with Knowledge Graph Data
# Run once after DB init: python scripts/seed_db.py
# ============================================================

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from loguru import logger
from sqlalchemy import text

from models.db_session import get_async_session, init_db
from models.database import (
    Sector, Industry, Company, Commodity, CommodityIndustryImpact,
    IndustryRelationship
)
from models.knowledge_graph_seed import (
    SECTORS, INDUSTRIES, COMPANIES, COMMODITIES,
    INDUSTRY_RELATIONSHIPS, COMMODITY_INDUSTRY_IMPACTS
)


async def seed():
    logger.info("🌱 Seeding database with knowledge graph data...")

    await init_db()

    async with get_async_session() as session:
        # ── Sectors ───────────────────────────────────────────────────────────────
        sector_map = {}
        for s in SECTORS:
            existing = await session.execute(
                text("SELECT id FROM sectors WHERE code = :code"), {"code": s["code"]}
            )
            row = existing.fetchone()
            if not row:
                sector = Sector(name=s["name"], code=s["code"])
                session.add(sector)
                await session.flush()
                sector_map[s["code"]] = sector.id
                logger.debug(f"  Added sector: {s['name']}")
            else:
                sector_map[s["code"]] = row[0]

        await session.commit()
        logger.info(f"✓ {len(SECTORS)} sectors seeded")

        # ── Industries ────────────────────────────────────────────────────────────
        industry_map = {}
        for ind in INDUSTRIES:
            existing = await session.execute(
                text("SELECT id FROM industries WHERE code = :code"), {"code": ind["code"]}
            )
            row = existing.fetchone()
            if not row:
                industry = Industry(
                    name=ind["name"],
                    code=ind["code"],
                    sector_id=sector_map.get(ind["sector"]),
                    avg_pe_ratio=ind.get("avg_pe"),
                )
                session.add(industry)
                await session.flush()
                industry_map[ind["code"]] = industry.id
            else:
                industry_map[ind["code"]] = row[0]

        await session.commit()
        logger.info(f"✓ {len(INDUSTRIES)} industries seeded")

        # ── Companies ─────────────────────────────────────────────────────────────
        for co in COMPANIES:
            existing = await session.execute(
                text("SELECT id FROM companies WHERE ticker = :t"), {"t": co["ticker"]}
            )
            if not existing.fetchone():
                company = Company(
                    name=co["name"],
                    ticker=co["ticker"],
                    bse_code=co.get("bse_code"),
                    nse_code=co.get("nse_code"),
                    industry_id=industry_map.get(co.get("industry", "")),
                    market_cap=co.get("market_cap"),
                    revenue_ttm=co.get("revenue_ttm"),
                    ebitda_margin=co.get("ebitda_margin"),
                    net_margin=co.get("net_margin"),
                    pe_ratio=co.get("pe_ratio"),
                    eps_ttm=co.get("eps_ttm"),
                    current_price=co.get("current_price"),
                    is_nifty50=co.get("is_nifty50", False),
                    is_sensex=co.get("is_sensex", False),
                    aliases=co.get("aliases", []),
                    description=co.get("description", ""),
                )
                session.add(company)

        await session.commit()
        logger.info(f"✓ {len(COMPANIES)} companies seeded")

        # ── Industry Relationships ────────────────────────────────────────────────
        for rel in INDUSTRY_RELATIONSHIPS:
            up_id = industry_map.get(rel["upstream"])
            dn_id = industry_map.get(rel["downstream"])
            if up_id and dn_id:
                relationship = IndustryRelationship(
                    upstream_industry_id=up_id,
                    downstream_industry_id=dn_id,
                    relationship_type=rel.get("type", "input"),
                    impact_coefficient=rel.get("impact", 0.3),
                    description=rel.get("desc", ""),
                )
                session.add(relationship)

        await session.commit()
        logger.info(f"✓ {len(INDUSTRY_RELATIONSHIPS)} industry relationships seeded")

        # ── Commodities ───────────────────────────────────────────────────────────
        commodity_map = {}
        for com in COMMODITIES:
            existing = await session.execute(
                text("SELECT id FROM commodities WHERE symbol = :s"), {"s": com["symbol"]}
            )
            row = existing.fetchone()
            if not row:
                commodity = Commodity(
                    name=com["name"],
                    symbol=com["symbol"],
                    unit=com.get("unit"),
                    currency=com.get("currency", "USD"),
                    description=com.get("description", ""),
                )
                session.add(commodity)
                await session.flush()
                commodity_map[com["name"]] = commodity.id
            else:
                commodity_map[com["name"]] = row[0]

        await session.commit()
        logger.info(f"✓ {len(COMMODITIES)} commodities seeded")

        # ── Commodity→Industry Impacts ────────────────────────────────────────────
        for ci in COMMODITY_INDUSTRY_IMPACTS:
            com_id = commodity_map.get(ci["commodity"])
            ind_id = industry_map.get(ci["industry"])
            if com_id and ind_id:
                impact = CommodityIndustryImpact(
                    commodity_id=com_id,
                    industry_id=ind_id,
                    cost_as_pct_revenue=ci.get("cost_pct"),
                    margin_sensitivity=ci.get("sensitivity"),
                    direction=ci.get("direction"),
                )
                session.add(impact)

        await session.commit()
        logger.info(f"✓ {len(COMMODITY_INDUSTRY_IMPACTS)} commodity impacts seeded")

    logger.info("🎉 Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
