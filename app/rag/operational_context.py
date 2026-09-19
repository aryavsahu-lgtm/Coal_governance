import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from app.database.mongo import mongo

logger = logging.getLogger("coal_governance.rag.operational")

# Operational keyword stems and intent triggers
OPERATIONAL_ENTITIES = [
    "mine", "mines", "violation", "violations", "contractor", "contractors",
    "capa", "corrective", "action", "actions", "incident", "incidents",
    "accident", "accidents", "inspection", "inspections", "compliance rate",
    "risk score", "risk scores", "penalty", "offender", "worker", "hazard"
]

OPERATIONAL_INTENT_WORDS = [
    "which", "who", "more", "most", "highest", "lowest", "max", "min",
    "worst", "best", "rank", "ranking", "compare", "comparison", "how many",
    "total", "count", "number of", "list", "status", "overview", "summary",
    "breakdown", "top", "active", "pending", "open", "diff", "difference"
]

KNOWN_MINES_KEYWORDS = [
    "rajmahal", "kusunda", "sonepur", "bazari", "moonidih",
    "ecl", "bccl", "opencast", "underground", "colliery"
]


def is_operational_query(query: str) -> bool:
    """
    Determines whether a user query asks about live operational database entities
    (e.g., mine rankings, violation counts, contractor risks, CAPA status).
    """
    q = query.lower()

    # Explicit operational superlatives / count questions
    has_superlative_or_count = any(k in q for k in [
        "which mine", "which mines", "more violation", "most violation", "highest violation",
        "how many violation", "how many open", "how many capa", "compare", "ranking", "rank",
        "highest risk", "lowest risk", "worst", "top mine", "more open", "total violation"
    ])

    if has_superlative_or_count:
        return True

    # Check if this is an explicit regulatory statute lookup without operational metrics
    is_explicit_law_lookup = bool(re.search(
        r"\b(section\s+\d+|sec\.?\s*\d+|regulation\s+\d+|reg\.?\s*\d+|mines\s+act\s+\d{4}|cmr\s+\d{4})\b",
        q
    ))
    if is_explicit_law_lookup:
        return False

    # Check for mine-specific mentions with operational words
    has_known_mine = any(m in q for m in KNOWN_MINES_KEYWORDS)
    has_op_entity = any(e in q for e in ["violation", "violations", "contractor", "contractors", "capa", "incident", "accident", "inspection"])
    has_op_intent = any(i in q for i in ["how many", "count", "status", "pending", "risk", "who", "which", "more", "most", "total", "list", "overview"])

    if has_known_mine and (has_op_entity or has_op_intent):
        return True

    if has_op_entity and has_op_intent:
        return True

    return False


def get_mines_violation_analytics(query: Optional[str] = None) -> Dict[str, Any]:
    """
    Aggregates live violations across all registered mines in MongoDB.
    Calculates total violations, severity distribution, category breakdown, and rankings.
    """
    try:
        mines = list(mongo.mines.find())
    except Exception as e:
        logger.error(f"Error fetching mines: {e}")
        mines = []

    try:
        violations = list(mongo.violations.find())
    except Exception as e:
        logger.error(f"Error fetching violations: {e}")
        violations = []

    # Map mine_id to mine record
    mine_map = {}
    for m in mines:
        mid = str(m.get("_id", ""))
        mine_map[mid] = {
            "mine_id": mid,
            "mine_name": m.get("mine_name", "Unknown Mine"),
            "mine_code": m.get("mine_code", "N/A"),
            "mine_type": m.get("mine_type", "OPENCAST"),
            "location": m.get("location", "N/A"),
            "total_violations": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "open_count": 0,
            "categories": {},
            "violations_list": []
        }

    # Aggregate violations
    for v in violations:
        v_mine_id = str(v.get("mine_id", ""))
        severity = str(v.get("severity", "MEDIUM")).upper()
        status = str(v.get("status", "DETECTED")).upper()
        category = str(v.get("category", "GENERAL")).upper()

        if v_mine_id not in mine_map:
            # Fallback placeholder for unmatched mine IDs
            mine_map[v_mine_id] = {
                "mine_id": v_mine_id,
                "mine_name": f"Mine ({v_mine_id[:8]})",
                "mine_code": "UNRESOLVED",
                "mine_type": "UNKNOWN",
                "location": "N/A",
                "total_violations": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "open_count": 0,
                "categories": {},
                "violations_list": []
            }

        stats = mine_map[v_mine_id]
        stats["total_violations"] += 1

        if severity == "CRITICAL":
            stats["critical"] += 1
        elif severity == "HIGH":
            stats["high"] += 1
        elif severity == "MEDIUM":
            stats["medium"] += 1
        elif severity == "LOW":
            stats["low"] += 1

        if status != "CLOSED":
            stats["open_count"] += 1

        stats["categories"][category] = stats["categories"].get(category, 0) + 1
        stats["violations_list"].append({
            "description": v.get("description", ""),
            "severity": severity,
            "category": category,
            "status": status,
            "zone": v.get("zone", "General")
        })

    rankings = sorted(mine_map.values(), key=lambda x: (x["total_violations"], x["critical"], x["high"]), reverse=True)
    top_mine = rankings[0] if rankings else None

    # Check if a specific mine is targeted in query
    targeted_mine = None
    if query:
        ql = query.lower()
        for r in rankings:
            cname = r["mine_name"].lower()
            if any(part in ql for part in cname.split() if len(part) > 3) or r["mine_code"].lower() in ql:
                targeted_mine = r
                break

    return {
        "total_mines": len(mines),
        "total_violations": len(violations),
        "rankings": rankings,
        "top_mine": top_mine,
        "targeted_mine": targeted_mine
    }


