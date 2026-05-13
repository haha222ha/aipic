# AI智能作图系统 - 服务器部署更新指南

> **AI 读取须知**：本项目的部署流程是 **本地开发 → git push 到 GitHub → 服务器 git pull → 重启服务**。
> 任何代码修改都必须先在本地提交并推送到 GitHub，服务器才能拉取到最新代码。
> 服务器上直接修改代码不会被保留，所有变更必须通过 Git 仓库同步。

## 系统信息

| 项目 | 值 |
|------|-----|
| 域名 | pic.xhs365.cn |
| 服务器部署路径 | /opt/aipic |
| Git仓库 | https://github.com/haha222ha/aipic.git |
| 分支 | master |
| 服务端口 | 8800 |
| 反向代理 | Nginx → 127.0.0.1:8800 |
| CDN/SSL | Cloudflare（DNS代理模式，自动HTTPS） |
| 进程管理 | systemd (aipic.service) |
| 运行用户 | www-data |

## 架构概览

```
用户浏览器
    ↓ HTTPS (Cloudflare CDN)
pic.xhs365.cn
    ↓ HTTP (Cloudflare → 源站)
Nginx (:80)
    ↓ proxy_pass
Uvicorn (:8800, 2 workers)
    ↓
FastAPI 应用
    ├── /api/auth/*      授权模块
    ├── /api/generate/*  生图模块
    ├── /api/user/*      用户模块
    └── /api/admin/*     管理模块
```

## ⚠️ 部署流程（重要）

**任何代码修改后，必须按以下顺序操作，缺一不可：**

```
┌─────────────────────────────────────────────────────────┐
│  第1步：本地修改代码                                       │
│  第2步：本地 git add + git commit + git push origin master│
│  第3步：SSH 到服务器执行更新命令                            │
│  第4步：验证服务状态                                       │
└─────────────────────────────────────────────────────────┘
```

**如果跳过第2步直接在第3步执行更新，服务器会显示 `Already up to date.`，拉不到任何新代码。**

### 完整更新命令

**第2步 - 本地推送（在开发机执行）：**

```bash
git add -A
git commit -m "描述本次修改内容"
git push origin master
```

**第3步 - 服务器更新（SSH 到服务器执行）：**

```bash
# 方式一：使用部署脚本（推荐）
sudo bash /opt/aipic/backend/deploy/deploy.sh update

# 方式二：手动执行
cd /opt/aipic
sudo git pull origin master
sudo /opt/aipic/venv/bin/pip install -r /opt/aipic/backend/requirements.txt
sudo systemctl restart aipic
sudo systemctl status aipic
```

**第4步 - 验证：**

```bash
# 检查服务是否正常运行
sudo systemctl status aipic

# 查看启动日志确认无报错
sudo journalctl -u aipic -n 30 --no-pager

# 浏览器访问 https://pic.xhs365.cn 验证功能
# 如页面未更新，按 Ctrl+Shift+R 强制刷新浏览器缓存
```

### 更新后浏览器缓存问题

静态文件（JS/CSS/HTML）更新后，浏览器可能使用旧缓存。解决方式：
- 用户端：**Ctrl+Shift+R** 强制刷新
- 如需全局生效：在 Nginx 配置中缩短静态文件缓存时间，或在静态文件 URL 添加版本号参数

## 首次部署

### 1. 服务器准备

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv git nginx
```

### 2. 克隆代码

```bash
sudo git clone -b master https://github.com/haha222ha/aipic.git /opt/aipic
```

### 3. 创建虚拟环境并安装依赖

```bash
sudo python3 -m venv /opt/aipic/venv
sudo /opt/aipic/venv/bin/pip install --upgrade pip
sudo /opt/aipic/venv/bin/pip install -r /opt/aipic/backend/requirements.txt
```

### 4. 配置环境变量

```bash
sudo cp /opt/aipic/backend/.env.example /opt/aipic/backend/.env
sudo nano /opt/aipic/backend/.env
```

`.env` 内容：

```env
SERVER_HOST=0.0.0.0
SERVER_PORT=8800

OPENAI_API_KEY=sk-你的实际API密钥
OPENAI_BASE_URL=https://www.packyapi.com/v1

CORS_ORIGINS=https://pic.xhs365.cn,http://pic.xhs365.cn
```

### 5. 创建必要目录并设置权限

```bash
sudo mkdir -p /opt/aipic/backend/outputs
sudo mkdir -p /opt/aipic/backend/temp
sudo mkdir -p /opt/aipic/backend/user_data
sudo mkdir -p /opt/aipic/backend/logs

