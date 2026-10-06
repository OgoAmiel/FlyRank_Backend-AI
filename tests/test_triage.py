import pytest

import llm.triage_service as triage_service
from llm.triage_service import _validate_output


def test_validate_valid_triage_output():
    raw_output = """
    {
        "category": "billing",
        "urgency": "normal",
        "confidence": 0.91,
        "reason": "The user reports a duplicate charge issue."
    }
    """

    result = _validate_output(raw_output)

    assert result.category.value == "billing"
    assert result.urgency.value == "normal"
    assert result.confidence == 0.91
    assert result.reason == "The user reports a duplicate charge issue."


def test_validate_invalid_category():
    raw_output = """
    {
        "category": "technical",
        "urgency": "high",
        "confidence": 0.90,
        "reason": "The application is not working."
    }
    """

    with pytest.raises(ValueError):
        _validate_output(raw_output)


def test_validate_confidence_above_one():
    raw_output = """
    {
        "category": "bug",
        "urgency": "high",
        "confidence": 1.5,
        "reason": "The application crashes during login."
    }
    """

    with pytest.raises(ValueError):
        _validate_output(raw_output)


def test_validate_markdown_wrapped_json():
    raw_output = """
    ```json
    {
        "category": "feature",
        "urgency": "normal",
        "confidence": 0.85,
        "reason": "The user is requesting a new feature."
    }
    ```
    """

    result = _validate_output(raw_output)

    assert result.category.value == "feature"
    assert result.urgency.value == "normal"
    assert result.confidence == 0.85
    assert result.reason == "The user is requesting a new feature."


def test_validate_malformed_json():
    raw_output = "This is not JSON at all."

    with pytest.raises(ValueError):
        _validate_output(raw_output)


def test_generate_triage_output_repairs_invalid_response(monkeypatch):
    responses = [
        "This is not valid JSON.",
        """
        {
            "category": "bug",
            "urgency": "high",
            "confidence": 0.92,
            "reason": "The application crashes during login."
        }
        """
    ]

    def fake_call_model(messages, used_repair):
        return responses.pop(0)

    monkeypatch.setattr(
        triage_service,
        "_call_model",
        fake_call_model
    )

    result = triage_service.generate_triage_output(
        "The app crashes every time I try to log in."
    )

    assert result.category.value == "bug"
    assert result.urgency.value == "high"
    assert result.confidence == 0.92


def test_generate_triage_output_fails_after_repair(monkeypatch, tmp_path):
    responses = [
        "This is not valid JSON.",
        "Still not valid JSON."
    ]

    def fake_call_model(messages, used_repair):
        return responses.pop(0)

    monkeypatch.setattr(
        triage_service,
        "_call_model",
        fake_call_model
    )

    monkeypatch.setattr(
        triage_service,
        "QUARANTINE_PATH",
        tmp_path / "quarantine.jsonl"
    )

    with pytest.raises(
        triage_service.TriageProcessingError,
        match="Could not produce valid triage JSON after one repair attempt"
    ):
        triage_service.generate_triage_output(
            "The app is behaving strangely."
        )

    quarantine_file = tmp_path / "quarantine.jsonl"

    assert quarantine_file.exists()

    contents = quarantine_file.read_text(encoding="utf-8")

    assert "This is not valid JSON." in contents
    assert "Still not valid JSON." in contents
    assert "The app is behaving strangely." in contents

def test_triage_endpoint_stub_mode(client, monkeypatch):
    monkeypatch.setenv("LLM_STUB", "1")

    response = client.post(
        "/triage/",
        json={"text": "I was charged twice this month."}
    )

    assert response.status_code == 200

    assert response.json() == {
        "category": "other",
        "urgency": "normal",
        "confidence": 0.25,
        "reason": "Stub mode enabled: model call skipped."
    }

def test_triage_endpoint_rejects_empty_text(client):
    response = client.post(
        "/triage/",
        json={"text": ""}
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Invalid field: text"
    }

