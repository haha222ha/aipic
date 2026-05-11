import os
import base64
import time
import uuid
import logging
import httpx

from core.config import (
    OUTPUTS_DIR, TEMP_DIR,
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL,
    OPENAI_DEFAULT_QUALITY, OPENAI_DEFAULT_SIZE,
    OPENAI_SUPPORTED_SIZES, OPENAI_TIMEOUT, QUALITY_TIERS,
    PRESET_RATIOS,
)

os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

logger = logging.getLogger(__name__)


def _resolve_size(ratio_key: str, quality_tier: str) -> str:
    ratio = PRESET_RATIOS.get(ratio_key, PRESET_RATIOS['square'])
    size = ratio['sizes'].get(quality_tier, ratio['sizes']['standard'])
    if size in OPENAI_SUPPORTED_SIZES:
        return size
    parts = size.split('x')
    w, h = int(parts[0]), int(parts[1])
    if w == h:
        return "1024x1024" if w <= 1024 else "2048x2048"
    elif w < h:
        return "1024x1536" if h <= 1536 else "2160x3840"
    else:
        return "1536x1024" if w <= 1536 else "3840x2160"


def _resolve_quality(quality_tier: str) -> str:
    tier = QUALITY_TIERS.get(quality_tier, QUALITY_TIERS['standard'])
    return tier['api_quality']


def _get_headers() -> dict:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 未配置，请在环境变量中设置")
    return {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }


def generate_image(
    prompt: str,
    negative_prompt: str = "",
    model_name: str = "gpt-image-2",
    ratio_key: str = "square",
    steps: int = 20,
    cfg_scale: float = 7.0,
    seed: int = -1,
    style_prompt: str = "",
    input_image_path: str = "",
    task_type: str = "text2img",
    quality_tier: str = "standard",
) -> dict:
    full_prompt = f"{style_prompt}, {prompt}" if style_prompt else prompt

    if seed == -1:
        seed = int(time.time()) % 2147483647

    start_time = time.time()

    try:
        size_str = _resolve_size(ratio_key, quality_tier)
        quality = _resolve_quality(quality_tier)
        tier_info = QUALITY_TIERS.get(quality_tier, QUALITY_TIERS['standard'])
        use_model = tier_info.get('model', OPENAI_MODEL)

        if task_type == "img2img" and input_image_path and os.path.exists(input_image_path):
            result = _generate_img2img(full_prompt, input_image_path, size_str, quality, use_model)
        else:
            result = _generate_text2img(full_prompt, size_str, quality, use_model)

        elapsed = time.time() - start_time
        result["elapsed_seconds"] = round(elapsed, 2)
        result["seed"] = seed
        return result

    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"生成图片失败: {e}", exc_info=True)
        elapsed = time.time() - start_time
        return {
            "success": False,
            "error": f"生成失败: {str(e)}",
            "elapsed_seconds": round(elapsed, 2),
        }


def _generate_text2img(prompt: str, size: str, quality: str, model: str = None) -> dict:
    url = f"{OPENAI_BASE_URL}/images/generations"
    payload = {
        "model": model or OPENAI_MODEL,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": 1,
        "response_format": "b64_json",
        "output_format": "png",
    }

    with httpx.Client(timeout=OPENAI_TIMEOUT) as client:
        response = client.post(url, json=payload, headers=_get_headers())
        response.raise_for_status()
        data = response.json()

    image_data = base64.b64decode(data["data"][0]["b64_json"])
    output_filename = f"{uuid.uuid4().hex}.png"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    with open(output_path, "wb") as f:
        f.write(image_data)

    return {"success": True, "output_path": output_path}


def _generate_img2img(prompt: str, input_image_path: str, size: str, quality: str, model: str = None) -> dict:
    url = f"{OPENAI_BASE_URL}/images/edits"

    with open(input_image_path, "rb") as f:
        image_bytes = f.read()

    filename = os.path.basename(input_image_path)

    with httpx.Client(timeout=OPENAI_TIMEOUT) as client:
        response = client.post(
            url,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            data={
                "model": model or OPENAI_MODEL,
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "n": "1",
                "response_format": "b64_json",
                "output_format": "png",
            },
            files={
                "image": (filename, image_bytes, "image/png"),
            },
        )
        response.raise_for_status()
        data = response.json()

    image_data = base64.b64decode(data["data"][0]["b64_json"])
    output_filename = f"{uuid.uuid4().hex}.png"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    with open(output_path, "wb") as f:
        f.write(image_data)

    return {"success": True, "output_path": output_path}
