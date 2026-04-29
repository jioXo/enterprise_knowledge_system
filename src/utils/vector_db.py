import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class BaseVectorDB(ABC):
    """向量数据库基类"""

    @abstractmethod
    def add_vectors(self, vectors: List[np.ndarray], metadata: List[Dict], ids: List[str]) -> bool:
        """添加向量"""
        pass

    @abstractmethod
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """搜索相似向量"""
        pass

    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        pass

    @abstractmethod
    def get_metadata(self, id: str) -> Optional[Dict]:
        """获取元数据"""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """清空数据库"""
        pass


class ChromaVectorDB(BaseVectorDB):
    """Chroma 向量数据库"""

    def __init__(self, path: str, collection_name: str = "enterprise_knowledge"):
        try:
            import chromadb
        except ImportError:
            raise ImportError("chromadb package is required. Install with: pip install chromadb")

        self.path = path
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=path)

        # 创建或获取集合
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_vectors(self, vectors: List[np.ndarray], metadata: List[Dict], ids: List[str]) -> bool:
        """添加向量"""
        try:
            # 转换numpy数组为列表
            vectors_list = [v.tolist() for v in vectors]

            # 准备数据
            documents = [meta.get("content", "") for meta in metadata]

            # 添加到集合
            self.collection.add(
                embeddings=vectors_list,
                documents=documents,
                metadatas=metadata,
                ids=ids
            )

            return True
        except Exception as e:
            logger.error(f"Failed to add vectors to ChromaDB: {e}")
            return False

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """搜索相似向量"""
        try:
            # 转换numpy数组为列表
            query_vector_list = query_vector.tolist()

            # 执行搜索
            results = self.collection.query(
                query_embeddings=[query_vector_list],
                n_results=top_k,
                include=["metadatas", "distances"]
            )

            # 格式化结果
            formatted_results = []
            for i, (id, distance, metadata) in enumerate(zip(
                results["ids"][0],
                results["distances"][0],
                results["metadatas"][0]
            )):
                formatted_results.append((id, float(distance), metadata))

            return formatted_results
        except Exception as e:
            logger.error(f"Failed to search in ChromaDB: {e}")
            return []

    def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        try:
            self.collection.delete(ids=ids)
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors from ChromaDB: {e}")
            return False

    def get_metadata(self, id: str) -> Optional[Dict]:
        """获取元数据"""
        try:
            results = self.collection.get(ids=[id], include=["metadatas"])
            return results["metadatas"][0] if results["metadatas"] else None
        except Exception as e:
            logger.error(f"Failed to get metadata from ChromaDB: {e}")
            return None

    def clear(self) -> bool:
        """清空数据库"""
        try:
            # 删除集合
            self.client.delete_collection(name=self.collection_name)
            # 重新创建
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            return True
        except Exception as e:
            logger.error(f"Failed to clear ChromaDB: {e}")
            return False


