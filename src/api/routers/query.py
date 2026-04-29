from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from src.models.database import get_db
from src.models.interaction import Interaction
from src.agents.query_intent_agent import QueryIntentAgent
from src.agents.answer_generation_agent import AnswerGenerationAgent
from src.config import get_settings
from src.utils.crud import crud_interaction

router = APIRouter()

@router.post("/query")
async def query_documents(
    query_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """查询文档并生成答案"""
    try:
        # 1. 意图理解与检索
        intent_agent = QueryIntentAgent({})
        intent_result = await intent_agent.process(query_data)

        if not intent_result.get("success"):
            raise HTTPException(status_code=400, detail=intent_result.get("error", "Intent recognition failed"))

        # 2. 答案生成
        answer_data = {
            "query": query_data.get("query"),
            "results": intent_result.get("results", []),
            "user_id": query_data.get("user_id")
        }

        answer_agent = AnswerGenerationAgent({})
        answer_result = await answer_agent.process(answer_data)

        # 3. 返回结果
        return {
            "success": True,
            "query": query_data.get("query"),
            "intent": intent_result.get("intent"),
            "answer": answer_result.get("answer"),
            "answer_type": answer_result.get("answer_type"),
            "confidence": answer_result.get("confidence"),
            "sources": answer_result.get("sources", []),
            "warnings": answer_result.get("warnings", []),
            "validation": answer_result.get("validation", {}),
            "interaction_id": answer_result.get("interaction_id")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_query_history(
    user_id: int,
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """获取查询历史"""
    try:
        interactions = crud_interaction.get_multi(
            db,
            user_id=user_id,
            skip=offset,
            limit=limit,
            interaction_type="question"
        )

        return {
            "success": True,
            "data": [
                {
                    "id": interaction.id,
                    "query": interaction.query,
                    "response": interaction.response,
                    "rating": interaction.rating,
                    "created_at": interaction.created_at.isoformat(),
                    "status": interaction.status
                }
                for interaction in interactions
            ],
            "total": len(interactions),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback/{interaction_id}")
async def submit_feedback(
    interaction_id: int,
    feedback_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """提交反馈"""
    try:
        success = crud_interaction.update_feedback(
            db,
            interaction_id,
            feedback_data.get("feedback"),
            feedback_data.get("rating")
        )

        if not success:
            raise HTTPException(status_code=404, detail="Interaction not found")

        return {
            "success": True,
            "message": "Feedback submitted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suggestions")
async def get_suggestions(
    query: str,
    limit: int = Query(default=5, le=10),
    db: Session = Depends(get_db)
):
    """获取建议问题"""
    try:
        from src.agents.query_intent_agent import QueryIntentAgent

        intent_agent = QueryIntentAgent({})
        results = await intent_agent.process({"query": query})

        suggestions = await intent_agent.suggest_follow_up_questions(
            query,
            results.get("results", [])
        )

        return {
            "success": True,
            "suggestions": suggestions[:limit]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_query_stats(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取查询统计"""
    try:
        # 获取总的统计信息
        if user_id:
            interactions = crud_interaction.get_by_user_id(db, user_id)
        else:
            interactions = crud_interaction.get_multi(db)

        total_queries = len(interactions)
        rated_queries = sum(1 for i in interactions if i.rating is not None)
        avg_rating = sum(i.rating or 0 for i in interactions if i.rating is not None) / max(rated_queries, 1)

        # 按状态统计
        status_counts = {}
        for interaction in interactions:
            status = interaction.status
            status_counts[status] = status_counts.get(status, 0) + 1

        # 按交互类型统计
        type_counts = {}
        for interaction in interactions:
            interaction_type = interaction.interaction_type
            type_counts[interaction_type] = type_counts.get(interaction_type, 0) + 1

        return {
            "success": True,
            "statistics": {
                "total_queries": total_queries,
                "rated_queries": rated_queries,
                "average_rating": round(avg_rating, 2),
                "status_distribution": status_counts,
                "type_distribution": type_counts
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))