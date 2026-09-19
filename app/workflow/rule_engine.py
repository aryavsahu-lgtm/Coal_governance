import logging
import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId
from app.database import mongo

logger = logging.getLogger("coal_governance.rules")

DEFAULT_RULES = [
    {
        "rule_id": "RULE_PPE_HELMET_VEST",
        "name": "Mandatory PPE (Helmet & Vest) Violation",
        "category": "Safety",
        "conditions": {
            "missing_helmet": True
        },
        "action": "CREATE_VIOLATION",
        "violation_category": "PPE_VIOLATION",
        "description": "Worker detected inside extraction/operational zone without mandatory protective helmet.",
        "severity": "HIGH",
        "deadline_hours": 24,
        "enabled": True
    },
    {
        "rule_id": "RULE_RESTRICTED_ZONE_ENTRY",
        "name": "Unauthorized Entry into High-Risk Restricted Zone",
        "category": "Safety",
        "conditions": {
            "unauthorized_zone_entry": True
        },
        "action": "CREATE_VIOLATION",
        "violation_category": "RESTRICTED_AREA",
        "description": "Personnel breach detected in blasting or active pit perimeter.",
        "severity": "CRITICAL",
        "deadline_hours": 4,
        "enabled": True
    },
    {
        "rule_id": "RULE_DOC_EXPIRED",
        "name": "Statutory Contractor/Machinery Document Expired",
        "category": "Compliance",
        "conditions": {
            "document_expired": True
        },
        "action": "CREATE_VIOLATION",
        "violation_category": "STATUTORY_NON_COMPLIANCE",
        "description": "Mandatory DGMS fitness certificate or contractor safety clearance has expired.",
        "severity": "HIGH",
        "deadline_hours": 48,
        "enabled": True
    },
    {
        "rule_id": "RULE_REPEAT_VIOLATION",
        "name": "Repeat Violations Flagging",
        "category": "Risk",
        "conditions": {
            "repeated_violation_count_gte": 3
        },
        "action": "MARK_HIGH_RISK",
        "description": "Zone has accumulated 3 or more safety violations within the last 30 days.",
        "severity": "CRITICAL",
        "deadline_hours": 12,
        "enabled": True
    },
    {
        "rule_id": "RULE_CONTRACT_SAFETY_CLAUSE",
        "name": "Mandatory Contract Safety Clauses & Insurance",
        "category": "Contractor Governance",
        "conditions": {
            "is_contract": True,
            "missing_safety_clauses": True
        },
        "action": "CREATE_VIOLATION",
        "violation_category": "CONTRACTOR_SAFETY_NON_COMPLIANCE",
        "description": "Uploaded contractor agreement lacks mandatory DGMS worker safety indemnification or insurance clauses.",
        "severity": "HIGH",
        "deadline_hours": 48,
        "enabled": True
    },
    {
        "rule_id": "RULE_MINE_SOP_COMPLIANCE",
        "name": "Mine Safety SOP Standard Compliance",
        "category": "Operational Safety",
        "conditions": {
            "is_sop": True,
            "missing_emergency_rules": True
        },
        "action": "CREATE_VIOLATION",
        "violation_category": "PROCEDURAL_NON_COMPLIANCE",
        "description": "Uploaded Mine Standard Operating Procedure (SOP) lacks mandatory emergency evacuation protocols.",
        "severity": "MEDIUM",
        "deadline_hours": 72,
        "enabled": True
    }
]


def seed_default_rules():
    """Ensure baseline rules exist in database."""
    try:
        for r in DEFAULT_RULES:
            existing = mongo.rules.find_one({"rule_id": r["rule_id"]})
            if not existing:
                r["created_at"] = datetime.datetime.utcnow()
                r["updated_at"] = datetime.datetime.utcnow()
                mongo.rules.insert_one(r)
    except Exception as e:
        logger.warning(f"Default rules check warning: {e}")


def evaluate_rules(event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluates enabled rules against an incoming event dictionary.
    Returns list of triggered rules and actions.
    """
    triggered = []
    rules = list(mongo.rules.find({"enabled": True}))
    if not rules:
        rules = [r for r in DEFAULT_RULES if r.get("enabled")]

    for rule in rules:
        conds = rule.get("conditions", {})
        matched = True

        for k, expected_v in conds.items():
            if k.endswith("_gte"):
                base_k = k[:-4]
                actual_v = event_data.get(base_k, 0)
                if not (isinstance(actual_v, (int, float)) and actual_v >= expected_v):
                    matched = False
                    break
            elif k.endswith("_lte"):
                base_k = k[:-4]
                actual_v = event_data.get(base_k, 0)
                if not (isinstance(actual_v, (int, float)) and actual_v <= expected_v):
                    matched = False
                    break
            else:
                if event_data.get(k) != expected_v:
                    matched = False
                    break

        if matched:
            logger.info(f"[RuleEngine] Triggered rule: {rule.get('name')} ({rule.get('rule_id')})")
            triggered.append(rule)

    return triggered


def evaluate_document_compliance(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluates an uploaded document, contract, or SOP against statutory compliance rules.
    """
    doc_type = str(doc.get("document_type", "")).upper()
    extracted_text = str(doc.get("extracted_text", "")).lower()
    status = str(doc.get("status", "")).upper()

    is_contract = any(k in doc_type for k in ["CONTRACT", "AGREEMENT"])
    is_sop = any(k in doc_type for k in ["SOP", "SAFETY_RULES", "PROCEDURE"])

    event = {
        "document_id": str(doc.get("_id", "")),
        "document_type": doc_type,
        "mine_id": str(doc.get("mine_id", "")),
        "document_expired": (status == "EXPIRED"),
        "is_contract": is_contract,
        "missing_safety_clauses": is_contract and not any(k in extracted_text for k in ["safety", "ppe", "insurance", "dgms", "indemn"]),
        "is_sop": is_sop,
        "missing_emergency_rules": is_sop and not any(k in extracted_text for k in ["emergency", "evacuation", "siren", "muster", "safety", "hazard"])
    }

    triggered = evaluate_rules(event)
    return triggered