class MilvusVectorDB(BaseVectorDB):
    """Milvus 向量数据库"""

    def __init__(self, host: str = "localhost", port: int = 19530, collection_name: str = "enterprise_knowledge"):
        try:
            from pymilvus import connections, Collection
        except ImportError:
            raise ImportError("pymilvus package is required. Install with: pip install pymilvus")

        self.host = host
        self.port = port
        self.collection_name = collection_name

        # 连接到Milvus
        connections.connect("default", host=host, port=port)

        # 创建集合（如果不存在）
        self._create_collection()

    def _create_collection(self):
        """创建集合"""
        from pymilvus import Collection, FieldSchema, CollectionSchema, DataType

        # 检查集合是否存在
        if Collection.exists(self.collection_name):
            return

        # 定义字段
        fields = [
            FieldSchema("id", DataType.INT64, is_primary=True),
            FieldSchema("vector", DataType.FLOAT_VECTOR, dim=768),  # 假设维度为768
            FieldSchema("metadata", DataType.JSON),
        ]

        # 创建模式
        schema = CollectionSchema(fields, "Enterprise Knowledge Collection")

        # 创建集合
        self.collection = Collection(self.collection_name, schema)

        # 创建索引
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 100}
        }
        self.collection.create_index("vector", index_params)

    def add_vectors(self, vectors: List[np.ndarray], metadata: List[Dict], ids: List[str]) -> bool:
        """添加向量"""
        try:
            # 准备数据
            entities = []
            for i, (vector, meta, id_str) in enumerate(zip(vectors, metadata, ids)):
                entities.append([
                    int(id_str.split("_")[-1]),  # 从ID中提取数字
                    vector.tolist(),
                    meta
                ])

            # 插入数据
            self.collection.insert(entities)
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors to Milvus: {e}")
            return False

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """搜索相似向量"""
        try:
            # 执行搜索
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10}
            }

            results = self.collection.search(
                data=[query_vector.tolist()],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["metadata"]
            )

            # 格式化结果
            formatted_results = []
            for hits in results:
                for hit in hits:
                    id_str = f"doc_{hit.id}"
                    formatted_results.append((id_str, float(hit.distance), hit.metadata))

            return formatted_results
        except Exception as e:
            logger.error(f"Failed to search in Milvus: {e}")
            return []

    def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        try:
            # 将字符串ID转换为数字
            int_ids = [int(id_str.split("_")[-1]) for id_str in ids]
            self.collection.delete(f"id in {int_ids}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors from Milvus: {e}")
            return False

    def get_metadata(self, id: str) -> Optional[Dict]:
        """获取元数据"""
        try:
            int_id = int(id.split("_")[-1])
            results = self.collection.query(expr=f"id == {int_id}", output_fields=["metadata"])
            return results[0]["metadata"] if results else None
        except Exception as e:
            logger.error(f"Failed to get metadata from Milvus: {e}")
            return None

    def clear(self) -> bool:
        """清空数据库"""
        try:
            self.collection.drop()
            self._create_collection()
            return True
        except Exception as e:
            logger.error(f"Failed to clear Milvus: {e}")
            return False


class SimpleVectorDB(BaseVectorDB):
    """简单的内存向量数据库（用于测试）"""

    def __init__(self):
        self.vectors = {}  # id -> vector
        self.metadata = {}  # id -> metadata

    def add_vectors(self, vectors: List[np.ndarray], metadata: List[Dict], ids: List[str]) -> bool:
        """添加向量"""
        try:
            for vector, meta, id_str in zip(vectors, metadata, ids):
                self.vectors[id_str] = vector
                self.metadata[id_str] = meta
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors to SimpleVectorDB: {e}")
            return False

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """搜索相似向量"""
        try:
            # 计算余弦相似度
            similarities = []
            for id_str, vector in self.vectors.items():
                similarity = self._cosine_similarity(query_vector, vector)
                similarities.append((id_str, similarity, self.metadata[id_str]))

            # 排序并返回top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
        except Exception as e:
            logger.error(f"Failed to search in SimpleVectorDB: {e}")
            return []

    def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        try:
            for id_str in ids:
                if id_str in self.vectors:
                    del self.vectors[id_str]
                if id_str in self.metadata:
                    del self.metadata[id_str]
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors from SimpleVectorDB: {e}")
            return False

    def get_metadata(self, id: str) -> Optional[Dict]:
        """获取元数据"""
        return self.metadata.get(id)

    def clear(self) -> bool:
        """清空数据库"""
        self.vectors.clear()
        self.metadata.clear()
        return True

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def get_vector_db(config: Dict) -> BaseVectorDB:
    """获取向量数据库实例"""
    db_type = config.get("type", "simple")
    path = config.get("path", "./data/vector_db")

    if db_type == "chroma":
        return ChromaVectorDB(path)
    elif db_type == "milvus":
        return MilvusVectorDB()
    elif db_type == "simple":
        return SimpleVectorDB()
    else:
        logger.warning(f"Unknown vector db type: {db_type}, using simple")
        return SimpleVectorDB()