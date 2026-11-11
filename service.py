"""Local WebSocket bridge for the React/Tauri desktop frontend.

The browser UI can run without this bridge for interaction and previews. The
desktop shell starts this service when an actual compression is requested.
"""
from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from typing import Any

import cv2
import websockets

from python.config import PipelineConfig
from python.pipeline import process_video


def _encode_image(image: Any) -> str:
    success, encoded = cv2.imencode(".webp", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if not success:
        raise RuntimeError("The processed preview could not be encoded")
    return base64.b64encode(encoded.tobytes()).decode("ascii")


async def _analyze(websocket: Any) -> None:
    message = json.loads(await websocket.recv())
    if message.get("type") != "analyze":
        await websocket.send(json.dumps({"type": "error", "message": "Unsupported request"}))
        return

    await websocket.send(json.dumps({"type": "progress", "value": 8, "label": "Loading video"}))
    settings = message.get("settings", {})
    config = PipelineConfig(
        bandwidth_kbps=int(settings.get("bandwidth_kbps", 350)),
        background_blur_strength=int(settings.get("background_softness", 55)),
        background_block_size=max(4, int(settings.get("background_softness", 55) / 5)),
        roi_quality=int(settings.get("subject_detail", 92)),
        roi_bandwidth_percent=min(95, 70 + int(settings.get("subject_detail", 92) * 0.25)),
        max_frames=int(settings.get("max_frames", 180)),
    )
    await websocket.send(json.dumps({"type": "progress", "value": 18, "label": "Finding focus areas"}))

    try:
        baseline, semantic, focus_map, metrics = await asyncio.to_thread(
            process_video, Path(message["video_path"]), config
        )
    except (OSError, RuntimeError, ValueError) as exc:
        await websocket.send(json.dumps({"type": "error", "message": str(exc)}))
        return

    await websocket.send(json.dumps({"type": "progress", "value": 92, "label": "Preparing previews"}))
    await websocket.send(
        json.dumps(
            {
                "type": "complete",
                "metrics": metrics,
                "baseline": _encode_image(baseline),
                "semantic": _encode_image(semantic),
                "focus_map": _encode_image(focus_map),
            }
        )
    )


async def main() -> None:
    async with websockets.serve(_analyze, "127.0.0.1", 8765, max_size=64 * 1024 * 1024):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
