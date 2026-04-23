# ============================================================
# models/knowledge_graph_seed.py – Knowledge Graph Seed Data
# Indian Market: Companies, Industries, Commodities, Relations
# ============================================================

SECTORS = [
    {"name": "Energy", "code": "ENERGY"},
    {"name": "Materials", "code": "MATRL"},
    {"name": "Industrials", "code": "INDUS"},
    {"name": "Consumer Discretionary", "code": "CDIS"},
    {"name": "Consumer Staples", "code": "CSTPL"},
    {"name": "Healthcare", "code": "HLTH"},
    {"name": "Financials", "code": "FIN"},
    {"name": "Technology", "code": "TECH"},
    {"name": "Telecommunication", "code": "TELCO"},
    {"name": "Utilities", "code": "UTIL"},
    {"name": "Real Estate", "code": "REALE"},
]

INDUSTRIES = [
    # Energy
    {"name": "Oil & Gas Exploration", "code": "OGE", "sector": "ENERGY", "avg_pe": 8.5},
    {"name": "Oil & Gas Refining", "code": "OGR", "sector": "ENERGY", "avg_pe": 9.0},
    {"name": "Renewable Energy", "code": "RENEW", "sector": "ENERGY", "avg_pe": 28.0},
    {"name": "Power Generation", "code": "POWER", "sector": "ENERGY", "avg_pe": 15.0},
    # Materials
    {"name": "Steel", "code": "STEEL", "sector": "MATRL", "avg_pe": 10.0},
    {"name": "Aluminium", "code": "ALUM", "sector": "MATRL", "avg_pe": 10.5},
    {"name": "Cement", "code": "CEMENT", "sector": "MATRL", "avg_pe": 22.0},
    {"name": "Chemicals", "code": "CHEM", "sector": "MATRL", "avg_pe": 25.0},
    {"name": "Mining", "code": "MINE", "sector": "MATRL", "avg_pe": 9.0},
    {"name": "Fertilizers", "code": "FERT", "sector": "MATRL", "avg_pe": 11.0},
    # Industrials
    {"name": "Capital Goods", "code": "CAPGD", "sector": "INDUS", "avg_pe": 35.0},
    {"name": "Defence", "code": "DEF", "sector": "INDUS", "avg_pe": 40.0},
    {"name": "Infrastructure", "code": "INFRA", "sector": "INDUS", "avg_pe": 30.0},
    # Consumer Discretionary
    {"name": "Automobile", "code": "AUTO", "sector": "CDIS", "avg_pe": 20.0},
    {"name": "Auto Components", "code": "AUTOCOMP", "sector": "CDIS", "avg_pe": 18.0},
    {"name": "Electric Vehicles", "code": "EV", "sector": "CDIS", "avg_pe": 45.0},
    {"name": "Consumer Durables", "code": "CDUR", "sector": "CDIS", "avg_pe": 32.0},
    {"name": "Real Estate", "code": "REALT", "sector": "CDIS", "avg_pe": 25.0},
    {"name": "Hotels & Hospitality", "code": "HOTEL", "sector": "CDIS", "avg_pe": 30.0},
    {"name": "Retail", "code": "RETAIL", "sector": "CDIS", "avg_pe": 60.0},
    # Consumer Staples
    {"name": "FMCG", "code": "FMCG", "sector": "CSTPL", "avg_pe": 45.0},
    {"name": "Food Processing", "code": "FOOD", "sector": "CSTPL", "avg_pe": 30.0},
    {"name": "Agri & Allied", "code": "AGRI", "sector": "CSTPL", "avg_pe": 20.0},
    # Healthcare
    {"name": "Pharmaceuticals", "code": "PHARMA", "sector": "HLTH", "avg_pe": 28.0},
    {"name": "Hospitals", "code": "HOSP", "sector": "HLTH", "avg_pe": 55.0},
    {"name": "Medical Devices", "code": "MEDDEV", "sector": "HLTH", "avg_pe": 35.0},
    # Financials
    {"name": "Banking", "code": "BANK", "sector": "FIN", "avg_pe": 12.0},
    {"name": "NBFC", "code": "NBFC", "sector": "FIN", "avg_pe": 18.0},
    {"name": "Insurance", "code": "INS", "sector": "FIN", "avg_pe": 25.0},
    {"name": "Asset Management", "code": "AMC", "sector": "FIN", "avg_pe": 35.0},
    # Technology
    {"name": "IT Services", "code": "IT", "sector": "TECH", "avg_pe": 28.0},
    {"name": "Semiconductors", "code": "SEMI", "sector": "TECH", "avg_pe": 35.0},
    {"name": "Software Products", "code": "SWPROD", "sector": "TECH", "avg_pe": 40.0},
    # Telecom
    {"name": "Telecom Services", "code": "TELCO", "sector": "TELCO", "avg_pe": 20.0},
    {"name": "Telecom Equipment", "code": "TELEQP", "sector": "TELCO", "avg_pe": 22.0},
]

