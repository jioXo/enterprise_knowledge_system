import re
import jieba
from typing import List, Dict, Set
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class TextProcessor:
    """文本处理工具类"""

    def __init__(self):
        # 停用词列表
        self.stop_words = self._load_stop_words()

        # 正则表达式模式
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'1[3-9]\d{9}')
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

    def clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""

        # 去除多余的空白字符
        text = re.sub(r'\s+', ' ', text)

        # 去除特殊字符（保留中文、英文、数字和基本标点）
        text = re.sub(r'[^\w\s一-鿿　-〿＀-￯]', '', text)

        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '', text)

        return text.strip()

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """文本分块"""
        if not text:
            return []

        # 按句子分割
        sentences = self._split_sentences(text)

        chunks = []
        current_chunk = ""
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            if current_size + sentence_size > chunk_size and current_chunk:
                # 保存当前块
                chunks.append(current_chunk.strip())
                # 创建新块，保留重叠部分
                overlap_text = self._get_overlap_text(current_chunk, overlap)
                current_chunk = overlap_text + sentence
                current_size = len(current_chunk)
            else:
                current_chunk += sentence
                current_size += sentence_size

        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """分句"""
        # 中文句子分割
        text = re.sub(r'([。！？；\n])', r'\1\n', text)
        sentences = [s.strip() for s in text.split('\n') if s.strip()]

        return sentences

    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """获取重叠文本"""
        words = text.split()
        overlap_words = words[-overlap_size:]
        return ' '.join(overlap_words)

    def extract_keywords(self, text: str, max_keywords: int = 20) -> List[str]:
        """提取关键词"""
        if not text:
            return []

        # 分词
        words = jieba.lcut(text)

        # 过滤停用词和短词
        filtered_words = [
            word for word in words
            if (len(word) > 1 and
                word not in self.stop_words and
                not word.isdigit())
        ]

        # 统计词频
        word_counter = Counter(filtered_words)

        # 获取高频词
        keywords = [word for word, count in word_counter.most_common(max_keywords)]

        return keywords

    def extract_topics(self, text: str) -> str:
        """提取主题"""
        keywords = self.extract_keywords(text, max_keywords=5)
        return ",".join(keywords)

    def generate_summary(self, text: str, max_sentences: int = 3) -> str:
        """生成摘要"""
        if not text:
            return ""

        # 简单实现：取前几句话
        sentences = self._split_sentences(text)
        if len(sentences) <= max_sentences:
            return " ".join(sentences)

        summary = " ".join(sentences[:max_sentences])
        return summary

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """提取实体（简化实现）"""
        entities = {
            "email": self.email_pattern.findall(text),
            "phone": self.phone_pattern.findall(text),
            "url": self.url_pattern.findall(text),
        }

        return entities

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 使用关键词重叠度计算相似度
        keywords1 = set(self.extract_keywords(text1))
        keywords2 = set(self.extract_keywords(text2))

        if not keywords1 and not keywords2:
            return 1.0
        if not keywords1 or not keywords2:
            return 0.0

        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)

        return intersection / union

    def detect_language(self, text: str) -> str:
        """检测语言"""
        # 简单实现：根据字符判断
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))

        if chinese_chars > english_chars:
            return "zh-CN"
        else:
            return "en"

    def _load_stop_words(self) -> Set[str]:
        """加载停用词列表"""
        # 基础停用词
        basic_stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "他", "她", "它", "们", "所", "以", "为", "可以", "这个", "那个", "什么", "怎么", "为什么", "因为", "所以", "但是", "然后", "还是", "或者", "如果", "虽然", "但是", "而且", "另外", "除了", "包括", "根据", "按照", "通过", "对于", "关于", "由于", "经过", "通过", "通过", "通过"
        }

        return basic_stop_words