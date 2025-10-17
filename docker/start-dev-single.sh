#!/bin/bash
# 单容器开发环境快速启动脚本（Linux/Mac）

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}OpenServerHub 单容器开发环境启动脚本${NC}"
echo "========================================"
echo "开发环境配置："
echo "- 数据库: SQLite (本地文件)"
echo "- 架构: 单容器（后端+前端）"
echo "- 前端: 端口 3000"
echo "- 后端: 端口 8000"
echo "- 访问地址: 根据环境配置自动确定（本地或远程）"
echo ""

# 检查环境配置文件
check_env_file() {
    ENV_FILE="$SCRIPT_DIR/.env.dev"
    ENV_EXAMPLE="$SCRIPT_DIR/.env.dev.network"
    
    # 读取服务器IP地址
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}警告: 环境配置文件 $ENV_FILE 不存在${NC}"
        echo -e "${BLUE}正在从示例文件创建配置文件...${NC}"
        
        if [ -f "$ENV_EXAMPLE" ]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            echo -e "${GREEN}✓ 已创建环境配置文件: $ENV_FILE${NC}"
            echo -e "${YELLOW}请编辑此文件，设置您的服务器IP地址${NC}"
            echo -e "${BLUE}特别是修改 SERVER_IP 和 CORS_ORIGINS 配置${NC}"
            echo ""
            read -p "按回车键继续..."
            
            # 加载新创建的环境文件
            source "$ENV_FILE"
        else
            echo -e "${RED}错误: 示例配置文件 $ENV_EXAMPLE 不存在${NC}"
            exit 1
        fi
    else
        # 加载已存在的环境文件
        source "$ENV_FILE"
    fi
    
    # 检查服务器IP配置
    if [ -z "$SERVER_IP" ]; then
        # 如果SERVER_IP未设置，使用本地访问模式
        export SERVER_IP="127.0.0.1"
        export REMOTE_ACCESS=false
        echo -e "${BLUE}ℹ  未设置服务器IP地址，使用本地访问模式${NC}"
    elif [ "$SERVER_IP" = "127.0.0.1" ] || [ "$SERVER_IP" = "localhost" ]; then
        # 如果SERVER_IP是本地地址，使用本地访问模式
        export REMOTE_ACCESS=false
        echo -e "${BLUE}ℹ  检测到本地访问配置，服务器IP: $SERVER_IP${NC}"
    else
        # 其他情况都是远程访问模式，使用0.0.0.0监听所有接口
        export LISTEN_IP="0.0.0.0"
        export REMOTE_ACCESS=true
        echo -e "${GREEN}✓ 检测到远程访问配置，将在所有IP上监听${NC}"
        echo -e "${GREEN}✓ 配置的服务器IP: $SERVER_IP (用于显示和访问)${NC}"
    fi
}

# 检查Docker环境
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker未安装${NC}"
        exit 1
    fi
    
    # 检查Docker Compose（支持docker-compose和docker compose两种命令）
    DOCKER_COMPOSE_CMD=""
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}错误: Docker Compose未安装（需要docker-compose或docker compose命令）${NC}"
        exit 1
    fi
    
    # 设置全局变量供其他函数使用
    export DOCKER_COMPOSE_CMD
    
    echo -e "${GREEN}✓ Docker环境检查通过${NC}"
    echo -e "${BLUE}ℹ  单容器开发环境配置：SQLite + 热重载${NC}"
    echo -e "${BLUE}ℹ  使用命令: ${DOCKER_COMPOSE_CMD}${NC}"
}

# 启动开发环境
start_dev() {
    echo -e "${YELLOW}正在启动单容器开发环境...${NC}"
    cd "$SCRIPT_DIR"
    
    # 创建数据目录
    mkdir -p "$PROJECT_ROOT/backend/data"
    
    # 启动单容器服务
    $DOCKER_COMPOSE_CMD -f docker-compose.dev.single.yml up -d
    
    echo -e "${GREEN}✓ 单容器开发环境启动成功！${NC}"
    echo ""
    echo "服务地址:"
    
    if [ "$REMOTE_ACCESS" = "true" ]; then
        echo "- 前端开发服务器: http://$SERVER_IP:3000"
        echo "- 后端API: http://$SERVER_IP:8000"
        echo "- API文档: http://$SERVER_IP:8000/docs"
        echo ""
        echo -e "${YELLOW}远程访问模式:${NC}"
        echo "- 服务将在所有网络接口上监听 (0.0.0.0)"
        echo "- 您可以从网络中的其他计算机访问这些服务"
        echo "- 请确保防火墙已开放端口 3000 和 8000"
    else
        echo "- 前端开发服务器: http://localhost:3000"
        echo "- 后端API: http://localhost:8000"
        echo "- API文档: http://localhost:8000/docs"
        echo ""
        echo -e "${BLUE}本地访问模式:${NC}"
        echo "- 仅可在本机访问这些服务"
        echo "- 如需远程访问，请编辑 .env.dev 文件设置 SERVER_IP"
    fi
    
    echo "- 数据库: SQLite (本地文件)"
    echo ""
    echo "使用说明:"
    echo "- 代码修改后自动热重载"
    echo "- 容器日志: docker logs -f openserverhub-dev"
    echo "- 进入容器: docker exec -it openserverhub-dev sh"
}

# 停止开发环境
stop_dev() {
    echo -e "${YELLOW}正在停止单容器开发环境...${NC}"
    cd "$SCRIPT_DIR"
    $DOCKER_COMPOSE_CMD -f docker-compose.dev.single.yml down --remove-orphans
    echo -e "${GREEN}✓ 单容器开发环境已停止${NC}"
}

# 查看日志
logs() {
    cd "$SCRIPT_DIR"
    docker logs -f openserverhub-dev
}

# 进入容器
shell() {
    cd "$SCRIPT_DIR"
    docker exec -it openserverhub-dev sh
}

# 清理环境
cleanup() {
    echo -e "${YELLOW}正在清理单容器开发环境...${NC}"
    cd "$SCRIPT_DIR"
    $DOCKER_COMPOSE_CMD -f docker-compose.dev.single.yml down -v --remove-orphans
    echo -e "${GREEN}✓ 单容器开发环境已清理${NC}"
}

# 主菜单
show_menu() {
    echo ""
    echo "请选择操作:"
    echo "1) 启动单容器开发环境"
    echo "2) 停止单容器开发环境"
    echo "3) 查看容器日志"
    echo "4) 进入容器Shell"
    echo "5) 清理环境"
    echo "6) 退出"
    echo ""
}

# 主程序
main() {
    check_docker
    check_env_file
    
    while true; do
        show_menu
        read -p "请输入选项 (1-6): " choice
        
        case $choice in
            1)
                start_dev
                ;;
            2)
                stop_dev
                ;;
            3)
                logs
                ;;
            4)
                shell
                ;;
            5)
                cleanup
                ;;
            6)
                echo -e "${GREEN}再见！${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}无效选项，请重新输入${NC}"
                ;;
        esac
        
        echo ""
        read -p "按回车键继续..."
    done
}

# 如果直接运行脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi