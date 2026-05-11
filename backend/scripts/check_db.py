import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import init_global_db, global_db_conn, get_user_db


def check_database():
    init_global_db()

    print("=" * 50)
    print("  AI智能作图系统 - 数据库检查")
    print("=" * 50)

    with global_db_conn() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM global_user_info")
        user_count = cursor.fetchone()[0]
        print(f"\n用户总数: {user_count}")

        cursor.execute("SELECT COUNT(*) FROM global_user_info WHERE status = '正常'")
        active_count = cursor.fetchone()[0]
        print(f"活跃用户: {active_count}")

        cursor.execute("SELECT COUNT(*) FROM global_auth_codes")
        code_count = cursor.fetchone()[0]
        print(f"\n授权码总数: {code_count}")

        cursor.execute("SELECT COUNT(*) FROM global_auth_codes WHERE status = '未激活'")
        unused_count = cursor.fetchone()[0]
        print(f"未使用授权码: {unused_count}")

        cursor.execute("SELECT COUNT(*) FROM global_generate_queue")
        task_count = cursor.fetchone()[0]
        print(f"\n任务总数: {task_count}")

        cursor.execute("SELECT task_status, COUNT(*) FROM global_generate_queue GROUP BY task_status")
        status_counts = cursor.fetchall()
        for row in status_counts:
            print(f"  {row[0]}: {row[1]}")

        cursor.execute("SELECT COUNT(*) FROM global_admin")
        admin_count = cursor.fetchone()[0]
        print(f"\n管理员数量: {admin_count}")

        cursor.execute("SELECT COUNT(*) FROM global_style_library")
        style_count = cursor.fetchone()[0]
        print(f"风格数量: {style_count}")

        cursor.execute("SELECT COUNT(*) FROM global_operation_log")
        log_count = cursor.fetchone()[0]
        print(f"操作日志: {log_count}")

    print("\n" + "=" * 50)
    print("  数据库检查完成")
    print("=" * 50)


if __name__ == "__main__":
    check_database()
