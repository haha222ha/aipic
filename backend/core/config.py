import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "8800"))

GLOBAL_DB_PATH = os.path.join(_BASE_DIR, "global_config.db")
USER_DATA_DIR = os.path.join(_BASE_DIR, "user_data")
TEMP_DIR = os.path.join(_BASE_DIR, "temp")
OUTPUTS_DIR = os.path.join(_BASE_DIR, "outputs")
MODELS_DIR = os.path.join(_BASE_DIR, "models")
STATIC_DIR = os.path.join(_BASE_DIR, "static")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://www.packyapi.com/v1")
OPENAI_MODEL = "gpt-image-2"
OPENAI_DEFAULT_QUALITY = "medium"
OPENAI_DEFAULT_SIZE = "1024x1024"
OPENAI_SUPPORTED_SIZES = [
    "1024x1024",
    "1024x1365",
    "1024x1536",
    "1024x1820",
    "1365x1024",
    "1536x1024",
    "1820x1024",
    "2048x2048",
    "2048x2730",
    "2160x3840",
    "2730x2048",
    "3840x2160",
]
OPENAI_TIMEOUT = 180

DEFAULT_MODEL = "gpt-image-2"
SUPPORTED_MODELS = [
    "gpt-image-2",
]

DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024
MAX_WIDTH = 3840
MAX_HEIGHT = 3840
MAX_BATCH_SIZE = 4

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW = 60

AUTH_CODE_LENGTH = 32
USER_ACTION_LIMIT = 10
USER_ACTION_WINDOW = 60
USER_FREEZE_DURATION = 300

GENERATE_TIMEOUT = 120
MAX_QUEUE_SIZE = 1000
WORKER_INTERVAL = 1.0
WORKER_COUNT = int(os.environ.get("WORKER_COUNT", 3))

TEMP_FILE_MAX_AGE_HOURS = 24
CLEANUP_INTERVAL_SECONDS = 3600

CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://127.0.0.1:8800,http://localhost:8800"
).split(",")

CONTENT_FILTER_ENABLED = True
CONTENT_FILTER_KEYWORDS = []

QUALITY_TIERS = {
    "standard": {
        "label": "标准",
        "model": "gpt-image-2",
        "api_quality": "low",
        "cost_per_image": 0.04,
        "credits_per_image": 1,
        "description": "GPT Image 2 · 标准画质",
        "icon": "✦",
    },
    "hd": {
        "label": "高清",
        "model": "gpt-image-2",
        "api_quality": "medium",
        "cost_per_image": 0.24,
        "credits_per_image": 3,
        "description": "GPT Image 2 · 高清画质",
        "icon": "✧",
    },
    "ultra": {
        "label": "超清",
        "model": "gpt-image-2",
        "api_quality": "high",
        "cost_per_image": 0.94,
        "credits_per_image": 10,
        "description": "GPT Image 2 · 超清画质",
        "icon": "◆",
    },
    "master": {
        "label": "大师",
        "model": "gemini-image",
        "api_quality": "high",
        "cost_per_image": 0.48,
        "credits_per_image": 6,
        "description": "Gemini · 大师级画质",
        "icon": "◈",
        "available": False,
    },
}

PRESET_RATIOS = {
    "square": {
        "label": "1:1 方图",
        "desc": "小红书封面·头像·产品图",
        "sizes": {
            "standard": "1024x1024",
            "hd": "1024x1024",
            "ultra": "2048x2048",
            "master": "2048x2048",
        },
    },
    "portrait_34": {
        "label": "3:4 竖图",
        "desc": "小红书笔记·手机壁纸·海报",
        "sizes": {
            "standard": "1024x1365",
            "hd": "1024x1536",
            "ultra": "2048x2730",
            "master": "2048x2730",
        },
    },
    "portrait_916": {
        "label": "9:16 长图",
        "desc": "短视频封面·故事图·竖屏广告",
        "sizes": {
            "standard": "1024x1820",
            "hd": "1024x1536",
            "ultra": "2160x3840",
            "master": "2160x3840",
        },
    },
    "landscape_43": {
        "label": "4:3 横图",
        "desc": "PPT配图·文章插图·电商详情",
        "sizes": {
            "standard": "1365x1024",
            "hd": "1536x1024",
            "ultra": "2730x2048",
            "master": "2730x2048",
        },
    },
    "landscape_169": {
        "label": "16:9 宽图",
        "desc": "电商主图·横幅·电脑壁纸",
        "sizes": {
            "standard": "1820x1024",
            "hd": "1536x1024",
            "ultra": "3840x2160",
            "master": "3840x2160",
        },
    },
}

CREDIT_PACKAGES = {
    "体验卡": {
        "credits": 30,
        "price": 9.9,
        "price_per_credit": 0.33,
        "valid_days": 30,
        "popular": False,
        "description": "30积分 · 约30张标准图",
        "badge": "",
    },
    "基础版": {
        "credits": 120,
        "price": 29.9,
        "price_per_credit": 0.249,
        "valid_days": 30,
        "popular": False,
        "description": "120积分 · 约120张标准图",
        "badge": "",
    },
    "专业版": {
        "credits": 350,
        "price": 69.9,
        "price_per_credit": 0.200,
        "valid_days": 30,
        "popular": True,
        "description": "350积分 · 约350张标准图",
        "badge": "最受欢迎",
    },
    "旗舰版": {
        "credits": 800,
        "price": 129.9,
        "price_per_credit": 0.162,
        "valid_days": 30,
        "popular": False,
        "description": "800积分 · 约800张标准图",
        "badge": "最划算",
    },
}

PACKAGES = {
    "免费版": {
        "limit": 3,
        "daily_generate_limit": 3,
        "price": 0,
        "days": 30,
        "free_credits": 3,
        "max_quality": "standard",
        "batch_support": False,
        "style_library": False,
        "api_access": False,
        "description": "免费体验 · 每日3积分",
    },
    "体验卡": {
        "limit": 9999,
        "daily_generate_limit": 9999,
        "price": 9.9,
        "days": 30,
        "free_credits": 0,
        "credits": 30,
        "max_quality": "hd",
        "batch_support": False,
        "style_library": True,
        "api_access": False,
        "description": "30积分 · 适合初次体验",
    },
    "基础版": {
        "limit": 9999,
        "daily_generate_limit": 9999,
        "price": 29.9,
        "days": 30,
        "free_credits": 0,
        "credits": 120,
        "max_quality": "hd",
        "batch_support": False,
        "style_library": True,
        "api_access": False,
        "description": "120积分 · 日常创作够用",
    },
    "专业版": {
        "limit": 9999,
        "daily_generate_limit": 9999,
        "price": 69.9,
        "days": 30,
        "free_credits": 0,
        "credits": 350,
        "max_quality": "ultra",
        "batch_support": True,
        "style_library": True,
        "api_access": True,
        "description": "350积分 · 高频创作首选",
    },
    "旗舰版": {
        "limit": 9999,
        "daily_generate_limit": 9999,
        "price": 129.9,
        "days": 30,
        "free_credits": 0,
        "credits": 800,
        "max_quality": "ultra",
        "batch_support": True,
        "style_library": True,
        "api_access": True,
        "description": "800积分 · 专业创作者",
    },
}
