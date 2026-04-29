from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.config import get_settings
from src.models.database import init_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="企业内部知识管理系统 - 多 Agent 协作架构",
    debug=settings.DEBUG
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )

# 应用启动事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("Starting application...")

    # 初始化数据库
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    yield

    # 关闭时执行
    logger.info("Shutting down application...")

# 应用生命周期
app.router.lifespan_context = lifespan

# 注册路由
from src.api import query, document, admin, health

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(query.router, prefix="/api/v1", tags=["query"])
app.include_router(document.router, prefix="/api/v1", tags=["document"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/v1/health"
    }

@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)