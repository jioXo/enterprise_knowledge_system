from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from .database import Base


class KnowledgeChunkStatus(str, Enum):
    """知识块状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    OUTDATED = "outdated"
    DELETED = "deleted"


class KnowledgeChunk(Base):
    """知识块模型"""
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, comment="所属文档ID")
    content = Column(Text, nullable=False, comment="知识块内容")
    summary = Column(Text, comment="知识块摘要")
    chunk_index = Column(Integer, nullable=False, comment="块索引")

    # 向量信息
    vector_id = Column(String(500), unique=True, comment="向量ID")
    embedding = Column(JSON, comment="向量嵌入")

    # 关键词和标签
    keywords = Column(String(1000), comment="关键词（逗号分隔）")
    topics = Column(String(500), comment="主题")
    importance_score = Column(Float, default=0.0, comment="重要性评分")

    # 元数据
    word_count = Column(Integer, default=0, comment="字数")
    start_char = Column(Integer, comment="原文起始位置")
    end_char = Column(Integer, comment="原文结束位置")

    # 状态
    status = Column(String(20), default="active", comment="状态")
    is_archived = Column(Boolean, default=False, comment="是否已归档")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    document = relationship("Document", back_populates="knowledge_chunks")
    interactions = relationship("Interaction", back_populates="knowledge_chunk")

    def __repr__(self):
        return f"<KnowledgeChunk(id={self.id}, document_id={self.document_id}, status='{self.status}')>"