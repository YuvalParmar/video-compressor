from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import gradio as gr

from python.config import PipelineConfig
from python.pipeline import process_video
from python.samples import SAMPLES_DIR, ensure_samples


def _metric(value: Any, suffix: str = "") -> str:
    if isinstance(value, float):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def _metrics_panel(metrics: dict[str, float]) -> str:
    saved = metrics.get("bandwidth_saved_percent", 0)
    return f"""
    <div class="metrics-wrap">
      <div class="metric-hero">
        <span class="metric-eyebrow">BANDWIDTH SAVED</span>
        <span class="metric-hero-value">{_metric(saved, "%")}</span>
        <span class="metric-hero-sub">vs. standard compression</span>
      </div>
      <div class="metrics-row">
        <div class="metric-cell">
          <span class="metric-label">FOCUS STREAM</span>
          <strong>{_metric(metrics.get("semantic_kbps", 0), " kbps")}</strong>
          <small>Actual payload rate</small>
        </div>
        <div class="metric-cell">
          <span class="metric-label">STANDARD STREAM</span>
          <strong>{_metric(metrics.get("baseline_kbps", 0), " kbps")}</strong>
          <small>Conventional baseline</small>
        </div>
        <div class="metric-cell">
          <span class="metric-label">PROCESSING</span>
          <strong>{_metric(metrics.get("processing_fps", 0), " fps")}</strong>
          <small>Local CPU pipeline</small>
        </div>
        <div class="metric-cell">
          <span class="metric-label">FOCAL AREA</span>
          <strong>{_metric(metrics.get("roi_fraction", 0) * 100, "%")}</strong>
          <small>Preserved at full detail</small>
        </div>
        <div class="metric-cell">
          <span class="metric-label">FRAMES</span>
          <strong>{_metric(metrics.get("frames", 0))}</strong>
          <small>{_metric(metrics.get("dropped_frames", 0))} dropped</small>
        </div>
      </div>
      <div class="status-bar"><span class="status-dot"></span>Focus-aware codec ready &middot; subjects kept crisp, background optimized</div>
    </div>
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
    roi_quality = 50 + int(focal_sharpness * 0.5)
    roi_bandwidth_percent = 70 + int(focal_sharpness * 0.25)
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


PRESETS = {
    "portrait_call": {
        "label": "Portrait call",
        "desc": "A face-centric video call scene.",
        "scenario": "Video calls over weak Wi-Fi",
        "bandwidth": 50,
        "blur": 20,
        "sharpness": 85,
        "frames": 90,
    },
    "outdoor_action": {
        "label": "Outdoor action",
        "desc": "Multiple moving subjects against a busy background.",
        "scenario": "Mobile streaming on cellular data",
        "bandwidth": 200,
        "blur": 35,
        "sharpness": 70,
        "frames": 90,
    },
    "extreme_low": {
        "label": "Extreme low-light",
        "desc": "Minimal detail, low-bandwidth stress test.",
        "scenario": "Hotel Wi-Fi or congested hotspots",
        "bandwidth": 10,
        "blur": 30,
        "sharpness": 60,
        "frames": 45,
    },
    "balanced": {
        "label": "Balanced scene",
        "desc": "Several subjects with moderate background detail.",
        "scenario": "Standard home internet",
        "bandwidth": 500,
        "blur": 15,
        "sharpness": 80,
        "frames": 120,
    },
}


def _load_preset(preset_key: str):
    """Return the sample video path and slider values for a preset key."""
    preset = PRESETS.get(preset_key)
    if preset is None:
        raise gr.Error("Unknown preset selected.")
    video_path = SAMPLES_DIR / f"{preset_key}.mp4"
    if not video_path.is_file():
        ensure_samples()
    if not video_path.is_file():
        raise gr.Error(f"Sample video could not be generated: {video_path}")
    return (
        str(video_path),
        preset["bandwidth"],
        preset["blur"],
        preset["sharpness"],
        preset["frames"],
    )


CSS = """
:root {
  --bg: #fbfbfd;
  --surface: #ffffff;
  --surface-2: #f5f5f7;
  --ink: #1d1d1f;
  --ink-2: #424245;
  --muted: #86868b;
  --line: #d2d2d7;
  --line-soft: #e8e8ed;
  --accent: #0071e3;
  --accent-hover: #0077ed;
  --accent-soft: #e8f1fd;
  --green: #34c759;
  --green-soft: #e3f9e9;
  --orange: #ff9500;
  --red: #ff3b30;
  --radius: 18px;
  --radius-sm: 12px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04);
  --shadow-lg: 0 12px 40px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.04);
}

