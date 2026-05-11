import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import init_global_db, global_db_conn
from core.auth import create_auth_code
from datetime import datetime


def batch_generate_codes(package_type: str, count: int, valid_days: int):
    init_global_db()

    codes = []
    with global_db_conn() as conn:
        cursor = conn.cursor()
        for _ in range(count):
            code = create_auth_code()
            cursor.execute('''
                INSERT INTO global_auth_codes (auth_code, package_type, valid_days, status, create_time)
                VALUES (?, ?, ?, '未激活', ?)
            ''', (code, package_type, valid_days, datetime.now().isoformat()))
            codes.append(code)
        conn.commit()

    print(f"成功生成 {count} 个 {package_type} 授权码（有效期 {valid_days} 天）:")
    for code in codes:
        print(code)

    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'codes_output.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        for code in codes:
            f.write(f"{code}\n")
    print(f"\n授权码已保存到: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python batch_codes.py <套餐类型> <数量> <有效天数>")
        print("套餐类型: 免费版, 基础版, 专业版, 旗舰版")
        sys.exit(1)

    package_type = sys.argv[1]
    count = int(sys.argv[2])
    valid_days = int(sys.argv[3])

    if package_type not in ['免费版', '基础版', '专业版', '旗舰版']:
        print("无效的套餐类型")
        sys.exit(1)

    batch_generate_codes(package_type, count, valid_days)
