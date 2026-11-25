# demo-video-factory

Declarative, agent-driven product demo & pitch video pipeline:

`storyboard.json` → **OpenAI-compatible TTS** → **Exact SRT subtitle alignment** → **FFmpeg 1080p H.264/AAC composer** (supporting screen recordings, still images, title cards, and optional ComfyUI Wan I2V clips).

## Features

- **Zero third-party Python dependencies** (Python stdlib + `ffmpeg` / `ffprobe`).
- **Provider-agnostic endpoints**: Configure any local or cloud OpenAI-compatible `/v1/audio/speech` & `/v1/audio/transcriptions` endpoints via `.env`.
- **Offline dry-run mode**: `--dry-run-silence` synthesizes exact-duration silent tracks so you can verify cuts, timing, and layout without hitting TTS servers.
- **Presentation-ready MP4**: Uses `yuv420p` + `+faststart` for universal playback in PowerPoint, Keynote, and browsers.

## Quick Start

```bash
cp .env.example .env
python scripts/tts_gen.py examples/sample_storyboard.json --work-dir ./work --dry-run-silence
python scripts/srt_align.py ./work/timeline.json --out ./work/subtitles.srt
python scripts/compose_video.py examples/sample_storyboard.json --timeline ./work/timeline.json --srt ./work/subtitles.srt --out ./out/demo.mp4
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT
