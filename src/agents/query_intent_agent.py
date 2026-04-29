from typing import Dict, List, Optional, Tuple, Any
import re
import json
from datetime import datetime
from src.models.database import SessionLocal
from src.models.document import Document
from src.models.knowledge import KnowledgeChunk
from src.agents.base import BaseAgent
from src.utils.embedding import get_embedding_service
from src.utils.vector_db import get_vector_db
from src.config import get_settings
from src.utils.text_processor import TextProcessor

settings = get_settings()


class IntentType(str):
    """查询意图类型"""
    INFORMATION_SEEKING = "information_seeking"  # 信息查询
    PROCEDURAL_INQUIRY = "procedural_inquiry"    # 流程咨询
    POLICY_CHECK = "policy_check"              # 政策核查
    TRAINING_REQUEST = "training_request"       # 培训需求
    COMPLAINT = "complaint"                    # 投诉反馈
    OTHER = "other"                           # 其他


class QueryIntentAgent(BaseAgent):
    """用户意图理解与检索 Agent"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("QueryIntentAgent", config)
        self.embedding_service = get_embedding_service()
        self.vector_db = get_vector_db(config.get("vector_db", {}))
        self.text_processor = TextProcessor()

        # 意图关键词
        self.intent_keywords = {
            IntentType.INFORMATION_SEEKING: ["什么是", "什么是", "是什么", "介绍一下", "说明", "解释", "定义"],
            IntentType.PROCEDURAL_INQUIRY: ["怎么", "如何", "流程", "步骤", "程序", "申请", "办理", "操作"],
            IntentType.POLICY_CHECK: ["政策", "规定", "制度", "办法", "章程", "条例", "要求", "标准"],
            IntentType.TRAINING_REQUEST: ["培训", "学习", "课程", "教程", "学习资料", "考试"],
            IntentType.COMPLAINT: ["投诉", "问题", "错误", "故障", "不满", "建议", "反馈"],
        }

        # 实体类型
        self.entity_types = {
            "department": ["人事", "人力资源", "财务", "行政", "技术", "研发", "市场", "销售", "运营"],
            "document_type": ["政策", "流程", "手册", "指南", "培训", "报告"],
            "time_period": ["年假", "病假", "产假", "加班", "考勤", "工资", "福利"],
            "action": ["申请", "审批", "查询", "修改", "删除", "提交"]
        }

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理用户查询"""
        try:
            # 验证输入
            if not self.validate_input(input_data):
                return self.format_output({
                    "success": False,
                    "error": "Invalid input data"
                })

            query = input_data.get("query", "").strip()
            user_id = input_data.get("user_id")

            # 识别意图
            intent = await self._recognize_intent(query)

            # 实体识别
            entities = await self._extract_entities(query)

            # 构建检索查询
            search_query = await self._build_search_query(query, intent, entities)

            # 执行向量检索
            search_results = await self._vector_search(search_query)

            # 重排序
            reranked_results = await self._rerank_results(query, search_results)

            # 生成结果摘要
            result_summary = self._generate_result_summary(reranked_results)

            return self.format_output({
                "success": True,
                "query": query,
                "intent": intent,
                "entities": entities,
                "results": reranked_results,
                "result_summary": result_summary,
                "result_count": len(reranked_results),
                "search_query": search_query
            })

        except Exception as e:
            self.log_error(e, f"Query processing failed: {query}")
            return self.format_output({
                "success": False,
                "error": str(e)
            })

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["query"]
        return all(field in input_data for field in required_fields)

    async def _recognize_intent(self, query: str) -> IntentType:
        """识别查询意图"""
        query_lower = query.lower()

        # 计算每个意图的得分
        intent_scores = {}
        for intent_type, keywords in self.intent_keywords.items():
            score = sum(query_lower.count(keyword) for keyword in keywords)
            intent_scores[intent_type] = score

        # 添加基于上下文的意图识别
        if any(word in query_lower for word in ["建议", "反馈", "投诉", "问题"]):
            intent_scores[IntentType.COMPLAINT] += 2

        if any(word in query_lower for word in ["培训", "学习", "课程"]):
            intent_scores[IntentType.TRAINING_REQUEST] += 2

        # 返回得分最高的意图
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        return IntentType.OTHER

    async def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """提取实体"""
        entities = {}

        # 部门实体
        for dept in self.entity_types["department"]:
            if dept in query:
                entities.setdefault("department", []).append(dept)

        # 文档类型实体
        for doc_type in self.entity_types["document_type"]:
            if doc_type in query:
                entities.setdefault("document_type", []).append(doc_type)

        # 时间实体
        for period in self.entity_types["time_period"]:
            if period in query:
                entities.setdefault("time_period", []).append(period)

        # 动作实体
        for action in self.entity_types["action"]:
            if action in query:
                entities.setdefault("action", []).append(action)

        return entities

    async def _build_search_query(self, query: str, intent: IntentType, entities: Dict[str, List[str]]) -> str:
        """构建检索查询"""
        # 基础查询
        search_query = query

        # 根据意图优化查询
        if intent == IntentType.PROCEDURAL_INQUIRY:
            # 流程查询添加步骤关键词
            search_query = f"流程 {query} 步骤"
        elif intent == IntentType.POLICY_CHECK:
            # 政策查询添加制度关键词
            search_query = f"政策 {query} 规定"

        # 根据实体扩展查询
        if "department" in entities:
            depts = " ".join(entities["department"])
            search_query = f"{depts} {search_query}"

        if "document_type" in entities:
            doc_types = " ".join(entities["document_type"])
            search_query = f"{doc_types} {search_query}"

        return search_query

    async def _vector_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """执行向量检索"""
        # 生成查询向量
        query_vector = await self.embedding_service.generate_embedding(query)
        if query_vector is None:
            return []

        # 搜索相似向量
        search_results = self.vector_db.search(query_vector, top_k)

        # 转换为结构化结果
        formatted_results = []
        for doc_id, distance, metadata in search_results:
            result = {
                "id": doc_id,
                "score": 1 - distance,  # 将距离转换为相似度分数
                "metadata": metadata,
                "relevance_score": self._calculate_relevance(query, metadata),
                "freshness_score": self._calculate_freshness(metadata)
            }
            formatted_results.append(result)

        return formatted_results

    def _calculate_relevance(self, query: str, metadata: Dict[str, Any]) -> float:
        """计算相关性分数"""
        # 文本相关性
        content = metadata.get("content", "")
        title = metadata.get("title", "")

        # 标题匹配权重更高
        title_relevance = 1.0 if query.lower() in title.lower() else 0.0
        content_relevance = 1.0 if query.lower() in content.lower() else 0.0

        # 标签匹配
        tags = metadata.get("keywords", "").split(",")
        tag_relevance = sum(1 for tag in tags if query.lower() in tag.lower()) / max(len(tags), 1)

        # 综合分数
        relevance = (title_relevance * 0.4 + content_relevance * 0.3 + tag_relevance * 0.3)
        return min(relevance, 1.0)

    def _calculate_freshness(self, metadata: Dict[str, Any]) -> float:
        """计算新鲜度分数"""
        # 获取文档更新时间
        updated_at = metadata.get("updated_at")
        if not updated_at:
            return 0.5

        # 简单实现：距离当前时间越近，分数越高
        # 实际应用中可以使用更复杂的算法
        current_time = datetime.utcnow()
        time_diff = current_time - updated_at

        # 假设30天内为新鲜
        if time_diff.days <= 30:
            return 1.0
        elif time_diff.days <= 90:
            return 0.7
        elif time_diff.days <= 180:
            return 0.4
        else:
            return 0.2

    async def _rerank_results(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """重排序搜索结果"""
        # 使用多因素排序
        for result in results:
            # 综合分数 = 相似度 * 0.4 + 相关性 * 0.3 + 新鲜度 * 0.3
            similarity_score = result.get("score", 0)
            relevance_score = result.get("relevance_score", 0)
            freshness_score = result.get("freshness_score", 0)

            result["combined_score"] = (
                similarity_score * 0.4 +
                relevance_score * 0.3 +
                freshness_score * 0.3
            )

        # 按综合分数排序
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results

    def _generate_result_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成结果摘要"""
        if not results:
            return {
                "total_results": 0,
                "confidence": 0.0,
                "top_source": None,
                "time_range": None
            }

        # 计算总体置信度
        confidence = sum(r.get("combined_score", 0) for r in results) / len(results)

        # 获取主要来源
        source_counts = {}
        for result in results:
            source = result.get("metadata", {}).get("title", "Unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

        top_source = max(source_counts, key=source_counts.get)

        # 获取时间范围
        dates = []
        for result in results:
            metadata = result.get("metadata", {})
            if "updated_at" in metadata:
                dates.append(metadata["updated_at"])

        time_range = None
        if dates:
            time_range = {
                "earliest": min(dates).isoformat(),
                "latest": max(dates).isoformat()
            }

        return {
            "total_results": len(results),
            "confidence": confidence,
            "top_source": top_source,
            "time_range": time_range
        }

    async def suggest_follow_up_questions(self, query: str, results: List[Dict[str, Any]]) -> List[str]:
        """建议后续问题"""
        suggestions = []

        # 基于结果内容生成建议
        if results:
            top_result = results[0]
            metadata = top_result.get("metadata", {})
            content = metadata.get("content", "")

            # 提取关键词生成建议
            keywords = self.text_processor.extract_keywords(content, max_keywords=3)
            for keyword in keywords:
                suggestions.append(f"关于 {keyword} 的详细信息")

            # 根据意图生成建议
            intent = await self._recognize_intent(query)
            if intent == IntentType.PROCEDURAL_INQUIRY:
                suggestions.append("查看完整的流程步骤")
                suggestions.append("了解相关的申请材料")
            elif intent == IntentType.POLICY_CHECK:
                suggestions.append("查看最新的政策更新")
                suggestions.append("了解政策的执行细则")

        return suggestions[:3]  # 返回最多3个建议