* { box-sizing: border-box; }

body, .gradio-container {
  background: var(--bg) !important;
  color: var(--ink) !important;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.gradio-container {
  max-width: 1280px !important;
  padding: 0 32px 80px !important;
  margin: 0 auto !important;
}

/* ---------- Nav ---------- */
.fs-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(251,251,253,0.72);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid var(--line-soft);
  padding: 14px 0;
  margin: 0 -32px 0;
  padding-left: 32px;
  padding-right: 32px;
}
.fs-nav-inner {
  display: flex; align-items: center; justify-content: space-between;
  max-width: 1280px; margin: 0 auto;
}
.fs-nav-brand { display: flex; align-items: center; gap: 10px; }
.fs-nav-mark {
  width: 30px; height: 30px; border-radius: 8px;
  background: var(--ink); color: #fff;
  display: grid; place-items: center;
  font-weight: 700; font-size: 15px;
  transition: transform 0.3s cubic-bezier(0.2,0.8,0.2,1);
}
.fs-nav-brand:hover .fs-nav-mark { transform: scale(1.08) rotate(-3deg); }
.fs-nav-name { font-size: 17px; font-weight: 600; letter-spacing: -0.02em; color: var(--ink) !important; }
.fs-nav-links { display: flex; gap: 28px; align-items: center; }
.fs-nav-links a {
  color: var(--ink-2) !important; font-size: 13px; font-weight: 400;
  text-decoration: none; transition: color 0.2s;
}
.fs-nav-links a:hover { color: var(--accent); }
.fs-nav-pill {
  background: var(--ink); color: #fff;
  padding: 7px 16px; border-radius: 980px;
  font-size: 12px; font-weight: 500;
  display: inline-flex; align-items: center; gap: 7px;
  transition: opacity 0.2s, transform 0.2s;
}
.fs-nav-pill:hover { opacity: 0.85; transform: translateY(-1px); }
.fs-nav-pill .dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--green); box-shadow: 0 0 0 3px rgba(52,199,89,0.25);
}

/* ---------- Hero ---------- */
.fs-hero {
  text-align: center;
  padding: 80px 0 56px;
}
.fs-hero-eyebrow {
  color: var(--accent);
  font-size: 13px; font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: 18px;
  display: inline-block;
}
.fs-hero h1 {
  font-size: clamp(40px, 6vw, 72px);
  line-height: 1.05;
  letter-spacing: -0.045em;
  font-weight: 700;
  margin: 0 auto 20px;
  max-width: 820px;
  color: var(--ink) !important;
}
.fs-hero-sub {
  font-size: clamp(17px, 2vw, 21px);
  line-height: 1.5;
  color: var(--ink-2);
  max-width: 680px;
  margin: 0 auto 36px;
  font-weight: 400;
}
.fs-hero-cta { display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; }
.fs-btn-primary {
  background: var(--accent); color: #fff;
  padding: 12px 28px; border-radius: 980px;
  font-size: 15px; font-weight: 500;
  border: none; cursor: pointer;
  transition: background 0.2s, transform 0.15s;
}
.fs-btn-primary:hover { background: var(--accent-hover); transform: translateY(-1px); }
.fs-btn-ghost {
  background: transparent; color: var(--accent);
  padding: 12px 24px; border-radius: 980px;
  font-size: 15px; font-weight: 500;
  border: 1px solid var(--accent); cursor: pointer;
  transition: background 0.2s;
}
.fs-btn-ghost:hover { background: var(--accent-soft); }

/* ---------- Feature strip ---------- */
.fs-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--line-soft);
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 72px;
}
.fs-strip-cell {
  background: var(--surface);
  padding: 36px 32px;
  transition: background 0.25s;
}
.fs-strip-cell:hover { background: var(--surface-2); }
.fs-strip-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: grid; place-items: center;
  font-size: 18px; margin-bottom: 16px;
}
.fs-strip-cell h3 { font-size: 18px; font-weight: 600; margin: 0 0 8px; letter-spacing: -0.01em; color: var(--ink) !important; }
.fs-strip-cell p { font-size: 14px; line-height: 1.55; color: var(--ink-2) !important; margin: 0; }

