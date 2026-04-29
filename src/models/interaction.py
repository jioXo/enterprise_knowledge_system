from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .database import Base


class InteractionType(str, Enum):
    """交互类型"""
    QUESTION = "question"  # 提问
    ANSWER = "answer"  # 回答
    FEEDBACK = "feedback"  # 反馈
    CLICK = "click"  # 点击查看
    SEARCH = "search"  # 搜索


class InteractionStatus(str, Enum):
    """交互状态"""
    PENDING = "pending"
    RESOLVED = "resolved"
    REJECTED = "rejected"
   escalated = "escalated"


class Interaction(Base):
    """交互记录模型"""
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    interaction_type = Column(SQLEnum(InteractionType), nullable=False, comment="交互类型")
    status = Column(SQLEnum(InteractionStatus), default=InteractionStatus.PENDING, comment="状态")

    # 内容
    query = Column(Text, comment="用户问题")
    response = Column(Text, comment="系统回答")
    feedback = Column(String(500), comment="用户反馈")
    rating = Column(Float, nullable=True, comment="评分（1-5）")

    # 知识块关联
    knowledge_chunk_id = Column(Integer, ForeignKey("knowledge_chunks.id"), comment="关联的知识块ID")
    document_id = Column(Integer, ForeignKey("documents.id"), comment="关联的文档ID")

    # 统计信息
    relevance_score = Column(Float, default=0.0, comment="相关性评分")
    response_time = Column(Float, comment="响应时间（秒）")
    tokens_used = Column(Integer, default=0, comment="使用的token数")

    # 处理信息
    assigned_to = Column(String(100), comment="处理人")
    resolved_at = Column(DateTime, comment="解决时间")
    resolution_notes = Column(Text, comment="解决备注")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    user = relationship("User", back_populates="interactions")
    knowledge_chunk = relationship("KnowledgeChunk", back_populates="interactions")
    document = relationship("Document", back_populates="interactions")

    def __repr__(self):
        return f"<Interaction(id={self.id}, user_id={self.user_id}, type='{self.interaction_type}')>"