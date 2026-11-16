import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine.production_pipeline import CONTENT_TYPES, create_script_package, write_captions


class ProductionPipelineTests(unittest.TestCase):
    def test_all_content_templates_are_available(self):
        for name in ("educational", "facts", "story", "documentary", "motivational",
                     "podcast", "product-explainer", "news-style", "how-to", "shorts"):
            self.assertIn(name, CONTENT_TYPES)

    @patch("engine.production_pipeline._post_local_json")
    def test_local_script_package_requires_exact_scene_count(self, mocked):
        mocked.return_value = {"response": json.dumps({
            "title": "A title", "description": "A description",
            "hook": "Look closely.", "script": "Look closely. Here is why.",
            "scenes": [
                {"narration": "Look closely.", "visual_prompt": "A cinematic close-up", "transition": "dissolve"},
                {"narration": "Here is why.", "visual_prompt": "A wide establishing shot", "transition": "cut"},
            ],
        })}
        package = create_script_package("How rain forms", "educational", 8, 2)
        self.assertEqual(len(package["scenes"]), 2)
        self.assertEqual(package["scenes"][0]["transition"], "dissolve")
        self.assertEqual(package["scenes"][1]["index"], 2)

    @patch("engine.production_pipeline._post_local_json")
    def test_invalid_scene_count_from_model_is_rejected(self, mocked):
        mocked.return_value = {"response": json.dumps({
            "title": "Bad", "script": "A script",
            "scenes": [{"visual_prompt": "Only one"}],
        })}
        with self.assertRaises(RuntimeError):
            create_script_package("A topic", "facts", 8, 2)

    def test_invalid_content_type_is_rejected(self):
        with self.assertRaises(ValueError):
            create_script_package("A topic", "unknown-format", 8, 2)

    def test_caption_file_has_sequential_cues(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.srt"
            write_captions("First sentence. Second sentence!", 10.0, path)
            text = path.read_text(encoding="utf-8-sig")
            self.assertIn("1\n00:00:00,000 --> ", text)
            self.assertIn("2\n", text)
            self.assertIn("Second sentence!", text)


if __name__ == "__main__":
    unittest.main()
