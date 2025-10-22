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
echo - 架构: 单容器（后端+前端+监控组件）
echo - 前端: 端口 3000
echo - 后端: 端口 8000
echo - Prometheus: 端口 9090
echo - Grafana: 端口 3001
echo - AlertManager: 端口 9093
echo - IPMI Exporter: 端口 9290
echo - 访问地址: 根据环境配置自动确定（本地或远程）
echo.

REM 检查Docker环境
call :check_docker
if %errorlevel% neq 0 (
    pause
    exit /b 1
)

REM 检查环境配置文件
call :check_env_file
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
exit /b 1

:docker_compose_found
echo √ Docker环境检查通过
echo ℹ 单容器开发环境配置：SQLite + 热重载 + 监控组件
echo ℹ 使用命令: %DOCKER_COMPOSE_CMD%
exit /b 0

REM 检查环境配置文件
:check_env_file
echo 正在检查环境配置文件...

set ENV_FILE=%SCRIPT_DIR%\.env.dev
set ENV_EXAMPLE_FILE=%SCRIPT_DIR%\.env.dev.network

REM 如果环境配置文件不存在，尝试从示例文件创建
if not exist "%ENV_FILE%" (
    if exist "%ENV_EXAMPLE_FILE%" (
        echo 环境配置文件不存在，从示例文件创建...
        copy "%ENV_EXAMPLE_FILE%" "%ENV_FILE%" >nul
        echo √ 已创建环境配置文件: %ENV_FILE%
        echo ℹ 您可以编辑此文件修改服务器IP地址和其他配置
    ) else (
        echo 错误: 环境配置文件和示例文件都不存在
        exit /b 1
    )
)

REM 读取环境变量
call :read_env_file "%ENV_FILE%" SERVER_IP
call :read_env_file "%ENV_FILE%" REMOTE_ACCESS

REM 检查服务器IP配置
if "%SERVER_IP%"=="" (
    REM 如果SERVER_IP未设置，使用本地访问模式
    set SERVER_IP=127.0.0.1
    set REMOTE_ACCESS=false
    echo 未设置服务器IP地址，使用本地访问模式
) else if "%SERVER_IP%"=="127.0.0.1" (
    REM 如果SERVER_IP是本地地址，使用本地访问模式
    set REMOTE_ACCESS=false
    echo 检测到本地访问配置，服务器IP: %SERVER_IP%
) else if "%SERVER_IP%"=="localhost" (
    REM 如果SERVER_IP是本地地址，使用本地访问模式
    set REMOTE_ACCESS=false
    echo 检测到本地访问配置，服务器IP: %SERVER_IP%
) else (
    REM 其他情况都是远程访问模式，使用0.0.0.0监听所有接口
    set LISTEN_IP=0.0.0.0
    set REMOTE_ACCESS=true
    echo √ 检测到远程访问配置，将在所有IP上监听
    echo √ 配置的服务器IP: %SERVER_IP% (用于显示和访问)
)

exit /b 0

REM 读取环境变量文件中的值
:read_env_file
set "key_to_find=%~2"
set "value="
for /f "usebackq tokens=1,2 delims==" %%a in ("%~1") do (
    if "%%a"=="%key_to_find%" set "value=%%b"
)
set "%key_to_find%=%value%"
exit /b 0

REM 启动开发环境
:start_dev
echo 正在启动单容器开发环境...

REM 创建数据目录
if not exist "%PROJECT_ROOT%\backend\data" mkdir "%PROJECT_ROOT%\backend\data"

REM 创建临时环境变量文件
set TEMP_ENV_FILE=%SCRIPT_DIR%\.env.temp
(
    echo # 临时环境变量文件 - 由start-dev-single.bat自动生成
    echo SERVER_IP=%SERVER_IP%
    echo REMOTE_ACCESS=%REMOTE_ACCESS%
    echo LISTEN_IP=%LISTEN_IP%
    echo REACT_APP_API_URL=http://%SERVER_IP%:8000
    echo REACT_APP_WS_URL=ws://%SERVER_IP%:8000
    echo CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://%SERVER_IP%:3000
    echo DATABASE_URL=sqlite:///./openserverhub.db
    echo SECRET_KEY=your-secret-key-here-change-this-in-development
    echo ENVIRONMENT=development
    echo DEBUG=true
    echo LOG_LEVEL=DEBUG
    echo IPMI_TIMEOUT=30
    echo IPMI_RETRY_COUNT=3
    echo SCHEDULER_ENABLED=true
    echo POWER_STATE_REFRESH_INTERVAL=1
    echo MONITORING_ENABLED=true
    echo GRAFANA_API_KEY=your-grafana-api-key-here
    echo PROMETHEUS_TARGETS_PATH=/etc/prometheus/targets/ipmi-targets.json
) > "%TEMP_ENV_FILE%"

REM 启动单容器服务
%DOCKER_COMPOSE_CMD% -f docker-compose.dev.single.yml --env-file "%TEMP_ENV_FILE%" up -d
if %errorlevel% neq 0 (
    echo 错误: 启动失败
    del "%TEMP_ENV_FILE%" >nul 2>&1
    pause
    goto menu
)

REM 清理临时环境文件
del "%TEMP_ENV_FILE%" >nul 2>&1

echo √ 单容器开发环境启动成功！
echo.
echo 服务地址:

if "%REMOTE_ACCESS%"=="true" (
    echo - 前端开发服务器: http://%SERVER_IP%:3000
    echo - 后端API: http://%SERVER_IP%:8000
    echo - API文档: http://%SERVER_IP%:8000/docs
    echo - Prometheus: http://%SERVER_IP%:9090
    echo - Grafana: http://%SERVER_IP%:3001
    echo - AlertManager: http://%SERVER_IP%:9093
    echo - IPMI Exporter: http://%SERVER_IP%:9290
    echo.
    echo 远程访问模式:
    echo - 服务将在所有网络接口上监听 (0.0.0.0)
    echo - 您可以从网络中的其他计算机访问这些服务
    echo - 请确保防火墙已开放端口 3000, 8000, 9090, 3001, 9093, 9290
) else (
    echo - 前端开发服务器: http://localhost:3000
    echo - 后端API: http://localhost:8000
    echo - API文档: http://localhost:8000/docs
    echo - Prometheus: http://localhost:9090
    echo - Grafana: http://localhost:3001
    echo - AlertManager: http://localhost:9093
    echo - IPMI Exporter: http://localhost:9290
    echo.
    echo 本地访问模式:
    echo - 仅可在本机访问这些服务
    echo - 如需远程访问，请编辑 .env.dev 文件设置 SERVER_IP
)

echo - 数据库: SQLite (本地文件)
echo.
echo 使用说明:
echo - 代码修改后自动热重载
echo - 后端日志: docker logs -f openserverhub-dev
echo - Prometheus日志: docker logs -f prometheus-dev
echo - Grafana日志: docker logs -f grafana-dev
echo - AlertManager日志: docker logs -f alertmanager-dev
echo - IPMI Exporter日志: docker logs -f ipmi-exporter-dev
echo - 进入容器: docker exec -it openserverhub-dev sh
echo.
pause
goto menu

REM 停止开发环境
:stop_dev
echo 正在停止单容器开发环境...
%DOCKER_COMPOSE_CMD% -f docker-compose.dev.single.yml down --remove-orphans
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
%DOCKER_COMPOSE_CMD% -f docker-compose.dev.single.yml down -v --remove-orphans
echo √ 单容器开发环境已清理
echo.
pause
goto menu

REM 退出
:exit_script
echo 再见！
exit /b 0