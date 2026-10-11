from unittest.mock import MagicMock, patch

import redis

from llm.cache import (
    CACHE_TTL_SECONDS,
    _cache_key,
    cache_triage,
    get_cached_triage,
)
from llm.schemas import TriageOutput


def sample_output():
    return TriageOutput(
        category="billing",
        urgency="normal",
        confidence=0.94,
        reason="The customer reports a payment issue.",
    )


def test_cache_key_is_consistent(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "llama3.2:3b")

    first_key = _cache_key("Payment failed")
    second_key = _cache_key("Payment failed")

    assert first_key == second_key
    assert first_key.startswith("triage:")


def test_cache_key_changes_with_message(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "llama3.2:3b")

    first_key = _cache_key("Payment failed")
    second_key = _cache_key("Login failed")

    assert first_key != second_key


def test_cache_hit_returns_cached_output():
    expected = sample_output()

    fake_redis = MagicMock()
    fake_redis.get.return_value = expected.model_dump_json()

    with patch("llm.cache._get_redis_client", return_value=fake_redis):
        result = get_cached_triage("Payment failed")

    assert result == expected
    fake_redis.get.assert_called_once()


def test_cache_miss_returns_none():
    fake_redis = MagicMock()
    fake_redis.get.return_value = None

    with patch("llm.cache._get_redis_client", return_value=fake_redis):
        result = get_cached_triage("New support message")

    assert result is None


def test_cache_write_uses_24_hour_ttl():
    output = sample_output()
    fake_redis = MagicMock()

    with patch("llm.cache._get_redis_client", return_value=fake_redis):
        cache_triage("Payment failed", output)

    fake_redis.setex.assert_called_once_with(
        _cache_key("Payment failed"),
        CACHE_TTL_SECONDS,
        output.model_dump_json(),
    )

    assert CACHE_TTL_SECONDS == 86400


def test_redis_failure_does_not_crash_cache_read():
    fake_redis = MagicMock()
    fake_redis.get.side_effect = redis.ConnectionError("Redis unavailable")

    with patch("llm.cache._get_redis_client", return_value=fake_redis):
        result = get_cached_triage("Payment failed")

    assert result is None


def test_redis_failure_does_not_crash_cache_write():
    fake_redis = MagicMock()
    fake_redis.setex.side_effect = redis.ConnectionError("Redis unavailable")

    with patch("llm.cache._get_redis_client", return_value=fake_redis):
        cache_triage("Payment failed", sample_output())

    fake_redis.setex.assert_called_once()


def test_triage_endpoint_cache_hit(monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from llm.schemas import TriageOutput
    from routes import triage

    client = TestClient(app)

    cached_output = TriageOutput(
        category="billing",
        urgency="normal",
        confidence=0.95,
        reason="Cached payment classification.",
    )

    monkeypatch.setenv("LLM_STUB", "0")
    monkeypatch.setenv("LLM_ENABLED", "1")

    monkeypatch.setattr(
    triage,
    "get_cached_triage_with_status",
    lambda text: (cached_output, "hit"),
)

    def fail_if_model_called(text):
        raise AssertionError(
            "Ollama should not be called on a cache hit"
        )

    monkeypatch.setattr(
        triage,
        "generate_triage_output",
        fail_if_model_called,
    )

    response = client.post(
        "/triage/",
        json={"text": "My payment failed"},
    )

    assert response.status_code == 200
    assert response.json()["category"] == "billing"
    assert response.json()["reason"] == "Cached payment classification."


def test_triage_endpoint_cache_miss(monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from llm.schemas import TriageOutput
    from routes import triage

    client = TestClient(app)

    expected_output = TriageOutput(
        category="bug",
        urgency="high",
        confidence=0.91,
        reason="The application is crashing.",
    )

    calls = []
    cached_results = []

    monkeypatch.setenv("LLM_STUB", "0")
    monkeypatch.setenv("LLM_ENABLED", "1")

    monkeypatch.setattr(
    triage,
    "get_cached_triage_with_status",
    lambda text: (None, "miss"),
)

    def fake_model(text):
        calls.append(text)
        return expected_output

    def fake_cache_write(text, output):
        cached_results.append((text, output))

    monkeypatch.setattr(
        triage,
        "generate_triage_output",
        fake_model,
    )
    monkeypatch.setattr(
        triage,
        "cache_triage",
        fake_cache_write,
    )

    response = client.post(
        "/triage/",
        json={"text": "The application keeps crashing"},
    )

    assert response.status_code == 200
    assert response.json()["category"] == "bug"
    assert calls == ["The application keeps crashing"]
    assert cached_results == [
        ("The application keeps crashing", expected_output)
    ]


def test_cache_error_status_when_redis_unavailable(monkeypatch):
    import redis

    from llm import cache

    class BrokenRedis:
        def get(self, key):
            raise redis.ConnectionError("Redis unavailable")

    monkeypatch.setattr(
        cache,
        "_get_redis_client",
        lambda: BrokenRedis(),
    )

    output, status = cache.get_cached_triage_with_status(
        "Test Redis failure"
    )

    assert output is None
    assert status == "error"


def test_triage_endpoint_records_redis_error(monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from routes import triage
    from llm.schemas import TriageOutput
    from llm.cache_metrics import get_cache_metrics

    client = TestClient(app)

    expected_output = TriageOutput(
        category="bug",
        urgency="high",
        confidence=0.95,
        reason="Application crashes on startup.",
    )

    monkeypatch.setenv("LLM_STUB", "0")
    monkeypatch.setenv("LLM_ENABLED", "1")

    monkeypatch.setattr(
        triage,
        "get_cached_triage_with_status",
        lambda text: (None, "error"),
    )

    monkeypatch.setattr(
        triage,
        "generate_triage_output",
        lambda text: expected_output,
    )

    monkeypatch.setattr(
        triage,
        "cache_triage",
        lambda text, output: None,
    )

    errors_before = get_cache_metrics()["errors"]

    response = client.post(
        "/triage",
        json={"text": "Application crashes on startup."},
    )

    assert response.status_code == 200
    assert response.json()["category"] == "bug"

    errors_after = get_cache_metrics()["errors"]

    assert errors_after == errors_before + 1
