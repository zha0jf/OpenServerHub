#!/bin/bash

# OpenServerHub Docker 快速启动脚本

set -e

echo "🚀 OpenServerHub Docker 部署启动器"
echo "=================================="

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 检查环境文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，正在创建..."
    cp .env.example .env
    echo "📝 请编辑 .env 文件以配置您的环境"
    read -p "按回车键继续..."
fi

# 选择部署模式
echo "请选择部署模式："
echo "1) 生产环境 (Production)"
echo "2) 开发环境 (Development)"
echo "3) 监控环境 (Monitoring)"
echo "4) 停止所有服务"
echo "5) 查看日志"
echo "6) 数据备份（仅生产环境）"
echo "7) 数据恢复（仅生产环境）"
read -p "请输入选项 (1-7): " choice

case $choice in
    1)
        echo "🏭 正在启动生产环境..."
        docker-compose up -d
        echo "✅ 生产环境已启动！"
        echo "🌐 前端地址: http://localhost"
        echo "🔧 API地址: http://localhost:8000"
        echo "📚 API文档: http://localhost:8000/docs"
        ;;
    2)
        echo "🔧 正在启动开发环境..."
        # 检查开发环境的.env文件
        if [ ! -f .env.dev ]; then
            echo "⚠️  未找到开发环境的 .env.dev 文件，正在创建..."
            cp .env.dev.example .env.dev
            echo "📝 请编辑 .env.dev 文件以配置您的开发环境"
            read -p "按回车键继续..."
        fi
        docker-compose -f docker-compose.dev.yml up -d
        echo "✅ 开发环境已启动！"
        echo "🌐 前端地址: http://localhost:3000"
        echo "🔧 API地址: http://localhost:8000"
        ;;
    3)
        echo "📊 正在启动监控环境..."
        docker-compose -f docker-compose.monitoring.yml up -d
        echo "✅ 监控环境已启动！"
        echo "📈 Prometheus: http://localhost:9090"
        echo "📊 Grafana: http://localhost:3001"
        echo "⚠️  AlertManager: http://localhost:9093"
        ;;
    4)
        echo "🛑 正在停止所有服务..."
        docker-compose down
        docker-compose -f docker-compose.dev.yml down
        docker-compose -f docker-compose.monitoring.yml down
        echo "✅ 所有服务已停止！"
        ;;
    5)
        echo "📋 选择服务查看日志："
        echo "1) 所有服务（生产环境）"
        echo "2) 后端服务"
        echo "3) 前端服务"
        echo "4) 数据库（仅生产环境）"
        echo "5) 监控服务"
        read -p "请输入选项 (1-5): " log_choice
        
        case $log_choice in
            1) docker-compose logs -f ;;
            2) docker-compose logs -f backend ;;
            3) docker-compose logs -f frontend ;;
            4) docker-compose logs -f postgres ;;
            5) docker-compose -f docker-compose.monitoring.yml logs -f ;;
            *) echo "无效选项" ;;
        esac
        ;;
    6)
        echo "💾 正在备份数据（仅适用于生产环境）..."
        backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
        docker-compose exec postgres pg_dump -U postgres openserverhub > "$backup_file"
        echo "✅ 数据备份完成: $backup_file"
        ;;
    7)
        echo "📂 可用的备份文件（仅适用于生产环境）："
        ls -la backup_*.sql 2>/dev/null || echo "未找到备份文件"
        read -p "请输入备份文件名: " backup_file
        if [ -f "$backup_file" ]; then
            echo "📥 正在恢复数据..."
            docker-compose exec -T postgres psql -U postgres openserverhub < "$backup_file"
            echo "✅ 数据恢复完成！"
        else
            echo "❌ 备份文件不存在！"
        fi
        ;;
    *)
        echo "❌ 无效选项！"
        exit 1
        ;;
esac

echo ""
echo "🎉 操作完成！"
echo "=================================="