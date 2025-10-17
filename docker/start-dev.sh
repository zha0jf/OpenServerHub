#!/bin/bash
# 开发环境快速启动脚本（Linux/Mac）

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}OpenServerHub 开发环境启动脚本${NC}"
echo "=================================="
echo "开发环境配置："
echo "- 数据库: SQLite (本地文件)"
echo "- 前端: http://localhost:3000"
echo "- 后端: http://localhost:8000"
echo ""

# 检查环境配置文件
check_env_file() {
    ENV_FILE="$SCRIPT_DIR/.env.dev"
    ENV_EXAMPLE_FILE="$SCRIPT_DIR/.env.dev.network"
    
    # 如果环境配置文件不存在，尝试从示例文件创建
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE_FILE" ]; then
            echo -e "${YELLOW}环境配置文件不存在，从示例文件创建...${NC}"
            cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
            echo -e "${GREEN}✓ 已创建环境配置文件: $ENV_FILE${NC}"
            echo -e "${BLUE}ℹ  您可以编辑此文件修改服务器IP地址和其他配置${NC}"
        else
            echo -e "${RED}错误: 环境配置文件和示例文件都不存在${NC}"
            exit 1
        fi
    fi
    
    # 加载环境变量
    source "$ENV_FILE"
    
    # 检查是否设置了服务器IP
    if [ -z "$SERVER_IP" ] || [ "$SERVER_IP" = "0.0.0.0" ]; then
        echo -e "${YELLOW}未设置服务器IP地址，使用本地访问模式${NC}"
        REMOTE_ACCESS="false"
    else
        echo -e "${GREEN}✓ 服务器IP地址: $SERVER_IP${NC}"
        REMOTE_ACCESS="true"
    fi
    
    # 设置全局变量供其他函数使用
    export SERVER_IP
    export REMOTE_ACCESS
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
    echo -e "${BLUE}ℹ  开发环境配置：SQLite + 热重载${NC}"
    echo -e "${BLUE}ℹ  使用命令: ${DOCKER_COMPOSE_CMD}${NC}"
}

# 启动开发环境
start_dev() {
    echo -e "${YELLOW}正在启动开发环境...${NC}"
    cd "$SCRIPT_DIR"
    
    # 创建数据目录
    mkdir -p "$PROJECT_ROOT/backend/data"
    
    # 启动服务
    $DOCKER_COMPOSE_CMD -f docker-compose.dev.sqlite.yml up -d
    
    echo -e "${GREEN}✓ 开发环境启动成功！${NC}"
    echo ""
    echo "服务地址:"
    
    if [ "$REMOTE_ACCESS" = "true" ]; then
        echo "- 前端开发服务器: http://$SERVER_IP:3000"
        echo "- 后端API: http://$SERVER_IP:8000"
        echo "- API文档: http://$SERVER_IP:8000/docs"
        echo ""
        echo -e "${YELLOW}远程访问模式:${NC}"
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
    echo "- 后端日志: docker logs -f openserverhub-backend-dev"
    echo "- 前端日志: docker logs -f openserverhub-frontend-dev"
}

# 停止开发环境
stop_dev() {
    echo -e "${YELLOW}正在停止开发环境...${NC}"
    cd "$SCRIPT_DIR"
    $DOCKER_COMPOSE_CMD -f docker-compose.dev.sqlite.yml down --remove-orphans
    echo -e "${GREEN}✓ 开发环境已停止${NC}"
}

# 查看日志
logs() {
    cd "$SCRIPT_DIR"
    if [ "$1" == "backend" ]; then
        docker logs -f openserverhub-backend-dev
    elif [ "$1" == "frontend" ]; then
        docker logs -f openserverhub-frontend-dev
    else
        $DOCKER_COMPOSE_CMD -f docker-compose.dev.sqlite.yml logs -f
    fi
}

# 清理环境
cleanup() {
    echo -e "${YELLOW}正在清理开发环境...${NC}"
    cd "$SCRIPT_DIR"
    $DOCKER_COMPOSE_CMD -f docker-compose.dev.sqlite.yml down -v --remove-orphans
    echo -e "${GREEN}✓ 开发环境已清理${NC}"
}

# 主菜单
show_menu() {
    echo ""
    echo "请选择操作:"
    echo "1) 启动开发环境"
    echo "2) 停止开发环境"
    echo "3) 查看日志"
    echo "4) 清理环境"
    echo "5) 退出"
    echo ""
}

# 主程序
main() {
    check_docker
    check_env_file
    
    while true; do
        show_menu
        read -p "请输入选项 (1-5): " choice
        
        case $choice in
            1)
                start_dev
                ;;
            2)
                stop_dev
                ;;
            3)
                echo "选择日志类型:"
                echo "1) 所有服务"
                echo "2) 后端服务"
                echo "3) 前端服务"
                read -p "请输入选项 (1-3): " log_choice
                case $log_choice in
                    1) logs ;;
                    2) logs backend ;;
                    3) logs frontend ;;
                    *) echo -e "${RED}无效选项${NC}" ;;
                esac
                ;;
            4)
                cleanup
                ;;
            5)
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