/* ---------- Section heading ---------- */
.fs-section-head {
  text-align: center;
  margin-bottom: 40px;
}
.fs-section-head h2 {
  font-size: clamp(30px, 4vw, 48px);
  letter-spacing: -0.035em;
  font-weight: 700;
  margin: 0 0 12px;
  color: var(--ink) !important;
}
.fs-section-head p {
  font-size: 17px; color: var(--ink-2) !important; max-width: 560px; margin: 0 auto;
  line-height: 1.5;
}

/* ---------- Cards / panels ---------- */
.fs-card {
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.3s, transform 0.3s;
}
.fs-card:hover { box-shadow: var(--shadow-md); }
.block, .gradio-container .block {
  background: var(--surface) !important;
  border: 1px solid var(--line-soft) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow-sm) !important;
}
.gradio-container .form {
  background: var(--surface-2) !important;
  border: 1px solid var(--line-soft) !important;
  border-radius: var(--radius) !important;
  overflow: hidden !important;
}

/* ---------- Form controls ---------- */
.gradio-container label, .gradio-container .label-wrap > label {
  color: var(--ink-2) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  opacity: 1 !important;
}
.gradio-container .block label[data-testid="block-label"],
.gradio-container .block label[data-testid="block-label"] span,
.gradio-container .block .info,
.gradio-container .block .wrap span,
.gradio-container [data-testid="upload-text"],
.gradio-container [data-testid="upload-text"] * {
  color: var(--ink-2) !important;
  opacity: 1 !important;
}
.gradio-container label[data-testid="block-label"] {
  background: var(--surface) !important;
  border: 1px solid var(--line-soft) !important;
  border-radius: 8px !important;
}
.gradio-container input[type="number"] {
  color: var(--ink) !important;
  font-weight: 600 !important;
}
.gradio-container input, .gradio-container textarea, .gradio-container select {
  background: var(--surface-2) !important;
  border: 1px solid var(--line-soft) !important;
  color: var(--ink) !important;
  border-radius: var(--radius-sm) !important;
  font-family: 'Inter', sans-serif !important;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.gradio-container input:focus, .gradio-container textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-soft) !important;
  outline: none !important;
}

/* Slider styling */
.gradio-container input[type="range"] {
  -webkit-appearance: none; appearance: none;
  height: 4px; border-radius: 980px;
  background: var(--line) !important;
  border: none !important;
}
.gradio-container input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 22px; height: 22px; border-radius: 50%;
  background: #fff; border: 1px solid var(--line);
  box-shadow: var(--shadow-md);
  cursor: pointer;
  transition: transform 0.15s, border-color 0.15s;
}
.gradio-container input[type="range"]::-webkit-slider-thumb:hover {
  transform: scale(1.12); border-color: var(--accent);
}
.gradio-container input[type="range"]::-moz-range-thumb {
  width: 22px; height: 22px; border-radius: 50%;
  background: #fff; border: 1px solid var(--line);
  box-shadow: var(--shadow-md); cursor: pointer;
}

/* Buttons */
.gradio-container button {
  border-radius: 980px !important;
  border: 1px solid var(--line) !important;
  background: var(--surface) !important;
  color: var(--ink) !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 500 !important;
  font-size: 15px !important;
  padding: 10px 22px !important;
  transition: all 0.2s !important;
}
.gradio-container button:hover {
  background: var(--surface-2) !important;
}
.gradio-container button.primary, .gradio-container button.btn-primary {
  background: var(--accent) !important;
  color: #fff !important;
  border-color: var(--accent) !important;
  font-weight: 600 !important;
  padding: 12px 32px !important;
  box-shadow: 0 4px 14px rgba(0,113,227,0.25) !important;
}
.gradio-container button.primary:hover {
  background: var(--accent-hover) !important;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0,113,227,0.3) !important;
}

/* Tabs */
.gradio-container .tabs > .tab-nav {
  justify-content: center;
  border-bottom: 1px solid var(--line-soft);
  gap: 8px;
  padding-bottom: 0;
}
.gradio-container .tab-nav button {
  border: none !important;
  background: transparent !important;
  border-radius: 980px !important;
  padding: 9px 20px !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  color: var(--muted) !important;
  transition: all 0.2s !important;
}
.gradio-container .tab-nav button:hover {
  background: var(--surface-2) !important;
  color: var(--ink) !important;
}
.gradio-container .tab-nav button.selected {
  background: var(--ink) !important;
  color: #fff !important;
  box-shadow: var(--shadow-sm) !important;
}

