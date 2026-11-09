from __future__ import annotations

from pathlib import Path

import gradio as gr

from python.config import PipelineConfig
from python.pipeline import process_video


def run_demo(video: str, bandwidth_kbps: int, confidence: float, max_frames: int):
    if not video:
        raise gr.Error("Upload a video before starting the codec.")
    config = PipelineConfig(
        bandwidth_kbps=int(bandwidth_kbps),
        confidence_threshold=float(confidence),
        max_frames=int(max_frames),
    )
    baseline, semantic, metrics = process_video(Path(video), config)
    caption = " | ".join(f"{key}: {value:.2f}" for key, value in metrics.items())
    return baseline, semantic, caption


with gr.Blocks(title="Semantic Live Codec") as demo:
    gr.Markdown("# Semantic Live Codec\nCompare conventional and semantic compression under a simulated low-bandwidth link.")
    with gr.Row():
        video = gr.Video(label="Input video", type="filepath")
        with gr.Column():
            bandwidth = gr.Slider(1, 2000, value=10, step=1, label="Simulated bandwidth (kbps)")
            confidence = gr.Slider(0.05, 0.95, value=0.35, step=0.05, label="Semantic confidence")
            max_frames = gr.Slider(1, 300, value=90, step=1, label="Frames to process")
            run = gr.Button("Run semantic codec", variant="primary")
    with gr.Row():
        baseline = gr.Image(label="Standard compression")
        semantic = gr.Image(label="Semantic codec")
    metrics = gr.Textbox(label="Metrics", interactive=False)
    run.click(run_demo, [video, bandwidth, confidence, max_frames], [baseline, semantic, metrics])


if __name__ == "__main__":
    demo.launch()
