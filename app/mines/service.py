import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.database import mongo
from app.audit.service import log_audit_event


def create_mine(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    doc = {
        "mine_name": data["mine_name"].strip(),
        "mine_code": data["mine_code"].strip().upper(),
        "subsidiary_id": str(data["subsidiary_id"]),
        "location": data.get("location", "").strip(),
        "latitude": float(data.get("latitude", 23.7957)),
        "longitude": float(data.get("longitude", 86.4304)),
        "mine_type": data.get("mine_type", "OPENCAST"),  # OPENCAST, UNDERGROUND, MIXED
        "operational_status": data.get("operational_status", "ACTIVE"),  # ACTIVE, INACTIVE, SUSPENDED
        "manager": {
            "name": data.get("manager_name", "Mine Manager"),
            "email": data.get("manager_email", ""),
            "phone": data.get("manager_phone", "")
        },
        "contact_information": data.get("contact_information", ""),
        "created_at": now,
        "updated_at": now
    }
    res = mongo.mines.insert_one(doc)
    doc["_id"] = res.inserted_id

    log_audit_event(
        action="CREATE",
        entity="MINE",
        entity_id=str(res.inserted_id),
        user=user,
        new_value={"mine_name": doc["mine_name"], "mine_code": doc["mine_code"]}
    )
    return doc


def update_mine(mine_id: str, data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(mine_id)} if ObjectId.is_valid(mine_id) else {"_id": mine_id}
    old_mine = mongo.mines.find_one(query)
    if not old_mine:
        return None

    allowed_updates = [
        "mine_name", "location", "latitude", "longitude",
        "operational_status", "mine_type", "manager", "contact_information"
    ]
    update_doc = {"updated_at": datetime.datetime.utcnow()}
    for key in allowed_updates:
        if key in data:
            update_doc[key] = data[key]

    mongo.mines.update_one(query, {"$set": update_doc})
    new_mine = mongo.mines.find_one(query)

    log_audit_event(
        action="UPDATE",
        entity="MINE",
        entity_id=str(mine_id),
        user=user,
        old_value={"status": old_mine.get("operational_status")},
        new_value={"status": new_mine.get("operational_status")}
    )
    return new_mine


def get_mine_by_id(mine_id: str) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(mine_id)} if ObjectId.is_valid(mine_id) else {"_id": mine_id}
    return mongo.mines.find_one(query)


def list_mines(subsidiary_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query = {}
    if subsidiary_id:
        query["subsidiary_id"] = str(subsidiary_id)
    return list(mongo.mines.find(query))


def set_mine_status(mine_id: str, status: str, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    return update_mine(mine_id, {"operational_status": status.upper()}, user)


# Zones inside mines
def create_zone(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    doc = {
        "mine_id": str(data["mine_id"]),
        "zone_name": data["zone_name"].strip(),
        "zone_code": data["zone_code"].strip().upper(),
        "zone_type": data.get("zone_type", "PIT"),  # PIT, HAUL_ROAD, BLASTING, WASHERY, RESTRICTED
        "risk_level": data.get("risk_level", "MEDIUM"),  # LOW, MEDIUM, HIGH, CRITICAL
        "is_restricted": data.get("is_restricted", False),
        "boundary_coordinates": data.get("boundary_coordinates", []),  # Polygon points [[lat, lng], ...]
        "created_at": now,
        "updated_at": now
    }
    res = mongo.zones.insert_one(doc)
    doc["_id"] = res.inserted_id

    log_audit_event(
        action="CREATE",
        entity="ZONE",
        entity_id=str(res.inserted_id),
        user=user,
        new_value={"zone_name": doc["zone_name"], "mine_id": doc["mine_id"]}
    )
    return doc


def list_zones(mine_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query = {}
    if mine_id:
        query["mine_id"] = str(mine_id)
    return list(mongo.zones.find(query))


def get_zone_by_id(zone_id: str) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(zone_id)} if ObjectId.is_valid(zone_id) else {"_id": zone_id}
    return mongo.zones.find_one(query)
