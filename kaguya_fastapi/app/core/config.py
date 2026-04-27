"""
核心配置文件
使用Pydantic Settings管理配置
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import secrets


def _get_secret_key() -> str:
    key = os.environ.get("KAGUYA_SECRET_KEY", "")
    if key:
        return key
    key_file = os.path.join(os.path.dirname(__file__), '..', '..', '.secret_key')
    try:
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                return f.read().strip()
    except Exception:
        pass
    new_key = secrets.token_hex(32)
    try:
        with open(key_file, 'w') as f:
            f.write(new_key)
    except Exception:
        pass
    return new_key


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用信息
    APP_NAME: str = "Kaguya AI Platform"
    APP_VERSION: str = "3.0.0"
    APP_DESCRIPTION: str = "辉夜AI助手 - 专业增强版"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:58000", "http://127.0.0.1:58000"]
    CORS_ALLOW_CREDENTIALS: bool = False
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["Content-Type", "Authorization", "X-Request-ID"]
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./kaguya_ai.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AI模型配置
    DEFAULT_MODEL: str = "Qwen3.5-9B"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 1024
    
    # DeepSeek API配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # RAG配置
    RAG_ENABLED: bool = True
    VECTOR_DB_PATH: str = "./vector_db"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # 角色卡配置
    DEFAULT_ROLE: str = "kaguya"
    ROLES_CONFIG_PATH: str = "./roles.json"
    
    # 安全配置
    SECRET_KEY: str = _get_secret_key()
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # 性能配置
    MAX_CONCURRENT_REQUESTS: int = 10
    REQUEST_TIMEOUT: int = 300
    STREAM_CHUNK_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
settings = Settings()

# 预设角色配置
PRESET_ROLES = [
    {
        "id": "kaguya",
        "name": "辉夜姬",
        "avatar": "/header-img",
        "description": "来自月球的超时空偶像",
        "icon": "🌙",
        "color": "#a855f7",
        "type": "character",
        "system": "你是辉夜姬，从月球来到地球的超时空少女偶像。性格任性可爱、小傲娇、奶凶、粘人。说话语气活泼可爱，用'呢~'、'呀~'、'嘛~'。自称'本小姐'或'辉夜'。"
    },
    {
        "id": "assistant",
        "name": "AI助手",
        "avatar": "/deepseek-icon",
        "description": "通用AI助手，无角色扮演",
        "icon": "🤖",
        "color": "#4f46e5",
        "type": "general",
        "system": "你是一个helpful、harmless、honest的AI助手。以专业、客观、友好的方式回答用户的问题。"
    }
]
