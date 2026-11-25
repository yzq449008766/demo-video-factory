#!/usr/bin/env python3
"""Compose 1080p presentation-ready MP4 from storyboard.json, timeline.json, and optional SRT."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def parse_res(res: str) -> tuple[int, int]:
    w, h = res.lower().split("x", 1)
    return int(w), int(h)


def render_scene_clip(
    scene: dict[str, Any],
    tl_entry: dict[str, Any],
    out_mp4: Path,
    width: int,
    height: int,
    fps: int,
    base_dir: Path,
) -> None:
    dur = float(tl_entry["total_dur"])
    audio_path = Path(tl_entry["audio_path"])
    vtype = str(scene.get("visual_type", "title")).lower()
    bg_color = str(scene.get("bg_color", "0x0B2545"))

    vf_scale = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={bg_color},setsar=1"
    )

    if vtype == "image":
        img = (base_dir / scene["visual_path"]).resolve()
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-loop", "1", "-t", f"{dur:.3f}", "-i", str(img),
            "-i", str(audio_path),
            "-vf", vf_scale,
            "-af", f"apad=whole_dur={dur:.3f}",
            "-r", str(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-t", f"{dur:.3f}", str(out_mp4),
        ]
    elif vtype == "video":
        vid = (base_dir / scene["visual_path"]).resolve()
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-stream_loop", "-1", "-i", str(vid),
            "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", vf_scale,
            "-af", f"apad=whole_dur={dur:.3f}",
            "-r", str(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-t", f"{dur:.3f}", str(out_mp4),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"color=c={bg_color}:s={width}x{height}:r={fps}:d={dur:.3f}",
            "-i", str(audio_path),
            "-af", f"apad=whole_dur={dur:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-t", f"{dur:.3f}", str(out_mp4),
        ]
    subprocess.run(cmd, check=True)


def compose(
    storyboard_path: Path,
    timeline_path: Path,
    out_mp4: Path,
    srt_path: Path | None = None,
) -> dict[str, Any]:
    sb = json.loads(storyboard_path.read_text(encoding="utf-8"))
    tl = json.loads(timeline_path.read_text(encoding="utf-8"))
    width, height = parse_res(str(sb.get("resolution", "1920x1080")))
    fps = int(sb.get("fps", 30))
    base_dir = storyboard_path.resolve().parent

    tl_map = {e["id"]: e for e in tl.get("scenes") or []}
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        clips: list[Path] = []
        for idx, sc in enumerate(sb.get("scenes") or [], start=1):
            sid = str(sc.get("id") or f"s{idx:02d}")
            clip = tdir / f"{idx:03d}_{sid}.mp4"
            render_scene_clip(sc, tl_map[sid], clip, width, height, fps, base_dir)
            clips.append(clip)

        concat_file = tdir / "concat.txt"
        concat_file.write_text(
            "\n".join(f"file '{c.as_posix()}'" for c in clips) + "\n",
            encoding="utf-8",
        )
        merged = tdir / "merged.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-f", "concat", "-safe", "0", "-i", str(concat_file),
                "-c", "copy", str(merged),
            ],
            check=True,
        )

        if srt_path and srt_path.exists() and srt_path.stat().st_size > 0:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error",
                    "-i", str(merged), "-i", str(srt_path),
                    "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
                    "-movflags", "+faststart", str(out_mp4),
                ],
                check=True,
            )
        else:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error",
                    "-i", str(merged), "-c", "copy",
                    "-movflags", "+faststart", str(out_mp4),
                ],
                check=True,
            )

    probe = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height",
            "-show_entries", "format=duration,size", "-of", "json", str(out_mp4),
        ],
        text=True,
    )
    return json.loads(probe)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compose demo MP4 from storyboard + timeline + optional SRT")
    p.add_argument("storyboard", help="Path to storyboard.json")
    p.add_argument("--timeline", required=True, help="Path to timeline.json")
    p.add_argument("--srt", default=None, help="Optional SRT subtitle file")
    p.add_argument("--out", required=True, help="Output MP4 path")
    args = p.parse_args(argv)

    info = compose(Path(args.storyboard), Path(args.timeline), Path(args.out), Path(args.srt) if args.srt else None)
    print(json.dumps({
        "out": str(Path(args.out).resolve()),
        "duration": info["format"].get("duration"),
        "size_bytes": info["format"].get("size"),
        "streams": [s.get("codec_type") for s in info.get("streams") or []],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
