import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.database import mongo
from app.audit.service import log_audit_event
from app.notifications.service import create_notification

INC_REPORTED = "REPORTED"
INC_UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
INC_ROOT_CAUSE_ANALYSIS = "ROOT_CAUSE_ANALYSIS"
INC_CORRECTIVE_ACTION = "CORRECTIVE_ACTION"
INC_VERIFICATION = "VERIFICATION"
INC_CLOSED = "CLOSED"

INCIDENT_LIFECYCLE = [
    INC_REPORTED,
    INC_UNDER_INVESTIGATION,
    INC_ROOT_CAUSE_ANALYSIS,
    INC_CORRECTIVE_ACTION,
    INC_VERIFICATION,
    INC_CLOSED
]


def report_incident(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    severity = data.get("severity", "HIGH").upper()
    reporter_id = str(user.get("_id", user.get("id"))) if user else "OFFICER"

    doc = {
        "mine_id": str(data["mine_id"]),
        "location": data.get("location", "Pit Zone").strip(),
        "latitude": float(data.get("latitude", 23.7957)),
        "longitude": float(data.get("longitude", 86.4304)),
        "incident_type": data.get("incident_type", "EQUIPMENT_SAFETY"),  # ROOF_FALL, SLOPE_FAILURE, GAS_EXCEEDANCE, FIRE, MACHINERY
        "severity": severity,
        "description": data["description"].strip(),
        "persons_involved": data.get("persons_involved", []),
        "evidence": data.get("evidence", []),
        "reported_by": reporter_id,
        "reported_at": now,
        "investigation_status": INC_REPORTED,
        "investigation_team": data.get("investigation_team", []),
        "root_cause": None,
        "root_cause_analysis_notes": None,
        "corrective_action": None,
        "closure_status": "OPEN",
        "created_at": now,
        "updated_at": now
    }
    res = mongo.incidents.insert_one(doc)
    doc["_id"] = res.inserted_id
    incident_id = str(res.inserted_id)

    log_audit_event(
        action="REPORT",
        entity="INCIDENT",
        entity_id=incident_id,
        user=user,
        new_value={"type": doc["incident_type"], "severity": severity, "mine_id": doc["mine_id"]}
    )

    create_notification(
        user_id=None,
        role="SAFETY_OFFICER",
        title=f"CRITICAL: Incident Reported ({doc['incident_type']})",
        message=f"{doc['description']} at mine #{doc['mine_id']}. Immediate investigation launched.",
        event_type="incident_created",
        entity_type="INCIDENT",
        entity_id=incident_id,
        severity=severity
    )

    # If critical, notify corporate management immediately
    if severity == "CRITICAL":
        create_notification(
            user_id=None,
            role="CORPORATE_MANAGEMENT",
            title=f"URGENT STATUTORY ALERT: Critical Mine Incident",
            message=f"Critical safety incident occurred at mine #{doc['mine_id']}. DGMS notification required.",
            event_type="incident_created",
            entity_type="INCIDENT",
            entity_id=incident_id,
            severity="CRITICAL"
        )

    return doc


def advance_incident_status(
    incident_id: str,
    status: str,
    root_cause: Optional[str] = None,
    corrective_action: Optional[str] = None,
    notes: Optional[str] = None,
    user: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(incident_id)} if ObjectId.is_valid(incident_id) else {"_id": incident_id}
    now = datetime.datetime.utcnow()

    update_doc = {
        "investigation_status": status.upper(),
        "updated_at": now
    }
    if root_cause:
        update_doc["root_cause"] = root_cause
    if notes:
        update_doc["root_cause_analysis_notes"] = notes
    if corrective_action:
        update_doc["corrective_action"] = corrective_action
    if status.upper() == INC_CLOSED:
        update_doc["closure_status"] = "CLOSED"
        update_doc["closed_at"] = now
        update_doc["closed_by"] = str(user.get("_id", user.get("id"))) if user else "SAFETY_OFFICER"

    mongo.incidents.update_one(query, {"$set": update_doc})
    doc = mongo.incidents.find_one(query)

    if doc:
        log_audit_event(
            action="UPDATE_STATUS",
            entity="INCIDENT",
            entity_id=incident_id,
            user=user,
            new_value={"status": status, "root_cause": root_cause}
        )
    return doc


def list_incidents(mine_id: Optional[str] = None, severity: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    query = {}
    if mine_id:
        query["mine_id"] = str(mine_id)
    if severity:
        query["severity"] = severity.upper()
    if status:
        query["investigation_status"] = status.upper()
    return list(mongo.incidents.find(query).sort("reported_at", -1))


def get_incident_by_id(incident_id: str) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(incident_id)} if ObjectId.is_valid(incident_id) else {"_id": incident_id}
    return mongo.incidents.find_one(query)
