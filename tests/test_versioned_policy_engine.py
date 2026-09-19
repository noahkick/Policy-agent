"""Tests for the canonical versioned policy engine."""

from __future__ import annotations

import unittest

from agent.versioned_policy_engine import evaluate_policy, resolve


class VersionedPolicyEngineTests(unittest.TestCase):
    def test_structured_effect_controls_resolution(self) -> None:
        result = resolve(
            [
                {
                    "policy_id": "SHARING",
                    "version": "1.0",
                    "effective_date": "2024-01-01",
                    "region": "GLOBAL",
                    "department": "ALL",
                    "vendor": "ALL",
                    "effect": "DENY",
                    "content": "This wording says allowed, but is not authoritative.",
                }
            ],
            {},
        )
        self.assertEqual(result.decision, "DENY")

    def test_unstructured_policy_text_is_unknown(self) -> None:
        result = resolve(
            [
                {
                    "policy_id": "SHARING",
                    "version": "1.0",
                    "effective_date": "2024-01-01",
                    "region": "GLOBAL",
                    "department": "ALL",
                    "vendor": "ALL",
                    "content": "External sharing is allowed.",
                }
            ],
            {},
        )
        self.assertEqual(result.decision, "UNKNOWN")

    def test_structured_evaluation_preserves_exception_and_evidence(self) -> None:
        evidence = [{"excerpt": "Read access is allowed."}]
        result = evaluate_policy(
            "ignored query",
            [
                {
                    "action": "read",
                    "resource": "customer data",
                    "effect": "ALLOW",
                    "conditions": {"role": "analyst"},
                    "exception": {"device": "unmanaged"},
                    "evidence": evidence,
                }
            ],
            {"action": "read", "resource": "customer data", "role": "analyst", "device": "managed"},
        )
        self.assertEqual(result["status"], "ALLOW")
        self.assertEqual(result["evidence"], evidence)

    def test_unknown_evaluation_reports_missing_context(self) -> None:
        result = evaluate_policy(
            "ignored query",
            [{"action": "read", "effect": "ALLOW", "conditions": {"role": "analyst"}}],
            {"action": "read"},
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["missing_context"], ["role"])

    def test_missing_action_is_reported_explicitly(self) -> None:
        result = evaluate_policy(
            "vague request",
            [{"action": "share", "resource": "customer data", "effect": "ALLOW"}],
            {"resource": "customer data"},
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["missing_context"], ["action"])

    def test_action_filter_excludes_unrelated_rule_conditions(self) -> None:
        result = evaluate_policy(
            "access request",
            [
                {
                    "action": "access",
                    "resource": "customer data",
                    "effect": "ALLOW",
                    "conditions": {"device": "corporate laptop", "mfa": "active"},
                },
                {
                    "action": "share",
                    "resource": "customer data",
                    "effect": "ALLOW",
                    "conditions": {"vendor": "approved vendor", "business_purpose": "documented"},
                },
            ],
            {"action": "access", "resource": "customer data"},
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(set(result["missing_context"]), {"device", "mfa"})
        self.assertNotIn("vendor", result["missing_context"])
        self.assertNotIn("business_purpose", result["missing_context"])

    def test_analyst_access_ignores_support_agent_case_fields(self) -> None:
        result = evaluate_policy(
            "analyst access",
            [
                {
                    "action": "access",
                    "resource": "customer data",
                    "role": "Analyst",
                    "effect": "ALLOW",
                    "conditions": {"device": "corporate laptop", "mfa": True},
                },
                {
                    "action": "access",
                    "resource": "customer data",
                    "role": "Support agent",
                    "effect": "ALLOW",
                    "conditions": {"case_status": "active customer case"},
                },
            ],
            {
                "action": "access",
                "resource": "Customer Data",
                "role": "Analyst",
                "device": "corporate laptop",
                "mfa": True,
            },
        )
        self.assertEqual(result["status"], "ALLOW")
        self.assertNotIn("case_status", result["missing_context"])

    def test_support_agent_access_still_requires_active_case(self) -> None:
        result = evaluate_policy(
            "support access",
            [
                {
                    "action": "access",
                    "resource": "customer data",
                    "role": "Support agent",
                    "effect": "ALLOW",
                    "conditions": {"case_status": "active customer case"},
                }
            ],
            {"action": "access", "resource": "customer data", "role": "Support agent"},
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["missing_context"], ["case_status"])

    def test_matching_role_with_missing_facts_remains_unknown(self) -> None:
        result = evaluate_policy(
            "analyst access",
            [
                {
                    "action": "access",
                    "resource": "customer data",
                    "role": "Analyst",
                    "effect": "ALLOW",
                    "conditions": {"device": "corporate laptop", "mfa": True},
                }
            ],
            {"action": "access", "resource": "customer data", "role": "Analyst"},
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(set(result["missing_context"]), {"device", "mfa"})

    def test_unknown_access_result_preserves_rule_evidence(self) -> None:
        evidence = [{"excerpt": "Access requires a corporate laptop and MFA."}]
        result = evaluate_policy(
            "access request",
            [
                {
                    "action": "access",
                    "resource": "customer data",
                    "effect": "ALLOW",
                    "conditions": {"device": "corporate laptop", "mfa": "active"},
                    "evidence": evidence,
                }
            ],
            {"action": "access", "resource": "customer data"},
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["evidence"], evidence)

    def test_share_and_retain_rules_remain_action_filtered(self) -> None:
        rules = [
            {
                "action": "share",
                "resource": "customer data",
                "effect": "ALLOW",
                "conditions": {"vendor": "approved vendor"},
            },
            {
                "action": "retain",
                "resource": "customer data",
                "effect": "ALLOW",
                "conditions": {"retention_period": 365},
            },
        ]
        share = evaluate_policy("share", rules, {"action": "share", "resource": "customer data"})
        retain = evaluate_policy("retain", rules, {"action": "retain", "resource": "customer data"})
        self.assertEqual(share["missing_context"], ["vendor"])
        self.assertEqual(retain["missing_context"], ["retention_period"])

    def test_vendor_x_share_selects_vendor_specific_denial(self) -> None:
        rules = [
            {
                "action": "share",
                "resource": "customer data",
                "effect": "CONDITIONAL",
                "conditions": {
                    "vendor": "approved vendor",
                    "location": "cross-border",
                    "required_approval": "Data Protection Officer",
                },
            },
            {
                "action": "share",
                "resource": "customer data",
                "effect": "DENY",
                "conditions": {"vendor": "Vendor-X"},
            },
        ]
        result = evaluate_policy(
            "Can the Analytics department share Customer Data with Vendor X in India?",
            rules,
            {
                "action": "share",
                "resource": "Customer Data",
                "vendor": "Vendor X",
                "region": "India",
                "policy_date": "2026-09-19",
            },
        )
        self.assertEqual(result["status"], "DENY")
        self.assertEqual(result["applicable_rules"][0]["conditions"]["vendor"], "Vendor-X")

    def test_unsupported_resource_is_not_rewritten(self) -> None:
        result = evaluate_policy(
            "access financial data",
            [{"action": "access", "resource": "customer data", "effect": "ALLOW"}],
            {"action": "access", "resource": "Financial Data"},
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertNotIn("customer data", result["missing_context"])


if __name__ == "__main__":
    unittest.main()