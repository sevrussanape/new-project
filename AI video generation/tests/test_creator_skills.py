import json
import unittest

import creator_skills as skills


SRT = """1
00:00:00,000 --> 00:00:08,000
We start with the first idea.

2
00:00:12,000 --> 00:00:20,000
The next part explains the problem.

3
00:00:22,000 --> 00:00:30,000
Now we show the first solution.

4
00:00:32,000 --> 00:00:40,000
Here is another useful detail.

5
00:00:42,000 --> 00:00:50,000
This is the practical example.

6
00:00:52,000 --> 00:01:00,000
Finally we explain the result.
"""


class TranscriptSkillTests(unittest.TestCase):
    def test_parse_srt(self):
        cues = skills.parse_transcript(SRT)
        self.assertEqual(len(cues), 6)
        self.assertEqual(cues[0][0], 0.0)
        self.assertEqual(cues[-1][1], 60.0)

    def test_chapters_are_valid_and_start_at_zero(self):
        result = skills.run_chapters(SRT, target=3)
        self.assertTrue(result["valid"])
        self.assertEqual(result["chapters"][0]["timestamp"], "00:00")
        self.assertGreaterEqual(len(result["chapters"]), 3)
        self.assertTrue(all(c["duration_seconds"] >= 10 for c in result["chapters"]))

    def test_chapters_accept_whisper_segments_object(self):
        segments = [
            {"start": 0, "end": 8, "text": "Opening idea here."},
            {"start": 12, "end": 20, "text": "Explain the main problem."},
            {"start": 22, "end": 30, "text": "Show the first solution."},
            {"start": 32, "end": 40, "text": "Add another important detail."},
            {"start": 42, "end": 50, "text": "Give a practical example."},
            {"start": 52, "end": 60, "text": "Finish with the result."},
        ]
        result = skills.run_skill("yt-chapters", json.dumps({"target": 3, "segments": segments}))
        self.assertEqual(result["engine"], "python")
        self.assertIn("Valid YouTube chapters: YES", result["result"])

    def test_edit_accepts_whisper_segments_object(self):
        segments = [
            {"start": 0, "end": 2, "text": "Hello everyone."},
            {"start": 4, "end": 4.5, "text": "Um."},
            {"start": 7, "end": 9, "text": "Today we build this."},
            {"start": 10, "end": 12, "text": "Today we build this."},
        ]
        result = skills.run_skill("yt-edit", json.dumps({"floor": 0.4, "segments": segments}))
        self.assertEqual(result["engine"], "python")
        self.assertIn("FILLER", result["result"])

    def test_edit_detects_dead_air_and_filler(self):
        transcript = """1
00:00:00,000 --> 00:00:02,000
Hello everyone.

2
00:00:04,000 --> 00:00:04,500
Um.

3
00:00:07,000 --> 00:00:09,000
Today we build this.

4
00:00:10,000 --> 00:00:12,000
Today we build this.
"""
        result = skills.run_edit(transcript, floor=0.4)
        kinds = {c["kind"] for c in result["cuts"]}
        self.assertIn("DEAD", kinds)
        self.assertIn("FILLER", kinds)
        self.assertIn("REPEAT", kinds)

    def test_retention_csv_detects_opening_loss_and_mid_slide(self):
        csv_text = "position,still_watching\n0,100\n10,80\n20,75\n30,65\n40,60\n50,55\n60,50\n70,45\n"
        result = skills.run_retention(csv_text, duration_seconds=100)
        self.assertEqual(result["hook_verdict"], "leaking")
        self.assertGreater(result["hook_loss_first_30s_or_10pct"], 25)
        self.assertGreater(result["average_mid_video_drop_per_step"], 0)

    def test_retention_accepts_elapsed_time_axis(self):
        csv_text = "elapsed_time,still_watching\n00:00,100\n00:10,90\n00:20,80\n00:30,70\n00:40,60\n00:50,50\n01:00,40\n01:10,30\n"
        result = skills.run_retention(csv_text, duration_seconds=70)
        self.assertEqual(result["hook_loss_first_30s_or_10pct"], 30.0)
        self.assertEqual(result["hook_verdict"], "leaking")

    def test_viral_outlier_uses_each_channel_median(self):
        videos = [
            {"channel": "A", "title": "One", "views": 100},
            {"channel": "A", "title": "Two", "views": 110},
            {"channel": "A", "title": "Three", "views": 90},
            {"channel": "A", "title": "Four", "views": 1000, "url": "https://example.com"},
            {"channel": "A", "title": "Five", "views": 100},
        ]
        result = skills.run_viral(json.dumps(videos), minimum_multiple=1.5)
        self.assertEqual(len(result["outliers"]), 1)
        self.assertEqual(result["outliers"][0]["multiple_of_median"], 10.0)

    def test_python_skill_dispatch(self):
        result = skills.run_skill("yt-chapters", SRT)
        self.assertEqual(result["engine"], "python")
        self.assertIn("Valid YouTube chapters", result["result"])

    def test_audit_does_not_claim_to_fetch_url(self):
        with self.assertRaises(ValueError):
            skills.run_skill("yt-audit", "https://youtube.com/@somechannel")

    def test_hook_scorecard_uses_five_dimensions(self):
        result = skills._score_hook("Why do you still lose viewers in the first 10 seconds?")
        self.assertEqual(set(result["properties"]), {
            "specificity", "direct_address", "stakes", "curiosity", "brevity"
        })
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertEqual(result["formula"], "The Question")

    def test_viral_title_formula_uses_21_formula_library(self):
        self.assertEqual(
            skills._title_formula("I tried this for 30 days so you don't have to"),
            "I Tried It"
        )
        self.assertEqual(len(skills.HOOK_FORMULAS), 21)

    def test_unknown_skill_is_rejected(self):
        with self.assertRaises(ValueError):
            skills.run_skill("yt-not-real", "hello")


if __name__ == "__main__":
    unittest.main()
