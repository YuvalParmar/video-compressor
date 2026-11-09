from __future__ import annotations

import importlib
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import PipelineConfig
from .metrics import summarize
from .ml_pipeline import SemanticMaskPipeline
from .video_source import read_video


def load_native_codec(config: PipelineConfig | int) -> Any:
    try:
        native = importlib.import_module("semantic_codec")
    except ImportError as exc:
        raise RuntimeError(
            "The native codec is not built. Run scripts\\build_extension.ps1 first."
        ) from exc
    settings = native.CodecSettings()
    if isinstance(config, int):
        settings.bandwidth_kbps = config
    else:
        settings.bandwidth_kbps = config.bandwidth_kbps
        settings.target_fps = config.target_fps
        settings.roi_bandwidth_percent = config.roi_bandwidth_percent
    return native.CodecEngine(settings)


def process_video(video_path: str | Path, config: PipelineConfig) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    codec = load_native_codec(config)
    segmenter = SemanticMaskPipeline(
        config.model_path,
        input_size=(config.inference_width, config.inference_height),
        confidence_threshold=config.confidence_threshold,
        dilation=config.roi_dilation,
    )
    semantic_frames: list[np.ndarray] = []
    baseline_frames: list[np.ndarray] = []
    result_metrics: list[dict[str, float]] = []
    masks: list[np.ndarray] = []
    started = time.perf_counter()
    for _, frame, _ in read_video(video_path, config.max_frames):
        mask = segmenter.infer(frame)
        result = codec.process(frame, mask)
        baseline_frames.append(cv2.cvtColor(result["baseline"], cv2.COLOR_BGR2RGB))
        semantic_frames.append(cv2.cvtColor(result["semantic"], cv2.COLOR_BGR2RGB))
        masks.append(result["mask"])
        result_metrics.append({
            "semantic_bytes": float(result["semantic_bytes"]),
            "roi_bytes": float(result["roi_bytes"]),
            "frame_dropped": float(result["frame_dropped"]),
        })
    if not semantic_frames:
        raise ValueError("The selected video contains no readable frames")
    metrics = summarize(result_metrics, masks)
    metrics["processing_fps"] = len(semantic_frames) / max(time.perf_counter() - started, 1e-6)
    return np.concatenate(baseline_frames, axis=1), np.concatenate(semantic_frames, axis=1), metrics
