"""Offline emergency coordination primitives.

The triage engine is a prioritization aid, not a medical diagnosis system. It
uses explainable rules so it can run without cloud services or model downloads.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class TriageAssessment:
    priority: str
    score: int
    confidence: float
    reasons: tuple[str, ...]
    recommended_action: str
    assessed_at: str


@dataclass
class Incident:
    incident_id: str
    reporter: str
    location: str
    notes: str
    visual_cues: list[str] = field(default_factory=list)
    transcript: str = ""
    vitals: dict[str, float] = field(default_factory=dict)
    status: str = "OPEN"
    assessment: TriageAssessment | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class OfflineTriageEngine:
    """Fuse local visual, language, and vital-sign cues deterministically."""

    _visual_weights = {
        "unconscious": 55,
        "not_breathing": 65,
        "severe_bleeding": 50,
        "fire": 35,
        "trapped": 35,
        "injury": 25,
        "person": 8,
    }
    _text_weights = {
        "unconscious": 55,
        "not breathing": 65,
        "can't breathe": 60,
        "severe bleeding": 50,
        "trapped": 35,
        "chest pain": 35,
        "injured": 25,
    }

    def assess(
        self,
        visual_cues: Iterable[str] = (),
        transcript: str = "",
        vitals: dict[str, float] | None = None,
    ) -> TriageAssessment:
        reasons: list[str] = []
        score = 0
        normalized_cues = {cue.strip().lower().replace(" ", "_") for cue in visual_cues}
        for cue, weight in self._visual_weights.items():
            if cue in normalized_cues:
                score += weight
                reasons.append(f"visual cue: {cue.replace('_', ' ')}")

        normalized_text = transcript.lower()
        for phrase, weight in self._text_weights.items():
            if phrase in normalized_text:
                score += weight
                reasons.append(f"field report: {phrase}")

        numeric_vitals = vitals or {}
        if numeric_vitals.get("spo2", 100) < 90:
            score += 45
            reasons.append("SpO2 below 90%")
        if numeric_vitals.get("heart_rate", 0) > 130:
            score += 25
            reasons.append("heart rate above 130 bpm")
        if numeric_vitals.get("respiratory_rate", 0) > 30:
            score += 30
            reasons.append("respiratory rate above 30/min")

        score = min(score, 100)
        if score >= 70:
            priority, action = "P1", "Immediate responder dispatch and casualty extraction."
        elif score >= 40:
            priority, action = "P2", "Dispatch the next available medical team."
        elif score >= 15:
            priority, action = "P3", "Assess when a responder is available."
        else:
            priority, action = "P4", "Monitor feed and request more information."
        confidence = min(0.95, 0.45 + 0.08 * len(reasons))
        return TriageAssessment(
            priority=priority,
            score=score,
            confidence=round(confidence, 2),
            reasons=tuple(reasons) or ("No high-risk cue detected.",),
            recommended_action=action,
            assessed_at=datetime.now(timezone.utc).isoformat(),
        )


class IncidentStore:
    """Thread-safe local incident registry shared by UI and mesh handlers."""

    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}
        self._lock = threading.RLock()

    def create(self, payload: dict[str, Any], engine: OfflineTriageEngine) -> Incident:
        incident = Incident(
            incident_id=str(uuid.uuid4()),
            reporter=str(payload.get("reporter", "unknown")).strip() or "unknown",
            location=str(payload.get("location", "unknown")).strip() or "unknown",
            notes=str(payload.get("notes", "")).strip(),
            visual_cues=list(payload.get("visual_cues", [])),
            transcript=str(payload.get("transcript", "")).strip(),
            vitals={key: float(value) for key, value in payload.get("vitals", {}).items()},
        )
        incident.assessment = engine.assess(
            incident.visual_cues, incident.transcript, incident.vitals
        )
        with self._lock:
            self._incidents[incident.incident_id] = incident
        return incident

    def list(self) -> list[Incident]:
        with self._lock:
            return sorted(
                self._incidents.values(),
                key=lambda item: (
                    item.assessment.priority if item.assessment else "P4",
                    item.created_at,
                ),
            )

    def update_status(self, incident_id: str, status: str) -> Incident:
        if status not in {"OPEN", "ACKNOWLEDGED", "RESOLVED"}:
            raise ValueError("status must be OPEN, ACKNOWLEDGED, or RESOLVED")
        with self._lock:
            try:
                incident = self._incidents[incident_id]
            except KeyError as exc:
                raise KeyError(f"unknown incident: {incident_id}") from exc
            incident.status = status
            return incident


def incident_to_dict(incident: Incident) -> dict[str, Any]:
    result = asdict(incident)
    if incident.assessment is not None:
        result["assessment"]["reasons"] = list(incident.assessment.reasons)
    return result
