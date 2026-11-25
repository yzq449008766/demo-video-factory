#!/usr/bin/env python3
"""Submit a ComfyUI workflow JSON (e.g. Wan TI2V) to COMFYUI_BASE_URL and poll until completion."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def http_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Submit a ComfyUI Wan workflow and download generated video/frames")
    p.add_argument("--workflow", required=True, help="ComfyUI API-format workflow JSON path")
    p.add_argument("--out-dir", required=True, help="Local directory to save outputs")
    p.add_argument("--timeout", type=int, default=600, help="Max wait seconds")
    args = p.parse_args(argv)

    base = os.environ.get("COMFYUI_BASE_URL", "http://127.0.0.1:8188").rstrip("/")
    wf = json.loads(Path(args.workflow).read_text(encoding="utf-8"))
    res = http_json(f"{base}/prompt", {"prompt": wf})
    prompt_id = res["prompt_id"]
    deadline = time.time() + args.timeout

    history: dict[str, Any] = {}
    while time.time() < deadline:
        h = http_json(f"{base}/history/{prompt_id}")
        if prompt_id in h:
            history = h[prompt_id]
            break
        time.sleep(3)
    else:
        print(f"ERROR: timeout waiting for prompt_id={prompt_id}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []
    for node_out in (history.get("outputs") or {}).values():
        for bucket in ("gifs", "videos", "images"):
            for item in node_out.get(bucket) or []:
                qs = urllib.parse.urlencode({
                    "filename": item["filename"],
                    "subfolder": item.get("subfolder", ""),
                    "type": item.get("type", "output"),
                })
                dest = out_dir / item["filename"]
                urllib.request.urlretrieve(f"{base}/view?{qs}", dest)
                downloaded.append(str(dest.resolve()))

    print(json.dumps({"prompt_id": prompt_id, "downloaded": downloaded}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
