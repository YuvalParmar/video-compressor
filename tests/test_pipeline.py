import numpy as np
import pytest

from python.metrics import region_mse, summarize


def test_region_mse_requires_matching_shapes():
    with pytest.raises(ValueError):
        region_mse(np.zeros((2, 2, 3), dtype=np.uint8),
                   np.zeros((3, 2, 3), dtype=np.uint8),
                   np.ones((2, 2), dtype=np.uint8))


def test_summary_reports_consumer_metrics():
    summary = summarize(
        [{"semantic_bytes": 100.0, "roi_bytes": 60.0, "baseline_bytes": 300.0, "frame_dropped": 0.0}],
        [np.array([[255, 0], [0, 0]], dtype=np.uint8)],
    )
    assert summary["roi_fraction"] == 0.25
    assert summary["semantic_kbps"] > 0
    assert summary["baseline_kbps"] > summary["semantic_kbps"]
    assert summary["bandwidth_saved_percent"] > 0
    assert summary["roi_bytes_percent"] > 0
