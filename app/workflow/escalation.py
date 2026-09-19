import datetime
import logging
from typing import List, Dict, Any
from app.database import mongo
from app.notifications.service import create_notification
from app.audit.service import log_audit_event

logger = logging.getLogger("coal_governance.escalation")


def process_escalations() -> Dict[str, Any]:
    """
    Checks all open violations and corrective actions against deadlines.
    Triggers tiered escalation notifications based on configurable thresholds.
    """
    now = datetime.datetime.utcnow()
    escalated_count = 0

    # Query active CAPAs not yet verified
    query = {
        "verification_status": {"$in": ["PENDING", "IN_PROGRESS", "SUBMITTED"]}
    }
    actions = list(mongo.corrective_actions.find(query))

    for action in actions:
        action_id = str(action["_id"])
        deadline = action.get("deadline")
        if not deadline or not isinstance(deadline, datetime.datetime):
            continue

        assigned_to = action.get("assigned_to")
        current_tier = action.get("escalation_tier", 0)
        hours_diff = (now - deadline).total_seconds() / 3600.0

        new_tier = current_tier

        # Tier 1: Approaching deadline (within 12 hours)
        if -12 <= hours_diff < 0 and current_tier < 1:
            new_tier = 1
            create_notification(
                user_id=assigned_to,
                role="SAFETY_OFFICER",
                title="Reminder: CAPA Deadline Approaching",
                message=f"Action #{action_id[:8]} for violation #{action.get('violation_id', '')[:8]} is due within 12 hours.",
                event_type="corrective_action_deadline",
                entity_type="CORRECTIVE_ACTION",
                entity_id=action_id,
                severity="WARNING"
            )

        # Tier 2: Exceeded deadline (0 to 24 hours overdue)
        elif 0 <= hours_diff < 24 and current_tier < 2:
            new_tier = 2
            create_notification(
                user_id=assigned_to,
                role="SAFETY_OFFICER",
                title="ALERT: Corrective Action Overdue (Tier 1 Escalation)",
                message=f"CAPA #{action_id[:8]} has breached its deadline! Immediate corrective action required.",
                event_type="overdue_action",
                entity_type="CORRECTIVE_ACTION",
                entity_id=action_id,
                severity="HIGH"
            )

        # Tier 3: 24 to 72 hours overdue -> Escalate to Mine Manager
        elif 24 <= hours_diff < 72 and current_tier < 3:
            new_tier = 3
            create_notification(
                user_id=None,
                role="MINE_OFFICER",
                title="ESCALATION (Tier 2): Unresolved Mine Safety Action",
                message=f"CAPA #{action_id[:8]} at mine is {int(hours_diff)}h overdue. Escalated to Mine Management.",
                event_type="escalation",
                entity_type="CORRECTIVE_ACTION",
                entity_id=action_id,
                severity="CRITICAL"
            )

        # Tier 4: > 72 hours overdue -> Escalate to Corporate Management
        elif hours_diff >= 72 and current_tier < 4:
            new_tier = 4
            create_notification(
                user_id=None,
                role="CORPORATE_MANAGEMENT",
                title="CRITICAL ESCALATION (Tier 3): Executive Compliance Breach",
                message=f"CAPA #{action_id[:8]} overdue for >72h. Statutory compliance risk flagged for Corporate board.",
                event_type="escalation",
                entity_type="CORRECTIVE_ACTION",
                entity_id=action_id,
                severity="CRITICAL"
            )

        if new_tier != current_tier:
            mongo.corrective_actions.update_one(
                {"_id": action["_id"]},
                {"$set": {"escalation_tier": new_tier, "last_escalated_at": now}}
            )
            log_audit_event(
                action="ESCALATE",
                entity="CORRECTIVE_ACTION",
                entity_id=action_id,
                old_value={"tier": current_tier},
                new_value={"tier": new_tier},
                notes=f"Overdue by {hours_diff:.1f} hours"
            )
            escalated_count += 1

    return {"processed": len(actions), "escalated": escalated_count}
