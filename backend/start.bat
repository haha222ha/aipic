@echo off
chcp 65001 >nul
echo ================================
echo   AI智能作图系统 启动脚本
echo ================================
echo.

cd /d "%~dp0"

if not exist "venv" (
    echo 正在创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo 正在安装依赖...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo 正在启动服务...
python main.py

pause
