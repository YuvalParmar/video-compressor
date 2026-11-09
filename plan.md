# Semantic Live Codec Implementation Plan

## Problem and proposed approach

Build a hackathon-ready semantic video compressor that makes a low-bandwidth feed useful by preserving high-value regions while aggressively degrading the background. The first implementation will be CPU-first and safe for a basic Windows laptop with approximately 4 GB RAM and integrated graphics.

The system will use a file-first frame source, OpenCV DNN loading a lightweight ONNX detector/segmenter, a Pybind11 C++ extension for zero-copy-friendly frame processing, and a Gradio single-page demo. The C++ layer will produce both a conventional low-bandwidth baseline and a semantic result so the UI can compare quality under the same simulated network budget.

## Decisions and boundaries

- **UI:** Gradio.
- **Inference:** OpenCV DNN with a lightweight ONNX model. The model adapter will expose a stable mask interface so the model can be replaced without changing the codec.
- **Integration:** Pybind11 in-process extension. This avoids serialization and process scheduling overhead on a low-memory laptop; the design will keep frame/mask contracts explicit so a future shared-memory process boundary can be added.
- **Initial input:** Video files. A source abstraction will leave a clean seam for webcam capture later without making webcam support a required milestone.
- **Runtime target:** CPU-first Windows laptop; optional CUDA/OpenVINO acceleration may be detected but must never be required.
- **Bandwidth:** Configurable simulated link, with 10 kbps as the default challenge setting. The simulator will use encoded byte counts and a token/budget model rather than merely changing a quality slider.
- **Semantic policy:** Preserve detected high-value pixels and a configurable safety margin; degrade non-semantic pixels using downsampling/pixelation and stronger JPEG quantization.
- **Output:** Side-by-side baseline versus semantic reconstruction, plus metrics such as achieved bitrate, FPS, latency, preserved-zone ratio, and dropped-frame count.
- **Out of scope for the first implementation:** training a new model, multi-user networking, production deployment, authenticated streaming, and a separate Python/C++ process topology.

## Proposed directory layout

```text
semantic-live-codec/
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
│   └── config.py
├── tests/
│   ├── test_ml_pipeline.py
│   ├── test_pipeline.py
│   └── cpp/
│       └── codec_engine_tests.cpp
└── scripts/
    ├── build_extension.ps1
    └── download_model.ps1
```

## Implementation phases and todos

### 1. Establish project contracts and build configuration

- Define Python configuration objects for frame size, input FPS cap, mask thresholds, ROI margin, JPEG quality levels, background block size, bitrate budget, queue limits, and metric sampling.
- Define the C++ API around `cv::Mat`/NumPy-compatible buffers: frame dimensions, BGR/RGB convention, binary or confidence mask, codec settings, encoded packet metadata, and decoded output.
- Add `pyproject.toml`, requirements, CMake configuration, and a reproducible Windows build script for the Pybind11 extension.
- Keep model files out of source control and document the expected ONNX path and checksum in `models/README.md`.

### 2. Implement the OpenCV DNN semantic mask pipeline

- Load the configured ONNX model once and reuse the `cv::dnn::Net`; select CPU backend/target by default and expose optional acceleration selection.
- Preprocess frames with a bounded inference resolution and letterbox metadata, preserving the transform needed to map detections/masks back to source coordinates.
- Decode model outputs into a confidence map or instance boxes, threshold them, merge classes considered high value, and apply morphological close/dilate operations for continuity and a safety margin.
- Avoid per-frame allocations where possible by reusing blobs, masks, and scratch buffers.
- Expose a synchronous `infer(frame)` method and a stream-friendly iterator/loop with explicit failure reporting for unreadable models or frames.

### 3. Implement the C++ semantic codec engine

- Add a baseline encoder that resizes/encodes the full frame at a constrained quality and records exact encoded bytes.
- Add semantic encoding that:
  - validates frame and mask dimensions;
  - encodes the ROI/high-value layer at higher quality;
  - reduces the background resolution with block pooling or controlled Gaussian/downsample/upsample;
  - encodes the degraded background at low quality;
  - composites the ROI over the reconstructed background with a feathered mask boundary;
  - enforces the total byte budget by reducing background quality/resolution first, then ROI quality only as a last resort.
- Add a deterministic network simulator with a byte budget per frame, packet/frame sequence metadata, queue limits, and explicit drop behavior when the budget is exceeded.
- Add decode/reassembly paths that tolerate missing background or ROI packets using the previous valid frame and report concealment rather than silently claiming success.
- Return encoded and decoded frames plus metrics needed by the UI and tests.

