import json
import os
from pathlib import Path
from datetime import datetime, timezone
from json import JSONDecoder

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from llm.schemas import TriageOutput


ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT_DIR / "prompts" / "triage-v1.md"
PROMPT_VERSION = "triage-v1"
QUARANTINE_PATH = ROOT_DIR / "logs" / "quarantine.jsonl"


class TriageProcessingError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


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


def _call_model(messages: list[dict[str, str]]) -> str:
    client = OpenAI(
        base_url=_required_env("LLM_BASE_URL"),
        api_key=_required_env("LLM_API_KEY"),
    )

    response = client.chat.completions.create(
        model=_required_env("LLM_MODEL"),
        temperature=0.2,
        messages=messages,
    )

    return response.choices[0].message.content or ""


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

    first_output = _call_model(first_messages)
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

        second_output = _call_model(repair_messages)
        outputs.append(second_output)

        try:
            return _validate_output(second_output)
        except ValueError as second_error:
            _append_quarantine(text, str(second_error), outputs)
            raise TriageProcessingError(
                "Could not produce valid triage JSON after one repair attempt"
            ) from second_error
