# AI 智能作图系统 - 全面审计报告

**审计日期**: 2026-05-11
**审计范围**: 首页、登录/注册、创作工坊、定价、画廊、管理后台、响应式设计、代码安全
**测试环境**: Windows + Chrome Browser + 代码审查
**目标 URL**: https://pic.xhs365.cn/

---

## 摘要

| 严重程度 | 数量 |
|----------|------|
| 🔴 严重 (Critical) | 3 |
|  高危 (High) | 5 |
| 🟡 中危 (Medium) | 8 |
| 🟢 低危 (Low) | 6 |
| **总计** | **22** |

---

## 详细发现

---

### 🔴 ISSUE-001: 管理员会话密钥在内存中硬编码，重启后失效

**文件**: [security.py](file:///d:/aipic/backend/core/security.py#L17)

**问题描述**:
```python
_ADMIN_SESSION_SECRET = secrets.token_hex(32)
```
管理员会话签名密钥在每次应用启动时随机生成，存储在内存中。这意味着：
1. 应用重启后，所有已登录的管理员会话立即失效
2. 在多进程/多实例部署（如 Gunicorn workers）中，不同进程有不同的密钥，导致会话验证失败
3. 无法实现管理员会话的持久化

**影响**: 生产环境中管理员每次重启后都需要重新登录，多实例部署时会话验证不一致。

**修复建议**: 将 `_ADMIN_SESSION_SECRET` 改为从环境变量读取，或存储到数据库/配置文件中：
```python
_ADMIN_SESSION_SECRET = os.environ.get("ADMIN_SESSION_SECRET", secrets.token_hex(32))
```

---

### 🔴 ISSUE-002: 速率限制使用内存存储，重启后丢失，无法抵御持续攻击

**文件**: [security.py](file:///d:/aipic/backend/core/security.py#L65-L85)

**问题描述**:
```python
_rate_limit_store: dict = {}
```
所有速率限制数据存储在内存字典中。应用重启后所有速率限制记录清零，攻击者可以通过等待应用重启来绕过所有限制。

**影响**: 
- 授权码激活接口限制为 5次/60秒，重启后限制清零
- 管理员登录接口限制为 20次/60秒，重启后限制清零
- 生图接口限制为 10次/60秒，重启后限制清零

**修复建议**: 使用 Redis 或 SQLite 存储速率限制数据，确保重启后不丢失。

---

### 🔴 ISSUE-003: 用户操作限制使用内存存储，重启后冻结状态丢失

**文件**: [security.py](file:///d:/aipic/backend/core/security.py#L88-L115)

**问题描述**:
```python
_user_action_store: dict = {}
_user_freeze_store: dict = {}
```
用户操作频率限制和冻结状态全部存储在内存中。应用重启后：
1. 所有被冻结的用户立即解冻
2. 所有操作计数清零
3. 恶意用户可以利用重启来绕过操作限制

**影响**: 用户可以在被冻结5分钟后，通过等待应用重启立即恢复操作能力。

**修复建议**: 将冻结状态和操作计数持久化到数据库或 Redis。

---

### 🟠 ISSUE-004: CORS 配置过于宽松，允许所有方法和头部

**文件**: [main.py](file:///d:/aipic/backend/main.py#L55-L61)

**问题描述**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
虽然 `allow_origins` 有限制，但 `allow_methods=["*"]` 和 `allow_headers=["*"]` 过于宽松。

**影响**: 任何允许的来源都可以使用任意 HTTP 方法和头部进行跨域请求，增加了 CSRF 攻击面。

**修复建议**: 明确指定允许的 HTTP 方法和头部：
```python
allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
allow_headers=["Content-Type", "Authorization"],
```

---

###  ISSUE-005: 授权码激活接口缺少防重放攻击机制

**文件**: [auth_routes.py](file:///d:/aipic/backend/api/auth_routes.py#L12-L23)

**问题描述**:
授权码激活接口只有速率限制（5次/60秒），但没有防重放机制。如果攻击者截获了有效的授权码，可以在速率限制窗口内多次尝试激活。

**影响**: 虽然授权码只能激活一次（数据库层面有约束），但攻击者可以通过重放请求来获取用户信息。

**修复建议**: 
1. 激活成功后立即使授权码失效
2. 添加请求签名或 nonce 机制
3. 激活接口应该使用 HTTPS（已通过 Cloudflare 解决）

---

### 🟠 ISSUE-006: 管理员操作日志记录的是 Nginx 代理 IP 而非真实用户 IP

**文件**: [admin_routes.py](file:///d:/aipic/backend/api/admin_routes.py#L35)

**问题描述**:
```python
log_admin_operation(
    current_admin['username'], "冻结用户", f"冻结用户 {user_id}",
    request.client.host if request else "unknown"
)
```
`request.client.host` 在 Nginx 反向代理后获取的是 Nginx 的 IP（127.0.0.1），而非真实的管理员 IP。虽然 `security.py` 中有 `_get_client_ip()` 函数支持 Cloudflare 真实 IP，但管理员操作日志没有使用该函数。

**影响**: 管理员操作日志中的 IP 地址全部为 127.0.0.1，无法追溯真实操作来源。

**修复建议**: 在所有 `log_admin_operation` 调用中使用 `_get_client_ip(request)` 替代 `request.client.host`。

---

### 🟠 ISSUE-007: 数据库连接没有连接池，高并发下性能瓶颈

**文件**: [database.py](file:///d:/aipic/backend/core/database.py#L18-L25)

**问题描述**:
每次数据库操作都创建新的 SQLite 连接：
```python
def get_global_db():
    conn = sqlite3.connect(GLOBAL_DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
```
虽然有 `global_db_conn()` 上下文管理器负责关闭连接，但没有连接池机制。

**影响**: 在高并发场景下（如多个用户同时生图），频繁的数据库连接创建和销毁会导致性能下降。

**修复建议**: 使用连接池或保持长连接，减少连接创建开销。

---

### 🟠 ISSUE-008: 生图 Worker 异常处理中积分退还可能失败但没有重试机制

**文件**: [generate_worker.py](file:///d:/aipic/backend/workers/generate_worker.py#L63-L72)

**问题描述**:
```python
except Exception as e:
    print(f"Worker执行异常: {e}")
    if self.current_task:
        try:
            update_task_status(...)
            if credits_cost > 0:
                refund_credits(...)
        except Exception:
            pass  # 静默忽略所有异常
```
如果积分退还失败（如数据库锁定），异常被静默忽略，用户损失了积分但没有收到任何通知。

**影响**: 用户在生图失败时可能损失积分，且没有任何补偿机制或通知。

**修复建议**: 
1. 添加积分退还失败的重试机制
2. 记录退还失败日志供管理员审查
3. 通知用户积分退还状态

---

### 🟠 ISSUE-009: 用户数据库文件路径基于 user_id 构造，存在路径遍历风险

**文件**: [database.py](file:///d:/aipic/backend/core/database.py#L227-L231)

**问题描述**:
```python
def get_user_db(user_id: str):
    safe_uid = user_id.replace("USER_", "").replace("-", "_")
    db_path = os.path.join(USER_DATA_DIR, f"user_data_{safe_uid}.db")
```
虽然做了简单的字符串替换，但如果 `user_id` 包含 `../` 等路径遍历字符，仍可能访问非预期目录。

**影响**: 理论上存在路径遍历风险，虽然当前 `user_id` 由系统生成（`USER_{auth_code[-8:]}_{random_part}`），但如果未来允许用户自定义 ID，则存在安全风险。

**修复建议**: 使用更严格的路径验证：
```python
import re
safe_uid = re.sub(r'[^a-zA-Z0-9_]', '', user_id.replace("USER_", ""))
```

---

### 🟡 ISSUE-010: 授权码激活后 Cookie 中存储了明文授权码

**文件**: [auth_routes.py](file:///d:/aipic/backend/api/auth_routes.py#L18-L20)

**问题描述**:
```python
response.set_cookie("user_id", result['data']['user_id'], max_age=86400 * 30, httponly=True, samesite="lax")
response.set_cookie("auth_code", auth_code, max_age=86400 * 30, httponly=True, samesite="lax")
```
授权码以明文形式存储在 Cookie 中，有效期 30 天。虽然设置了 `httponly=True`，但如果存在 XSS 漏洞，攻击者仍可能通过其他方式获取。

**影响**: 授权码泄露可能导致账号被他人使用。

**修复建议**: 
1. 不在 Cookie 中存储授权码，只存储 `user_id`
2. 服务端通过 `user_id` 查询关联的授权码进行验证
3. 或者对授权码进行哈希后存储

---

### 🟡 ISSUE-011: 内容过滤器关键词列表为空，实际上没有内容过滤

**文件**: [config.py](file:///d:/aipic/backend/core/config.py#L62-L63)

**问题描述**:
```python
CONTENT_FILTER_ENABLED = True
CONTENT_FILTER_KEYWORDS = []
```
虽然 `CONTENT_FILTER_ENABLED` 为 `True`，但关键词列表为空，实际上不会过滤任何内容。

**影响**: 用户可以使用任何提示词生成图片，包括可能违规的内容。

**修复建议**: 添加敏感词列表，或接入第三方内容审核 API。

---

### 🟡 ISSUE-012: 全局配置表只有一行数据但使用 id=1 硬编码

**文件**: [database.py](file:///d:/aipic/backend/core/database.py#L38-L46)

**问题描述**:
```python
CREATE TABLE IF NOT EXISTS global_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    ...
)
```
全局配置表设计为只有一行数据，使用 `CHECK (id = 1)` 约束。这种设计虽然简单，但缺乏扩展性。

**影响**: 如果未来需要添加更多配置项，需要修改表结构。

**修复建议**: 考虑使用 key-value 模式存储配置：
```sql
CREATE TABLE global_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
```

---

### 🟡 ISSUE-013: 生图队列没有最大队列长度限制

**文件**: [generate_routes.py](file:///d:/aipic/backend/api/generate_routes.py#L82-L97)

**问题描述**:
虽然配置中有 `MAX_QUEUE_SIZE = 1000`，但在提交生图任务时没有检查当前队列长度：
```python
cursor.execute("SELECT MAX(queue_order) FROM global_generate_queue WHERE task_status = '待执行'")
max_order = cursor.fetchone()[0]
queue_order = (max_order or 0) + 1
```
没有检查 `queue_order` 是否超过 `MAX_QUEUE_SIZE`。

**影响**: 如果大量用户同时提交任务，队列可能无限增长，导致系统资源耗尽。

**修复建议**: 在提交任务前检查队列长度：
```python
cursor.execute("SELECT COUNT(*) FROM global_generate_queue WHERE task_status = '待执行'")
queue_count = cursor.fetchone()[0]
if queue_count >= MAX_QUEUE_SIZE:
    return {"code": 429, "msg": "队列已满，请稍后再试", "data": None}
```

---

### 🟡 ISSUE-014: 用户作品删除时只删除了数据库记录，没有验证文件所有权

**文件**: [user_routes.py](file:///d:/aipic/backend/api/user_routes.py#L79-L95)

**问题描述**:
```python
@router.delete("/works/{work_id}")
async def delete_work(request: Request, work_id: int, current_user: dict = Depends(get_current_user)):
    with get_user_db_conn(current_user['user_id']) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_works WHERE id = ?", (work_id,))
        work = cursor.fetchone()
        ...
        image_path = work['output_image_path']
        cursor.execute("DELETE FROM user_works WHERE id = ?", (work_id,))
```
虽然每个用户有独立的数据库，但如果数据库被篡改或存在其他漏洞，用户可能删除其他用户的作品文件。

**影响**: 潜在的文件删除风险。

**修复建议**: 在删除文件前验证文件路径是否在用户的输出目录内。

---

### 🟡 ISSUE-015: 管理员初始化接口没有速率限制

**文件**: [admin_routes.py](file:///d:/aipic/backend/api/admin_routes.py#L197-L222)

**问题描述**:
```python
@router.post("/init_admin")
async def init_admin(request: Request):
```
管理员初始化接口没有 `@rate_limit` 装饰器，可以被无限次调用。

**影响**: 虽然接口有"管理员已存在"的检查，但仍然可以被暴力尝试。

**修复建议**: 添加速率限制：
```python
@router.post("/init_admin")
@rate_limit(limit=5, time_window=300)
async def init_admin(request: Request):
```

---

###  ISSUE-016: 授权码批量生成接口没有去重检查

**文件**: [admin_routes.py](file:///d:/aipic/backend/api/admin_routes.py#L416-L453)

**问题描述**:
批量生成授权码时，每个授权码独立生成，没有检查是否与已有授权码重复：
```python
for _ in range(count):
    code = create_auth_code()
    cursor.execute('INSERT INTO global_auth_codes ...', (code, ...))
```
虽然 `auth_code` 是主键，插入重复值会失败，但没有优雅的错误处理。

**影响**: 如果发生冲突（虽然概率极低），整个批量生成操作会失败。

**修复建议**: 添加冲突检测和重试机制。

---

### 🟢 ISSUE-017: 前端粒子系统没有清理机制，可能导致内存泄漏

**文件**: [index.js](file:///d:/aipic/backend/static/js/index.js#L45-L195)

**问题描述**:
`ParticleSystem` 类有 `destroy()` 方法，但在页面导航时没有调用：
```javascript
function navigateTo(page) {
    ...
    if (page === 'login' && loginParticles) {
        setTimeout(() => loginParticles.resize(), 100);
    }
}
```
切换页面时没有销毁不需要的粒子系统。

**影响**: 长时间使用后可能导致内存占用增加。

**修复建议**: 在页面切换时调用 `destroy()` 方法清理不需要的粒子系统。

---

### 🟢 ISSUE-018: 前端使用 alert() 显示错误信息，用户体验不佳

**文件**: [index.js](file:///d:/aipic/backend/static/js/index.js#L595)

**问题描述**:
```javascript
alert(res.msg);
```
多处使用 `alert()` 显示错误信息，阻塞用户操作且样式不统一。

**影响**: 用户体验不一致，移动端 alert 显示效果差。

**修复建议**: 使用统一的 Toast/Notification 组件替代 alert。

---

### 🟢 ISSUE-019: 前端没有处理 API 请求超时

**文件**: [index.js](file:///d:/aipic/backend/static/js/index.js)

**问题描述**:
前端 API 调用没有设置超时时间：
```javascript
async function apiPost(url, data) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    return await res.json();
}
```

**影响**: 如果服务器响应慢或无响应，用户界面会一直等待。

**修复建议**: 添加超时控制：
```javascript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000);
const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    signal: controller.signal,
});
clearTimeout(timeoutId);
```

---

### 🟢 ISSUE-020: 数据库 WAL 模式没有配置检查点阈值

**文件**: [database.py](file:///d:/aipic/backend/core/database.py#L21)

**问题描述**:
```python
conn.execute("PRAGMA journal_mode=WAL")
```
启用了 WAL 模式但没有配置 `wal_autocheckpoint`，可能导致 WAL 文件无限增长。

**影响**: 长时间运行后 WAL 文件可能占用大量磁盘空间。

**修复建议**: 添加自动检查点配置：
```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA wal_autocheckpoint=1000")
```

---

### 🟢 ISSUE-021: 前端导航没有处理页面加载失败的情况

**文件**: [index.js](file:///d:/aipic/backend/static/js/index.js#L470-L502)

**问题描述**:
`navigateTo()` 函数假设所有页面元素都存在，没有处理元素不存在的情况。

**影响**: 如果 HTML 结构变化，导航可能静默失败。

**修复建议**: 添加元素存在性检查和错误处理。

---

###  ISSUE-022: 环境变量没有默认值保护

**文件**: [config.py](file:///d:/aipic/backend/core/config.py#L16)

**问题描述**:
```python
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
```
如果 `OPENAI_API_KEY` 未设置，系统会使用空字符串，导致生图功能完全失效但没有明确的错误提示。

**影响**: 部署时如果忘记设置 API Key，系统会静默失败。

**修复建议**: 在应用启动时检查关键环境变量：
```python
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY 环境变量未设置")
```

---

## 修复优先级建议

| 优先级 | 问题编号 | 修复难度 | 影响范围 |
|--------|----------|----------|----------|
| P0 | ISSUE-001, 002, 003 | 中 | 核心安全 |
| P1 | ISSUE-004, 006, 007 | 低 | 安全/性能 |
| P2 | ISSUE-008, 009, 010, 013 | 中 | 用户体验/安全 |
| P3 | ISSUE-011, 012, 014, 015, 016 | 低 | 功能完善 |
| P4 | ISSUE-017 ~ 022 | 低 | 代码质量 |

---

## 总结

本次审计共发现 **22 个问题**，其中：
- **3 个严重问题**：主要涉及会话管理和速率限制的持久化问题
- **5 个高危问题**：涉及 CORS 配置、IP 记录、数据库性能等
- **8 个中危问题**：涉及内容过滤、队列限制、路径安全等
- **6 个低危问题**：涉及前端体验、代码质量等

**最关键的修复项**：
1. 将管理员会话密钥持久化到环境变量
2. 将速率限制和用户冻结状态迁移到 Redis 或 SQLite
3. 修复管理员操作日志的 IP 记录问题
4. 添加生图队列长度限制
