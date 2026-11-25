---
name: demo-video-factory
description: 全自动产品演示片与提案短视频工厂：分镜 JSON → OpenAI 兼容 TTS 中/日/英配音 → 精准 SRT 字幕轴 → 录屏/配图/图生视频素材适配 → ffmpeg 一键合成 1080p 交付级 MP4（PPT/网页秒开）。触发：做产品演示视频、给录屏配中/日文旁白字幕、把分镜和截图做成提案短视频、调用本地 TTS/ASR/Wan 生成演示片。
---

# demo-video-factory — 全自动产品演示片工厂

> **核心理念**：用一份声明式 `storyboard.json` 驱动「配音 → 字幕 → 视觉镜头 → 合成交付」，把原本需要剪辑软件熬两天的产品演示片压缩到 10 分钟可复跑流水线。

## 配置（严禁硬编码端点，全部走 `.env` 或环境变量）

参考 `.env.example`：
- `TTS_BASE_URL`：OpenAI 兼容语音合成服务（如 `http://localhost:8872/v1`）
- `TTS_MODEL` / `TTS_VOICE`：默认模型与音色
- `ASR_BASE_URL`：可选，OpenAI 兼容 `/v1/audio/transcriptions` 端点
- `COMFYUI_BASE_URL`：可选，ComfyUI 图生视频（Wan）端点

## 标准 4 步流水线

### 1. 准备分镜 `storyboard.json`
```json
{
  "title": "Product Demo",
  "resolution": "1920x1080",
  "fps": 30,
  "scenes": [
    {
      "id": "s01",
      "narration": "欢迎观看自动化平台演示。",
      "visual_type": "image",
      "visual_path": "./assets/cover.png",
      "pad_sec": 0.4
    },
    {
      "id": "s02",
      "narration": "系统自动完成数据核对并生成证据报告。",
      "visual_type": "video",
      "visual_path": "./assets/screen_capture.mp4",
      "pad_sec": 0.3
    }
  ]
}
```
- `visual_type` 支持 `image`（自动等比缩放适配 1080p）、`video`（截断或定格补齐匹配语音时长）、`title`（纯色+居中标题卡，零外部素材即可出片）。

### 2. 生成逐幕配音（可选 `--dry-run-silence` 离线联调）
```bash
python scripts/tts_gen.py storyboard.json --work-dir ./work
```
输出 `work/audio/<id>.wav` 及带精确时长的 `work/timeline.json`。

### 3. 生成精准字幕（SRT）
```bash
python scripts/srt_align.py ./work/timeline.json --out ./work/subtitles.srt
```

### 4. 一键合成交付级 MP4（H.264 + AAC + faststart）
```bash
python scripts/compose_video.py storyboard.json --timeline ./work/timeline.json --srt ./work/subtitles.srt --out ./out/demo.mp4
```

### 可选：ComfyUI Wan 图生视频片段
```bash
python scripts/wan_i2v.py --workflow workflow.json --out-dir ./assets/clips
```
> 若远端 GPU 与 LLM 共享互斥显存，调用前请确认窗口空闲并在完成后释放/归还 GPU。
