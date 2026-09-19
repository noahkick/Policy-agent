"""Tests for the deterministic demo-rule fallback path."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.llm import LLMExtractionError
from agent.nodes import extract_rules_node, policy_evaluation_node


_POLICY_METADATA = {
    "source": "vendor_sharing_policy.md",
    "section": "Explicit Vendor Exception",
    "policy_id": "DEMO-VENDOR-SHARING",
    "version": "1.0",
    "effective_date": "2026-03-01",
    "scope": "region=ALL; department=ALL; vendor=ALL",
    "region": "ALL",
    "department": "ALL",
    "vendor": "ALL",
}
_CHUNK_CONTENT = "Vendor-X is not approved for customer data sharing."


def _chunk(metadata: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "content": _CHUNK_CONTENT,
        "chunk_id": "vendor_sharing_policy.md#chunk-0",
        "metadata": metadata or _POLICY_METADATA,
    }


def _llm_rule(effect: str = "ALLOW") -> dict[str, object]:
    return {
        "action": "share",
        "resource": "customer data",
        "effect": effect,
        "evidence": [{"excerpt": _CHUNK_CONTENT}],
    }


class DemoFallbackTests(unittest.TestCase):
    def test_successful_llm_extraction_wins_over_cache(self) -> None:
        with patch("agent.nodes.extract_policy_rules", return_value=[_llm_rule("ALLOW")]):
            result = extract_rules_node({"relevant_chunks": [_chunk()]})

        self.assertEqual(result["extraction_source"], "llm")
        self.assertEqual(result["extracted_policies"][0]["effect"], "ALLOW")

    def test_api_failure_uses_matching_cached_rule(self) -> None:
        with patch(
            "agent.nodes.extract_policy_rules",
            side_effect=LLMExtractionError("quota exhausted"),
        ):
            result = extract_rules_node({"relevant_chunks": [_chunk()]})

        self.assertEqual(result["extraction_source"], "cached_demo")
        self.assertTrue(result["extracted_policies"])
        self.assertNotIn("quota exhausted", " ".join(result["warnings"]))

    def test_failure_without_cache_remains_unknown(self) -> None:
        metadata = dict(_POLICY_METADATA)
        metadata["policy_id"] = "UNSUPPORTED-DEMO-POLICY"
        with patch(
            "agent.nodes.extract_policy_rules",
            side_effect=LLMExtractionError("API unavailable"),
        ):
            result = extract_rules_node({"relevant_chunks": [_chunk(metadata)]})

        evaluated = policy_evaluation_node(result)
        self.assertEqual(result["extraction_source"], "unavailable")
        self.assertEqual(evaluated["decision"], "UNKNOWN")
        self.assertFalse(result["extracted_policies"])

    def test_cached_rule_reaches_canonical_engine(self) -> None:
        with patch(
            "agent.nodes.extract_policy_rules",
            side_effect=LLMExtractionError("temporary failure"),
        ):
            extracted = extract_rules_node({"relevant_chunks": [_chunk()]})
        evaluated = policy_evaluation_node(
            {
                **extracted,
                "execution_metadata": {
                    "situation": {
                        "action": "share",
                        "resource": "customer data",
                        "vendor": "Vendor-X",
                        "policy_date": "2026-06-01",
                    }
                },
            }
        )
        self.assertEqual(evaluated["decision"], "DENY")

    def test_cached_rule_preserves_policy_metadata(self) -> None:
        with patch(
            "agent.nodes.extract_policy_rules",
            side_effect=LLMExtractionError("temporary failure"),
        ):
            result = extract_rules_node({"relevant_chunks": [_chunk()]})

        rule = result["extracted_policies"][0]
        self.assertEqual(rule["policy_id"], "DEMO-VENDOR-SHARING")
        self.assertEqual(rule["version"], "1.0")
        self.assertEqual(rule["effective_date"], "2026-03-01")
        self.assertEqual(rule["policy_scope"]["region"], "ALL")
        self.assertEqual(rule["evidence"][0]["source"], "vendor_sharing_policy.md")

    def test_unknown_policy_id_does_not_invent_a_rule(self) -> None:
        metadata = dict(_POLICY_METADATA)
        metadata["policy_id"] = "NOT-IN-DEMO-CACHE"
        with patch(
            "agent.nodes.extract_policy_rules",
            side_effect=LLMExtractionError("temporary failure"),
        ):
            result = extract_rules_node({"relevant_chunks": [_chunk(metadata)]})

        self.assertEqual(result["extraction_source"], "unavailable")
        self.assertEqual(result["extracted_policies"], [])


if __name__ == "__main__":
    unittest.main()