def get_contractors_analytics() -> Dict[str, Any]:
    """Fetches contractors and safety risk scores."""
    try:
        contractors = list(mongo.contractors.find())
    except Exception as e:
        logger.error(f"Error fetching contractors: {e}")
        contractors = []

    contractor_list = []
    for c in contractors:
        contractor_list.append({
            "company_name": c.get("company_name", "Unknown Contractor"),
            "registration_number": c.get("registration_number", "N/A"),
            "risk_score": c.get("risk_score", 0),
            "risk_level": c.get("risk_level", "LOW"),
            "compliance_status": c.get("compliance_status", "COMPLIANT"),
            "workers_count": c.get("workers_count", 0),
            "risk_factors": c.get("risk_factors", [])
        })

    contractor_list.sort(key=lambda x: x["risk_score"], reverse=True)
    highest_risk = contractor_list[0] if contractor_list else None

    return {
        "total_contractors": len(contractor_list),
        "highest_risk": highest_risk,
        "contractors": contractor_list
    }


def get_capa_analytics() -> Dict[str, Any]:
    """Fetches corrective actions status."""
    try:
        capas = list(mongo.corrective_actions.find())
    except Exception as e:
        logger.error(f"Error fetching CAPAs: {e}")
        capas = []

    pending = sum(1 for c in capas if c.get("verification_status") == "PENDING")
    verified = sum(1 for c in capas if c.get("verification_status") == "VERIFIED")
    escalated = sum(1 for c in capas if (c.get("escalation_tier") or 0) > 0)

    return {
        "total_capas": len(capas),
        "pending_verification": pending,
        "verified": verified,
        "escalated": escalated
    }