/* ---------- Upload ---------- */
.gradio-container .gr-video, .gradio-container .gr-image {
  border-radius: var(--radius) !important;
  border: 1px solid var(--line-soft) !important;
}
.gradio-container .gradio-video, .gradio-container .gradio-image {
  border-radius: var(--radius) !important;
}

/* ---------- Metrics ---------- */
.metrics-wrap {
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius);
  padding: 36px;
  box-shadow: var(--shadow-sm);
  animation: fsFadeIn 0.5s cubic-bezier(0.2,0.8,0.2,1);
}
@keyframes fsFadeIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
.metric-hero {
  text-align: center;
  padding-bottom: 32px;
  margin-bottom: 32px;
  border-bottom: 1px solid var(--line-soft);
}
.metric-eyebrow {
  display: block;
  font: 500 11px 'JetBrains Mono', monospace;
  letter-spacing: 0.12em;
  color: var(--ink-2) !important;
  margin-bottom: 10px;
}
.metric-hero-value {
  display: block;
  font-size: 64px;
  font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--accent) !important;
  line-height: 1;
  margin-bottom: 10px;
}
.metric-hero-sub {
  display: block;
  font-size: 14px;
  color: var(--ink-2) !important;
}
.metrics-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1px;
  background: var(--line-soft);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.metric-cell {
  background: var(--surface);
  padding: 24px 18px;
  text-align: center;
  transition: background 0.2s;
}
.metric-cell:hover { background: var(--surface-2); }
.metric-label {
  display: block;
  font: 500 10px 'JetBrains Mono', monospace;
  letter-spacing: 0.1em;
  color: var(--ink-2) !important;
  margin-bottom: 12px;
}
.metric-cell strong {
  display: block;
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin-bottom: 6px;
}
.metric-cell small {
  display: block;
  font-size: 11px;
  color: var(--ink-2) !important;
}
.status-bar {
  display: flex; align-items: center; justify-content: center;
  margin-top: 28px;
  font-size: 13px;
  color: var(--ink-2);
  gap: 8px;
}
.status-dot {
  display: inline-block;
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 4px rgba(52,199,89,0.18);
  animation: fsPulse 2s ease-in-out infinite;
}
@keyframes fsPulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(52,199,89,0.18); }
  50% { box-shadow: 0 0 0 7px rgba(52,199,89,0.08); }
}

/* ---------- Empty state ---------- */
.empty-state {
  padding: 64px 24px;
  text-align: center;
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}
.empty-state strong { display: block; font-size: 17px; font-weight: 600; margin-bottom: 8px; color: var(--ink) !important; }
.empty-state span { display: block; font-size: 14px; color: var(--ink-2) !important; }
.empty-icon {
  margin: 0 auto 20px;
  width: 56px; height: 56px;
  border: 2px solid var(--line);
  border-radius: 50%;
  display: grid; place-items: center;
  color: var(--accent); font-size: 24px;
  transition: border-color 0.3s, transform 0.3s;
}
.empty-state:hover .empty-icon { border-color: var(--accent); transform: scale(1.05); }

/* ---------- How it works ---------- */
.how-section { padding: 16px 0 0; }
.how-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-top: 40px;
}
.how-card {
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius);
  padding: 40px 32px;
  box-shadow: var(--shadow-sm);
  transition: transform 0.35s cubic-bezier(0.2,0.8,0.2,1), box-shadow 0.35s;
}
.how-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}
.how-step {
  width: 36px; height: 36px; border-radius: 10px;
  background: var(--accent-soft); color: var(--accent);
  display: grid; place-items: center;
  font: 600 13px 'JetBrains Mono', monospace;
  margin-bottom: 20px;
  transition: transform 0.3s;
}
.how-card:hover .how-step { transform: scale(1.1) rotate(-5deg); }
.how-card h4 {
  margin: 0 0 12px;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.how-card p {
  color: var(--ink-2) !important;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}
.how-card ul {
  list-style: none;
  padding: 0;
  margin: 20px 0 0;
}
.how-card li {
  position: relative;
  padding-left: 22px;
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--ink-2) !important;
  line-height: 1.5;
}
.how-card li::before {
  content: '';
  position: absolute;
  left: 0; top: 7px;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--green);
}

