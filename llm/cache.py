
import hashlib
import json
import logging
import os

import redis
from pydantic import ValidationError

from llm.schemas import TriageOutput
from llm.triage_service import get_prompt_version


logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 86400  # 24 hours


def _get_redis_client():
    redis_url = os.getenv("REDIS_URL")

    if not redis_url:
        return None

    return redis.Redis.from_url(
        redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def _cache_key(text: str) -> str:
    payload = {
        "text": text,
        "prompt_version": get_prompt_version(),
        "model": os.getenv("LLM_MODEL", ""),
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
    )

    digest = hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()

    return f"triage:{digest}"


def get_cached_triage(text: str) -> TriageOutput | None:
    try:
        client = _get_redis_client()

        if client is None:
            return None

        cached = client.get(_cache_key(text))

        if cached is None:
            return None

        return TriageOutput.model_validate_json(cached)

    except (redis.RedisError, ValueError, ValidationError) as exc:
        logger.warning("Redis cache read failed: %s", exc)
        return None


def cache_triage(text: str, output: TriageOutput) -> None:
    try:
        client = _get_redis_client()

        if client is None:
            return

        client.setex(
            _cache_key(text),
            CACHE_TTL_SECONDS,
            output.model_dump_json(),
        )

    except (redis.RedisError, ValueError) as exc:
        logger.warning("Redis cache write failed: %s", exc)
