import tempfile
import unittest
from pathlib import Path
from PIL import Image
from engine.video_engine import ltx_capability, render_image_motion


class VideoEngineTests(unittest.TestCase):
    def test_4gb_gpu_is_blocked_from_ltx(self):
        inventory = {
            "primary_gpu": {"name": "NVIDIA GTX 1650", "vram_total_mb": 4096, "vram_free_mb": 3500},
            "compute_runtime": {"cuda_available": True},
            "disk": {"free_gb": 500},
        }
        result = ltx_capability(inventory)
        self.assertFalse(result["available"])
        self.assertTrue(any("10 GB" in item for item in result["blockers"]))

    def test_missing_cuda_blocks_ltx(self):
        inventory = {"primary_gpu": {"name": "GPU", "vram_total_mb": 16384, "vram_free_mb": 14000},
                     "compute_runtime": {"cuda_available": False}, "disk": {"free_gb": 100}}
        self.assertFalse(ltx_capability(inventory)["available"])

    def test_image_motion_creates_mp4(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            image_path = folder / "source.jpg"
            output_path = folder / "render.mp4"
            Image.new("RGB", (800, 600), (45, 95, 145)).save(image_path)
            result = render_image_motion(image_path, output_path, duration=2, fps=12)
            self.assertTrue(result.exists())
            self.assertGreater(result.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
