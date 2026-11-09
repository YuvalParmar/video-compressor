"""Offline edge adapters for injury photos, voice notes, and camera vitals."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .emergency import OfflineTriageEngine, TriageAssessment


class OfflineMultimodalTriage:
    """Uses local OpenCV heuristics and optional text; no cloud calls."""

    def __init__(self, triage_engine: OfflineTriageEngine | None = None) -> None:
        self.triage_engine = triage_engine or OfflineTriageEngine()

    def assess(
        self,
        photo_path: str | Path | None = None,
        voice_note_path: str | Path | None = None,
        voice_transcript: str = "",
        vitals: dict[str, float] | None = None,
    ) -> TriageAssessment:
        if voice_note_path and not Path(voice_note_path).is_file():
            raise ValueError(f"unable to read voice note: {voice_note_path}")
        visual_cues = self._photo_cues(photo_path) if photo_path else []
        if voice_note_path and not voice_transcript:
            voice_transcript = "voice note received; offline transcript unavailable"
        return self.triage_engine.assess(visual_cues, voice_transcript, vitals)

    @staticmethod
    def _photo_cues(photo_path: str | Path) -> list[str]:
        image = cv2.imread(str(photo_path))
        if image is None:
            raise ValueError(f"unable to read injury photo: {photo_path}")
        # Conservative offline signal: red-pixel prevalence flags a possible
        # bleeding/injury region for human review, never a diagnosis.
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        red = ((hsv[:, :, 0] < 12) | (hsv[:, :, 0] > 170)) & (hsv[:, :, 1] > 100)
        return ["injury", "severe_bleeding"] if float(np.mean(red)) > 0.08 else ["person"]

    @staticmethod
    def estimate_rppg(camera_frames: list[np.ndarray], fps: float) -> dict[str, float]:
        if len(camera_frames) < 30 or fps <= 0:
            raise ValueError("rPPG requires at least 30 frames and a positive FPS")
        green = np.array([float(np.mean(frame[:, :, 1])) for frame in camera_frames])
        green -= np.mean(green)
        frequencies = np.fft.rfftfreq(len(green), 1.0 / fps)
        spectrum = np.abs(np.fft.rfft(green))
        band = (frequencies >= 0.8) & (frequencies <= 3.0)
        if not np.any(band) or float(np.max(spectrum[band])) == 0:
            return {"heart_rate": 0.0, "respiratory_rate": 0.0, "signal_quality": 0.0}
        heart_rate = float(frequencies[band][np.argmax(spectrum[band])] * 60.0)
        return {
            "heart_rate": round(heart_rate, 1),
            "respiratory_rate": round(heart_rate / 4.0, 1),
            "signal_quality": round(float(np.max(spectrum[band]) / (np.sum(spectrum) + 1e-6)), 3),
        }
