"""Workflow nodes for the policy-agent pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .policy_engine import PolicyStatus, evaluate_policy
from .retriever import retrieve_documents
from .state import AgentState, Evidence


def retrieve_node(
    state: AgentState,
    vector_store: Any | None = None,
    top_k: int = 5,
) -> AgentState:
    """Retrieve policy chunks for the query and store them in shared state."""

    updated = dict(state)
    query = state.get("query")
    if not isinstance(query, str) or not query.strip():
        _add_error(updated, "A non-empty query is required for retrieval")
        updated["retrieved_documents"] = []
        updated["relevant_chunks"] = []
        updated["document_metadata"] = []
        return updated

    try:
        chunks = retrieve_documents(query, top_k=top_k, vector_store=vector_store)
    except Exception as exc:
        _add_error(updated, str(exc))
        updated["retrieved_documents"] = []
        updated["relevant_chunks"] = []
        updated["document_metadata"] = []
        return updated

    updated["retrieved_documents"] = chunks
    updated["relevant_chunks"] = chunks
    updated["document_metadata"] = [
        chunk["metadata"] for chunk in chunks if chunk.get("metadata")
    ]
    if not chunks:
        _add_warning(updated, "No relevant policy documents were retrieved")
    return updated


def extract_rules_node(state: AgentState) -> AgentState:
    """Pass through explicitly structured rules without interpreting text.

    Natural-language extraction is intentionally unavailable until the
    project provides an extractor or LLM utility. Retrieved chunks may still
    provide a ``rules`` or ``policy_rules`` list for deterministic integration.
    """

    updated = dict(state)
    existing = state.get("extracted_policies")
    if isinstance(existing, list) and existing:
        rules = [rule for rule in existing if isinstance(rule, Mapping)]
    else:
        rules = _rules_from_chunks(state.get("relevant_chunks", []))

    updated["extracted_policies"] = rules
    updated["applicable_rules"] = rules
    if not rules:
        _add_warning(
            updated,
            "Structured policy rules are unavailable; retrieved policy text was not interpreted",
        )
    return updated


def policy_evaluation_node(state: AgentState) -> AgentState:
    """Evaluate structured rules and write the result into shared state."""

    updated = dict(state)
    rules = state.get("applicable_rules") or state.get("extracted_policies") or []
    situation = _situation_from_state(state)
    try:
        result = evaluate_policy(state.get("query", ""), rules, situation)
    except Exception as exc:
        _add_error(updated, f"Policy evaluation failed: {exc}")
        result = {
            "status": PolicyStatus.UNKNOWN.value,
            "reason": "Policy evaluation could not be completed",
            "applicable_rules": [],
            "conflicts": [],
            "evidence": [],
        }

    updated["policy_evaluation_result"] = result
    updated["decision"] = result["status"]
    updated["decision_reasons"] = [result["reason"]]
    updated["conflicts"] = result["conflicts"]
    updated["supporting_excerpts"] = result["evidence"]
    return updated


def final_answer_node(state: AgentState) -> AgentState:
    """Create a conservative answer from the policy evaluation and evidence."""

    updated = dict(state)
    raw_result = state.get("policy_evaluation_result")
    result = raw_result if isinstance(raw_result, Mapping) else {}
    status = result.get("status", PolicyStatus.UNKNOWN.value)
    reason = result.get("reason", "Available policy information is insufficient")

    messages = {
        PolicyStatus.ALLOW.value: "The applicable policy rules allow the requested action.",
        PolicyStatus.DENY.value: "The applicable policy rules deny the requested action.",
        PolicyStatus.CONDITIONAL.value: "The requested action is allowed only conditionally.",
        PolicyStatus.UNKNOWN.value: "The available policy information is insufficient to determine the answer.",
        PolicyStatus.CONFLICT.value: "Multiple applicable policy rules produce conflicting outcomes.",
    }
    answer = f"{messages.get(status, messages[PolicyStatus.UNKNOWN.value])} {reason}."

    evidence = result.get("evidence", state.get("supporting_excerpts", []))
    evidence_lines = _evidence_lines(evidence)
    if evidence_lines:
        answer += "\n\nSupporting evidence:\n" + "\n".join(evidence_lines)
    else:
        answer += "\n\nNo supporting policy evidence was available."

    updated["final_answer"] = answer
    if status in {PolicyStatus.UNKNOWN.value, PolicyStatus.CONFLICT.value}:
        updated["uncertainty"] = reason
    return updated


def _rules_from_chunks(chunks: Any) -> list[Mapping[str, Any]]:
    if not isinstance(chunks, list):
        return []
    rules: list[Mapping[str, Any]] = []
    for chunk in chunks:
        if not isinstance(chunk, Mapping):
            continue
        candidates = chunk.get("rules", chunk.get("policy_rules", []))
        if isinstance(candidates, Mapping):
            candidates = [candidates]
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if isinstance(candidate, Mapping):
                rule = dict(candidate)
                if "evidence" not in rule:
                    evidence = _chunk_evidence(chunk)
                    if evidence:
                        rule["evidence"] = evidence
                rules.append(rule)
    return rules


def _chunk_evidence(chunk: Mapping[str, Any]) -> list[Evidence]:
    content = chunk.get("content")
    metadata = chunk.get("metadata", {})
    if not isinstance(content, str) or not content.strip() or not isinstance(metadata, Mapping):
        return []
    evidence: Evidence = {"excerpt": content, "metadata": dict(metadata)}
    source = metadata.get("source") or metadata.get("title")
    if isinstance(source, str):
        evidence["source"] = source
    return [evidence]


def _situation_from_state(state: AgentState) -> Mapping[str, Any]:
    execution_metadata = state.get("execution_metadata", {})
    if isinstance(execution_metadata, Mapping):
        situation = execution_metadata.get("situation")
        if isinstance(situation, Mapping):
            return situation
    analysis = state.get("intermediate_analysis")
    if isinstance(analysis, Mapping):
        situation = analysis.get("situation")
        if isinstance(situation, Mapping):
            return situation
    return {}


def _evidence_lines(evidence: Any) -> list[str]:
    if not isinstance(evidence, list):
        return []
    lines: list[str] = []
    for item in evidence:
        if not isinstance(item, Mapping) or not isinstance(item.get("excerpt"), str):
            continue
        reference = item.get("source")
        metadata = item.get("metadata")
        if not reference and isinstance(metadata, Mapping):
            reference = metadata.get("source") or metadata.get("title")
        suffix = f" ({reference})" if reference else ""
        lines.append(f"- {item['excerpt']}{suffix}")
    return lines


def _add_error(state: AgentState, message: str) -> None:
    errors = state.setdefault("errors", [])
    errors.append(message)


def _add_warning(state: AgentState, message: str) -> None:
    warnings = state.setdefault("warnings", [])
    warnings.append(message)


__all__ = [
    "extract_rules_node",
    "final_answer_node",
    "policy_evaluation_node",
    "retrieve_node",
]