from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Agent 基础类"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """处理数据的抽象方法"""
        pass

    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        # 子类可以重写此方法来实现具体的验证逻辑
        return True

    def format_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化输出结果"""
        result["agent_name"] = self.name
        result["timestamp"] = datetime.utcnow().isoformat()
        return result

    def log_error(self, error: Exception, context: str = ""):
        """记录错误日志"""
        error_msg = f"Error in {self.name}: {str(error)}"
        if context:
            error_msg += f" | Context: {context}"
        self.logger.error(error_msg, exc_info=True)

    def log_info(self, message: str, **kwargs):
        """记录信息日志"""
        self.logger.info(message, extra=kwargs)