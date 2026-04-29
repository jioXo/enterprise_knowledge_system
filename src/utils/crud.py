from typing import Type, TypeVar, Generic, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

# 泛型类型变量
ModelType = TypeVar("ModelType")


class CRUDBase(Generic[ModelType]):
    """基础CRUD操作类"""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """根据ID获取记录"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        **kwargs
    ) -> List[ModelType]:
        """获取多条记录"""
        query = db.query(self.model)
        for key, value in kwargs.items():
            if value is not None:
                query = query.filter(getattr(self.model, key) == value)
        return query.offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: dict) -> ModelType:
        """创建记录"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: dict
    ) -> ModelType:
        """更新记录"""
        obj_data = db_obj.__dict__
        for field, value in obj_in.items():
            if field in obj_data and value is not None:
                setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> ModelType:
        """删除记录"""
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj

    def exists(self, db: Session, **kwargs) -> bool:
        """检查记录是否存在"""
        query = db.query(self.model)
        for key, value in kwargs.items():
            query = query.filter(getattr(self.model, key) == value)
        return db.query(query.exists()).scalar()


class CRUDDocument(CRUDBase):
    """文档CRUD操作"""

    def get_by_platform_id(self, db: Session, platform_id: int) -> List:
        """根据平台ID获取文档"""
        return db.query(self.model).filter(
            and_(
                self.model.platform_id == platform_id,
                self.model.is_deleted == False
            )
        ).all()

    def search_by_title(self, db: Session, keyword: str) -> List:
        """根据标题搜索文档"""
        return db.query(self.model).filter(
            and_(
                self.model.title.ilike(f"%{keyword}%"),
                self.model.is_deleted == False
            )
        ).all()

    def get_outdated_documents(self, db: Session) -> List:
        """获取过时的文档"""
        return db.query(self.model).filter(
            self.model.status == "outdated"
        ).all()


class CRUDKnowledgeChunk(CRUDBase):
    """知识块CRUD操作"""

    def get_by_document_id(self, db: Session, document_id: int) -> List:
        """根据文档ID获取知识块"""
        return db.query(self.model).filter(
            self.model.document_id == document_id
        ).all()

    def search_by_keywords(self, db: Session, keywords: List[str]) -> List:
        """根据关键词搜索知识块"""
        query = db.query(self.model)
        for keyword in keywords:
            query = query.filter(
                or_(
                    self.model.keywords.ilike(f"%{keyword}%"),
                    self.model.content.ilike(f"%{keyword}%")
                )
            )
        return query.all()

    def get_active_chunks(self, db: Session, limit: int = 100) -> List:
        """获取活跃的知识块"""
        return db.query(self.model).filter(
            self.model.status == "active"
        ).limit(limit).all()


class CRUDInteraction(CRUDBase):
    """交互记录CRUD操作"""

    def get_by_user_id(self, db: Session, user_id: int) -> List:
        """根据用户ID获取交互记录"""
        return db.query(self.model).filter(
            self.model.user_id == user_id
        ).all()

    def get_pending_interactions(self, db: Session) -> List:
        """获取待处理的交互记录"""
        return db.query(self.model).filter(
            self.model.status == "pending"
        ).all()

    def update_feedback(self, db: Session, interaction_id: int, feedback: str, rating: float = None) -> bool:
        """更新用户反馈"""
        interaction = db.query(self.model).filter(
            self.model.id == interaction_id
        ).first()

        if interaction:
            interaction.feedback = feedback
            if rating is not None:
                interaction.rating = rating
                interaction.status = "resolved"
            db.commit()
            return True
        return False


# 实例化CRUD操作
crud_document = CRUDDocument()
crud_knowledge_chunk = CRUDKnowledgeChunk()
crud_interaction = CRUDInteraction()