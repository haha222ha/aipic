import os
import threading
import time
from datetime import datetime, timedelta

from core.config import TEMP_DIR, TEMP_FILE_MAX_AGE_HOURS, CLEANUP_INTERVAL_SECONDS
from core.database import global_db_conn, refund_credits

STUCK_TASK_TIMEOUT_MINUTES = 10

_cleanup_thread = None
_cleanup_running = False


class CleanupWorker:
    def __init__(self):
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.thread.start()
        print("清理Worker已启动")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("清理Worker已停止")

    def _cleanup_loop(self):
        while self.running:
            try:
                self._cleanup_temp_files()
                self._cleanup_stuck_tasks()
            except Exception as e:
                print(f"清理异常: {e}")
            time.sleep(CLEANUP_INTERVAL_SECONDS)

    def _cleanup_temp_files(self):
        cutoff = datetime.now() - timedelta(hours=TEMP_FILE_MAX_AGE_HOURS)
        cleaned = 0

        for dir_path in [TEMP_DIR]:
            if not os.path.exists(dir_path):
                continue
            for filename in os.listdir(dir_path):
                filepath = os.path.join(dir_path, filename)
                if not os.path.isfile(filepath):
                    continue
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < cutoff:
                        os.remove(filepath)
                        cleaned += 1
                except Exception:
                    pass

        if cleaned > 0:
            print(f"清理了 {cleaned} 个过期临时文件")

    def _cleanup_stuck_tasks(self):
        cutoff = (datetime.now() - timedelta(minutes=STUCK_TASK_TIMEOUT_MINUTES)).isoformat()
        refunded = 0

        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, task_id, user_id, credits_cost, prompt
                FROM global_generate_queue
                WHERE task_status = '执行中' AND submit_time < ?
            ''', (cutoff,))
            stuck_tasks = cursor.fetchall()

            for task in stuck_tasks:
                task_dict = dict(task)
                try:
                    cursor.execute('''
                        UPDATE global_generate_queue
                        SET task_status = '失败', fail_reason = '任务超时自动关闭', finish_time = ?
                        WHERE task_id = ?
                    ''', (datetime.now().isoformat(), task_dict['task_id']))

                    credits_cost = task_dict.get('credits_cost', 0)
                    if credits_cost > 0:
                        refund_credits(
                            task_dict['user_id'],
                            credits_cost,
                            f"任务超时退还：{task_dict.get('prompt', '')[:20]}"
                        )
                    refunded += 1
                except Exception as e:
                    print(f"退还超时任务失败 {task_dict['task_id']}: {e}")

            conn.commit()

        if refunded > 0:
            print(f"清理了 {refunded} 个超时任务并退还积分")


_cleanup_instance = CleanupWorker()


def start_cleanup_worker():
    _cleanup_instance.start()


def stop_cleanup_worker():
    _cleanup_instance.stop()
