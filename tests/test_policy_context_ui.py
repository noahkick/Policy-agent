"""Focused tests for explicit action wording in the Streamlit context layer."""

from __future__ import annotations

import contextlib
import io
import unittest

with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from datetime import date

    from app import (
        _build_generated_question,
        _compose_display_output,
        _context_value,
        _situation_from_context,
    )


class PolicyContextQuestionTests(unittest.TestCase):
    def test_share_question_contains_action(self) -> None:
        question = _build_generated_question(
            {
                "Action": "Share",
                "Department": "HR",
                "Dataset / Data Type": "Financial Data",
                "Vendor": "Vendor X",
                "Region": "India",
            }
        )
        self.assertEqual(
            question,
            "Can the HR department share Financial Data with Vendor X in India?",
        )

    def test_access_question_contains_action(self) -> None:
        question = _build_generated_question(
            {
                "Action": "Access",
                "Role": "Employee",
                "Dataset / Data Type": "Financial Data",
                "Region": "India",
            }
        )
        self.assertEqual(question, "Can a Employee access Financial Data in India?")

    def test_retain_question_contains_action(self) -> None:
        question = _build_generated_question(
            {
                "Action": "Retain",
                "Department": "HR",
                "Dataset / Data Type": "Financial Data",
                "Region": "India",
            }
        )
        self.assertEqual(question, "Can the HR department retain Financial Data in India?")

    def test_missing_action_does_not_invent_one(self) -> None:
        question = _build_generated_question(
            {"Department": "HR", "Dataset / Data Type": "Financial Data"}
        )
        self.assertNotIn("share", question.casefold())
        self.assertNotIn("access", question.casefold())
        self.assertNotIn("retain", question.casefold())

    def test_mfa_selector_preserves_boolean_false(self) -> None:
        self.assertIs(_context_value("MFA", "Inactive"), False)
        self.assertIs(_context_value("MFA", "Active"), True)

    def test_ui_situation_builder_preserves_inactive_mfa(self) -> None:
        situation = _situation_from_context(
            {
                "Region": "India",
                "Department": "Analytics",
                "Role": "Analyst",
                "Dataset / Data Type": "Customer Data",
                "Action": "Access",
                "Device": "Corporate laptop",
                "MFA": "Inactive",
                "Purpose": "Reporting",
                "Required for assigned work": "Yes",
            },
            date(2026, 9, 19),
        )
        self.assertEqual(situation["mfa"], False)
        self.assertIs(type(situation["mfa"]), bool)
        self.assertEqual(situation["required_for_assigned_work"], True)

    def test_inactive_mfa_display_output_is_not_contradictory(self) -> None:
        evidence = [{
            "excerpt": "Analysts may access customer data from a corporate laptop with MFA.",
            "source": "data_access_policy.md",
        }]
        output = _compose_display_output(
            "The available policy information is insufficient to determine the answer. "
            "No policy rule applies to the supplied situation.\n\n"
            "No supporting policy evidence was available.",
            evidence,
        )
        self.assertNotIn("No supporting policy evidence was available", output)
        self.assertNotIn("No policy rule applies to the supplied situation", output)
        self.assertIn("Relevant policy rules were evaluated", output)
        self.assertIn("Analysts may access customer data", output)


if __name__ == "__main__":
    unittest.main()
