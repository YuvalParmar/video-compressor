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

    def __post_init__(self) -> None:
        if self.bandwidth_kbps <= 0 or self.target_fps <= 0:
            raise ValueError("bandwidth_kbps and target_fps must be positive")
        if not 50 <= self.roi_bandwidth_percent <= 100:
            raise ValueError("roi_bandwidth_percent must be between 50 and 100")
        if self.inference_width <= 0 or self.inference_height <= 0:
            raise ValueError("inference dimensions must be positive")
        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be between 0 and 1")
        if self.roi_dilation < 0 or self.max_frames <= 0:
            raise ValueError("roi_dilation must be non-negative and max_frames positive")
