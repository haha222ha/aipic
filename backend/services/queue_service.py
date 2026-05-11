from datetime import datetime

from core.database import global_db_conn, get_user_db_conn


def get_queue_stats():
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '待执行'")
        pending = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '执行中'")
        running = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '已完成'")
        completed = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '失败'")
        failed = cursor.fetchone()[0]
    return {"pending": pending, "running": running, "completed": completed, "failed": failed}


def get_user_tasks(user_id: str, status: str = "", page: int = 1, page_size: int = 20):
    offset = (page - 1) * page_size
    with global_db_conn() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT COUNT(*) FROM global_generate_queue WHERE user_id = ? AND task_status = ?",
                (user_id, status)
            )
            total = cursor.fetchone()[0]
            cursor.execute('''
                SELECT task_id, prompt, model_name, width, height, task_type, task_status,
                       submit_time, finish_time, output_image_path, fail_reason
                FROM global_generate_queue WHERE user_id = ? AND task_status = ?
                ORDER BY submit_time DESC LIMIT ? OFFSET ?
            ''', (user_id, status, page_size, offset))
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM global_generate_queue WHERE user_id = ?",
                (user_id,)
            )
            total = cursor.fetchone()[0]
            cursor.execute('''
                SELECT task_id, prompt, model_name, width, height, task_type, task_status,
                       submit_time, finish_time, output_image_path, fail_reason
                FROM global_generate_queue WHERE user_id = ?
                ORDER BY submit_time DESC LIMIT ? OFFSET ?
            ''', (user_id, page_size, offset))
        tasks = [dict(row) for row in cursor.fetchall()]
    return {"total": total, "tasks": tasks}


def cancel_task(user_id: str, task_id: str):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT task_status FROM global_generate_queue WHERE task_id = ? AND user_id = ?",
            (task_id, user_id)
        )
        row = cursor.fetchone()
        if not row:
            return False, "任务不存在"
        if row['task_status'] != '待执行':
            return False, "只能取消待执行的任务"
        cursor.execute(
            "UPDATE global_generate_queue SET task_status = '已取消' WHERE task_id = ?",
            (task_id,)
        )
        conn.commit()
    return True, "取消成功"


def save_work_to_user(user_id: str, task_data: dict):
    with get_user_db_conn(user_id) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO user_works
            (task_id, prompt, negative_prompt, model_name, width, height, steps, cfg_scale, seed,
             style_name, task_type, input_image_path, output_image_path, create_time, quality_tier, credits_cost, ratio_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_data['task_id'], task_data['prompt'], task_data.get('negative_prompt', ''),
            task_data['model_name'], task_data['width'], task_data['height'],
            task_data['steps'], task_data['cfg_scale'], task_data['seed'],
            task_data.get('style_name', ''), task_data['task_type'],
            task_data.get('input_image_path', ''), task_data.get('output_image_path', ''),
            datetime.now().isoformat(),
            task_data.get('quality_tier', 'standard'),
            task_data.get('credits_cost', 1),
            task_data.get('ratio_key', 'square')
        ))
        conn.commit()