### 4. Bind the C++ engine through Pybind11

- Expose typed settings, engine construction, mask/frame processing, and result metadata without copying more than necessary.
- Accept NumPy arrays with validation for contiguous layout, dtype, channel count, and dimensions; return NumPy arrays or encoded byte buffers with clear ownership rules.
- Release the Python GIL during CPU-heavy C++ processing so the UI/inference loop remains responsive.
- Convert C++ exceptions into actionable Python exceptions and avoid broad catches or success-shaped fallbacks.

### 5. Build the orchestration pipeline

- Implement file decoding with OpenCV, bounded frame queues, FPS pacing, and an optional frame-skip policy for slow machines.
- Connect inference, codec processing, and metric collection while keeping source FPS, processing FPS, and display FPS distinct.
- Add cancellation and cleanup for repeated Gradio runs so capture handles, native objects, and worker threads are released.
- Provide a pure-Python fallback codec path only for diagnostics/tests if the native extension is unavailable; production/demo errors should clearly state how to build the extension.

### 6. Build the Gradio demo

- Add video upload/input controls, bandwidth slider with a 10 kbps default, target FPS, inference threshold, ROI margin, and background degradation controls.
- Render baseline and semantic outputs side by side, with a mask/ROI visualization option.
- Display achieved bitrate, encoded bytes, effective FPS, processing latency, dropped frames, and percentage of bytes allocated to semantic regions.
- Use bounded previews and cached model initialization to avoid exhausting 4 GB RAM.
- Make CPU fallback and missing-model/build errors visible in the UI with actionable messages.

### 7. Validate correctness and constrained-device behavior

- Unit-test mask post-processing, coordinate transforms, empty-mask behavior, dimension validation, budget enforcement, packet loss/concealment, and deterministic metric calculations.
- Test C++/Python buffer ownership and repeated calls for leaks or stale data.
- Run an integration test on a short fixture video comparing baseline and semantic outputs at 10 kbps and at higher budgets.
- Verify the semantic path preserves substantially more quality in masked zones than in the background using objective ROI/background metrics; do not rely only on visual inspection.
- Add a smoke test for a 4 GB/CPU-only configuration: bounded memory, no required GPU, graceful frame skipping, and clear startup errors.
- Document Windows setup, Visual C++/CMake prerequisites, model acquisition, build commands, demo launch, troubleshooting, and known limitations.

## Key algorithm and performance considerations

- Use a small inference resolution and configurable inference cadence; reuse the last mask between inference frames when CPU pressure requires it.
- Prefer `uint8` masks and contiguous BGR buffers at the Python/C++ boundary.
- Use a ring/bounded queue to prevent latency from growing without limit.
- Budget bytes after encoding, because JPEG size varies with image content; reserve a minimum ROI budget and spend remaining bytes on background quality.
- Keep the baseline and semantic paths synchronized to the same source frame and simulated budget.
- Treat 10 kbps as a simulated application-level budget for the demo, not as a claim about a real transport protocol.
- Keep the model adapter independent of codec policy so future face/text/injury/object-specific priorities can be added without rewriting transport code.

## Verification gates

1. Native extension builds on Windows with the documented commands.
2. A short video runs end-to-end on CPU without a GPU or network service.
3. Both output panes produce frames and metrics at the same configured bandwidth.
4. At 10 kbps, semantic ROI metrics are better than the baseline while background degradation is measurable.
5. Invalid input, missing model, native build failure, and empty detections produce explicit user-facing errors.
6. Tests pass for Python orchestration and C++ codec invariants, and memory remains bounded over a multi-minute run.

## Risks and mitigations

- **Model mismatch or unavailable weights:** define a versioned ONNX contract, validate output shapes, and document a tested lightweight model artifact.
- **4 GB RAM pressure:** cap resolution, queue depth, retained frames, and Gradio preview size; process incrementally rather than collecting full videos in memory.
- **Pybind11 build friction on Windows:** provide CMake and PowerShell build scripts plus a diagnostic import command; keep the Python contract testable independently.
- **10 kbps starving all content:** reserve ROI bytes, use frame pacing/drop policy, and expose the actual achieved bitrate rather than hiding budget misses.
- **Mask instability:** use temporal reuse and morphological smoothing, while reporting the mask age/latency so stale semantics are visible.
- **Perceptual claims overpromised:** report measurable ROI/background metrics and label the demo as a simulation.
