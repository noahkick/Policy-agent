"""Workflow nodes for the policy-agent pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .demo_policy_cache import cached_rules_for_metadata
from .llm import LLMExtractionError, extract_policy_rules
from .versioned_policy_engine import PolicyStatus, evaluate_policy
from .retriever import retrieve_documents
from .state import AgentState, Evidence
from .validation import validate_policy_rules


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
    """Extract and validate rules from retrieved policy chunks."""

    updated = dict(state)
    extraction_sources: set[str] = set()
    existing = state.get("extracted_policies")
    if isinstance(existing, list) and existing:
        rules = validate_policy_rules(existing)
        extraction_sources.add("provided")
        if len(rules) != len(existing):
            _add_warning(updated, "Some existing policy rules failed validation")
    else:
        rules = []
        cached_policy_ids: set[str] = set()
        chunks = state.get("relevant_chunks", [])
        if isinstance(chunks, list):
            for chunk in chunks:
                if not isinstance(chunk, Mapping):
                    continue
                content = chunk.get("content")
                if not isinstance(content, str) or not content.strip():
                    continue

                structured = chunk.get("rules", chunk.get("policy_rules"))
                if structured is not None:
                    candidates = [structured] if isinstance(structured, Mapping) else structured
                    candidates = _attach_chunk_evidence(candidates, chunk)
                    extraction_sources.add("provided")
                else:
                    try:
                        candidates = extract_policy_rules(
                            content,
                            source_metadata=chunk.get("metadata", {}),
                        )
                        extraction_sources.add("llm")
                    except LLMExtractionError as exc:
                        metadata = chunk.get("metadata", {})
                        policy_id = metadata.get("policy_id") if isinstance(metadata, Mapping) else None
                        candidates = []
                        if policy_id not in cached_policy_ids and isinstance(metadata, Mapping):
                            candidates = cached_rules_for_metadata(metadata)
                        if candidates:
                            cached_policy_ids.add(policy_id)
                            candidates = _attach_chunk_evidence(candidates, chunk)
                            extraction_sources.add("cached_demo")
                            _add_warning(updated, "LLM extraction unavailable; used cached demo rules")
                        else:
                            _add_warning(updated, "Structured policy rules unavailable for a retrieved policy")
                            continue
                    except Exception as exc:
                        metadata = chunk.get("metadata", {})
                        policy_id = metadata.get("policy_id") if isinstance(metadata, Mapping) else None
                        candidates = []
                        if policy_id not in cached_policy_ids and isinstance(metadata, Mapping):
                            candidates = cached_rules_for_metadata(metadata)
                        if candidates:
                            cached_policy_ids.add(policy_id)
                            candidates = _attach_chunk_evidence(candidates, chunk)
                            extraction_sources.add("cached_demo")
                            _add_warning(updated, "LLM extraction unavailable; used cached demo rules")
                        else:
                            _add_warning(updated, "Structured policy rules unavailable for a retrieved policy")
                            continue

                validated = validate_policy_rules(candidates, source_chunk=chunk)
                if candidates and not validated:
                    _add_warning(updated, "LLM returned no reliable policy rules for a retrieved chunk")
                rules.extend(_attach_policy_metadata(validated, chunk))

    updated["extracted_policies"] = rules
    updated["applicable_rules"] = rules
    if not extraction_sources:
        updated["extraction_source"] = "unavailable"
    elif len(extraction_sources) == 1:
        updated["extraction_source"] = next(iter(extraction_sources))
    else:
        updated["extraction_source"] = "mixed"
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
            "missing_context": [],
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


def _attach_chunk_evidence(candidates: Any, chunk: Mapping[str, Any]) -> Any:
    """Give legacy structured rules trusted evidence before validation."""

    if isinstance(candidates, Mapping):
        candidates = [candidates]
    if not isinstance(candidates, list):
        return candidates
    evidence = _chunk_evidence(chunk)
    result: list[Any] = []
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            rule = dict(candidate)
            if "evidence" not in rule and evidence:
                rule["evidence"] = evidence
            result.append(rule)
        else:
            result.append(candidate)
    return result


def _attach_policy_metadata(
    rules: list[dict[str, Any]], chunk: Mapping[str, Any]
) -> list[dict[str, Any]]:
    metadata = chunk.get("metadata", {})
    if not isinstance(metadata, Mapping):
        return rules

    policy_fields = ("policy_id", "version", "effective_date")
    scope_fields = ("region", "department", "vendor")
    policy_scope = {
        field: metadata[field]
        for field in scope_fields
        if metadata.get(field) is not None
    }
    enriched: list[dict[str, Any]] = []
    for candidate in rules:
        rule = dict(candidate)
        for field in policy_fields:
            if metadata.get(field) is not None:
                rule[field] = metadata[field]
        if policy_scope:
            rule["policy_scope"] = policy_scope
        enriched.append(rule)
    return enriched


def _chunk_evidence(chunk: Mapping[str, Any]) -> list[Evidence]:
    content = chunk.get("content")
    metadata = chunk.get("metadata", {})
    if not isinstance(content, str) or not content.strip() or not isinstance(metadata, Mapping):
        return []
    evidence_metadata = dict(metadata)
    if chunk.get("chunk_id") is not None:
        evidence_metadata["chunk_id"] = chunk["chunk_id"]
    evidence: Evidence = {"excerpt": content, "metadata": evidence_metadata}
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