/* ---------- Footer ---------- */
.fs-footer {
  text-align: center;
  padding: 56px 0 0;
  margin-top: 72px;
  border-top: 1px solid var(--line-soft);
}
.fs-footer-mark {
  width: 28px; height: 28px; border-radius: 8px;
  background: var(--ink); color: #fff;
  display: inline-grid; place-items: center;
  font-weight: 700; font-size: 14px;
  margin-bottom: 16px;
}
.fs-footer p {
  font-size: 13px;
  color: var(--ink-2) !important;
  margin: 0 0 8px;
  line-height: 1.6;
}
.fs-footer-links {
  display: flex; justify-content: center; gap: 24px;
  margin-top: 20px;
}
.fs-footer-links a {
  color: var(--ink-2) !important; font-size: 12px;
  text-decoration: none; transition: color 0.2s;
}
.fs-footer-links a:hover { color: var(--accent); }

/* ---------- Section spacing helper ---------- */
.fs-divider { height: 1px; background: var(--line-soft); margin: 80px 0; border: none; }

/* ---------- Preset gallery ---------- */
.fs-gallery {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
  margin-bottom: 40px;
}
.fs-gallery-item {
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: transform 0.3s cubic-bezier(0.2,0.8,0.2,1), box-shadow 0.3s;
  cursor: pointer;
  text-align: left;
  padding: 0;
  font-family: inherit;
  width: 100%;
}
.fs-gallery-item:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}
.fs-gallery-thumb {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
  background: var(--surface-2);
}
.fs-gallery-body { padding: 18px 20px 22px; }
.fs-gallery-label {
  font-size: 15px; font-weight: 600; letter-spacing: -0.01em;
  margin: 0 0 4px; color: var(--ink);
}
.fs-gallery-desc {
  font-size: 12px; color: var(--ink-2) !important; line-height: 1.5;
  margin: 0 0 10px;
}
.fs-gallery-tag {
  display: inline-block;
  font: 500 10px 'JetBrains Mono', monospace;
  letter-spacing: 0.08em;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 4px 10px; border-radius: 980px;
}
.demo-section {
  margin: 0 0 40px;
}
.demo-section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  margin: 0 0 18px;
}
.demo-section-head h3 {
  margin: 0 0 6px;
  color: var(--ink) !important;
  font-size: 24px;
  letter-spacing: -0.02em;
}
.demo-section-head p {
  margin: 0;
  color: var(--ink-2) !important;
  font-size: 14px;
  line-height: 1.5;
}
.demo-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}
.demo-card {
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}
.demo-card video {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: var(--surface-2);
}
.demo-card-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
}
.demo-card-body strong {
  display: block;
  margin-bottom: 4px;
  color: var(--ink) !important;
  font-size: 15px;
}
.demo-card-body span {
  color: var(--ink-2) !important;
  font-size: 12px;
}
.demo-load {
  flex: 0 0 auto;
  border: 1px solid var(--line) !important;
  border-radius: 980px;
  background: var(--surface) !important;
  color: var(--ink) !important;
  padding: 8px 14px;
  font: 500 12px 'Inter', sans-serif;
  cursor: pointer;
}
.demo-load:hover {
  background: var(--surface-2) !important;
}

