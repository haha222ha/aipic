import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import init_global_db, global_db_conn
from core.security import hash_password
from datetime import datetime


def create_admin(username: str, password: str):
    init_global_db()

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM global_admin WHERE username = ?", (username,))
        if cursor.fetchone():
            password_hash = hash_password(password)
            cursor.execute(
                "UPDATE global_admin SET password_hash = ? WHERE username = ?",
                (password_hash, username),
            )
            conn.commit()
            print(f"管理员 '{username}' 密码已重置")
            return

        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO global_admin (username, password_hash, create_time)
            VALUES (?, ?, ?)
        ''', (username, password_hash, datetime.now().isoformat()))
        conn.commit()

    print(f"管理员 '{username}' 创建成功")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python create_admin.py <用户名> <密码>")
        sys.exit(1)

    create_admin(sys.argv[1], sys.argv[2])
