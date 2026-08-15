from __future__ import annotations

import json
import unittest

from reference.ps.temporal_vectors import build_all_files


class Phase06JVectorTests(unittest.TestCase):
    def test_generated_files_are_byte_deterministic(self) -> None:
        first = build_all_files()
        self.assertEqual(first, build_all_files())
        golden = json.loads(first["golden-sequences.json"])
        self.assertEqual((10, 33, 1501), (
            golden["sequence_count"], golden["frame_count"], golden["candidate_records_checked"]
        ))
        self.assertEqual((64, 1352), (golden["maximum_active_tracks"], golden["maximum_candidates"]))

    def test_manifest_reuses_frozen_phase06i_packet_source(self) -> None:
        manifest = json.loads(build_all_files()["fixture-manifest.json"])
        self.assertEqual(
            "datasets/fixtures/phase06i/transport-packets.bin",
            manifest["frozen_phase06i_source"]["path"],
        )
        self.assertNotIn(":\\", json.dumps(manifest))


if __name__ == "__main__":
    unittest.main()