/* ---------- Responsive ---------- */
@media (max-width: 900px) {
  .gradio-container { padding: 0 20px 60px !important; }
  .fs-nav-links { display: none; }
  .fs-hero { padding: 48px 0 36px; }
  .fs-strip { grid-template-columns: 1fr; }
  .fs-gallery { grid-template-columns: repeat(2, 1fr); }
  .metrics-row { grid-template-columns: repeat(2, 1fr); }
  .metric-hero-value { font-size: 48px; }
  .how-grid { grid-template-columns: 1fr; }
  .demo-grid { grid-template-columns: 1fr; }
  .demo-section-head { display: block; }
  .demo-section-head p { margin-top: 6px; }
}
"""

with gr.Blocks(title="FocusStream — Smart Video Optimizer", css=CSS) as demo:
    # ---------- Navigation ----------
    gr.HTML("""
    <nav class="fs-nav">
      <div class="fs-nav-inner">
        <div class="fs-nav-brand">
          <div class="fs-nav-mark">F</div>
          <span class="fs-nav-name">FocusStream</span>
        </div>
        <div class="fs-nav-links">
          <a href="#optimizer">Optimizer</a>
          <a href="#how">How it works</a>
          <a href="#privacy">Privacy</a>
          <span class="fs-nav-pill"><span class="dot"></span>Local engine</span>
        </div>
      </div>
    </nav>
    """)

    # ---------- Hero ----------
    gr.HTML("""
    <section class="fs-hero">
      <span class="fs-hero-eyebrow">Smart video optimization</span>
      <h1>Keep your subject crisp.<br>Let the background breathe.</h1>
      <p class="fs-hero-sub">FocusStream uses a focus-aware codec that preserves the people and objects you care about at full resolution while intelligently optimizing everything else — built for weak Wi-Fi, slow cell data, and video calls on the move.</p>
      <div class="fs-hero-cta">
        <button class="fs-btn-primary" onclick="document.getElementById('optimizer').scrollIntoView({behavior:'smooth'})">Try the optimizer</button>
        <button class="fs-btn-ghost" onclick="document.getElementById('how').scrollIntoView({behavior:'smooth'})">See how it works</button>
      </div>
    </section>
    """)

    # ---------- Feature strip ----------
    gr.HTML("""
    <div class="fs-strip">
      <div class="fs-strip-cell">
        <div class="fs-strip-icon" style="background:var(--accent-soft);color:var(--accent)">&#9679;</div>
        <h3>Focus-aware compression</h3>
        <p>Detects people, faces, and foreground objects, then reserves up to 95% of your bandwidth for what matters most.</p>
      </div>
      <div class="fs-strip-cell">
        <div class="fs-strip-icon" style="background:var(--green-soft);color:var(--green)">&#9889;</div>
        <h3>Built for slow connections</h3>
        <p>Simulate networks down to 10 kbps and see exactly how each approach handles hotel Wi-Fi, train commutes, or weak cellular.</p>
      </div>
      <div class="fs-strip-cell">
        <div class="fs-strip-icon" style="background:#fff4e6;color:var(--orange)">&#128274;</div>
        <h3>Completely private</h3>
        <p>Runs entirely on your device. No video, frames, or telemetry ever leave your machine — the model runs on your CPU.</p>
      </div>
    </div>
    """)

    # ---------- Tabs ----------
    with gr.Tabs():
        with gr.Tab("Video Optimizer", id="optimizer"):
            gr.HTML(
                '<div class="fs-section-head"><h2>Compare compression side by side</h2>'
                '<p>Pick a preset below or upload your own clip, simulate a slow connection, and judge the difference between standard compression and our focus-aware codec at the same bandwidth.</p></div>'
            )

            ensure_samples()
            gr.HTML("""
            <section class="demo-section">
              <div class="demo-section-head">
                <div>
                  <h3>Start with a built-in demo</h3>
                  <p>Preview a clip, load it into the optimizer, then compare standard and focus-aware compression.</p>
                </div>
              </div>
            </section>
            """)
            with gr.Row(elem_classes="demo-grid"):
                with gr.Column(elem_classes="demo-card"):
                    gr.Video(
                        value=str(SAMPLES_DIR / "portrait_call.mp4"),
                        label="Portrait call demo",
                        height=180,
                        interactive=False,
                    )
                    with gr.Row(elem_classes="demo-card-body"):
                        gr.HTML(
                            '<div><strong>Portrait call</strong>'
                            '<span>Subject detail over weak Wi-Fi</span></div>'
                        )
                        load_portrait = gr.Button("Use this demo")
                with gr.Column(elem_classes="demo-card"):
                    gr.Video(
                        value=str(SAMPLES_DIR / "outdoor_action.mp4"),
                        label="Outdoor action demo",
                        height=180,
                        interactive=False,
                    )
                    with gr.Row(elem_classes="demo-card-body"):
                        gr.HTML(
                            '<div><strong>Outdoor action</strong>'
                            '<span>Moving subjects on cellular data</span></div>'
                        )
                        load_outdoor = gr.Button("Use this demo")

            _preset_keys = list(PRESETS.keys())
            _gallery_items = []
            for _key in _preset_keys:
                _thumb = SAMPLES_DIR / f"{_key}.jpg"
                _gallery_items.append((str(_thumb), PRESETS[_key]["label"]))
            preset_gallery = gr.Gallery(
                value=_gallery_items,
                label="Preset samples — click to load",
                show_label=True,
                columns=4,
                height=200,
                allow_preview=False,
                elem_classes="fs-card",
            )

            with gr.Row():
                with gr.Column(scale=5, elem_classes="fs-card"):
                    video = gr.Video(label="Your video", sources=["upload"], height=280)
                with gr.Column(scale=3, elem_classes="fs-card"):
                    bandwidth = gr.Slider(
                        1, 2000, value=10, step=1,
                        label="Simulated network speed (kbps)",
                        info="Throttle down to 10 kbps for extreme conditions",
                    )
                    blur_intensity = gr.Slider(
                        0, 50, value=25, step=1,
                        label="Background blur intensity",
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
                    run = gr.Button("Optimize video", variant="primary")
            with gr.Row():
                baseline = gr.Image(label="Standard compression", height=300)
                semantic = gr.Image(label="Focus-aware codec — subject preserved", height=300)
            with gr.Row():
                mask_viz = gr.Image(label="Focus map — detected subject regions", height=220)
            metrics_html = gr.HTML(
                '<div class="empty-state"><div class="empty-icon">+</div>'
                '<strong>Run the optimizer to see results</strong>'
                '<span>Pick a preset above or upload your own video, then click Optimize to compare compression strategies.</span></div>'
            )

            def _on_preset_select(evt: gr.SelectData):
                idx = evt.index
                if isinstance(idx, (list, tuple)):
                    idx = idx[0] if idx else 0
                idx = int(idx)
                if idx < 0 or idx >= len(_preset_keys):
                    raise gr.Error("Invalid preset selected.")
                return _load_preset(_preset_keys[idx])

            preset_gallery.select(
                _on_preset_select,
                None,
                [video, bandwidth, blur_intensity, focal_sharpness, max_frames],
            )
            load_portrait.click(
                lambda: _load_preset("portrait_call"),
                None,
                [video, bandwidth, blur_intensity, focal_sharpness, max_frames],
            )
            load_outdoor.click(
                lambda: _load_preset("outdoor_action"),
                None,
                [video, bandwidth, blur_intensity, focal_sharpness, max_frames],
            )
            run.click(
                run_demo,
                [video, bandwidth, blur_intensity, focal_sharpness, max_frames],
                [baseline, semantic, mask_viz, metrics_html],
            )

        with gr.Tab("How it works", id="how"):
            gr.HTML("""
            <div class="how-section">
              <div class="fs-section-head">
                <h2>How FocusStream works</h2>
                <p>The codec engine, ML detection, and interface are fully decoupled — the core compression logic never depends on the UI.</p>
              </div>
              <div class="how-grid">
                <article class="how-card">
                  <div class="how-step">01</div>
                  <h4>Find the subject</h4>
                  <p>A lightweight on-device model identifies the important regions — people, faces, foreground objects — in each frame.</p>
                  <ul>
                    <li>Runs entirely on your CPU</li>
                    <li>No cloud, no uploads, no tracking</li>
                    <li>Swap the model without touching the codec</li>
                  </ul>
                </article>
                <article class="how-card">
                  <div class="how-step">02</div>
                  <h4>Split and encode</h4>
                  <p>The native C++ engine encodes the focal region at high quality while downscaling and blurring the background to fit your bandwidth budget.</p>
                  <ul>
                    <li>Subject stays at full resolution</li>
                    <li>Background is pixelated and blurred</li>
                    <li>Binary quality search hits the byte target</li>
                  </ul>
                </article>
                <article class="how-card">
                  <div class="how-step">03</div>
                  <h4>Reassemble and display</h4>
                  <p>The receiver composites the crisp subject over the degraded background, producing a frame that looks good even at 10 kbps.</p>
                  <ul>
                    <li>Feathered mask for smooth transitions</li>
                    <li>Drop-tolerant UDP transport option</li>
                    <li>Reports real bandwidth, not promises</li>
                  </ul>
                </article>
              </div>
            </div>
            """)

    # ---------- Footer ----------
    gr.HTML("""
    <footer class="fs-footer" id="privacy">
      <div class="fs-footer-mark">F</div>
      <p>FocusStream runs entirely on your device.</p>
      <p>No cloud. No tracking. Your video never leaves your machine.</p>
      <div class="fs-footer-links">
        <a href="#optimizer">Optimizer</a>
        <a href="#how">How it works</a>
        <a href="#privacy">Privacy</a>
      </div>
    </footer>
    """)


if __name__ == "__main__":
    demo.launch(css=CSS, allowed_paths=[str(SAMPLES_DIR)])
