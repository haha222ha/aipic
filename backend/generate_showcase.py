import os
import sys
import time
import base64
import uuid
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, OUTPUTS_DIR

os.makedirs(OUTPUTS_DIR, exist_ok=True)

SHOWCASE_DIR = os.path.join(OUTPUTS_DIR, "showcase")
os.makedirs(SHOWCASE_DIR, exist_ok=True)

PROMPTS = [
    {
        "prompt": "A beautiful Chinese girl in a white dress standing under cherry blossom trees, soft backlight, cinematic color grading, portrait photography style, 8K ultra detailed",
        "ratio": "portrait_34",
        "category": "人像摄影",
        "title": "樱花少女",
    },
    {
        "prompt": "Minimalist product photography of a luxury perfume bottle on white marble, golden light, clean background, commercial advertising style, high-end fashion",
        "ratio": "square",
        "category": "电商主图",
        "title": "香氛之境",
    },
    {
        "prompt": "A cute orange tabby cat lying on a windowsill in warm sunlight, cozy home interior, soft bokeh, pet photography, warm tones",
        "ratio": "square",
        "category": "萌宠日常",
        "title": "午后暖阳",
    },
    {
        "prompt": "Chinese style illustration of a dragon and phoenix, traditional gongbi painting, rich colors, gold accents, elegant composition, cultural art",
        "ratio": "portrait_34",
        "category": "国潮插画",
        "title": "龙凤呈祥",
    },
    {
        "prompt": "Delicious matcha latte art in a ceramic cup on a wooden table, Japanese aesthetic, food photography, soft natural light, wabi-sabi style",
        "ratio": "square",
        "category": "美食探店",
        "title": "抹茶时光",
    },
    {
        "prompt": "Cyberpunk cityscape at night, neon lights reflecting on wet streets, futuristic architecture, purple and blue color palette, sci-fi concept art",
        "ratio": "landscape_169",
        "category": "概念艺术",
        "title": "霓虹未来",
    },
    {
        "prompt": "Watercolor painting of Jiangnan water town, small bridge over flowing stream, misty morning, traditional Chinese architecture, peaceful atmosphere",
        "ratio": "landscape_43",
        "category": "水彩风景",
        "title": "江南水乡",
    },
    {
        "prompt": "Flat lay photography of a creative workspace with laptop, coffee, plants and notebook, aesthetic desk setup, warm morning light, productivity vibes",
        "ratio": "square",
        "category": "生活方式",
        "title": "灵感工位",
    },
    {
        "prompt": "Fashion editorial photo of a woman in traditional Chinese hanfu walking in a bamboo forest, ethereal atmosphere, soft diffused light, editorial style",
        "ratio": "portrait_916",
        "category": "穿搭分享",
        "title": "竹林汉服",
    },
    {
        "prompt": "Aesthetic room interior with fairy lights, cozy bed with white linen, dried flowers, minimal Scandinavian style, dreamy atmosphere, warm tones",
        "ratio": "landscape_43",
        "category": "家居美学",
        "title": "梦幻小屋",
    },
    {
        "prompt": "Macro photography of a butterfly on a flower, extreme detail, shallow depth of field, natural bokeh, vivid colors, nature photography",
        "ratio": "square",
        "category": "微距摄影",
        "title": "蝶恋花",
    },
    {
        "prompt": "Travel photography of Santorini blue domes at sunset, golden hour light, Mediterranean vibes, vacation mood, postcard perfect composition",
        "ratio": "landscape_169",
        "category": "旅行日记",
        "title": "圣托里尼",
    },
    {
        "prompt": "Korean style skincare product flat lay on pink marble, beauty products arrangement, pastel colors, clean aesthetic, cosmetic advertising",
        "ratio": "square",
        "category": "美妆种草",
        "title": "肌肤之钥",
    },
    {
        "prompt": "Steampunk mechanical butterfly with gears and brass elements, dark background, detailed illustration, fantasy art, Victorian aesthetic",
        "ratio": "square",
        "category": "概念艺术",
        "title": "蒸汽蝴蝶",
    },
    {
        "prompt": "Healthy smoothie bowl with fresh berries and granola, overhead shot, clean white background, food styling, wellness lifestyle photography",
        "ratio": "square",
        "category": "健康饮食",
        "title": "活力早餐",
    },
    {
        "prompt": "Modern minimalist white architecture with geometric shapes, clear blue sky, architectural photography, clean lines, contemporary design",
        "ratio": "portrait_34",
        "category": "建筑美学",
        "title": "极简之境",
    },
    {
        "prompt": "Hand-drawn illustration of a dreamy night sky with moon and stars, girl sitting on a cloud, whimsical art style, pastel colors, children book illustration",
        "ratio": "portrait_34",
        "category": "梦幻插画",
        "title": "星夜童话",
    },
    {
        "prompt": "Vintage film photography of a Parisian cafe terrace, autumn leaves, warm nostalgic tones, street photography, romantic atmosphere",
        "ratio": "landscape_43",
        "category": "街拍纪实",
        "title": "巴黎秋日",
    },
    {
        "prompt": "Aesthetic bookshelf with colorful books, green plants and warm lamp light, cozy reading nook, hygge style, knowledge and wisdom",
        "ratio": "portrait_34",
        "category": "阅读时光",
        "title": "书海拾光",
    },
    {
        "prompt": "Abstract fluid art with gold and deep blue, marble texture, luxury background, modern art, elegant and sophisticated design",
        "ratio": "square",
        "category": "抽象艺术",
        "title": "流金岁月",
    },
]

RATIO_SIZES = {
    "square": "1024x1024",
    "portrait_34": "768x1024",
    "portrait_916": "768x1360",
    "landscape_43": "1024x768",
    "landscape_169": "1360x768",
}


def generate_one(prompt, size, index, total):
    url = f"{OPENAI_BASE_URL}/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "prompt": prompt,
        "size": size,
        "quality": "medium",
        "n": 1,
        "response_format": "b64_json",
        "output_format": "png",
    }

    print(f"[{index+1}/{total}] Generating...", flush=True)
    try:
        with httpx.Client(timeout=180) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        image_data = base64.b64decode(data["data"][0]["b64_json"])
        filename = f"showcase_{index+1:02d}.png"
        filepath = os.path.join(SHOWCASE_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(image_data)

        print(f"[{index+1}/{total}] Saved: {filepath}", flush=True)
        return filename
    except Exception as e:
        print(f"[{index+1}/{total}] Failed: {e}", flush=True)
        return None


def main():
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set")
        return

    results = []
    total = len(PROMPTS)

    for i, item in enumerate(PROMPTS):
        size = RATIO_SIZES.get(item["ratio"], "1024x1024")
        filename = generate_one(item["prompt"], size, i, total)
        results.append({
            "index": i + 1,
            "filename": filename,
            "category": item["category"],
            "title": item["title"],
            "ratio": item["ratio"],
            "prompt": item["prompt"],
        })
        if i < total - 1:
            time.sleep(2)

    manifest_path = os.path.join(SHOWCASE_DIR, "manifest.txt")
    with open(manifest_path, "w", encoding="utf-8") as f:
        for r in results:
            if r["filename"]:
                f.write(f"{r['filename']}|{r['category']}|{r['title']}|{r['ratio']}\n")

    success = sum(1 for r in results if r["filename"])
    print(f"\nDone: {success}/{total} images generated")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
