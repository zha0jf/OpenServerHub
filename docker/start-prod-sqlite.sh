#!/bin/bash

# OpenServerHub 生产环境启动脚本 (SQLite版本)

set -e

echo "🚀 OpenServerHub 生产环境启动器 (SQLite版本)"
echo "=========================================="

# 颜色输出定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查环境配置文件
check_env_file() {
    ENV_FILE="$SCRIPT_DIR/.env.prod"
    
    # 检查服务器IP地址
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}⚠️  未找到生产环境的 .env.prod 文件，正在创建...${NC}"
        cp .env.example .env.prod
        echo -e "${BLUE}📝 请编辑 .env.prod 文件以配置您的生产环境${NC}"
        echo -e "${BLUE}   特别注意修改 SECRET_KEY 等安全配置${NC}"
        read -p "按回车键继续..."
    fi
    
    # 加载环境文件
    source "$ENV_FILE"
    
    # 检查服务器IP配置
    if [ -z "$SERVER_IP" ]; then
        # 如果SERVER_IP未设置，使用本地访问模式
        export SERVER_IP="localhost"
        export REMOTE_ACCESS=false
        echo -e "${BLUE}ℹ  未设置服务器IP地址，使用默认地址: $SERVER_IP${NC}"
    elif [ "$SERVER_IP" = "127.0.0.1" ] || [ "$SERVER_IP" = "localhost" ]; then
        # 如果SERVER_IP是本地地址，使用本地访问模式
        export REMOTE_ACCESS=false
        echo -e "${BLUE}ℹ  检测到本地访问配置，服务器IP: $SERVER_IP${NC}"
    else
        # 其他情况都是远程访问模式
        export REMOTE_ACCESS=true
        echo -e "${GREEN}✓ 检测到远程访问配置${NC}"
        echo -e "${GREEN}✓ 配置的服务器IP: $SERVER_IP${NC}"
    fi
}

# 检查Docker和Docker Compose
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker 未安装，请先安装 Docker${NC}"
        exit 1
    fi
    
    # 检查Docker Compose（支持docker-compose和docker compose两种命令）
    DOCKER_COMPOSE_CMD=""
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}❌ Docker Compose 未安装（需要docker-compose或docker compose命令）${NC}"
        exit 1
    fi
    
    # 设置全局变量供其他函数使用
    export DOCKER_COMPOSE_CMD
    
    echo -e "${GREEN}✓ Docker环境检查通过${NC}"
}

# 选择操作
echo "请选择操作："
echo "1) 启动生产环境"
echo "2) 停止生产环境"
echo "3) 重启生产环境"
echo "4) 查看服务状态"
echo "5) 查看日志"
echo "6) 初始化数据库"
echo "7) 退出"
read -p "请输入选项 (1-7): " choice

case $choice in
    1)
        echo -e "${YELLOW}🏭 正在启动生产环境...${NC}"
        check_docker
        check_env_file
        $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod up -d
        echo -e "${GREEN}✅ 生产环境已启动！${NC}"
        if [ "$REMOTE_ACCESS" = "true" ]; then
            echo -e "${BLUE}🌐 应用地址: http://$SERVER_IP:8000${NC}"
            echo -e "${BLUE}🔧 API文档: http://$SERVER_IP:8000/docs${NC}"
            echo -e "${BLUE}📊 监控面板: http://$SERVER_IP:3001${NC}"
        else
            echo "🌐 应用地址: http://localhost:8000"
            echo "🔧 API文档: http://localhost:8000/docs"
            echo "📊 监控面板: http://localhost:3001"
        fi
        ;;
    2)
        echo -e "${YELLOW}🛑 正在停止生产环境...${NC}"
        check_docker
        $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod down
        echo -e "${GREEN}✅ 生产环境已停止！${NC}"
        ;;
    3)
        echo -e "${YELLOW}🔄 正在重启生产环境...${NC}"
        check_docker
        $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod down
        sleep 3
        $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod up -d
        echo -e "${GREEN}✅ 生产环境已重启！${NC}"
        if [ "$REMOTE_ACCESS" = "true" ]; then
            echo -e "${BLUE}🌐 应用地址: http://$SERVER_IP:8000${NC}"
            echo -e "${BLUE}🔧 API文档: http://$SERVER_IP:8000/docs${NC}"
            echo -e "${BLUE}📊 监控面板: http://$SERVER_IP:3001${NC}"
        else
            echo "🌐 应用地址: http://localhost:8000"
            echo "🔧 API文档: http://localhost:8000/docs"
            echo "📊 监控面板: http://localhost:3001"
        fi
        ;;
    4)
        echo -e "${BLUE}📋 服务状态：${NC}"
        check_docker
        $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod ps
        ;;
    5)
        echo -e "${BLUE}📋 选择服务查看日志：${NC}"
        echo "1) 所有服务"
        echo "2) 后端服务"
        echo "3) Prometheus"
        echo "4) Grafana"
        echo "5) AlertManager"
        echo "6) IPMI Exporter"
        read -p "请输入选项 (1-6): " log_choice
        
        check_docker
        case $log_choice in
            1) $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f ;;
            2) $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f backend ;;
            3) $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f prometheus ;;
            4) $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f grafana ;;
            5) $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f alertmanager ;;
            6) $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f ipmi-exporter ;;
            *) echo -e "${RED}无效选项${NC}" ;;
        esac
        ;;
    6)
        echo -e "${YELLOW}💾 正在初始化数据库...${NC}"
        check_docker
        check_env_file
        $DOCKER_COMPOSE_CMD -f docker-compose.prod.sqlite.yml --env-file .env.prod exec backend sh -c "cd /app/backend && python init_db.py"
        echo -e "${GREEN}✅ 数据库初始化完成！${NC}"
        ;;
    7)
        echo -e "${GREEN}再见！${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ 无效选项！${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}🎉 操作完成！${NC}"
echo "=========================================="