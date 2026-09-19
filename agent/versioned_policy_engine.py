"""Resolve versioned, JSON-structured policies to a single applicable decision.

This module handles a policy shape distinct from the markdown corpus used
elsewhere in this repo: each policy has a ``policy_id``, a ``version``, an
``effective_date``, scope fields (``region``, ``department``, ``vendor``, ...),
and a ``supersedes`` pointer to an older version of the same ``policy_id``.

Two problems have to be solved deterministically, without an LLM, so the
result is reproducible and free of rate limits during live grading:

1. **Version resolution** - for a given ``policy_id``, only the latest
   effective version should apply. A version whose ``effective_date`` is in
   the future, or that has been named in another version's ``supersedes``
   field, is inactive.
2. **Specificity resolution** - once every *currently effective* policy is
   known, several policy_ids may still apply to the same situation (e.g. a
   GLOBAL/ALL rule and a department+vendor-specific exception). The more
   specific policy - the one that names the actual region/department/vendor
   in the situation, rather than a wildcard like ``"ALL"`` or ``"GLOBAL"`` -
   wins. Ties are broken by the later ``effective_date``.

The wildcard values ``"ALL"`` and ``"GLOBAL"`` are treated as "applies to
everyone"; any other value must match the situation exactly to apply at all.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any, TypedDict

from .state import Evidence

WILDCARDS = {"ALL", "GLOBAL", "ANY", "*"}

# Fields on a policy record that scope it to a situation. Any of these not
# present on a record is treated as a wildcard (applies to everyone).
_SCOPE_FIELDS: tuple[str, ...] = ("region", "department", "vendor")

class PolicyResolutionError(ValueError):
    """Raised when the supplied policy records cannot be interpreted."""


@dataclass
class ResolvedDecision:
    """Outcome of resolving a set of versioned policies against a situation."""

    decision: str  # ALLOW | DENY | CONDITIONAL | ANSWER | UNKNOWN | CONFLICT
    reason: str
    winning_policy: dict[str, Any] | None
    all_applicable: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)


class PolicyStatus(StrEnum):
    """Possible outcomes of structured policy evaluation."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class PolicyRule(TypedDict, total=False):
    """Structured rule produced by the policy extraction step."""

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
    policy_id: str
    version: str
    effective_date: str
    policy_scope: Mapping[str, Any]


class PolicyEvaluationResult(TypedDict):
    """State-compatible result returned by :func:`evaluate_policy`."""

    status: str
    reason: str
    applicable_rules: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    evidence: list[Evidence]
    missing_context: list[str]


def load_policies(source: Sequence[Mapping[str, Any]] | str) -> list[dict[str, Any]]:
    """Accept either a parsed list of policy dicts or a path to a JSON file."""

    if isinstance(source, str):
        import json
        from pathlib import Path

        text = Path(source).read_text(encoding="utf-8")
        records = json.loads(text)
    else:
        records = source

    if not isinstance(records, list):
        raise PolicyResolutionError("policies.json must contain a JSON array")
    return [dict(record) for record in records]


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise PolicyResolutionError(f"invalid effective_date: {value!r}")
    return datetime.strptime(value, "%Y-%m-%d").date()


