@echo off
title OpenServerHub 生产环境启动器 (SQLite版本)

echo 🚀 OpenServerHub 生产环境启动器 (SQLite版本)
echo ==========================================

REM 检查Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker 未安装，请先安装 Docker
    pause
    exit /b 1
)

REM 检查Docker Compose
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose 未安装，请先安装 Docker Compose
    pause
    exit /b 1
)

REM 检查环境文件
if not exist .env.prod (
    echo ⚠️  未找到生产环境的 .env.prod 文件，正在创建...
    copy .env.example .env.prod >nul
    echo 📝 请编辑 .env.prod 文件以配置您的生产环境
    echo    特别注意修改 SECRET_KEY 等安全配置
    pause
)

echo 请选择操作：
echo 1) 启动生产环境
echo 2) 停止生产环境
echo 3) 重启生产环境
echo 4) 查看服务状态
echo 5) 查看日志
echo 6) 初始化数据库
echo 7) 备份数据库
echo 8) 恢复数据库
set /p choice=请输入选项 (1-8): 

if "%choice%"=="1" (
    echo 🏭 正在启动生产环境...
    docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod up -d
    echo ✅ 生产环境已启动！
    echo 🌐 应用地址: http://localhost:8000
    echo 🔧 API文档: http://localhost:8000/docs
    echo 📊 监控面板: http://localhost:3001
) else if "%choice%"=="2" (
    echo 🛑 正在停止生产环境...
    docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod down
    echo ✅ 生产环境已停止！
) else if "%choice%"=="3" (
    echo 🔄 正在重启生产环境...
    docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod down
    timeout /t 3 /nobreak >nul
    docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod up -d
    echo ✅ 生产环境已重启！
    echo 🌐 应用地址: http://localhost:8000
    echo 🔧 API文档: http://localhost:8000/docs
    echo 📊 监控面板: http://localhost:3001
) else if "%choice%"=="4" (
    echo 📋 服务状态：
    docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod ps
) else if "%choice%"=="5" (
    echo 📋 选择服务查看日志：
    echo 1) 所有服务
    echo 2) 后端服务
    echo 3) Prometheus
    echo 4) Grafana
    echo 5) AlertManager
    echo 6) IPMI Exporter
    set /p log_choice=请输入选项 (1-6): 
    
    if "%log_choice%"=="1" (
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f
    ) else if "%log_choice%"=="2" (
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f backend
    ) else if "%log_choice%"=="3" (
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f prometheus
    ) else if "%log_choice%"=="4" (
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f grafana
    ) else if "%log_choice%"=="5" (
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f alertmanager
    ) else if "%log_choice%"=="6" (
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f ipmi-exporter
    ) else (
        echo 无效选项
    )
) else if "%choice%"=="6" (
    echo 💾 正在初始化数据库...
    docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod exec backend sh -c "cd /app/backend && python init_db.py"
    echo ✅ 数据库初始化完成！
) else if "%choice%"=="7" (
    echo 💾 正在备份数据库...
    REM 获取当前时间戳
    for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
    set backup_file=backup_%dt:~0,8%_%dt:~8,6%.db
    docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod exec backend cp /app/data/openserverhub.db /app/data/%backup_file%
    docker cp openserverhub-backend-prod:/app/data/%backup_file% ./%backup_file%
    echo ✅ 数据库备份完成: %backup_file%
) else if "%choice%"=="8" (
    echo 📂 可用的备份文件：
    dir backup_*.db 2>nul | findstr .db || echo 未找到备份文件
    set /p backup_file=请输入备份文件名: 
    if exist "%backup_file%" (
        echo 📥 正在恢复数据库...
        docker cp ./%backup_file% openserverhub-backend-prod:/app/data/openserverhub.db
        echo ✅ 数据库恢复完成！
        echo ⚠️  建议重启服务以确保数据一致性
    ) else (
        echo ❌ 备份文件不存在！
    )
) else (
    echo ❌ 无效选项！
    pause
    exit /b 1
)

echo.
echo 🎉 操作完成！
echo ==========================================
pause