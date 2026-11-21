import base64
import json
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image
import studio


class StudioApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), studio.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_endpoint_reports_native_engine(self):
        with urlopen(self.base + "/api/health", timeout=15) as response:
            payload = json.loads(response.read())
        self.assertTrue(payload["studio"])
        self.assertEqual(payload["engine"], "native-python")
        self.assertIn("ltx", payload["hardware"])

    def test_config_endpoint_exposes_limits(self):
        with urlopen(self.base + "/api/config", timeout=5) as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["limits"]["max_prompt_chars"], 2000)
        self.assertIn("image-motion", payload["modes"])

    def test_creator_skills_endpoint_lists_eleven_workflows(self):
        with urlopen(self.base + "/api/creator/skills", timeout=5) as response:
            payload = json.loads(response.read())
        self.assertEqual(len(payload["skills"]), 11)
        self.assertEqual(payload["recommended_model"], "qwen3.5:4b")

    def test_creator_viral_skill_runs_without_ollama(self):
        videos = [
            {"channel": "A", "title": "One", "views": 100},
            {"channel": "A", "title": "Two", "views": 100},
            {"channel": "A", "title": "Three", "views": 100},
            {"channel": "A", "title": "Four", "views": 100},
            {"channel": "A", "title": "Five", "views": 1000},
        ]
        payload = {"skill": "yt-viral", "input": json.dumps(videos)}
        request = Request(self.base + "/api/creator/run", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read())
        self.assertEqual(result["engine"], "python")
        self.assertIn("10.00", result["result"])

    def test_invalid_aspect_is_rejected(self):
        payload = {"mode": "image-motion", "prompt": "test", "aspect": "999:1"}
        request = Request(self.base + "/api/generate", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(Exception) as caught:
            urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 400)

    def test_oversized_prompt_is_rejected(self):
        payload = {"mode": "image-motion", "prompt": "x" * 2001}
        request = Request(self.base + "/api/generate", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(Exception) as caught:
            urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 400)

    def test_image_motion_job_runs_through_api(self):
        image_buffer = BytesIO()
        Image.new("RGB", (320, 240), (35, 90, 140)).save(image_buffer, format="JPEG")
        payload = {
            "mode": "image-motion", "prompt": "API integration test",
            "image_data": "data:image/jpeg;base64," + base64.b64encode(image_buffer.getvalue()).decode(),
            "duration": 2, "fps": 12, "aspect": "16:9",
        }
        request = Request(self.base + "/api/generate", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=10) as response:
            job = json.loads(response.read())["job"]
        deadline = time.time() + 20
        state = None
        while time.time() < deadline:
            with urlopen(self.base + "/api/jobs/" + job["id"], timeout=10) as response:
                state = json.loads(response.read())
            if state["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(.2)
        self.assertEqual(state["status"], "completed", state.get("error"))
        self.assertFalse(state["is_generative_ai"])
        with urlopen(self.base + state["output"], timeout=10) as response:
            self.assertEqual(response.headers.get("Content-Type"), "video/mp4")
            video_bytes = response.read()
            self.assertGreater(len(video_bytes), 1000)
        range_request = Request(self.base + state["output"], headers={"Range": "bytes=0-99"})
        with urlopen(range_request, timeout=10) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(len(response.read()), 100)
        Path(studio.OUTPUTS / Path(state["output"]).name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
