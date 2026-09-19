import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.database import mongo
from app.audit.service import log_audit_event
from app.notifications.service import create_notification


def submit_field_report(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    officer_id = str(user.get("_id", user.get("id"))) if user else "UNKNOWN_OFFICER"
    officer_name = user.get("name", "Field Officer") if user else "Field Officer"

    doc = {
        "mine_id": str(data["mine_id"]),
        "zone_id": str(data.get("zone_id", "")),
        "zone_name": data.get("zone_name", "General Mine Area"),
        "category": data.get("category", "Safety"),  # Safety, Environment, Machine, PPE, Hazard
        "observation": data.get("observation", "").strip(),
        "evidence_photos": data.get("photos", []),
        "evidence_videos": data.get("videos", []),
        "latitude": float(data.get("latitude", 23.7957)),
        "longitude": float(data.get("longitude", 86.4304)),
        "timestamp": now,
        "officer_id": officer_id,
        "officer_name": officer_name,
        "is_synced_from_offline": data.get("is_synced_from_offline", False),
        "status": "PENDING_TRIAGE",  # PENDING_TRIAGE, CONVERTED_TO_VIOLATION, DISMISSED
        "created_at": now
    }
    res = mongo.field_reports.insert_one(doc)
    doc["_id"] = res.inserted_id

    log_audit_event(
        action="CREATE",
        entity="FIELD_REPORT",
        entity_id=str(res.inserted_id),
        user=user,
        new_value={"mine_id": doc["mine_id"], "category": doc["category"]}
    )

    create_notification(
        user_id=None,
        role="SAFETY_OFFICER",
        title=f"New Field Observation: {doc['category']}",
        message=f"{officer_name} reported an observation at {doc['zone_name']} in mine #{doc['mine_id']}",
        event_type="field_observation",
        entity_type="FIELD_REPORT",
        entity_id=str(res.inserted_id),
        severity="INFO"
    )

    return doc


def list_field_reports(mine_id: Optional[str] = None, zone_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query = {}
    if mine_id:
        query["mine_id"] = str(mine_id)
    if zone_id:
        query["zone_id"] = str(zone_id)
    return list(mongo.field_reports.find(query).sort("timestamp", -1))


def get_field_report_by_id(report_id: str) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(report_id)} if ObjectId.is_valid(report_id) else {"_id": report_id}
    return mongo.field_reports.find_one(query)
