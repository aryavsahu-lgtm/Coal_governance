from typing import Dict, Any, List, Optional
from app.database import mongo
from app.ai.risk_engine import calculate_mine_risk_score


def get_gis_layers(user: Optional[Dict[str, Any]] = None, mine_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Constructs GeoJSON feature collections for Mines, Zones, Violations,
    Incidents, Inspections, and Field Reports. Respects role-based scoping.
    """
    user_role = user.get("role") if user else "PUBLIC"
    user_mine = str(user.get("mine_id") or "") if user else ""

    # Scope filter
    effective_mine_id = mine_id
    if user_role in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER") and user_mine:
        effective_mine_id = user_mine

    query = {"mine_id": str(effective_mine_id)} if effective_mine_id else {}

    # 1. Mine Points
    mine_query = {"_id": mongo.mines.find_one({"_id": effective_mine_id})["_id"]} if (effective_mine_id and False) else {}
    if effective_mine_id:
        from bson import ObjectId
        m_q = {"_id": ObjectId(effective_mine_id)} if ObjectId.is_valid(effective_mine_id) else {"_id": effective_mine_id}
        mines = list(mongo.mines.find(m_q))
    else:
        mines = list(mongo.mines.find())

    mine_features = []
    for m in mines:
        mid = str(m["_id"])
        risk = calculate_mine_risk_score(mid)
        mine_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(m.get("longitude", 86.4304)), float(m.get("latitude", 23.7957))]
            },
            "properties": {
                "entity": "MINE",
                "id": mid,
                "name": m.get("mine_name"),
                "code": m.get("mine_code"),
                "status": m.get("operational_status", "ACTIVE"),
                "type": m.get("mine_type", "OPENCAST"),
                "risk_score": risk.get("risk_score", 20),
                "risk_level": risk.get("risk_level", "LOW")
            }
        })

    # 2. Zone Polygons
    zone_features = []
    zones = list(mongo.zones.find(query))
    for z in zones:
        coords = z.get("boundary_coordinates", [])
        if coords and len(coords) >= 3:
            # Convert [lat, lng] to GeoJSON standard [lng, lat]
            polygon_ring = [[float(pt[1]), float(pt[0])] for pt in coords]
            # Ensure closed ring
            if polygon_ring[0] != polygon_ring[-1]:
                polygon_ring.append(polygon_ring[0])

            zone_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [polygon_ring]
                },
                "properties": {
                    "entity": "ZONE",
                    "id": str(z["_id"]),
                    "name": z.get("zone_name"),
                    "code": z.get("zone_code"),
                    "type": z.get("zone_type"),
                    "risk_level": z.get("risk_level", "MEDIUM"),
                    "is_restricted": z.get("is_restricted", False)
                }
            })

    # 3. Violations Points
    violation_features = []
    violations = list(mongo.violations.find(query))
    for v in violations:
        violation_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(v.get("longitude", 86.4304)), float(v.get("latitude", 23.7957))]
            },
            "properties": {
                "entity": "VIOLATION",
                "id": str(v["_id"]),
                "category": v.get("category"),
                "severity": v.get("severity", "MEDIUM"),
                "status": v.get("status"),
                "description": v.get("description"),
                "created_at": v.get("created_at").isoformat() if hasattr(v.get("created_at"), "isoformat") else str(v.get("created_at"))
            }
        })

    # 4. Incidents Points
    incident_features = []
    incidents = list(mongo.incidents.find(query))
    for inc in incidents:
        incident_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(inc.get("longitude", 86.4304)), float(inc.get("latitude", 23.7957))]
            },
            "properties": {
                "entity": "INCIDENT",
                "id": str(inc["_id"]),
                "type": inc.get("incident_type"),
                "severity": inc.get("severity", "HIGH"),
                "status": inc.get("investigation_status"),
                "description": inc.get("description")
            }
        })

    # 5. Field Reports Points
    field_features = []
    reports = list(mongo.field_reports.find(query))
    for r in reports:
        field_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(r.get("longitude", 86.4304)), float(r.get("latitude", 23.7957))]
            },
            "properties": {
                "entity": "FIELD_REPORT",
                "id": str(r["_id"]),
                "category": r.get("category"),
                "observation": r.get("observation"),
                "officer_name": r.get("officer_name")
            }
        })

    return {
        "mines": {"type": "FeatureCollection", "features": mine_features},
        "zones": {"type": "FeatureCollection", "features": zone_features},
        "violations": {"type": "FeatureCollection", "features": violation_features},
        "incidents": {"type": "FeatureCollection", "features": incident_features},
        "field_reports": {"type": "FeatureCollection", "features": field_features}
    }