COMPANIES = [
    # ── Tata Group ──────────────────────────────────────────────────────────────
    {
        "name": "Tata Motors", "ticker": "TATAMOTORS", "bse_code": "500570",
        "nse_code": "TATAMOTORS", "industry": "AUTO",
        "market_cap": 270000, "revenue_ttm": 437928, "ebitda_margin": 11.2,
        "net_margin": 4.8, "pe_ratio": 9.8, "eps_ttm": 63.5,
        "current_price": 735, "is_sensex": True,
        "aliases": ["Tata Motors", "TATAMOTORS", "TML", "Tata Auto"],
        "description": "India's largest automobile manufacturer. Owns Jaguar Land Rover."
    },
    {
        "name": "Tata Steel", "ticker": "TATASTEEL", "bse_code": "500470",
        "nse_code": "TATASTEEL", "industry": "STEEL",
        "market_cap": 165000, "revenue_ttm": 222500, "ebitda_margin": 12.5,
        "net_margin": 3.2, "pe_ratio": 16.2, "eps_ttm": 8.5,
        "current_price": 139, "is_nifty50": True,
        "aliases": ["Tata Steel", "TATASTEEL", "TSL"],
        "description": "Tata Group steel company. Operates in India, UK (Port Talbot) and Netherlands."
    },
    {
        "name": "TCS", "ticker": "TCS", "bse_code": "532540",
        "nse_code": "TCS", "industry": "IT",
        "market_cap": 1380000, "revenue_ttm": 241240, "ebitda_margin": 28.1,
        "net_margin": 19.5, "pe_ratio": 28.5, "eps_ttm": 130.0,
        "current_price": 3700, "is_nifty50": True, "is_sensex": True,
        "aliases": ["TCS", "Tata Consultancy", "Tata Consultancy Services"],
        "description": "India's largest IT services company. Serves BFSI, Retail, and Manufacturing."
    },
    # ── Reliance ────────────────────────────────────────────────────────────────
    {
        "name": "Reliance Industries", "ticker": "RELIANCE", "bse_code": "500325",
        "nse_code": "RELIANCE", "industry": "OGR",
        "market_cap": 1720000, "revenue_ttm": 899279, "ebitda_margin": 18.2,
        "net_margin": 7.8, "pe_ratio": 25.3, "eps_ttm": 97.0,
        "current_price": 2452, "is_nifty50": True, "is_sensex": True,
        "aliases": ["Reliance", "RIL", "Reliance Industries", "Mukesh Ambani company"],
        "description": "India's largest conglomerate. O&G, Retail (JioMart), Telecom (Jio), Green Energy."
    },
    # ── JSW Group ───────────────────────────────────────────────────────────────
    {
        "name": "JSW Steel", "ticker": "JSWSTEEL", "bse_code": "500228",
        "nse_code": "JSWSTEEL", "industry": "STEEL",
        "market_cap": 188000, "revenue_ttm": 166000, "ebitda_margin": 15.8,
        "net_margin": 6.5, "pe_ratio": 17.4, "eps_ttm": 45.3,
        "current_price": 780, "is_nifty50": True,
        "aliases": ["JSW Steel", "JSWSTEEL", "JSW"],
        "description": "India's largest private steel producer. Capacity of 28 MT."
    },
    {
        "name": "JSW Energy", "ticker": "JSWENERGY", "bse_code": "533148",
        "nse_code": "JSWENERGY", "industry": "POWER",
        "market_cap": 78000, "revenue_ttm": 12500, "ebitda_margin": 42.0,
        "net_margin": 18.2, "pe_ratio": 35.0, "eps_ttm": 10.5,
        "current_price": 370,
        "aliases": ["JSW Energy", "JSWENERGY"],
        "description": "Power generation company. Expanding into renewables aggressively."
    },
    # ── Auto ────────────────────────────────────────────────────────────────────
    {
        "name": "Maruti Suzuki", "ticker": "MARUTI", "bse_code": "532500",
        "nse_code": "MARUTI", "industry": "AUTO",
        "market_cap": 325000, "revenue_ttm": 135000, "ebitda_margin": 12.8,
        "net_margin": 8.5, "pe_ratio": 27.0, "eps_ttm": 390.0,
        "current_price": 10500, "is_nifty50": True, "is_sensex": True,
        "aliases": ["Maruti", "Maruti Suzuki", "MARUTI"],
        "description": "India's largest passenger car maker. 42% market share."
    },
    {
        "name": "Mahindra & Mahindra", "ticker": "M&M", "bse_code": "500520",
        "nse_code": "M&M", "industry": "AUTO",
        "market_cap": 275000, "revenue_ttm": 132000, "ebitda_margin": 15.2,
        "net_margin": 8.8, "pe_ratio": 25.0, "eps_ttm": 88.0,
        "current_price": 2200, "is_nifty50": True,
        "aliases": ["M&M", "Mahindra", "M and M"],
        "description": "SUV and tractor leader. Aggressive EV roadmap (BE 6e, XEV 9e)."
    },
    # ── Pharma ──────────────────────────────────────────────────────────────────
    {
        "name": "Sun Pharmaceuticals", "ticker": "SUNPHARMA", "bse_code": "524715",
        "nse_code": "SUNPHARMA", "industry": "PHARMA",
        "market_cap": 380000, "revenue_ttm": 47800, "ebitda_margin": 28.5,
        "net_margin": 20.3, "pe_ratio": 40.0, "eps_ttm": 40.0,
        "current_price": 1580, "is_nifty50": True,
        "aliases": ["Sun Pharma", "SUNPHARMA", "Sun Pharmaceutical"],
        "description": "India's largest pharma company. Major US generics player."
    },
    # ── Banking ─────────────────────────────────────────────────────────────────
    {
        "name": "HDFC Bank", "ticker": "HDFCBANK", "bse_code": "500180",
        "nse_code": "HDFCBANK", "industry": "BANK",
        "market_cap": 1220000, "revenue_ttm": 245000, "ebitda_margin": 35.0,
        "net_margin": 24.0, "pe_ratio": 18.5, "eps_ttm": 92.0,
        "current_price": 1700, "is_nifty50": True, "is_sensex": True,
        "aliases": ["HDFC Bank", "HDFCBANK", "HDFC"],
        "description": "India's largest private bank by assets."
    },
    {
        "name": "ICICI Bank", "ticker": "ICICIBANK", "bse_code": "532174",
        "nse_code": "ICICIBANK", "industry": "BANK",
        "market_cap": 890000, "revenue_ttm": 185000, "ebitda_margin": 33.0,
        "net_margin": 22.0, "pe_ratio": 17.0, "eps_ttm": 72.0,
        "current_price": 1260, "is_nifty50": True, "is_sensex": True,
        "aliases": ["ICICI Bank", "ICICIBANK", "ICICI"],
        "description": "India's second largest private bank. Strong retail franchise."
    },
    # ── FMCG ────────────────────────────────────────────────────────────────────
    {
        "name": "Hindustan Unilever", "ticker": "HINDUNILVR", "bse_code": "500696",
        "nse_code": "HINDUNILVR", "industry": "FMCG",
        "market_cap": 520000, "revenue_ttm": 60000, "ebitda_margin": 24.5,
        "net_margin": 16.8, "pe_ratio": 52.0, "eps_ttm": 45.0,
        "current_price": 2350, "is_sensex": True,
        "aliases": ["HUL", "Hindustan Unilever", "HINDUNILVR", "Unilever India"],
        "description": "India's largest FMCG company. Brands: Lux, Surf, Dove, Horlicks."
    },
    # ── Cement ──────────────────────────────────────────────────────────────────
    {
        "name": "UltraTech Cement", "ticker": "ULTRACEMCO", "bse_code": "532538",
        "nse_code": "ULTRACEMCO", "industry": "CEMENT",
        "market_cap": 325000, "revenue_ttm": 67000, "ebitda_margin": 22.0,
        "net_margin": 11.5, "pe_ratio": 38.0, "eps_ttm": 250.0,
        "current_price": 9500, "is_nifty50": True,
        "aliases": ["UltraTech", "ULTRACEMCO", "Ultratech Cement"],
        "description": "India's largest cement company. 140 MT capacity."
    },
    # ── Infra / Capital Goods ───────────────────────────────────────────────────
    {
        "name": "Larsen & Toubro", "ticker": "LT", "bse_code": "500510",
        "nse_code": "LT", "industry": "CAPGD",
        "market_cap": 480000, "revenue_ttm": 220000, "ebitda_margin": 12.5,
        "net_margin": 8.2, "pe_ratio": 37.0, "eps_ttm": 120.0,
        "current_price": 3450, "is_nifty50": True, "is_sensex": True,
        "aliases": ["L&T", "Larsen Toubro", "LT", "Larsen & Toubro"],
        "description": "India's largest infrastructure and engineering conglomerate."
    },
    # ── Metals ──────────────────────────────────────────────────────────────────
    {
        "name": "Hindalco Industries", "ticker": "HINDALCO", "bse_code": "500440",
        "nse_code": "HINDALCO", "industry": "ALUM",
        "market_cap": 130000, "revenue_ttm": 225000, "ebitda_margin": 13.5,
        "net_margin": 5.8, "pe_ratio": 12.0, "eps_ttm": 55.0,
        "current_price": 660, "is_nifty50": True,
        "aliases": ["Hindalco", "HINDALCO", "Novelis"],
        "description": "World's largest aluminium rolling company. Owns Novelis globally."
    },
    # ── EV ──────────────────────────────────────────────────────────────────────
    {
        "name": "Ola Electric", "ticker": "OLAELEC", "bse_code": "544225",
        "nse_code": "OLAELEC", "industry": "EV",
        "market_cap": 25000, "revenue_ttm": 5010, "ebitda_margin": -12.0,
        "net_margin": -25.0, "pe_ratio": None, "eps_ttm": -8.5,
        "current_price": 55,
        "aliases": ["Ola Electric", "OLAELEC", "Ola EV"],
        "description": "India's largest EV scooter maker. Building Gigafactory for cells."
    },
    # ── Telecom ─────────────────────────────────────────────────────────────────
    {
        "name": "Bharti Airtel", "ticker": "BHARTIARTL", "bse_code": "532454",
        "nse_code": "BHARTIARTL", "industry": "TELCO",
        "market_cap": 950000, "revenue_ttm": 151000, "ebitda_margin": 52.0,
        "net_margin": 10.5, "pe_ratio": 75.0, "eps_ttm": 25.0,
        "current_price": 1780, "is_nifty50": True, "is_sensex": True,
        "aliases": ["Airtel", "Bharti Airtel", "BHARTIARTL"],
        "description": "India's second largest telecom. 370 million subscribers."
    },
]

