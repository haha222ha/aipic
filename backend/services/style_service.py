from datetime import datetime

from core.database import global_db_conn


def get_style_list(category: str = ""):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        if category:
            cursor.execute(
                "SELECT * FROM global_style_library WHERE category = ? ORDER BY id",
                (category,)
            )
        else:
            cursor.execute("SELECT * FROM global_style_library ORDER BY category, id")
        styles = [dict(row) for row in cursor.fetchall()]
    return styles


def get_style_by_name(style_name: str):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM global_style_library WHERE style_name = ?", (style_name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_style(style_name: str, style_prompt: str, negative_prompt: str = "", category: str = "通用", is_preset: int = 0):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO global_style_library (style_name, style_prompt, style_negative_prompt, category, is_preset, create_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (style_name, style_prompt, negative_prompt, category, is_preset, datetime.now().isoformat()))
            conn.commit()
            return True, "风格添加成功"
        except Exception as e:
            if "UNIQUE" in str(e):
                return False, "风格名称已存在"
            return False, str(e)


def delete_style(style_name: str):
    with global_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM global_style_library WHERE style_name = ? AND is_preset = 0", (style_name,))
        if cursor.rowcount == 0:
            return False, "风格不存在或为预设风格不可删除"
        conn.commit()
    return True, "风格删除成功"


def init_preset_styles():
    presets = [
        ("国风水墨", "traditional chinese ink painting, watercolor, elegant, minimalist, zen", "blurry, low quality", "艺术"),
        ("赛博朋克", "cyberpunk, neon lights, futuristic city, rain, dark atmosphere", "bright, sunny, natural", "艺术"),
        ("水彩插画", "watercolor illustration, soft colors, artistic, dreamy", "harsh, dark, realistic", "艺术"),
        ("3D渲染", "3D render, octane render, cinema 4D, highly detailed, studio lighting", "flat, 2d, sketch", "技术"),
        ("日系动漫", "anime style, japanese animation, vibrant colors, detailed eyes", "realistic, photographic", "艺术"),
        ("油画风格", "oil painting, classical art, rich colors, textured brushstrokes", "digital, smooth, flat", "艺术"),
        ("极简设计", "minimalist design, clean lines, white space, modern, simple", "cluttered, complex, ornate", "设计"),
        ("电商产品", "product photography, white background, studio lighting, commercial", "artistic, abstract, dark", "商业"),
        ("人像摄影", "professional portrait photography, bokeh, natural lighting, high detail", "cartoon, anime, painting", "摄影"),
        ("像素艺术", "pixel art, 8-bit, retro game style, low resolution aesthetic", "realistic, high resolution", "游戏"),
    ]

    with global_db_conn() as conn:
        cursor = conn.cursor()
        for name, prompt, neg, cat in presets:
            try:
                cursor.execute('''
                    INSERT INTO global_style_library (style_name, style_prompt, style_negative_prompt, category, is_preset, create_time)
                    VALUES (?, ?, ?, ?, 1, ?)
                ''', (name, prompt, neg, cat, datetime.now().isoformat()))
            except Exception:
                pass
        conn.commit()
