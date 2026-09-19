import unittest
from app import create_app
from app.workflow.rule_engine import evaluate_rules, seed_default_rules


class TestRuleEngine(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        seed_default_rules()

    def test_missing_helmet_triggers_ppe_rule(self):
        event = {
            "missing_helmet": True,
            "zone": "Pit Operational Area"
        }
        triggered = evaluate_rules(event)
        rule_ids = [r["rule_id"] for r in triggered]
        self.assertIn("RULE_PPE_HELMET_VEST", rule_ids)

    def test_restricted_zone_breach_triggers_critical_rule(self):
        event = {
            "unauthorized_zone_entry": True
        }
        triggered = evaluate_rules(event)
        rule_ids = [r["rule_id"] for r in triggered]
        self.assertIn("RULE_RESTRICTED_ZONE_ENTRY", rule_ids)
        rule = next(r for r in triggered if r["rule_id"] == "RULE_RESTRICTED_ZONE_ENTRY")
        self.assertEqual(rule["severity"], "CRITICAL")

    def test_expired_document_triggers_compliance_rule(self):
        event = {
            "document_expired": True
        }
        triggered = evaluate_rules(event)
        rule_ids = [r["rule_id"] for r in triggered]
        self.assertIn("RULE_DOC_EXPIRED", rule_ids)


if __name__ == "__main__":
    unittest.main()
