# FocusStream Implementation Plan

## Problem and proposed approach

Build a consumer-focused video compression tool that makes low-bandwidth video
useful by preserving high-value regions (people, faces, foreground objects)
while aggressively degrading the background. The first implementation is
CPU-first and safe for a basic Windows laptop with approximately 4 GB RAM and
integrated graphics.

The system uses a file-first frame source, OpenCV DNN loading a lightweight
ONNX detector/segmenter, a Pybind11 C++ extension for zero-copy-friendly frame
processing, and a Gradio single-page demo. The C++ layer produces both a
conventional low-bandwidth baseline and a focus-aware result so the UI can
compare quality under the same simulated network budget.

## Decisions and boundaries

- **UI:** Gradio consumer dashboard — clean, no domain-specific terminology.
- **Inference:** OpenCV DNN with a lightweight ONNX model. The model adapter
  exposes a stable mask interface so the model can be replaced without
  changing the codec.
- **Integration:** Pybind11 in-process extension. Frame/mask contracts are
  explicit so a future shared-memory process boundary can be added.
- **Initial input:** Video files. A source abstraction leaves a clean seam for
  webcam capture later.
- **Runtime target:** CPU-first Windows laptop; optional acceleration may be
  detected but is never required.
- **Bandwidth:** Configurable simulated link, with 10 kbps as the default.
- **Focus-aware policy:** Preserve detected subject pixels at full resolution
  with high JPEG quality; degrade background with block downsampling
  (pixelation) plus optional Gaussian blur and stronger JPEG quantization.
- **Output:** Side-by-side baseline versus focus-aware reconstruction, focus
  map visualization, and metrics such as achieved bitrate, bandwidth savings,
  FPS, focal-area ratio, and dropped-frame count.
- **Architecture separation:** UI, Python orchestration, and C++ engine are
  fully decoupled. Re-skinning the interface for a different audience requires
  changes to `app.py` only.
- **Out of scope:** training a new model, multi-user networking, production
  deployment, authenticated streaming.

## Proposed directory layout

```text
focusstream/
├── app.py
├── README.md
├── pyproject.toml
├── requirements.txt
├── CMakeLists.txt
├── models/
│   └── README.md
├── src/
│   ├── codec_engine.hpp
│   ├── codec_engine.cpp
│   └── bindings.cpp
├── python/
│   ├── __init__.py
│   ├── ml_pipeline.py
│   ├── video_source.py
│   ├── pipeline.py
│   ├── metrics.py
│   ├── config.py
│   └── udp_transport.py
├── tests/
│   ├── test_ml_pipeline.py
│   ├── test_pipeline.py
│   ├── test_udp_transport.py
│   └── cpp/
│       └── codec_engine_tests.cpp
└── scripts/
    ├── build_extension.ps1
    └── run_udp_receiver.py
```

## Implementation phases

### 1. Core engine and contracts
- C++ codec with background pixelation + blur, high-quality ROI, bounded
  JPEG quality search, byte budget enforcement.
- Python config, metrics, pipeline bridge with new consumer settings.
- Pybind11 bindings exposing all settings including blur strength.

### 2. ML mask pipeline
- OpenCV DNN adapter with stable binary-mask output.
- Supports heatmap and detection tensor layouts.
- Morphological close/dilate for mask continuity.

### 3. Consumer UI
- Gradio dashboard with split-screen comparison.
- Network simulation slider (down to 10 kbps).
- Background blur/downscale intensity slider.
- Focal subject sharpness slider.
- Focus map visualization.
- Metrics panel: bandwidth saved, focus vs. standard kbps, FPS, focal area.

### 4. Optional UDP transport
- Packetizer with 8-byte headers (type/ROI flags, sequence, offsets).
- Drop-tolerant assembler with frame timeout eviction.
- Receiver script for local network streaming.

### 5. Validation
- Unit tests for mask decoding, metrics, UDP assembly.
- Integration test on short fixture video at 10 kbps and higher budgets.
- Verify focus-aware ROI quality is better than baseline at the same budget.

## Key algorithm notes

- Background degradation combines INTER_AREA downsampling (pixelation) with
  Gaussian blur for a smooth, low-detail background.
- ROI is copied at full source resolution and encoded at high JPEG quality —
  no downscaling of the subject.
- Feathered mask boundary via Gaussian blur on the mask for smooth compositing.
- Binary quality search avoids redundant JPEG encodes.
- Budget: ROI bytes reserved first, remaining budget spent on background.

## Verification gates

1. Native extension builds on Windows with documented commands.
2. A short video runs end-to-end on CPU without GPU or network.
3. Both output panes produce frames at the same configured bandwidth.
4. At 10 kbps, focus-aware ROI quality is better than baseline.
5. Invalid input, missing model, build failure produce explicit errors.
6. Tests pass for Python orchestration and codec invariants.
