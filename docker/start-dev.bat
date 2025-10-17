# 开发环境快速启动脚本（Windows）
@echo off
chcp 65001 >nul 2>&1

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

echo ======================================
echo OpenServerHub 开发环境启动脚本（Windows）
echo ======================================
echo.
echo 开发环境配置：
echo - 数据库: SQLite (本地文件)
echo - 前端: http://localhost:3000
echo - 后端: http://localhost:8000
echo.

:check_docker
echo 正在检查Docker环境...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Docker未安装
    pause
    exit /b 1
)

REM 检查Docker Compose（支持docker-compose和docker compose两种命令）
set DOCKER_COMPOSE_CMD=
docker-compose --version >nul 2>&1
if %errorlevel% equ 0 (
    set DOCKER_COMPOSE_CMD=docker-compose
    goto docker_compose_found
)

docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    set DOCKER_COMPOSE_CMD=docker compose
    goto docker_compose_found
)

echo 错误: Docker Compose未安装（需要docker-compose或docker compose命令）
pause
exit /b 1

:docker_compose_found
echo √ Docker环境检查通过
echo ℹ 开发环境配置：SQLite + 热重载
echo ℹ 使用命令: %DOCKER_COMPOSE_CMD%
echo.

:start_dev
echo 正在启动开发环境...
cd /d "%SCRIPT_DIR%"

rem 创建数据目录
if not exist "%PROJECT_ROOT%\backend\data" mkdir "%PROJECT_ROOT%\backend\data"

rem 启动服务
%DOCKER_COMPOSE_CMD% -f docker-compose.dev.sqlite.yml up -d

if %errorlevel% equ 0 (
    echo √ 开发环境启动成功！
    echo.
    echo 服务地址:
    echo - 前端开发服务器: http://localhost:3000
    echo - 后端API: http://localhost:8000
    echo - API文档: http://localhost:8000/docs
    echo - 数据库: SQLite (本地文件)
    echo.
    echo 使用说明:
    echo - 代码修改后自动热重载
    echo - 后端日志: docker logs -f openserverhub-backend-dev
    echo - 前端日志: docker logs -f openserverhub-frontend-dev
) else (
    echo 错误: 开发环境启动失败
)
pause
exit /b 0

:stop_dev
echo 正在停止开发环境...
cd /d "%SCRIPT_DIR%"
%DOCKER_COMPOSE_CMD% -f docker-compose.dev.sqlite.yml down
echo √ 开发环境已停止
pause
exit /b 0

:logs_all
cd /d "%SCRIPT_DIR%"
%DOCKER_COMPOSE_CMD% -f docker-compose.dev.sqlite.yml logs -f
exit /b 0

:logs_backend
docker logs -f openserverhub-backend-dev
exit /b 0

:logs_frontend
docker logs -f openserverhub-frontend-dev
exit /b 0

:cleanup
echo 正在清理开发环境...
cd /d "%SCRIPT_DIR%"
%DOCKER_COMPOSE_CMD% -f docker-compose.dev.sqlite.yml down -v --remove-orphans
echo √ 开发环境已清理
pause
exit /b 0

:menu
echo.
echo 请选择操作:
echo 1) 启动开发环境
echo 2) 停止开发环境
echo 3) 查看日志
echo 4) 清理环境
echo 5) 退出
echo.
set /p choice=请输入选项 (1-5): 

if "%choice%"=="1" goto start_dev
if "%choice%"=="2" goto stop_dev
if "%choice%"=="3" goto logs_menu
if "%choice%"=="4" goto cleanup
if "%choice%"=="5" exit /b 0

echo 无效选项，请重新输入
goto menu

:logs_menu
echo.
echo 选择日志类型:
echo 1) 所有服务
echo 2) 后端服务
echo 3) 前端服务
echo 4) 返回主菜单
echo.
set /p log_choice=请输入选项 (1-4): 

if "%log_choice%"=="1" goto logs_all
if "%log_choice%"=="2" goto logs_backend
if "%log_choice%"=="3" goto logs_frontend
if "%log_choice%"=="4" goto menu

echo 无效选项，请重新输入
goto logs_menu

rem 直接运行脚本时显示菜单
goto menu