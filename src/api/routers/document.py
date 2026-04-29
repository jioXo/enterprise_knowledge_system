from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import asyncio
import json

from src.models.database import get_db
from src.models.document import Document, DocumentStatus, DocumentType
from src.models.platform import Platform
from src.agents.document_sync_agent import DocumentSyncAgent
from src.config import get_settings
from src.utils.crud import crud_document, crud_platform
from src.utils.vector_db import get_vector_db

router = APIRouter()
settings = get_settings()

@router.post("/sync/{platform_id}")
async def sync_documents(
    platform_id: int,
    force_sync: bool = Form(default=False),
    db: Session = Depends(get_db)
):
    """同步平台文档"""
    try:
        # 验证平台存在
        platform = db.query(Platform).filter(Platform.id == platform_id).first()
        if not platform:
            raise HTTPException(status_code=404, detail="Platform not found")

        # 执行同步
        sync_agent = DocumentSyncAgent({})
        result = await sync_agent.process({
            "platform_id": platform_id,
            "force_sync": force_sync
        })

        return {
            "success": True,
            "message": "Document sync completed",
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    platform_id: int = Form(...),
    document_type: str = Form(default="other"),
    db: Session = Depends(get_db)
):
    """上传文档"""
    try:
        # 验证平台存在
        platform = db.query(Platform).filter(Platform.id == platform_id).first()
        if not platform:
            raise HTTPException(status_code=404, detail="Platform not found")

        # 验证文件类型
        allowed_extensions = settings.document_config["supported_formats"]
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="File type not supported")

        # 创建文件路径
        docs_path = Path(settings.RAW_DOCS_PATH) / str(platform_id)
        docs_path.mkdir(parents=True, exist_ok=True)

        file_path = docs_path / file.filename

        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 解析文档内容
        from src.agents.document_sync_agent import DocumentSyncAgent
        sync_agent = DocumentSyncAgent({})

        content, metadata = await sync_agent.parse_document_file(file_path)
        if not content:
            raise HTTPException(status_code=400, detail="Failed to parse document")

        # 创建文档记录
        document_data = {
            "title": metadata.get("title", file.filename),
            "content": content,
            "summary": metadata.get("summary", ""),
            "document_type": DocumentType(document_type),
            "status": DocumentStatus.PUBLISHED,
            "author": metadata.get("author", ""),
            "department": metadata.get("department", ""),
            "tags": metadata.get("tags", ""),
            "version": "1.0",
            "word_count": metadata.get("word_count", 0),
            "platform_id": platform_id,
            "source_id": str(file_path),
            "source_url": str(file_path.absolute())
        }

        document = crud_document.create(db, obj_in=document_data)

        # 创建知识块
        from src.models.knowledge import KnowledgeChunk
        from src.utils.embedding import get_embedding_service

        embedding_service = get_embedding_service()

        # 文档分块
        from src.utils.text_processor import TextProcessor
        text_processor = TextProcessor()
        chunks = text_processor.chunk_text(content, chunk_size=500, overlap=50)

        for i, chunk_content in enumerate(chunks):
            chunk_summary = text_processor.generate_summary(chunk_content)
            embedding = await embedding_service.generate_embedding(chunk_content)

            chunk_data = {
                "document_id": document.id,
                "content": chunk_content,
                "summary": chunk_summary,
                "chunk_index": i,
                "vector_id": f"doc_{document.id}_chunk_{i}",
                "embedding": embedding.tolist() if embedding is not None else None,
                "keywords": ",".join(text_processor.extract_keywords(chunk_content)[:5]),
                "topics": text_processor.extract_topics(chunk_content),
                "importance_score": 0.5,
                "word_count": len(chunk_content.split()),
                "start_char": 0,
                "end_char": len(chunk_content),
                "status": "active"
            }

            crud_document.create(db, obj_in=chunk_data)

        db.commit()

        return {
            "success": True,
            "message": "Document uploaded successfully",
            "document": {
                "id": document.id,
                "title": document.title,
                "type": document.document_type,
                "status": document.status
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def get_documents(
    platform_id: Optional[int] = None,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """获取文档列表"""
    try:
        kwargs = {"is_deleted": False}
        if platform_id:
            kwargs["platform_id"] = platform_id
        if document_type:
            kwargs["document_type"] = document_type
        if status:
            kwargs["status"] = status

        documents = crud_document.get_multi(db, skip=skip, limit=limit, **kwargs)

        return {
            "success": True,
            "data": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "summary": doc.summary,
                    "document_type": doc.document_type,
                    "status": doc.status,
                    "author": doc.author,
                    "department": doc.department,
                    "tags": doc.tags,
                    "created_at": doc.created_at.isoformat(),
                    "updated_at": doc.updated_at.isoformat()
                }
                for doc in documents
            ],
            "total": len(documents),
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}")
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """获取文档详情"""
    try:
        document = crud_document.get(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "success": True,
            "data": {
                "id": document.id,
                "title": document.title,
                "content": document.content,
                "summary": document.summary,
                "document_type": document.document_type,
                "status": document.status,
                "author": document.author,
                "department": document.department,
                "tags": document.tags,
                "version": document.version,
                "word_count": document.word_count,
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat(),
                "platform": {
                    "id": document.platform.id,
                    "name": document.platform.name,
                    "type": document.platform.platform_type
                } if document.platform else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{document_id}")
async def update_document(
    document_id: int,
    update_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """更新文档"""
    try:
        document = crud_document.get(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # 只允许更新特定字段
        allowed_fields = ["title", "summary", "tags", "status"]
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not filtered_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        updated_document = crud_document.update(db, db_obj=document, obj_in=filtered_data)

        return {
            "success": True,
            "message": "Document updated successfully",
            "document": {
                "id": updated_document.id,
                "title": updated_document.title,
                "status": updated_document.status
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """删除文档"""
    try:
        document = crud_document.get(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # 软删除
        crud_document.update(db, db_obj=document, obj_in={"is_deleted": True})

        return {
            "success": True,
            "message": "Document deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_documents(
    keyword: str = Query(..., min_length=1),
    platform_id: Optional[int] = None,
    document_type: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """搜索文档"""
    try:
        # 先搜索标题
        title_results = crud_document.search_by_title(db, keyword)

        # 如果指定了平台，过滤结果
        if platform_id:
            title_results = [doc for doc in title_results if doc.platform_id == platform_id]

        # 如果指定了文档类型，过滤结果
        if document_type:
            title_results = [doc for doc in title_results if doc.document_type == document_type]

        # 分页
        start = skip
        end = start + limit
        paginated_results = title_results[start:end]

        return {
            "success": True,
            "data": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "summary": doc.summary,
                    "document_type": doc.document_type,
                    "status": doc.status,
                    "author": doc.author,
                    "department": doc.department,
                    "tags": doc.tags,
                    "created_at": doc.created_at.isoformat(),
                    "updated_at": doc.updated_at.isoformat()
                }
                for doc in paginated_results
            ],
            "total": len(title_results),
            "skip": skip,
            "limit": limit,
            "keyword": keyword
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))