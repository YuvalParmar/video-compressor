from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import gradio as gr

from python.config import PipelineConfig
from python.pipeline import process_video


def _metric(value: Any, suffix: str = "") -> str:
    if isinstance(value, float):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def _metrics_panel(metrics: dict[str, float]) -> str:
    saved = metrics.get("bandwidth_saved_percent", 0)
    return f"""
    <div class="metrics-grid">
      <div class="metric-card highlight">
        <span class="metric-label">BANDWIDTH SAVED</span>
        <strong>{_metric(saved, "%")}</strong>
        <small>vs. standard compression</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">FOCUS STREAM</span>
        <strong>{_metric(metrics.get("semantic_kbps", 0), " kbps")}</strong>
        <small>Actual payload rate</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">STANDARD STREAM</span>
        <strong>{_metric(metrics.get("baseline_kbps", 0), " kbps")}</strong>
        <small>Conventional baseline</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">PROCESSING</span>
        <strong>{_metric(metrics.get("processing_fps", 0), " fps")}</strong>
        <small>Local CPU pipeline</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">FOCAL AREA</span>
        <strong>{_metric(metrics.get("roi_fraction", 0) * 100, "%")}</strong>
        <small>Preserved at full detail</small>
      </div>
      <div class="metric-card">
        <span class="metric-label">FRAMES</span>
        <strong>{_metric(metrics.get("frames", 0))}</strong>
        <small>{_metric(metrics.get("dropped_frames", 0))} dropped</small>
      </div>
    </div>
    <div class="status-note"><span class="status-dot"></span> Focus-aware codec ready · subjects kept crisp, background optimized</div>
    """


def run_demo(
    video: str,
    bandwidth_kbps: int,
    blur_intensity: int,
    focal_sharpness: int,
    max_frames: int,
):
    if not video:
        raise gr.Error("Upload a video clip to begin.")
    # Map the focal sharpness slider (1–100) to roi_quality (50–100)
    # and roi_bandwidth_percent (70–95). Higher sharpness = more bytes
    # reserved for the subject and higher JPEG quality.
    roi_quality = 50 + int(focal_sharpness * 0.5)
    roi_bandwidth_percent = 70 + int(focal_sharpness * 0.25)
    # Map blur intensity (0–50) to background block size (4–30) and blur
    # strength (0–51, kept odd internally by the C++ layer).
    background_block_size = 4 + int(blur_intensity * 0.52)
    background_blur_strength = int(blur_intensity * 1.02)
    config = PipelineConfig(
        bandwidth_kbps=int(bandwidth_kbps),
        roi_quality=roi_quality,
        roi_bandwidth_percent=min(roi_bandwidth_percent, 95),
        background_block_size=background_block_size,
        background_blur_strength=background_blur_strength,
        max_frames=int(max_frames),
    )
    baseline, semantic, mask_viz, metrics = process_video(Path(video), config)
    metrics["target_fps"] = float(config.target_fps)
    return baseline, semantic, mask_viz, _metrics_panel(metrics)


CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root {
  --ink:#f2f5f2; --muted:#8d9b99; --line:#263532; --panel:#111a19; --panel2:#172321;
  --mint:#8df2c4; --amber:#f4c66d; --red:#ff7f72; --blue:#6db4f0;
}
body, .gradio-container {
  background:#09100f !important; color:var(--ink) !important;
  font-family:'Space Grotesk',sans-serif !important;
}
.gradio-container { max-width:1420px !important; padding:24px 42px 54px !important; }

/* Header */
.app-header {
  display:flex; justify-content:space-between; align-items:flex-start;
  border-bottom:1px solid var(--line); padding:14px 0 25px; margin-bottom:28px;
}
.brand { display:flex; gap:14px; align-items:center; }
.brand-mark {
  width:42px; height:42px; border-radius:13px; background:var(--mint);
  color:#09100f; display:grid; place-items:center; font-weight:700; font-size:20px;
}
.brand h1 { font-size:22px; margin:0; letter-spacing:-.03em; }
.brand p { color:var(--muted); margin:4px 0 0; font-size:13px; }
.live {
  color:var(--mint); font:500 11px 'DM Mono',monospace;
  letter-spacing:.1em; margin-top:11px;
}
.status-dot {
  display:inline-block; width:7px; height:7px; border-radius:50%;
  background:var(--mint); box-shadow:0 0 0 4px #8df2c41c; margin-right:8px;
}

