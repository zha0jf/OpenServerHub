#!/bin/bash

# OpenServerHub 生产环境启动脚本 (SQLite版本)

set -e

echo "🚀 OpenServerHub 生产环境启动器 (SQLite版本)"
echo "=========================================="

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
if [ ! -f .env.prod ]; then
    echo "⚠️  未找到生产环境的 .env.prod 文件，正在创建..."
    cp .env.example .env.prod
    echo "📝 请编辑 .env.prod 文件以配置您的生产环境"
    echo "   特别注意修改 SECRET_KEY 等安全配置"
    read -p "按回车键继续..."
fi

# 选择操作
echo "请选择操作："
echo "1) 启动生产环境"
echo "2) 停止生产环境"
echo "3) 重启生产环境"
echo "4) 查看服务状态"
echo "5) 查看日志"
echo "6) 初始化数据库"
echo "7) 备份数据库"
echo "8) 恢复数据库"
read -p "请输入选项 (1-8): " choice

case $choice in
    1)
        echo "🏭 正在启动生产环境..."
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod up -d
        echo "✅ 生产环境已启动！"
        echo "🌐 应用地址: http://localhost:8000"
        echo "🔧 API文档: http://localhost:8000/docs"
        echo "📊 监控面板: http://localhost:3001"
        ;;
    2)
        echo "🛑 正在停止生产环境..."
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod down
        echo "✅ 生产环境已停止！"
        ;;
    3)
        echo "🔄 正在重启生产环境..."
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod down
        sleep 3
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod up -d
        echo "✅ 生产环境已重启！"
        echo "🌐 应用地址: http://localhost:8000"
        echo "🔧 API文档: http://localhost:8000/docs"
        echo "📊 监控面板: http://localhost:3001"
        ;;
    4)
        echo "📋 服务状态："
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod ps
        ;;
    5)
        echo "📋 选择服务查看日志："
        echo "1) 所有服务"
        echo "2) 后端服务"
        echo "3) Prometheus"
        echo "4) Grafana"
        echo "5) AlertManager"
        echo "6) IPMI Exporter"
        read -p "请输入选项 (1-6): " log_choice
        
        case $log_choice in
            1) docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f ;;
            2) docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f backend ;;
            3) docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f prometheus ;;
            4) docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f grafana ;;
            5) docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f alertmanager ;;
            6) docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod logs -f ipmi-exporter ;;
            *) echo "无效选项" ;;
        esac
        ;;
    6)
        echo "💾 正在初始化数据库..."
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod exec backend sh -c "cd /app/backend && python init_db.py"
        echo "✅ 数据库初始化完成！"
        ;;
    7)
        echo "💾 正在备份数据库..."
        backup_file="backup_$(date +%Y%m%d_%H%M%S).db"
        docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod exec backend cp /app/data/openserverhub.db /app/data/$backup_file
        docker cp openserverhub-backend-prod:/app/data/$backup_file ./$backup_file
        echo "✅ 数据库备份完成: $backup_file"
        ;;
    8)
        echo "📂 可用的备份文件："
        ls -la backup_*.db 2>/dev/null || echo "未找到备份文件"
        read -p "请输入备份文件名: " backup_file
        if [ -f "$backup_file" ]; then
            echo "📥 正在恢复数据库..."
            docker cp ./$backup_file openserverhub-backend-prod:/app/data/openserverhub.db
            echo "✅ 数据库恢复完成！"
            echo "⚠️  建议重启服务以确保数据一致性"
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
echo "=========================================="