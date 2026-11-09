import numpy as np

from python.edge_inference import OfflineMultimodalTriage
from python.mesh_crdt import MeshIncidentCRDT


def test_rppg_returns_local_signal_metrics():
    frames = [
        np.full((8, 8, 3), 100 + (index % 4), dtype=np.uint8)
        for index in range(60)
    ]
    result = OfflineMultimodalTriage.estimate_rppg(frames, 30)
    assert set(result) == {"heart_rate", "respiratory_rate", "signal_quality"}


def test_mesh_crdt_merge_converges():
    left = MeshIncidentCRDT("left")
    right = MeshIncidentCRDT("right")
    left.upsert("case-1", {"status": "OPEN"})
    right.merge(left)
    assert right.snapshot()["case-1"]["status"] == "OPEN"
