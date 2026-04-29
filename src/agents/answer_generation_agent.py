from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import re
from src.models.database import SessionLocal
from src.models.document import Document, DocumentStatus
from src.models.interaction import Interaction, InteractionStatus
from src.agents.base import BaseAgent
from src.config import get_settings

settings = get_settings()


class AnswerType(str):
    """答案类型"""
    DIRECT_ANSWER = "direct_answer"      # 直接回答
    PROCEDURAL_GUIDE = "procedural_guide"  # 流程指导
    POLICY_REFERENCE = "policy_reference"  # 政策引用
    TRAINING_MATERIAL = "training_material" # 培训材料
    MULTIPLE_SOURCE = "multiple_source"    # 多源综合
    UNCLEAR = "unclear"                    # 不明确
    ESCALATED = "escalated"                # 需要人工处理


class AnswerGenerationAgent(BaseAgent):
    """答案生成与校验 Agent"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("AnswerGenerationAgent", config)

        # 答案模板
        self.answer_templates = {
            AnswerType.DIRECT_ANSWER: {
                "format": "direct",
                "structure": ["direct_answer", "source", "confidence"]
            },
            AnswerType.PROCEDURAL_GUIDE: {
                "format": "steps",
                "structure": ["title", "overview", "steps", "notes", "source"]
            },
            AnswerType.POLICY_REFERENCE: {
                "format": "reference",
                "structure": ["policy_title", "content", "applicability", "validity", "source"]
            },
            AnswerType.MULTIPLE_SOURCE: {
                "format": "comparison",
                "structure": ["summary", "sources", "comparison", "recommendation"]
            }
        }

        # 过时关键词
        self.outdated_keywords = [
            "已废止", "已失效", "已更新", "修订前", "旧版", "作废",
            "previous version", "deprecated", "outdated", "obsolete"
        ]

        # 矛盾检测模式
        self.contradiction_patterns = [
            (r"(\d+)天内", r"(\d+)天内"),  # 时间冲突
            (r"(\d+)天", r"(\d+)天以上"),  # 时间范围冲突
            (r"必须", r"可以"),  # 强制性冲突
            (r"禁止", r"允许"),  # 禁止性冲突
        ]

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理答案生成任务"""
        try:
            # 验证输入
            if not self.validate_input(input_data):
                return self.format_output({
                    "success": False,
                    "error": "Invalid input data"
                })

            query = input_data.get("query", "").strip()
            search_results = input_data.get("results", [])
            user_id = input_data.get("user_id")

            # 生成答案
            answer_result = await self._generate_answer(query, search_results)

            # 答案校验
            validation_result = await self._validate_answer(query, answer_result)

            # 融合结果
            final_result = self._merge_results(answer_result, validation_result)

            # 创建交互记录
            await self._create_interaction(query, final_result, user_id)

            return self.format_output(final_result)

        except Exception as e:
            self.log_error(e, f"Answer generation failed: {query}")
            return self.format_output({
                "success": False,
                "error": str(e)
            })

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["query", "results"]
        return all(field in input_data for field in required_fields)

    async def _generate_answer(self, query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成答案"""
        if not search_results:
            return {
                "answer_type": AnswerType.UNCLEAR,
                "answer": "抱歉，我没有找到相关信息。请尝试其他关键词或咨询相关部门。",
                "confidence": 0.0,
                "sources": [],
                "warnings": ["未找到相关信息"]
            }

        # 检测过时信息
        outdated_info = self._detect_outdated_info(search_results)

        # 检测信息矛盾
        contradictions = self._detect_contradictions(search_results)

        # 根据结果类型生成答案
        answer_type = self._determine_answer_type(query, search_results)

        # 使用对应的模板生成答案
        if answer_type == AnswerType.MULTIPLE_SOURCE:
            answer = await self._generate_multiple_source_answer(search_results)
        else:
            answer = await self._generate_single_source_answer(search_results[0], answer_type)

        # 构建结果
        result = {
            "answer_type": answer_type,
            "answer": answer,
            "confidence": self._calculate_answer_confidence(search_results),
            "sources": self._extract_sources(search_results),
            "warnings": []
        }

        # 添加警告信息
        if outdated_info:
            result["warnings"].append("发现部分信息可能已过时")
        if contradictions:
            result["warnings"].append("发现信息存在矛盾，请以最新规定为准")

        return result

    def _detect_outdated_info(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """检测过时信息"""
        outdated = []

        for result in search_results:
            metadata = result.get("metadata", {})

            # 检查文档状态
            if metadata.get("status") == DocumentStatus.OUTDATED:
                outdated.append(metadata.get("title", ""))

            # 检查内容中的过时关键词
            content = metadata.get("content", "")
            if any(keyword in content for keyword in self.outdated_keywords):
                outdated.append(metadata.get("title", ""))

            # 检查更新时间
            updated_at = metadata.get("updated_at")
            if updated_at:
                # 假设6个月以上为过时
                if datetime.utcnow() - updated_at > timedelta(days=180):
                    outdated.append(metadata.get("title", ""))

        return list(set(outdated))  # 去重

    def _detect_contradictions(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """检测信息矛盾"""
        contradictions = []

        # 简单实现：检查相同主题的内容差异
        for i, result1 in enumerate(search_results):
            for j, result2 in enumerate(search_results[i+1:], i+1):
                content1 = result1.get("metadata", {}).get("content", "")
                content2 = result2.get("metadata", {}).get("content", "")

                # 检查矛盾模式
                for pattern in self.contradiction_patterns:
                    if re.search(pattern[0], content1) and re.search(pattern[1], content2):
                        contradictions.append(f"在 '{result1.get('metadata', {}).get('title', '')}' 和 "
                                           f"'{result2.get('metadata', {}).get('title', '')}' 中发现矛盾")

        return contradictions

    def _determine_answer_type(self, query: str, search_results: List[Dict[str, Any]]) -> AnswerType:
        """确定答案类型"""
        # 检查是否需要人工处理
        if len(search_results) == 0:
            return AnswerType.UNCLEAR

        # 检查是否矛盾过多
        contradictions = self._detect_contradictions(search_results)
        if len(contradictions) > 2:
            return AnswerType.ESCALATED

        # 检查是否流程查询
        if any(keyword in query.lower() for keyword in ["怎么", "如何", "流程", "步骤"]):
            return AnswerType.PROCEDURAL_GUIDE

        # 检查是否政策查询
        if any(keyword in query.lower() for keyword in ["政策", "规定", "制度"]):
            return AnswerType.POLICY_REFERENCE

        # 检查是否培训材料
        if any(keyword in query.lower() for keyword in ["培训", "学习", "教程"]):
            return AnswerType.TRAINING_MATERIAL

        # 检查是否多个来源
        if len(search_results) > 3:
            return AnswerType.MULTIPLE_SOURCE

        # 默认直接回答
        return AnswerType.DIRECT_ANSWER

    async def _generate_single_source_answer(self, result: Dict[str, Any], answer_type: AnswerType) -> str:
        """生成单源答案"""
        metadata = result.get("metadata", {})
        content = metadata.get("content", "")
        title = metadata.get("title", "")

        if answer_type == AnswerType.DIRECT_ANSWER:
            # 直接提取相关内容
            sentences = self._extract_relevant_sentences(content, result.get("score", 0))
            return " ".join(sentences[:3])  # 返回最相关的3句话

        elif answer_type == AnswerType.PROCEDURAL_GUIDE:
            # 提取步骤信息
            steps = self._extract_steps(content)
            return self._format_steps(title, steps)

        elif answer_type == AnswerType.POLICY_REFERENCE:
            # 提取政策要点
            points = self._extract_policy_points(content)
            return self._format_policy_reference(title, points)

        elif answer_type == AnswerType.TRAINING_MATERIAL:
            # 提取培训要点
            key_points = self._extract_key_points(content)
            return self._format_training_material(title, key_points)

        else:
            return content[:500] + "..."

    async def _generate_multiple_source_answer(self, search_results: List[Dict[str, Any]]) -> str:
        """生成多源综合答案"""
        # 提取各来源的关键信息
        source_summaries = []
        for result in search_results[:3]:  # 取前3个结果
            metadata = result.get("metadata", {})
            content = metadata.get("content", "")
            title = metadata.get("title", "")

            summary = self._generate_summary(content)
            source_summaries.append({
                "title": title,
                "summary": summary,
                "confidence": result.get("score", 0)
            })

        # 生成综合回答
        intro = "根据多个来源的信息，为您总结如下：\n\n"

        # 按置信度排序
        source_summaries.sort(key=lambda x: x["confidence"], reverse=True)

        # 构建回答
        answer_parts = [intro]

        for i, source in enumerate(source_summaries):
            answer_parts.append(f"{i+1}. 【{source['title']}】\n")
            answer_parts.append(f"   {source['summary']}\n")

        # 添加建议
        answer_parts.append("\n建议：以上信息可能存在差异，请以最新发布的官方文件为准。")

        return "".join(answer_parts)

    def _extract_relevant_sentences(self, content: str, score: float) -> List[str]:
        """提取相关句子"""
        # 简单实现：按段落分割，返回前几个段落
        paragraphs = content.split('\n\n')
        return [p.strip() for p in paragraphs[:3] if p.strip()]

    def _extract_steps(self, content: str) -> List[str]:
        """提取步骤信息"""
        steps = []

        # 查找数字编号的步骤
        step_pattern = r'(\d+)\.\s*([^\n]+)'
        matches = re.findall(step_pattern, content)

        for match in matches:
            steps.append({
                "step": int(match[0]),
                "description": match[1].strip()
            })

        return steps

    def _format_steps(self, title: str, steps: List[Dict[str, Any]]) -> str:
        """格式化步骤答案"""
        result = f"## {title}\n\n"
        result += "### 操作步骤\n\n"

        for step in steps:
            result += f"{step['step']}. {step['description']}\n"

        result += "\n### 注意事项\n\n请确保按照以上步骤操作，如有疑问请咨询相关部门。"

        return result

    def _extract_policy_points(self, content: str) -> List[str]:
        """提取政策要点"""
        points = []

        # 查找要点标记
        point_patterns = [
            r'([一二三四五六七八九十]、\s*[^\n]+)',
            r'(\d+\.\s*[^\n]+)',
            r'([•·▪]\s*[^\n]+)'
        ]

        for pattern in point_patterns:
            matches = re.findall(pattern, content)
            points.extend(matches)

        return points[:5]  # 返回前5个要点

    def _format_policy_reference(self, title: str, points: List[str]) -> str:
        """格式化政策引用答案"""
        result = f"## {title}\n\n"
        result += "### 政策要点\n\n"

        for i, point in enumerate(points, 1):
            result += f"{i}. {point}\n"

        result += f"\n### 生效时间\n\n请以最新发布的文件为准。"

        return result

    def _extract_key_points(self, content: str) -> List[str]:
        """提取培训要点"""
        return self._extract_policy_points(content)  # 复用政策要点提取

    def _format_training_material(self, title: str, key_points: List[str]) -> str:
        """格式化培训材料答案"""
        result = f"## {title}\n\n"
        result += "### 培训要点\n\n"

        for i, point in enumerate(key_points, 1):
            result += f"{i}. {point}\n"

        result += f"\n### 建议\n\n建议结合实际操作进行学习，如有疑问请向培训师咨询。"

        return result

    def _generate_summary(self, content: str) -> str:
        """生成摘要"""
        # 简单实现：取前100个字符
        return content[:100] + "..." if len(content) > 100 else content

    def _calculate_answer_confidence(self, search_results: List[Dict[str, Any]]) -> float:
        """计算答案置信度"""
        if not search_results:
            return 0.0

        # 基于搜索结果的平均分数
        avg_score = sum(result.get("score", 0) for result in search_results) / len(search_results)

        # 基于结果的时效性
        fresh_count = sum(1 for result in search_results
                         if self._is_fresh(result.get("metadata", {})))
        freshness_ratio = fresh_count / len(search_results)

        # 综合置信度
        confidence = (avg_score * 0.7 + freshness_ratio * 0.3)
        return min(confidence, 1.0)

    def _is_fresh(self, metadata: Dict[str, Any]) -> bool:
        """检查信息是否新鲜"""
        updated_at = metadata.get("updated_at")
        if not updated_at:
            return True

        # 假设3个月内为新鲜
        return datetime.utcnow() - updated_at <= timedelta(days=90)

    def _extract_sources(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取来源信息"""
        sources = []

        for result in search_results:
            metadata = result.get("metadata", {})
            source = {
                "title": metadata.get("title", "Unknown"),
                "document_id": metadata.get("document_id", ""),
                "url": metadata.get("source_url", ""),
                "updated_at": metadata.get("updated_at", ""),
                "confidence": result.get("score", 0)
            }
            sources.append(source)

        return sources

    async def _validate_answer(self, query: str, answer_result: Dict[str, Any]) -> Dict[str, Any]:
        """校验答案"""
        validation = {
            "is_valid": True,
            "warnings": [],
            "suggestions": []
        }

        # 检查答案是否为空
        if not answer_result.get("answer"):
            validation["is_valid"] = False
            validation["warnings"].append("生成的答案为空")

        # 检查置信度
        confidence = answer_result.get("confidence", 0)
        if confidence < 0.5:
            validation["warnings"].append("答案置信度较低，建议核实")

        # 检查是否需要人工处理
        if answer_result.get("answer_type") == AnswerType.ESCALATED:
            validation["is_valid"] = False
            validation["suggestions"].append("该问题需要人工处理")

        return validation

    def _merge_results(self, answer_result: Dict[str, Any], validation: Dict[str, Any]) -> Dict[str, Any]:
        """融合答案和校验结果"""
        result = answer_result.copy()

        # 添加校验信息
        result["validation"] = validation

        # 如果校验失败，调整答案
        if not validation["is_valid"]:
            result["answer"] = "抱歉，无法为您提供准确答案。建议您咨询相关部门或稍后再试。"
            result["answer_type"] = AnswerType.ESCALATED

        return result

    async def _create_interaction(self, query: str, result: Dict[str, Any], user_id: int):
        """创建交互记录"""
        if not user_id:
            return

        db = SessionLocal()
        try:
            interaction = Interaction(
                user_id=user_id,
                interaction_type="question",
                query=query,
                response=result.get("answer", ""),
                status="pending"
            )

            db.add(interaction)
            db.commit()

        except Exception as e:
            self.log_error(e, "Failed to create interaction record")
        finally:
            db.close()