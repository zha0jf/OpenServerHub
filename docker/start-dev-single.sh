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
echo "- 前端: http://localhost:3000"
echo "- 后端: http://localhost:8000"
echo ""

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
    echo "- 前端开发服务器: http://localhost:3000"
    echo "- 后端API: http://localhost:8000"
    echo "- API文档: http://localhost:8000/docs"
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