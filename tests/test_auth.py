import unittest
from app import create_app
from app.auth.service import hash_password, verify_password, generate_access_token, decode_access_token


class TestAuthAndSecurity(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        from app.database.seed_data import seed_database
        seed_database()

    def test_password_hashing(self):
        plain = "SecureCoalPassword@2026"
        hashed = hash_password(plain)
        self.assertTrue(verify_password(plain, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    def test_jwt_token_generation_and_decode(self):
        dummy_user = {
            "_id": "64bf00112233445566778899",
            "email": "test.officer@coalgov.in",
            "role": "SAFETY_OFFICER",
            "subsidiary_id": "sub_1",
            "mine_id": "mine_1"
        }
        token = generate_access_token(dummy_user)
        self.assertIsInstance(token, str)

        payload = decode_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["email"], "test.officer@coalgov.in")
        self.assertEqual(payload["role"], "SAFETY_OFFICER")

    def test_login_invalid_credentials(self):
        response = self.client.post("/api/auth/login", json={
            "email": "nonexistent.user@coalgov.in",
            "password": "BadPassword123"
        })
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "INVALID_CREDENTIALS")

    def test_login_valid_demo_super_admin(self):
        # Using seeded demo account
        response = self.client.post("/api/auth/login", json={
            "email": "admin@coalgov.in",
            "password": "Admin@1234"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("token", data["data"])
        self.assertEqual(data["data"]["user"]["role"], "SUPER_ADMIN")


if __name__ == "__main__":
    unittest.main()
