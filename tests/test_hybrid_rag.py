import unittest
from app import create_app
from app.database.mongo import mongo
from app.rag.chatbot import generate_rag_response
from app.rag.operational_context import is_operational_query, get_mines_violation_analytics


class TestHybridRAG(unittest.TestCase):
    """Test suite for Hybrid Operational and Statutory RAG Assistant."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_operational_intent_detection(self):
        """Verify queries asking about live database metrics are classified as operational."""
        self.assertTrue(is_operational_query("which mine has more violation"))
        self.assertTrue(is_operational_query("which mine has the most violations"))
        self.assertTrue(is_operational_query("compare violations across all mines"))
        self.assertTrue(is_operational_query("which contractor has highest risk"))
        self.assertTrue(is_operational_query("how many open capas"))
        self.assertTrue(is_operational_query("violations in Rajmahal"))

        # Strictly legal questions should NOT trigger as operational
        self.assertFalse(is_operational_query("What is CMR 2017 Regulation 191?"))
        self.assertFalse(is_operational_query("What does Section 23 of the Mines Act 1952 state?"))

    def test_02_which_mine_has_more_violation(self):
        """Verify asking 'which mine has more violation' returns Rajmahal and full breakdown."""
        result = generate_rag_response("which mine has more violation")

        self.assertIn("response", result)
        self.assertIn("citations", result)

        response_text = result["response"]

        # Must name Rajmahal as having the most violations
        self.assertIn("Rajmahal Open Cast Project", response_text)
        self.assertIn("most violations", response_text)
        self.assertIn("4", response_text)  # 4 recorded violations in Rajmahal

        # Must include citation to live database
        citations = [c["regulation"] for c in result["citations"]]
        self.assertTrue(any("Live Operational Database" in c for c in citations))

    def test_03_contractor_risk_query(self):
        """Verify asking about contractor risk queries live contractors."""
        result = generate_rag_response("which contractor has highest risk?")

        self.assertIn("response", result)
        response_text = result["response"]
        self.assertIn("Contractor Safety & Risk", response_text)
        self.assertIn("ABC Earthmovers", response_text)

    def test_04_statutory_cmr_query(self):
        """Verify strictly statutory queries return CMR legal articles without hallucination."""
        result = generate_rag_response("What are the mandatory PPE requirements under CMR Regulation 191?")

        response_text = result["response"]
        self.assertIn("CMR 2017 Reg. 191", response_text)
        self.assertIn("Protective Footwear and Helmets", response_text)

        citations = [c["regulation"] for c in result["citations"]]
        self.assertIn("CMR 2017 Reg. 191", citations)

    def test_05_hybrid_query(self):
        """Verify a hybrid query returns both live operational metrics and statutory rules."""
        query = "Which mine has more violations and what does CMR 191 mandate for PPE?"
        result = generate_rag_response(query)

        response_text = result["response"]
        citations = [c["regulation"] for c in result["citations"]]

        # Both operational and statutory content present
        self.assertIn("Rajmahal Open Cast Project", response_text)
        self.assertIn("CMR 2017 Reg. 191", response_text)

        # Both operational and statutory citations present
        self.assertTrue(any("Live Operational Database" in c for c in citations))
        self.assertTrue(any("CMR 2017 Reg. 191" in c for c in citations))


if __name__ == "__main__":
    unittest.main()
