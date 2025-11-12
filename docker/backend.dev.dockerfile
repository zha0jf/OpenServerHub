# 开发环境后端Dockerfile - 基于Python，集成Node.js和SQLite
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV NODE_VERSION=22.x

# 安装系统依赖，包括ipmitool和其他常用工具
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    sqlite3 \
    libsqlite3-dev \
    ipmitool \
    iputils-ping \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 配置Node.js国内源并安装Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm config set registry https://registry.npmmirror.com \
    && npm install -g npm@latest

# 配置Python国内源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 设置工作目录
WORKDIR /app

# 复制后端依赖文件
COPY backend/requirements.txt ./

# 安装Python依赖 - 强制重新安装以避免缓存问题
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt

# 复制前端package.json和package-lock.json文件
COPY frontend/package.json frontend/package-lock.json* /app/frontend/

# 在构建阶段安装前端依赖 - 使用npm install来处理跨平台兼容性
RUN cd /app/frontend && npm install --ignore-scripts

# 复制后端代码到子目录
COPY backend/ /app/backend/

# 复制前端代码到子目录
COPY frontend/ /app/frontend/

# 创建SQLite数据库目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 启动命令 - 开发模式带热重载
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/backend"]