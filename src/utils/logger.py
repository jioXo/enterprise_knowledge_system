import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from src.config import get_settings

settings = get_settings()


class LoggerManager:
    """日志管理器"""

    def __init__(self):
        self.loggers = {}
        self._setup_logging()

    def _setup_logging(self):
        """设置日志配置"""
        # 创建日志目录
        log_dir = Path(settings.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 配置根日志记录器
        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(settings.LOG_FILE),
                logging.StreamHandler()
            ]
        )

    def get_logger(self, name: str) -> logging.Logger:
        """获取日志记录器"""
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        return self.loggers[name]

    def log_request(self, logger: logging.Logger, method: str, url: str,
                   status_code: int, response_time: float):
        """记录请求日志"""
        logger.info(
            f"Request {method} {url} - Status: {status_code} - Time: {response_time:.3f}s"
        )

    def log_error(self, logger: logging.Logger, error: Exception,
                  context: str = ""):
        """记录错误日志"""
        error_msg = f"Error: {str(error)}"
        if context:
            error_msg += f" | Context: {context}"
        logger.error(error_msg, exc_info=True)

    def log_agent_action(self, logger: logging.Logger, agent_name: str,
                        action: str, result: dict):
        """记录Agent操作日志"""
        logger.info(
            f"Agent '{agent_name}' - Action: {action} - "
            f"Result: {'Success' if result.get('success') else 'Failed'}"
        )

    def log_document_sync(self, logger: logging.Logger, platform_id: int,
                         result: dict):
        """记录文档同步日志"""
        logger.info(
            f"Document sync for platform {platform_id} - "
            f"Synced: {result.get('synced_count', 0)}, "
            f"Created: {result.get('created_count', 0)}, "
            f"Updated: {result.get('updated_count', 0)}, "
            f"Errors: {len(result.get('errors', []))}"
        )

    def log_user_interaction(self, logger: logging.Logger, user_id: int,
                           query: str, response: str, confidence: float):
        """记录用户交互日志"""
        logger.info(
            f"User interaction - User: {user_id} - "
            f"Query: {query[:50]}... - "
            f"Confidence: {confidence:.2f}"
        )

    def log_api_metrics(self, logger: logging.Logger, endpoint: str,
                       method: str, duration: float, status_code: int):
        """记录API指标日志"""
        logger.info(
            f"API metrics - {method} {endpoint} - "
            f"Duration: {duration:.3f}s - Status: {status_code}"
        )

    def log_system_event(self, logger: logging.Logger, event: str,
                        details: dict):
        """记录系统事件日志"""
        logger.info(f"System event: {event} - Details: {details}")


# 全局日志管理器实例
logger_manager = LoggerManager()


# 便捷函数
def get_logger(name: str) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return logger_manager.get_logger(name)