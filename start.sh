#!/bin/bash

echo "===================================="
echo "OpenServerHub 启动脚本"
echo "===================================="

echo ""
echo "1. 启动后端服务..."
cd "$(dirname "$0")/backend"

# 检查是否已安装依赖
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装后端依赖..."
pip install -r requirements.txt

# 复制环境配置
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "已创建环境配置文件，请根据需要修改 backend/.env"
fi

# 初始化数据库
echo "初始化数据库..."
python init_db.py

# 启动后端服务
echo "启动后端服务..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &

echo ""
echo "2. 启动前端服务..."
cd "../frontend"

# 安装前端依赖
echo "安装前端依赖..."
npm install

# 启动前端服务
echo "启动前端服务..."
npm start &

echo ""
echo "===================================="
echo "启动完成！"
echo "前端地址: http://localhost:3000"
echo "后端API: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "默认账号: admin / admin123"
echo "===================================="

# 等待用户输入
read -p "按回车键退出..."