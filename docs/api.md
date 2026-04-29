# API 文档

## 概述

企业内部知识管理系统 RESTful API，提供文档管理、智能检索、用户交互等功能。

## 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **协议**: HTTPS
- **数据格式**: JSON

## 认证

大多数 API 需要认证，在请求头中添加：
```
Authorization: Bearer <token>
```

## 错误响应

所有错误响应格式：
```json
{
  "success": false,
  "error": "错误信息",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 429 | 请求过多 |
| 500 | 服务器错误 |

## API 端点

### 健康检查

#### GET /health

检查服务健康状况。

**响应**:
```json
{
  "status": "healthy",
  "database": "healthy",
  "cpu_usage": 45.2,
  "memory_usage": 67.8,
  "disk_usage": 23.4
}
```

### 查询接口

#### POST /query

智能文档查询。

**请求体**:
```json
{
  "query": "如何申请年假",
  "user_id": 1
}
```

**响应**:
```json
{
  "success": true,
  "query": "如何申请年假",
  "intent": "procedural_inquiry",
  "answer": "年假申请流程：\n1. 提前3天提交申请\n2. 部门主管审批\n3. HR备案\n...",
  "answer_type": "procedural_guide",
  "confidence": 0.95,
  "sources": [
    {
      "title": "员工手册",
      "document_id": 1,
      "url": "...",
      "updated_at": "2024-01-01T00:00:00Z",
      "confidence": 0.95
    }
  ],
  "warnings": [],
  "validation": {
    "is_valid": true,
    "warnings": []
  }
}
```

#### GET /history

获取查询历史。

**参数**:
- `user_id`: 用户ID (必需)
- `limit`: 返回数量，默认10，最大100
- `offset`: 偏移量，默认0

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "query": "如何申请年假",
      "response": "年假申请流程...",
      "rating": 4,
      "created_at": "2024-01-01T00:00:00Z",
      "status": "resolved"
    }
  ],
  "total": 10,
  "limit": 10,
  "offset": 0
}
```

#### POST /feedback/{interaction_id}

提交反馈。

**请求体**:
```json
{
  "feedback": "回答很清晰",
  "rating": 5
}
```

**响应**:
```json
{
  "success": true,
  "message": "Feedback submitted successfully"
}
```

#### GET /suggestions

获取建议问题。

**参数**:
- `query`: 查询关键词 (必需)
- `limit`: 返回数量，默认5，最大10

**响应**:
```json
{
  "success": true,
  "suggestions": [
    "关于年假申请材料的要求",
    "年假审批时间是多久",
    "年假可以分段申请吗"
  ]
}
```

#### GET /stats

获取查询统计。

**参数**:
- `user_id`: 用户ID (可选，不提供则返回全局统计)

**响应**:
```json
{
  "success": true,
  "statistics": {
    "total_queries": 100,
    "rated_queries": 85,
    "average_rating": 4.2,
    "status_distribution": {
      "resolved": 85,
      "pending": 10,
      "escalated": 5
    },
    "type_distribution": {
      "question": 80,
      "feedback": 20
    }
  }
}
```

### 文档管理

#### POST /sync/{platform_id}

同步平台文档。

**参数**:
- `force_sync`: 是否强制同步 (表单字段，默认false)

**响应**:
```json
{
  "success": true,
  "message": "Document sync completed",
  "result": {
    "synced_count": 10,
    "updated_count": 2,
    "created_count": 8,
    "deleted_count": 0,
    "errors": []
  }
}
```

#### POST /upload

上传文档。

**参数**:
- `file`: 文件 (必需)
- `platform_id`: 平台ID (表单字段，必需)
- `document_type`: 文档类型 (表单字段，默认"other")

**响应**:
```json
{
  "success": true,
  "message": "Document uploaded successfully",
  "document": {
    "id": 1,
    "title": "员工手册",
    "type": "policy",
    "status": "published"
  }
}
```

#### GET /documents

获取文档列表。

**参数**:
- `platform_id`: 平台ID (可选)
- `document_type`: 文档类型 (可选)
- `status`: 状态 (可选)
- `skip`: 偏移量，默认0
- `limit`: 返回数量，默认20，最大100

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "员工手册",
      "summary": "公司规章制度概述...",
      "document_type": "policy",
      "status": "published",
      "author": "HR部门",
      "department": "人力资源",
      "tags": "入职,制度",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 20,
  "skip": 0,
  "limit": 20
}
```

#### GET /documents/{document_id}

获取文档详情。

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "员工手册",
    "content": "完整文档内容...",
    "summary": "文档摘要...",
    "document_type": "policy",
    "status": "published",
    "author": "HR部门",
    "department": "人力资源",
    "tags": "入职,制度",
    "version": "1.0",
    "word_count": 5000,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "platform": {
      "id": 1,
      "name": "本地文档",
      "type": "local"
    }
  }
}
```

