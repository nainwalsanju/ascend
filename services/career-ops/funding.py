"""
Startup Funding & Runway Radar.
Adapted from upstream santifer/career-ops (company-funded.mjs & funding.json).
Provides venture funding intelligence, rounds, lead investors, and valuation data for high-growth tech companies.
"""

STARTUP_FUNDING_RADAR: dict[str, dict] = {
    "openai": {
        "round": "Growth / Non-Profit / For-Profit Restructuring",
        "raised": "$13 Billion+",
        "valuation": "$157 Billion",
        "lead_investors": "Microsoft, Thrive Capital, SoftBank, Khosla Ventures",
        "runway_health": "Tier-1 Sovereign Scale"
    },
    "anthropic": {
        "round": "Series D / Strategic",
        "raised": "$7.6 Billion+",
        "valuation": "$40 Billion+",
        "lead_investors": "Amazon, Google, Menlo Ventures, Spark Capital",
        "runway_health": "Extreme High Runway (Backed by AWS & GCP)"
    },
    "stripe": {
        "round": "Pre-IPO / Tender",
        "raised": "$8.7 Billion+",
        "valuation": "$65 Billion",
        "lead_investors": "Sequoia Capital, Founders Fund, General Catalyst",
        "runway_health": "Cash Flow Positive / Pre-IPO"
    },
    "databricks": {
        "round": "Series I",
        "raised": "$4.1 Billion+",
        "valuation": "$43 Billion",
        "lead_investors": "T. Rowe Price, Andreessen Horowitz, Fidelity",
        "runway_health": "Massive Enterprise Scale / Pre-IPO"
    },
    "ramp": {
        "round": "Series D-2",
        "raised": "$1.2 Billion+",
        "valuation": "$7.65 Billion",
        "lead_investors": "Founders Fund, Thrive Capital, D1 Capital Partners",
        "runway_health": "Rapid Growth / Strong Balance Sheet"
    },
    "scale ai": {
        "round": "Series F",
        "raised": "$1.6 Billion+",
        "valuation": "$13.8 Billion",
        "lead_investors": "Accel, Founders Fund, Nvidia, Amazon",
        "runway_health": "Extremely Strong (Key US Government / GenAI Contracts)"
    },
    "scaleai": {
        "round": "Series F",
        "raised": "$1.6 Billion+",
        "valuation": "$13.8 Billion",
        "lead_investors": "Accel, Founders Fund, Nvidia, Amazon",
        "runway_health": "Extremely Strong"
    },
    "figma": {
        "round": "Pre-IPO / Secondary",
        "raised": "$3.3 Billion+",
        "valuation": "$12.5 Billion",
        "lead_investors": "Sequoia Capital, Kleiner Perkins, Index Ventures",
        "runway_health": "High Profitability / Strong Runway"
    },
    "vercel": {
        "round": "Series E",
        "raised": "$563 Million+",
        "valuation": "$3.25 Billion",
        "lead_investors": "Accel, CRV, GV, Bedrock",
        "runway_health": "Strong Enterprise Expansion"
    },
    "linear": {
        "round": "Series B",
        "raised": "$52 Million+",
        "valuation": "$400 Million+",
        "lead_investors": "Accel, Sequoia Capital",
        "runway_health": "High Efficiency / Low Burn"
    },
    "replit": {
        "round": "Series B Extension",
        "raised": "$220 Million+",
        "valuation": "$1.16 Billion",
        "lead_investors": "Andreessen Horowitz, Coatue",
        "runway_health": "Strong Growth in AI Coding Agents"
    }
}

def get_company_funding_info(company: str) -> dict | None:
    """Returns verified venture capital funding info for target tech companies."""
    if not company:
        return None
    key = company.lower().strip()
    for name, data in STARTUP_FUNDING_RADAR.items():
        if name in key or key in name:
            return data
    return None
