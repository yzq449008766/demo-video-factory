import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compose_video  # noqa: E402
import srt_align  # noqa: E402
import tts_gen  # noqa: E402


class TestDemoVideoFactory(unittest.TestCase):
    def test_end_to_end_compose_with_silence_and_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            sb_path = t / "storyboard.json"
            sb = {
                "title": "Smoke Test",
                "resolution": "1280x720",
                "fps": 24,
                "scenes": [
                    {"id": "s01", "narration": "First scene narration.", "visual_type": "title", "bg_color": "0x0B2545", "pad_sec": 0.2},
                    {"id": "s02", "narration": "Second scene narration.", "visual_type": "title", "bg_color": "0x134074", "pad_sec": 0.2},
                ],
            }
            sb_path.write_text(json.dumps(sb, ensure_ascii=False), encoding="utf-8")

            work = t / "work"
            tl = tts_gen.generate_timeline(sb, work, dry_run_silence=True)
            self.assertEqual(len(tl["scenes"]), 2)
            self.assertGreater(tl["total_duration_sec"], 3.0)

            srt_text = srt_align.build_srt(tl)
            self.assertEqual(srt_text.count("-->"), 2)
            srt_path = work / "subtitles.srt"
            srt_path.write_text(srt_text, encoding="utf-8")

            out_mp4 = t / "out" / "smoke.mp4"
            info = compose_video.compose(sb_path, work / "timeline.json", out_mp4, srt_path)
            self.assertTrue(out_mp4.exists())
            stream_types = {s["codec_type"] for s in info["streams"]}
            self.assertIn("video", stream_types)
            self.assertIn("audio", stream_types)
            self.assertIn("subtitle", stream_types)


if __name__ == "__main__":
    unittest.main()
