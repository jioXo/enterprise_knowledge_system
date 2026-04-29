from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .database import Base


class PlatformType(str, Enum):
    """平台类型"""
    FEISHU = "feishu"  # 飞书
    CONFLUENCE = "confluence"  # Confluence
    LOCAL = "local"  # 本地文档
    NOTION = "notion"  # Notion
    SHAREPOINT = "sharepoint"  # SharePoint
    OTHER = "other"  # 其他


class Platform(Base):
    """平台模型"""
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="平台名称")
    platform_type = Column(SQLEnum(PlatformType), nullable=False, comment="平台类型")
    description = Column(Text, comment="平台描述")
    base_url = Column(String(500), comment="基础URL")

    # 配置信息
    config = Column(Text, comment="平台配置（JSON格式）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    sync_enabled = Column(Boolean, default=True, comment="是否启用同步")

    # 认证信息
    auth_config = Column(Text, comment="认证配置（JSON格式，加密存储）")

    # 统计信息
    total_documents = Column(Integer, default=0, comment="文档总数")
    last_sync_at = Column(DateTime, comment="最后同步时间")
    next_sync_at = Column(DateTime, comment="下次同步时间")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    documents = relationship("Document", back_populates="platform")

    def __repr__(self):
        return f"<Platform(id={self.id}, name='{self.name}', type='{self.platform_type}')>"