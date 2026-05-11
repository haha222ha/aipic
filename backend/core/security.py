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

_ADMIN_SESSION_SECRET = os.environ.get("ADMIN_SESSION_SECRET") or secrets.token_hex(32)
_admin_sessions: dict = {}


def _sign_admin_token(username: str) -> str:
    raw = f"{username}:{_ADMIN_SESSION_SECRET}"
    sig = hmac.new(_ADMIN_SESSION_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{username}:{sig}"


def _verify_admin_token(token: str) -> Optional[str]:
    try:
        username, sig = token.rsplit(':', 1)
        raw = f"{username}:{_ADMIN_SESSION_SECRET}"
        expected_sig = hmac.new(_ADMIN_SESSION_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:32]
        if hmac.compare_digest(sig, expected_sig):
            return username
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


_rate_limit_store: dict = {}


def rate_limit(limit: int = RATE_LIMIT_REQUESTS, time_window: int = RATE_LIMIT_WINDOW):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = _get_client_ip(request)
            key = f"{func.__name__}:{client_ip}"
            now = time.time()

            if key not in _rate_limit_store:
                _rate_limit_store[key] = []

            _rate_limit_store[key] = [t for t in _rate_limit_store[key] if now - t < time_window]

            if len(_rate_limit_store[key]) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"code": 429, "msg": "请求过于频繁，请稍后再试", "data": None}
                )

            _rate_limit_store[key].append(now)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


_user_action_store: dict = {}
_user_freeze_store: dict = {}


def check_user_action_limit(user_id: str, action_type: str = 'generate') -> tuple:
    now = time.time()

    if user_id in _user_freeze_store:
        if now < _user_freeze_store[user_id]:
            remaining = int(_user_freeze_store[user_id] - now)
            return False, f"操作过于频繁，请{remaining}秒后再试"
        else:
            del _user_freeze_store[user_id]

    if user_id not in _user_action_store:
        _user_action_store[user_id] = {}

    if action_type not in _user_action_store[user_id]:
        _user_action_store[user_id][action_type] = []

    cutoff = now - USER_ACTION_WINDOW
    _user_action_store[user_id][action_type] = [
        t for t in _user_action_store[user_id][action_type] if t > cutoff
    ]

    recent_count = len(_user_action_store[user_id][action_type])

    if recent_count >= USER_ACTION_LIMIT:
        _user_freeze_store[user_id] = now + USER_FREEZE_DURATION
        _user_action_store[user_id][action_type] = []
        return False, "操作过于频繁，系统已临时限制5分钟"

    _user_action_store[user_id][action_type].append(now)
    return True, ""


def cleanup_user_action_store():
    now = time.time()
    cutoff = now - USER_FREEZE_DURATION

    expired_users = [
        uid for uid, actions in _user_action_store.items()
        if not any(t > cutoff for t in actions.get('generate', []))
    ]
    for uid in expired_users:
        del _user_action_store[uid]

    expired_frozen = [
        uid for uid, until in _user_freeze_store.items()
        if now >= until
    ]
    for uid in expired_frozen:
        del _user_freeze_store[uid]

    expired_rate_limits = [
        key for key, timestamps in _rate_limit_store.items()
        if not any(now - t < RATE_LIMIT_WINDOW for t in timestamps)
    ]
    for key in expired_rate_limits:
        del _rate_limit_store[key]


def _cleanup_expired_rate_limits():
    now = time.time()
    expired_keys = [
        key for key, timestamps in _rate_limit_store.items()
        if not any(now - t < RATE_LIMIT_WINDOW for t in timestamps)
    ]
    for key in expired_keys:
        del _rate_limit_store[key]


def get_user_from_cookie(request: Request) -> Optional[dict]:
    user_id = request.cookies.get("user_id")
    auth_code = request.cookies.get("auth_code")
    if not user_id or not auth_code:
        return None
    return verify_user(user_id, auth_code)


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
