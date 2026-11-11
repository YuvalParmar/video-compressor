from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class SemanticMaskPipeline:
    """Small OpenCV-DNN adapter with a stable binary-mask output contract."""

    def __init__(
        self,
        model_path: str | Path,
        input_size: tuple[int, int] = (320, 320),
        confidence_threshold: float = 0.35,
        dilation: int = 7,
    ) -> None:
        path = Path(model_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"ONNX model not found at {path}. Download a tested model into models/."
            )
        self.net = cv2.dnn.readNetFromONNX(str(path))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.input_size = input_size
        self.confidence_threshold = confidence_threshold
        self.dilation = max(0, dilation)
        self._dilation_kernel = (
            cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (self.dilation, self.dilation)
            )
            if self.dilation
            else None
        )

    def infer(self, frame: np.ndarray) -> np.ndarray:
        if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
            raise ValueError("frame must be a uint8 BGR array with shape (height, width, 3)")
        height, width = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            frame, scalefactor=1 / 255.0, size=self.input_size,
            swapRB=True, crop=False
        )
        self.net.setInput(blob)
        outputs = self.net.forward()
        mask = self._decode_output(outputs, (height, width))
        if self._dilation_kernel is not None:
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._dilation_kernel)
            mask = cv2.dilate(mask, self._dilation_kernel, iterations=1)
        return np.ascontiguousarray(mask, dtype=np.uint8)

    def _decode_output(self, output: np.ndarray, size: tuple[int, int]) -> np.ndarray:
        """Accept common semantic heatmap and detection tensor layouts."""
        height, width = size
        values = np.asarray(output)
        if values.ndim >= 4 and values.shape[1] == 1:
            heatmap = values[0, 0]
            heatmap = cv2.resize(heatmap, (width, height), interpolation=cv2.INTER_LINEAR)
            return np.where(heatmap >= self.confidence_threshold, 255, 0).astype(np.uint8)
        if values.ndim >= 4 and values.shape[1] > 1:
            heatmap = np.max(values[0], axis=0)
            heatmap = cv2.resize(heatmap, (width, height), interpolation=cv2.INTER_LINEAR)
            return np.where(heatmap >= self.confidence_threshold, 255, 0).astype(np.uint8)
        if values.ndim == 3 and values.shape[-1] >= 5:
            mask = np.zeros((height, width), dtype=np.uint8)
            for detection in values.reshape(-1, values.shape[-1]):
                confidence = float(detection[4])
                if confidence < self.confidence_threshold:
                    continue
                cx, cy, box_width, box_height = detection[:4]
                x1 = max(0, int((cx - box_width / 2) * width))
                y1 = max(0, int((cy - box_height / 2) * height))
                x2 = min(width, int((cx + box_width / 2) * width))
                y2 = min(height, int((cy + box_height / 2) * height))
                if x2 > x1 and y2 > y1:
                    mask[y1:y2, x1:x2] = 255
            return mask
        raise ValueError(f"unsupported ONNX output shape: {values.shape}")
