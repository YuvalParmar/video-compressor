from __future__ import annotations

from pathlib import Path

import gradio as gr

from python.config import PipelineConfig
from python.edge_inference import OfflineMultimodalTriage
from python.emergency import IncidentStore, OfflineTriageEngine, incident_to_dict
from python.pipeline import process_video

incident_store = IncidentStore()
triage_engine = OfflineTriageEngine()
edge_triage = OfflineMultimodalTriage(triage_engine)


def run_demo(video: str, bandwidth_kbps: int, confidence: float, max_frames: int):
    if not video:
        raise gr.Error("Upload a video before starting the codec.")
    config = PipelineConfig(
        bandwidth_kbps=int(bandwidth_kbps),
        confidence_threshold=float(confidence),
        max_frames=int(max_frames),
    )
    baseline, semantic, metrics = process_video(Path(video), config)
    metrics["target_fps"] = 60.0
    metrics["roi_bandwidth_percent"] = 90.0
    caption = " | ".join(f"{key}: {value:.2f}" for key, value in metrics.items())
    return baseline, semantic, caption


def submit_incident(
    reporter: str,
    location: str,
    notes: str,
    visual_cues: list[str],
    transcript: str,
    spo2: float,
    heart_rate: float,
    respiratory_rate: float,
):
    incident = incident_store.create(
        {
            "reporter": reporter,
            "location": location,
            "notes": notes,
            "visual_cues": visual_cues or [],
            "transcript": transcript,
            "vitals": {
                "spo2": spo2,
                "heart_rate": heart_rate,
                "respiratory_rate": respiratory_rate,
            },
        },
        triage_engine,
    )
    return incident_to_dict(incident), [
        incident_to_dict(item) for item in incident_store.list()
    ]


def refresh_incidents():
    return [incident_to_dict(item) for item in incident_store.list()]


def assess_edge_case(photo, voice_note, transcript, spo2, heart_rate, respiratory_rate):
    assessment = edge_triage.assess(
        photo_path=photo,
        voice_note_path=voice_note,
        voice_transcript=transcript or "",
        vitals={
            "spo2": float(spo2),
            "heart_rate": float(heart_rate),
            "respiratory_rate": float(respiratory_rate),
        },
    )
    return {
        "priority": assessment.priority,
        "score": assessment.score,
        "confidence": assessment.confidence,
        "reasons": list(assessment.reasons),
        "recommended_action": assessment.recommended_action,
        "offline": True,
    }


with gr.Blocks(
    title="Off-Grid Autonomous Emergency Command Station",
) as demo:
    gr.Markdown(
        "# Off-Grid Autonomous Emergency Command Station\n"
        "Offline-first coordination for field medics and drone operators. "
        "Triage is a prioritization aid, not a medical diagnosis."
    )
    with gr.Tab("Live feed codec"):
        with gr.Row():
            video = gr.Video(label="Input aerial/field video")
            with gr.Column():
                bandwidth = gr.Slider(1, 2000, value=10, step=1, label="Simulated mesh bandwidth (kbps)")
                confidence = gr.Slider(0.05, 0.95, value=0.35, step=0.05, label="Semantic confidence")
                max_frames = gr.Slider(1, 300, value=90, step=1, label="Frames to process")
                run = gr.Button("Run adaptive feed", variant="primary")
        with gr.Row():
            baseline = gr.Image(label="Conventional low-bandwidth feed")
            semantic = gr.Image(label="Semantic emergency feed")
        metrics = gr.Textbox(label="Feed metrics", interactive=False)
        run.click(run_demo, [video, bandwidth, confidence, max_frames], [baseline, semantic, metrics])
    with gr.Tab("Offline triage"):
        with gr.Row():
            with gr.Column():
                reporter = gr.Textbox(label="Reporter / unit", value="field-team-1")
                location = gr.Textbox(label="Location", placeholder="Sector, grid, or landmark")
                notes = gr.Textbox(label="Field notes", lines=3)
                visual_cues = gr.CheckboxGroup(
                    ["person", "injury", "severe_bleeding", "unconscious",
                     "not_breathing", "trapped", "fire"],
                    label="Locally observed visual cues",
                )
                transcript = gr.Textbox(
                    label="Offline voice-to-text report",
                    placeholder="Optional transcript from a local radio/voice model",
                    lines=3,
                )
            with gr.Column():
                spo2 = gr.Number(label="SpO2 (%)", value=98)
                heart_rate = gr.Number(label="Heart rate (bpm)", value=80)
                respiratory_rate = gr.Number(label="Respiratory rate (/min)", value=16)
                submit = gr.Button("Assess and queue incident", variant="primary")
                assessment = gr.JSON(label="Local triage assessment")
        incident_queue = gr.JSON(label="Command-post incident queue")
        refresh = gr.Button("Refresh local queue")
        submit.click(
            submit_incident,
            [reporter, location, notes, visual_cues, transcript, spo2, heart_rate, respiratory_rate],
            [assessment, incident_queue],
        )
        refresh.click(refresh_incidents, outputs=incident_queue)
    with gr.Tab("Edge multimodal intake"):
        gr.Markdown("Local-only photo and voice-note intake. No cloud inference is used.")
        with gr.Row():
            injury_photo = gr.Image(label="Injury photo", type="filepath")
            voice_note = gr.Audio(label="Voice note", type="filepath")
            with gr.Column():
                edge_transcript = gr.Textbox(
                    label="Offline transcript / operator summary", lines=3
                )
                edge_spo2 = gr.Number(label="SpO2 (%)", value=98)
                edge_hr = gr.Number(label="Heart rate (bpm)", value=80)
                edge_rr = gr.Number(label="Respiratory rate (/min)", value=16)
                assess = gr.Button("Run edge assessment", variant="primary")
        edge_result = gr.JSON(label="Offline multimodal assessment")
        assess.click(
            assess_edge_case,
            [injury_photo, voice_note, edge_transcript, edge_spo2, edge_hr, edge_rr],
            edge_result,
        )


if __name__ == "__main__":
    demo.launch(
        css="body { background: #0b1220; } .gradio-container { max-width: 1500px !important; }"
    )
