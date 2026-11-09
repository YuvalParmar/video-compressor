# Off-Grid Autonomous Emergency Command Station

CPU-first, offline-first command-post prototype for disaster zones. It
preserves semantically important regions under a simulated low-bandwidth
budget and combines local video, field reports, and vital signs into an
explainable casualty-prioritization queue.

## Operating modes

- **Live feed codec:** side-by-side conventional and semantic video feeds,
  including a 10 kbps mesh-pipe simulation.
- **Offline triage:** local rule-based multimodal prioritization using visual
  cues, field text/transcripts, and optional vitals. It produces P1-P4
  dispatch priorities with reasons and recommended actions. It is not a
  diagnostic tool.
- **Mesh API:** dependency-free local HTTP service for nearby medics,
  gateways, or drone operators on the same Wi-Fi/mesh network.
- **P2P UDP transport:** low-latency datagrams for semantic frames with
  8-byte headers carrying packet type/ROI flags, sequence IDs, packet offsets,
  and packet counts. Incomplete frames expire instead of being retransmitted,
  preventing latency accumulation.
- **Edge multimodal intake:** local injury-photo cues, operator voice-note
  transcripts, and camera-derived rPPG estimates. Voice-note files are accepted
  locally; an offline ASR adapter can populate the transcript before scoring.
  The rPPG and photo detectors are transparent heuristics until a quantized
  ONNX/llama.cpp model is installed.

The native engine targets 60 FPS and reserves 90% of each application-level
frame budget for ROI data. Actual throughput depends on source resolution,
CPU, model latency, and mesh contention; the dashboard reports measured
processing FPS rather than promising a guaranteed transport rate. Incident
records can converge across peers through the last-write-wins CRDT snapshot
endpoint at `GET /sync`.

## Setup on Windows

1. Install Python 3.10+ and Visual Studio Build Tools with C++ support.
2. Install OpenCV and Python dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Place a compatible ONNX model at `models\semantic.onnx`.
4. Build the native extension:

   ```powershell
   .\scripts\build_extension.ps1
   ```

5. Launch the demo:

   ```powershell
   python app.py
   ```

6. In a separate terminal, optionally start the local command-post API:

   ```powershell
   python scripts\run_mesh_server.py
   ```

   The API binds to all local interfaces on port 8765. It has `GET /health`,
   `GET /incidents`, and `POST /incidents` endpoints and stores data in memory
   so the system remains usable without a database or internet connection.

7. For a direct local transport hop, connect the field laptop and command post
   using Windows Mobile Hotspot, Wi-Fi Direct, or an existing local AP. The
   application does not silently reconfigure the operating system network:
   start a receiver with:

   ```powershell
   python scripts\run_udp_receiver.py --host 0.0.0.0 --port 5000
   ```

   A sender can use `UdpFrameSender(("COMMAND_POST_IP", 5000))`. Keep the
   payload below the configured MTU; the packetizer defaults to 1200-byte
   datagrams to avoid IP fragmentation. UDP intentionally trades reliability
   for bounded latency, so the receiver reports dropped packets and frames.

The default simulation is 10 kbps. The standard path encodes the complete
frame at low quality; the semantic path uses a high-quality detected ROI and
pixelated, low-quality background. The UI reports actual encoded bytes rather
than treating a quality setting as a bitrate guarantee.

## Tests

```powershell
python -m pytest
```

The native extension is required for the end-to-end demo. Tests that only
exercise the Python mask and metric contracts do not require model weights.

## Safety and deployment boundaries

The triage rules are deliberately transparent and conservative, but they are
only an operational prioritization aid. Field teams must follow their medical
protocols and human command decisions. For real deployments, add authenticated
mesh transport, encrypted local storage, durable replication, audit logs, and
validated medical-device models before handling real casualty data.
