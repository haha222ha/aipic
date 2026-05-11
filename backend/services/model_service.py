from core.config import SUPPORTED_MODELS, DEFAULT_MODEL, OPENAI_SUPPORTED_SIZES
from core.database import global_db_conn


def get_available_models():
    return SUPPORTED_MODELS


def get_default_model():
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT default_model FROM global_config WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return row['default_model']
    return DEFAULT_MODEL


def set_default_model(model_name: str):
    if model_name not in SUPPORTED_MODELS:
        return False, f"不支持的模型: {model_name}"
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE global_config SET default_model = ? WHERE id = 1", (model_name,))
        conn.commit()
    return True, f"默认模型已设置为 {model_name}"


def get_model_info(model_name: str):
    model_registry = {
        "gpt-image-2": {
            "name": "GPT Image 2",
            "version": "2.0",
            "description": "OpenAI最新图像生成模型，支持文字渲染、多轮编辑、高分辨率输出",
            "max_resolution": 3840,
            "supported_sizes": OPENAI_SUPPORTED_SIZES,
            "quality_options": ["low", "medium", "high", "auto"],
            "supports_img2img": True,
            "supports_inpainting": True,
            "max_batch": 1,
            "output_formats": ["png", "jpeg"],
        },
    }
    return model_registry.get(model_name, None)
