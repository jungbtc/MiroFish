"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)


class Config:
    """Flask配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False
    
    # LLM配置（统一使用OpenAI格式）
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or os.environ.get('LLM_API_KEY')
    LLM_API_KEY = os.environ.get('LLM_API_KEY') or OPENAI_API_KEY
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # Graphiti knowledge graph configuration
    GRAPH_BACKEND = os.environ.get('GRAPH_BACKEND', 'graphiti')
    GRAPHITI_DRIVER = os.environ.get('GRAPHITI_DRIVER', 'falkordb').lower()
    GRAPHITI_RERANKER_MODEL = os.environ.get('GRAPHITI_RERANKER_MODEL', 'gpt-4o-mini')
    FALKORDB_HOST = os.environ.get('FALKORDB_HOST', 'localhost')
    FALKORDB_PORT = int(os.environ.get('FALKORDB_PORT', '6379'))
    FALKORDB_USERNAME = os.environ.get('FALKORDB_USERNAME') or None
    FALKORDB_PASSWORD = os.environ.get('FALKORDB_PASSWORD') or None
    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', '')
    GRAPHITI_TELEMETRY_ENABLED = os.environ.get('GRAPHITI_TELEMETRY_ENABLED', 'false').lower() == 'true'
    SEMAPHORE_LIMIT = int(os.environ.get('SEMAPHORE_LIMIT', '3'))
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    @classmethod
    def validate(cls) -> list[str]:
        """验证必要配置"""
        errors: list[str] = []
        errors.extend(cls.validate_graph_settings())
        return errors

    @staticmethod
    def _is_placeholder_secret(value: str | None) -> bool:
        if not value:
            return True
        normalized = value.strip().lower()
        return (
            normalized.startswith("your_")
            or normalized in {"", "sk-your-real-key", "your-openai-api-key"}
        )

    @classmethod
    def validate_graph_settings(cls) -> list[str]:
        """Validate the Graphiti/OpenAI settings required by graph operations."""
        errors: list[str] = []
        if cls._is_placeholder_secret(cls.OPENAI_API_KEY or cls.LLM_API_KEY):
            errors.append("OPENAI_API_KEY or LLM_API_KEY is required.")
        if cls.GRAPH_BACKEND != 'graphiti':
            errors.append("GRAPH_BACKEND must be graphiti.")
        if cls.GRAPHITI_DRIVER not in {'falkordb', 'neo4j'}:
            errors.append("GRAPHITI_DRIVER must be falkordb or neo4j.")
        if cls.GRAPHITI_DRIVER == 'falkordb':
            if not cls.FALKORDB_HOST:
                errors.append("FALKORDB_HOST is required.")
            if not cls.FALKORDB_PORT:
                errors.append("FALKORDB_PORT is required.")
        if cls.GRAPHITI_DRIVER == 'neo4j':
            if not cls.NEO4J_URI or not cls.NEO4J_USER or not cls.NEO4J_PASSWORD:
                errors.append("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD are required for Neo4j.")
        return errors
