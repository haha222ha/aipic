from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response

from core.security import get_current_admin, hash_password
from core.database import global_db_conn, log_admin_operation
from core.auth import create_auth_code
from core.config import PACKAGES

router = APIRouter(prefix="/api/admin", tags=["管理员模块"])


@router.get("/users")
async def list_users(request: Request, current_admin: dict = Depends(get_current_admin)):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, package_type, daily_generate_limit, today_generated_count,
                   last_reset_date, expire_time, status, create_time
            FROM global_user_info ORDER BY create_time DESC
        ''')
        users = [dict(row) for row in cursor.fetchall()]

    return {"code": 200, "msg": "查询成功", "data": {"users": users}}


@router.post("/users/{user_id}/freeze")
async def freeze_user(request: Request, user_id: str, current_admin: dict = Depends(get_current_admin)):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE global_user_info SET status = '冻结' WHERE user_id = ?", (user_id,))
        conn.commit()

    log_admin_operation(
        current_admin['username'], "冻结用户", f"冻结用户 {user_id}",
        request.client.host if request else "unknown"
    )
    return {"code": 200, "msg": "用户已冻结", "data": None}


@router.post("/users/{user_id}/unfreeze")
async def unfreeze_user(request: Request, user_id: str, current_admin: dict = Depends(get_current_admin)):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE global_user_info SET status = '正常' WHERE user_id = ?", (user_id,))
        conn.commit()

    log_admin_operation(
        current_admin['username'], "解冻用户", f"解冻用户 {user_id}",
        request.client.host if request else "unknown"
    )
    return {"code": 200, "msg": "用户已解冻", "data": None}


@router.get("/codes")
async def list_codes(request: Request, current_admin: dict = Depends(get_current_admin)):
    status_filter = request.query_params.get('status', '')

    with global_db_conn() as conn:
        cursor = conn.cursor()
        if status_filter:
            cursor.execute(
                "SELECT * FROM global_auth_codes WHERE status = ? ORDER BY create_time DESC",
                (status_filter,)
            )
        else:
            cursor.execute("SELECT * FROM global_auth_codes ORDER BY create_time DESC")
        codes = [dict(row) for row in cursor.fetchall()]

    return {"code": 200, "msg": "查询成功", "data": {"codes": codes}}


@router.post("/codes/generate")
async def generate_codes(request: Request, current_admin: dict = Depends(get_current_admin)):
    data = await request.json()
    package_type = data.get('package_type', '基础版')
    count = min(data.get('count', 1), 100)
    valid_days = data.get('valid_days', 30)

    if package_type not in PACKAGES:
        return {"code": 400, "msg": "无效的套餐类型", "data": None}

    pkg = PACKAGES[package_type]
    credits = pkg.get('credits', 0)
    if credits == 0 and package_type == '免费版':
        credits = pkg.get('free_credits', 3)

    codes = []
    with global_db_conn() as conn:
        cursor = conn.cursor()
        for _ in range(count):
            code = create_auth_code()
            cursor.execute('''
                INSERT INTO global_auth_codes (auth_code, package_type, valid_days, credits, status, create_time)
                VALUES (?, ?, ?, ?, '未激活', ?)
            ''', (code, package_type, valid_days, credits, datetime.now().isoformat()))
            codes.append(code)
        conn.commit()

    log_admin_operation(
        current_admin['username'], "生成授权码",
        f"生成{count}个{package_type}授权码，有效期{valid_days}天，含{credits}积分",
        request.client.host if request else "unknown"
    )

    return {"code": 200, "msg": f"成功生成{count}个授权码", "data": {"codes": codes}}


@router.delete("/codes/{auth_code}")
async def delete_code(request: Request, auth_code: str, current_admin: dict = Depends(get_current_admin)):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM global_auth_codes WHERE auth_code = ?", (auth_code,))
        row = cursor.fetchone()
        if not row:
            return {"code": 404, "msg": "授权码不存在", "data": None}
        if row['status'] == '已激活':
            return {"code": 400, "msg": "已激活的授权码不能删除", "data": None}
        cursor.execute("DELETE FROM global_auth_codes WHERE auth_code = ?", (auth_code,))
        conn.commit()

    return {"code": 200, "msg": "删除成功", "data": None}


@router.get("/stats")
async def get_stats(request: Request, current_admin: dict = Depends(get_current_admin)):
    with global_db_conn() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM global_user_info WHERE status = '正常'")
        active_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM global_user_info")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '待执行'")
        pending_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '执行中'")
        running_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '已完成' AND date(finish_time) = date('now')")
        today_completed = cursor.fetchone()[0]

        cursor.execute('''
            SELECT package_type, COUNT(*) as count FROM global_user_info WHERE status = '正常'
            GROUP BY package_type
        ''')
        package_dist = {row['package_type']: row['count'] for row in cursor.fetchall()}

    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "total_users": total_users,
            "active_users": active_users,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "today_completed": today_completed,
            "package_distribution": package_dist,
        }
    }


@router.get("/config")
async def get_config(request: Request, current_admin: dict = Depends(get_current_admin)):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM global_config WHERE id = 1")
        config = cursor.fetchone()

    if not config:
        return {"code": 404, "msg": "配置不存在", "data": None}

    return {"code": 200, "msg": "查询成功", "data": dict(config)}


@router.post("/config")
async def update_config(request: Request, current_admin: dict = Depends(get_current_admin)):
    data = await request.json()

    with global_db_conn() as conn:
        cursor = conn.cursor()
        if 'default_model' in data:
            cursor.execute("UPDATE global_config SET default_model = ? WHERE id = 1", (data['default_model'],))
        if 'daily_generate_limit' in data:
            cursor.execute("UPDATE global_config SET daily_generate_limit = ? WHERE id = 1", (data['daily_generate_limit'],))
        if 'content_filter_enabled' in data:
            cursor.execute("UPDATE global_config SET content_filter_enabled = ? WHERE id = 1", (int(data['content_filter_enabled']),))
        conn.commit()

    log_admin_operation(
        current_admin['username'], "修改配置", str(data),
        request.client.host if request else "unknown"
    )

    return {"code": 200, "msg": "配置已更新", "data": None}


@router.post("/init_admin")
async def init_admin(request: Request):
    data = await request.json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return {"code": 400, "msg": "请输入用户名和密码", "data": None}

    if len(password) < 6:
        return {"code": 400, "msg": "密码至少6位", "data": None}

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM global_admin")
        if cursor.fetchone()[0] > 0:
            return {"code": 400, "msg": "管理员账号已存在，请使用脚本创建", "data": None}

        cursor.execute('''
            INSERT INTO global_admin (username, password_hash, create_time)
            VALUES (?, ?, ?)
        ''', (username, hash_password(password), datetime.now().isoformat()))
        conn.commit()

    return {"code": 200, "msg": "管理员账号创建成功", "data": None}


@router.get("/logs")
async def get_logs(request: Request, current_admin: dict = Depends(get_current_admin)):
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('size', 50))
    offset = (page - 1) * page_size

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM global_operation_log")
        total = cursor.fetchone()[0]

        cursor.execute('''
            SELECT * FROM global_operation_log
            ORDER BY operation_time DESC LIMIT ? OFFSET ?
        ''', (page_size, offset))
        logs = [dict(row) for row in cursor.fetchall()]

    return {"code": 200, "msg": "查询成功", "data": {"total": total, "logs": logs}}


@router.get("/styles")
async def list_styles(request: Request, current_admin: dict = Depends(get_current_admin)):
    from services.style_service import get_style_list
    styles = get_style_list()
    return {"code": 200, "msg": "查询成功", "data": {"styles": styles}}


@router.post("/styles")
async def add_style_route(request: Request, current_admin: dict = Depends(get_current_admin)):
    from services.style_service import add_style
    data = await request.json()
    success, msg = add_style(
        style_name=data.get('style_name', ''),
        style_prompt=data.get('style_prompt', ''),
        negative_prompt=data.get('negative_prompt', ''),
        category=data.get('category', '通用'),
    )
    if success:
        return {"code": 200, "msg": msg, "data": None}
    return {"code": 400, "msg": msg, "data": None}


@router.delete("/styles/{style_name}")
async def delete_style_route(request: Request, style_name: str, current_admin: dict = Depends(get_current_admin)):
    from services.style_service import delete_style
    success, msg = delete_style(style_name)
    if success:
        return {"code": 200, "msg": msg, "data": None}
    return {"code": 400, "msg": msg, "data": None}


@router.get("/credits/log")
async def get_all_credits_log(request: Request, current_admin: dict = Depends(get_current_admin)):
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('size', 50))
    user_id = request.query_params.get('user_id', '')
    change_type = request.query_params.get('type', '')
    offset = (page - 1) * page_size

    with global_db_conn() as conn:
        cursor = conn.cursor()
        conditions = []
        params = []
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if change_type:
            conditions.append("change_type = ?")
            params.append(change_type)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(f"SELECT COUNT(*) FROM global_credits_log {where}", params)
        total = cursor.fetchone()[0]

        cursor.execute(f'''
            SELECT cl.*, ui.username
            FROM global_credits_log cl
            LEFT JOIN global_user_info ui ON cl.user_id = ui.user_id
            {where}
            ORDER BY cl.create_time DESC LIMIT ? OFFSET ?
        ''', params + [page_size, offset])
        logs = [dict(row) for row in cursor.fetchall()]

    return {"code": 200, "msg": "查询成功", "data": {"total": total, "logs": logs}}


@router.get("/credits/overview")
async def get_credits_overview(request: Request, current_admin: dict = Depends(get_current_admin)):
    with global_db_conn() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT SUM(total_credits_purchased) FROM global_user_info")
        total_purchased = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(total_credits_used) FROM global_user_info")
        total_used = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(credits) FROM global_user_info")
        total_remaining = cursor.fetchone()[0] or 0

        cursor.execute('''
            SELECT change_type, COUNT(*) as count, SUM(ABS(change_amount)) as total_amount
            FROM global_credits_log
            GROUP BY change_type
        ''')
        breakdown = {}
        for r in cursor.fetchall():
            breakdown[r['change_type']] = {"count": r['count'], "total_amount": r['total_amount']}

        cursor.execute('''
            SELECT quality_tier, COUNT(*) as count, SUM(credits_cost) as total_cost
            FROM global_generate_queue
            WHERE task_status = '已完成'
            GROUP BY quality_tier
        ''')
        quality_stats = {}
        for r in cursor.fetchall():
            quality_stats[r['quality_tier']] = {"count": r['count'], "total_cost": r['total_cost']}

        cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '已完成'")
        total_generated = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM global_user_info WHERE status = '正常' AND credits > 0")
        active_paying_users = cursor.fetchone()[0]

    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "total_purchased": total_purchased,
            "total_used": total_used,
            "total_remaining": total_remaining,
            "total_generated": total_generated,
            "active_paying_users": active_paying_users,
            "breakdown": breakdown,
            "quality_stats": quality_stats,
        }
    }


@router.get("/users/{user_id}/credits")
async def get_user_credits_detail(request: Request, user_id: str, current_admin: dict = Depends(get_current_admin)):
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('size', 50))
    offset = (page - 1) * page_size

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM global_user_info WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return {"code": 404, "msg": "用户不存在", "data": None}

        cursor.execute(
            "SELECT COUNT(*) FROM global_credits_log WHERE user_id = ?",
            (user_id,)
        )
        total = cursor.fetchone()[0]

        cursor.execute('''
            SELECT id, change_amount, change_type, description, balance_after, create_time
            FROM global_credits_log
            WHERE user_id = ?
            ORDER BY create_time DESC LIMIT ? OFFSET ?
        ''', (user_id, page_size, offset))
        logs = [dict(row) for row in cursor.fetchall()]

    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "user": dict(user),
            "total": total,
            "logs": logs,
        }
    }


import secrets
from io import StringIO
import csv
from fastapi.responses import StreamingResponse


def generate_batch_no():
    now = datetime.now()
    return f"BATCH{now.strftime('%Y%m%d%H%M%S')}{secrets.token_hex(2).upper()}"


@router.post("/codes/batch-generate")
async def batch_generate_codes(request: Request, current_admin: dict = Depends(get_current_admin)):
    data = await request.json()
    package_type = data.get('package_type', '基础版')
    count = min(data.get('count', 1), 500)
    valid_days = data.get('valid_days', 30)
    batch_name = data.get('batch_name', '').strip()
    export_tag = data.get('export_tag', '').strip()

    if package_type not in PACKAGES:
        return {"code": 400, "msg": "无效的套餐类型", "data": None}

    if not batch_name:
        batch_name = f"{package_type}-{datetime.now().strftime('%Y%m%d')}"

    pkg = PACKAGES[package_type]
    credits = pkg.get('credits', 0)
    if credits == 0 and package_type == '免费版':
        credits = pkg.get('free_credits', 3)

    batch_no = generate_batch_no()

    codes = []
    with global_db_conn() as conn:
        cursor = conn.cursor()
        for _ in range(count):
            code = create_auth_code()
            cursor.execute('''
                INSERT INTO global_auth_codes (auth_code, package_type, valid_days, credits, status, create_time, batch_no, batch_name, export_tag)
                VALUES (?, ?, ?, ?, '未激活', ?, ?, ?, ?)
            ''', (code, package_type, valid_days, credits, datetime.now().isoformat(), batch_no, batch_name, export_tag))
            codes.append(code)
        conn.commit()

    log_admin_operation(
        current_admin['username'], "批量生成授权码",
        f"批次号:{batch_no}, 批次名:{batch_name}, 套餐:{package_type}, 数量:{count}, 积分:{credits}, 标签:{export_tag}",
        request.client.host if request else "unknown"
    )

    return {
        "code": 200,
        "msg": f"成功生成{count}个授权码",
        "data": {
            "batch_no": batch_no,
            "batch_name": batch_name,
            "package_type": package_type,
            "count": count,
            "credits": credits,
            "valid_days": valid_days,
            "export_tag": export_tag,
            "codes": codes,
        }
    }


@router.get("/codes/batches")
async def list_batches(request: Request, current_admin: dict = Depends(get_current_admin)):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT batch_no, batch_name, package_type, export_tag,
                   COUNT(*) as total_count,
                   SUM(CASE WHEN status = '未激活' THEN 1 ELSE 0 END) as unused_count,
                   SUM(CASE WHEN status = '已激活' THEN 1 ELSE 0 END) as used_count,
                   MIN(create_time) as create_time,
                   credits
            FROM global_auth_codes
            WHERE batch_no != '' AND batch_no IS NOT NULL
            GROUP BY batch_no
            ORDER BY create_time DESC
        ''')
        batches = [dict(row) for row in cursor.fetchall()]

    return {"code": 200, "msg": "查询成功", "data": {"batches": batches}}


