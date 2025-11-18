# 生产环境后端Dockerfile - 基于Python，集成Node.js和SQLite
# 使用多阶段构建来减小最终镜像大小

# 第一阶段：前端构建阶段
FROM node:22-alpine AS frontend-builder

# 安装git以支持版本信息获取
RUN apk add --no-cache git

# 配置Node.js国内源
RUN npm config set registry https://registry.npmmirror.com

# 设置工作目录
WORKDIR /app

# 复制整个项目以确保Git信息可用
COPY . .

# 安装前端依赖
RUN cd frontend && npm ci --only=production

# 构建前端静态资源
RUN cd frontend && npm run build

# 第二阶段：后端构建阶段
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖，包括ipmitool和其他常用工具
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    sqlite3 \
    libsqlite3-dev \
    ipmitool \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 配置Python国内源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 设置工作目录
WORKDIR /app

# 复制后端依赖文件
COPY backend/requirements.txt ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ /app/backend/

# 从第一阶段复制构建好的前端文件到后端静态文件目录
COPY --from=frontend-builder /app/frontend/build /app/backend/static

# 创建SQLite数据库目录
RUN mkdir -p /app/data

# 创建日志目录
RUN mkdir -p /app/logs

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONPATH=/app

# 启动命令 - 生产模式
CMD ["sh", "-c", "cd /app/backend && python init_db.py && uvicorn main:app --host 0.0.0.0 --port 8000"]