import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from core.database import init_global_db


class TestGenerateService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_global_db()

    def test_generate_image_returns_dict(self):
        from services.generate_service import generate_image
        result = generate_image(
            prompt="test prompt",
            model_name="gpt-image-2",
            width=1024,
            height=1024,
        )
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)

    def test_generate_image_with_params(self):
        from services.generate_service import generate_image
        result = generate_image(
            prompt="a beautiful sunset",
            negative_prompt="blurry",
            model_name="gpt-image-2",
            width=1024,
            height=1536,
            package_type="基础版",
        )
        self.assertIsInstance(result, dict)


class TestModelService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_global_db()

    def test_get_available_models(self):
        from services.model_service import get_available_models
        models = get_available_models()
        self.assertIsInstance(models, list)
        self.assertIn("gpt-image-2", models)

    def test_get_model_info(self):
        from services.model_service import get_model_info
        info = get_model_info("gpt-image-2")
        self.assertIsNotNone(info)
        self.assertEqual(info["name"], "GPT Image 2")
        self.assertIn("1024x1024", info["supported_sizes"])

    def test_get_model_info_not_found(self):
        from services.model_service import get_model_info
        info = get_model_info("nonexistent-model")
        self.assertIsNone(info)


class TestStyleService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_global_db()
        from services.style_service import init_preset_styles
        init_preset_styles()

    def test_get_style_list(self):
        from services.style_service import get_style_list
        styles = get_style_list()
        self.assertIsInstance(styles, list)

    def test_add_and_delete_style(self):
        from services.style_service import add_style, delete_style, get_style_by_name
        success, msg = add_style(
            style_name="test_style_unique",
            style_prompt="test prompt",
            negative_prompt="test negative",
            category="测试",
        )
        self.assertTrue(success)

        style = get_style_by_name("test_style_unique")
        self.assertIsNotNone(style)

        success, msg = delete_style("test_style_unique")
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
