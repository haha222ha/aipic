import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from core.database import init_global_db, global_db_conn
from core.security import hash_password
from core.config import OPENAI_API_KEY
from datetime import datetime


class TestAuthCode(unittest.TestCase):
    def test_create_auth_code_hex(self):
        from core.auth import create_auth_code
        code = create_auth_code()
        self.assertEqual(len(code), 32)
        int(code, 16)

    def test_create_auth_code_length(self):
        from core.auth import create_auth_code
        for _ in range(10):
            code = create_auth_code()
            self.assertEqual(len(code), 32)

    def test_create_auth_code_unique(self):
        from core.auth import create_auth_code
        codes = set(create_auth_code() for _ in range(100))
        self.assertEqual(len(codes), 100)


class TestSecurity(unittest.TestCase):
    def test_hash_password(self):
        from core.security import hash_password, verify_password
        hashed = hash_password("test123")
        self.assertTrue(verify_password("test123", hashed))

    def test_wrong_password(self):
        from core.security import hash_password, verify_password
        hashed = hash_password("test123")
        self.assertFalse(verify_password("wrong", hashed))


class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_global_db()

    def test_global_db_connection(self):
        from core.database import global_db_conn
        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM global_config")
            count = cursor.fetchone()[0]
            self.assertGreaterEqual(count, 0)

    def test_config_table(self):
        from core.database import global_db_conn
        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT default_model FROM global_config WHERE id = 1")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row['default_model'], 'gpt-image-2')


if __name__ == "__main__":
    unittest.main()
