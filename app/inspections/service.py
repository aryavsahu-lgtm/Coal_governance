import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.database import mongo
from app.audit.service import log_audit_event
from app.notifications.service import create_notification

INSP_SCHEDULED = "SCHEDULED"
INSP_ASSIGNED = "ASSIGNED"
INSP_IN_PROGRESS = "IN_PROGRESS"
INSP_SUBMITTED = "SUBMITTED"
INSP_REVIEWED = "REVIEWED"
INSP_CLOSED = "CLOSED"

INSPECTION_STATUSES = [
    INSP_SCHEDULED,
    INSP_ASSIGNED,
    INSP_IN_PROGRESS,
    INSP_SUBMITTED,
    INSP_REVIEWED,
    INSP_CLOSED
]


def create_inspection(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    officer_id = data.get("officer_id")
    initial_status = INSP_ASSIGNED if officer_id else INSP_SCHEDULED

    doc = {
        "mine_id": str(data["mine_id"]),
        "officer_id": str(officer_id) if officer_id else None,
        "inspection_type": data.get("inspection_type", "ROUTINE_SAFETY"),  # ROUTINE_SAFETY, DGMS_SURPRISE, ENVIRONMENTAL, ELECTRICAL, MECHANICAL
        "location": data.get("location", "Pit Zone").strip(),
        "latitude": float(data.get("latitude", 23.7957)),
        "longitude": float(data.get("longitude", 86.4304)),
        "scheduled_date": data.get("scheduled_date", now.isoformat()),
        "timestamp": now,
        "observations": data.get("observations", []),
        "photos": data.get("photos", []),
        "videos": data.get("videos", []),
        "severity": data.get("severity", "LOW"),  # LOW, MEDIUM, HIGH, CRITICAL
        "status": initial_status,
        "remarks": data.get("remarks", ""),
        "created_by": str(user.get("_id", user.get("id"))) if user else "SYSTEM",
        "created_at": now,
        "updated_at": now
    }
    res = mongo.inspections.insert_one(doc)
    doc["_id"] = res.inserted_id

    log_audit_event(
        action="CREATE",
        entity="INSPECTION",
        entity_id=str(res.inserted_id),
        user=user,
        new_value={"mine_id": doc["mine_id"], "type": doc["inspection_type"]}
    )

    if officer_id:
        create_notification(
            user_id=officer_id,
            role="INSPECTION_OFFICER",
            title="New Inspection Assigned",
            message=f"You have been assigned an inspection at mine {doc['mine_id']}",
            event_type="assigned_inspection",
            entity_type="INSPECTION",
            entity_id=str(res.inserted_id),
            severity="INFO"
        )

    return doc


def assign_inspection(inspection_id: str, officer_id: str, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(inspection_id)} if ObjectId.is_valid(inspection_id) else {"_id": inspection_id}
    now = datetime.datetime.utcnow()
    update_data = {
        "officer_id": str(officer_id),
        "status": INSP_ASSIGNED,
        "updated_at": now
    }
    mongo.inspections.update_one(query, {"$set": update_data})
    doc = mongo.inspections.find_one(query)
    
    if doc:
        log_audit_event(action="ASSIGN", entity="INSPECTION", entity_id=inspection_id, user=user, new_value={"assigned_to": officer_id})
        create_notification(
            user_id=officer_id,
            role="INSPECTION_OFFICER",
            title="Inspection Assigned",
            message=f"Inspection #{inspection_id[:8]} has been assigned to you.",
            event_type="assigned_inspection",
            entity_type="INSPECTION",
            entity_id=inspection_id,
            severity="INFO"
        )
    return doc


def start_inspection(inspection_id: str, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(inspection_id)} if ObjectId.is_valid(inspection_id) else {"_id": inspection_id}
    now = datetime.datetime.utcnow()
    mongo.inspections.update_one(query, {"$set": {"status": INSP_IN_PROGRESS, "started_at": now, "updated_at": now}})
    doc = mongo.inspections.find_one(query)
    if doc:
        log_audit_event(action="START", entity="INSPECTION", entity_id=inspection_id, user=user)
    return doc


def submit_inspection(
    inspection_id: str,
    observations: List[Dict[str, Any]],
    photos: Optional[List[str]] = None,
    videos: Optional[List[str]] = None,
    severity: str = "LOW",
    remarks: Optional[str] = None,
    user: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(inspection_id)} if ObjectId.is_valid(inspection_id) else {"_id": inspection_id}
    now = datetime.datetime.utcnow()
    update_data = {
        "observations": observations,
        "photos": photos or [],
        "videos": videos or [],
        "severity": severity.upper(),
        "remarks": remarks or "",
        "status": INSP_SUBMITTED,
        "submitted_at": now,
        "updated_at": now
    }
    mongo.inspections.update_one(query, {"$set": update_data})
    doc = mongo.inspections.find_one(query)
    if doc:
        log_audit_event(action="SUBMIT", entity="INSPECTION", entity_id=inspection_id, user=user, new_value={"severity": severity})
        create_notification(
            user_id=None,
            role="SAFETY_OFFICER",
            title="Inspection Submitted for Review",
            message=f"Inspection #{inspection_id[:8]} at mine {doc.get('mine_id')} is ready for review.",
            event_type="inspection_submitted",
            entity_type="INSPECTION",
            entity_id=inspection_id,
            severity=severity
        )
    return doc


def review_inspection(inspection_id: str, remarks: str, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(inspection_id)} if ObjectId.is_valid(inspection_id) else {"_id": inspection_id}
    now = datetime.datetime.utcnow()
    mongo.inspections.update_one(query, {"$set": {"status": INSP_REVIEWED, "review_remarks": remarks, "reviewed_by": str(user.get("_id", user.get("id"))) if user else "OFFICER", "reviewed_at": now, "updated_at": now}})
    doc = mongo.inspections.find_one(query)
    if doc:
        log_audit_event(action="APPROVE", entity="INSPECTION", entity_id=inspection_id, user=user)
    return doc


def close_inspection(inspection_id: str, closure_remarks: str, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(inspection_id)} if ObjectId.is_valid(inspection_id) else {"_id": inspection_id}
    now = datetime.datetime.utcnow()
    mongo.inspections.update_one(query, {"$set": {"status": INSP_CLOSED, "closure_remarks": closure_remarks, "closed_at": now, "updated_at": now}})
    doc = mongo.inspections.find_one(query)
    if doc:
        log_audit_event(action="CLOSE", entity="INSPECTION", entity_id=inspection_id, user=user)
    return doc


def list_inspections(mine_id: Optional[str] = None, status: Optional[str] = None, officer_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query = {}
    if mine_id:
        query["mine_id"] = str(mine_id)
    if status:
        query["status"] = status.upper()
    if officer_id:
        query["officer_id"] = str(officer_id)
    return list(mongo.inspections.find(query).sort("timestamp", -1))


def get_inspection_by_id(inspection_id: str) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(inspection_id)} if ObjectId.is_valid(inspection_id) else {"_id": inspection_id}
    return mongo.inspections.find_one(query)
