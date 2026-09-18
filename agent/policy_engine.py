"""Deterministic evaluation of structured policy rules."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, TypedDict

from .state import Evidence


class PolicyStatus(StrEnum):
    """Possible outcomes of policy evaluation."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class PolicyRule(TypedDict, total=False):
    """Structured rule produced by an upstream policy-extraction step."""

    action: str
    resource: str
    subject: str
    role: str
    location: str
    device: str
    vendor: str
    retention_period: Any
    required_approval: Any
    conditions: Mapping[str, Any]
    exception: Mapping[str, Any]
    effect: str
    reason: str
    evidence: list[Evidence]


class PolicyEvaluationResult(TypedDict):
    """State-compatible result returned by :func:`evaluate_policy`."""

    status: str
    reason: str
    applicable_rules: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    evidence: list[Evidence]


_MATCH_FIELDS = {
    "action",
    "resource",
    "subject",
    "role",
    "location",
    "device",
    "vendor",
    "retention_period",
    "required_approval",
}
_EFFECTS = {status.value for status in PolicyStatus}


def evaluate_policy(
    query: str,
    rules: list[Mapping[str, Any]] | None = None,
    situation: Mapping[str, Any] | None = None,
) -> PolicyEvaluationResult:
    """Evaluate structured rules against the supplied user situation.

    ``query`` is retained for workflow compatibility, but is deliberately not
    parsed here. Rule interpretation belongs to an upstream extraction node.
    A rule without conditions applies generally; a conditional rule requires
    every fact it names to be present in ``situation``.
    """

    del query
    if rules is None or not rules:
        return _result(PolicyStatus.UNKNOWN, "No policy rules were provided")

    facts = situation or {}
    applicable: list[dict[str, Any]] = []
    evidence: list[Evidence] = []
    unknown_rules: list[dict[str, Any]] = []
    invalid_rules: list[dict[str, Any]] = []

    for raw_rule in rules:
        if not isinstance(raw_rule, Mapping):
            invalid_rules.append({"rule": raw_rule, "reason": "rule is not a mapping"})
            continue

        rule = dict(raw_rule)
        effect = _normalise_effect(rule.get("effect"))
        if effect is None:
            invalid_rules.append({"rule": rule, "reason": "unsupported or missing effect"})
            continue

        match = _rule_matches(rule, facts)
        if match is None:
            unknown_rules.append(rule)
        elif match:
            applicable.append(rule)
            evidence.extend(_rule_evidence(rule))

    if invalid_rules:
        unknown_rules.extend(item["rule"] for item in invalid_rules)

    statuses = {_normalise_effect(rule.get("effect")) for rule in applicable}
    statuses.discard(None)
    if len(statuses) > 1 or PolicyStatus.CONFLICT.value in statuses:
        conflicts = [
            {"status": _normalise_effect(rule.get("effect")), "rule": rule}
            for rule in applicable
        ]
        return _result(
            PolicyStatus.CONFLICT,
            "Applicable policy rules produce different outcomes",
            applicable,
            conflicts,
            evidence,
        )

    if unknown_rules:
        return _result(
            PolicyStatus.UNKNOWN,
            "Required policy facts or rule information are missing",
            applicable + unknown_rules,
            [],
            evidence,
        )

    if not applicable:
        return _result(PolicyStatus.UNKNOWN, "No policy rule applies to the supplied situation")

    status = PolicyStatus(next(iter(statuses)))
    reason = "; ".join(
        str(rule.get("reason", f"Rule evaluated to {status.value}")) for rule in applicable
    )
    return _result(status, reason, applicable, [], evidence)


def _rule_matches(rule: Mapping[str, Any], facts: Mapping[str, Any]) -> bool | None:
    """Return true, false, or unknown for a rule/fact match."""

    expected: dict[str, Any] = {
        key: rule[key] for key in _MATCH_FIELDS if key in rule
    }
    conditions = rule.get("conditions", {})
    if conditions is not None:
        if not isinstance(conditions, Mapping):
            return None
        expected.update(conditions)

    for key, value in expected.items():
        if key not in facts:
            return None
        if facts[key] != value:
            return False

    exception = rule.get("exception")
    if exception is not None:
        if not isinstance(exception, Mapping):
            return None
        exception_match = _facts_match(exception, facts)
        if exception_match is None:
            return None
        if exception_match:
            return False
    return True


def _facts_match(expected: Mapping[str, Any], facts: Mapping[str, Any]) -> bool | None:
    for key, value in expected.items():
        if key not in facts:
            return None
        if facts[key] != value:
            return False
    return True


def _normalise_effect(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    effect = value.upper().strip()
    return effect if effect in _EFFECTS else None


def _rule_evidence(rule: Mapping[str, Any]) -> list[Evidence]:
    evidence = rule.get("evidence", [])
    if not isinstance(evidence, list):
        return []
    return [item for item in evidence if isinstance(item, Mapping)]


def _result(
    status: PolicyStatus,
    reason: str,
    applicable_rules: list[Mapping[str, Any]] | None = None,
    conflicts: list[dict[str, Any]] | None = None,
    evidence: list[Evidence] | None = None,
) -> PolicyEvaluationResult:
    return {
        "status": status.value,
        "reason": reason,
        "applicable_rules": [dict(rule) for rule in (applicable_rules or [])],
        "conflicts": conflicts or [],
        "evidence": evidence or [],
    }


__all__ = ["PolicyEvaluationResult", "PolicyRule", "PolicyStatus", "evaluate_policy"]