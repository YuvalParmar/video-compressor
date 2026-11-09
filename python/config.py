from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineConfig:
    bandwidth_kbps: int = 10
    target_fps: int = 60
    roi_bandwidth_percent: int = 90
    inference_width: int = 320
    inference_height: int = 320
    confidence_threshold: float = 0.35
    roi_dilation: int = 7
    max_frames: int = 180
    display_fps: float = 15.0
    model_path: str = "models/semantic.onnx"
