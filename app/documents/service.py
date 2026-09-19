import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.database import mongo
from app.audit.service import log_audit_event
from app.notifications.service import create_notification
from app.ai.ocr_engine import run_ocr_on_file


def save_document_record(
    file_meta: Dict[str, Any],
    document_type: str,
    mine_id: str,
    user: Optional[Dict[str, Any]] = None,
    manual_override: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Runs OCR, parses metadata, stores record, and performs expiry checks."""
    now = datetime.datetime.utcnow()
    user_id = str(user.get("_id", user.get("id"))) if user else "SYSTEM"

    # Execute OCR
    ocr_result = run_ocr_on_file(file_meta["absolute_path"])

    issue_date = ocr_result.get("issue_date")
    expiry_date = ocr_result.get("expiry_date")
    doc_num = ocr_result.get("document_number")
    authority = ocr_result.get("authority")

    # If manual overrides provided by user
    if manual_override:
        if manual_override.get("expiry_date"):
            try:
                expiry_date = datetime.datetime.fromisoformat(manual_override["expiry_date"].replace("Z", ""))
            except Exception:
                pass
        if manual_override.get("issue_date"):
            try:
                issue_date = datetime.datetime.fromisoformat(manual_override["issue_date"].replace("Z", ""))
            except Exception:
                pass
        if manual_override.get("document_number"):
            doc_num = manual_override["document_number"]
        if manual_override.get("authority"):
            authority = manual_override["authority"]

    # Compute status
    status = "ACTIVE"
    if expiry_date:
        if expiry_date < now:
            status = "EXPIRED"
        elif expiry_date <= now + datetime.timedelta(days=30):
            status = "EXPIRING_SOON"
    elif ocr_result.get("requires_manual_verification"):
        status = "REQUIRES_MANUAL_REVIEW"

    doc = {
        "original_filename": file_meta["filename"],
        "file_path": file_meta["relative_path"],
        "file_url": file_meta["url"],
        "file_size": file_meta["size_bytes"],
        "document_type": document_type.upper(),
        "mine_id": str(mine_id),
        "document_number": doc_num,
        "authority": authority,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "extracted_text": ocr_result.get("extracted_text", ""),
        "ocr_mode": ocr_result.get("ocr_mode"),
        "status": status,
        "requires_manual_verification": ocr_result.get("requires_manual_verification", False),
        "upload_user": user_id,
        "timestamp": now,
        "created_at": now,
        "updated_at": now
    }
    res = mongo.documents.insert_one(doc)
    doc["_id"] = res.inserted_id
    doc_id = str(res.inserted_id)

    log_audit_event(
        action="UPLOAD",
        entity="DOCUMENT",
        entity_id=doc_id,
        user=user,
        new_value={"doc_type": doc["document_type"], "doc_num": doc_num, "status": status}
    )

    # Expiry alerts
    if status == "EXPIRED":
        create_notification(
            user_id=None,
            role="SAFETY_OFFICER",
            title=f"STATUTORY COMPLIANCE ALERT: Expired Document",
            message=f"{doc['document_type']} ({doc_num}) for mine #{mine_id} has EXPIRED on {expiry_date.strftime('%d-%b-%Y') if expiry_date else 'unknown'}.",
            event_type="document_expiry",
            entity_type="DOCUMENT",
            entity_id=doc_id,
            severity="HIGH"
        )
    elif status == "EXPIRING_SOON":
        create_notification(
            user_id=None,
            role="SAFETY_OFFICER",
            title=f"REMINDER: Document Expiring Soon",
            message=f"{doc['document_type']} ({doc_num}) expires on {expiry_date.strftime('%d-%b-%Y') if expiry_date else 'soon'}.",
            event_type="document_expiry",
            entity_type="DOCUMENT",
            entity_id=doc_id,
            severity="WARNING"
        )

    # 4. Trigger Statutory Rule Engine Evaluation
    try:
        from app.workflow.rule_engine import evaluate_document_compliance
        triggered_rules = evaluate_document_compliance(doc)
        doc["triggered_rules"] = [r.get("rule_id") for r in triggered_rules]

        for rule in triggered_rules:
            create_notification(
                user_id=None,
                role="SAFETY_OFFICER",
                title=f"RULE ENGINE ALERT: {rule.get('name')}",
                message=f"Rule {rule.get('rule_id')} triggered for {doc['document_type']}: {rule.get('description')}",
                event_type="rule_violation",
                entity_type="DOCUMENT",
                entity_id=doc_id,
                severity=rule.get("severity", "HIGH")
            )
            # Update document status if rule flagged critical/high non-compliance
            if rule.get("action") == "CREATE_VIOLATION":
                mongo.documents.update_one({"_id": res.inserted_id}, {"$set": {"compliance_flag": rule.get("rule_id")}})
    except Exception as re_err:
        logger.warning(f"[Documents] Rule engine evaluation error: {re_err}")

    return doc


def scan_and_update_document_expiries() -> Dict[str, Any]:
    """Batch scan to refresh document expiry states and trigger warnings."""
    now = datetime.datetime.utcnow()
    docs = list(mongo.documents.find())
    expired_count = 0
    expiring_soon_count = 0

    for d in docs:
        expiry = d.get("expiry_date")
        if not expiry or not isinstance(expiry, datetime.datetime):
            continue

        doc_id = str(d["_id"])
        new_status = d.get("status")

        if expiry < now and d.get("status") != "EXPIRED":
            new_status = "EXPIRED"
            expired_count += 1
            mongo.documents.update_one({"_id": d["_id"]}, {"$set": {"status": "EXPIRED", "updated_at": now}})
            create_notification(
                user_id=None,
                role="SAFETY_OFFICER",
                title="Document Expired",
                message=f"Document {d.get('document_number', '')} has expired. Compliance breach warning.",
                event_type="document_expiry",
                entity_type="DOCUMENT",
                entity_id=doc_id,
                severity="HIGH"
            )
        elif now <= expiry <= now + datetime.timedelta(days=30) and d.get("status") != "EXPIRING_SOON":
            new_status = "EXPIRING_SOON"
            expiring_soon_count += 1
            mongo.documents.update_one({"_id": d["_id"]}, {"$set": {"status": "EXPIRING_SOON", "updated_at": now}})

    return {"total": len(docs), "expired": expired_count, "expiring_soon": expiring_soon_count}


def list_documents(mine_id: Optional[str] = None, doc_type: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    query = {}
    if mine_id:
        query["mine_id"] = str(mine_id)
    if doc_type:
        query["document_type"] = doc_type.upper()
    if status:
        query["status"] = status.upper()
    return list(mongo.documents.find(query).sort("timestamp", -1))


def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    query = {"_id": ObjectId(doc_id)} if ObjectId.is_valid(doc_id) else {"_id": doc_id}
    return mongo.documents.find_one(query)
