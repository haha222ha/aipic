#!/bin/bash
set -e

APP_DIR="/opt/aipic"
REPO_URL="https://github.com/haha222ha/aipic.git"
BRANCH="master"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="aipic"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "请使用 sudo 运行此脚本"
    fi
}

install_dependencies() {
    info "安装系统依赖..."
    apt-get update
    apt-get install -y python3 python3-pip python3-venv git nginx
}

clone_repo() {
    if [ -z "$REPO_URL" ]; then
        error "请先在脚本中设置 REPO_URL 变量"
    fi

    if [ -d "$APP_DIR" ]; then
        warn "$APP_DIR 已存在，跳过克隆"
        return
    fi

    info "克隆代码仓库..."
    git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
}

setup_venv() {
    info "创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r "$APP_DIR/backend/requirements.txt"
}

setup_env() {
    if [ -f "$APP_DIR/backend/.env" ]; then
        warn ".env 文件已存在，跳过创建"
        return
    fi

    info "创建 .env 配置文件..."
    cp "$APP_DIR/backend/.env.example" "$APP_DIR/backend/.env"
    warn "请编辑 $APP_DIR/backend/.env 填写实际配置（API Key 等）"
}

setup_directories() {
    info "创建必要目录..."
    mkdir -p "$APP_DIR/backend/outputs"
    mkdir -p "$APP_DIR/backend/temp"
    mkdir -p "$APP_DIR/backend/user_data"
    mkdir -p "$APP_DIR/backend/logs"
    chown -R www-data:www-data "$APP_DIR/backend/outputs"
    chown -R www-data:www-data "$APP_DIR/backend/temp"
    chown -R www-data:www-data "$APP_DIR/backend/user_data"
    chown -R www-data:www-data "$APP_DIR/backend/logs"
    chown -R www-data:www-data "$APP_DIR/backend/global_config.db" 2>/dev/null || true
}

setup_systemd() {
    info "配置 systemd 服务..."
    cp "$APP_DIR/backend/deploy/aipic.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    info "服务已注册（暂未启动，请先配置 .env 后运行: sudo systemctl start aipic）"
}

setup_nginx() {
    info "配置 Nginx..."
    cp "$APP_DIR/backend/deploy/nginx_aipic.conf" /etc/nginx/sites-available/aipic
    ln -sf /etc/nginx/sites-available/aipic /etc/nginx/sites-enabled/
    nginx -t && info "Nginx 配置验证通过" || error "Nginx 配置有误"
    systemctl reload nginx
}

do_deploy() {
    info "========== 首次部署 =========="
    check_root
    install_dependencies
    clone_repo
    setup_venv
    setup_env
    setup_directories
    setup_systemd
    setup_nginx
    info "========== 部署完成 =========="
    echo ""
    echo "后续步骤："
    echo "  1. 编辑 .env:  nano $APP_DIR/backend/.env"
    echo "  2. 启动服务:    sudo systemctl start aipic"
    echo "  3. 查看状态:    sudo systemctl status aipic"
    echo "  4. 查看日志:    sudo journalctl -u aipic -f"
    echo "  5. Cloudflare:  添加 pic.xhs365.cn A 记录指向服务器IP"
}

do_update() {
    info "========== 更新部署 =========="
    check_root

    cd "$APP_DIR"
    info "拉取最新代码..."
    git pull origin "$BRANCH"

    info "更新依赖..."
    "$VENV_DIR/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

    info "重启服务..."
    systemctl restart "$SERVICE_NAME"

    info "========== 更新完成 =========="
    systemctl status "$SERVICE_NAME" --no-pager
}

do_status() {
    systemctl status "$SERVICE_NAME" --no-pager
    echo ""
    echo "最近日志:"
    journalctl -u "$SERVICE_NAME" -n 20 --no-pager
}

case "${1:-deploy}" in
    deploy)  do_deploy  ;;
    update)  do_update  ;;
    status)  do_status  ;;
    *)
        echo "用法: $0 {deploy|update|status}"
        echo "  deploy  - 首次部署"
        echo "  update  - 更新代码并重启"
        echo "  status  - 查看服务状态"
        exit 1
        ;;
esac
