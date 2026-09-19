import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.database import mongo
from app.audit.service import log_audit_event

STATUS_COMPLIANT = "COMPLIANT"
STATUS_PENDING = "PENDING"
STATUS_DUE_SOON = "DUE_SOON"
STATUS_OVERDUE = "OVERDUE"
STATUS_NON_COMPLIANT = "NON_COMPLIANT"
STATUS_UNDER_REVIEW = "UNDER_REVIEW"

COMPLIANCE_STATUSES = [
    STATUS_COMPLIANT,
    STATUS_PENDING,
    STATUS_DUE_SOON,
    STATUS_OVERDUE,
    STATUS_NON_COMPLIANT,
    STATUS_UNDER_REVIEW
]

COMPLIANCE_CATEGORIES = [
    "Safety",
    "Environment",
    "Labour",
    "Production",
    "Equipment",
    "Contractor",
    "Documentation"
]


def create_compliance_requirement(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    due_date = data.get("due_date")
    if isinstance(due_date, str):
        try:
            due_date = datetime.datetime.fromisoformat(due_date.replace("Z", ""))
        except Exception:
            due_date = now + datetime.timedelta(days=30)
    elif not due_date:
        due_date = now + datetime.timedelta(days=30)

    doc = {
        "title": data["title"].strip(),
        "description": data.get("description", "").strip(),
        "category": data.get("category", "Safety"),
        "applicable_mine": str(data["applicable_mine"]),
        "responsible_role": data.get("responsible_role", "SAFETY_OFFICER"),
        "frequency": data.get("frequency", "MONTHLY"),  # DAILY, WEEKLY, MONTHLY, QUARTERLY, ANNUALLY
        "due_date": due_date,
        "status": data.get("status", STATUS_PENDING),
        "evidence": data.get("evidence", []),  # Array of file objects/urls
        "remarks": data.get("remarks", ""),
        "statutory_reference": data.get("statutory_reference", "Coal Mines Regulations 2017"),
        "created_at": now,
        "updated_at": now
    }
    res = mongo.compliance_requirements.insert_one(doc)
    doc["_id"] = res.inserted_id

    log_audit_event(
        action="CREATE",
        entity="COMPLIANCE_REQUIREMENT",
        entity_id=str(res.inserted_id),
        user=user,
        new_value={"title": doc["title"], "mine_id": doc["applicable_mine"]}
    )
    return doc


def list_compliance_requirements(mine_id: Optional[str] = None, category: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    query = {}
    if mine_id:
        query["applicable_mine"] = str(mine_id)
    if category:
        query["category"] = category
    if status:
        query["status"] = status.upper()

    now = datetime.datetime.utcnow()
    docs = list(mongo.compliance_requirements.find(query))

    # Dynamic status update based on due_date if not COMPLIANT
    for d in docs:
        if d.get("status") not in (STATUS_COMPLIANT, STATUS_NON_COMPLIANT):
            due = d.get("due_date")
            if isinstance(due, datetime.datetime):
                if due < now:
                    d["status"] = STATUS_OVERDUE
                elif due <= now + datetime.timedelta(days=7):
                    d["status"] = STATUS_DUE_SOON
    return docs


def update_compliance_status(req_id: str, status: str, evidence: Optional[List[str]] = None, remarks: Optional[str] = None, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(req_id)} if ObjectId.is_valid(req_id) else {"_id": req_id}
    old_doc = mongo.compliance_requirements.find_one(query)
    if not old_doc:
        return None

    update_fields = {
        "status": status.upper(),
        "updated_at": datetime.datetime.utcnow()
    }
    if evidence is not None:
        update_fields["evidence"] = evidence
    if remarks is not None:
        update_fields["remarks"] = remarks

    mongo.compliance_requirements.update_one(query, {"$set": update_fields})
    new_doc = mongo.compliance_requirements.find_one(query)

    log_audit_event(
        action="UPDATE",
        entity="COMPLIANCE_REQUIREMENT",
        entity_id=str(req_id),
        user=user,
        old_value={"status": old_doc.get("status")},
        new_value={"status": status}
    )
    return new_doc


def get_compliance_dashboard_metrics(mine_id: Optional[str] = None) -> Dict[str, Any]:
    """Calculate aggregated stats for compliance dashboard."""
    query = {}
    if mine_id:
        query["applicable_mine"] = str(mine_id)

    items = list_compliance_requirements(mine_id)
    total = len(items)
    compliant = sum(1 for x in items if x.get("status") == STATUS_COMPLIANT)
    pending = sum(1 for x in items if x.get("status") == STATUS_PENDING)
    due_soon = sum(1 for x in items if x.get("status") == STATUS_DUE_SOON)
    overdue = sum(1 for x in items if x.get("status") == STATUS_OVERDUE)
    non_compliant = sum(1 for x in items if x.get("status") == STATUS_NON_COMPLIANT)
    under_review = sum(1 for x in items if x.get("status") == STATUS_UNDER_REVIEW)

    percentage = round((compliant / total * 100), 1) if total > 0 else 100.0

    return {
        "total_requirements": total,
        "compliant": compliant,
        "pending": pending,
        "due_soon": due_soon,
        "overdue": overdue,
        "non_compliant": non_compliant,
        "under_review": under_review,
        "compliance_percentage": percentage
    }
