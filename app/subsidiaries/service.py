import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.database import mongo
from app.audit.service import log_audit_event


def create_subsidiary(data: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    doc = {
        "name": data["name"].strip(),
        "code": data["code"].strip().upper(),
        "headquarters": data.get("headquarters", ""),
        "contact_email": data.get("contact_email", ""),
        "contact_phone": data.get("contact_phone", ""),
        "is_active": data.get("is_active", True),
        "created_at": now,
        "updated_at": now
    }
    res = mongo.subsidiaries.insert_one(doc)
    doc["_id"] = res.inserted_id

    log_audit_event(
        action="CREATE",
        entity="SUBSIDIARY",
        entity_id=str(res.inserted_id),
        user=user,
        new_value={"name": doc["name"], "code": doc["code"]}
    )
    return doc


def list_subsidiaries() -> List[Dict[str, Any]]:
    return list(mongo.subsidiaries.find())


def get_subsidiary_by_id(sub_id: str) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(sub_id)} if ObjectId.is_valid(sub_id) else {"_id": sub_id}
    return mongo.subsidiaries.find_one(query)
