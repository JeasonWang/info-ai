"""
信息聚合系统 - 全局配置文件
定义系统运行所需的所有配置项，包括数据库、爬虫、定时任务等
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ENV = os.getenv("APP_ENV", "local")
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)
APP_TIMEZONE = os.getenv("APP_TIMEZONE", os.getenv("TZ", "Asia/Shanghai"))

# ==================== 数据库配置 ====================
DEFAULT_DB_TYPE = "sqlite" if APP_ENV == "test" else "mysql"
DB_TYPE = os.getenv("DB_TYPE", DEFAULT_DB_TYPE)
AUTO_INIT_DB_SCHEMA = os.getenv("AUTO_INIT_DB_SCHEMA", "0" if APP_ENV in {"local", "test"} else "0") == "1"
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_NAME = os.getenv("DB_NAME", "info-max")

if DB_TYPE == "sqlite":
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'info_aggregation.db')}"
else:
    SQLALCHEMY_DATABASE_URL = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        f"?charset=utf8mb4"
    )

# ==================== 爬虫通用配置 ====================
CRAWLER_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

CRAWLER_REQUEST_TIMEOUT = 15
CRAWLER_RETRY_TIMES = 3
CRAWLER_RETRY_INTERVAL = 300
CRAWLER_MAX_CONTENT_LENGTH = int(os.getenv("CRAWLER_MAX_CONTENT_LENGTH", "12000"))
DETAIL_JOB_RUNNING_TIMEOUT_MINUTES = int(os.getenv("DETAIL_JOB_RUNNING_TIMEOUT_MINUTES", "30"))

# ==================== 事件分析配置 ====================
EVENT_ANALYSIS_MODE = os.getenv("EVENT_ANALYSIS_MODE", "hybrid")
EVENT_ANALYSIS_ENABLE_LLM = os.getenv("EVENT_ANALYSIS_ENABLE_LLM", "0") == "1"
EVENT_ANALYSIS_PROVIDER = os.getenv("EVENT_ANALYSIS_PROVIDER", "openai_compatible")
EVENT_ANALYSIS_BASE_URL = os.getenv("EVENT_ANALYSIS_BASE_URL", "http://127.0.0.1:8001/v1")
EVENT_ANALYSIS_API_KEY = os.getenv("EVENT_ANALYSIS_API_KEY", "")
EVENT_ANALYSIS_MODEL = os.getenv("EVENT_ANALYSIS_MODEL", "qwen2.5-14b-instruct")
EVENT_ANALYSIS_TIMEOUT = int(os.getenv("EVENT_ANALYSIS_TIMEOUT", "60"))
EVENT_ANALYSIS_MAX_INPUT_CHARS = int(os.getenv("EVENT_ANALYSIS_MAX_INPUT_CHARS", "12000"))
EVENT_ANALYSIS_TEMPERATURE = float(os.getenv("EVENT_ANALYSIS_TEMPERATURE", "0.2"))
EVENT_ANALYSIS_FALLBACK_TO_RULE = os.getenv("EVENT_ANALYSIS_FALLBACK_TO_RULE", "1") == "1"
EVENT_ANALYSIS_LLM_RETRY_TIMES = int(os.getenv("EVENT_ANALYSIS_LLM_RETRY_TIMES", "2"))
EVENT_ANALYSIS_LLM_FAILURE_THRESHOLD = int(os.getenv("EVENT_ANALYSIS_LLM_FAILURE_THRESHOLD", "3"))
EVENT_ANALYSIS_LLM_COOLDOWN_MINUTES = int(os.getenv("EVENT_ANALYSIS_LLM_COOLDOWN_MINUTES", "30"))

# ==================== 定时任务配置 ====================
#热点事件爬取
SCHEDULER_HOT_INTERVAL = 10
#经济数据爬取
SCHEDULER_ECONOMY_INTERVAL = 30
#国际大事爬取
SCHEDULER_INTERNATIONAL_INTERVAL = 30
#科技动向爬取
SCHEDULER_TECH_INTERVAL = 30
#AI大模型动向爬取
SCHEDULER_AI_INTERVAL = 30

# ==================== 日志配置 ====================
LOG_DIR = os.getenv("LOG_DIR", os.path.join(DATA_DIR, "logs"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ==================== API配置 ====================
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
ENABLE_PUBLIC_API = os.getenv("ENABLE_PUBLIC_API", "1" if APP_ENV == "test" else "0") == "1"
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:8085,http://127.0.0.1:8085",
    ).split(",")
    if origin.strip()
]

# ==================== Redis 命令总线配置 ====================
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
ENABLE_REDIS_COMMAND_CONSUMER = os.getenv("ENABLE_REDIS_COMMAND_CONSUMER", "1") == "1"
AGGREGATION_COMMAND_STREAM = os.getenv("AGGREGATION_COMMAND_STREAM", "info_ai:aggregation:commands")
AGGREGATION_COMMAND_CONSUMER_GROUP = os.getenv("AGGREGATION_COMMAND_CONSUMER_GROUP", "info_aggregation")
AGGREGATION_COMMAND_CONSUMER_NAME = os.getenv("AGGREGATION_COMMAND_CONSUMER_NAME", "")
AGGREGATION_COMMAND_PENDING_IDLE_MS = int(os.getenv("AGGREGATION_COMMAND_PENDING_IDLE_MS", "60000"))
AGGREGATION_RESULT_PREFIX = os.getenv("AGGREGATION_RESULT_PREFIX", "info_ai:aggregation:results:")
AGGREGATION_RESULT_TTL_SECONDS = int(os.getenv("AGGREGATION_RESULT_TTL_SECONDS", "86400"))

# ==================== 信息分类枚举 ====================
CATEGORY_HOT = "热点事件"
CATEGORY_ECONOMY = "经济数据"
CATEGORY_INTERNATIONAL = "国际大事"
CATEGORY_TECH = "科技动向"
CATEGORY_AI = "AI大模型动向"
CATEGORY_SPORTS = "体育"

CATEGORIES = [
    CATEGORY_HOT,
    CATEGORY_ECONOMY,
    CATEGORY_INTERNATIONAL,
    CATEGORY_TECH,
    CATEGORY_AI,
    CATEGORY_SPORTS,
]

# ==================== 渠道配置 ====================
CHANNELS = [
    {"name": "微博", "code": "weibo", "category": CATEGORY_HOT},
    {"name": "今日头条", "code": "toutiao", "category": CATEGORY_HOT},
    {"name": "小红书", "code": "xiaohongshu", "category": CATEGORY_HOT},
    {"name": "东方财富网", "code": "eastmoney", "category": CATEGORY_ECONOMY},
    {"name": "路透社", "code": "reuters", "category": CATEGORY_INTERNATIONAL},
    {"name": "CSDN", "code": "csdn", "category": CATEGORY_TECH},
    {"name": "掘金", "code": "juejin", "category": CATEGORY_TECH},
    {"name": "博客园", "code": "cnblogs", "category": CATEGORY_TECH},
    {"name": "36氪", "code": "36kr", "category": CATEGORY_AI},
    {"name": "知乎", "code": "zhihu", "category": CATEGORY_AI},
    {"name": "央视体育网", "code": "cctv_sports", "category": CATEGORY_SPORTS},
    {"name": "新浪体育", "code": "sina_sports", "category": CATEGORY_SPORTS},
]