def generate_operational_synthesis(query: str) -> Dict[str, Any]:
    """
    Synthesizes a data-grounded operational response based on live MongoDB collections.
    Returns response text and operational citation metadata.
    """
    ql = query.lower()
    citations = [{
        "doc_id": "OPERATIONAL-DB-MINES-VIOLATIONS",
        "regulation": "Live Operational Database (Mines & Violations Registry)",
        "title": "CoalGov-AI Central Governance Database",
        "authority": "DGMS Coal Governance Live Operational Store",
        "category": "Live Field Operational Metrics"
    }]

    # 1. Contractor risk inquiry
    if "contractor" in ql and ("risk" in ql or "who" in ql or "highest" in ql or "worst" in ql):
        c_data = get_contractors_analytics()
        highest = c_data["highest_risk"]
        if not highest:
            return {
                "response": "No registered contractors currently logged in the operational database.",
                "citations": citations
            }

        response = (
            f"### 👷 Contractor Safety & Risk Analytics\n\n"
            f"**Direct Answer:**\n"
            f"**{highest['company_name']}** currently has the **highest risk score** ({highest['risk_score']}/100 - {highest['risk_level']}) "
            f"with {highest['workers_count']} deployed workers and status **{highest['compliance_status']}**.\n\n"
            f"**Risk Factors Noted:** {', '.join(highest['risk_factors']) or 'No major infractions.'}\n\n"
            f"**All Registered Contractors Ranking:**\n"
            f"| Contractor Name | Reg No | Workers | Risk Score | Risk Level | Status |\n"
            f"| :--- | :--- | :---: | :---: | :---: | :--- |\n"
        )
        for c in c_data["contractors"]:
            response += f"| {c['company_name']} | {c['registration_number']} | {c['workers_count']} | **{c['risk_score']}** | {c['risk_level']} | {c['compliance_status']} |\n"

        return {
            "response": response,
            "citations": citations
        }

    # 2. CAPA / Corrective Actions inquiry
    if ("capa" in ql or "corrective action" in ql) and ("how many" in ql or "status" in ql or "pending" in ql):
        capa_data = get_capa_analytics()
        response = (
            f"### 🛠️ Corrective Action (CAPA) Operational Overview\n\n"
            f"- **Total CAPAs Tracked:** {capa_data['total_capas']}\n"
            f"- **Pending Verification:** {capa_data['pending_verification']}\n"
            f"- **Verified & Rectified:** {capa_data['verified']}\n"
            f"- **Escalated Actions (Tier 1+):** {capa_data['escalated']}\n\n"
            f"Statutory mandate requires that all high and critical severity CAPAs undergo biometric or supervisor photographic verification within 24–48 hours."
        )
        return {
            "response": response,
            "citations": citations
        }

    # 3. Mine Violations Inquiry (Default and primary operational flow)
    m_data = get_mines_violation_analytics(query)
    rankings = m_data["rankings"]
    top_mine = m_data["top_mine"]
    targeted_mine = m_data["targeted_mine"]

    if not rankings or m_data["total_mines"] == 0:
        return {
            "response": "No registered mines or violation records found in the current operational database.",
            "citations": citations
        }

    # If asking about a specific mine
    if targeted_mine and not ("which" in ql or "more" in ql or "most" in ql or "compare" in ql or "rank" in ql):
        c_cats = ", ".join([f"{k} ({v})" for k, v in targeted_mine["categories"].items()]) or "None"
        response = (
            f"### 📍 Operational Safety Status: **{targeted_mine['mine_name']}** ({targeted_mine['mine_code']})\n\n"
            f"- **Total Recorded Violations:** **{targeted_mine['total_violations']}**\n"
            f"- **Active/Open Violations:** {targeted_mine['open_count']}\n"
            f"- **Severity Breakdown:** Critical: **{targeted_mine['critical']}**, High: **{targeted_mine['high']}**, Medium: **{targeted_mine['medium']}**, Low: **{targeted_mine['low']}**\n"
            f"- **Categories:** {c_cats}\n"
            f"- **Location:** {targeted_mine['location']} | Type: {targeted_mine['mine_type']}\n"
        )
        return {
            "response": response,
            "citations": citations
        }

    # Comparative / "which mine has more violation" response
    top_name = top_mine["mine_name"]
    top_count = top_mine["total_violations"]

    response = (
        f"### 📊 Live Operational Safety Analytics: Mine Violations\n\n"
        f"**Direct Answer:**\n"
        f"Based on live records in the central Coal Governance database, **{top_name}** currently has the **most violations**, "
        f"with a total of **{top_count} recorded violation{'s' if top_count != 1 else ''}** "
        f"({top_mine['critical']} Critical, {top_mine['high']} High, {top_mine['medium']} Medium).\n\n"
        f"#### 📋 Mine-by-Mine Violation Rankings\n"
        f"| Rank | Mine Name | Code | Total Violations | Critical | High | Medium | Open / Pending |\n"
        f"| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |\n"
    )

    for i, m in enumerate(rankings, 1):
        clean_name = m["mine_name"].replace(" (DEMO DATA)", "")
        badge = " ⚠️ *(Highest)*" if i == 1 and m["total_violations"] > 0 else ""
        response += (
            f"| #{i} | **{clean_name}**{badge} | `{m['mine_code']}` | **{m['total_violations']}** | "
            f"{m['critical']} | {m['high']} | {m['medium']} | {m['open_count']} |\n"
        )

    # Top offending categories across the top mine
    if top_mine and top_mine["categories"]:
        top_cats = sorted(top_mine["categories"].items(), key=lambda x: x[1], reverse=True)
        cat_str = ", ".join([f"**{c[0].replace('_', ' ').title()}** ({c[1]})" for c in top_cats])
        response += f"\n**Primary Violation Categories in {top_name}:**\n{cat_str}\n"

    response += (
        f"\n> **Safety Action Notice:**\n"
        f"> The Statutory Mining Inspector and Mine Safety Officer should prioritize physical audits and CAPA enforcement "
        f"at **{top_name}** to remediate open critical/high infractions pursuant to DGMS standards."
    )

    return {
        "response": response,
        "citations": citations
    }