COMMODITIES = [
    {"name": "Iron Ore", "symbol": "IRONORE", "unit": "per tonne", "currency": "USD",
     "description": "Key input for steel production"},
    {"name": "Coking Coal", "symbol": "COKE", "unit": "per tonne", "currency": "USD",
     "description": "Metallurgical coal for steel making"},
    {"name": "Crude Oil (Brent)", "symbol": "BRENT", "unit": "per barrel", "currency": "USD",
     "description": "Global crude oil benchmark"},
    {"name": "Natural Gas", "symbol": "NATGAS", "unit": "per mmBtu", "currency": "USD",
     "description": "Key feedstock for fertilizers and power"},
    {"name": "Aluminium", "symbol": "ALUMINIUM", "unit": "per tonne", "currency": "USD",
     "description": "Non-ferrous metal"},
    {"name": "Copper", "symbol": "COPPER", "unit": "per tonne", "currency": "USD",
     "description": "Used in EVs, construction, electronics"},
    {"name": "Lithium", "symbol": "LITHIUM", "unit": "per tonne", "currency": "USD",
     "description": "Critical for EV batteries"},
    {"name": "Urea", "symbol": "UREA", "unit": "per tonne", "currency": "USD",
     "description": "Key fertilizer input"},
    {"name": "Limestone", "symbol": "LSTN", "unit": "per tonne", "currency": "INR",
     "description": "Key input for cement"},
    {"name": "Palm Oil", "symbol": "PALM", "unit": "per tonne", "currency": "USD",
     "description": "Edible oil – impacts FMCG food margins"},
    {"name": "Naphtha", "symbol": "NAPHTHA", "unit": "per tonne", "currency": "USD",
     "description": "Petrochemical feedstock"},
    {"name": "PTA (Purified Terephthalic Acid)", "symbol": "PTA", "unit": "per tonne", "currency": "USD",
     "description": "Polyester feedstock – impacts textile, packaging"},
]

