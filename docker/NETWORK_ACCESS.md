# 开发环境网络访问配置指南

本指南说明如何配置OpenServerHub开发环境，使您可以从Windows开发机通过网络访问运行在Linux服务器上的容器。

## 配置步骤

### 1. 配置服务器IP地址

1. 在Linux服务器上，复制环境变量配置文件：
   ```bash
   cd docker
   cp .env.dev.network .env.dev
   ```

2. 编辑 `.env.dev` 文件，修改以下配置：
   ```bash
   # 设置为您的Linux服务器的实际IP地址
   SERVER_IP=192.168.1.100
   
   # 前端API配置（会自动使用SERVER_IP）
   REACT_APP_API_URL=http://192.168.1.100:8000
   REACT_APP_WS_URL=ws://192.168.1.100:8000
   
   # 允许来自您的Windows开发机的跨域请求
   # 添加您的Windows开发机IP地址
   CORS_ORIGINS=http://192.168.1.50:3000,http://localhost:3000
   ```
   
   > 注意：请将 `192.168.1.100` 替换为您的Linux服务器实际IP地址，
   > 将 `192.168.1.50` 替换为您的Windows开发机实际IP地址。

### 2. 启动开发环境

#### 单容器模式（推荐）
```bash
# 在Linux服务器上执行
cd docker
./start-dev-single.sh
```

#### 双容器模式
```bash
# 在Linux服务器上执行
cd docker
./start-dev.sh
```

### 3. 从Windows开发机访问

启动成功后，您可以从Windows开发机通过以下地址访问服务：

- **前端应用**: `http://192.168.1.100:3000`
- **后端API**: `http://192.168.1.100:8000`
- **API文档**: `http://192.168.1.100:8000/docs`

## 网络配置说明

### 后端服务
- 后端服务已配置为监听 `0.0.0.0:8000`，可以从任何IP地址访问

### 前端服务
- 前端开发服务器已配置为监听 `0.0.0.0:3000`，可以从任何IP地址访问
- 前端环境变量已配置为使用服务器IP地址连接后端API

### CORS配置
- CORS配置已设置为允许来自指定IP地址的跨域请求
- 请确保在 `CORS_ORIGINS` 中添加您的Windows开发机IP地址

## 故障排除

### 1. 无法访问服务
- 检查Linux服务器防火墙设置，确保端口3000和8000已开放
- 确认Docker容器正在运行：`docker ps`
- 查看容器日志：`docker logs -f openserverhub-dev` 或 `docker logs -f openserverhub-frontend-dev`

### 2. 前端无法连接后端API
- 检查 `.env.dev` 文件中的 `REACT_APP_API_URL` 和 `REACT_APP_WS_URL` 配置
- 确认后端服务正在运行：`curl http://localhost:8000/docs`
- 检查CORS配置是否包含您的Windows开发机IP地址

### 3. 跨域请求被阻止
- 确认 `CORS_ORIGINS` 配置正确
- 检查浏览器控制台错误信息
- 尝试在浏览器中直接访问API地址确认服务可用

## 高级配置

### 自定义端口
如果需要使用不同的端口，可以修改 `docker-compose.dev.sqlite.yml` 或 `docker-compose.dev.single.yml` 中的端口映射：
```yaml
ports:
  - "8001:8000"  # 将外部端口改为8001
  - "3001:3000"  # 将外部端口改为3001
```

### 使用域名
如果配置了域名解析，可以在 `.env.dev` 文件中使用域名：
```bash
SERVER_IP=your-domain.com
REACT_APP_API_URL=http://your-domain.com:8000
REACT_APP_WS_URL=ws://your-domain.com:8000
```

## 安全注意事项

1. 在生产环境中，请确保：
   - 使用HTTPS而非HTTP
   - 限制CORS来源，不要使用通配符 `*`
   - 配置适当的防火墙规则
   - 使用强密码和安全的认证机制

2. 开发环境中，请确保：
   - 不要将 `.env.dev` 文件提交到版本控制系统
   - 定期更新依赖项
   - 使用VPN或安全网络连接访问远程开发环境