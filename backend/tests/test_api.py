import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from fastapi.testclient import TestClient
from core.database import init_global_db, global_db_conn
from core.security import hash_password
from datetime import datetime


class TestAPIRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_global_db()
        from main import app
        cls.client = TestClient(app)

        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM global_admin WHERE username = 'testadmin'")
            password_hash = hash_password("admin123")
            cursor.execute(
                "INSERT INTO global_admin (username, password_hash, create_time) VALUES (?, ?, ?)",
                ("testadmin", password_hash, datetime.now().isoformat())
            )
            conn.commit()

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_admin_page(self):
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)

    def test_admin_login(self):
        response = self.client.post("/api/auth/admin/login", json={
            "username": "testadmin",
            "password": "admin123"
        })
        data = response.json()
        self.assertEqual(data['code'], 200)

    def test_activate_invalid_code(self):
        response = self.client.post("/api/auth/activate", json={
            "auth_code": "invalidcode12345678901234567890"
        })
        data = response.json()
        self.assertNotEqual(data['code'], 200)

    def test_verify_without_auth(self):
        response = self.client.get("/api/auth/verify")
        data = response.json()
        self.assertNotEqual(data['code'], 200)

    def test_models_api(self):
        response = self.client.get("/api/generate/models")
        data = response.json()
        self.assertEqual(data['code'], 200)
        self.assertIn('gpt-image-2', data['data']['models'])
        self.assertIn('supported_sizes', data['data'])

    def test_styles_api(self):
        response = self.client.get("/api/generate/styles")
        data = response.json()
        self.assertEqual(data['code'], 200)


if __name__ == "__main__":
    unittest.main()
