"""Pre-extracted rules for the checked-in demo policy corpus.

These rules mirror only statements that are explicitly structured in the
bundled Markdown policies. They are used solely when extraction is unavailable
and are still validated and evaluated by the normal policy pipeline.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


CACHED_DEMO_RULES: dict[str, tuple[dict[str, Any], ...]] = {
    "DEMO-DATA-ACCESS": (
        {
            "action": "access",
            "resource": "customer data",
            "effect": "ALLOW",
            "conditions": {
                "device": "corporate laptop",
                "mfa": "active",
            },
        },
        {
            "action": "access",
            "resource": "customer data",
            "effect": "ALLOW",
            "conditions": {
                "device": "personal laptop",
                "role": "approved remote-work pilot participant",
                "pilot_manager_approval": True,
                "managed_browser_profile": True,
                "mfa": "active",
            },
        },
    ),
    "DEMO-DATA-RETENTION": (
        {
            "action": "retain",
            "resource": "customer data",
            "effect": "ALLOW",
            "conditions": {"retention_period": 365},
        },
        {
            "action": "retain",
            "resource": "support case data",
            "effect": "ALLOW",
            "conditions": {"retention_period": 180},
        },
        {
            "action": "retain",
            "resource": "customer data",
            "effect": "ALLOW",
            "conditions": {"location": "EU", "retention_period": 30},
        },
    ),
    "DEMO-VENDOR-SHARING": (
        {
            "action": "share",
            "resource": "customer data",
            "effect": "ALLOW",
            "conditions": {
                "vendor": "approved vendor",
                "business_purpose": "documented",
            },
        },
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
    ),
    "DEMO-SECURITY-DEVICE": (
        {
            "action": "access",
            "resource": "customer data",
            "effect": "DENY",
            "conditions": {"device": "personal laptop"},
        },
        {
            "action": "access",
            "resource": "customer data",
            "effect": "ALLOW",
            "conditions": {
                "device": "corporate laptop",
                "mfa": "active",
            },
        },
        {
            "action": "access",
            "resource": "customer data",
            "effect": "DENY",
            "conditions": {"mfa": "inactive"},
        },
    ),
}

CACHED_DEMO_METADATA = {
    "DEMO-DATA-ACCESS": ("1.0", "2026-01-15"),
    "DEMO-DATA-RETENTION": ("1.0", "2026-02-01"),
    "DEMO-VENDOR-SHARING": ("1.0", "2026-03-01"),
    "DEMO-SECURITY-DEVICE": ("1.0", "2026-01-20"),
}


def cached_rules_for_metadata(metadata: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return a copy of cached rules for one matching demo policy version."""

    policy_id = metadata.get("policy_id")
    version = metadata.get("version")
    effective_date = metadata.get("effective_date")
    if not isinstance(policy_id, str) or not isinstance(version, str):
        return []
    if not isinstance(effective_date, str):
        return []
    if CACHED_DEMO_METADATA.get(policy_id) != (version, effective_date):
        return []
    return [dict(rule) for rule in CACHED_DEMO_RULES.get(policy_id, ())]


__all__ = ["CACHED_DEMO_RULES", "cached_rules_for_metadata"]
