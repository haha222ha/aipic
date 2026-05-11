import threading
import time
from datetime import datetime

from core.database import get_next_task_from_queue, update_task_status
from core.config import WORKER_INTERVAL

_worker_thread = None
_worker_running = False


class GenerateWorker:
    def __init__(self):
        self.running = False
        self.thread = None
        self.current_task = None
        self.current_task_info = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        print("生图Worker已启动")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("生图Worker已停止")

    def get_status(self):
        return {
            "running": self.running,
            "current_task": self.current_task,
        }

    def _worker_loop(self):
        while self.running:
            try:
                task = get_next_task_from_queue()
                if not task:
                    time.sleep(WORKER_INTERVAL)
                    continue

                self.current_task = task['task_id']
                self.current_task_info = task
                update_task_status(task['task_id'], '执行中', execute_time=datetime.now().isoformat())

                result = self._execute_task(task)

                if result['success']:
                    update_task_status(
                        task['task_id'], '已完成',
                        finish_time=datetime.now().isoformat(),
                        output_image_path=result['output_path'],
                        seed=result.get('seed', task.get('seed', -1))
                    )

                    from services.queue_service import save_work_to_user
                    task['output_image_path'] = result['output_path']
                    task['seed'] = result.get('seed', task.get('seed', -1))
                    save_work_to_user(task['user_id'], task)
                else:
                    update_task_status(
                        task['task_id'], '失败',
                        finish_time=datetime.now().isoformat(),
                        fail_reason=result.get('error', '未知错误')
                    )

                    credits_cost = task.get('credits_cost', 0)
                    if credits_cost > 0:
                        from core.database import refund_credits
                        self._safe_refund(task['user_id'], credits_cost, f"生成失败退还：{task.get('prompt', '')[:20]}")

                self.current_task = None
                self.current_task_info = None

            except Exception as e:
                print(f"Worker执行异常: {e}")
                if self.current_task:
                    try:
                        update_task_status(
                            self.current_task, '失败',
                            finish_time=datetime.now().isoformat(),
                            fail_reason=str(e)
                        )
                        if self.current_task_info:
                            credits_cost = self.current_task_info.get('credits_cost', 0)
                            if credits_cost > 0:
                                self._safe_refund(
                                    self.current_task_info['user_id'],
                                    credits_cost,
                                    f"生成异常退还：{self.current_task_info.get('prompt', '')[:20]}"
                                )
                    except Exception as inner_e:
                        print(f"Worker异常处理失败: {inner_e}")
                    self.current_task = None
                    self.current_task_info = None
                time.sleep(WORKER_INTERVAL)

    def _safe_refund(self, user_id: str, credits_cost: int, description: str, max_retries: int = 3):
        from core.database import refund_credits
        for attempt in range(max_retries):
            try:
                result = refund_credits(user_id, credits_cost, description)
                if result >= 0:
                    return
                print(f"积分退还失败(尝试{attempt + 1}/{max_retries}): 用户{user_id}, 积分{credits_cost}, 结果={result}")
            except Exception as e:
                print(f"积分退还异常(尝试{attempt + 1}/{max_retries}): 用户{user_id}, 积分{credits_cost}, 错误={e}")
            time.sleep(1)
        print(f"[严重] 积分退还最终失败: 用户{user_id}, 积分{credits_cost}, 描述={description}")

    def _execute_task(self, task: dict) -> dict:
        from services.generate_service import generate_image

        style_prompt = ""
        if task.get('style_name'):
            from services.style_service import get_style_by_name
            style = get_style_by_name(task['style_name'])
            if style:
                style_prompt = style['style_prompt']

        return generate_image(
            prompt=task['prompt'],
            negative_prompt=task.get('negative_prompt', ''),
            model_name=task.get('model_name', 'gpt-image-2'),
            ratio_key=task.get('ratio_key', 'square'),
            steps=task.get('steps', 20),
            cfg_scale=task.get('cfg_scale', 7.0),
            seed=task.get('seed', -1),
            style_prompt=style_prompt,
            input_image_path=task.get('input_image_path', ''),
            task_type=task.get('task_type', 'text2img'),
            quality_tier=task.get('quality_tier', 'standard'),
        )


_worker_instance = GenerateWorker()


def start_generate_worker():
    _worker_instance.start()


def stop_generate_worker():
    _worker_instance.stop()


def get_worker_status():
    return _worker_instance.get_status()