# Supply-chain propagation graph
# Format: {"from_industry": "TO_INDUSTRY", "impact_coefficient": 0.0–1.0, "direction": "+/-", "type": "input/output"}
INDUSTRY_RELATIONSHIPS = [
    # Iron Ore → Steel
    {"upstream": "MINE", "downstream": "STEEL", "impact": 0.45, "direction": "-", "type": "input",
     "desc": "Iron ore is 40-45% of steel production cost"},
    # Coking Coal → Steel
    {"upstream": "MINE", "downstream": "ALUM", "impact": 0.35, "direction": "-", "type": "input",
     "desc": "Bauxite mining feeds aluminium smelters"},
    # Steel → Auto
    {"upstream": "STEEL", "downstream": "AUTO", "impact": 0.18, "direction": "-", "type": "input",
     "desc": "Steel is ~18% of auto production cost"},
    # Steel → Capital Goods
    {"upstream": "STEEL", "downstream": "CAPGD", "impact": 0.15, "direction": "-", "type": "input",
     "desc": "Steel input for heavy machinery"},
    # Steel → Infrastructure
    {"upstream": "STEEL", "downstream": "INFRA", "impact": 0.20, "direction": "-", "type": "input",
     "desc": "Steel for construction and rail"},
    # Steel → Real Estate
    {"upstream": "STEEL", "downstream": "REALT", "impact": 0.12, "direction": "-", "type": "input",
     "desc": "Structural steel for buildings"},
    # Crude Oil → OGR (direct)
    {"upstream": "OGE", "downstream": "OGR", "impact": 0.70, "direction": "+", "type": "input",
     "desc": "Crude is primary feedstock for refineries"},
    # Crude Oil → Chemicals
    {"upstream": "OGR", "downstream": "CHEM", "impact": 0.40, "direction": "-", "type": "input",
     "desc": "Petrochemical feedstock from refineries"},
    # Crude Oil → FMCG (indirect)
    {"upstream": "CHEM", "downstream": "FMCG", "impact": 0.08, "direction": "-", "type": "input",
     "desc": "Plastic packaging and surfactant costs"},
    # Crude Oil → Auto (fuel price → demand)
    {"upstream": "OGR", "downstream": "AUTO", "impact": 0.10, "direction": "+", "type": "demand",
     "desc": "High fuel prices drive EV demand shift"},
    # Lithium → EV Batteries → EV
    {"upstream": "MINE", "downstream": "EV", "impact": 0.35, "direction": "-", "type": "input",
     "desc": "Lithium is key battery cost driver for EVs"},
    # EV penetration → Auto incumbents
    {"upstream": "EV", "downstream": "AUTO", "impact": 0.15, "direction": "-", "type": "competition",
     "desc": "EV share gain disrupts ICE auto market share"},
    # Power costs → Steel (energy-intensive)
    {"upstream": "POWER", "downstream": "STEEL", "impact": 0.12, "direction": "-", "type": "input",
     "desc": "Power is 12% of steel production cost"},
    {"upstream": "POWER", "downstream": "ALUM", "impact": 0.30, "direction": "-", "type": "input",
     "desc": "Power is 30% of aluminium smelting cost"},
    {"upstream": "POWER", "downstream": "CEMENT", "impact": 0.15, "direction": "-", "type": "input",
     "desc": "Power is 15% of cement production cost"},
    # Cement → Infrastructure / Real Estate (output)
    {"upstream": "CEMENT", "downstream": "INFRA", "impact": 0.25, "direction": "+", "type": "output",
     "desc": "Cement demand driven by infrastructure spend"},
    {"upstream": "CEMENT", "downstream": "REALT", "impact": 0.20, "direction": "+", "type": "output",
     "desc": "Cement demand driven by housing"},
    # Fertilizer → Agriculture → Food Processing → FMCG
    {"upstream": "FERT", "downstream": "AGRI", "impact": 0.25, "direction": "-", "type": "input",
     "desc": "Fertilizer cost affects farm profitability"},
    {"upstream": "AGRI", "downstream": "FOOD", "impact": 0.40, "direction": "-", "type": "input",
     "desc": "Raw agri commodities feed food processors"},
    {"upstream": "FOOD", "downstream": "FMCG", "impact": 0.15, "direction": "-", "type": "input",
     "desc": "Processed food ingredients impact FMCG margins"},
    # Banking ↔ Real Estate
    {"upstream": "BANK", "downstream": "REALT", "impact": 0.20, "direction": "+", "type": "credit",
     "desc": "Rate cuts spur home loan growth and real estate"},
    # Telecom → IT
    {"upstream": "TELCO", "downstream": "IT", "impact": 0.05, "direction": "+", "type": "enabler",
     "desc": "5G rollout drives enterprise digitization IT demand"},
]

