@echo off
REM 单容器开发环境快速启动脚本（Windows）

setlocal enabledelayedexpansion

REM 脚本目录
cd /d "%~dp0"
set SCRIPT_DIR=%cd%
cd ..
set PROJECT_ROOT=%cd%
cd /d "%~dp0"

echo OpenServerHub 单容器开发环境启动脚本
echo ========================================
echo 开发环境配置：
echo - 数据库: SQLite (本地文件)
echo - 架构: 单容器（后端+前端）
echo - 前端: http://localhost:3000
echo - 后端: http://localhost:8000
echo.

REM 检查Docker环境
call :check_docker
if %errorlevel% neq 0 (
    pause
    exit /b 1
)

REM 主菜单
:menu
echo.
echo 请选择操作:
echo 1) 启动单容器开发环境
echo 2) 停止单容器开发环境
echo 3) 查看容器日志
echo 4) 进入容器Shell
echo 5) 清理环境
echo 6) 退出
echo.
set /p choice=请输入选项 (1-6): 

if "%choice%"=="1" goto start_dev
if "%choice%"=="2" goto stop_dev
if "%choice%"=="3" goto logs
if "%choice%"=="4" goto shell
if "%choice%"=="5" goto cleanup
if "%choice%"=="6" goto exit_script

echo 无效选项，请重新输入
goto menu

REM 检查Docker环境
:check_docker
echo 正在检查Docker环境...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Docker未安装
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Docker Compose未安装
    exit /b 1
)
echo √ Docker环境检查通过
echo ℹ 单容器开发环境配置：SQLite + 热重载
exit /b 0

REM 启动开发环境
:start_dev
echo 正在启动单容器开发环境...

REM 创建数据目录
if not exist "%PROJECT_ROOT%\backend\data" mkdir "%PROJECT_ROOT%\backend\data"

REM 启动单容器服务
docker-compose -f docker-compose.dev.single.yml up -d
if %errorlevel% neq 0 (
    echo 错误: 启动失败
    pause
    goto menu
)

echo √ 单容器开发环境启动成功！
echo.
echo 服务地址:
echo - 前端开发服务器: http://localhost:3000
echo - 后端API: http://localhost:8000
echo - API文档: http://localhost:8000/docs
echo - 数据库: SQLite (本地文件)
echo.
echo 使用说明:
echo - 代码修改后自动热重载
echo - 容器日志: docker logs -f openserverhub-dev
echo - 进入容器: docker exec -it openserverhub-dev sh
echo.
pause
goto menu

REM 停止开发环境
:stop_dev
echo 正在停止单容器开发环境...
docker-compose -f docker-compose.dev.single.yml down --remove-orphans
echo √ 单容器开发环境已停止
echo.
pause
goto menu

REM 查看日志
:logs
docker logs -f openserverhub-dev
goto menu

REM 进入容器
:shell
docker exec -it openserverhub-dev sh
goto menu

REM 清理环境
:cleanup
echo 正在清理单容器开发环境...
docker-compose -f docker-compose.dev.single.yml down -v --remove-orphans
echo √ 单容器开发环境已清理
echo.
pause
goto menu

REM 退出
:exit_script
echo 再见！
exit /b 0