"""Last-write-wins CRDT for incident queue convergence across mesh peers."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any


@dataclass
class MeshIncidentCRDT:
    node_id: str
    records: dict[str, dict[str, Any]] = field(default_factory=dict)
    clocks: dict[str, tuple[float, str]] = field(default_factory=dict)

    def upsert(self, incident_id: str, payload: dict[str, Any]) -> None:
        stamp = (time(), self.node_id)
        previous = self.clocks.get(incident_id)
        if previous is None or stamp >= previous:
            self.records[incident_id] = dict(payload)
            self.clocks[incident_id] = stamp

    def merge(self, peer: "MeshIncidentCRDT") -> None:
        for incident_id, payload in peer.records.items():
            stamp = peer.clocks[incident_id]
            if stamp >= self.clocks.get(incident_id, (0.0, "")):
                self.records[incident_id] = dict(payload)
                self.clocks[incident_id] = stamp

    def merge_snapshot(
        self, records: dict[str, dict[str, Any]], clocks: dict[str, tuple[float, str]]
    ) -> None:
        for incident_id, payload in records.items():
            stamp = clocks.get(incident_id, (0.0, "peer"))
            if stamp >= self.clocks.get(incident_id, (0.0, "")):
                self.records[incident_id] = dict(payload)
                self.clocks[incident_id] = stamp

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {key: dict(value) for key, value in self.records.items()}
