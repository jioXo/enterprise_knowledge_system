from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .database import Base


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"  # 管理员
    MANAGER = "manager"  # 经理
    EMPLOYEE = "employee"  # 普通员工
    HR = "hr"  # HR
   IT = "it"  # IT支持
   TRAINER = "trainer"  # 培训师


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, comment="用户名")
    email = Column(String(255), unique=True, nullable=False, comment="邮箱")
    full_name = Column(String(200), nullable=False, comment="姓名")
    role = Column(SQLEnum(UserRole), default=UserRole.EMPLOYEE, comment="角色")

    # 认证信息
    hashed_password = Column(String(255), nullable=False, comment="密码哈希")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_verified = Column(Boolean, default=False, comment="是否验证")

    # 部门信息
    department = Column(String(100), comment="部门")
    position = Column(String(100), comment="职位")
    employee_id = Column(String(50), comment="员工编号")

    # 偏好设置
    language = Column(String(10), default="zh-CN", comment="语言偏好")
    timezone = Column(String(50), default="Asia/Shanghai", comment="时区")

    # 统计信息
    total_questions = Column(Integer, default=0, comment="提问总数")
    helpful_answers = Column(Integer, default=0, comment="获得有用回答数")
    last_login_at = Column(DateTime, comment="最后登录时间")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    interactions = relationship("Interaction", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"