sudo chown -R www-data:www-data /opt/aipic/backend/outputs
sudo chown -R www-data:www-data /opt/aipic/backend/temp
sudo chown -R www-data:www-data /opt/aipic/backend/user_data
sudo chown -R www-data:www-data /opt/aipic/backend/logs
sudo chown -R www-data:www-data /opt/aipic/backend/global_config.db 2>/dev/null || true
```

### 6. 配置 systemd 服务

```bash
sudo cp /opt/aipic/backend/deploy/aipic.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable aipic
```

### 7. 配置 Nginx

```bash
sudo cp /opt/aipic/backend/deploy/nginx_aipic.conf /etc/nginx/sites-available/aipic
sudo ln -sf /etc/nginx/sites-available/aipic /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 8. Cloudflare DNS 配置

| 类型 | 名称 | 内容 | 代理状态 |
|------|------|------|----------|
| A | pic | 服务器IP | 已代理（橙色云朵） |

SSL/TLS 设置：加密模式 **完全（严格）**

### 9. 启动服务

```bash
sudo systemctl start aipic
sudo systemctl status aipic
```

### 10. 创建管理员账号

```bash
cd /opt/aipic/backend
sudo /opt/aipic/venv/bin/python scripts/create_admin.py
```

## 常用运维命令

```bash
sudo systemctl status aipic          # 查看服务状态
sudo systemctl restart aipic         # 重启服务
sudo systemctl stop aipic            # 停止服务
sudo journalctl -u aipic -f         # 实时日志
sudo journalctl -u aipic -n 50      # 最近50行日志
sudo nginx -t                        # 检查 Nginx 配置
sudo systemctl reload nginx          # 重新加载 Nginx
sudo tail -f /var/log/nginx/aipic_access.log   # Nginx 访问日志
sudo tail -f /var/log/nginx/aipic_error.log    # Nginx 错误日志
```

数据库相关：

```bash
cd /opt/aipic/backend
sudo /opt/aipic/venv/bin/python scripts/check_db.py    # 查看数据库
```

## 注意事项

1. **数据库备份**：更新前建议备份数据库
   ```bash
   sudo cp /opt/aipic/backend/global_config.db /opt/aipic/backend/global_config.db.bak.$(date +%Y%m%d)
   sudo cp -r /opt/aipic/backend/user_data /opt/aipic/backend/user_data.bak.$(date +%Y%m%d)
   ```

2. **Cookie secure 问题**：Cloudflare 以 HTTPS 接收用户请求，但 Cloudflare 到源站走 HTTP，Uvicorn 收到的 `request.url.scheme` 是 `http`。当前代码根据 scheme 动态决定 `secure` 参数，HTTP 下为 False，HTTPS 下为 True。

3. **CORS 配置**：`.env` 中的 `CORS_ORIGINS` 必须包含 `https://pic.xhs365.cn`，否则跨域请求被拒绝。

4. **Cloudflare SSL 模式**：必须设置为"完全（严格）"，否则出现重定向循环。

5. **文件权限**：运行时产生的文件（outputs、temp、user_data、数据库）必须归 `www-data` 用户所有。

6. **套餐名称一致性**：后端 `PACKAGES` 字典的 key（免费版、体验卡、基础版、专业版、旗舰版）必须与前端 HTML 中的 `<option value>` 完全一致，否则授权码生成会报"无效的套餐类型"。

## 已修复的历史 Bug 记录

### 2026-05-12 批量修复

| # | 问题 | 文件 | 根因 | 修复方式 |
|---|------|------|------|----------|
| 1 | 授权码激活成功却提示失败 | `index.js` | `studioCredits`/`creditsBar` DOM 元素不存在，TypeError 被 catch 捕获 | 对 DOM 元素添加空值检查 |
| 2 | 创作工坊"开始创作"没反应 | `index.js` | `getElementById('prompt')` 与 HTML 的 `promptInput` 不匹配 | 改为 `getElementById('promptInput')` |
| 3 | Cookie 在 HTTP 下无法保存 | `auth_routes.py` | `secure=True` 在 HTTP 下浏览器拒绝保存 Cookie | 根据 `request.url.scheme` 动态决定 |
| 4 | 体验卡授权码生成失败 | `admin.html` | 前端 `体验版` 与后端 `体验卡` 不匹配 | 统一为 `体验卡`，补充 `免费版` |
| 5 | 激活时积分重复添加 | `auth.py` | INSERT 和 add_credits 各加了一次积分 | INSERT 中 credits 设为 0 |
