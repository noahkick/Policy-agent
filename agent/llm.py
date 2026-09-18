"""Gemini adapter for extracting structured policy rules."""

from __future__ import annotations

import json
import os
import random
import time
from collections.abc import Mapping
from typing import Any

from dotenv import load_dotenv
from google import genai

from .prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt


DEFAULT_MODEL = "gemini-3.6-flash"

load_dotenv()


class LLMExtractionError(RuntimeError):
    """Raised when policy-rule extraction cannot produce structured data."""


def extract_policy_rules(
    policy_text: str,
    *,
    source_metadata: Mapping[str, object] | None = None,
    client: Any | None = None,
) -> list[dict[str, Any]]:
    """Extract JSON rule objects from one policy chunk using Gemini."""

    if not isinstance(policy_text, str) or not policy_text.strip():
        return []

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key and client is None:
        raise LLMExtractionError(
            "GEMINI_API_KEY is not configured"
        )

    if client is None:
        try:
            client = genai.Client(api_key=api_key)
        except Exception as exc:
            raise LLMExtractionError(
                f"Failed to initialize Gemini client: {exc}"
            ) from exc

    model = (
        os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip()
        or DEFAULT_MODEL
    )

    prompt = f"""
{EXTRACTION_SYSTEM_PROMPT}

{build_extraction_prompt(
    policy_text,
    dict(source_metadata or {})
)}
"""

    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                },
            )
            break
        except Exception as exc:
            if (
                _is_quota_exhaustion_error(exc)
                or not _is_transient_gemini_error(exc)
                or attempt == 3
            ):
                raise LLMExtractionError(
                    f"Gemini policy extraction failed: {exc}"
                ) from exc
            delay = min(2 ** (attempt + 1), 8) + random.uniform(0, 0.5)
            time.sleep(delay)

    content = _response_content(response)

    try:
        payload = json.loads(content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LLMExtractionError(
            "Gemini returned malformed JSON"
        ) from exc

    if not isinstance(payload, Mapping):
        raise LLMExtractionError(
            "Gemini response must be a JSON object"
        )

    rules = payload.get("rules")

    if (
        not isinstance(rules, list)
        or any(not isinstance(rule, Mapping) for rule in rules)
    ):
        raise LLMExtractionError(
            "Gemini response must contain a list of rule objects"
        )

    return [dict(rule) for rule in rules]


def _is_quota_exhaustion_error(error: Exception) -> bool:
    """Return whether a Gemini error indicates exhausted quota."""

    error_text = str(error)
    return (
        "RESOURCE_EXHAUSTED" in error_text
        or "GenerateRequestsPerDayPerModel-FreeTier" in error_text
    )


def _is_transient_gemini_error(error: Exception) -> bool:
    """Return whether a Gemini error should be retried."""

    status_code = getattr(error, "status_code", None)
    if status_code is None:
        status_code = getattr(error, "code", None)
    if callable(status_code):
        status_code = status_code()
    if status_code is None:
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
    return status_code in {429, 500, 502, 503, 504}


def _response_content(response: Any) -> str:
    """Extract text from Gemini response."""

    try:
        content = response.text
    except AttributeError as exc:
        raise LLMExtractionError(
            "Gemini response did not contain text"
        ) from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMExtractionError(
            "Gemini response contained empty content"
        )

    return content


__all__ = [
    "DEFAULT_MODEL",
    "LLMExtractionError",
    "extract_policy_rules",
]