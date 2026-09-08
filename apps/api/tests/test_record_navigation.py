from app.agents.record_agent import SYSTEM_PROMPT


def test_record_agent_has_non_clinical_safety_boundary() -> None:
    prompt = SYSTEM_PROMPT.lower()
    assert "do not diagnose" in prompt
    assert "do not" in prompt and "recommend treatment" in prompt


def test_record_navigation_mentions_authenticated_patient_scope() -> None:
    assert "authenticated patient" in SYSTEM_PROMPT.lower()
    assert "their own health-record documents" in SYSTEM_PROMPT.lower()
