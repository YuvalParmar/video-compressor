# FocusStream — Smart Video Optimizer

CPU-first, offline-first video compression tool for everyday consumers dealing
with slow internet. It keeps the parts of a video you care about — people,
faces, foreground objects — crisp and detailed while aggressively optimizing
the background to fit weak Wi-Fi, cell data, or congested connections.

## What it does

- **Split-screen comparison:** See standard compression next to our focus-aware
  codec so you can judge the difference at the same simulated bandwidth.
- **Network simulation:** Throttle down to 10 kbps to see how each approach
  handles extreme conditions — bad hotel Wi-Fi, a train commute, a weak cellular
  signal.
- **Background control:** Adjust how aggressively the background is downscaled
  and blurred, from subtle to heavily pixelated.
- **Subject sharpness:** Control how many bytes are reserved for the focal
  subject — more sharpness means higher quality on the person or object that
  matters.
- **P2P UDP transport (optional):** Low-latency datagram transport for
  streaming focus-aware frames to another device on the same local network.

The native C++ engine targets 60 FPS and reserves 90% of each frame's byte
budget for subject (ROI) data. The dashboard reports measured throughput and
bandwidth savings rather than promising a guaranteed rate.

## Architecture

The system is intentionally layered so the UI can be swapped without touching
the core engine:

- **UI layer** (`app.py`): Gradio consumer dashboard. This is the only file
  that needs to change if the interface is re-skinned for a different audience.
- **Python orchestration** (`python/`): Video source, ML mask pipeline, codec
  bridge, metrics, config, UDP transport. No UI dependencies.
- **Native C++ engine** (`src/`): ROI-aware JPEG codec with background
  pixelation + blur, bounded quality search, and Pybind11 bindings. No UI or
  Python orchestration dependencies.

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

5. Launch the app:

   ```powershell
   python app.py
   ```

6. For direct local streaming to another device, start a receiver:

   ```powershell
   python scripts\run_udp_receiver.py --host 0.0.0.0 --port 5000
   ```

   A sender can use `UdpFrameSender(("RECEIVER_IP", 5000))`. Keep the payload
   below the configured MTU; the packetizer defaults to 1200-byte datagrams.

The default simulation is 10 kbps. The standard path encodes the complete
frame at low quality; the focus-aware path uses a high-quality detected subject
region and pixelated, blurred, low-quality background. The UI reports actual
encoded bytes rather than treating a quality setting as a bitrate guarantee.

## Performance notes

The native codec releases the Python GIL during frame processing, uses a
bounded JPEG-quality binary search for each byte budget, and avoids Huffman
optimization because its CPU cost is not worthwhile for low-latency streams.
The mask pipeline reuses its morphology kernel across frames. UDP assembly
rejects inconsistent or duplicate packets and evicts incomplete frames after
the configured timeout, keeping latency bounded.

## Tests

```powershell
python -m pytest
```

The native extension is required for the end-to-end demo. Tests that only
exercise the Python mask and metric contracts do not require model weights.

## Privacy

FocusStream runs entirely on your device. No video, frames, or telemetry leave
your machine. The ML model runs locally via OpenCV DNN on CPU.
