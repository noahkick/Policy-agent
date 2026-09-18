"""Integrity checks for the fictional demo policy corpus."""

from __future__ import annotations

import unittest
from pathlib import Path

from agent.ingestion import load_policy_documents


EXPECTED_FILES = {
    "data_access_policy.md",
    "data_retention_policy.md",
    "vendor_sharing_policy.md",
    "security_policy.md",
    "privacy_policy.md",
}


class PolicyCorpusTests(unittest.TestCase):
    def test_all_fictional_policy_documents_load_with_metadata(self) -> None:
        directory = Path(__file__).parents[1] / "data" / "policies"
        self.assertEqual({path.name for path in directory.glob("*.md")}, EXPECTED_FILES)
        self.assertTrue(all(path.stat().st_size > 0 for path in directory.glob("*.md")))

        chunks = load_policy_documents(directory)
        self.assertGreaterEqual(len(chunks), len(EXPECTED_FILES))
        self.assertEqual(
            {chunk["metadata"]["source"] for chunk in chunks}, EXPECTED_FILES
        )
        self.assertTrue(all(chunk.get("metadata", {}).get("section") for chunk in chunks))
        self.assertEqual(
            len({chunk["chunk_id"] for chunk in chunks}),
            len(chunks),
        )


if __name__ == "__main__":
    unittest.main()