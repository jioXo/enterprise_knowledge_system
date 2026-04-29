# 部署指南

本文档介绍企业内部知识管理系统的部署过程，包括开发环境、生产环境的配置。

## 目录

- [环境要求](#环境要求)
- [开发环境部署](#开发环境部署)
- [生产环境部署](#生产环境部署)
- [Docker 部署](#docker-部署)
- [Kubernetes 部署](#kubernetes-部署)
- [监控和维护](#监控和维护)
- [故障排查](#故障排查)

## 环境要求

### 系统要求
- **操作系统**: Linux (推荐 Ubuntu 20.04+) / macOS / Windows
- **内存**: 最少 2GB，推荐 4GB+
- **存储**: 最少 10GB，推荐 50GB+
- **CPU**: 双核以上

### 软件要求
- **Python**: 3.8+
- **PostgreSQL**: 12+ (可选，默认使用 SQLite)
- **Redis**: 6.0+ (可选，用于缓存)
- **Nginx**: 1.18+ (生产环境推荐)

### Python 依赖
主要依赖包：
- fastapi==0.104.1
- uvicorn==0.24.0
- langchain==0.1.0
- chromadb==0.4.18
- sqlalchemy==2.0.23
- psycopg2-binary==2.9.9
- redis==5.0.1

## 开发环境部署

### 1. 克隆项目
```bash
git clone <repository-url>
cd enterprise_knowledge_system
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置环境变量
```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
# 数据库配置（开发环境使用 SQLite）
DATABASE_URL=sqlite:///./data/enterprise_knowledge.db

# Redis 配置（可选）
REDIS_URL=redis://localhost:6379/0

# API 密钥（使用测试密钥）
OPENAI_API_KEY=test_key_here

# 向量数据库配置
VECTOR_DB_PATH=./data/vector_db
VECTOR_DB_TYPE=chroma

# 服务配置
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

### 5. 创建必要的目录
```bash
mkdir -p data/{vector_db,raw_docs,processed_docs} logs
```

### 6. 初始化数据库
```bash
python -c "from src.models.database import init_db; init_db()"
```

### 7. 启动开发服务器
```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

## 生产环境部署

### 1. 服务器准备

#### 安装系统依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3-pip python3-venv postgresql redis-server nginx

# CentOS/RHEL
sudo yum install -y python3-pip python3-venv postgresql-server redis nginx
```

#### 配置 PostgreSQL（推荐）
```bash
# 初始化 PostgreSQL
sudo postgresql-setup --initdb

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql -c "CREATE DATABASE enterprise_knowledge;"
sudo -u postgres psql -c "CREATE USER app_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE enterprise_knowledge TO app_user;"
```

### 2. 部署应用

#### 上传代码
```bash
# 创建应用目录
sudo mkdir -p /opt/enterprise-knowledge
sudo chown -R $USER:$USER /opt/enterprise-knowledge

# 复制代码
cp -r /path/to/enterprise-knowledge-system/* /opt/enterprise-knowledge/
cd /opt/enterprise-knowledge
```

#### 创建生产环境配置
```bash
cp .env.example .env
```

编辑 `.env` 文件（生产环境）：
```env
# 数据库配置（使用 PostgreSQL）
DATABASE_URL=postgresql://app_user:your_password@localhost:5432/enterprise_knowledge

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# API 密钥（使用真实密钥）
OPENAI_API_KEY=your_real_openai_key
ANTHROPIC_API_KEY=your_real_anthropic_key

# 向量数据库配置
VECTOR_DB_PATH=/opt/enterprise-knowledge/data/vector_db
VECTOR_DB_TYPE=chroma

# 文档存储路径
RAW_DOCS_PATH=/opt/enterprise-knowledge/data/raw_docs
PROCESSED_DOCS_PATH=/opt/enterprise-knowledge/data/processed_docs

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/opt/enterprise-knowledge/logs/app.log

# 服务配置
DEBUG=False
SECRET_KEY=your_secret_key_here
HOST=0.0.0.0
PORT=8000
```

#### 创建虚拟环境并安装依赖
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置系统服务

#### 创建 systemd 服务
```bash
sudo tee /etc/systemd/system/enterprise-knowledge.service > /dev/null <<EOF
[Unit]
Description=Enterprise Knowledge System
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/enterprise-knowledge
Environment=PATH=/opt/enterprise-knowledge/venv/bin
ExecStart=/opt/enterprise-knowledge/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

#### 启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl start enterprise-knowledge
sudo systemctl enable enterprise-knowledge
```

### 4. 配置 Nginx

#### 创建 Nginx 配置
```bash
sudo tee /etc/nginx/sites-available/enterprise-knowledge > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;

    access_log /var/log/nginx/enterprise-knowledge.access.log;
    error_log /var/log/nginx/enterprise-knowledge.error.log;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host \$host;
    }

    location /static {
        alias /opt/enterprise-knowledge/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF
```

#### 启用站点
```bash
sudo ln -s /etc/nginx/sites-available/enterprise-knowledge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Docker 部署

### 1. 创建 Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p data/{vector_db,raw_docs,processed_docs} logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "main.py"]
```

### 2. 创建 docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/enterprise_knowledge
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEBUG=False
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - db
      - redis

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=enterprise_knowledge
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app

volumes:
  postgres_data:
```

### 3. 构建和运行
```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## Kubernetes 部署

### 1. 创建命名空间
```bash
kubectl create namespace knowledge-system
```

### 2. 创建配置文件
```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: knowledge-system
data:
  .env: |
    DEBUG=False
    DATABASE_URL=postgresql://postgres:password@postgres-service:5432/enterprise_knowledge
    REDIS_URL=redis://redis-service:6379/0
    OPENAI_API_KEY=${OPENAI_API_KEY}
```

### 3. 部署 PostgreSQL
```yaml
# postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: knowledge-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:13
        env:
        - name: POSTGRES_DB
          value: enterprise_knowledge
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          value: password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
```

### 4. 部署应用
```yaml
# app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: knowledge-system
  namespace: knowledge-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: knowledge-system
  template:
    metadata:
      labels:
        app: knowledge-system
    spec:
      containers:
      - name: app
        image: enterprise-knowledge:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: app-config
        volumeMounts:
        - name: data-storage
          mountPath: /app/data
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: data-storage
        persistentVolumeClaim:
          claimName: app-data-pvc
      - name: logs
        persistentVolumeClaim:
          claimName: app-logs-pvc
```

### 5. 部署服务
```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: knowledge-system-service
  namespace: knowledge-system
spec:
  selector:
    app: knowledge-system
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

### 6. 部署
```bash
kubectl apply -f k8s/
```

## 监控和维护

### 1. 日志管理
```bash
# 查看应用日志
journalctl -u enterprise-knowledge -f

# 查看 Nginx 日志
tail -f /var/log/nginx/enterprise-knowledge.access.log
tail -f /var/log/nginx/enterprise-knowledge.error.log
```

### 2. 健康检查
```bash
# 检查服务状态
curl http://localhost:8000/api/v1/health

# 检查数据库连接
sudo -u postgres psql -c "SELECT 1 FROM enterprise_knowledge LIMIT 1;"
```

### 3. 定期维护
```bash
# 备份数据库
sudo -u postgres pg_dump enterprise_knowledge > backup_$(date +%Y%m%d).sql

# 清理旧日志
find /var/log/nginx -name "enterprise-knowledge.*.log.*" -mtime +30 -delete

# 更新应用
sudo systemctl stop enterprise-knowledge
git pull
pip install -r requirements.txt
sudo systemctl start enterprise-knowledge
```

### 4. 性能监控
```bash
# 系统资源监控
htop

# 磁盘使用监控
df -h

# 内存使用监控
free -h
```

## 故障排查

### 1. 应用启动失败
```bash
# 检查服务状态
sudo systemctl status enterprise-knowledge

# 查看详细错误
sudo journalctl -u enterprise-knowledge --no-pager -n 100

# 检查端口占用
netstat -tlnp | grep 8000
```

### 2. 数据库连接问题
```bash
# 测试数据库连接
psql $DATABASE_URL

# 检查 PostgreSQL 状态
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT version();"
```

### 3. Redis 连接问题
```bash
# 测试 Redis 连接
redis-cli ping

# 检查 Redis 状态
sudo systemctl status redis-server
```

### 4. 文件权限问题
```bash
# 检查文件权限
ls -la /opt/enterprise-knowledge/
ls -la /opt/enterprise-knowledge/data/

# 修复权限
sudo chown -R www-data:www-data /opt/enterprise-knowledge/
sudo chmod -R 755 /opt/enterprise-knowledge/
```

### 5. 内存使用过高
```bash
# 查看内存使用
ps aux --sort=-%mem | head

# 查看进程详细信息
ps -p <pid> -o pid,ppid,cmd,%mem,%cpu --width=100
```

### 6. 常见错误解决方案

#### 端口被占用
```bash
# 查找占用端口的进程
lsof -i :8000

# 终止进程
sudo kill -9 <PID>
```

#### 权限不足
```bash
# 添加用户到 www-data 组
sudo usermod -a -G www-data $USER

# 重新登录或使用 newgrp
newgrp www-data
```

#### 依赖包问题
```bash
# 更新 pip
pip install --upgrade pip

# 重新安装依赖
pip install --no-cache-dir -r requirements.txt
```

### 7. 性能优化建议

1. **调整数据库连接池**
   ```sql
   -- PostgreSQL 配置
   ALTER SYSTEM SET max_connections = 200;
   ```

2. **启用 Redis 缓存**
   ```bash
   # 配置 Redis 作为缓存
   sudo nano /etc/redis/redis.conf
   # 设置 maxmemory 和 maxmemory-policy
   ```

3. **优化 Nginx 配置**
   ```nginx
   # 启用 gzip 压缩
   gzip on;
   gzip_types text/plain text/css application/json application/javascript;
   ```

4. **调整 Uvicorn 配置**
   ```bash
   # 增加工作进程数
   uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
   ```

## 更新和维护计划

### 定期任务
- 每日：检查服务状态和日志
- 每周：备份数据库
- 每月：更新依赖包和安全补丁
- 每季度：性能评估和优化

### 备份策略
- 数据库：每日全量备份
- 文档文件：每周备份
- 配置文件：版本控制管理

### 应急响应
1. 监控系统告警
2. 快速诊断问题
3. 按照预案处理
4. 记录和总结