import secrets
from datetime import datetime, timedelta
from typing import Optional

from core.database import global_db_conn, init_user_db, add_credits
from core.config import PACKAGES, AUTH_CODE_LENGTH


def generate_user_id(auth_code: str) -> str:
    random_part = secrets.token_hex(2)
    return f"USER_{auth_code[-8:]}_{random_part}"


def create_auth_code(length: int = AUTH_CODE_LENGTH) -> str:
    return secrets.token_hex(length // 2)


def get_package_info(package_type: str) -> dict:
    return PACKAGES.get(package_type, PACKAGES['免费版'])


def activate_auth_code(auth_code: str):
    if not auth_code or len(auth_code) != AUTH_CODE_LENGTH:
        return {"code": 400, "msg": "授权码格式错误", "data": None}

    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM global_auth_codes WHERE auth_code = ?", (auth_code,))
        code_info = cursor.fetchone()
        if not code_info:
            return {"code": 400, "msg": "授权码不存在", "data": None}
        code_info = dict(code_info)

        if code_info['status'] == '已激活':
            cursor.execute(
                "SELECT * FROM global_user_info WHERE auth_code_hash = ? AND status = '正常'",
                (auth_code,)
            )
            user = cursor.fetchone()
            if user:
                user = dict(user)
                expire_time = _parse_datetime(user['expire_time'])
                if datetime.now() > expire_time:
                    return {"code": 403, "msg": "账号已过期，请续费", "data": None}
                return {
                    "code": 200,
                    "msg": "登录成功",
                    "data": {
                        "user_id": user['user_id'],
                        "username": user['username'],
                        "package_type": user['package_type'],
                        "expire_time": user['expire_time'],
                        "credits": user.get('credits', 0),
                        "daily_generate_limit": user['daily_generate_limit'],
                    }
                }
            else:
                return {"code": 400, "msg": "授权码已激活但用户不存在", "data": None}

        if code_info['status'] == '已过期':
            return {"code": 400, "msg": "该授权码已过期", "data": None}

        user_id = generate_user_id(auth_code)
        username = user_id
        pkg = get_package_info(code_info['package_type'])
        expire_time = (datetime.now() + timedelta(days=code_info['valid_days'])).isoformat()

        initial_credits = code_info.get('credits', 0)
        if initial_credits == 0 and pkg.get('credits', 0) > 0:
            initial_credits = pkg['credits']
        if initial_credits == 0 and pkg.get('free_credits', 0) > 0:
            initial_credits = pkg['free_credits']

        cursor.execute('''
            INSERT INTO global_user_info
            (user_id, username, auth_code_hash, package_type, credits, total_credits_purchased, total_credits_used, daily_generate_limit, today_generated_count, last_reset_date, expire_time, status, create_time)
            VALUES (?, ?, ?, ?, 0, 0, 0, ?, 0, date('now'), ?, '正常', ?)
        ''', (
            user_id, username, auth_code, code_info['package_type'],
            pkg['daily_generate_limit'], expire_time, datetime.now().isoformat()
        ))

        cursor.execute('''
            UPDATE global_auth_codes SET status = '已激活', activate_user_id = ? WHERE auth_code = ?
        ''', (user_id, auth_code))

        conn.commit()

    init_user_db(user_id)

    if initial_credits > 0:
        add_credits(user_id, initial_credits, 'purchase', f"激活{code_info['package_type']}授权码，获得{initial_credits}积分")

    return {
        "code": 200,
        "msg": "激活成功",
        "data": {
            "user_id": user_id,
            "username": username,
            "package_type": code_info['package_type'],
            "expire_time": expire_time,
            "credits": initial_credits,
            "daily_generate_limit": pkg['daily_generate_limit'],
        }
    }


def verify_user(user_id: str, auth_code: str) -> Optional[dict]:
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM global_user_info
            WHERE user_id = ? AND auth_code_hash = ? AND status = '正常'
        ''', (user_id, auth_code))
        user = cursor.fetchone()
        if not user:
            return None
        user = dict(user)
        expire_time = _parse_datetime(user['expire_time'])
        if datetime.now() > expire_time:
            cursor.execute("UPDATE global_user_info SET status = '冻结' WHERE user_id = ?", (user_id,))
            conn.commit()
            return None

        if user.get('package_type') == '免费版':
            today = datetime.now().strftime('%Y-%m-%d')
            if user.get('last_reset_date') != today:
                free_credits = PACKAGES['免费版'].get('free_credits', 3)
                old_credits = user.get('credits', 0)
                cursor.execute(
                    "UPDATE global_user_info SET credits = ?, today_generated_count = 0, last_reset_date = ? WHERE user_id = ?",
                    (free_credits, today, user_id)
                )
                cursor.execute('''
                    INSERT INTO global_credits_log (user_id, change_amount, change_type, description, balance_after, create_time)
                    VALUES (?, ?, 'daily_reset', '免费版每日积分重置', ?, ?)
                ''', (user_id, free_credits - old_credits, free_credits, datetime.now().isoformat()))
                user['credits'] = free_credits
                conn.commit()

        return user


def check_package_limit(user_id: str) -> bool:
    from core.database import check_daily_quota
    return check_daily_quota(user_id)


def _parse_datetime(dt_str: str) -> datetime:
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(dt_str, fmt)
        except (ValueError, TypeError):
            continue
    return datetime.now()
