import sqlite3
import threading
import os
import uuid
from datetime import datetime
from contextlib import contextmanager

from core.config import GLOBAL_DB_PATH, USER_DATA_DIR, PACKAGES

_global_db_lock = threading.RLock()

os.makedirs(USER_DATA_DIR, exist_ok=True)


def get_global_db():
    conn = sqlite3.connect(GLOBAL_DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA wal_autocheckpoint=1000")
    return conn


@contextmanager
def global_db_conn():
    conn = get_global_db()
    try:
        yield conn
    finally:
        conn.close()


def init_global_db():
    conn = get_global_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            default_model TEXT NOT NULL DEFAULT 'gpt-image-2',
            daily_generate_limit INTEGER NOT NULL DEFAULT 500,
            today_generated_count INTEGER NOT NULL DEFAULT 0,
            last_reset_date TEXT NOT NULL,
            content_filter_enabled INTEGER NOT NULL DEFAULT 1
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM global_config")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO global_config (id, default_model, daily_generate_limit, today_generated_count, last_reset_date)
            VALUES (1, 'gpt-image-2', 500, 0, date('now'))
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_user_info (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            auth_code_hash TEXT NOT NULL,
            package_type TEXT NOT NULL DEFAULT '免费版',
            credits INTEGER NOT NULL DEFAULT 0,
            total_credits_purchased INTEGER NOT NULL DEFAULT 0,
            total_credits_used INTEGER NOT NULL DEFAULT 0,
            daily_generate_limit INTEGER NOT NULL DEFAULT 9999,
            today_generated_count INTEGER NOT NULL DEFAULT 0,
            last_reset_date TEXT NOT NULL,
            expire_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT '正常',
            create_time TEXT NOT NULL
        )
    ''')

    try:
        cursor.execute("ALTER TABLE global_user_info ADD COLUMN credits INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE global_user_info ADD COLUMN total_credits_purchased INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE global_user_info ADD COLUMN total_credits_used INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_auth_codes (
            auth_code TEXT PRIMARY KEY,
            package_type TEXT NOT NULL,
            valid_days INTEGER NOT NULL,
            credits INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT '未激活',
            create_time TEXT NOT NULL,
            activate_user_id TEXT,
            batch_no TEXT DEFAULT '',
            batch_name TEXT DEFAULT '',
            export_tag TEXT DEFAULT ''
        )
    ''')
    try:
        cursor.execute("ALTER TABLE global_auth_codes ADD COLUMN credits INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE global_auth_codes ADD COLUMN batch_no TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE global_auth_codes ADD COLUMN batch_name TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE global_auth_codes ADD COLUMN export_tag TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_codes_status ON global_auth_codes(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_codes_batch ON global_auth_codes(batch_no)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_codes_package ON global_auth_codes(package_type)")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_credits_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            change_amount INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            balance_after INTEGER NOT NULL,
            create_time TEXT NOT NULL
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_credits_log_user ON global_credits_log(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_credits_log_time ON global_credits_log(create_time)")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_generate_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            task_id TEXT UNIQUE NOT NULL,
            prompt TEXT NOT NULL,
            negative_prompt TEXT DEFAULT '',
            model_name TEXT NOT NULL DEFAULT 'gpt-image-2',
            width INTEGER NOT NULL DEFAULT 1024,
            height INTEGER NOT NULL DEFAULT 1024,
            steps INTEGER NOT NULL DEFAULT 20,
            cfg_scale REAL NOT NULL DEFAULT 7.0,
            seed INTEGER DEFAULT -1,
            style_name TEXT DEFAULT '',
            input_image_path TEXT DEFAULT '',
            task_type TEXT NOT NULL DEFAULT 'text2img',
            quality_tier TEXT NOT NULL DEFAULT 'standard',
            credits_cost INTEGER NOT NULL DEFAULT 1,
            submit_time TEXT NOT NULL,
            task_status TEXT NOT NULL DEFAULT '待执行',
            execute_time TEXT,
            finish_time TEXT,
            fail_reason TEXT,
            output_image_path TEXT DEFAULT '',
            queue_order REAL NOT NULL
        )
    ''')
    try:
        cursor.execute("ALTER TABLE global_generate_queue ADD COLUMN package_type TEXT DEFAULT '基础版'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE global_generate_queue ADD COLUMN quality_tier TEXT NOT NULL DEFAULT 'standard'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE global_generate_queue ADD COLUMN credits_cost INTEGER NOT NULL DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE global_generate_queue ADD COLUMN ratio_key TEXT DEFAULT 'square'")
    except sqlite3.OperationalError:
        pass
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON global_generate_queue(task_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_user ON global_generate_queue(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_order ON global_generate_queue(queue_order)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_task_id ON global_generate_queue(task_id)")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            create_time TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_operation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_username TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            operation_content TEXT NOT NULL,
            operation_time TEXT NOT NULL,
            operation_ip TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_daily_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary_date TEXT NOT NULL UNIQUE,
            total_users INTEGER DEFAULT 0,
            total_generated INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            revenue REAL DEFAULT 0,
            cost REAL DEFAULT 0
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_summary_date ON global_daily_summary(summary_date)")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_style_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            style_name TEXT UNIQUE NOT NULL,
            style_prompt TEXT NOT NULL,
            style_negative_prompt TEXT DEFAULT '',
            preview_image TEXT DEFAULT '',
            category TEXT DEFAULT '通用',
            is_preset INTEGER NOT NULL DEFAULT 1,
            create_time TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def get_user_db(user_id: str):
    import re
    safe_uid = re.sub(r'[^a-zA-Z0-9_]', '', user_id.replace("USER_", ""))
    if not safe_uid:
        safe_uid = "unknown"
    db_path = os.path.join(USER_DATA_DIR, f"user_data_{safe_uid}.db")
    real_path = os.path.realpath(db_path)
    real_data_dir = os.path.realpath(USER_DATA_DIR)
    if not real_path.startswith(real_data_dir):
        raise ValueError(f"Invalid user_id: {user_id}")
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_user_db_conn(user_id: str):
    conn = get_user_db(user_id)
    try:
        yield conn
    finally:
        conn.close()


def init_user_db(user_id: str):
    conn = get_user_db(user_id)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            prompt TEXT NOT NULL,
            negative_prompt TEXT DEFAULT '',
            model_name TEXT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            steps INTEGER NOT NULL,
            cfg_scale REAL NOT NULL,
            seed INTEGER NOT NULL,
            style_name TEXT DEFAULT '',
            task_type TEXT NOT NULL DEFAULT 'text2img',
            input_image_path TEXT DEFAULT '',
            output_image_path TEXT NOT NULL DEFAULT '',
            create_time TEXT NOT NULL,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            is_deleted INTEGER NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_works_create_time ON user_works(create_time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_works_favorite ON user_works(is_favorite)")

    try:
        cursor.execute("ALTER TABLE user_works ADD COLUMN quality_tier TEXT NOT NULL DEFAULT 'standard'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE user_works ADD COLUMN credits_cost INTEGER NOT NULL DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE user_works ADD COLUMN ratio_key TEXT DEFAULT 'square'")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_generate_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            model_name TEXT NOT NULL,
            status TEXT NOT NULL,
            create_time TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def get_next_task_from_queue():
    with _global_db_lock:
        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM global_generate_queue
                WHERE task_status = '待执行'
                ORDER BY queue_order ASC, id ASC
                LIMIT 1
            ''')
            task = cursor.fetchone()
            return dict(task) if task else None


