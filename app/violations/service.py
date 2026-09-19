import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.database import mongo
from app.audit.service import log_audit_event
from app.notifications.service import create_notification

VIOLATION_DETECTED = "DETECTED"
VIOLATION_CREATED = "CREATED"
VIOLATION_ASSIGNED = "ASSIGNED"
VIOLATION_ACKNOWLEDGED = "ACKNOWLEDGED"
VIOLATION_CORRECTIVE_ACTION = "CORRECTIVE_ACTION"
VIOLATION_VERIFICATION = "VERIFICATION"
VIOLATION_CLOSED = "CLOSED"

VIOLATION_STATUSES = [
    VIOLATION_DETECTED,
    VIOLATION_CREATED,
    VIOLATION_ASSIGNED,
    VIOLATION_ACKNOWLEDGED,
    VIOLATION_CORRECTIVE_ACTION,
    VIOLATION_VERIFICATION,
    VIOLATION_CLOSED
]

VIOLATION_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def create_violation(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    severity = data.get("severity", "MEDIUM").upper()
    if severity not in VIOLATION_SEVERITIES:
        severity = "MEDIUM"

    # Default deadline based on severity: Critical=12h, High=24h, Medium=48h, Low=72h
    default_hours = {"CRITICAL": 12, "HIGH": 24, "MEDIUM": 48, "LOW": 72}.get(severity, 48)
    deadline = data.get("deadline")
    if isinstance(deadline, str):
        try:
            deadline = datetime.datetime.fromisoformat(deadline.replace("Z", ""))
        except Exception:
            deadline = now + datetime.timedelta(hours=default_hours)
    elif not deadline:
        deadline = now + datetime.timedelta(hours=default_hours)

    assigned_to = data.get("assigned_to")
    # If not provided, find a Safety Officer for this mine
    if not assigned_to:
        safety_officer = mongo.users.find_one({"mine_id": str(data["mine_id"]), "role": "SAFETY_OFFICER"})
        if safety_officer:
            assigned_to = str(safety_officer["_id"])
        else:
            # Fallback to any active safety officer
            any_so = mongo.users.find_one({"role": "SAFETY_OFFICER"})
            assigned_to = str(any_so["_id"]) if any_so else None

    doc = {
        "mine_id": str(data["mine_id"]),
        "zone": data.get("zone", "Pit Operational Zone"),
        "zone_id": str(data.get("zone_id", "")),
        "category": data.get("category", "PPE_VIOLATION"),
        "description": data["description"].strip(),
        "severity": severity,
        "source": data.get("source", "MANUAL"),  # AI_DETECTION, INSPECTION, FIELD_REPORT, MANUAL
        "evidence": data.get("evidence", []),  # Array of photo/video URLs or frame info
        "latitude": float(data.get("latitude", 23.7957)),
        "longitude": float(data.get("longitude", 86.4304)),
        "detected_by": str(user.get("_id", user.get("id"))) if user else "AI_DETECTION_ENGINE",
        "assigned_to": str(assigned_to) if assigned_to else None,
        "deadline": deadline,
        "status": VIOLATION_ASSIGNED if assigned_to else VIOLATION_CREATED,
        "created_at": now,
        "updated_at": now
    }
    res = mongo.violations.insert_one(doc)
    doc["_id"] = res.inserted_id
    violation_id = str(res.inserted_id)

    log_audit_event(
        action="CREATE",
        entity="VIOLATION",
        entity_id=violation_id,
        user=user,
        new_value={"severity": severity, "category": doc["category"], "mine_id": doc["mine_id"]}
    )

    # Automatically generate associated Corrective Action (CAPA) record
    capa_doc = {
        "violation_id": violation_id,
        "mine_id": doc["mine_id"],
        "assigned_to": assigned_to,
        "description": f"Remediate {doc['category']}: {doc['description']}",
        "deadline": deadline,
        "evidence": [],
        "completion_date": None,
        "verification_status": "PENDING",  # PENDING, SUBMITTED, VERIFIED, REJECTED
        "verified_by": None,
        "verified_at": None,
        "escalation_tier": 0,
        "created_at": now,
        "updated_at": now
    }
    capa_res = mongo.corrective_actions.insert_one(capa_doc)
    doc["corrective_action_id"] = str(capa_res.inserted_id)

    # Trigger In-App Notification
    create_notification(
        user_id=assigned_to,
        role="SAFETY_OFFICER",
        title=f"New {severity} Violation Detected: {doc['category']}",
        message=f"{doc['description']} at mine #{doc['mine_id']}. Action required before deadline.",
        event_type="new_violation",
        entity_type="VIOLATION",
        entity_id=violation_id,
        severity=severity
    )

    return doc


def assign_violation(violation_id: str, officer_id: str, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(violation_id)} if ObjectId.is_valid(violation_id) else {"_id": violation_id}
    now = datetime.datetime.utcnow()
    mongo.violations.update_one(query, {"$set": {"assigned_to": str(officer_id), "status": VIOLATION_ASSIGNED, "updated_at": now}})
    mongo.corrective_actions.update_one({"violation_id": violation_id}, {"$set": {"assigned_to": str(officer_id), "updated_at": now}})
    
    doc = mongo.violations.find_one(query)
    if doc:
        log_audit_event(action="ASSIGN", entity="VIOLATION", entity_id=violation_id, user=user, new_value={"assigned_to": officer_id})
        create_notification(
            user_id=officer_id,
            role="SAFETY_OFFICER",
            title="Violation Assigned to You",
            message=f"Violation #{violation_id[:8]} assigned to you for corrective remediation.",
            event_type="violation_assigned",
            entity_type="VIOLATION",
            entity_id=violation_id,
            severity=doc.get("severity", "MEDIUM")
        )
    return doc


def acknowledge_violation(violation_id: str, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(violation_id)} if ObjectId.is_valid(violation_id) else {"_id": violation_id}
    now = datetime.datetime.utcnow()
    mongo.violations.update_one(query, {"$set": {"status": VIOLATION_ACKNOWLEDGED, "acknowledged_at": now, "updated_at": now}})
    doc = mongo.violations.find_one(query)
    if doc:
        log_audit_event(action="ACKNOWLEDGE", entity="VIOLATION", entity_id=violation_id, user=user)
    return doc


def close_violation(violation_id: str, closure_notes: str, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Strict verified closure: requires verified CAPA proof and authorized role."""
    query = {"_id": ObjectId(violation_id)} if ObjectId.is_valid(violation_id) else {"_id": violation_id}
    now = datetime.datetime.utcnow()
    
    # Check CAPA status
    capa = mongo.corrective_actions.find_one({"violation_id": violation_id})
    if capa and capa.get("verification_status") != "VERIFIED":
        return None  # Cannot close until CAPA is verified

    mongo.violations.update_one(
        query,
        {"$set": {"status": VIOLATION_CLOSED, "closure_notes": closure_notes, "closed_by": str(user.get("_id", user.get("id"))), "closed_at": now, "updated_at": now}}
    )
    doc = mongo.violations.find_one(query)
    if doc:
        log_audit_event(action="CLOSE", entity="VIOLATION", entity_id=violation_id, user=user, notes=closure_notes)
    return doc


def list_violations(mine_id: Optional[str] = None, severity: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    query = {}
    if mine_id:
        query["mine_id"] = str(mine_id)
    if severity:
        query["severity"] = severity.upper()
    if status:
        query["status"] = status.upper()
    return list(mongo.violations.find(query).sort("created_at", -1))


def get_violation_by_id(violation_id: str) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(violation_id)} if ObjectId.is_valid(violation_id) else {"_id": violation_id}
    return mongo.violations.find_one(query)
