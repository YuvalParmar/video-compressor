from __future__ import annotations

import numpy as np


def region_mse(reference: np.ndarray, candidate: np.ndarray, mask: np.ndarray) -> float:
    if reference.shape != candidate.shape or reference.shape[:2] != mask.shape:
        raise ValueError("metric inputs must have matching dimensions")
    selected = mask.astype(bool)
    if not np.any(selected):
        return 0.0
    error = reference.astype(np.float32) - candidate.astype(np.float32)
    return float(np.mean(np.square(error[selected])))


def summarize(results: list[dict[str, float]], masks: list[np.ndarray]) -> dict[str, float]:
    if not results:
        return {"frames": 0.0, "semantic_kbps": 0.0, "roi_fraction": 0.0}
    total_bytes = sum(item["semantic_bytes"] for item in results)
    roi_bytes = sum(item["roi_bytes"] for item in results)
    seconds = max(len(results) / 30.0, 1 / 30.0)
    roi_fraction = float(np.mean([np.mean(mask > 0) for mask in masks]))
    return {
        "frames": float(len(results)),
        "semantic_kbps": total_bytes * 8.0 / seconds / 1000.0,
        "roi_fraction": roi_fraction,
        "dropped_frames": float(sum(item["frame_dropped"] for item in results)),
    }