def update_task_status(task_id: str, status: str, **kwargs):
    with _global_db_lock:
        with global_db_conn() as conn:
            cursor = conn.cursor()
            sets = ["task_status = ?"]
            vals = [status]
            for k, v in kwargs.items():
                if k in ('execute_time', 'finish_time', 'output_image_path', 'fail_reason', 'seed'):
                    sets.append(f"{k} = ?")
                    vals.append(v)
            vals.append(task_id)
            cursor.execute(
                f"UPDATE global_generate_queue SET {', '.join(sets)} WHERE task_id = ?",
                vals
            )
            conn.commit()


def increment_daily_count(user_id: str):
    today = datetime.now().strftime('%Y-%m-%d')
    with _global_db_lock:
        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT today_generated_count, last_reset_date FROM global_user_info WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if not row:
                return
            if row['last_reset_date'] != today:
                cursor.execute(
                    "UPDATE global_user_info SET today_generated_count = 1, last_reset_date = ? WHERE user_id = ?",
                    (today, user_id)
                )
            else:
                cursor.execute(
                    "UPDATE global_user_info SET today_generated_count = today_generated_count + 1 WHERE user_id = ?",
                    (user_id,)
                )
            conn.commit()


def check_daily_quota(user_id: str) -> bool:
    today = datetime.now().strftime('%Y-%m-%d')
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT today_generated_count, last_reset_date, daily_generate_limit FROM global_user_info WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False
        if row['last_reset_date'] != today:
            return True
        return row['today_generated_count'] < row['daily_generate_limit']


