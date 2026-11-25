#!/usr/bin/env python3
"""Build exact SRT subtitles from timeline.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def fmt_srt_time(seconds: float) -> str:
    ms_total = max(0, int(round(seconds * 1000)))
    hours = ms_total // 3_600_000
    rem = ms_total % 3_600_000
    minutes = rem // 60_000
    rem %= 60_000
    secs = rem // 1000
    ms = rem % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_srt(timeline: dict[str, Any]) -> str:
    blocks: list[str] = []
    idx = 1
    for sc in timeline.get("scenes") or []:
        text = str(sc.get("narration") or "").strip()
        if not text:
            continue
        start = fmt_srt_time(float(sc["start_sec"]))
        end = fmt_srt_time(float(sc["speech_end_sec"]))
        blocks.append(f"{idx}\n{start} --> {end}\n{text}\n")
        idx += 1
    return "\n".join(blocks)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate SRT subtitles from timeline.json")
    p.add_argument("timeline", help="Path to timeline.json")
    p.add_argument("--out", required=True, help="Output .srt file path")
    args = p.parse_args(argv)

    tl = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    srt = build_srt(tl)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(srt, encoding="utf-8")
    print(json.dumps({"srt": str(out.resolve()), "cues": srt.count("-->")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
