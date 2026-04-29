#!/usr/bin/env python3
"""
系统运行脚本
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.config import get_settings
from src.models.database import init_db
from src.utils.logger import logger_manager

# 设置日志
logger = logger_manager.get_logger(__name__)

def setup_directories():
    """创建必要的目录"""
    settings = get_settings()

    directories = [
        Path(settings.RAW_DOCS_PATH),
        Path(settings.PROCESSED_DOCS_PATH),
        Path(settings.VECTOR_DB_PATH),
        Path(settings.LOG_FILE).parent
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def initialize_database():
    """初始化数据库"""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

def main():
    """主函数"""
    # 加载配置
    settings = get_settings()

    # 设置日志级别
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))

    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {'Development' if settings.DEBUG else 'Production'}")

    # 创建必要的目录
    setup_directories()

    # 初始化数据库
    initialize_database()

    # 导入并启动应用
    from main import app
    import uvicorn

    logger.info(f"Server starting on {settings.HOST}:{settings.PORT}")

    try:
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower()
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()