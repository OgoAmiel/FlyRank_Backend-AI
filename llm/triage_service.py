import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT_DIR / "prompts" / "triage-v1.md"
PROMPT_VERSION = "triage-v1"


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


def generate_triage_raw_output(text: str) -> str:
    _load_env()

    client = OpenAI(
        base_url=_required_env("LLM_BASE_URL"),
        api_key=_required_env("LLM_API_KEY"),
    )

    system_prompt = _read_prompt()
    user_payload = json.dumps({"text": text}, ensure_ascii=False)

    response = client.chat.completions.create(
        model=_required_env("LLM_MODEL"),
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ],
    )

    return response.choices[0].message.content or ""
