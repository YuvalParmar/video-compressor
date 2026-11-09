from python.emergency import IncidentStore, OfflineTriageEngine


def test_multimodal_triage_prioritizes_life_threat():
    assessment = OfflineTriageEngine().assess(
        visual_cues=["person", "severe_bleeding"],
        transcript="patient can't breathe",
        vitals={"spo2": 84},
    )
    assert assessment.priority == "P1"
    assert assessment.score == 100
    assert len(assessment.reasons) >= 3


def test_incident_store_is_local_and_status_is_validated():
    store = IncidentStore()
    incident = store.create(
        {"reporter": "drone-7", "location": "sector A", "visual_cues": ["person"]},
        OfflineTriageEngine(),
    )
    assert store.list()[0].incident_id == incident.incident_id
    store.update_status(incident.incident_id, "ACKNOWLEDGED")
    assert incident.status == "ACKNOWLEDGED"
