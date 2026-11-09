# Semantic Live Codec

CPU-first hackathon prototype for preserving semantically important regions
under a simulated low-bandwidth budget.

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
