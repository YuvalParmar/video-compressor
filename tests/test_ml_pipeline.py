import numpy as np
import pytest

from python.ml_pipeline import SemanticMaskPipeline


def test_detection_output_is_projected_to_mask():
    pipeline = object.__new__(SemanticMaskPipeline)
    pipeline.confidence_threshold = 0.5
    output = np.array([[[0.5, 0.5, 0.4, 0.4, 0.9]]], dtype=np.float32)
    mask = pipeline._decode_output(output, (100, 200))
    assert mask.shape == (100, 200)
    assert mask.dtype == np.uint8
    assert np.count_nonzero(mask) > 0


def test_invalid_frame_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        SemanticMaskPipeline(tmp_path / "missing.onnx")
