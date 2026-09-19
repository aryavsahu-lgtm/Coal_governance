import io
import unittest
import datetime
from app import create_app
from app.database.mongo import mongo
from app.ai.ocr_engine import run_ocr_on_file
from app.workflow.rule_engine import evaluate_document_compliance
from app.rag.chatbot import generate_rag_response
from app.rag.document_context import is_document_query, retrieve_document_context


class TestDocumentRAGAndRules(unittest.TestCase):
    """Test suite for OCR document processing, Rule Engine checks, and RAG contract/SOP querying."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_document_query_intent(self):
        """Verify queries asking about contracts, agreements, and SOPs are classified as document queries."""
        self.assertTrue(is_document_query("Check contract details for ABC Earthmovers"))
        self.assertTrue(is_document_query("What are the penalty clauses in the contractor agreement?"))
        self.assertTrue(is_document_query("What does SOP-04 say about haul road speed limits & berm height?"))
        self.assertTrue(is_document_query("What are the emergency evacuation procedures in the mine SOP?"))

        # Pure law or pure general greetings are not document queries
        self.assertFalse(is_document_query("Hello assistant"))

    def test_02_rule_engine_document_compliance(self):
        """Verify the rule engine triggers on expired documents and contracts missing safety clauses."""
        now = datetime.datetime.utcnow()

        # Non-compliant contract missing safety clauses
        bad_contract = {
            "_id": "dummy_bad_contract",
            "document_type": "CONTRACTOR_AGREEMENT",
            "mine_id": "test_mine",
            "extracted_text": "Generic invoice for civil excavation work. No terms attached.",
            "status": "ACTIVE",
            "expiry_date": now + datetime.timedelta(days=100)
        }
        triggered = evaluate_document_compliance(bad_contract)
        rule_ids = [r["rule_id"] for r in triggered]
        self.assertIn("RULE_CONTRACT_SAFETY_CLAUSE", rule_ids)

        # Compliant contract with safety clauses
        good_contract = {
            "_id": "dummy_good_contract",
            "document_type": "CONTRACTOR_AGREEMENT",
            "mine_id": "test_mine",
            "extracted_text": "Contractor shall provide mandatory PPE, insurance, and follow DGMS safety rules.",
            "status": "ACTIVE",
            "expiry_date": now + datetime.timedelta(days=100)
        }
        triggered_good = evaluate_document_compliance(good_contract)
        good_rule_ids = [r["rule_id"] for r in triggered_good]
        self.assertNotIn("RULE_CONTRACT_SAFETY_CLAUSE", good_rule_ids)

        # Expired document triggers RULE_DOC_EXPIRED
        expired_doc = {
            "_id": "dummy_expired_doc",
            "document_type": "DGMS_CLEARANCE",
            "mine_id": "test_mine",
            "extracted_text": "DGMS statutory clearance",
            "status": "EXPIRED",
            "expiry_date": now - datetime.timedelta(days=10)
        }
        triggered_exp = evaluate_document_compliance(expired_doc)
        exp_rule_ids = [r["rule_id"] for r in triggered_exp]
        self.assertIn("RULE_DOC_EXPIRED", exp_rule_ids)

    def test_03_rag_contract_details_query(self):
        """Verify asking the chatbot about ABC Earthmovers contract returns exact OCR-extracted terms."""
        result = generate_rag_response("Check contract details for ABC Earthmovers")

        self.assertIn("response", result)
        resp = result["response"]

        # Assert contract parameters are extracted from seeded OCR document
        self.assertIn("ABC Earthmovers", resp)
        self.assertIn("CON-AGR-ECL-2026-088", resp)
        self.assertIn("14.50 Crores", resp)
        self.assertIn("85 Personnel", resp)
        self.assertIn("50,000", resp)  # Penalty clause
        self.assertIn("15 Lakhs", resp)  # Insurance clause

        # Assert document citation
        citations = [c["regulation"] for c in result["citations"]]
        self.assertTrue(any("ABC_Earthmovers_Mining_Contract_2026.pdf" in c for c in citations))

    def test_04_rag_sop_haul_road_query(self):
        """Verify asking the chatbot about SOP-04 returns speed limits, berm dimensions, and safety rules."""
        result = generate_rag_response("What does SOP-04 say about haul road speed limits & berm height?")

        self.assertIn("response", result)
        resp = result["response"]

        # Assert SOP parameters are extracted from seeded OCR document
        self.assertIn("SOP-RJM-2026-04", resp)
        self.assertIn("20 km/h", resp)  # Speed limit ramp
        self.assertIn("30 km/h", resp)  # Speed limit corridor
        self.assertIn("2.5 meters", resp)  # Berm height
        self.assertIn("45 degrees", resp)  # Slope angle
        self.assertIn("Muster Station Alpha", resp)  # Emergency evacuation

        # Assert document citation
        citations = [c["regulation"] for c in result["citations"]]
        self.assertTrue(any("SOP_04_Haul_Road_and_Slope_Stability.pdf" in c for c in citations))

    def test_05_document_upload_and_ocr_flow(self):
        """Verify document upload endpoint runs OCR, rule engine, and creates a document record."""
        # 1. Login as Safety Officer to obtain JWT token
        login_res = self.client.post("/api/auth/login", json={
            "email": "safety.officer@coalgov.in",
            "password": "Safety@1234"
        })
        self.assertEqual(login_res.status_code, 200)
        token = login_res.get_json()["data"]["token"]

        # Get primary mine id
        mine = mongo.mines.find_one()
        mine_id = str(mine["_id"])

        # 2. Upload sample SOP text file
        sop_content = (
            "MINE STANDARD OPERATING PROCEDURE (SOP)\n"
            "SOP Number: SOP-TEST-2026-99\n"
            "Title: Test Blast Safety SOP\n"
            "Date of Issue: 01/01/2026\n"
            "Valid Till / Expiry Date: 31/12/2026\n"
            "All workers must evacuate to Muster Station Gamma upon siren alert."
        )

        data = {
            "mine_id": mine_id,
            "document_type": "MINE_SOP",
            "document_number": "SOP-TEST-2026-99",
            "file": (io.BytesIO(sop_content.encode("utf-8")), "Test_Blast_SOP.txt")
        }

        upload_res = self.client.post(
            "/api/documents/upload",
            data=data,
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {token}"}
        )

        self.assertEqual(upload_res.status_code, 201)
        res_json = upload_res.get_json()
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["data"]["document_type"], "MINE_SOP")
        self.assertIn("Muster Station Gamma", res_json["data"]["extracted_text"])


if __name__ == "__main__":
    unittest.main()
