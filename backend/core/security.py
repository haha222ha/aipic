import hashlib
import hmac
import os
import secrets
import time
from functools import wraps
from typing import Optional

from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse

from core.config import (
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW,
    USER_ACTION_LIMIT, USER_ACTION_WINDOW, USER_FREEZE_DURATION,
    CONTENT_FILTER_ENABLED, CONTENT_FILTER_KEYWORDS,
)
from core.auth import verify_user
from core.database import (
    get_persistent_secret, rate_limit_get, rate_limit_set, rate_limit_cleanup_expired,
    user_action_get, user_action_set, user_freeze_get, user_freeze_set,
    user_freeze_delete, user_freeze_cleanup_expired, user_action_cleanup_expired,
    global_db_conn,
)

_ADMIN_SESSION_SECRET = os.environ.get("ADMIN_SESSION_SECRET") or ""
_admin_sessions: dict = {}


def _ensure_admin_secret():
    global _ADMIN_SESSION_SECRET
    if not _ADMIN_SESSION_SECRET:
        _ADMIN_SESSION_SECRET = get_persistent_secret("admin_session_secret")


def _sign_admin_token(username: str) -> str:
    _ensure_admin_secret()
    raw = f"{username}:{_ADMIN_SESSION_SECRET}"
    sig = hmac.new(_ADMIN_SESSION_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{username}:{sig}"


def _verify_admin_token(token: str) -> Optional[str]:
    _ensure_admin_secret()
    try:
        username, sig = token.rsplit(':', 1)
        raw = f"{username}:{_ADMIN_SESSION_SECRET}"
        expected_sig = hmac.new(_ADMIN_SESSION_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:32]
        if hmac.compare_digest(sig, expected_sig):
            return username
    except (ValueError, AttributeError):
        pass
    return None


def _generate_session_token(user_id: str, auth_code: str) -> str:
    _ensure_admin_secret()
    raw = f"user:{user_id}:{auth_code}"
    sig = hmac.new(_ADMIN_SESSION_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{user_id}:{sig}"


def _verify_session_token(token: str) -> Optional[str]:
    _ensure_admin_secret()
    try:
        user_id, sig = token.rsplit(':', 1)
        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT auth_code_hash FROM global_user_info WHERE user_id = ? AND status = '正常'", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            auth_code = row['auth_code_hash']
            raw = f"user:{user_id}:{auth_code}"
            expected_sig = hmac.new(_ADMIN_SESSION_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:32]
            if hmac.compare_digest(sig, expected_sig):
                return user_id
    except (ValueError, AttributeError):
        pass
    return None


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${hashed}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, stored_hash = hashed.split('$', 1)
        computed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return computed == stored_hash
    except (ValueError, AttributeError):
        return False


def _get_client_ip(request: Request) -> str:
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(',')[0].strip()
    return request.client.host if request else "unknown"


def rate_limit(limit: int = RATE_LIMIT_REQUESTS, time_window: int = RATE_LIMIT_WINDOW):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = _get_client_ip(request)
            key = f"{func.__name__}:{client_ip}"
            now = time.time()

            timestamps = rate_limit_get(key)
            timestamps = [t for t in timestamps if now - t < time_window]

            if len(timestamps) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"code": 429, "msg": "请求过于频繁，请稍后再试", "data": None}
                )

            timestamps.append(now)
            rate_limit_set(key, timestamps)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def check_user_action_limit(user_id: str, action_type: str = 'generate') -> tuple:
    now = time.time()

    unfreeze_time = user_freeze_get(user_id)
    if unfreeze_time > 0:
        if now < unfreeze_time:
            remaining = int(unfreeze_time - now)
            return False, f"操作过于频繁，请{remaining}秒后再试"
        else:
            user_freeze_delete(user_id)

    timestamps = user_action_get(user_id, action_type)

    cutoff = now - USER_ACTION_WINDOW
    timestamps = [t for t in timestamps if t > cutoff]

    recent_count = len(timestamps)

    if recent_count >= USER_ACTION_LIMIT:
        user_freeze_set(user_id, now + USER_FREEZE_DURATION)
        user_action_set(user_id, action_type, [])
        return False, "操作过于频繁，系统已临时限制5分钟"

    timestamps.append(now)
    user_action_set(user_id, action_type, timestamps)
    return True, ""


