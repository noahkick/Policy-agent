"""Shared state passed between policy-agent workflow nodes."""

from __future__ import annotations

from typing import Any, TypedDict


class DocumentMetadata(TypedDict, total=False):
    """Metadata associated with a retrieved document or chunk."""

    document_id: str
    title: str
    source: str
    page: int
    section: str
    uri: str


class Evidence(TypedDict, total=False):
    """A source excerpt used to support an analysis or final answer."""

    source: str
    excerpt: str
    document_id: str
    page: int
    section: str
    metadata: DocumentMetadata


class AgentState(TypedDict, total=False):
    """Incrementally populated state shared by policy-agent nodes.

    Payloads whose concrete models are not present in this repository use
    ``Any`` so future retrieval and policy components can supply their own
    objects without this module introducing dependencies or business logic.
    """

    # User input and retrieval context.
    query: str
    retrieved_documents: list[Any]
    relevant_chunks: list[Any]
    document_metadata: list[DocumentMetadata]

    # Policy extraction and analysis.
    extracted_policies: list[Any]
    applicable_rules: list[Any]
    policy_conditions: list[Any]
    conflicts: list[Any]
    intermediate_analysis: Any

    # Policy-engine output.
    policy_evaluation_result: Any
    decision: str
    decision_reasons: list[str]

    # Evidence and final response.
    sources: list[Any]
    supporting_excerpts: list[Evidence]
    final_answer: str
    confidence: float
    uncertainty: str

    # Execution and diagnostics.
    errors: list[str]
    warnings: list[str]
    execution_metadata: dict[str, Any]


__all__ = ["AgentState", "DocumentMetadata", "Evidence"]