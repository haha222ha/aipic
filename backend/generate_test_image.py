import os
import sys
import base64
import uuid
import httpx

API_KEY = os.environ.get("OPENAI_API_KEY", "")
BASE_URL = "https://www.packyapi.com/v1"
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")

if not API_KEY:
    print("ERROR: 请设置环境变量 OPENAI_API_KEY")
    print("用法: $env:OPENAI_API_KEY='你的key'; python generate_test_image.py")
    sys.exit(1)

prompt = (
    "A stunning Xiaohongshu (Little Red Book) viral cover image design. "
    "Beautiful gradient background in warm pink and gold tones. "
    "Center: a delicious matcha latte art with flower pattern in a ceramic cup on a marble table, "
    "surrounded by cherry blossom petals. "
    "Large bold Chinese text '春日限定' at the top in elegant white font with soft shadow. "
    "Small Chinese text '治愈系下午茶' below. "
    "Trendy aesthetic, soft lighting, dreamy bokeh, pastel colors, "
    "Xiaohongshu style, Instagram aesthetic, lifestyle photography, "
    "clean composition, high-end magazine feel"
)

sizes_qualities = [
    ("1024x1024", "low", "standard_low_1024x1024"),
    ("1024x1024", "medium", "hd_medium_1024x1024"),
    ("1024x1024", "high", "ultra_high_1024x1024"),
    ("1024x1536", "medium", "hd_medium_1024x1536"),
    ("1536x1024", "medium", "hd_medium_1536x1024"),
]

print("=" * 60)
print("GPT-Image-2 测试图片生成 - 小红书爆款风格")
print("=" * 60)

for size, quality, label in sizes_qualities:
    print(f"\n--- 生成: {label} (size={size}, quality={quality}) ---")
    try:
        payload = {
            "model": "gpt-image-2",
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": 1,
            "response_format": "b64_json",
            "output_format": "png",
        }
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=180) as client:
            response = client.post(f"{BASE_URL}/images/generations", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        image_data = base64.b64decode(data["data"][0]["b64_json"])
        filename = f"gpt_image2_{label}.png"
        filepath = os.path.join(DESKTOP, filename)

        with open(filepath, "wb") as f:
            f.write(image_data)

        file_size_kb = len(image_data) / 1024
        print(f"  SUCCESS: {filepath}")
        print(f"  Size: {file_size_kb:.1f} KB")
        print(f"  Resolution: {size}")
        print(f"  Quality: {quality}")

    except Exception as e:
        print(f"  FAILED: {e}")

print("\n" + "=" * 60)
print("生成完成！请查看桌面上的图片文件")
print("=" * 60)
