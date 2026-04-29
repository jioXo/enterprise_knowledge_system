import uvicorn
from src.config import get_settings
from src.api.main import app

def main():
    """应用入口函数"""
    settings = get_settings()

    print(f"🚀 启动 {settings.APP_NAME} v{settings.VERSION}")
    print(f"📝 日志级别: {settings.LOG_LEVEL}")
    print(f"🗄️  数据库: {settings.DATABASE_URL}")
    print(f"🔍 向量数据库: {settings.VECTOR_DB_TYPE} @ {settings.VECTOR_DB_PATH}")
    print(f"📄 文档路径: {settings.RAW_DOCS_PATH}")

    # 启动服务
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

if __name__ == "__main__":
    main()