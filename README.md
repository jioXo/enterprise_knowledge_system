# 企业内部知识管理系统

基于多 Agent 协作架构的企业内部知识管理系统，支持多平台文档同步、智能检索和答案生成。

## 项目特点

### 🎯 核心痛点解决
- **信息分散**：统一管理飞书、Confluence、本地文档等多个平台的文档
- **查找困难**：通过智能语义检索快速找到相关信息
- **版本不一致**：自动检测文档更新，保证信息时效性
- **重复咨询**：智能问答减少人工咨询成本

### 🤖 多 Agent 协作架构
1. **文档同步与治理 Agent**：自动同步、去重、版本管理
2. **用户意图理解与检索 Agent**：语义理解、智能检索、重排序
3. **答案生成与校验 Agent**：多源综合、矛盾检测、置信度评估

## 快速开始

### 环境要求
- Python 3.8+
- PostgreSQL (可选，默认使用SQLite)
- Redis (可选，用于缓存)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd enterprise_knowledge_system
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

5. **启动服务**
```bash
python main.py
```

6. **访问服务**
- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health

## 核心功能

### 📄 文档管理
- 支持多种文档格式：PDF、Word、Excel、Markdown、TXT
- 自动提取文档元数据：标题、作者、部门、关键词
- 智能分块处理，支持长文档检索
- 版本控制和更新检测

### 🔍 智能检索
- 语义理解：识别用户真实意图
- 向量检索：基于内容的相似度匹配
- 多因素排序：相似度、相关性、时效性
- 智能推荐：相关问题和文档

### 📝 答案生成
- 多源信息综合
- 矛盾信息检测
- 信息时效性验证
- 格式化答案生成

### 🎯 精准问答
- 区分"如何申请年假"和"年假审批流程变更"
- 适配企业话术风格
- 标注信息来源和更新时间
- 无法回答时自动流转

## API 使用示例

### 文档查询
```python
import requests

response = requests.post("http://localhost:8000/api/v1/query", json={
    "query": "如何申请年假",
    "user_id": 1
})

print(response.json())
```

### 上传文档
```python
import requests

with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/document/upload",
        files={"file": f},
        data={
            "platform_id": 1,
            "document_type": "policy"
        }
    )

print(response.json())
```

### 同步文档
```python
response = requests.post(
    "http://localhost:8000/api/v1/document/sync/1",
    data={"force_sync": True}
)

print(response.json())
```

## 系统架构

### 数据流
1. **文档同步**：定期扫描各平台文档
2. **内容解析**：提取文本和元数据
3. **向量化**：生成文本嵌入向量
4. **知识构建**：建立知识库索引
5. **查询处理**：意图识别和检索
6. **答案生成**：多源信息整合
7. **反馈学习**：持续优化结果

### 技术栈
- **后端**：FastAPI + SQLAlchemy
- **AI框架**：LangChain
- **向量数据库**：ChromaDB/Milvus
- **文本处理**：PyMuPDF、python-docx
- **缓存**：Redis
- **数据库**：PostgreSQL/SQLite

## 配置说明

### 主要配置项
- `DATABASE_URL`: 数据库连接字符串
- `OPENAI_API_KEY`: OpenAI API 密钥
- `REDIS_URL`: Redis 连接地址
- `VECTOR_DB_TYPE`: 向量数据库类型
- `SYNC_INTERVAL`: 文档同步间隔（秒）

### 平台配置
在数据库中配置支持的文档平台：
- 飞书
- Confluence
- 本地文档
- Notion
- SharePoint

## 部署指南

### Docker 部署
```bash
# 构建镜像
docker build -t enterprise-knowledge-system .

# 运行容器
docker run -d -p 8000:8000 \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  enterprise-knowledge-system
```

### 生产环境配置
1. 使用 PostgreSQL 作为主数据库
2. 配置 Redis 缓存
3. 使用 Nginx 反向代理
4. 配置 SSL 证书
5. 设置日志轮转

## 监控和维护

### 日志管理
- 应用日志：`./logs/app.log`
- 错误日志：自动记录异常
- 访问日志：记录 API 调用

### 性能监控
- 健康检查：`/api/v1/health`
- 指标监控：`/api/v1/metrics`
- 缓存统计：`/api/v1/admin/cache-stats`

### 数据备份
- 定期备份数据库
- 备份向量数据库
- 备份原始文档

## 扩展开发

### 添加新 Agent
1. 继承 `BaseAgent` 类
2. 实现 `process` 方法
3. 注册到路由中

### 添加新文档类型
1. 扩展 `DocumentType` 枚举
2. 更新文档解析逻辑
3. 配置支持格式

### 自定义检索策略
1. 实现 `BaseVectorDB` 接口
2. 配置使用新的向量数据库
3. 调整检索参数

## 故障排查

### 常见问题
1. **文档同步失败**：检查文件权限和格式
2. **检索结果不准确**：调整向量嵌入模型
3. **内存占用过高**：优化分块大小
4. **API 响应慢**：检查缓存配置

### 调试模式
设置 `DEBUG=True` 启用详细日志：
```bash
export DEBUG=True
python main.py
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License

---

**注意**：本系统仅供企业内部使用，请确保遵守相关法律法规。