COMMODITY_INDUSTRY_IMPACTS = [
    {"commodity": "Iron Ore", "industry": "STEEL", "cost_pct": 42, "sensitivity": -4.5, "direction": "negative"},
    {"commodity": "Coking Coal", "industry": "STEEL", "cost_pct": 18, "sensitivity": -1.8, "direction": "negative"},
    {"commodity": "Crude Oil (Brent)", "industry": "OGR", "cost_pct": 72, "sensitivity": -0.5, "direction": "negative"},
    {"commodity": "Crude Oil (Brent)", "industry": "AUTO", "cost_pct": 3, "sensitivity": -0.3, "direction": "negative"},
    {"commodity": "Crude Oil (Brent)", "industry": "FMCG", "cost_pct": 5, "sensitivity": -0.5, "direction": "negative"},
    {"commodity": "Aluminium", "industry": "AUTO", "cost_pct": 8, "sensitivity": -0.8, "direction": "negative"},
    {"commodity": "Aluminium", "industry": "CAPGD", "cost_pct": 10, "sensitivity": -1.0, "direction": "negative"},
    {"commodity": "Copper", "industry": "EV", "cost_pct": 12, "sensitivity": -1.2, "direction": "negative"},
    {"commodity": "Copper", "industry": "CAPGD", "cost_pct": 8, "sensitivity": -0.8, "direction": "negative"},
    {"commodity": "Lithium", "industry": "EV", "cost_pct": 25, "sensitivity": -2.5, "direction": "negative"},
    {"commodity": "Natural Gas", "industry": "FERT", "cost_pct": 55, "sensitivity": -5.5, "direction": "negative"},
    {"commodity": "Natural Gas", "industry": "POWER", "cost_pct": 35, "sensitivity": -3.5, "direction": "negative"},
    {"commodity": "Limestone", "industry": "CEMENT", "cost_pct": 10, "sensitivity": -1.0, "direction": "negative"},
    {"commodity": "Palm Oil", "industry": "FMCG", "cost_pct": 8, "sensitivity": -0.8, "direction": "negative"},
    {"commodity": "Urea", "industry": "AGRI", "cost_pct": 18, "sensitivity": -1.8, "direction": "negative"},
]
