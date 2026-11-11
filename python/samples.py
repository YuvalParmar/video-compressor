"""Procedurally generate short sample videos for the preset gallery.

Each sample simulates a real-world scenario so users can instantly test the
optimizer without uploading their own files. Videos are generated with OpenCV
and written to ``samples/`` alongside JPEG thumbnails.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

_WIDTH, _HEIGHT, _FPS = 480, 360, 15


def _writer(name: str) -> cv2.VideoWriter:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(
        str(SAMPLES_DIR / f"{name}.mp4"), fourcc, _FPS, (_WIDTH, _HEIGHT)
    )


def _save_thumb(name: str, frame: np.ndarray) -> None:
    cv2.imwrite(str(SAMPLES_DIR / f"{name}.jpg"), frame)


def _draw_face(frame: np.ndarray, cx: int, cy: int, scale: float) -> None:
    skin = (180, 160, 140)
    cv2.ellipse(frame, (cx, cy), (int(60 * scale), int(80 * scale)), 0, 0, 360, skin, -1)
    cv2.circle(frame, (cx - int(22 * scale), cy - int(15 * scale)), int(8 * scale), (40, 40, 40), -1)
    cv2.circle(frame, (cx + int(22 * scale), cy - int(15 * scale)), int(8 * scale), (40, 40, 40), -1)
    cv2.ellipse(frame, (cx, cy + int(18 * scale)), (int(18 * scale), int(10 * scale)), 0, 0, 180, (60, 40, 40), -1)


def _gen_portrait_call() -> None:
    w = _writer("portrait_call")
    thumb = None
    for i in range(90):
        frame = np.full((_HEIGHT, _WIDTH, 3), 45, dtype=np.uint8)
        cv2.rectangle(frame, (0, 0), (_WIDTH, 60), (55, 55, 60), -1)
        sway = int(math.sin(i * 0.08) * 12)
        _draw_face(frame, _WIDTH // 2 + sway, _HEIGHT // 2 + 10, 1.0)
        thumb = frame.copy()
        w.write(frame)
    w.release()
    if thumb is not None:
        _save_thumb("portrait_call", thumb)


def _gen_outdoor_action() -> None:
    w = _writer("outdoor_action")
    colors = [(80, 130, 60), (120, 80, 160), (200, 120, 50), (50, 160, 200)]
    thumb = None
    for i in range(90):
        frame = np.full((_HEIGHT, _WIDTH, 3), 100, dtype=np.uint8)
        cv2.rectangle(frame, (0, _HEIGHT - 80), (_WIDTH, _HEIGHT), (60, 100, 50), -1)
        cv2.rectangle(frame, (0, 0), (_WIDTH, 120), (140, 180, 220), -1)
        for j, color in enumerate(colors):
            x = int((i * 5 + j * 120) % (_WIDTH + 60)) - 30
            y = _HEIGHT - 70 - j * 15
            cv2.circle(frame, (x, y), 20, color, -1)
        thumb = frame.copy()
        w.write(frame)
    w.release()
    if thumb is not None:
        _save_thumb("outdoor_action", thumb)


def _gen_extreme_low() -> None:
    w = _writer("extreme_low")
    thumb = None
    for i in range(45):
        frame = np.full((_HEIGHT, _WIDTH, 3), 12, dtype=np.uint8)
        cx = _WIDTH // 2 + int(math.sin(i * 0.1) * 20)
        cy = _HEIGHT // 2
        cv2.circle(frame, (cx, cy), 45, (200, 200, 180), -1)
        cv2.circle(frame, (cx, cy), 45, (120, 120, 100), 2)
        thumb = frame.copy()
        w.write(frame)
    w.release()
    if thumb is not None:
        _save_thumb("extreme_low", thumb)


def _gen_balanced() -> None:
    w = _writer("balanced")
    thumb = None
    for i in range(120):
        frame = np.full((_HEIGHT, _WIDTH, 3), 70, dtype=np.uint8)
        for j in range(5):
            angle = i * 0.05 + j * 1.2
            x = int(_WIDTH // 2 + math.cos(angle) * (60 + j * 25))
            y = int(_HEIGHT // 2 + math.sin(angle) * (40 + j * 20))
            color = (60 + j * 30, 100 + j * 20, 150 - j * 20)
            cv2.circle(frame, (x, y), 18, color, -1)
        cv2.rectangle(frame, (_WIDTH // 2 - 70, _HEIGHT - 50), (_WIDTH // 2 + 70, _HEIGHT), (50, 60, 70), -1)
        thumb = frame.copy()
        w.write(frame)
    w.release()
    if thumb is not None:
        _save_thumb("balanced", thumb)


def generate_all() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    _gen_portrait_call()
    _gen_outdoor_action()
    _gen_extreme_low()
    _gen_balanced()


def ensure_samples() -> None:
    needed = ["portrait_call", "outdoor_action", "extreme_low", "balanced"]
    if all((SAMPLES_DIR / f"{n}.mp4").is_file() and (SAMPLES_DIR / f"{n}.jpg").is_file() for n in needed):
        return
    generate_all()
