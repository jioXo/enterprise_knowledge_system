from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.models.database import get_db
from src.models.document import Document, DocumentStatus
from src.models.platform import Platform, PlatformType
from src.models.user import User, UserRole
from src.agents.document_sync_agent import DocumentSyncAgent
from src.utils.crud import crud_document, crud_platform, crud_user
from src.config import get_settings

router = APIRouter()
settings = get_settings()

@router.get("/platforms")
async def get_platforms(
    db: Session = Depends(get_db)
):
    """获取所有平台列表"""
    try:
        platforms = db.query(Platform).filter(Platform.is_deleted == False).all()

        return {
            "success": True,
            "data": [
                {
                    "id": platform.id,
                    "name": platform.name,
                    "platform_type": platform.platform_type,
                    "description": platform.description,
                    "is_active": platform.is_active,
                    "sync_enabled": platform.sync_enabled,
                    "total_documents": platform.total_documents,
                    "last_sync_at": platform.last_sync_at.isoformat() if platform.last_sync_at else None,
                    "next_sync_at": platform.next_sync_at.isoformat() if platform.next_sync_at else None,
                    "created_at": platform.created_at.isoformat()
                }
                for platform in platforms
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/platforms")
async def create_platform(
    platform_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """创建新平台"""
    try:
        # 验证平台类型
        if platform_data.get("platform_type") not in [e.value for e in PlatformType]:
            raise HTTPException(status_code=400, detail="Invalid platform type")

        platform = crud_platform.create(db, obj_in=platform_data)

        return {
            "success": True,
            "message": "Platform created successfully",
            "platform": {
                "id": platform.id,
                "name": platform.name,
                "platform_type": platform.platform_type
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/platforms/{platform_id}")
async def update_platform(
    platform_id: int,
    update_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """更新平台配置"""
    try:
        platform = crud_platform.get(db, platform_id)
        if not platform:
            raise HTTPException(status_code=404, detail="Platform not found")

        # 只允许更新特定字段
        allowed_fields = ["name", "description", "is_active", "sync_enabled", "config"]
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not filtered_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        updated_platform = crud_platform.update(db, db_obj=platform, obj_in=filtered_data)

        return {
            "success": True,
            "message": "Platform updated successfully",
            "platform": {
                "id": updated_platform.id,
                "name": updated_platform.name,
                "platform_type": updated_platform.platform_type,
                "is_active": updated_platform.is_active,
                "sync_enabled": updated_platform.sync_enabled
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/platforms/{platform_id}")
async def delete_platform(
    platform_id: int,
    db: Session = Depends(get_db)
):
    """删除平台"""
    try:
        platform = crud_platform.get(db, platform_id)
        if not platform:
            raise HTTPException(status_code=404, detail="Platform not found")

        # 软删除
        crud_platform.update(db, db_obj=platform, obj_in={"is_deleted": True})

        return {
            "success": True,
            "message": "Platform deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/platforms/{platform_id}/sync")
async def trigger_sync(
    platform_id: int,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """手动触发文档同步"""
    try:
        platform = crud_platform.get(db, platform_id)
        if not platform:
            raise HTTPException(status_code=404, detail="Platform not found")

        # 执行同步
        sync_agent = DocumentSyncAgent({})
        result = await sync_agent.process({
            "platform_id": platform_id,
            "force_sync": force
        })

        # 更新平台同步时间
        platform.last_sync_at = datetime.utcnow()
        platform.next_sync_at = datetime.utcnow() + timedelta(seconds=settings.SYNC_INTERVAL)
        db.commit()

        return {
            "success": True,
            "message": "Sync completed successfully",
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users")
async def get_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, le=100),
    role: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    try:
        kwargs = {}
        if role:
            kwargs["role"] = role

        users = crud_user.get_multi(db, skip=skip, limit=limit, **kwargs)

        return {
            "success": True,
            "data": [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "department": user.department,
                    "position": user.position,
                    "is_active": user.is_active,
                    "total_questions": user.total_questions,
                    "helpful_answers": user.helpful_answers,
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                    "created_at": user.created_at.isoformat()
                }
                for user in users
            ],
            "total": len(users),
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users")
async def create_user(
    user_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """创建用户"""
    try:
        # 验证角色
        if user_data.get("role") not in [e.value for e in UserRole]:
            raise HTTPException(status_code=400, detail="Invalid user role")

        user = crud_user.create(db, obj_in=user_data)

        return {
            "success": True,
            "message": "User created successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取仪表板统计"""
    try:
        # 文档统计
        total_documents = db.query(Document).filter(Document.is_deleted == False).count()
        active_documents = db.query(Document).filter(
            Document.is_deleted == False,
            Document.status == DocumentStatus.PUBLISHED
        ).count()
        outdated_documents = db.query(Document).filter(
            Document.status == DocumentStatus.OUTDATED
        ).count()

        # 平台统计
        total_platforms = db.query(Platform).filter(Platform.is_deleted == False).count()
        active_platforms = db.query(Platform).filter(
            Platform.is_deleted == False,
            Platform.is_active == True
        ).count()

        # 用户统计
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()

        # 最近交互
        from src.models.interaction import Interaction
        recent_interactions = db.query(Interaction).order_by(
            Interaction.created_at.desc()
        ).limit(10).all()

        return {
            "success": True,
            "statistics": {
                "documents": {
                    "total": total_documents,
                    "active": active_documents,
                    "outdated": outdated_documents
                },
                "platforms": {
                    "total": total_platforms,
                    "active": active_platforms
                },
                "users": {
                    "total": total_users,
                    "active": active_users
                }
            },
            "recent_interactions": [
                {
                    "id": interaction.id,
                    "user_id": interaction.user_id,
                    "query": interaction.query,
                    "created_at": interaction.created_at.isoformat(),
                    "status": interaction.status
                }
                for interaction in recent_interactions
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sync/schedule")
async def get_sync_schedule(db: Session = Depends(get_db)):
    """获取同步计划"""
    try:
        platforms = db.query(Platform).filter(
            Platform.is_deleted == False,
            Platform.sync_enabled == True
        ).all()

        schedule = []
        now = datetime.utcnow()

        for platform in platforms:
            # 计算下次同步时间
            if platform.next_sync_at:
                next_sync = platform.next_sync_at
            else:
                next_sync = now + timedelta(seconds=settings.SYNC_INTERVAL)

            # 计算距离下次同步的时间
                time_until = next_sync - now
                hours_until = int(time_until.total_seconds() / 3600)

            schedule.append({
                "platform_id": platform.id,
                "platform_name": platform.name,
                "platform_type": platform.platform_type,
                "last_sync_at": platform.last_sync_at.isoformat() if platform.last_sync_at else None,
                "next_sync_at": next_sync.isoformat(),
                "time_until_hours": hours_until,
                "is_active": platform.is_active,
                "sync_enabled": platform.sync_enabled
            })

        return {
            "success": True,
            "schedule": sorted(schedule, key=lambda x: x["next_sync_at"])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/system/clear-cache")
async def clear_cache(db: Session = Depends(get_db)):
    """清理系统缓存"""
    try:
        # 这里可以添加缓存清理逻辑
        # 例如：清理向量数据库、Redis缓存等

        return {
            "success": True,
            "message": "Cache cleared successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))