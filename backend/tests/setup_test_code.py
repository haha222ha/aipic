import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.database import init_global_db, global_db_conn
from datetime import datetime

init_global_db()

TEST_CODE = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"

with global_db_conn() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM global_auth_codes WHERE auth_code = ?", (TEST_CODE,))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO global_auth_codes (auth_code, package_type, valid_days, credits, status, create_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (TEST_CODE, '专业版', 30, 50, '未激活', datetime.now().isoformat()))
        conn.commit()
        print(f"✅ 测试授权码已创建: {TEST_CODE}")
    else:
        print(f"⚠️ 测试授权码已存在: {TEST_CODE}")
    
    cursor.execute("SELECT auth_code, package_type, credits, status FROM global_auth_codes WHERE auth_code = ?", (TEST_CODE,))
    row = cursor.fetchone()
    print(f"授权码信息: {dict(row)}")
