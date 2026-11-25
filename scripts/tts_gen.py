#!/usr/bin/env python3
"""Generate per-scene narration audio via OpenAI-compatible /v1/audio/speech (or offline silence dry-run)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def probe_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return round(float(out), 3)


def make_silence_wav(out_path: Path, duration_sec: float) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", f"{duration_sec:.3f}",
            "-c:a", "pcm_s16le", str(out_path),
        ],
        check=True,
    )


def call_tts_api(text: str, out_path: Path, base_url: str, api_key: str, model: str, voice: str) -> None:
    url = f"{base_url.rstrip('/')}/audio/speech"
    payload = {
        "model": model,
        "voice": voice,
        "input": text,
        "response_format": "wav",
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=180) as resp:
        out_path.write_bytes(resp.read())


def generate_timeline(
    storyboard: dict[str, Any],
    work_dir: Path,
    dry_run_silence: bool = False,
) -> dict[str, Any]:
    audio_dir = work_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    base_url = os.environ.get("TTS_BASE_URL", "http://127.0.0.1:8872/v1")
    api_key = os.environ.get("TTS_API_KEY", "")
    model = os.environ.get("TTS_MODEL", "tts-1")
    voice = os.environ.get("TTS_VOICE", "alloy")

    cursor = 0.0
    entries: list[dict[str, Any]] = []
    for idx, scene in enumerate(storyboard.get("scenes") or [], start=1):
        sid = str(scene.get("id") or f"s{idx:02d}")
        narration = str(scene.get("narration") or "").strip()
        pad = float(scene.get("pad_sec", 0.3))
        out_wav = audio_dir / f"{sid}.wav"

        if dry_run_silence or not narration:
            est = max(1.5, min(8.0, len(narration) * 0.18)) if narration else float(scene.get("duration_sec", 2.0))
            make_silence_wav(out_wav, est)
        else:
            call_tts_api(narration, out_wav, base_url, api_key, model, voice)

        speech_dur = probe_duration(out_wav)
        total_dur = round(speech_dur + pad, 3)
        entries.append({
            "id": sid,
            "narration": narration,
            "audio_path": str(out_wav.resolve()),
            "start_sec": round(cursor, 3),
            "speech_end_sec": round(cursor + speech_dur, 3),
            "end_sec": round(cursor + total_dur, 3),
            "speech_dur": speech_dur,
            "total_dur": total_dur,
        })
        cursor += total_dur

    timeline = {
        "title": storyboard.get("title", "Demo"),
        "total_duration_sec": round(cursor, 3),
        "scenes": entries,
    }
    (work_dir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return timeline


def main(argv: list[str] | None = None) -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    p = argparse.ArgumentParser(description="Generate per-scene TTS audio and timeline.json")
    p.add_argument("storyboard", help="Path to storyboard.json")
    p.add_argument("--work-dir", required=True, help="Working directory for audio and timeline.json")
    p.add_argument("--dry-run-silence", action="store_true", help="Generate silent tracks instead of calling TTS API")
    args = p.parse_args(argv)

    sb = json.loads(Path(args.storyboard).read_text(encoding="utf-8"))
    tl = generate_timeline(sb, Path(args.work_dir), dry_run_silence=args.dry_run_silence)
    print(json.dumps({"scenes": len(tl["scenes"]), "total_duration_sec": tl["total_duration_sec"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
