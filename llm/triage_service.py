import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from json import JSONDecoder
from pathlib import Path
import random
import time

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from pydantic import ValidationError

from llm.schemas import TriageOutput


ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT_DIR / "prompts" / "triage-v2.md"
PROMPT_VERSION = "triage-v2"
QUARANTINE_PATH = ROOT_DIR / "logs" / "quarantine.jsonl"
COST_LOG_PATH = ROOT_DIR / "logs" / "cost.jsonl"
REQUEST_TIMEOUT_SECONDS = 60.0
RETRY_DELAYS_SECONDS = [1.0, 2.0, 4.0]


class TriageProcessingError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LLMTimeoutError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LLMProviderError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _load_env() -> None:
    load_dotenv(ROOT_DIR / ".env")


def _read_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_prompt_version() -> str:
    return PROMPT_VERSION


def _parse_retry_after_seconds(retry_after: str | None) -> float | None:
    if not retry_after:
        return None

    try:
        seconds = float(retry_after)
        return max(0.0, seconds)
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(retry_after)
        now = datetime.now(timezone.utc)
        return max(0.0, (retry_at - now).total_seconds())
    except Exception:
        return None


def _append_cost_log(
    model: str,
    duration_ms: int,
    input_tokens: int,
    output_tokens: int,
    used_repair: bool,
) -> None:
    COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "used_repair": used_repair,
    }
    with COST_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _call_model(messages: list[dict[str, str]], used_repair: bool) -> str:
    model_name = _required_env("LLM_MODEL")
    client = OpenAI(
        base_url=_required_env("LLM_BASE_URL"),
        api_key=_required_env("LLM_API_KEY"),
        max_retries=0,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    for attempt in range(len(RETRY_DELAYS_SECONDS) + 1):
        call_started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model_name,
                temperature=0.2,
                messages=messages,
            )
            duration_ms = int((time.perf_counter() - call_started) * 1000)
            usage = response.usage
            _append_cost_log(
                model=model_name,
                duration_ms=duration_ms,
                input_tokens=(usage.prompt_tokens if usage else 0),
                output_tokens=(usage.completion_tokens if usage else 0),
                used_repair=used_repair,
            )
            return response.choices[0].message.content or ""
        except APITimeoutError as exc:
            if attempt < len(RETRY_DELAYS_SECONDS):
                delay = RETRY_DELAYS_SECONDS[attempt] + random.uniform(0.0, 0.35)
                time.sleep(delay)
                continue
            raise LLMTimeoutError(
                f"The model request timed out after {REQUEST_TIMEOUT_SECONDS:g} seconds"
                ) from exc
        except APIConnectionError as exc:
            if attempt < len(RETRY_DELAYS_SECONDS):
                delay = RETRY_DELAYS_SECONDS[attempt] + random.uniform(0.0, 0.35)
                time.sleep(delay)
                continue
            raise LLMProviderError("Could not connect to the model provider") from exc
        except APIStatusError as exc:
            status = exc.status_code
            if status in {400, 401, 403}:
                raise LLMProviderError(
                    f"Provider request failed with status {status}; request was not retried",
                    status_code=status,
                ) from exc

            if status == 429 or (500 <= status <= 599):
                if attempt < len(RETRY_DELAYS_SECONDS):
                    retry_after = _parse_retry_after_seconds(
                        exc.response.headers.get("Retry-After") if exc.response else None
                    )
                    if retry_after is not None:
                        delay = retry_after
                    else:
                        delay = RETRY_DELAYS_SECONDS[attempt] + random.uniform(0.0, 0.35)
                    time.sleep(delay)
                    continue

            raise LLMProviderError(
                f"Provider request failed with status {status}",
                status_code=status,
            ) from exc


def _extract_json_object(raw_text: str) -> dict:
    text = raw_text.strip()

    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1]
            if "\n" in text:
                first_line, rest = text.split("\n", 1)
                if first_line.strip().lower() in {"json", "javascript", "js"}:
                    text = rest

    decoder = JSONDecoder()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("Model output JSON must be an object")
    except Exception:
        pass

    for idx, char in enumerate(text):
        if char != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(text, idx)
            if isinstance(candidate, dict):
                return candidate
        except Exception:
            continue

    raise ValueError("Could not parse a JSON object from model output")


def _validate_output(raw_text: str) -> TriageOutput:
    try:
        parsed_obj = _extract_json_object(raw_text)
        return TriageOutput.model_validate(parsed_obj)
    except ValidationError as exc:
        raise ValueError(f"Schema validation failed: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"JSON parse failed: {exc}") from exc


def _append_quarantine(input_text: str, error_text: str, outputs: list[str]) -> None:
    QUARANTINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input": {"text": input_text},
        "error": error_text,
        "outputs": outputs,
    }
    with QUARANTINE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def generate_triage_output(text: str) -> TriageOutput:
    _load_env()

    system_prompt = _read_prompt()
    user_payload = json.dumps({"text": text}, ensure_ascii=False)
    outputs: list[str] = []

    first_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_payload},
    ]

    first_output = _call_model(first_messages, used_repair=False)
    outputs.append(first_output)

    try:
        return _validate_output(first_output)
    except ValueError as first_error:
        repair_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
            {"role": "assistant", "content": first_output},
            {
                "role": "user",
                "content": (
                    "Your previous answer was rejected for this reason: "
                    f"{first_error}. Return only corrected JSON matching the schema."
                ),
            },
        ]

        second_output = _call_model(repair_messages, used_repair=True)
        outputs.append(second_output)

        try:
            return _validate_output(second_output)
        except ValueError as second_error:
            _append_quarantine(text, str(second_error), outputs)
            raise TriageProcessingError(
                "Could not produce valid triage JSON after one repair attempt"
            ) from second_error
