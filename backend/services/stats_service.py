from datetime import datetime

from core.database import global_db_conn


def get_global_stats():
    with global_db_conn() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM global_user_info")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM global_user_info WHERE status = '正常'")
        active_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '已完成'")
        total_generated = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*) FROM global_generate_queue
            WHERE task_status = '已完成' AND date(finish_time) = date('now')
        ''')
        today_generated = cursor.fetchone()[0]

        cursor.execute('''
            SELECT package_type, COUNT(*) as count FROM global_user_info
            WHERE status = '正常' GROUP BY package_type
        ''')
        package_dist = {row['package_type']: row['count'] for row in cursor.fetchall()}

        cursor.execute('''
            SELECT model_name, COUNT(*) as count FROM global_generate_queue
            WHERE task_status = '已完成' GROUP BY model_name ORDER BY count DESC
        ''')
        model_usage = {row['model_name']: row['count'] for row in cursor.fetchall()}

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_generated": total_generated,
        "today_generated": today_generated,
        "package_distribution": package_dist,
        "model_usage": model_usage,
    }


def get_user_stats(user_id: str):
    with global_db_conn() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT today_generated_count, daily_generate_limit, last_reset_date FROM global_user_info WHERE user_id = ?",
            (user_id,)
        )
        user_row = cursor.fetchone()
        if not user_row:
            return None

        cursor.execute(
            "SELECT COUNT(*) FROM global_generate_queue WHERE user_id = ? AND task_status = '已完成'",
            (user_id,)
        )
        total_generated = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*) FROM global_generate_queue
            WHERE user_id = ? AND task_status = '已完成' AND date(finish_time) = date('now')
        ''', (user_id,))
        today_generated = cursor.fetchone()[0]

        cursor.execute('''
            SELECT model_name, COUNT(*) as count FROM global_generate_queue
            WHERE user_id = ? AND task_status = '已完成' GROUP BY model_name
        ''', (user_id,))
        model_usage = {row['model_name']: row['count'] for row in cursor.fetchall()}

    return {
        "total_generated": total_generated,
        "today_generated": today_generated,
        "daily_limit": user_row['daily_generate_limit'],
        "remaining_today": max(0, user_row['daily_generate_limit'] - today_generated),
        "model_usage": model_usage,
    }


def generate_daily_summary():
    today = datetime.now().strftime('%Y-%m-%d')
    with global_db_conn() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM global_user_info WHERE status = '正常'")
        total_users = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) FROM global_generate_queue
            WHERE task_status = '已完成' AND date(finish_time) = date('now')
        ''')
        active_users = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*) FROM global_generate_queue
            WHERE task_status = '已完成' AND date(finish_time) = date('now')
        ''')
        total_generated = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM global_user_info WHERE package_type = '免费版' AND status = '正常'")
        free_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM global_user_info WHERE package_type = '基础版' AND status = '正常'")
        basic_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM global_user_info WHERE package_type = '专业版' AND status = '正常'")
        pro_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM global_user_info WHERE package_type = '旗舰版' AND status = '正常'")
        flagship_count = cursor.fetchone()[0]

        try:
            cursor.execute('''
                INSERT INTO global_daily_summary
                (summary_date, total_users, total_generated, active_users, free_count, basic_count, pro_count, flagship_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (today, total_users, total_generated, active_users, free_count, basic_count, pro_count, flagship_count))
        except Exception:
            cursor.execute('''
                UPDATE global_daily_summary SET
                total_users = ?, total_generated = ?, active_users = ?,
                free_count = ?, basic_count = ?, pro_count = ?, flagship_count = ?
                WHERE summary_date = ?
            ''', (total_users, total_generated, active_users, free_count, basic_count, pro_count, flagship_count, today))
        conn.commit()
