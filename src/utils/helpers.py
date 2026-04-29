import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import json
from pathlib import Path

def generate_uuid() -> str:
    """生成UUID"""
    return str(uuid.uuid4())

def extract_email(text: str) -> List[str]:
    """从文本中提取邮箱地址"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)

def extract_phone(text: str) -> List[str]:
    """从文本中提取电话号码"""
    phone_pattern = r'(?:\+86[-\s]?)?(1[3-9]\d{9})'
    return re.findall(phone_pattern, text)

def extract_url(text: str) -> List[str]:
    """从文本中提取URL"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)

def clean_text(text: str) -> str:
    """清理文本"""
    if not text:
        return ""

    # 去除多余的空白
    text = re.sub(r'\s+', ' ', text)
    # 去除特殊字符
    text = re.sub(r'[^\w\s一-鿿]', '', text)
    return text.strip()

def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def extract_chinese(text: str) -> str:
    """提取中文字符"""
    chinese_pattern = r'[一-鿿]+'
    return ' '.join(re.findall(chinese_pattern, text))

def count_tokens(text: str) -> int:
    """粗略计算token数量"""
    # 简单实现：假设1个token约等于4个字符
    return len(text) // 4

def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """验证电话号码格式"""
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.2f}{size_names[i]}"

def is_file_allowed(filename: str, allowed_extensions: List[str]) -> bool:
    """检查文件类型是否允许"""
    file_extension = Path(filename).suffix.lower()
    return file_extension in allowed_extensions

def merge_dictionaries(dict1: Dict, dict2: Dict) -> Dict:
    """合并两个字典"""
    result = dict1.copy()
    result.update(dict2)
    return result

def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """扁平化字典"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def unflatten_dict(d: Dict, sep: str = '.') -> Dict:
    """反扁平化字典"""
    result = {}
    for k, v in d.items():
        keys = k.split(sep)
        current = result
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = v
    return result

def safe_json_loads(json_str: str) -> Optional[Dict]:
    """安全的JSON解析"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None

def safe_json_dumps(obj: Any, indent: Optional[int] = None) -> str:
    """安全的JSON序列化"""
    try:
        return json.dumps(obj, ensure_ascii=False, indent=indent)
    except (TypeError, ValueError):
        return "{}"

def get_file_hash(filepath: Path) -> str:
    """计算文件哈希值"""
    import hashlib
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def ensure_directory_exists(path: Union[str, Path]) -> Path:
    """确保目录存在"""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    return dt.strftime(format_str)

def parse_datetime(datetime_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """解析日期时间字符串"""
    try:
        return datetime.strptime(datetime_str, format_str)
    except ValueError:
        return None

def time_ago(dt: datetime) -> str:
    """计算时间差（多久前）"""
    now = datetime.utcnow()
    diff = now - dt

    if diff.days > 0:
        return f"{diff.days}天前"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600}小时前"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60}分钟前"
    else:
        return "刚刚"

def create_response(
    success: bool = True,
    data: Any = None,
    message: str = "",
    error: str = "",
    status_code: int = 200
) -> Dict[str, Any]:
    """创建标准响应格式"""
    response = {
        "success": success,
        "message": message,
        "error": error,
        "timestamp": datetime.utcnow().isoformat()
    }

    if data is not None:
        response["data"] = data

    return response

def paginate_data(
    data: List[Any],
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """分页数据"""
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page

    paginated_data = data[start:end]

    return {
        "items": paginated_data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }