import datetime
from typing import Dict, Any, List, Optional
from app.database import mongo


def calculate_mine_risk_score(mine_id: str) -> Dict[str, Any]:
    """
    Computes an explainable, transparent composite risk score (0-100)
    for a mine based on statutory safety factors and recent events.
    """
    score = 15  # Baseline operational baseline
    contributing_reasons = []

    now = datetime.datetime.utcnow()
    thirty_days_ago = now - datetime.timedelta(days=30)

    # 1. Violation count & severity
    violations = list(mongo.violations.find({"mine_id": str(mine_id)}))
    recent_violations = [v for v in violations if v.get("created_at", now) >= thirty_days_ago]
    
    crit_v = sum(1 for v in recent_violations if v.get("severity") == "CRITICAL")
    high_v = sum(1 for v in recent_violations if v.get("severity") == "HIGH")
    med_v = sum(1 for v in recent_violations if v.get("severity") == "MEDIUM")

    if crit_v > 0:
        pts = crit_v * 15
        score += pts
        contributing_reasons.append(f"{crit_v} Critical safety violations in last 30 days (+{pts} pts)")
    if high_v > 0:
        pts = min(high_v * 8, 32)
        score += pts
        contributing_reasons.append(f"{high_v} High-severity violations in last 30 days (+{pts} pts)")
    if med_v > 0:
        pts = min(med_v * 3, 15)
        score += pts
        contributing_reasons.append(f"{med_v} Medium-severity violations (+{pts} pts)")

    # 2. Repeated category violations (e.g. PPE)
    ppe_violations = sum(1 for v in recent_violations if "PPE" in v.get("category", "").upper())
    if ppe_violations >= 3:
        score += 15
        contributing_reasons.append(f"{ppe_violations} Repeated PPE violations indicates systemic non-compliance (+15 pts)")

    # 3. Overdue Corrective Actions (CAPA)
    capas = list(mongo.corrective_actions.find({"mine_id": str(mine_id)}))
    overdue_capas = []
    for c in capas:
        if c.get("verification_status") != "VERIFIED":
            dl = c.get("deadline")
            if dl and isinstance(dl, datetime.datetime) and dl < now:
                overdue_capas.append(c)

    if overdue_capas:
        pts = min(len(overdue_capas) * 10, 30)
        score += pts
        contributing_reasons.append(f"{len(overdue_capas)} Overdue corrective actions pending resolution (+{pts} pts)")

    # 4. Incident history (Accidents, Slope failure, Gas)
    incidents = list(mongo.incidents.find({"mine_id": str(mine_id)}))
    recent_incidents = [i for i in incidents if i.get("reported_at", now) >= thirty_days_ago]
    if recent_incidents:
        pts = min(len(recent_incidents) * 15, 30)
        score += pts
        contributing_reasons.append(f"{len(recent_incidents)} Hazardous incidents reported in last 30 days (+{pts} pts)")

    # 5. Expired statutory documents
    expired_docs = list(mongo.documents.find({"mine_id": str(mine_id), "status": "EXPIRED"}))
    if expired_docs:
        pts = min(len(expired_docs) * 8, 24)
        score += pts
        contributing_reasons.append(f"{len(expired_docs)} Expired statutory clearances/certificates (+{pts} pts)")

    # Cap score at 100
    score = min(max(score, 0), 100)

    # Determine risk level
    if score >= 75:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    if not contributing_reasons:
        contributing_reasons.append("Zero active violations or overdue corrective actions. Normal operational risk.")

    result = {
        "mine_id": str(mine_id),
        "risk_score": score,
        "risk_level": level,
        "calculated_at": now.isoformat(),
        "contributing_factors": contributing_reasons
    }

    # Persist in risk_scores collection
    mongo.risk_scores.update_one(
        {"mine_id": str(mine_id)},
        {"$set": result},
        upsert=True
    )

    return result
