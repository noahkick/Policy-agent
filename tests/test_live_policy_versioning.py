"""Focused tests for version metadata flowing from Markdown into the engine."""

from __future__ import annotations

import unittest
from pathlib import Path

from agent.ingestion import load_policy_documents
from agent.policy_store import PolicyStore
from agent.versioned_policy_engine import evaluate_policy


class LivePolicyVersioningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        policy_directory = Path(__file__).parents[1] / "data" / "policies"
        cls.documents = load_policy_documents(policy_directory)
        cls.store = PolicyStore()
        cls.store.add_documents(cls.documents)

    def _rule(
        self,
        *,
        version: str = "1.0",
        effective_date: str = "2026-01-01",
        effect: str = "ALLOW",
        policy_id: str = "LIVE-POLICY",
        scope: dict[str, str] | None = None,
    ) -> dict[str, object]:
        return {
            "policy_id": policy_id,
            "version": version,
            "effective_date": effective_date,
            "effect": effect,
            "action": "read",
            "evidence": [{"excerpt": "A live policy rule."}],
            "policy_scope": scope or {"region": "ALL", "department": "ALL", "vendor": "ALL"},
        }

    def test_live_markdown_metadata_reaches_policy_store(self) -> None:
        metadata = self.documents[0]["metadata"]
        self.assertEqual(metadata["policy_id"], "DEMO-DATA-ACCESS")
        self.assertEqual(metadata["version"], "1.0")
        self.assertEqual(metadata["effective_date"], "2026-01-15")
        self.assertEqual(metadata["region"], "ALL")
        self.assertEqual(metadata["department"], "ALL")
        self.assertEqual(metadata["vendor"], "ALL")

        retrieved = self.store.similarity_search("customer data access", k=1)
        self.assertEqual(retrieved[0]["metadata"]["policy_id"], "DEMO-DATA-ACCESS")

    def test_one_policy_version_is_evaluated(self) -> None:
        result = evaluate_policy(
            "read",
            [self._rule()],
            {"action": "read", "policy_date": "2026-06-01"},
        )
        self.assertEqual(result["status"], "ALLOW")

    def test_latest_effective_version_is_selected(self) -> None:
        rules = [
            self._rule(version="1.0", effective_date="2026-01-01", effect="DENY"),
            self._rule(version="2.0", effective_date="2026-04-01", effect="ALLOW"),
        ]
        result = evaluate_policy("read", rules, {"action": "read", "policy_date": "2026-06-01"})
        self.assertEqual(result["status"], "ALLOW")
        self.assertEqual(result["applicable_rules"][0]["version"], "2.0")

    def test_future_version_is_not_selected(self) -> None:
        rules = [
            self._rule(version="1.0", effective_date="2026-01-01", effect="DENY"),
            self._rule(version="2.0", effective_date="2027-01-01", effect="ALLOW"),
        ]
        result = evaluate_policy("read", rules, {"action": "read", "policy_date": "2026-06-01"})
        self.assertEqual(result["status"], "DENY")
        self.assertEqual(result["applicable_rules"][0]["version"], "1.0")

    def test_scope_matching_prefers_specific_policy(self) -> None:
        rules = [
            self._rule(effect="DENY"),
            self._rule(
                policy_id="EU-POLICY",
                effect="ALLOW",
                scope={"region": "EU", "department": "ALL", "vendor": "ALL"},
            ),
        ]
        result = evaluate_policy(
            "read",
            rules,
            {"action": "read", "region": "EU", "policy_date": "2026-06-01"},
        )
        self.assertEqual(result["status"], "ALLOW")

    def test_missing_rule_context_remains_unknown(self) -> None:
        result = evaluate_policy(
            "read",
            [self._rule()],
            {"policy_date": "2026-06-01"},
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("action", result["missing_context"])


if __name__ == "__main__":
    unittest.main()
