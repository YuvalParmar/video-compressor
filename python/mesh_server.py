"""Small dependency-free HTTP API for a local Wi-Fi/mesh command post."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .emergency import IncidentStore, OfflineTriageEngine, incident_to_dict
from .mesh_crdt import MeshIncidentCRDT


class MeshRequestHandler(BaseHTTPRequestHandler):
    store: IncidentStore
    engine: OfflineTriageEngine
    crdt: MeshIncidentCRDT

    def _write(self, status: int, payload: Any) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write(200, {"ok": True, "service": "offline-command-station"})
        elif self.path == "/incidents":
            self._write(200, [incident_to_dict(item) for item in self.store.list()])
        elif self.path == "/sync":
            self._write(200, {"node_id": self.crdt.node_id, "records": self.crdt.snapshot()})
        else:
            self._write(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/incidents":
            self._write(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            incident = self.store.create(payload, self.engine)
            self.crdt.upsert(incident.incident_id, incident_to_dict(incident))
            self._write(201, incident_to_dict(incident))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._write(400, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        return


def create_mesh_server(host: str = "0.0.0.0", port: int = 8765) -> ThreadingHTTPServer:
    store = IncidentStore()
    engine = OfflineTriageEngine()

    class Handler(MeshRequestHandler):
        pass

    Handler.store = store
    Handler.engine = engine
    Handler.crdt = MeshIncidentCRDT(node_id=f"command-post-{port}")
    return ThreadingHTTPServer((host, port), Handler)
