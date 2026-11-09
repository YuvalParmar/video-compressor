from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import gradio as gr

from python.config import PipelineConfig
from python.edge_inference import OfflineMultimodalTriage
from python.emergency import IncidentStore, OfflineTriageEngine, incident_to_dict
from python.pipeline import process_video

incident_store = IncidentStore()
triage_engine = OfflineTriageEngine()
edge_triage = OfflineMultimodalTriage(triage_engine)


def _metric(value: Any, suffix: str = "") -> str:
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def _feed_report(metrics: dict[str, float]) -> str:
    return f"""
    <div class="result-grid">
      <div class="result-card accent"><span>SEMANTIC THROUGHPUT</span><strong>{_metric(metrics.get("semantic_kbps", 0), " kbps")}</strong><small>Measured payload rate</small></div>
      <div class="result-card"><span>PROCESSING</span><strong>{_metric(metrics.get("processing_fps", 0), " fps")}</strong><small>Local CPU pipeline</small></div>
      <div class="result-card"><span>ROI PRESERVED</span><strong>{_metric(metrics.get("roi_fraction", 0) * 100, "%")}</strong><small>High-detail scene area</small></div>
      <div class="result-card"><span>FRAMES</span><strong>{_metric(metrics.get("frames", 0))}</strong><small>{_metric(metrics.get("dropped_frames", 0))} dropped</small></div>
    </div>
    <div class="result-note"><span class="pulse-dot"></span> Semantic stream ready · priority regions protected first</div>
    """


def run_demo(video: str, bandwidth_kbps: int, confidence: float, max_frames: int):
    if not video:
        raise gr.Error("Add a field video before starting the codec.")
    config = PipelineConfig(
        bandwidth_kbps=int(bandwidth_kbps),
        confidence_threshold=float(confidence),
        max_frames=int(max_frames),
    )
    baseline, semantic, metrics = process_video(Path(video), config)
    metrics["target_fps"] = 60.0
    metrics["roi_bandwidth_percent"] = 90.0
    return baseline, semantic, _feed_report(metrics)


def _assessment_card(assessment: dict[str, Any]) -> str:
    priority = escape(str(assessment.get("priority", "P4")))
    tone = {"P1": "critical", "P2": "high", "P3": "medium"}.get(priority, "low")
    reasons = "".join(f"<li>{escape(str(reason))}</li>" for reason in assessment.get("reasons", []))
    return f"""
    <div class="assessment-card {tone}">
      <div class="assessment-top"><div><span class="eyebrow">OFFLINE TRIAGE</span><h2>{priority} <em>priority</em></h2></div><div class="score">{assessment.get("score", 0)}<small>/100</small></div></div>
      <div class="confidence"><span>Confidence</span><b>{float(assessment.get("confidence", 0)) * 100:.0f}%</b></div>
      <div class="bar"><i style="width:{float(assessment.get("confidence", 0)) * 100:.0f}%"></i></div>
      <p class="recommendation">{escape(str(assessment.get("recommended_action", "")))}</p>
      <ul>{reasons}</ul>
      <small class="muted">Local model · No network required · Human review required</small>
    </div>
    """


