from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np


def read_video(path: str | Path, max_frames: int) -> Iterator[tuple[int, np.ndarray, float]]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"video file not found: {source}")
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise OSError(f"OpenCV could not open video: {source}")
    source_fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    try:
        for index in range(max_frames):
            ok, frame = capture.read()
            if not ok:
                break
            yield index, np.ascontiguousarray(frame), float(source_fps)
    finally:
        capture.release()
