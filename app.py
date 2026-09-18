"""Streamlit entry point for the local policy agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

from agent.graph import run_agent
from agent.ingestion import load_policy_documents
from agent.policy_store import PolicyStore


POLICY_DIRECTORY = Path(__file__).parent / "data" / "policies"


def _load_policy_store() -> tuple[PolicyStore | None, list[dict[str, Any]]]:
    """Load the checked-in policy corpus without hiding filesystem errors."""

    if not POLICY_DIRECTORY.is_dir():
        return None, []
    try:
        documents = load_policy_documents(POLICY_DIRECTORY)
    except Exception as exc:
        st.error(f"Policy documents could not be loaded: {exc}")
        return None, []
    if not documents:
        return None, []
    store = PolicyStore()
    store.add_documents(documents)
    return store, documents


def _situation_from_inputs(values: dict[str, str]) -> dict[str, str]:
    return {key: value.strip() for key, value in values.items() if value.strip()}


def _show_evidence(evidence: Any) -> None:
    if not isinstance(evidence, list) or not evidence:
        st.info("No supporting policy evidence was returned.")
        return
    for item in evidence:
        if not isinstance(item, dict):
            continue
        excerpt = item.get("excerpt")
        metadata = item.get("metadata", {})
        source = item.get("source")
        if not source and isinstance(metadata, dict):
            source = metadata.get("source") or metadata.get("title")
        label = f" ({source})" if source else ""
        if isinstance(excerpt, str):
            st.markdown(f"- {excerpt}{label}")


def main() -> None:
    st.set_page_config(page_title="Policy Agent", page_icon="P", layout="wide")
    st.title("Policy Agent")
    st.caption("Evidence-backed policy evaluation")

    if not os.getenv("OPENAI_API_KEY", "").strip():
        st.warning(
            "OPENAI_API_KEY is not configured. Rule extraction will be unavailable "
            "and the safe result will be UNKNOWN."
        )

    store, documents = _load_policy_store()
    if store is None:
        st.error(
            "No policy documents are available. Restore the data/policies directory "
            "before running an analysis."
        )
        return

    st.caption(f"Loaded {len(documents)} policy chunk(s) from data/policies/")
    with st.form("policy_question"):
        question = st.text_area(
            "Policy question",
            placeholder="Can I access customer data from my personal laptop?",
            height=100,
        )
        st.subheader("Optional context")
        first, second = st.columns(2)
        with first:
            role = st.text_input("Role")
            action = st.text_input("Action")
            resource = st.text_input("Resource or data type")
            location = st.text_input("Region or location")
        with second:
            vendor = st.text_input("Vendor")
            device = st.text_input("Device or access method")
            department = st.text_input("Department")
            required_approval = st.text_input("Required approval")
        submitted = st.form_submit_button("Evaluate policy")

    if not submitted:
        return
    if not question.strip():
        st.warning("Enter a natural-language policy question.")
        return

    situation = _situation_from_inputs(
        {
            "role": role,
            "action": action,
            "resource": resource,
            "location": location,
            "vendor": vendor,
            "device": device,
            "department": department,
            "required_approval": required_approval,
        }
    )
    result = run_agent(
        {
            "query": question.strip(),
            "execution_metadata": {"situation": situation},
        },
        vector_store=store,
    )

    decision = result.get("decision", "UNKNOWN")
    st.subheader(f"Decision: {decision}")
    st.write(result.get("final_answer", "No answer was returned."))

    evidence = result.get("supporting_excerpts", [])
    with st.expander("Evidence", expanded=True):
        _show_evidence(evidence)

    with st.expander("Retrieved policy chunks"):
        for chunk in result.get("relevant_chunks", []):
            if isinstance(chunk, dict):
                st.markdown(f"**{chunk.get('metadata', {}).get('source', 'Policy')}**")
                st.write(chunk.get("content", ""))

    conflicts = result.get("conflicts", [])
    if conflicts:
        with st.expander("Conflicts", expanded=True):
            st.json(conflicts)

    warnings = result.get("warnings", [])
    errors = result.get("errors", [])
    if warnings:
        st.warning("\n".join(str(item) for item in warnings))
    if errors:
        st.error("\n".join(str(item) for item in errors))


if __name__ == "__main__":
    main()