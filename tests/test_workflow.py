import io
import unittest
import json
from app import create_app
from app.database.seed_data import seed_database


class TestEndToEndGovernanceWorkflow(unittest.TestCase):
    """
    Primary Acceptance Integration Test covering the 20-step lifecycle:
    Login -> Mine Selection -> Start Inspection -> Evidence Upload ->
    AI Detection -> Rule Evaluation -> Violation Creation -> Auto-Assignment ->
    Notification Dispatch -> CAPA Submission -> Verification -> Closure ->
    Audit Trail -> Dashboard & GIS Update.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        seed_database()

    def test_complete_primary_acceptance_scenario(self):
        # 1. Officer Logs In
        login_res = self.client.post("/api/auth/login", json={
            "email": "safety.officer@coalgov.in",
            "password": "Safety@1234"
        })
        self.assertEqual(login_res.status_code, 200)
        auth_data = login_res.get_json()["data"]
        token = auth_data["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Officer Selects a Mine
        mines_res = self.client.get("/api/mines", headers=headers)
        self.assertEqual(mines_res.status_code, 200)
        mines = mines_res.get_json()["data"]
        self.assertGreater(len(mines), 0)
        mine_id = mines[0]["_id"]

        # 3. Officer Starts an Inspection
        insp_res = self.client.post("/api/inspections", headers=headers, json={
            "mine_id": mine_id,
            "inspection_type": "ROUTINE_SAFETY",
            "location": "Pit 1 Operational Face",
            "latitude": 25.0485,
            "longitude": 87.3785
        })
        self.assertEqual(insp_res.status_code, 201)
        insp_id = insp_res.get_json()["data"]["_id"]

        start_res = self.client.post(f"/api/inspections/{insp_id}/start", headers=headers)
        self.assertEqual(start_res.status_code, 200)
        self.assertEqual(start_res.get_json()["data"]["status"], "IN_PROGRESS")

        # 4 & 5 & 6. AI Analyzes Evidence, Detects Violation, Evaluates Rule Engine & Creates Violation
        import cv2
        import numpy as np
        blank_img = np.zeros((200, 200, 3), dtype=np.uint8)
        _, enc_img = cv2.imencode('.jpg', blank_img)
        dummy_img = (io.BytesIO(enc_img.tobytes()), "field_evidence.jpg")
        detect_res = self.client.post(
            "/api/ai/image-detect",
            headers=headers,
            data={
                "image": dummy_img,
                "mine_id": mine_id,
                "auto_create_violation": "true"
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(detect_res.status_code, 200)
        detect_data = detect_res.get_json()["data"]
        self.assertGreater(detect_data["violations_detected"], 0)

        # 7 & 8 & 9. Violation Created with GPS, Timestamp, and Auto-Assignment
        dispatched = detect_data.get("dispatched_violations", [])
        self.assertGreater(len(dispatched), 0)
        violation = dispatched[0]
        violation_id = violation["_id"]
        self.assertEqual(violation["mine_id"], mine_id)
        self.assertIsNotNone(violation.get("latitude"))
        self.assertIsNotNone(violation.get("assigned_to"))

        # 10. In-App Notification Generated
        notif_res = self.client.get("/api/notifications", headers=headers)
        self.assertEqual(notif_res.status_code, 200)
        notifications = notif_res.get_json()["data"]
        self.assertGreater(len(notifications), 0)

        # 11. Corrective Action (CAPA) Created
        capa_res = self.client.get(f"/api/corrective-actions?assigned_to={auth_data['user']['_id']}", headers=headers)
        self.assertEqual(capa_res.status_code, 200)
        capas = capa_res.get_json()["data"]
        matching_capa = next((c for c in capas if c.get("violation_id") == violation_id), None)
        self.assertIsNotNone(matching_capa)
        capa_id = matching_capa["_id"]

        # 12. Officer Submits Corrective Evidence
        submit_capa_res = self.client.post(f"/api/corrective-actions/{capa_id}/submit-evidence", headers=headers, json={
            "notes": "Safety helmets distributed to all workers on bench. Signed briefing register attached.",
            "evidence": ["/api/documents/file/evidence/rectification_proof.jpg"]
        })
        self.assertEqual(submit_capa_res.status_code, 200)
        self.assertEqual(submit_capa_res.get_json()["data"]["verification_status"], "SUBMITTED")

        # 13. Authorized Safety Officer Verifies It
        verify_res = self.client.post(f"/api/corrective-actions/{capa_id}/verify", headers=headers, json={
            "status": "VERIFIED",
            "remarks": "On-site physical verification completed. Full PPE compliance observed."
        })
        self.assertEqual(verify_res.status_code, 200)
        self.assertEqual(verify_res.get_json()["data"]["verification_status"], "VERIFIED")

        # 14. Violation is Closed
        close_res = self.client.post(f"/api/violations/{violation_id}/close", headers=headers, json={
            "closure_notes": "Statutory verified closure following successful CAPA implementation."
        })
        self.assertEqual(close_res.status_code, 200)
        self.assertEqual(close_res.get_json()["data"]["status"], "CLOSED")

        # 15. Audit Trail Recorded Important Actions
        audit_res = self.client.get(f"/api/audit-logs?entity=VIOLATION&entity_id={violation_id}", headers=headers)
        self.assertEqual(audit_res.status_code, 200)
        audit_logs = audit_res.get_json()["data"]
        actions = [a["action"] for a in audit_logs]
        self.assertIn("CREATE", actions)
        self.assertIn("CLOSE", actions)

        # 16. Dashboard & Risk Analytics Reflect Updated Event
        dash_res = self.client.get(f"/api/analytics/dashboard?mine_id={mine_id}", headers=headers)
        self.assertEqual(dash_res.status_code, 200)
        dash_data = dash_res.get_json()["data"]
        self.assertIn("risk_summary", dash_data)
        self.assertIn("compliance", dash_data)

        # 17. GIS Displays the Location
        gis_res = self.client.get(f"/api/gis/features?mine_id={mine_id}", headers=headers)
        self.assertEqual(gis_res.status_code, 200)
        gis_data = gis_res.get_json()["data"]
        self.assertIn("mines", gis_data)
        self.assertIn("violations", gis_data)


if __name__ == "__main__":
    unittest.main()
