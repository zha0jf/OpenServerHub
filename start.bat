@echo off
echo ====================================
echo OpenServerHub 启动脚本
echo ====================================

REM 设置PowerShell执行策略以允许脚本运行
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force" >nul 2>&1

REM 设置文件句柄限制（Windows中通过PowerShell）
powershell -Command "[System.Threading.Thread]::CurrentThread.Priority = 'Highest'" >nul 2>&1

echo.
echo 1. 启动后端服务...
cd /d "%~dp0backend"

:: 检查是否已安装依赖
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 安装依赖
echo 安装后端依赖...
pip install -r requirements.txt

:: 复制环境配置
if not exist ".env" (
    copy .env.example .env
    echo 已创建环境配置文件，请根据需要修改 backend/.env
)

:: 初始化数据库
echo 初始化数据库...
python init_db.py

:: 启动后端服务
echo 启动后端服务...
start "OpenServerHub Backend" cmd /k "uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo 2. 启动前端服务...
cd /d "%~dp0frontend"

:: 安装前端依赖
echo 安装前端依赖...
call npm install

:: 启动前端服务
echo 启动前端服务...
start "OpenServerHub Frontend" cmd /k "npm start"

echo.
echo ====================================
echo 启动完成！
echo 前端地址: http://localhost:3000
echo 后端API: http://localhost:8000  
echo API文档: http://localhost:8000/docs
echo 默认账号: admin / admin123
echo ====================================
echo.
pause