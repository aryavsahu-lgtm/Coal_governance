import logging
import pymongo
from app.database.mongo import mongo

logger = logging.getLogger("coal_governance.indexes")


def create_indexes():
    """Initializes all required indexes for collections."""
    try:
        # Users
        mongo.users.create_index([("email", pymongo.ASCENDING)], unique=True)
        mongo.users.create_index([("role", pymongo.ASCENDING)])
        mongo.users.create_index([("mine_id", pymongo.ASCENDING)])
        mongo.users.create_index([("subsidiary_id", pymongo.ASCENDING)])

        # Subsidiaries
        mongo.subsidiaries.create_index([("code", pymongo.ASCENDING)], unique=True)

        # Mines
        mongo.mines.create_index([("mine_code", pymongo.ASCENDING)], unique=True)
        mongo.mines.create_index([("subsidiary_id", pymongo.ASCENDING)])
        mongo.mines.create_index([("operational_status", pymongo.ASCENDING)])

        # Zones
        mongo.zones.create_index([("mine_id", pymongo.ASCENDING)])
        mongo.zones.create_index([("zone_code", pymongo.ASCENDING)])

        # Compliance Requirements
        mongo.compliance_requirements.create_index([("mine_id", pymongo.ASCENDING)])
        mongo.compliance_requirements.create_index([("status", pymongo.ASCENDING)])
        mongo.compliance_requirements.create_index([("category", pymongo.ASCENDING)])
        mongo.compliance_requirements.create_index([("due_date", pymongo.ASCENDING)])

        # Inspections
        mongo.inspections.create_index([("mine_id", pymongo.ASCENDING)])
        mongo.inspections.create_index([("officer_id", pymongo.ASCENDING)])
        mongo.inspections.create_index([("status", pymongo.ASCENDING)])
        mongo.inspections.create_index([("created_at", pymongo.DESCENDING)])

        # Field Reports
        mongo.field_reports.create_index([("mine_id", pymongo.ASCENDING)])
        mongo.field_reports.create_index([("zone_id", pymongo.ASCENDING)])
        mongo.field_reports.create_index([("timestamp", pymongo.DESCENDING)])

        # Violations
        mongo.violations.create_index([("mine_id", pymongo.ASCENDING)])
        mongo.violations.create_index([("status", pymongo.ASCENDING)])
        mongo.violations.create_index([("severity", pymongo.ASCENDING)])
        mongo.violations.create_index([("assigned_to", pymongo.ASCENDING)])
        mongo.violations.create_index([("deadline", pymongo.ASCENDING)])
        mongo.violations.create_index([("created_at", pymongo.DESCENDING)])

        # Corrective Actions (CAPA)
        mongo.corrective_actions.create_index([("violation_id", pymongo.ASCENDING)])
        mongo.corrective_actions.create_index([("assigned_to", pymongo.ASCENDING)])
        mongo.corrective_actions.create_index([("verification_status", pymongo.ASCENDING)])
        mongo.corrective_actions.create_index([("deadline", pymongo.ASCENDING)])

        # Incidents
        mongo.incidents.create_index([("mine_id", pymongo.ASCENDING)])
        mongo.incidents.create_index([("severity", pymongo.ASCENDING)])
        mongo.incidents.create_index([("investigation_status", pymongo.ASCENDING)])
        mongo.incidents.create_index([("reported_at", pymongo.DESCENDING)])

        # Contractors
        mongo.contractors.create_index([("mine_id", pymongo.ASCENDING)])
        mongo.contractors.create_index([("compliance_status", pymongo.ASCENDING)])
        mongo.contractors.create_index([("risk_score", pymongo.DESCENDING)])

        # Documents
        mongo.documents.create_index([("mine_id", pymongo.ASCENDING)])
        mongo.documents.create_index([("document_type", pymongo.ASCENDING)])
        mongo.documents.create_index([("expiry_date", pymongo.ASCENDING)])

        # Notifications
        mongo.notifications.create_index([("user_id", pymongo.ASCENDING)])
        mongo.notifications.create_index([("is_read", pymongo.ASCENDING)])
        mongo.notifications.create_index([("created_at", pymongo.DESCENDING)])

        # Audit Logs
        mongo.audit_logs.create_index([("user_id", pymongo.ASCENDING)])
        mongo.audit_logs.create_index([("action", pymongo.ASCENDING)])
        mongo.audit_logs.create_index([("entity", pymongo.ASCENDING)])
        mongo.audit_logs.create_index([("timestamp", pymongo.DESCENDING)])

        logger.info("[Database] All MongoDB indexes created successfully.")
        return True
    except Exception as e:
        logger.warning(f"[Database] Index creation warning: {e}")
        return False