@router.get("/codes/export")
async def export_codes(request: Request):
    admin_username = request.cookies.get('admin_username')
    if not admin_username:
        return {"code": 401, "msg": "请先登录", "data": None}
        
    batch_no = request.query_params.get('batch_no', '')
    package_type = request.query_params.get('package_type', '')
    status = request.query_params.get('status', '')
    export_format = request.query_params.get('format', 'csv')

    with global_db_conn() as conn:
        cursor = conn.cursor()
        conditions = []
        params = []

        if batch_no:
            conditions.append("batch_no = ?")
            params.append(batch_no)
        if package_type:
            conditions.append("package_type = ?")
            params.append(package_type)
        if status:
            conditions.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(f'''
            SELECT auth_code, package_type, credits, valid_days, status, batch_no, batch_name, export_tag, create_time, activate_user_id
            FROM global_auth_codes {where}
            ORDER BY create_time DESC
        ''', params)
        codes = [dict(row) for row in cursor.fetchall()]

    if not codes:
        return {"code": 404, "msg": "没有符合条件的授权码", "data": None}

    if export_format == 'csv':
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['授权码', '套餐类型', '积分', '有效期(天)', '状态', '批次号', '批次名称', '导出标签', '创建时间', '激活用户'])
        for c in codes:
            writer.writerow([
                c['auth_code'],
                c['package_type'],
                c['credits'],
                c['valid_days'],
                c['status'],
                c['batch_no'],
                c['batch_name'],
                c['export_tag'],
                c['create_time'],
                c['activate_user_id'] or '',
            ])

        safe_filename = f"auth_codes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_bytes = output.getvalue().encode('utf-8')

        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=\"{safe_filename}\"",
                "Access-Control-Expose-Headers": "Content-Disposition",
            }
        )

    return {"code": 400, "msg": "不支持的导出格式", "data": None}
