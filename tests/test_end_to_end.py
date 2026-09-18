"""In-memory retrieval-to-decision integration tests."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.graph import run_agent
from agent.policy_store import PolicyStore


def _document(text: str, chunk_id: str) -> dict[str, object]:
    return {
        "content": text,
        "chunk_id": chunk_id,
        "metadata": {"source": f"{chunk_id}.md"},
    }


def _rule(effect: str, excerpt: str) -> dict[str, object]:
    return {
        "action": "share",
        "resource": "customer data",
        "effect": effect,
        "evidence": [{"excerpt": excerpt}],
    }


class EndToEndTests(unittest.TestCase):
    def _run(self, documents: list[dict[str, object]], rules: list[dict[str, object]]) -> dict[str, object]:
        store = PolicyStore()
        store.add_documents(documents)
        def extract_for_chunk(content: str, **_: object) -> list[dict[str, object]]:
            return [rule for rule in rules if rule["evidence"][0]["excerpt"] in content]

        with patch("agent.nodes.extract_policy_rules", side_effect=extract_for_chunk):
            return run_agent(
                {
                    "query": "Can I share customer data with a vendor?",
                    "execution_metadata": {
                        "situation": {
                            "action": "share",
                            "resource": "customer data",
                        }
                    },
                },
                vector_store=store,
            )

    def test_allow_decision_contains_retrieved_evidence(self) -> None:
        text = "Sharing customer data with a vendor is allowed."
        result = self._run([_document(text, "sharing")], [_rule("ALLOW", text)])
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["supporting_excerpts"][0]["excerpt"], text)

    def test_deny_decision(self) -> None:
        text = "Sharing customer data with a vendor is denied."
        result = self._run([_document(text, "sharing")], [_rule("DENY", text)])
        self.assertEqual(result["decision"], "DENY")

    def test_unknown_without_rules(self) -> None:
        text = "The policy discusses customer data handling."
        result = self._run([_document(text, "handling")], [])
        self.assertEqual(result["decision"], "UNKNOWN")

    def test_conflict_remains_deterministic(self) -> None:
        first = "Sharing customer data is allowed."
        second = "Sharing customer data is denied."
        result = self._run(
            [_document(first, "allow"), _document(second, "deny")],
            [_rule("ALLOW", first), _rule("DENY", second)],
        )
        self.assertEqual(result["decision"], "CONFLICT")
        self.assertEqual(len(result["conflicts"]), 2)


if __name__ == "__main__":
    unittest.main()