def cleanup_user_action_store():
    now = time.time()
    cutoff = now - USER_FREEZE_DURATION

    expired_rate_limits = []
    all_rate_keys = []
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, timestamps FROM global_rate_limits")
        for row in cursor.fetchall():
            import json
            timestamps = json.loads(row['timestamps'])
            if not any(now - t < RATE_LIMIT_WINDOW for t in timestamps):
                expired_rate_limits.append(row['key'])
    rate_limit_cleanup_expired(expired_rate_limits)

    expired_freeze = []
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, unfreeze_time FROM global_user_freeze")
        for row in cursor.fetchall():
            if now >= row['unfreeze_time']:
                expired_freeze.append(row['user_id'])
    user_freeze_cleanup_expired(expired_freeze)

    expired_actions = []
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, action_type, timestamps FROM global_user_actions")
        for row in cursor.fetchall():
            import json
            timestamps = json.loads(row['timestamps'])
            if not any(t > cutoff for t in timestamps):
                expired_actions.append((row['user_id'], row['action_type']))
    user_action_cleanup_expired(expired_actions)


def get_user_from_cookie(request: Request) -> Optional[dict]:
    user_id = request.cookies.get("user_id")
    session_token = request.cookies.get("session")
    if not user_id or not session_token:
        return None
    verified_user_id = _verify_session_token(session_token)
    if not verified_user_id or verified_user_id != user_id:
        return None
    return verify_user_by_id(user_id)


async def get_current_user(request: Request) -> dict:
    user = get_user_from_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail={"code": 401, "msg": "未登录或登录已过期", "data": None})
    return user


async def get_current_admin(request: Request) -> dict:
    admin_token = request.cookies.get("admin_session")
    if not admin_token:
        raise HTTPException(status_code=401, detail={"code": 401, "msg": "请先登录管理员账号", "data": None})

    admin_username = _verify_admin_token(admin_token)
    if not admin_username:
        raise HTTPException(status_code=401, detail={"code": 401, "msg": "管理员会话已失效，请重新登录", "data": None})

    from core.database import global_db_conn
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM global_admin WHERE username = ?", (admin_username,))
        admin = cursor.fetchone()

    if not admin:
        raise HTTPException(status_code=403, detail={"code": 403, "msg": "管理员权限不足", "data": None})

    return dict(admin)


def require_auth(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user = get_user_from_cookie(request)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "msg": "未登录或登录已过期", "data": None}
            )
        kwargs['current_user'] = user
        return await func(request, *args, **kwargs)
    return wrapper


def require_admin(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        admin_token = request.cookies.get("admin_session")
        if not admin_token:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "msg": "请先登录管理员账号", "data": None}
            )

        admin_username = _verify_admin_token(admin_token)
        if not admin_username:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "msg": "管理员会话已失效，请重新登录", "data": None}
            )

        from core.database import global_db_conn
        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM global_admin WHERE username = ?", (admin_username,))
            admin = cursor.fetchone()

        if not admin:
            return JSONResponse(
                status_code=403,
                content={"code": 403, "msg": "管理员权限不足", "data": None}
            )

        kwargs['current_admin'] = dict(admin)
        return await func(request, *args, **kwargs)
    return wrapper


def filter_prompt(prompt: str) -> tuple:
    if not CONTENT_FILTER_ENABLED:
        return True, ""

    prompt_lower = prompt.lower()
    for keyword in CONTENT_FILTER_KEYWORDS:
        if keyword in prompt_lower:
            return False, f"提示词包含违规内容：{keyword}"

    return True, ""
