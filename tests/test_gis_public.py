import unittest
from app import create_app
from app.database.seed_data import seed_database
from app.auth.service import authenticate_user, generate_access_token


class TestGISPublicAccess(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        seed_database()

    def test_gis_features_public_access_no_token(self):
        """Verify unauthenticated/guest users can fetch GIS layers without 401 redirect."""
        res = self.client.get("/api/gis/features")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("mines", data["data"])
        self.assertIn("zones", data["data"])
        self.assertIn("violations", data["data"])
        self.assertIn("incidents", data["data"])
        self.assertIn("field_reports", data["data"])
        self.assertGreater(len(data["data"]["mines"]["features"]), 0)

    def test_gis_features_authenticated_access(self):
        """Verify authenticated officer can fetch GIS layers with valid token."""
        user = authenticate_user("safety.officer@coalgov.in", "Safety@1234")
        self.assertIsNotNone(user)
        token = generate_access_token(user)

        res = self.client.get(
            "/api/gis/features",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

    def test_public_mines_and_violations_no_token(self):
        """Verify /api/mines and /api/violations allow public access without 401."""
        res_mines = self.client.get("/api/mines")
        self.assertEqual(res_mines.status_code, 200)
        m_data = res_mines.get_json()
        self.assertTrue(m_data.get("success"))
        self.assertGreater(len(m_data["data"]), 0)

        res_v = self.client.get("/api/violations")
        self.assertEqual(res_v.status_code, 200)
        v_data = res_v.get_json()
        self.assertTrue(v_data.get("success"))

    def test_public_documents_and_chat_no_token(self):
        """Verify /api/documents and /api/chat allow public access without 401."""
        res_docs = self.client.get("/api/documents")
        self.assertEqual(res_docs.status_code, 200)
        d_data = res_docs.get_json()
        self.assertTrue(d_data.get("success"))

        res_chat = self.client.post("/api/chat", json={"message": "What are safety rules for mines?"})
        self.assertEqual(res_chat.status_code, 200)
        c_data = res_chat.get_json()
        self.assertTrue(c_data.get("success"))


if __name__ == "__main__":
    unittest.main()
