import uuid
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from core.security import get_current_user, rate_limit, check_user_action_limit, filter_prompt
from core.database import (
    global_db_conn, check_daily_quota, get_user_credits,
    deduct_credits, refund_credits, increment_daily_count,
)
from core.config import (
    SUPPORTED_MODELS, DEFAULT_MODEL, OPENAI_SUPPORTED_SIZES,
    PACKAGES, QUALITY_TIERS, CREDIT_PACKAGES, PRESET_RATIOS, MAX_QUEUE_SIZE,
)

router = APIRouter(prefix="/api/generate", tags=["生图模块"])


def _get_quality_tier(quality: str, user_package: str) -> tuple:
    quality_order = {'standard': 0, 'hd': 1, 'ultra': 2, 'master': 3}
    pkg = PACKAGES.get(user_package, PACKAGES['免费版'])
    max_quality = pkg.get('max_quality', 'standard')
    if quality_order.get(quality, 0) > quality_order.get(max_quality, 0):
        quality = max_quality
    tier = QUALITY_TIERS.get(quality, QUALITY_TIERS['standard'])
    if not tier.get('available', True):
        quality = 'ultra'
        tier = QUALITY_TIERS['ultra']
    return quality, tier


@router.post("/text2img")
@rate_limit(limit=10, time_window=60)
async def text2img(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    prompt = data.get('prompt', '').strip()
    negative_prompt = data.get('negative_prompt', '').strip()
    model_name = data.get('model', DEFAULT_MODEL)
    ratio_key = data.get('ratio', 'square')
    steps = data.get('steps', 20)
    cfg_scale = data.get('cfg_scale', 7.0)
    seed = data.get('seed', -1)
    style_name = data.get('style', '')
    quality = data.get('quality', 'standard')

    if not prompt:
        return {"code": 400, "msg": "请输入提示词", "data": None}

    if len(prompt) > 2000:
        return {"code": 400, "msg": "提示词过长，最多2000字符", "data": None}

    passed, filter_msg = filter_prompt(prompt)
    if not passed:
        return {"code": 400, "msg": filter_msg, "data": None}

    user_id = current_user['user_id']

    allowed, action_msg = check_user_action_limit(user_id, 'generate')
    if not allowed:
        return {"code": 429, "msg": action_msg, "data": None}

    quality, quality_tier = _get_quality_tier(quality, current_user['package_type'])
    credits_cost = quality_tier['credits_per_image']

    user_credits = get_user_credits(user_id)
    if user_credits < credits_cost:
        return {"code": 403, "msg": f"积分不足，当前{user_credits}积分，需要{credits_cost}积分", "data": None}

    if ratio_key not in PRESET_RATIOS:
        ratio_key = 'square'

    if model_name not in SUPPORTED_MODELS:
        model_name = DEFAULT_MODEL

    ratio_info = PRESET_RATIOS[ratio_key]
    size_str = ratio_info['sizes'].get(quality, ratio_info['sizes']['standard'])

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '待执行'")
        queue_count = cursor.fetchone()[0]
        if queue_count >= MAX_QUEUE_SIZE:
            return {"code": 429, "msg": "队列已满，请稍后再试", "data": None}

    if not deduct_credits(user_id, credits_cost, f"文生图 {quality} {ratio_info['label']}"):
        return {"code": 403, "msg": "积分扣费失败", "data": None}

    increment_daily_count(user_id)

    task_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(queue_order) FROM global_generate_queue WHERE task_status = '待执行'")
        max_order = cursor.fetchone()[0]
        queue_order = (max_order or 0) + 1

        cursor.execute('''
            INSERT INTO global_generate_queue
            (user_id, task_id, prompt, negative_prompt, model_name, width, height, steps, cfg_scale, seed, style_name, task_type, quality_tier, credits_cost, submit_time, task_status, queue_order, package_type, ratio_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'text2img', ?, ?, ?, '待执行', ?, ?, ?)
        ''', (user_id, task_id, prompt, negative_prompt, model_name, 0, 0, steps, cfg_scale, seed, style_name, quality, credits_cost, now, queue_order, current_user['package_type'], ratio_key))
        conn.commit()

    return {
        "code": 200,
        "msg": "任务已提交",
        "data": {
            "task_id": task_id,
            "status": "待执行",
            "queue_position": int(queue_order),
            "credits_cost": credits_cost,
            "quality": quality,
            "ratio": ratio_key,
            "ratio_label": ratio_info['label'],
            "remaining_credits": get_user_credits(user_id),
        }
    }


@router.post("/img2img")
@rate_limit(limit=10, time_window=60)
async def img2img(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    prompt = data.get('prompt', '').strip()
    negative_prompt = data.get('negative_prompt', '').strip()
    model_name = data.get('model', DEFAULT_MODEL)
    ratio_key = data.get('ratio', 'square')
    steps = data.get('steps', 20)
    cfg_scale = data.get('cfg_scale', 7.0)
    seed = data.get('seed', -1)
    style_name = data.get('style', '')
    input_image = data.get('input_image', '').strip()
    quality = data.get('quality', 'standard')

    if not prompt:
        return {"code": 400, "msg": "请输入提示词", "data": None}

    if not input_image:
        return {"code": 400, "msg": "请上传参考图片", "data": None}

    passed, filter_msg = filter_prompt(prompt)
    if not passed:
        return {"code": 400, "msg": filter_msg, "data": None}

    user_id = current_user['user_id']

    allowed, action_msg = check_user_action_limit(user_id, 'generate')
    if not allowed:
        return {"code": 429, "msg": action_msg, "data": None}

    quality, quality_tier = _get_quality_tier(quality, current_user['package_type'])
    credits_cost = quality_tier['credits_per_image'] + 1

    user_credits = get_user_credits(user_id)
    if user_credits < credits_cost:
        return {"code": 403, "msg": f"积分不足，当前{user_credits}积分，需要{credits_cost}积分", "data": None}

    if ratio_key not in PRESET_RATIOS:
        ratio_key = 'square'

    if model_name not in SUPPORTED_MODELS:
        model_name = DEFAULT_MODEL

    ratio_info = PRESET_RATIOS[ratio_key]

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '待执行'")
        queue_count = cursor.fetchone()[0]
        if queue_count >= MAX_QUEUE_SIZE:
            return {"code": 429, "msg": "队列已满，请稍后再试", "data": None}

    if not deduct_credits(user_id, credits_cost, f"图生图 {quality} {ratio_info['label']}"):
        return {"code": 403, "msg": "积分扣费失败", "data": None}

    increment_daily_count(user_id)

    task_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(queue_order) FROM global_generate_queue WHERE task_status = '待执行'")
        max_order = cursor.fetchone()[0]
        queue_order = (max_order or 0) + 1

        cursor.execute('''
            INSERT INTO global_generate_queue
            (user_id, task_id, prompt, negative_prompt, model_name, width, height, steps, cfg_scale, seed, style_name, input_image_path, task_type, quality_tier, credits_cost, submit_time, task_status, queue_order, package_type, ratio_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'img2img', ?, ?, ?, '待执行', ?, ?, ?)
        ''', (user_id, task_id, prompt, negative_prompt, model_name, 0, 0, steps, cfg_scale, seed, style_name, input_image, quality, credits_cost, now, queue_order, current_user['package_type'], ratio_key))
        conn.commit()

    return {
        "code": 200,
        "msg": "任务已提交",
        "data": {
            "task_id": task_id,
            "status": "待执行",
            "queue_position": int(queue_order),
            "credits_cost": credits_cost,
            "quality": quality,
            "ratio": ratio_key,
            "ratio_label": ratio_info['label'],
            "remaining_credits": get_user_credits(user_id),
        }
    }


@router.get("/status/{task_id}")
async def get_task_status(request: Request, task_id: str, current_user: dict = Depends(get_current_user)):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM global_generate_queue WHERE task_id = ? AND user_id = ?",
            (task_id, current_user['user_id'])
        )
        task = cursor.fetchone()

    if not task:
        return {"code": 404, "msg": "任务不存在", "data": None}

    task = dict(task)

    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "task_id": task['task_id'],
            "status": task['task_status'],
            "prompt": task['prompt'],
            "model_name": task['model_name'],
            "width": task['width'],
            "height": task['height'],
            "quality_tier": task.get('quality_tier', 'standard'),
            "credits_cost": task.get('credits_cost', 1),
            "output_image_path": task['output_image_path'],
            "fail_reason": task['fail_reason'],
            "submit_time": task['submit_time'],
            "finish_time": task['finish_time'],
        }
    }