def get_user_credits(user_id: str) -> int:
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT credits FROM global_user_info WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row['credits'] if row else 0


def deduct_credits(user_id: str, amount: int, description: str = "") -> bool:
    with _global_db_lock:
        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT credits FROM global_user_info WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row or row['credits'] < amount:
                return False
            new_balance = row['credits'] - amount
            cursor.execute(
                "UPDATE global_user_info SET credits = ?, total_credits_used = total_credits_used + ? WHERE user_id = ?",
                (new_balance, amount, user_id)
            )
            cursor.execute('''
                INSERT INTO global_credits_log (user_id, change_amount, change_type, description, balance_after, create_time)
                VALUES (?, ?, 'consume', ?, ?, ?)
            ''', (user_id, -amount, description, new_balance, datetime.now().isoformat()))
            conn.commit()
            return True


def add_credits(user_id: str, amount: int, change_type: str = 'purchase', description: str = "") -> int:
    with _global_db_lock:
        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT credits FROM global_user_info WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return -1
            new_balance = row['credits'] + amount
            cursor.execute(
                "UPDATE global_user_info SET credits = ?, total_credits_purchased = total_credits_purchased + ? WHERE user_id = ?",
                (new_balance, amount, user_id)
            )
            cursor.execute('''
                INSERT INTO global_credits_log (user_id, change_amount, change_type, description, balance_after, create_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, amount, change_type, description, new_balance, datetime.now().isoformat()))
            conn.commit()
            return new_balance


def refund_credits(user_id: str, amount: int, description: str = "") -> int:
    with _global_db_lock:
        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT credits FROM global_user_info WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return -1
            new_balance = row['credits'] + amount
            cursor.execute(
                "UPDATE global_user_info SET credits = ?, total_credits_used = total_credits_used - ? WHERE user_id = ?",
                (new_balance, amount, user_id)
            )
            cursor.execute('''
                INSERT INTO global_credits_log (user_id, change_amount, change_type, description, balance_after, create_time)
                VALUES (?, ?, 'refund', ?, ?, ?)
            ''', (user_id, amount, description, new_balance, datetime.now().isoformat()))
            conn.commit()
            return new_balance


def get_user_today_count(user_id: str) -> int:
    today = datetime.now().strftime('%Y-%m-%d')
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT today_generated_count, last_reset_date FROM global_user_info WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return 0
        if row['last_reset_date'] != today:
            return 0
        return row['today_generated_count']


def log_admin_operation(admin_username: str, op_type: str, op_content: str, op_ip: str = "127.0.0.1"):
    with _global_db_lock:
        with global_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO global_operation_log (admin_username, operation_type, operation_content, operation_time, operation_ip)
                VALUES (?, ?, ?, ?, ?)
            ''', (admin_username, op_type, op_content, datetime.now().isoformat(), op_ip))
            conn.commit()
