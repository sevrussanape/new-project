import unittest

from engine.duration_planner import (
    DURATION_PRESETS,
    plan_scene_slots,
    resolve_duration,
)


class DurationPlannerTests(unittest.TestCase):
    def test_all_presets_resolve(self):
        for label, seconds in DURATION_PRESETS.items():
            with self.subTest(label=label):
                self.assertEqual(resolve_duration(label), seconds)

    def test_sixty_seconds_is_an_optional_preset(self):
        self.assertEqual(resolve_duration("60 seconds"), 60)
        self.assertEqual(resolve_duration("30 seconds"), 30)
        self.assertNotEqual(resolve_duration("30 seconds"), 60)

    def test_custom_duration(self):
        self.assertEqual(resolve_duration("Custom", 73), 73)

    def test_custom_duration_rejects_invalid_values(self):
        for value in (None, 4, 1801, 12.5, "not-a-number", True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    resolve_duration("Custom", value)

    def test_unknown_preset_rejected(self):
        with self.assertRaises(ValueError):
            resolve_duration("10 minutes")

    def test_scene_plan_exactly_matches_target(self):
        for total in (15, 30, 45, 60, 90, 120, 300, 73):
            with self.subTest(total=total):
                slots = plan_scene_slots(total)
                self.assertEqual(sum(slot.duration_seconds for slot in slots), total)
                self.assertEqual(slots[0].start_seconds, 0)
                self.assertEqual([s.index for s in slots], list(range(1, len(slots) + 1)))
                for previous, current in zip(slots, slots[1:]):
                    self.assertEqual(current.start_seconds,
                                     previous.start_seconds + previous.duration_seconds)
                self.assertTrue(all(2 <= s.duration_seconds <= 4 for s in slots))

    def test_remainder_is_balanced(self):
        slots = plan_scene_slots(5)
        self.assertEqual([s.duration_seconds for s in slots], [3, 2])

    def test_invalid_total_rejected(self):
        for value in (1, 0, -1, 4.5, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    plan_scene_slots(value)


if __name__ == "__main__":
    unittest.main()
