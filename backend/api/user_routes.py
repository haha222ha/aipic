import os
import base64
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from core.security import get_current_user
from core.database import global_db_conn, get_user_db_conn, get_user_today_count, get_user_credits
from core.config import USER_DATA_DIR

router = APIRouter(prefix="/api/user", tags=["用户模块"])


@router.get("/info")
async def get_user_info(request: Request, current_user: dict = Depends(get_current_user)):
    today_count = get_user_today_count(current_user['user_id'])
    credits = get_user_credits(current_user['user_id'])
    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "user_id": current_user['user_id'],
            "username": current_user['username'],
            "package_type": current_user['package_type'],
            "expire_time": current_user['expire_time'],
            "credits": credits,
            "daily_generate_limit": current_user['daily_generate_limit'],
            "today_generated_count": today_count,
            "status": current_user['status'],
        }
    }


@router.get("/works")
async def get_user_works(request: Request, current_user: dict = Depends(get_current_user)):
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('size', 20))
    work_type = request.query_params.get('type', 'all')
    offset = (page - 1) * page_size

    with get_user_db_conn(current_user['user_id']) as conn:
        cursor = conn.cursor()

        if work_type == 'favorite':
            cursor.execute("SELECT COUNT(*) FROM user_works WHERE is_favorite = 1")
            total = cursor.fetchone()[0]
            cursor.execute('''
                SELECT * FROM user_works WHERE is_favorite = 1 ORDER BY create_time DESC LIMIT ? OFFSET ?
            ''', (page_size, offset))
        else:
            cursor.execute("SELECT COUNT(*) FROM user_works")
            total = cursor.fetchone()[0]
            cursor.execute('''
                SELECT * FROM user_works ORDER BY create_time DESC LIMIT ? OFFSET ?
            ''', (page_size, offset))
        works = [dict(row) for row in cursor.fetchall()]

    return {"code": 200, "msg": "查询成功", "data": {"total": total, "works": works}}


@router.post("/works/{work_id}/favorite")
async def favorite_work(request: Request, work_id: int, current_user: dict = Depends(get_current_user)):
    with get_user_db_conn(current_user['user_id']) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_works WHERE id = ?", (work_id,))
        work = cursor.fetchone()
        if not work:
            return {"code": 404, "msg": "作品不存在", "data": None}

        new_status = 0 if work['is_favorite'] else 1
        cursor.execute("UPDATE user_works SET is_favorite = ? WHERE id = ?", (new_status, work_id))
        conn.commit()

    return {"code": 200, "msg": "操作成功", "data": {"is_favorite": new_status}}


@router.delete("/works/{work_id}")
async def delete_work(request: Request, work_id: int, current_user: dict = Depends(get_current_user)):
    with get_user_db_conn(current_user['user_id']) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_works WHERE id = ?", (work_id,))
        work = cursor.fetchone()
        if not work:
            return {"code": 404, "msg": "作品不存在", "data": None}

        image_path = work['output_image_path']
        cursor.execute("DELETE FROM user_works WHERE id = ?", (work_id,))
        conn.commit()

    if image_path and os.path.exists(image_path):
        try:
            os.remove(image_path)
        except OSError:
            pass

    return {"code": 200, "msg": "删除成功", "data": None}


@router.get("/works/{work_id}/download")
async def download_work(request: Request, work_id: int, current_user: dict = Depends(get_current_user)):
    with get_user_db_conn(current_user['user_id']) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_works WHERE id = ?", (work_id,))
        work = cursor.fetchone()
        if not work:
            return {"code": 404, "msg": "作品不存在", "data": None}

    image_path = work['output_image_path']
    if not image_path or not os.path.exists(image_path):
        return {"code": 404, "msg": "图片文件不存在", "data": None}

    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        filename = os.path.basename(image_path)
        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "filename": filename,
                "image_base64": image_base64,
                "content_type": "image/png",
            }
        }
    except Exception as e:
        return {"code": 500, "msg": f"读取文件失败: {str(e)}", "data": None}


@router.get("/history")
async def get_history(request: Request, current_user: dict = Depends(get_current_user)):
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('size', 20))
    offset = (page - 1) * page_size

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT task_id, prompt, model_name, width, height, task_status, submit_time, finish_time, output_image_path
            FROM global_generate_queue
            WHERE user_id = ? ORDER BY submit_time DESC LIMIT ? OFFSET ?
        ''', (current_user['user_id'], page_size, offset))
        history = [dict(row) for row in cursor.fetchall()]

    return {"code": 200, "msg": "查询成功", "data": {"history": history}}


@router.get("/credits/log")
async def get_credits_log(request: Request, current_user: dict = Depends(get_current_user)):
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('size', 20))
    change_type = request.query_params.get('type', '')
    offset = (page - 1) * page_size

    with global_db_conn() as conn:
        cursor = conn.cursor()
        if change_type:
            cursor.execute(
                "SELECT COUNT(*) FROM global_credits_log WHERE user_id = ? AND change_type = ?",
                (current_user['user_id'], change_type)
            )
            total = cursor.fetchone()[0]
            cursor.execute('''
                SELECT id, change_amount, change_type, description, balance_after, create_time
                FROM global_credits_log
                WHERE user_id = ? AND change_type = ?
                ORDER BY create_time DESC LIMIT ? OFFSET ?
            ''', (current_user['user_id'], change_type, page_size, offset))
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM global_credits_log WHERE user_id = ?",
                (current_user['user_id'],)
            )
            total = cursor.fetchone()[0]
            cursor.execute('''
                SELECT id, change_amount, change_type, description, balance_after, create_time
                FROM global_credits_log
                WHERE user_id = ?
                ORDER BY create_time DESC LIMIT ? OFFSET ?
            ''', (current_user['user_id'], page_size, offset))
        logs = [dict(row) for row in cursor.fetchall()]

    return {"code": 200, "msg": "查询成功", "data": {"total": total, "logs": logs}}


@router.get("/credits/summary")
async def get_credits_summary(request: Request, current_user: dict = Depends(get_current_user)):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT credits, total_credits_purchased, total_credits_used FROM global_user_info WHERE user_id = ?",
                       (current_user['user_id'],))
        row = cursor.fetchone()
        if not row:
            return {"code": 404, "msg": "用户不存在", "data": None}

        cursor.execute('''
            SELECT change_type, COUNT(*) as count, SUM(ABS(change_amount)) as total_amount
            FROM global_credits_log
            WHERE user_id = ?
            GROUP BY change_type
        ''', (current_user['user_id'],))
        breakdown = {}
        for r in cursor.fetchall():
            breakdown[r['change_type']] = {"count": r['count'], "total_amount": r['total_amount']}

        cursor.execute('''
            SELECT COUNT(*) FROM global_generate_queue
            WHERE user_id = ? AND task_status = '已完成'
        ''', (current_user['user_id'],))
        total_generated = cursor.fetchone()[0]

        cursor.execute('''
            SELECT quality_tier, COUNT(*) as count, SUM(credits_cost) as total_cost
            FROM global_generate_queue
            WHERE user_id = ? AND task_status = '已完成'
            GROUP BY quality_tier
        ''', (current_user['user_id'],))
        quality_breakdown = {}
        for r in cursor.fetchall():
            quality_breakdown[r['quality_tier']] = {"count": r['count'], "total_cost": r['total_cost']}

    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "current_credits": row['credits'],
            "total_purchased": row['total_credits_purchased'],
            "total_used": row['total_credits_used'],
            "total_generated": total_generated,
            "breakdown": breakdown,
            "quality_breakdown": quality_breakdown,
        }
    }
