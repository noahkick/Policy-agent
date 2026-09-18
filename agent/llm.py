"""Gemini adapter for extracting structured policy rules."""

from __future__ import annotations

import json
import os
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

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            },
        )
    except Exception as exc:
        raise LLMExtractionError(
            f"Gemini policy extraction failed: {exc}"
        ) from exc

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