#### PUT /documents/{document_id}

更新文档。

**请求体**:
```json
{
  "title": "新标题",
  "summary": "新摘要",
  "tags": "新标签",
  "status": "published"
}
```

#### DELETE /documents/{document_id}

删除文档（软删除）。

**响应**:
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

#### GET /search

搜索文档。

**参数**:
- `keyword`: 搜索关键词 (必需)
- `platform_id`: 平台ID (可选)
- `document_type`: 文档类型 (可选)
- `skip`: 偏移量，默认0
- `limit`: 返回数量，默认20，最大100

**响应**:
```json
{
  "success": true,
  "data": [...],
  "total": 5,
  "skip": 0,
  "limit": 20,
  "keyword": "年假"
}
```

### 管理接口

#### GET /platforms

获取所有平台列表。

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "飞书文档",
      "platform_type": "feishu",
      "description": "飞书空间文档",
      "is_active": true,
      "sync_enabled": true,
      "total_documents": 100,
      "last_sync_at": "2024-01-01T00:00:00Z",
      "next_sync_at": "2024-01-02T00:00:00Z",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### POST /platforms

创建新平台。

**请求体**:
```json
{
  "name": "Confluence",
  "platform_type": "confluence",
  "description": "Confluence文档空间",
  "is_active": true,
  "sync_enabled": true
}
```

#### PUT /platforms/{platform_id}

更新平台配置。

**请求体**:
```json
{
  "name": "新名称",
  "description": "新描述",
  "is_active": false,
  "sync_enabled": true
}
```

#### GET /dashboard

获取仪表板统计。

**响应**:
```json
{
  "success": true,
  "statistics": {
    "documents": {
      "total": 1000,
      "active": 950,
      "outdated": 50
    },
    "platforms": {
      "total": 5,
      "active": 4
    },
    "users": {
      "total": 200,
      "active": 180
    }
  },
  "recent_interactions": [
    {
      "id": 1,
      "user_id": 1,
      "query": "如何申请年假",
      "created_at": "2024-01-01T00:00:00Z",
      "status": "resolved"
    }
  ]
}
```

#### GET /sync/schedule

获取同步计划。

**响应**:
```json
{
  "success": true,
  "schedule": [
    {
      "platform_id": 1,
      "platform_name": "飞书文档",
      "platform_type": "feishu",
      "last_sync_at": "2024-01-01T00:00:00Z",
      "next_sync_at": "2024-01-02T00:00:00Z",
      "time_until_hours": 24,
      "is_active": true,
      "sync_enabled": true
    }
  ]
}
```

## 使用示例

### Python 示例

```python
import requests

# 初始化会话
session = requests.Session()

# 用户登录（获取token）
login_response = session.post("http://localhost:8000/api/v1/login", json={
    "username": "admin",
    "password": "password"
})
token = login_response.json()["data"]["token"]
session.headers["Authorization"] = f"Bearer {token}"

# 查询文档
response = session.post("http://localhost:8000/api/v1/query", json={
    "query": "如何申请年假",
    "user_id": 1
})
print(response.json())

# 上传文档
with open("employee_handbook.pdf", "rb") as f:
    response = session.post(
        "http://localhost:8000/api/v1/document/upload",
        files={"file": f},
        data={"platform_id": 1, "document_type": "policy"}
    )
    print(response.json())
```

### JavaScript 示例

```javascript
// 查询文档
const query = async () => {
    const response = await fetch('http://localhost:8000/api/v1/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({
            query: '如何申请年假',
            user_id: 1
        })
    });
    const result = await response.json();
    console.log(result);
};

// 获取文档列表
const getDocuments = async () => {
    const response = await fetch('http://localhost:8000/api/v1/documents', {
        method: 'GET',
        headers: {
            'Authorization': 'Bearer ' + token
        }
    });
    const result = await response.json();
    console.log(result);
};
```

## 限制说明

1. **查询长度**: 查询文本限制 1000 字符
2. **文件大小**: 单个文件限制 10MB
3. **返回数量**: 列表接口最多返回 100 条记录
4. **查询频率**: 默认限制每分钟 60 次查询
5. **并发请求**: 建议不超过 100 个并发连接

## 版本历史

### v1.0.0
- 初始版本
- 支持基本查询和文档管理
- 多 Agent 协作架构

## 更新日志

- 2024-01-01: v1.0.0 发布，支持核心功能