from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from core.auth import activate_auth_code, create_auth_code
from core.security import rate_limit, get_current_admin, verify_password, _sign_admin_token, _get_client_ip
from core.database import global_db_conn, log_admin_operation
from core.config import PACKAGES

router = APIRouter(prefix="/api/auth", tags=["授权模块"])


@router.post("/activate")
@rate_limit(limit=5, time_window=60)
async def activate(request: Request):
    data = await request.json()
    auth_code = data.get('auth_code', '').strip()
    result = activate_auth_code(auth_code)

    if result['code'] == 200:
        is_secure = request.url.scheme == 'https'
        response = JSONResponse(result)
        response.set_cookie("user_id", result['data']['user_id'], max_age=86400 * 30, httponly=True, samesite="lax", secure=is_secure)
        response.set_cookie("auth_code", auth_code, max_age=86400 * 30, httponly=True, samesite="lax", secure=is_secure)
        return response

    return result


@router.get("/verify")
async def verify(request: Request):
    from core.security import get_user_from_cookie
    user = get_user_from_cookie(request)
    if not user:
        return {"code": 401, "msg": "未登录", "data": None}

    from core.database import get_user_today_count, get_user_credits
    today_count = get_user_today_count(user['user_id'])
    credits = get_user_credits(user['user_id'])

    return {
        "code": 200,
        "msg": "已登录",
        "data": {
            "user_id": user['user_id'],
            "username": user['username'],
            "package_type": user['package_type'],
            "expire_time": user['expire_time'],
            "credits": credits,
            "daily_generate_limit": user['daily_generate_limit'],
            "today_generated_count": today_count,
        }
    }


@router.post("/logout")
async def logout(request: Request):
    response = JSONResponse({"code": 200, "msg": "已退出", "data": None})
    response.delete_cookie("user_id")
    response.delete_cookie("auth_code")
    return response


@router.post("/admin/login")
@rate_limit(limit=20, time_window=60)
async def admin_login(request: Request):
    data = await request.json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return {"code": 400, "msg": "请输入用户名和密码", "data": None}

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM global_admin WHERE username = ?", (username,))
        admin = cursor.fetchone()

    if not admin or not verify_password(password, admin['password_hash']):
        return {"code": 400, "msg": "用户名或密码错误", "data": None}

    log_admin_operation(username, "登录", "管理员登录", _get_client_ip(request))

    session_token = _sign_admin_token(username)
    is_secure = request.url.scheme == 'https'
    response = JSONResponse({"code": 200, "msg": "登录成功", "data": {"username": username}})
    response.set_cookie("admin_session", session_token, max_age=86400, httponly=True, samesite="lax", secure=is_secure)
    response.delete_cookie("admin_username")
    return response


@router.post("/admin/logout")
async def admin_logout(request: Request):
    response = JSONResponse({"code": 200, "msg": "已退出", "data": None})
    response.delete_cookie("admin_session")
    response.delete_cookie("admin_username")
    return response
