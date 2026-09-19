"""Legacy adapter retained for the standalone policy-project test fixture.

The application canonical engine is ``agent.versioned_policy_engine``. This
package is not imported by the application and remains only for compatibility
with the original policy-project fixture.
"""

from policy_engine.loader import load_policies
from policy_engine.search import search_policy
from policy_engine.version import get_active_version
from policy_engine.scope import find_applicable_policies
from policy_engine.exceptions import find_exceptions
from policy_engine.conflicts import detect_conflicts
from policy_engine.evidence import get_evidence


class PolicyEngine:

    def __init__(self, path="data/policies.json"):
        self.policies = load_policies(path)

    def search(self, **kwargs):
        return search_policy(
            self.policies,
            **kwargs
        )

    def version(self, policy_id, requested_date):
        return get_active_version(
            self.policies,
            policy_id,
            requested_date
        )

    def scope(self, context):
        return find_applicable_policies(
            self.policies,
            context
        )

    def exceptions(self, **kwargs):
        return find_exceptions(
            self.policies,
            **kwargs
        )

    def conflicts(self, policies):
        return detect_conflicts(policies)

    def evidence(self, policies):
        return get_evidence(policies)