@router.get("/queue")
async def get_queue_status(request: Request, current_user: dict = Depends(get_current_user)):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '待执行'"
        )
        pending_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '执行中'"
        )
        running_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM global_generate_queue WHERE user_id = ? AND task_status = '待执行'",
            (current_user['user_id'],)
        )
        my_pending = cursor.fetchone()[0]

    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "pending_count": pending_count,
            "running_count": running_count,
            "my_pending": my_pending,
        }
    }


@router.get("/models")
async def get_models(request: Request):
    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "models": SUPPORTED_MODELS,
            "default": DEFAULT_MODEL,
            "quality_tiers": {k: {
                "label": v["label"],
                "model": v.get("model", "gpt-image-2"),
                "api_quality": v["api_quality"],
                "credits_per_image": v["credits_per_image"],
                "description": v["description"],
                "icon": v["icon"],
                "available": v.get("available", True),
            } for k, v in QUALITY_TIERS.items()},
            "preset_ratios": {k: {
                "label": v["label"],
                "desc": v["desc"],
                "sizes": v["sizes"],
            } for k, v in PRESET_RATIOS.items()},
            "supported_sizes": OPENAI_SUPPORTED_SIZES,
        }
    }


@router.get("/styles")
async def get_styles(request: Request):
    from services.style_service import get_style_list
    styles = get_style_list()
    return {
        "code": 200,
        "msg": "查询成功",
        "data": {"styles": styles}
    }


@router.get("/pricing")
async def get_pricing(request: Request):
    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "quality_tiers": {k: {
                "label": v["label"],
                "credits_per_image": v["credits_per_image"],
                "description": v["description"],
                "icon": v["icon"],
                "available": v.get("available", True),
            } for k, v in QUALITY_TIERS.items()},
            "credit_packages": {k: {
                "credits": v["credits"],
                "price": v["price"],
                "price_per_credit": round(v["price_per_credit"], 2),
                "valid_days": v["valid_days"],
                "popular": v["popular"],
                "description": v["description"],
                "badge": v["badge"],
            } for k, v in CREDIT_PACKAGES.items()},
            "preset_ratios": {k: {
                "label": v["label"],
                "desc": v["desc"],
            } for k, v in PRESET_RATIOS.items()},
        }
    }
