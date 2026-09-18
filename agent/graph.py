"""Workflow construction and execution for the policy agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .nodes import (
    extract_rules_node,
    final_answer_node,
    policy_evaluation_node,
    retrieve_node,
)
from .state import AgentState


AgentWorkflow = Callable[[AgentState], AgentState]


def build_graph(
    vector_store: Any | None = None,
    top_k: int = 5,
) -> AgentWorkflow:
    """Build the current linear workflow without external dependencies."""

    def run(initial_state: AgentState) -> AgentState:
        state = retrieve_node(initial_state, vector_store=vector_store, top_k=top_k)
        state = extract_rules_node(state)
        state = policy_evaluation_node(state)
        return final_answer_node(state)

    return run


def run_agent(
    state: AgentState,
    vector_store: Any | None = None,
    top_k: int = 5,
) -> AgentState:
    """Run retrieval, extraction, evaluation, and answer generation in order."""

    return build_graph(vector_store=vector_store, top_k=top_k)(state)


__all__ = ["AgentWorkflow", "build_graph", "run_agent"]