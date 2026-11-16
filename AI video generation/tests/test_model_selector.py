import unittest
from model_selector import recommend_models
from engine.video_engine import ltx_capability


def inventory(vram_mb, ram_gb=64, disk_gb=500, cuda=True, free_mb=None):
    return {"primary_gpu": {"name": "NVIDIA GeForce RTX", "vram_total_mb": vram_mb,
                            "vram_free_mb": free_mb if free_mb is not None else vram_mb * .9,
                            "compute_capability": "8.9"},
            "memory_gb": ram_gb, "disk": {"free_gb": disk_gb},
            "compute_runtime": {"cuda_available": cuda}}


class ModelSelectorTests(unittest.TestCase):
    def test_4gb_gpu_does_not_get_false_compatible_recommendation(self):
        result = recommend_models(inventory(4096))
        self.assertEqual(result["status"], "no-validated-fit")
        self.assertIsNone(result["selected_model"])
        self.assertFalse(result["ranked_models"][0]["compatible_by_planning_rules"])

    def test_ltx_selected_when_all_planning_gates_are_met(self):
        result = recommend_models(inventory(12288, free_mb=11000))
        self.assertEqual(result["status"], "recommended")
        self.assertEqual(result["selected_model"]["id"], "ltx-video-diffusers")

    def test_free_vram_gate_blocks_model(self):
        result = recommend_models(inventory(12288, free_mb=4096))
        self.assertIsNone(result["selected_model"])
        self.assertTrue(any("free" in x.lower() for x in result["ranked_models"][0]["blockers"]))

    def test_missing_free_vram_blocks_model(self):
        machine = inventory(12288)
        machine["primary_gpu"].pop("vram_free_mb")
        self.assertIsNone(recommend_models(machine)["selected_model"])

    def test_insufficient_disk_blocks_model(self):
        result = recommend_models(inventory(12288, disk_gb=5, free_mb=11000))
        self.assertIsNone(result["selected_model"])

    def test_cuda_unavailable_blocks_gpu_models(self):
        result = recommend_models(inventory(24576, cuda=False, free_mb=20000))
        self.assertIsNone(result["selected_model"])
        self.assertTrue(any("CUDA" in reason for reason in result["ranked_models"][0]["blockers"]))

    def test_missing_gpu_is_not_assumed_compatible(self):
        result = recommend_models({"memory_gb": 64, "disk": {"free_gb": 500}})
        self.assertEqual(result["status"], "no-validated-fit")
        self.assertIsNone(result["selected_model"])

    def test_runtime_gate_uses_same_selector_as_advisor(self):
        machine = inventory(12288, free_mb=11000)
        self.assertTrue(ltx_capability(machine)["available"])
        machine["primary_gpu"]["vram_free_mb"] = 4096
        self.assertFalse(ltx_capability(machine)["available"])


if __name__ == "__main__":
    unittest.main()
