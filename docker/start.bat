@echo off
REM OpenServerHub Docker 快速启动脚本（Windows）

echo 🚀 OpenServerHub Docker 部署启动器
echo ==================================

REM 检查Docker
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Docker 未安装，请先安装 Docker
    pause
    exit /b 1
)

REM 检查Docker Compose
where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Docker Compose 未安装，请先安装 Docker Compose
    pause
    exit /b 1
)

REM 检查环境文件
if not exist .env (
    echo ⚠️  未找到 .env 文件，正在创建...
    copy .env.example .env
    echo 📝 请编辑 .env 文件以配置您的环境
    pause
)

REM 选择部署模式
echo 请选择部署模式：
echo 1) 生产环境 (Production)
echo 2) 开发环境 (Development)
echo 3) 监控环境 (Monitoring)
echo 4) 停止所有服务
echo 5) 查看日志
echo 6) 数据备份（仅生产环境）
echo 7) 数据恢复（仅生产环境）
set /p choice=请输入选项 (1-7): 

if "%choice%"=="1" goto :production
if "%choice%"=="2" goto :development
if "%choice%"=="3" goto :monitoring
if "%choice%"=="4" goto :stop
if "%choice%"=="5" goto :logs
if "%choice%"=="6" goto :backup
if "%choice%"=="7" goto :restore
echo ❌ 无效选项！
pause
exit /b 1

:production
echo 🏭 正在启动生产环境...
docker-compose up -d
echo ✅ 生产环境已启动！
echo 🌐 前端地址: http://localhost
echo 🔧 API地址: http://localhost:8000
echo 📚 API文档: http://localhost:8000/docs
goto :end

:development
echo 🔧 正在启动开发环境...
REM 检查开发环境的.env文件
if not exist .env.dev (
    echo ⚠️  未找到开发环境的 .env.dev 文件，正在创建...
    copy .env.dev.example .env.dev
    echo 📝 请编辑 .env.dev 文件以配置您的开发环境
    pause
)
docker-compose -f docker-compose.dev.yml up -d
echo ✅ 开发环境已启动！
echo 🌐 前端地址: http://localhost:3000
echo 🔧 API地址: http://localhost:8000
goto :end

:monitoring
echo 📊 正在启动监控环境...
docker-compose -f docker-compose.monitoring.yml up -d
echo ✅ 监控环境已启动！
echo 📈 Prometheus: http://localhost:9090
echo 📊 Grafana: http://localhost:3001
echo ⚠️  AlertManager: http://localhost:9093
goto :end

:stop
echo 🛑 正在停止所有服务...
docker-compose down
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.monitoring.yml down
echo ✅ 所有服务已停止！
goto :end

:logs
echo 📋 选择服务查看日志：
echo 1) 所有服务（生产环境）
echo 2) 后端服务
echo 3) 前端服务
echo 4) 数据库（仅生产环境）
echo 5) 监控服务
set /p log_choice=请输入选项 (1-5): 

if "%log_choice%"=="1" docker-compose logs -f
if "%log_choice%"=="2" docker-compose logs -f backend
if "%log_choice%"=="3" docker-compose logs -f frontend
if "%log_choice%"=="4" docker-compose logs -f postgres
if "%log_choice%"=="5" docker-compose -f docker-compose.monitoring.yml logs -f
goto :end

:backup
echo 💾 正在备份数据（仅适用于生产环境）...
set backup_file=backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sql
docker-compose exec postgres pg_dump -U postgres openserverhub > "%backup_file%"
echo ✅ 数据备份完成: %backup_file%
goto :end

:restore
echo 📂 可用的备份文件（仅适用于生产环境）：
dir /b backup_*.sql 2>nul || echo 未找到备份文件
set /p backup_file=请输入备份文件名: 
if exist "%backup_file%" (
    echo 📥 正在恢复数据...
    docker-compose exec -T postgres psql -U postgres openserverhub < "%backup_file%"
    echo ✅ 数据恢复完成！
) else (
    echo ❌ 备份文件不存在！
)
goto :end

:end
echo.
echo 🎉 操作完成！
echo ==================================
pause