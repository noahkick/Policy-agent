"""Small OpenAI adapter for extracting structured policy rules."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from .prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt


DEFAULT_MODEL = "gpt-4o-mini"


class LLMExtractionError(RuntimeError):
    """Raised when policy-rule extraction cannot produce structured data."""


def extract_policy_rules(
    policy_text: str,
    *,
    source_metadata: Mapping[str, object] | None = None,
    client: Any | None = None,
) -> list[dict[str, Any]]:
    """Extract JSON rule objects from one policy chunk.

    The OpenAI import is lazy so the rest of the deterministic pipeline can be
    imported and tested without installing the optional network client.
    """

    if not isinstance(policy_text, str) or not policy_text.strip():
        return []

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key and client is None:
        raise LLMExtractionError("OPENAI_API_KEY is not configured")

    if client is None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMExtractionError("The openai package is not installed") from exc
        client = OpenAI(api_key=api_key)

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_extraction_prompt(
                        policy_text, dict(source_metadata or {})
                    ),
                },
            ],
        )
    except Exception as exc:
        raise LLMExtractionError(f"LLM policy extraction failed: {exc}") from exc

    content = _response_content(response)
    try:
        payload = json.loads(content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LLMExtractionError("LLM returned malformed JSON") from exc

    if not isinstance(payload, Mapping):
        raise LLMExtractionError("LLM response must be a JSON object")
    rules = payload.get("rules")
    if not isinstance(rules, list) or any(not isinstance(rule, Mapping) for rule in rules):
        raise LLMExtractionError("LLM response must contain a list of rule objects")
    return [dict(rule) for rule in rules]


def _response_content(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        raise LLMExtractionError("LLM response did not contain message content") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMExtractionError("LLM response contained empty content")
    return content


__all__ = ["DEFAULT_MODEL", "LLMExtractionError", "extract_policy_rules"]