/* Hero */
.hero {
  background:linear-gradient(115deg,#182a27 0%,#101918 60%,#111b1a 100%);
  border:1px solid #2b4840; border-radius:20px; padding:32px 36px;
  position:relative; overflow:hidden; margin-bottom:24px;
}
.hero:after {
  content:''; position:absolute; width:290px; height:290px;
  border:1px solid #8df2c41b; border-radius:50%; right:5%; top:-150px;
}
.hero h2 { font-size:38px; line-height:1.04; letter-spacing:-.06em; max-width:620px; margin:10px 0 13px; }
.hero p { color:#b5c3c0; max-width:600px; line-height:1.6; margin:0; }
.hero-tag { color:var(--mint); font:500 11px 'DM Mono',monospace; letter-spacing:.12em; }

/* Section titles */
.section-title { margin:28px 0 14px; }
.section-title h3 { margin:0; font-size:17px; }
.section-title p { color:var(--muted); margin:4px 0 0; font-size:13px; }

/* Panels */
.panel, .block {
  background:var(--panel) !important; border:1px solid var(--line) !important;
  border-radius:16px !important; padding:20px !important;
}
.gradio-container label, .gradio-container .label { color:#b9c5c2 !important; font-size:12px !important; }
.gradio-container input, .gradio-container textarea, .gradio-container select {
  background:#0b1413 !important; border-color:#2a3b38 !important; color:var(--ink) !important;
  border-radius:10px !important;
}
.gradio-container button {
  border-radius:10px !important; border:1px solid #304743 !important;
  background:#1b2b28 !important; color:var(--ink) !important;
}
.gradio-container button.primary {
  background:var(--mint) !important; color:#08110f !important;
  border-color:var(--mint) !important; font-weight:700 !important;
}

/* Metrics */
.metrics-grid {
  display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin-top:12px;
}
.metric-card {
  background:#0c1514; border:1px solid var(--line); border-radius:12px; padding:16px;
}
.metric-card.highlight { border-color:#3e6e5d; background:#0e1a17; }
.metric-card strong { display:block; font-size:20px; margin:9px 0 3px; }
.metric-card small { color:var(--muted); font-size:11px; }
.metric-label { font:500 10px 'DM Mono',monospace; letter-spacing:.13em; color:var(--muted); }
.status-note { color:#aabbb5; font:12px 'DM Mono',monospace; margin-top:15px; }

/* Empty state */
.empty-state { padding:38px 12px; text-align:center; color:var(--muted); }
.empty-state strong, .empty-state span { display:block; }
.empty-state span { font-size:12px; margin-top:7px; }
.empty-icon {
  margin:0 auto 12px; width:30px; height:30px;
  border:1px dashed #557269; border-radius:50%; display:grid; place-items:center;
  color:var(--mint); font-size:16px;
}

/* How-it-works cards */
.how-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-top:22px; }
.how-card {
  background:#101a18; border:1px solid #2b4840; border-radius:15px; padding:22px;
}
.how-card h4 { margin:8px 0 8px; font-size:16px; }
.how-card p { color:var(--muted); font-size:12px; line-height:1.55; margin:0; }
.how-card ul { padding-left:18px; margin:13px 0 0; color:#b8c6c1; font-size:12px; line-height:1.8; }
.how-kicker { color:var(--mint); font:500 10px 'DM Mono',monospace; letter-spacing:.12em; }

@media (max-width:900px) {
  .gradio-container { padding:18px !important; }
  .hero h2 { font-size:30px; }
  .metrics-grid { grid-template-columns:repeat(2,1fr); }
  .how-grid { grid-template-columns:1fr; }
  .app-header { display:block; }
  .live { margin-top:18px; }
}
"""

with gr.Blocks(title="FocusStream / Smart Video Optimizer") as demo:
    gr.HTML("""
    <header class="app-header">
      <div class="brand">
        <div class="brand-mark">F</div>
        <div><h1>FocusStream</h1><p>Smart video optimization for slow connections</p></div>
      </div>
      <div class="live"><span class="status-dot"></span>LOCAL ENGINE · READY</div>
    </header>
    <section class="hero">
      <span class="hero-tag">CONSUMER / 01</span>
      <h2>Keep your subject crisp.<br>Let the background breathe.</h2>
      <p>FocusStream uses a focus-aware codec that preserves the people and objects you care about at full resolution while aggressively optimizing everything else — perfect for weak Wi-Fi, slow cell data, or video calls on the move.</p>
    </section>
    """)
    with gr.Tabs():
        with gr.Tab("Video Optimizer", id="optimizer"):
            gr.HTML(
                '<div class="section-title"><h3>Focus-aware video compression</h3>'
                '<p>Upload a clip, simulate a slow connection, and compare standard compression against our focus-aware codec side by side.</p></div>'
            )
            with gr.Row():
                with gr.Column(scale=5, elem_classes="panel"):
                    video = gr.Video(label="YOUR VIDEO", sources=["upload"], height=260)
                with gr.Column(scale=3, elem_classes="panel"):
                    bandwidth = gr.Slider(
                        1, 2000, value=10, step=1,
                        label="Simulated network speed (kbps)",
                        info="Throttle down to 10 kbps to see extreme conditions",
                    )
                    blur_intensity = gr.Slider(
                        0, 50, value=25, step=1,
                        label="Background blur / downscale intensity",
                        info="Higher = more aggressive background pixelation",
                    )
                    focal_sharpness = gr.Slider(
                        1, 100, value=75, step=1,
                        label="Focal subject sharpness",
                        info="Higher = more bytes reserved for the subject",
                    )
                    max_frames = gr.Slider(
                        1, 300, value=90, step=1,
                        label="Frames to process",
                    )
                    run = gr.Button("Optimize video  →", variant="primary")
            with gr.Row():
                baseline = gr.Image(label="STANDARD COMPRESSION", height=280)
                semantic = gr.Image(label="FOCUS-AWARE CODEC · SUBJECT PRESERVED", height=280)
            with gr.Row():
                mask_viz = gr.Image(label="FOCUS MAP · detected subject regions", height=200)
            metrics_html = gr.HTML(
                '<div class="empty-state"><div class="empty-icon">+</div>'
                '<strong>Run the optimizer to see results</strong>'
                '<span>Upload a video and click Optimize to compare compression strategies.</span></div>'
            )
            run.click(
                run_demo,
                [video, bandwidth, blur_intensity, focal_sharpness, max_frames],
                [baseline, semantic, mask_viz, metrics_html],
            )
        with gr.Tab("How it works", id="how"):
            gr.HTML("""
            <div class="section-title">
              <h3>How FocusStream works</h3>
              <p>The codec engine, ML detection, and interface are fully decoupled — the core compression logic never depends on the UI.</p>
            </div>
            <div class="how-grid">
              <article class="how-card">
                <span class="how-kicker">01 / DETECT</span>
                <h4>Find the subject</h4>
                <p>A lightweight on-device model identifies the important regions — people, faces, foreground objects — in each frame.</p>
                <ul>
                  <li>Runs entirely on your CPU</li>
                  <li>No cloud, no uploads, no tracking</li>
                  <li>Swap the model without touching the codec</li>
                </ul>
              </article>
              <article class="how-card">
                <span class="how-kicker">02 / COMPRESS</span>
                <h4>Split and encode</h4>
                <p>The native C++ engine encodes the focal region at high quality while downscaling and blurring the background to fit your bandwidth budget.</p>
                <ul>
                  <li>Subject stays at full resolution</li>
                  <li>Background is pixelated and blurred</li>
                  <li>Binary quality search hits the byte target</li>
                </ul>
              </article>
              <article class="how-card">
                <span class="how-kicker">03 / DELIVER</span>
                <h4>Reassemble and display</h4>
                <p>The receiver composites the crisp subject over the degraded background, producing a frame that looks good even at 10 kbps.</p>
                <ul>
                  <li>Feathered mask for smooth transitions</li>
                  <li>Drop-tolerant UDP transport option</li>
                  <li>Reports real bandwidth, not promises</li>
                </ul>
              </article>
            </div>
            """)
    gr.HTML(
        '<footer style="text-align:center;margin-top:35px;color:var(--muted);'
        'font:500 10px \'DM Mono\',monospace;letter-spacing:.13em">'
        'FOCUSSTREAM RUNS ENTIRELY ON YOUR DEVICE · NO CLOUD · NO TRACKING</footer>'
    )


if __name__ == "__main__":
    demo.launch(css=CSS)
