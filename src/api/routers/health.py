from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.models.database import get_db
from src.config import get_settings
import psutil
import os

router = APIRouter()

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """健康检查端点"""
    settings = get_settings()

    # 检查数据库连接
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # 获取系统信息
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage('/').percent

    return {
        "status": "healthy",
        "database": db_status,
        "cpu_usage": cpu_percent,
        "memory_usage": memory_percent,
        "disk_usage": disk_percent,
        "environment": settings.DEBUG and "development" or "production"
    }

@router.get("/metrics")
async def get_metrics():
    """获取系统指标"""
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory()._asdict(),
        "disk": psutil.disk_usage('/')._asdict(),
        "process": {
            "pid": os.getpid(),
            "memory_info": psutil.Process().memory_info()._asdict()
        }
    }