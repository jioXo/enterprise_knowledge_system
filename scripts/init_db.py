#!/usr/bin/env python3
"""
数据库初始化脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.models.database import init_db, engine, Base
from src.models.document import Document, DocumentStatus, DocumentType
from src.models.platform import Platform, PlatformType
from src.models.user import User, UserRole
from src.models.interaction import Interaction
from src.models.knowledge import KnowledgeChunk
from src.utils.auth import auth_manager
from sqlalchemy.orm import Session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user(db: Session):
    """创建管理员用户"""
    # 检查是否已存在管理员用户
    admin_user = db.query(User).filter(User.username == "admin").first()
    if admin_user:
        logger.info("Admin user already exists")
        return admin_user

    # 创建管理员用户
    admin_user = User(
        username="admin",
        email="admin@example.com",
        full_name="系统管理员",
        role=UserRole.ADMIN,
        hashed_password=auth_manager.get_password_hash("admin123"),
        is_active=True,
        is_verified=True
    )

    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    logger.info("Admin user created successfully")
    return admin_user

def create_sample_platforms(db: Session):
    """创建示例平台"""
    platforms = [
        {
            "name": "本地文档",
            "platform_type": PlatformType.LOCAL,
            "description": "本地文件系统中的文档",
            "is_active": True,
            "sync_enabled": True
        },
        {
            "name": "飞书文档",
            "platform_type": PlatformType.FEISHU,
            "description": "飞书云文档空间",
            "is_active": True,
            "sync_enabled": True
        },
        {
            "name": "Confluence",
            "platform_type": PlatformType.CONFLUENCE,
            "description": "Atlassian Confluence",
            "is_active": False,
            "sync_enabled": False
        }
    ]

    for platform_data in platforms:
        # 检查平台是否已存在
        existing = db.query(Platform).filter(
            Platform.name == platform_data["name"]
        ).first()

        if not existing:
            platform = Platform(**platform_data)
            db.add(platform)
            logger.info(f"Created platform: {platform_data['name']}")

    db.commit()

def create_sample_documents(db: Session):
    """创建示例文档"""
    # 获取第一个平台
    platform = db.query(Platform).first()
    if not platform:
        logger.warning("No platform found, skipping sample documents")
        return

    # 示例文档数据
    sample_docs = [
        {
            "title": "员工手册",
            "content": """欢迎使用本公司！

第一章 入职指南
1.1 入职流程
新员工入职需要完成以下步骤：
1. 提交入职材料
2. 签订劳动合同
3. 办理社保公积金
4. 领取办公用品

1.2 试用期规定
试用期一般为3个月，表现优秀者可提前转正。

第二章 考勤制度
2.1 工作时间
周一至周五，9:00-18:00，午休1小时。

2.2 请假流程
- 病假：提供医院证明
- 年假：提前3天申请
- 事假：部门主管审批

第三章 薪酬福利
3.1 工资发放
每月15日发放上月工资，银行转账。

3.2 社保公积金
公司为员工缴纳五险一金，按照国家规定执行。

第四章 行为规范
4.1 职业操守
- 诚实守信
- 团队合作
- 客户至上

4.2 信息安全
- 保护公司机密
- 遵守保密协议
- 安全使用网络资源""",
            "document_type": DocumentType.MANUAL,
            "status": DocumentStatus.PUBLISHED,
            "author": "HR部门",
            "department": "人力资源",
            "tags": "入职,制度,手册",
            "platform_id": platform.id,
            "source_url": f"file://{Path('sampledocs/employee_handbook.pdf')}",
            "version": "1.0"
        },
        {
            "title": "年假申请流程",
            "content": """年假申请指南

1. 申请条件
- 工作满1年
- 年假天数：工作满1年5天，满10年10天，满20年15天
- 当年未休年假可结转至次年3月底

2. 申请流程
2.1 在线申请
- 登录OA系统
- 进入"请假申请"模块
- 选择"年假"类型
- 填写申请日期和事由
- 上传相关证明材料（如有）

2.2 审批流程
- 部门主管审批
- HR部门备案
- 系统自动生成休假通知

3. 注意事项
- 年假应提前3天申请
- 旺季（如节假日前后）可能需要更早申请
- 年假期间保持通讯畅通

4. 特殊情况
- 新入职员工当年年假按比例计算
- 离职时未休年假按工资标准折算""",
            "document_type": DocumentType.PROCEDURE,
            "status": DocumentStatus.PUBLISHED,
            "author": "HR部门",
            "department": "人力资源",
            "tags": "年假,申请,流程",
            "platform_id": platform.id,
            "source_url": f"file://{Path('sampledocs/annual_leave.pdf')}",
            "version": "2.1"
        },
        {
            "title": "信息安全政策",
            "content": """公司信息安全政策

1. 总则
1.1 目的
保护公司信息系统和数据的机密性、完整性和可用性。

1.2 适用范围
适用于全体员工和第三方合作伙伴。

2. 账户管理
2.1 账户创建
- 使用公司邮箱创建账户
- 强密码要求：至少8位，包含大小写字母、数字和特殊字符
- 定期更换密码（每90天）

2.2 账户注销
员工离职时，IT部门应在24小时内注销其账户。

3. 数据安全
3.1 数据分类
- 公开信息：可对外公开
- 内部信息：公司内部使用
- 机密信息：严格控制访问

3.2 数据保护
- 重要数据加密存储
- 定期备份
- 访问权限最小化

4. 网络安全
4.1 访问控制
- 使用VPN访问内网
- 禁止使用公共WiFi处理敏感数据
- 防火墙开启

4.2 设备安全
- 安装杀毒软件
- 及时更新系统补丁
- 禁止安装未经授权的软件

5. 安全事件处理
5.1 事件报告
发现安全问题立即报告IT部门。

5.2 应急响应
启动应急预案，控制影响范围，消除安全隐患。

6. 违规处理
违反本政策的，视情节轻重给予警告、记过直至解除劳动合同。""",
            "document_type": DocumentType.POLICY,
            "status": DocumentStatus.PUBLISHED,
            "author": "IT部门",
            "department": "技术",
            "tags": "安全,信息,政策",
            "platform_id": platform.id,
            "source_url": f"file://{Path('sampledocs/security_policy.pdf')}",
            "version": "3.0"
        }
    ]

    for doc_data in sample_docs:
        # 检查文档是否已存在
        existing = db.query(Document).filter(
            Document.title == doc_data["title"]
        ).first()

        if not existing:
            doc_data["word_count"] = len(doc_data["content"].split())
            document = Document(**doc_data)
            db.add(document)
            logger.info(f"Created document: {doc_data['title']}")

    db.commit()

def main():
    """主函数"""
    logger.info("Starting database initialization...")

    try:
        # 初始化数据库
        init_db()
        logger.info("Database tables created successfully")

        # 创建会话
        db = SessionLocal()

        try:
            # 创建管理员用户
            create_admin_user(db)

            # 创建示例平台
            create_sample_platforms(db)

            # 创建示例文档
            create_sample_documents(db)

            logger.info("Database initialization completed successfully!")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()