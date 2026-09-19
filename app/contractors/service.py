import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.database import mongo
from app.audit.service import log_audit_event


def calculate_contractor_risk(contractor_id: str) -> Dict[str, Any]:
    """
    Computes explainable contractor safety risk score (0-100)
    with explicit contributing reasons.
    """
    contractor = get_contractor_by_id(contractor_id)
    if not contractor:
        return {"risk_score": 0, "risk_level": "LOW", "factors": []}

    score = 10
    factors = []

    mine_id = str(contractor.get("mine_id"))
    comp_name = contractor.get("company_name", "")

    # 1. Associated violations count
    violations = list(mongo.violations.find({
        "mine_id": mine_id,
        "description": {"$regex": comp_name, "$options": "i"}
    }))
    v_count = len(violations)
    if v_count > 0:
        penalty = min(v_count * 10, 40)
        score += penalty
        factors.append(f"{v_count} safety/PPE violations associated with contractor workforce (+{penalty} pts)")

    # 2. Expired contractor documents
    doc_query = {"mine_id": mine_id, "document_type": "CONTRACTOR_PERMIT", "status": "EXPIRED"}
    expired_docs = list(mongo.documents.find(doc_query))
    if expired_docs:
        doc_penalty = min(len(expired_docs) * 20, 30)
        score += doc_penalty
        factors.append(f"{len(expired_docs)} mandatory statutory permits/clearances expired (+{doc_penalty} pts)")

    # 3. High worker headcount safety exposure
    workers = contractor.get("workers_count", 0)
    if workers > 100:
        score += 10
        factors.append(f"Large operational deployment ({workers} personnel) elevated risk exposure (+10 pts)")
    elif workers > 50:
        score += 5
        factors.append(f"Medium deployment ({workers} personnel) (+5 pts)")

    # 4. Cap score at 100
    score = min(score, 100)

    if score >= 80:
        level = "CRITICAL"
    elif score >= 60:
        level = "HIGH"
    elif score >= 35:
        level = "MEDIUM"
    else:
        level = "LOW"

    if not factors:
        factors.append("Clean compliance track record with valid DGMS safety clearance.")

    return {
        "risk_score": score,
        "risk_level": level,
        "contributing_factors": factors
    }


def create_contractor(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    doc = {
        "company_name": data["company_name"].strip(),
        "registration_number": data.get("registration_number", f"REG-{now.strftime('%y%m%d%H%M')}").strip(),
        "mine_id": str(data["mine_id"]),
        "contact_person": data.get("contact_person", "Site Supervisor"),
        "contact_email": data.get("contact_email", "").strip(),
        "contact_phone": data.get("contact_phone", "").strip(),
        "workers_count": int(data.get("workers_count", 25)),
        "contract_start": data.get("contract_start", now.isoformat()),
        "contract_end": data.get("contract_end", (now + datetime.timedelta(days=365)).isoformat()),
        "compliance_status": data.get("compliance_status", "COMPLIANT"),  # COMPLIANT, PROBATION, HIGH_RISK, SUSPENDED
        "documents": data.get("documents", []),
        "risk_score": 15,
        "risk_level": "LOW",
        "risk_factors": ["Initial safety registration"],
        "created_at": now,
        "updated_at": now
    }
    res = mongo.contractors.insert_one(doc)
    doc["_id"] = res.inserted_id

    log_audit_event(
        action="CREATE",
        entity="CONTRACTOR",
        entity_id=str(res.inserted_id),
        user=user,
        new_value={"company_name": doc["company_name"], "mine_id": doc["mine_id"]}
    )
    return doc


def update_contractor(contractor_id: str, data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(contractor_id)} if ObjectId.is_valid(contractor_id) else {"_id": contractor_id}
    data["updated_at"] = datetime.datetime.utcnow()
    
    mongo.contractors.update_one(query, {"$set": data})
    
    # Recalculate explainable risk
    risk_info = calculate_contractor_risk(contractor_id)
    mongo.contractors.update_one(query, {"$set": {
        "risk_score": risk_info["risk_score"],
        "risk_level": risk_info["risk_level"],
        "risk_factors": risk_info["contributing_factors"]
    }})

    doc = mongo.contractors.find_one(query)
    if doc:
        log_audit_event(action="UPDATE", entity="CONTRACTOR", entity_id=contractor_id, user=user)
    return doc


def list_contractors(mine_id: Optional[str] = None, compliance_status: Optional[str] = None) -> List[Dict[str, Any]]:
    query = {}
    if mine_id:
        query["mine_id"] = str(mine_id)
    if compliance_status:
        query["compliance_status"] = compliance_status.upper()
    return list(mongo.contractors.find(query))


def get_contractor_by_id(contractor_id: str) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(contractor_id)} if ObjectId.is_valid(contractor_id) else {"_id": contractor_id}
    return mongo.contractors.find_one(query)
