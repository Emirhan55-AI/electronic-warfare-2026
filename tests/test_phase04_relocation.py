from __future__ import annotations

import unittest

from verification.phase04_relocation import archived_implementation_digest, load_relocation_manifest


class Phase04RelocationTests(unittest.TestCase):
    def test_manifest_binds_all_archived_parameter_runs(self) -> None:
        document = load_relocation_manifest()
        entries = {item["artifact_id"]: item for item in document["artifacts"]}
        self.assertEqual({"phase04-r1", "phase04-r2", "phase04-e1"}, set(entries))
        for artifact_id, entry in entries.items():
            self.assertEqual(
                entry["historical_implementation_manifest_sha256"],
                archived_implementation_digest(
                    artifact_id,
                    entry["historical_implementation_manifest_sha256"],
                ),
            )

    def test_digest_mismatch_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            archived_implementation_digest("phase04-r2", "0" * 64)


if __name__ == "__main__":
    unittest.main()
