"""Validation and trusted evidence conversion for extracted policy rules."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .policy_engine import PolicyStatus
from .state import Evidence


RULE_FIELDS = frozenset(
    {
        "action",
        "resource",
        "subject",
        "role",
        "location",
        "device",
        "vendor",
        "retention_period",
        "required_approval",
        "conditions",
        "exception",
        "effect",
        "reason",
        "evidence",
    }
)
REQUIRED_FIELDS = frozenset({"action", "resource", "effect", "evidence"})


def validate_policy_rule(
    candidate: Any,
    *,
    source_chunk: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return a compatible rule, or ``None`` when the candidate is unsafe."""

    if not isinstance(candidate, Mapping):
        return None
    if set(candidate) - RULE_FIELDS or not REQUIRED_FIELDS.issubset(candidate):
        return None

    rule = dict(candidate)
    for field in ("action", "resource", "effect"):
        if not isinstance(rule[field], str) or not rule[field].strip():
            return None
    if rule["effect"] not in {status.value for status in PolicyStatus}:
        return None
    for field in ("subject", "role", "location", "device", "vendor", "reason"):
        if field in rule and (not isinstance(rule[field], str) or not rule[field].strip()):
            return None
    for field in ("conditions", "exception"):
        if field in rule and not isinstance(rule[field], Mapping):
            return None
        if isinstance(rule.get(field), Mapping) and not all(
            isinstance(key, str) for key in rule[field]
        ):
            return None

    evidence = _validated_evidence(rule["evidence"], source_chunk)
    if evidence is None:
        return None
    rule["evidence"] = evidence
    return rule


def validate_policy_rules(
    candidates: Any,
    *,
    source_chunk: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate a list of model rules without silently repairing invalid data."""

    if not isinstance(candidates, list):
        return []
    validated: list[dict[str, Any]] = []
    for candidate in candidates:
        rule = validate_policy_rule(candidate, source_chunk=source_chunk)
        if rule is not None:
            validated.append(rule)
    return validated


def _validated_evidence(value: Any, source_chunk: Mapping[str, Any] | None) -> list[Evidence] | None:
    if not isinstance(value, list) or not value:
        return None
    content = source_chunk.get("content") if isinstance(source_chunk, Mapping) else None
    metadata = source_chunk.get("metadata", {}) if isinstance(source_chunk, Mapping) else {}
    if not isinstance(content, str) or not content.strip() or not isinstance(metadata, Mapping):
        return None if source_chunk is not None else _standalone_evidence(value)

    trusted_metadata = dict(metadata)
    if source_chunk.get("chunk_id") is not None:
        trusted_metadata["chunk_id"] = source_chunk["chunk_id"]
    source = trusted_metadata.get("source") or trusted_metadata.get("title")
    result: list[Evidence] = []
    for item in value:
        if not isinstance(item, Mapping):
            return None
        excerpt = item.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt.strip() or excerpt not in content:
            return None
        evidence: Evidence = {"excerpt": excerpt, "metadata": trusted_metadata}
        if isinstance(source, str):
            evidence["source"] = source
        result.append(evidence)
    return result


def _standalone_evidence(value: list[Any]) -> list[Evidence] | None:
    result: list[Evidence] = []
    for item in value:
        if not isinstance(item, Mapping) or not isinstance(item.get("excerpt"), str):
            return None
        if not item["excerpt"].strip():
            return None
        result.append(dict(item))
    return result or None


__all__ = ["REQUIRED_FIELDS", "RULE_FIELDS", "validate_policy_rule", "validate_policy_rules"]