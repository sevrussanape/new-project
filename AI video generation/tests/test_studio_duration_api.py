import unittest

from studio import build_duration_plan


class StudioDurationApiTests(unittest.TestCase):
    def test_default_plan_is_sixty_seconds_but_not_forced(self):
        default = build_duration_plan({})
        shorter = build_duration_plan({"duration_preset": "30 seconds"})
        self.assertEqual(default["total_duration_seconds"], 60)
        self.assertEqual(shorter["total_duration_seconds"], 30)
        self.assertEqual(sum(s["duration_seconds"] for s in default["scene_slots"]), 60)

    def test_custom_duration_plan(self):
        plan = build_duration_plan({
            "duration_preset": "Custom",
            "custom_duration_seconds": 73,
            "max_scene_seconds": 4,
            "min_scene_seconds": 2,
        })
        self.assertEqual(plan["total_duration_seconds"], 73)
        self.assertEqual(plan["scene_count"], len(plan["scene_slots"]))
        self.assertEqual(sum(s["duration_seconds"] for s in plan["scene_slots"]), 73)

    def test_scene_slots_are_contiguous(self):
        plan = build_duration_plan({"duration_preset": "90 seconds"})
        slots = plan["scene_slots"]
        self.assertEqual(slots[0]["start_seconds"], 0)
        for previous, current in zip(slots, slots[1:]):
            self.assertEqual(
                current["start_seconds"],
                previous["start_seconds"] + previous["duration_seconds"],
            )

    def test_invalid_preset_and_scene_bounds_are_rejected(self):
        with self.assertRaises(ValueError):
            build_duration_plan({"duration_preset": "10 minutes"})
        with self.assertRaises(ValueError):
            build_duration_plan({"duration_preset": "30 seconds", "min_scene_seconds": 5,
                                 "max_scene_seconds": 4})

    def test_planning_response_does_not_claim_generation(self):
        plan = build_duration_plan({"duration_preset": "15 seconds"})
        self.assertEqual(plan["status"], "planned")
        self.assertIn("planning only", plan["note"].lower())


if __name__ == "__main__":
    unittest.main()
