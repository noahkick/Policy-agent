import unittest

from policy_engine.engine import PolicyEngine


class TestPolicyEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = PolicyEngine()

    def test_version(self):
        result = self.engine.version(
            "DATA-SHARING",
            "2026-09-18"
        )

        self.assertIsNotNone(result)

        if result is not None:
            self.assertEqual(result["version"], "5.0")

    def test_eu_support_scope(self):
        results = self.engine.scope({
            "region": "EU",
            "department": "Support"
        })

        self.assertGreater(len(results), 0)

        score, policy = results[0]

        self.assertEqual(
            policy["policy_id"],
            "EU-RETENTION"
        )

        self.assertEqual(score, 4)

    def test_vendor_exception(self):
        results = self.engine.exceptions(
            vendor="Vendor-X",
            department="Analytics",
            dataset="Dataset Y"
        )

        self.assertGreater(len(results), 0)

        self.assertEqual(
            results[0]["policy_id"],
            "VENDOR-EXCEPTION"
        )


if __name__ == "__main__":
    unittest.main()
