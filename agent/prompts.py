"""Prompts used by the policy-rule extraction layer."""

from __future__ import annotations


EXTRACTION_SYSTEM_PROMPT = """You are a policy interpretation assistant. Extract explicit rules from the supplied policy text. Do not invent rules. Do not make the final authorization decision. Preserve uncertainty when the policy does not contain enough information.

Return only valid JSON with this shape: {"rules": [{...}]}. Each rule must use only fields supported by the existing PolicyRule structure: action, resource, subject, role, location, device, vendor, retention_period, required_approval, conditions, exception, effect, reason, and evidence.

The required fields are action, resource, effect, and evidence. effect must be exactly one of ALLOW, DENY, CONDITIONAL, UNKNOWN, or CONFLICT. conditions and exception must be JSON objects when present. Evidence must be a non-empty list of objects with an excerpt copied exactly from the supplied policy text. Never infer a rule or evidence that the text does not support. If no reliable rule can be extracted, return {"rules": []}."""


def build_extraction_prompt(policy_text: str, source_metadata: dict[str, object] | None = None) -> str:
    """Build the user message for one retrieved policy chunk."""

    metadata = source_metadata or {}
    return (
        "Extract explicit policy rules from this retrieved policy chunk. "
        "The source metadata is context only; do not treat it as policy text.\n\n"
        f"SOURCE METADATA:\n{metadata}\n\n"
        "POLICY TEXT (quote evidence only from this block):\n"
        "<policy_text>\n"
        f"{policy_text}\n"
        "</policy_text>"
    )


__all__ = ["EXTRACTION_SYSTEM_PROMPT", "build_extraction_prompt"]