def _queue_markup(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<div class="empty-state"><div class="empty-icon">+</div><strong>No incidents queued</strong><span>New field reports will appear here in priority order.</span></div>'
    rows = []
    for item in items:
        assessment = item.get("assessment") or {}
        priority = escape(str(assessment.get("priority", "P4")))
        tone = {"P1": "critical", "P2": "high", "P3": "medium"}.get(priority, "low")
        rows.append(
            f'<div class="queue-row"><span class="priority-pill {tone}">{priority}</span>'
            f'<div><strong>{escape(item.get("location", "Unknown location"))}</strong><small>{escape(item.get("reporter", "unknown"))} · {escape(item.get("status", "OPEN"))}</small></div>'
            f'<span class="queue-score">{assessment.get("score", 0)}<small> score</small></span></div>'
        )
    return "".join(rows)


def submit_incident(
    reporter: str, location: str, notes: str, visual_cues: list[str],
    transcript: str, spo2: float, heart_rate: float, respiratory_rate: float,
):
    incident = incident_store.create(
        {
            "reporter": reporter, "location": location, "notes": notes,
            "visual_cues": visual_cues or [], "transcript": transcript,
            "vitals": {"spo2": spo2, "heart_rate": heart_rate, "respiratory_rate": respiratory_rate},
        },
        triage_engine,
    )
    items = [incident_to_dict(item) for item in incident_store.list()]
    return _assessment_card(incident_to_dict(incident)["assessment"]), _queue_markup(items), items


def refresh_incidents():
    items = [incident_to_dict(item) for item in incident_store.list()]
    return _queue_markup(items), items


def assess_edge_case(photo, voice_note, transcript, spo2, heart_rate, respiratory_rate):
    assessment = edge_triage.assess(
        photo_path=photo, voice_note_path=voice_note, voice_transcript=transcript or "",
        vitals={"spo2": float(spo2), "heart_rate": float(heart_rate), "respiratory_rate": float(respiratory_rate)},
    )
    return _assessment_card({
        "priority": assessment.priority, "score": assessment.score,
        "confidence": assessment.confidence, "reasons": list(assessment.reasons),
        "recommended_action": assessment.recommended_action,
    })


CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { --ink:#f2f5f2; --muted:#8d9b99; --line:#263532; --panel:#111a19; --panel2:#172321; --mint:#8df2c4; --amber:#f4c66d; --red:#ff7f72; }
body, .gradio-container { background:#09100f !important; color:var(--ink) !important; font-family:'Space Grotesk',sans-serif !important; }
.gradio-container { max-width:1420px !important; padding:24px 42px 54px !important; }
.app-header { display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid var(--line); padding:14px 0 25px; margin-bottom:28px; }
.brand { display:flex; gap:14px; align-items:center; }.brand-mark { width:42px;height:42px;border-radius:13px;background:var(--mint);color:#09100f;display:grid;place-items:center;font-weight:700;font-size:20px; }
.eyebrow, .brand-meta, .result-card span { font:500 10px 'DM Mono',monospace; letter-spacing:.13em; color:var(--muted); }.brand h1 { font-size:22px; margin:0; letter-spacing:-.03em; }.brand p { color:var(--muted); margin:4px 0 0; font-size:13px; }.live { color:var(--mint); font:500 11px 'DM Mono',monospace; letter-spacing:.1em; margin-top:11px; }.pulse-dot { display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--mint);box-shadow:0 0 0 4px #8df2c41c;margin-right:8px; }
.hero { background:linear-gradient(115deg,#182a27 0%,#101918 60%,#111b1a 100%); border:1px solid #2b4840; border-radius:20px; padding:32px 36px; position:relative; overflow:hidden; margin-bottom:24px; }.hero:after { content:''; position:absolute; width:290px;height:290px;border:1px solid #8df2c41b;border-radius:50%;right:5%;top:-150px; }.hero h2 { font-size:38px; line-height:1.04; letter-spacing:-.06em; max-width:620px; margin:10px 0 13px; }.hero p { color:#b5c3c0; max-width:600px; line-height:1.6; margin:0; }.hero-tag { color:var(--mint); font:500 11px 'DM Mono',monospace; letter-spacing:.12em; }
.section-title { margin:28px 0 14px; }.section-title h3 { margin:0; font-size:17px; }.section-title p { color:var(--muted); margin:4px 0 0; font-size:13px; }
.tabs { border:0 !important; }.tab-nav { gap:8px !important; border-bottom:1px solid var(--line) !important; margin-bottom:22px !important; }.tab-nav button { background:transparent !important; color:var(--muted) !important; border:0 !important; padding:12px 18px !important; }.tab-nav button.selected { color:var(--ink) !important; border-bottom:2px solid var(--mint) !important; }
.panel, .block { background:var(--panel) !important; border:1px solid var(--line) !important; border-radius:16px !important; padding:20px !important; }.panel h3 { margin-top:0; }.gradio-container label, .gradio-container .label { color:#b9c5c2 !important; font-size:12px !important; }.gradio-container input, .gradio-container textarea, .gradio-container select { background:#0b1413 !important; border-color:#2a3b38 !important; color:var(--ink) !important; border-radius:10px !important; }.gradio-container button { border-radius:10px !important; border:1px solid #304743 !important; background:#1b2b28 !important; color:var(--ink) !important; }.gradio-container button.primary { background:var(--mint) !important; color:#08110f !important; border-color:var(--mint) !important; font-weight:700 !important; }
.result-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-top:12px; }.result-card { background:#0c1514; border:1px solid var(--line); border-radius:12px; padding:16px; }.result-card.accent { border-color:#3e6e5d; }.result-card strong { display:block; font-size:22px; margin:9px 0 3px; }.result-card small { color:var(--muted); }.result-note { color:#aabbb5; font:12px 'DM Mono',monospace; margin-top:15px; }
.assessment-card { background:#111a19; border:1px solid #335248; border-radius:16px; padding:22px; }.assessment-card.critical { border-color:#8d4942; }.assessment-card h2 { margin:6px 0 0; font-size:36px; }.assessment-card h2 em { color:var(--muted); font-style:normal;font-size:17px;font-weight:400; }.assessment-top { display:flex; justify-content:space-between; }.score { color:var(--mint); font-size:34px; font-weight:700; }.score small { color:var(--muted); font-size:13px; }.confidence { display:flex; justify-content:space-between; color:var(--muted); font:11px 'DM Mono',monospace; margin-top:24px; }.confidence b { color:var(--ink); }.bar { height:5px; background:#25312f; border-radius:5px; margin:8px 0 19px; }.bar i { display:block; height:100%; background:var(--mint); border-radius:5px; }.recommendation { color:#d5e0dc; line-height:1.5; border-left:2px solid var(--mint); padding-left:12px; }.assessment-card li { color:var(--muted); margin:6px 0; font-size:13px; }.muted { color:var(--muted); }.queue-row { display:flex; align-items:center; gap:12px; border-bottom:1px solid var(--line); padding:14px 0; }.queue-row:last-child { border-bottom:0; }.queue-row div:nth-child(2) { flex:1; }.queue-row strong, .queue-row small { display:block; }.queue-row small { color:var(--muted); margin-top:4px; font-size:11px; }.priority-pill { font:600 11px 'DM Mono',monospace; padding:6px 8px; border-radius:7px; background:#24312e; }.priority-pill.critical { color:var(--red); background:#482725; }.priority-pill.high { color:var(--amber); background:#44361f; }.queue-score { color:var(--mint); font:500 13px 'DM Mono',monospace; }.queue-score small { display:inline; }.empty-state { padding:38px 12px; text-align:center; color:var(--muted); }.empty-state strong,.empty-state span { display:block; }.empty-state span { font-size:12px; margin-top:7px; }.empty-icon { margin:0 auto 12px; width:30px;height:30px;border:1px dashed #557269;border-radius:50%;display:grid;place-items:center;color:var(--mint); }
.architecture { display:grid; grid-template-columns:1fr 38px 1.4fr 38px 1fr; align-items:stretch; gap:12px; margin-top:22px; }.arch-node { background:#101a18; border:1px solid #2b4840; border-radius:15px; padding:20px; }.arch-node.core { background:linear-gradient(145deg,#19312b,#101b19); border-color:#42745f; }.arch-node.receiver { background:linear-gradient(145deg,#202a24,#101918); border-color:#53654a; }.arch-node h4 { margin:8px 0 8px; font-size:16px; }.arch-node p { color:var(--muted); font-size:12px; line-height:1.55; margin:0; }.arch-node ul { padding-left:18px; margin:13px 0 0; color:#b8c6c1; font-size:12px; line-height:1.8; }.arch-arrow { display:grid; place-items:center; color:var(--mint); font-size:22px; }.arch-kicker { color:var(--mint); font:500 10px 'DM Mono',monospace; letter-spacing:.12em; }.arch-caption { color:var(--muted); font:11px 'DM Mono',monospace; text-align:center; margin-top:12px; }.receiver-strip { margin-top:20px; border:1px solid #3b4a3b; border-radius:14px; padding:15px 18px; background:#141c18; display:flex; align-items:center; gap:14px; }.receiver-icon { width:32px; height:32px; border-radius:9px; background:#d8b772; color:#141b16; display:grid; place-items:center; font-weight:700; }.receiver-strip strong { font-size:13px; }.receiver-strip span { display:block; color:var(--muted); font-size:11px; margin-top:3px; }
@media (max-width:800px) { .gradio-container { padding:18px !important; }.hero h2 { font-size:30px; }.result-grid { grid-template-columns:repeat(2,1fr); }.app-header { display:block; }.live { margin-top:18px; } }
@media (max-width:800px) { .architecture { grid-template-columns:1fr; }.arch-arrow { transform:rotate(90deg); height:20px; } }
"""

with gr.Blocks(title="Relay / Offline Emergency Coordination") as demo:
    gr.HTML("""
    <header class="app-header"><div class="brand"><div class="brand-mark">R</div><div><h1>Relay</h1><p>Offline emergency coordination</p></div></div><div class="live"><span class="pulse-dot"></span>LOCAL NODE · ONLINE</div></header>
    <section class="hero"><span class="hero-tag">FIELD OPERATIONS / 01</span><h2>Keep the signal alive<br>when everything else drops.</h2><p>Relay protects the details that matter most: people, injuries, and decisions. A local-first command post for low-bandwidth teams.</p></section>
    """)
    with gr.Tabs(elem_classes="tabs"):
        with gr.Tab("Signal optimizer", id="signal"):
            gr.HTML('<div class="section-title"><h3>Semantic video uplink</h3><p>Preserve high-detail regions while the mesh is under pressure.</p></div>')
            with gr.Row():
                with gr.Column(scale=5, elem_classes="panel"):
                    video = gr.Video(label="FIELD VIDEO", sources=["upload"], height=260)
                with gr.Column(scale=3, elem_classes="panel"):
                    bandwidth = gr.Slider(1, 2000, value=10, step=1, label="Mesh budget (kbps)")
                    confidence = gr.Slider(0.05, 0.95, value=0.35, step=0.05, label="Semantic confidence")
                    max_frames = gr.Slider(1, 300, value=90, step=1, label="Frames to process")
                    run = gr.Button("Optimize signal  →", variant="primary")
            with gr.Row():
                baseline = gr.Image(label="CONVENTIONAL FEED", height=280)
                semantic = gr.Image(label="SEMANTIC FEED · ROI PROTECTED", height=280)
            feed_metrics = gr.HTML('<div class="empty-state">Run an uplink to see measured performance.</div>')
            run.click(run_demo, [video, bandwidth, confidence, max_frames], [baseline, semantic, feed_metrics])
        with gr.Tab("Incident board", id="incidents"):
            gr.HTML('<div class="section-title"><h3>Local incident board</h3><p>Turn field observations into an explainable dispatch queue. No cloud. No guesswork.</p></div>')
            with gr.Row():
                with gr.Column(scale=5, elem_classes="panel"):
                    reporter = gr.Textbox(label="REPORTING UNIT", value="field-team-1")
                    location = gr.Textbox(label="LOCATION", placeholder="Sector, grid, or landmark")
                    notes = gr.Textbox(label="FIELD NOTES", lines=3, placeholder="What is happening?")
                    visual_cues = gr.CheckboxGroup(["person", "injury", "severe_bleeding", "unconscious", "not_breathing", "trapped", "fire"], label="OBSERVED CUES")
                    transcript = gr.Textbox(label="OFFLINE VOICE TRANSCRIPT", lines=2)
                    with gr.Row():
                        spo2 = gr.Number(label="SpO2", value=98)
                        heart_rate = gr.Number(label="Heart rate", value=80)
                        respiratory_rate = gr.Number(label="Resp. rate", value=16)
                    submit = gr.Button("Assess & queue incident  →", variant="primary")
                with gr.Column(scale=4):
                    assessment = gr.HTML('<div class="empty-state">Assessment will appear here.</div>')
                    gr.Markdown("### Dispatch queue")
                    queue = gr.HTML('<div class="empty-state">No incidents queued.</div>')
                    refresh = gr.Button("Refresh queue")
            hidden_queue = gr.JSON(visible=False)
            submit.click(submit_incident, [reporter, location, notes, visual_cues, transcript, spo2, heart_rate, respiratory_rate], [assessment, queue, hidden_queue])
            refresh.click(refresh_incidents, outputs=[queue, hidden_queue])
        with gr.Tab("Edge intake", id="edge"):
            gr.HTML('<div class="section-title"><h3>Multimodal edge intake</h3><p>Combine a local photo, voice note, and vitals before a responder arrives.</p></div>')
            with gr.Row():
                with gr.Column(elem_classes="panel"):
                    injury_photo = gr.Image(label="INJURY PHOTO", type="filepath", height=230)
                    voice_note = gr.Audio(label="VOICE NOTE", type="filepath")
                with gr.Column(elem_classes="panel"):
                    edge_transcript = gr.Textbox(label="OPERATOR SUMMARY", lines=3)
                    edge_spo2 = gr.Number(label="SpO2", value=98)
                    edge_hr = gr.Number(label="Heart rate", value=80)
                    edge_rr = gr.Number(label="Resp. rate", value=16)
                    assess = gr.Button("Run edge assessment  →", variant="primary")
            edge_result = gr.HTML('<div class="empty-state">Assessment will appear here.</div>')
            assess.click(assess_edge_case, [injury_photo, voice_note, edge_transcript, edge_spo2, edge_hr, edge_rr], edge_result)
        with gr.Tab("How it works", id="architecture"):
            gr.HTML("""
            <div class="section-title"><h3>The edge mesh, at a glance</h3><p>Decisions happen close to the incident. Only the signal that matters travels across the mesh.</p></div>
            <div class="architecture">
              <article class="arch-node"><span class="arch-kicker">01 / INPUTS</span><h4>Field teams & drones</h4><p>Capture the scene from the places where infrastructure is already gone.</p><ul><li>Visual triage data</li><li>Voice notes & vitals</li><li>Camera feeds</li></ul></article>
              <div class="arch-arrow">→</div>
              <article class="arch-node core"><span class="arch-kicker">02 / EDGE MESH NODE</span><h4>Relay runs locally</h4><p>One laptop or Raspberry Pi turns raw inputs into actionable, bandwidth-aware intelligence.</p><ul><li><b>Semantic codec</b> protects wounds, survivors, and vitals</li><li><b>Offline triage</b> scores urgency with explainable rules</li><li><b>rPPG extraction</b> estimates vitals without cloud calls</li></ul></article>
              <div class="arch-arrow">→</div>
              <article class="arch-node receiver"><span class="arch-kicker">03 / RECEIVER · LAPTOP 2</span><h4>Re-assemble, then render</h4><p>Late packets and drops do not freeze the view. The receiver keeps the last-known valid background while a fresh ROI arrives.</p><ul><li><b>C++ frame re-assembler</b> expires incomplete frames safely</li><li><b>Canvas stitching</b> overlays the detail box on the background map</li><li><b>60 FPS viewport</b> keeps the scene readable in motion</li></ul></article>
            </div>
            <div class="receiver-strip"><div class="receiver-icon">↗</div><div><strong>Receiver re-assembly is the resilience layer.</strong><span>Compressed background + high-detail ROI bounding box → one synchronized canvas on the command dashboard.</span></div></div>
            <div class="arch-caption"><span class="pulse-dot"></span> OFFLINE-FIRST · DROP-TOLERANT · LOW LATENCY · HUMAN OVERSIGHT</div>
            """)
    gr.HTML('<footer class="brand-meta" style="text-align:center;margin-top:35px">RELAY IS A PRIORITIZATION AID · HUMAN COMMAND ALWAYS HAS THE FINAL WORD</footer>')


if __name__ == "__main__":
    demo.launch(css=CSS)
