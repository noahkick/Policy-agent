"""Smoke-test the fictional policy corpus through ingestion and retrieval."""

from __future__ import annotations

from pathlib import Path

from agent.ingestion import load_policy_documents
from agent.policy_store import PolicyStore


QUESTIONS = (
    "Can I access customer data from my personal laptop?",
    "How long can customer data be retained?",
    "Can customer data be shared with an external vendor?",
    "Can this dataset be shared with an external vendor in India?",
    "Can I access customer data during an emergency?",
)


def main() -> None:
    policy_directory = Path(__file__).parents[1] / "data" / "policies"
    documents = load_policy_documents(policy_directory)
    sources = sorted({chunk["metadata"].get("source") for chunk in documents})
    chunk_ids = [chunk["chunk_id"] for chunk in documents]
    if len(sources) != 5 or len(set(chunk_ids)) != len(chunk_ids):
        raise RuntimeError("policy corpus did not produce five unique sources and chunk IDs")
    if any(not chunk.get("metadata", {}).get("section") for chunk in documents):
        raise RuntimeError("one or more policy chunks lack section metadata")

    store = PolicyStore()
    store.add_documents(documents)
    print(f"documents loaded: {len(sources)}")
    print(f"chunks generated: {len(documents)}")
    print(f"sources: {', '.join(sources)}")

    for question in QUESTIONS:
        results = store.similarity_search_with_score(question, k=5)
        result_sources = [item[0].get("metadata", {}).get("source") for item in results]
        print(f"\nquestion: {question}")
        print(f"multiple sources retrieved: {len(set(result_sources)) > 1}")
        for rank, (chunk, score) in enumerate(results, start=1):
            metadata = chunk.get("metadata", {})
            excerpt = " ".join(str(chunk.get("content", "")).split())[:180]
            print(
                f"{rank}. source={metadata.get('source')} score={score:.3f} "
                f"chunk={chunk.get('chunk_id')} section={metadata.get('section')}"
            )
            print(f"   evidence: {excerpt}")


if __name__ == "__main__":
    main()