def test_triage_endpoint_when_llm_disabled(client, monkeypatch):
    monkeypatch.delenv("LLM_STUB", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "false")

    response = client.post(
        "/triage/",
        json={"text": "I was charged twice this month."}
    )

    assert response.status_code == 503

    assert response.json() == {
        "error": "LLM processing is disabled by configuration",
        "fallback": {
            "category": "other",
            "urgency": "low",
            "confidence": 0.0,
            "reason": "LLM disabled; returning deterministic fallback."
        }
    }

def test_triage_endpoint_processing_error(client, monkeypatch):
    monkeypatch.delenv("LLM_STUB", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "true")

    def fake_generate_triage_output(text):
        raise triage_service.TriageProcessingError(
            "Could not produce valid triage JSON after one repair attempt"
        )

    monkeypatch.setattr(
        "routes.triage.generate_triage_output",
        fake_generate_triage_output
    )

    response = client.post(
        "/triage/",
        json={"text": "The app is not working."}
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": "Could not produce valid triage JSON after one repair attempt"
    }

def test_triage_endpoint_timeout(client, monkeypatch):
    monkeypatch.delenv("LLM_STUB", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "true")

    def fake_generate_triage_output(text):
        raise triage_service.LLMTimeoutError(
            "The model request timed out after 30 seconds"
        )

    monkeypatch.setattr(
        "routes.triage.generate_triage_output",
        fake_generate_triage_output
    )

    response = client.post(
        "/triage/",
        json={"text": "The app keeps crashing."}
    )

    assert response.status_code == 504
    assert response.json() == {
        "error": "The model request timed out after 30 seconds"
    }

def test_triage_endpoint_provider_authentication_error(client, monkeypatch):
    monkeypatch.delenv("LLM_STUB", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "true")

    def fake_generate_triage_output(text):
        raise triage_service.LLMProviderError(
            "Provider request failed with status 401",
            status_code=401
        )

    monkeypatch.setattr(
        "routes.triage.generate_triage_output",
        fake_generate_triage_output
    )

    response = client.post(
        "/triage/",
        json={"text": "I was charged twice."}
    )

    assert response.status_code == 502
    assert response.json() == {
        "error": "Provider authentication failed (check LLM_API_KEY)",
        "provider_status": 401
    }

def test_triage_endpoint_provider_error(client, monkeypatch):
    monkeypatch.delenv("LLM_STUB", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "true")

    def fake_generate_triage_output(text):
        raise triage_service.LLMProviderError(
            "Provider request failed with status 500",
            status_code=500
        )

    monkeypatch.setattr(
        "routes.triage.generate_triage_output",
        fake_generate_triage_output
    )

    response = client.post(
        "/triage/",
        json={"text": "The dashboard is not loading."}
    )

    assert response.status_code == 502
    assert response.json() == {
        "error": "Provider request failed with status 500",
        "provider_status": 500
    }

def test_triage_endpoint_success(client, monkeypatch):
    monkeypatch.delenv("LLM_STUB", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "true")

    def fake_generate_triage_output(text):
        return triage_service.TriageOutput(
            category="billing",
            urgency="normal",
            confidence=0.91,
            reason="The user reports a duplicate charge issue."
        )

    monkeypatch.setattr(
        "routes.triage.generate_triage_output",
        fake_generate_triage_output
    )

    response = client.post(
        "/triage/",
        json={"text": "I was charged twice this month."}
    )

    assert response.status_code == 200
    assert response.json() == {
        "category": "billing",
        "urgency": "normal",
        "confidence": 0.91,
        "reason": "The user reports a duplicate charge issue."
    }

def test_triage_endpoint_missing_llm_configuration(client, monkeypatch):
    monkeypatch.delenv("LLM_STUB", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "true")

    def fake_generate_triage_output(text):
        raise RuntimeError(
            "Missing required environment variable: LLM_API_KEY"
        )

    monkeypatch.setattr(
        "routes.triage.generate_triage_output",
        fake_generate_triage_output
    )

    response = client.post(
        "/triage/",
        json={"text": "I need help with my account."}
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": "Missing required environment variable: LLM_API_KEY"
    }