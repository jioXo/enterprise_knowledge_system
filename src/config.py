import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 基础配置
    APP_NAME: str = "企业知识管理系统"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/enterprise_knowledge.db"
    SQLALCHEMY_DATABASE_URL: str = "sqlite:///./data/enterprise_knowledge_test.db"

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # 向量数据库配置
    VECTOR_DB_PATH: str = "./data/vector_db"
    VECTOR_DB_TYPE: str = "chroma"  # chroma, milvus, faiss

    # 文档存储配置
    RAW_DOCS_PATH: str = "./data/raw_docs"
    PROCESSED_DOCS_PATH: str = "./data/processed_docs"

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"

    # 文档同步配置
    SYNC_INTERVAL: int = 3600  # 秒
    DOCUMENT_PLATFORMS: List[str] = ["feishu", "confluence", "local"]
    MAX_DOCUMENT_SIZE: int = 10485760  # 10MB

    # Agent 配置
    AGENT_MODEL_NAME: str = "gpt-4"
    EMBEDDING_MODEL_NAME: str = "text-embedding-ada-002"
    MAX_TOKENS: int = 4000
    TEMPERATURE: float = 0.7

    # API 密钥
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def database_config(self) -> dict:
        """获取数据库配置"""
        return {
            "url": self.DATABASE_URL,
            "echo": self.DEBUG
        }

    @property
    def vector_db_config(self) -> dict:
        """获取向量数据库配置"""
        return {
            "type": self.VECTOR_DB_TYPE,
            "path": self.VECTOR_DB_PATH,
            "embedding_model": self.EMBEDDING_MODEL_NAME
        }

    @property
    def document_config(self) -> dict:
        """获取文档配置"""
        return {
            "raw_path": self.RAW_DOCS_PATH,
            "processed_path": self.PROCESSED_DOCS_PATH,
            "platforms": self.DOCUMENT_PLATFORMS,
            "max_size": self.MAX_DOCUMENT_SIZE
        }


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    return Settings()