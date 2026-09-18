"""Tests for safe LLM rule extraction and deterministic evaluation."""

from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agent.llm import LLMExtractionError, extract_policy_rules
from agent.nodes import extract_rules_node, policy_evaluation_node
from agent.validation import validate_policy_rule


def _chunk(text: str, chunk_id: str = "policy.md#chunk-0") -> dict[str, object]:
    return {
        "content": text,
        "chunk_id": chunk_id,
        "metadata": {"source": "policy.md", "section": "Access"},
    }


def _model_response(payload: object) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(payload)),
            )
        ]
    )


class PolicyExtractionTests(unittest.TestCase):
    def test_successful_extraction_uses_configured_model(self) -> None:
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: _model_response(
                        {
                            "rules": [
                                {
                                    "action": "read",
                                    "resource": "customer data",
                                    "effect": "ALLOW",
                                    "evidence": [{"excerpt": "Read access is allowed."}],
                                }
                            ]
                        }
                    )
                )
            )
        )
        with patch.dict(os.environ, {"GROQ_MODEL": "test-model"}, clear=False):
            rules = extract_policy_rules(
                "Read access is allowed.",
                source_metadata={"source": "policy.md"},
                client=client,
            )
        self.assertEqual(rules[0]["effect"], "ALLOW")

    def test_empty_policy_text_does_not_call_api(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(extract_policy_rules("  "), [])

    def test_missing_api_key_is_controlled_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(LLMExtractionError, "GROQ_API_KEY"):
                extract_policy_rules("A policy rule")

    def test_malformed_model_response_is_rejected(self) -> None:
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: _model_response("not a rules object")
                )
            )
        )
        with self.assertRaises(LLMExtractionError):
            extract_policy_rules("A policy rule", client=client)

    def test_validation_rejects_invalid_rule_and_fabricated_evidence(self) -> None:
        self.assertIsNone(
            validate_policy_rule(
                {
                    "action": "read",
                    "resource": "customer data",
                    "effect": "MAYBE",
                    "evidence": [{"excerpt": "Read access is allowed."}],
                }
            )
        )
        self.assertIsNone(
            validate_policy_rule(
                {
                    "action": "read",
                    "resource": "customer data",
                    "effect": "ALLOW",
                    "conditions": "not an object",
                    "evidence": [{"excerpt": "Read access is allowed."}],
                },
                source_chunk=_chunk("Read access is allowed."),
            )
        )

    def test_multiple_chunks_preserve_source_and_chunk_metadata(self) -> None:
        first = _chunk("Read customer data is allowed.", "policy.md#chunk-0")
        second = _chunk("Write customer data is denied.", "policy.md#chunk-1")
        extracted = [
            [{"action": "read", "resource": "customer data", "effect": "ALLOW", "evidence": [{"excerpt": first["content"]}]}],
            [{"action": "write", "resource": "customer data", "effect": "DENY", "evidence": [{"excerpt": second["content"]}]}],
        ]
        with patch("agent.nodes.extract_policy_rules", side_effect=extracted):
            state = extract_rules_node({"relevant_chunks": [first, second]})
        rules = state["extracted_policies"]
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[1]["evidence"][0]["metadata"]["chunk_id"], "policy.md#chunk-1")
        self.assertEqual(rules[0]["evidence"][0]["source"], "policy.md")

    def test_extraction_failure_reaches_safe_unknown(self) -> None:
        with patch("agent.nodes.extract_policy_rules", side_effect=LLMExtractionError("API unavailable")):
            extracted = extract_rules_node({"relevant_chunks": [_chunk("Read access is allowed.")]})
        evaluated = policy_evaluation_node(extracted)
        self.assertEqual(evaluated["decision"], "UNKNOWN")
        self.assertIn("API unavailable", " ".join(extracted["warnings"]))

    def test_validated_rule_reaches_deterministic_engine(self) -> None:
        chunk = _chunk("Read customer data is allowed.")
        rule = {
            "action": "read",
            "resource": "customer data",
            "effect": "ALLOW",
            "conditions": {"role": "analyst"},
            "evidence": [{"excerpt": chunk["content"]}],
        }
        with patch("agent.nodes.extract_policy_rules", return_value=[rule]):
            extracted = extract_rules_node({"query": "Can I read customer data?", "relevant_chunks": [chunk], "execution_metadata": {"situation": {"action": "read", "resource": "customer data", "role": "analyst"}}})
        evaluated = policy_evaluation_node(extracted)
        self.assertEqual(evaluated["decision"], "ALLOW")
        self.assertEqual(evaluated["supporting_excerpts"][0]["source"], "policy.md")


if __name__ == "__main__":
    unittest.main()