import os
import numpy as np
from typing import List, Optional, Union
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseEmbeddingService(ABC):
    """向量嵌入服务基类"""

    @abstractmethod
    async def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """生成文本向量"""
        pass

    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """批量生成文本向量"""
        pass


class OpenAIEmbeddingService(BaseEmbeddingService):
    """OpenAI 向量嵌入服务"""

    def __init__(self, model_name: str = "text-embedding-ada-002"):
        try:
            import openai
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_name = model_name

    async def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """生成单个文本向量"""
        try:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def generate_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """批量生成文本向量"""
        try:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            return [np.array(item.embedding) for item in response.data]
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return [None] * len(texts)


class AnthropicEmbeddingService(BaseEmbeddingService):
    """Anthropic 向量嵌入服务"""

    def __init__(self, model_name: str = "text-embedding-3-small"):
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")

        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model_name = model_name

    async def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """生成单个文本向量"""
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text
            )
            return np.array(response.embedding)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def generate_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """批量生成文本向量"""
        try:
            embeddings = []
            for text in texts:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=text
                )
                embeddings.append(np.array(response.embedding))
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return [None] * len(texts)


class LocalEmbeddingService(BaseEmbeddingService):
    """本地向量嵌入服务（使用sentence-transformers）"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers package is required. Install with: pip install sentence-transformers")

        self.model = SentenceTransformer(model_name)

    async def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """生成单个文本向量"""
        try:
            # sentence-transformers是同步的，所以用run_in_executor
            import asyncio
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode(text)
            )
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def generate_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """批量生成文本向量"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(texts)
            )
            return list(embeddings)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return [None] * len(texts)


class MockEmbeddingService(BaseEmbeddingService):
    """Mock 向量嵌入服务（用于测试）"""

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    async def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """生成随机向量"""
        return np.random.random(self.dimension)

    async def generate_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """批量生成随机向量"""
        return [np.random.random(self.dimension) for _ in texts]


def get_embedding_service() -> BaseEmbeddingService:
    """获取向量嵌入服务实例"""
    from src.config import get_settings

    settings = get_settings()

    # 优先使用OpenAI
    if settings.OPENAI_API_KEY:
        return OpenAIEmbeddingService(settings.EMBEDDING_MODEL_NAME)

    # 其次使用Anthropic
    if settings.ANTHROPIC_API_KEY:
        return AnthropicEmbeddingService(settings.EMBEDDING_MODEL_NAME)

    # 最后使用本地模型
    try:
        return LocalEmbeddingService()
    except ImportError:
        # 如果不可用，使用Mock服务
        logger.warning("No embedding service available, using mock service")
        return MockEmbeddingService()