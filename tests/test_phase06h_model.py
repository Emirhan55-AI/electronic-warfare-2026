from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from reference.detection.cfar import CellDetectionResult
from reference.detection.pipeline import DetectionPipeline
from reference.rtl.candidate_grouping import (
    HALF_MAX_CANDIDATES,
    MAX_CANDIDATES,
    axis_candidate_records,
    group_detector_cells,
)
from reference.rtl.candidate_vectors import grouping_vectors


class Phase06HModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = {vector.vector_id: vector for vector in grouping_vectors()}

    def test_authoritative_phase03_grouping_matches_hardware_oriented_model(self) -> None:
        pipeline = object.__new__(DetectionPipeline)
        pipeline.max_gap_bins = 1
        for vector in self.vectors.values():
            if vector.source.startswith("frozen"):
                continue
            shifted = sorted(vector.cells, key=lambda item: item.shifted_index)
            detected = np.asarray([cell.detected for cell in shifted], dtype=np.bool_)
            noise = np.asarray([cell.noise_power for cell in shifted], dtype=np.float64)
            threshold = np.asarray([cell.threshold_power for cell in shifted], dtype=np.float64)
            power = np.asarray([cell.input_power for cell in shifted], dtype=np.float64)
            cells = CellDetectionResult(
                method="regional",
                pfa=1e-4,
                evaluated_mask=np.asarray([cell.evaluated for cell in shifted], dtype=np.bool_),
                detected_mask=detected,
                noise_power=noise,
                threshold_power=threshold,
                evaluated_count=int(np.count_nonzero([cell.evaluated for cell in shifted])),
            )
            spectrum = SimpleNamespace(
                display=SimpleNamespace(
                    bin_power_fs2=power,
                    frequency_absolute_hz=np.arange(4096, dtype=np.float64),
                )
            )
            authoritative = pipeline._group(cells, spectrum)
            hardware = group_detector_cells(vector.cells)
            self.assertEqual(
                [(item.start_bin, item.end_bin, item.peak_bin) for item in authoritative],
                [(item.start_shifted_bin, item.end_shifted_bin, item.peak_shifted_bin) for item in hardware],
                vector.vector_id,
            )
            self.assertEqual(
                [(int(item.peak_power), int(item.local_noise_power), int(item.threshold_power)) for item in authoritative],
                [(item.peak_power, item.regional_noise, item.threshold) for item in hardware],
                vector.vector_id,
            )

    def test_gap_peak_tie_region_and_half_boundary_rules(self) -> None:
        bridged = group_detector_cells(self.vectors["one_missing_bin_bridged"].cells)
        self.assertEqual((500, 502, 502, 3), (
            bridged[0].start_shifted_bin,
            bridged[0].end_shifted_bin,
            bridged[0].peak_shifted_bin,
            bridged[0].coarse_span_bins,
        ))
        tied = group_detector_cells(self.vectors["equal_peak_first_wins"].cells)
        self.assertEqual(900, tied[0].peak_shifted_bin)
        region = group_detector_cells(self.vectors["region_boundary"].cells)
        self.assertEqual((767, 768), (region[0].start_shifted_bin, region[0].end_shifted_bin))
        center = group_detector_cells(self.vectors["center_exclusion_bridged"].cells)
        self.assertEqual((2047, 2049, 2049), (
            center[0].start_shifted_bin,
            center[0].end_shifted_bin,
            center[0].peak_shifted_bin,
        ))

    def test_maximum_bound_and_shifted_output_order(self) -> None:
        maximum = group_detector_cells(self.vectors["maximum_candidate_count"].cells)
        self.assertEqual(2 * HALF_MAX_CANDIDATES, len(maximum))
        self.assertEqual(MAX_CANDIDATES, len(maximum))
        ordered = group_detector_cells(self.vectors["shifted_half_order"].cells)
        self.assertEqual([30, 2050, 3000], [item.peak_shifted_bin for item in ordered])

    def test_empty_frame_has_one_invalid_axis_sentinel(self) -> None:
        semantic = group_detector_cells(self.vectors["no_candidate"].cells)
        axis = axis_candidate_records(semantic)
        self.assertEqual((), semantic)
        self.assertEqual(1, len(axis))
        self.assertFalse(axis[0].candidate_valid)
        self.assertTrue(axis[0].tlast)

    def test_frame_shape_and_metadata_drift_are_rejected(self) -> None:
        cells = self.vectors["one_bin"].cells
        with self.assertRaises(ValueError):
            group_detector_cells(cells[:-1])
        changed = list(cells)
        changed[100] = __import__("dataclasses").replace(changed[100], pfa_select=2)
        with self.assertRaises(ValueError):
            group_detector_cells(changed)


if __name__ == "__main__":
    unittest.main()
