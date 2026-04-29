from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .database import Base


class DocumentStatus(str, Enum):
    """文档状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"
    OUTDATED = "outdated"


class DocumentType(str, Enum):
    """文档类型"""
    POLICY = "policy"  # 政策制度
    PROCEDURE = "procedure"  # 流程规范
    FAQ = "faq"  # 常见问题
    TRAINING = "training"  # 培训材料
    MANUAL = "manual"  # 操作手册
    REPORT = "report"  # 报告文档
    OTHER = "other"  # 其他


class Document(Base):
    """文档模型"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, comment="文档标题")
    content = Column(Text, nullable=False, comment="文档内容")
    summary = Column(Text, comment="文档摘要")
    document_type = Column(SQLEnum(DocumentType), nullable=False, default=DocumentType.OTHER, comment="文档类型")
    status = Column(SQLEnum(DocumentStatus), nullable=False, default=DocumentStatus.DRAFT, comment="文档状态")

    # 元数据
    author = Column(String(100), comment="作者")
    department = Column(String(100), comment="所属部门")
    tags = Column(String(500), comment="标签（逗号分隔）")
    version = Column(String(50), default="1.0", comment="版本号")
    word_count = Column(Integer, default=0, comment="字数")

    # 平台信息
    platform_id = Column(Integer, ForeignKey("platforms.id"), comment="来源平台ID")
    source_url = Column(String(1000), comment="来源URL")
    source_id = Column(String(500), comment="来源平台唯一ID")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    published_at = Column(DateTime, comment="发布时间")

    # 软删除
    is_deleted = Column(Boolean, default=False, comment="是否已删除")

    # 关联关系
    platform = relationship("Platform", back_populates="documents")
    knowledge_chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="document")

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', status='{self.status}')>"