def current_versions(
    policies: Sequence[Mapping[str, Any]],
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    """Return only the currently-effective version of each ``policy_id``.

    A version is excluded if its ``effective_date`` is in the future, or if
    another version of the same ``policy_id`` names it in ``supersedes``.
    Among the remaining candidates for a ``policy_id``, the one with the
    latest ``effective_date`` wins.
    """

    reference_date = reference_date or date.today()

    by_id: dict[str, list[dict[str, Any]]] = {}
    for policy in policies:
        policy_id = policy.get("policy_id")
        if not policy_id:
            raise PolicyResolutionError(f"policy record missing policy_id: {policy!r}")
        by_id.setdefault(policy_id, []).append(dict(policy))

    superseded_versions: dict[str, set[str]] = {}
    for policy_id, versions in by_id.items():
        superseded_versions[policy_id] = {
            str(v["supersedes"]) for v in versions if v.get("supersedes")
        }

    resolved: list[dict[str, Any]] = []
    for policy_id, versions in by_id.items():
        eligible = [
            v
            for v in versions
            if _parse_date(v["effective_date"]) <= reference_date
            and str(v.get("version")) not in superseded_versions[policy_id]
        ]
        if not eligible:
            continue
        eligible.sort(key=lambda v: _parse_date(v["effective_date"]), reverse=True)
        resolved.append(eligible[0])

    return resolved


def _scope_matches(policy: Mapping[str, Any], situation: Mapping[str, Any]) -> bool:
    """A policy applies to a situation if every non-wildcard scope field matches."""

    for scope_field in _SCOPE_FIELDS:
        policy_value = policy.get(scope_field)
        if policy_value is None or str(policy_value).upper() in WILDCARDS:
            continue  # wildcard: applies regardless of situation
        situation_value = situation.get(scope_field)
        if situation_value is None:
            return False  # required fact missing from situation
        if str(situation_value).strip().lower() != str(policy_value).strip().lower():
            return False
    return True


def _specificity(policy: Mapping[str, Any]) -> int:
    """Count how many scope fields are non-wildcard (more = more specific)."""

    return sum(
        1
        for scope_field in _SCOPE_FIELDS
        if policy.get(scope_field) is not None
        and str(policy.get(scope_field)).upper() not in WILDCARDS
    )


def _missing_scope_facts(
    active: Sequence[Mapping[str, Any]], situation: Mapping[str, Any]
) -> list[str]:
    """Facts that, if supplied, could change which policy applies."""

    missing: list[str] = []
    for policy in active:
        for scope_field in _SCOPE_FIELDS:
            policy_value = policy.get(scope_field)
            if policy_value is None or str(policy_value).upper() in WILDCARDS:
                continue
            if scope_field not in situation:
                missing.append(scope_field)
    return sorted(set(missing))


def resolve(
    policies: Sequence[Mapping[str, Any]],
    situation: Mapping[str, Any],
    reference_date: date | None = None,
) -> ResolvedDecision:
    """Resolve the single applicable policy for ``situation`` and derive a decision.

    Resolution order:
    1. Drop superseded/not-yet-effective versions (per ``policy_id``).
    2. Drop policies whose named scope (region/department/vendor) does not
       match the situation.
    3. Among what is left, the most specific policy (most non-wildcard scope
       fields matching the situation) wins; ties are broken by the later
       ``effective_date``; unresolved ties are reported as a conflict.
    4. If a policy that could change the outcome exists but a required
       situation fact was not supplied, the result is UNKNOWN rather than a
       guess.
    """

    current = current_versions(policies, reference_date=reference_date)
    if not current:
        return ResolvedDecision(
            decision="UNKNOWN",
            reason="No currently effective policy version was found",
            winning_policy=None,
        )

    applicable = [policy for policy in current if _scope_matches(policy, situation)]
    missing = _missing_scope_facts(current, situation)

    if not applicable:
        reason = "No policy scope matches the supplied situation"
        if missing:
            reason += f"; missing facts that could change this: {', '.join(missing)}"
        return ResolvedDecision(
            decision="UNKNOWN",
            reason=reason,
            winning_policy=None,
            missing_context=missing,
        )

    ranked = sorted(
        applicable,
        key=lambda p: (_specificity(p), _parse_date(p["effective_date"])),
        reverse=True,
    )
    top_score = (_specificity(ranked[0]), _parse_date(ranked[0]["effective_date"]))
    tied = [p for p in ranked if (_specificity(p), _parse_date(p["effective_date"])) == top_score]

    if len(tied) > 1:
        return ResolvedDecision(
            decision="CONFLICT",
            reason="Multiple equally specific, equally current policies disagree",
            winning_policy=None,
            all_applicable=applicable,
            conflicts=tied,
        )

    winner = ranked[0]

    # If a less-specific policy is still in play and a scope fact that would
    # let a *more specific, currently inapplicable* policy activate is
    # missing, preserve uncertainty instead of committing to the general rule.
    more_specific_missing = [
        p
        for p in current
        if p not in applicable
        and _specificity(p) > _specificity(winner)
        and any(
            p.get(f) is not None
            and str(p.get(f)).upper() not in WILDCARDS
            and f not in situation
            for f in _SCOPE_FIELDS
        )
    ]
    if more_specific_missing:
        relevant_missing = sorted(
            {
                f
                for p in more_specific_missing
                for f in _SCOPE_FIELDS
                if p.get(f) is not None
                and str(p.get(f)).upper() not in WILDCARDS
                and f not in situation
            }
        )
        return ResolvedDecision(
            decision="UNKNOWN",
            reason=(
                "A more specific policy could apply but required context was "
                f"not supplied: {', '.join(relevant_missing)}"
            ),
            winning_policy=winner,
            all_applicable=applicable,
            missing_context=relevant_missing,
        )

    rules = _rules_from_policy(winner)
    if not rules:
        return ResolvedDecision(
            decision="UNKNOWN",
            reason=(
                "The applicable policy has no structured rule; policy text must "
                "be interpreted before deterministic evaluation"
            ),
            winning_policy=winner,
            all_applicable=applicable,
        )

    result = evaluate_policy("", rules, situation)
    reason = result["reason"]
    if winner.get("policy_id"):
        reason = f"{winner.get('policy_id')} v{winner.get('version')}: {reason}"

    return ResolvedDecision(
        decision=result["status"],
        reason=reason,
        winning_policy=winner,
        all_applicable=applicable,
        conflicts=result["conflicts"],
    )


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
    """Evaluate structured rules without interpreting natural-language text."""

    del query
    if not rules:
        return _evaluation_result(PolicyStatus.UNKNOWN, "No policy rules were provided")

    facts = situation or {}
    requested_action = facts.get("action")
    action_bearing_rules = any("action" in rule for rule in rules)
    if action_bearing_rules and (not isinstance(requested_action, str) or not requested_action.strip()):
        return _evaluation_result(
            PolicyStatus.UNKNOWN,
            "A policy action is required to evaluate the request",
            missing_context=["action"],
        )
    reference_date = _reference_date(facts)
    current_rules = _current_versioned_rules(rules, reference_date)
    if action_bearing_rules:
        current_rules = [
            rule
            for rule in current_rules
            if str(rule.get("action", "")).strip().casefold()
            == requested_action.strip().casefold()
        ]
    scoped_rules, missing_scope = _select_scoped_rules(current_rules, facts)
    if missing_scope:
        return _evaluation_result(
            PolicyStatus.UNKNOWN,
            "Required policy scope facts are missing",
            scoped_rules,
            evidence=_rules_evidence(scoped_rules),
            missing_context=missing_scope,
        )
    rules = scoped_rules
    if not rules:
        return _evaluation_result(
            PolicyStatus.UNKNOWN,
            "No policy rule applies to the supplied situation",
        )
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
        return _evaluation_result(
            PolicyStatus.CONFLICT,
            "Applicable policy rules produce different outcomes",
            applicable,
            conflicts,
            evidence,
        )

    if unknown_rules and not applicable:
        return _evaluation_result(
            PolicyStatus.UNKNOWN,
            "Required policy facts or rule information are missing",
            applicable + unknown_rules,
            evidence=evidence + _rules_evidence(unknown_rules),
            missing_context=_missing_rule_facts(unknown_rules, facts),
        )
    if not applicable:
        return _evaluation_result(
            PolicyStatus.UNKNOWN,
            "No policy rule applies to the supplied situation",
        )

    status = PolicyStatus(next(iter(statuses)))
    reason = "; ".join(
        str(rule.get("reason", f"Rule evaluated to {status.value}")) for rule in applicable
    )
    if unknown_rules:
        reason += (
            f" (Note: {len(unknown_rules)} other rule(s) could not be verified against "
            "the supplied context and may change this outcome if additional facts are provided.)"
        )
    return _evaluation_result(status, reason, applicable + unknown_rules, evidence=evidence)


def _rules_from_policy(policy: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rules = policy.get("rules", policy.get("policy_rules"))
    if isinstance(rules, Mapping):
        return [rules]
    if isinstance(rules, list):
        return [rule for rule in rules if isinstance(rule, Mapping)]
    if "effect" in policy:
        policy_metadata = {
            "policy_id",
            "version",
            "effective_date",
            "region",
            "department",
            "vendor",
            "supersedes",
            "content",
        }
        return [{key: value for key, value in policy.items() if key not in policy_metadata}]
    return []


def _rule_matches(rule: Mapping[str, Any], facts: Mapping[str, Any]) -> bool | None:
    expected = {key: rule[key] for key in _MATCH_FIELDS if key in rule}
    conditions = rule.get("conditions", {})
    if conditions is not None:
        if not isinstance(conditions, Mapping):
            return None
        expected.update(conditions)

    missing_fact = False
    for key, value in expected.items():
        if key not in facts:
            missing_fact = True
            continue
        if not _fact_values_equal(key, facts[key], value):
            return False
    if missing_fact:
        return None

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


def _reference_date(facts: Mapping[str, Any]) -> date:
    value = facts.get("policy_date", facts.get("reference_date"))
    if value is None:
        return date.today()
    return _parse_date(value)


def _current_versioned_rules(
    rules: Sequence[Mapping[str, Any]], reference_date: date
) -> list[Mapping[str, Any]]:
    unversioned: list[Mapping[str, Any]] = []
    versioned: dict[str, list[Mapping[str, Any]]] = {}
    for rule in rules:
        policy_id = rule.get("policy_id")
        if not policy_id or rule.get("effective_date") is None:
            unversioned.append(rule)
        else:
            versioned.setdefault(str(policy_id), []).append(rule)

    current = list(unversioned)
    for policy_rules in versioned.values():
        superseded = {
            str(rule["supersedes"])
            for rule in policy_rules
            if rule.get("supersedes") is not None
        }
        eligible = [
            rule
            for rule in policy_rules
            if _parse_date(rule["effective_date"]) <= reference_date
            and str(rule.get("version")) not in superseded
        ]
        if not eligible:
            continue
        latest_date = max(_parse_date(rule["effective_date"]) for rule in eligible)
        latest = [
            rule for rule in eligible if _parse_date(rule["effective_date"]) == latest_date
        ]
        current.extend(latest)
    return current


def _select_scoped_rules(
    rules: Sequence[Mapping[str, Any]], facts: Mapping[str, Any]
) -> tuple[list[Mapping[str, Any]], list[str]]:
    applicable: list[Mapping[str, Any]] = []
    missing: set[str] = set()
    for rule in rules:
        scope = rule.get("policy_scope", {})
        if not isinstance(scope, Mapping):
            scope = {}
        matches = True
        for field in _SCOPE_FIELDS:
            value = scope.get(field)
            if value is None or str(value).upper() in WILDCARDS:
                continue
            if field not in facts:
                missing.add(field)
                matches = False
                continue
            if str(facts[field]).strip().lower() != str(value).strip().lower():
                matches = False
        if matches:
            applicable.append(rule)

    if not applicable:
        return [], sorted(missing)

    highest_specificity = max(_rule_specificity(rule) for rule in applicable)
    return (
        [rule for rule in applicable if _rule_specificity(rule) == highest_specificity],
        [],
    )


def _rule_specificity(rule: Mapping[str, Any]) -> int:
    scope = rule.get("policy_scope", {})
    if not isinstance(scope, Mapping):
        return 0
    return sum(
        1
        for field in _SCOPE_FIELDS
        if scope.get(field) is not None and str(scope[field]).upper() not in WILDCARDS
    )


def _rules_evidence(rules: Sequence[Mapping[str, Any]]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for rule in rules:
        evidence.extend(_rule_evidence(rule))
    return evidence


def _facts_match(expected: Mapping[str, Any], facts: Mapping[str, Any]) -> bool | None:
    missing_fact = False
    for key, value in expected.items():
        if key not in facts:
            missing_fact = True
            continue
        if not _fact_values_equal(key, facts[key], value):
            return False
    if missing_fact:
        return None
    return True


def _fact_values_equal(key: str, actual: Any, expected: Any) -> bool:
    """Compare structured facts without changing their semantic values."""

    if not isinstance(actual, str) or not isinstance(expected, str):
        return actual == expected
    actual_text = actual.strip().casefold()
    expected_text = expected.strip().casefold()
    if key == "vendor":
        return _compact_vendor(actual_text) == _compact_vendor(expected_text)
    return actual_text == expected_text


def _compact_vendor(value: str) -> str:
    return value.replace("-", "").replace(" ", "").replace("_", "")


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


def _missing_rule_facts(
    rules: Sequence[Mapping[str, Any]], facts: Mapping[str, Any]
) -> list[str]:
    missing: set[str] = set()
    for rule in rules:
        expected = {key for key in _MATCH_FIELDS if key in rule}
        conditions = rule.get("conditions", {})
        if isinstance(conditions, Mapping):
            expected.update(conditions)
        missing.update(key for key in expected if key not in facts)
    return sorted(missing)


def _evaluation_result(
    status: PolicyStatus,
    reason: str,
    applicable_rules: list[Mapping[str, Any]] | None = None,
    conflicts: list[dict[str, Any]] | None = None,
    evidence: list[Evidence] | None = None,
    missing_context: list[str] | None = None,
) -> PolicyEvaluationResult:
    return {
        "status": status.value,
        "reason": reason,
        "applicable_rules": [dict(rule) for rule in (applicable_rules or [])],
        "conflicts": conflicts or [],
        "evidence": evidence or [],
        "missing_context": missing_context or [],
    }


__all__ = [
    "PolicyEvaluationResult",
    "PolicyRule",
    "PolicyResolutionError",
    "PolicyStatus",
    "ResolvedDecision",
    "current_versions",
    "evaluate_policy",
    "load_policies",
    "resolve",
]
