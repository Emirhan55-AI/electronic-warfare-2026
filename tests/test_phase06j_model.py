from __future__ import annotations

import unittest

from reference.ps.temporal_confirmation import (
    ASSOCIATION_TOLERANCE_BINS,
    CONFIRMATIONS_REQUIRED,
    CONFIRMATION_WINDOW,
    EXPIRY_CONSECUTIVE_MISSES,
    MAX_ACTIVE_TRACKS,
    MAX_ENDED_HISTORY,
    AuthoritativeTemporalOracle,
)
from reference.ps.temporal_vectors import scenario_packets


class Phase06JModelTests(unittest.TestCase):
    def _run(self, name: str):
        packets = dict(scenario_packets())[name]
        oracle = AuthoritativeTemporalOracle()
        return tuple(oracle.process(packet) for packet in packets)

    def test_authoritative_constants_are_frozen(self) -> None:
        self.assertEqual((2, 2, 3, 2), (
            ASSOCIATION_TOLERANCE_BINS,
            CONFIRMATIONS_REQUIRED,
            CONFIRMATION_WINDOW,
            EXPIRY_CONSECUTIVE_MISSES,
        ))
        self.assertEqual((64, 128), (MAX_ACTIVE_TRACKS, MAX_ENDED_HISTORY))

    def test_one_two_and_three_of_three_semantics(self) -> None:
        one = self._run("one_of_three_expiry")
        self.assertEqual(("tentative", "tentative"), tuple(frame.active_events[0].state for frame in one[:2]))
        self.assertEqual("ended", one[2].ended_events[0].state)
        two = self._run("two_of_three_with_one_miss")
        self.assertEqual("confirmed", two[2].active_events[0].state)
        three = self._run("three_of_three_moving")
        self.assertEqual(("tentative", "confirmed", "confirmed"), tuple(frame.active_events[0].state for frame in three))

    def test_association_ambiguity_reset_and_uint32_wrap(self) -> None:
        ambiguous = self._run("ambiguous_equal_distance_event_id_tie")[-1]
        self.assertEqual((502, 506), tuple(event.candidate.peak_shifted_bin for event in ambiguous.active_events))
        reset = self._run("nonconsecutive_frame_resets")
        self.assertTrue(reset[-1].reset_applied)
        self.assertEqual((1, "tentative"), (reset[-1].active_events[0].event_id, reset[-1].active_events[0].state))
        wrapped = self._run("uint32_frame_wrap_is_consecutive")
        self.assertFalse(wrapped[-1].reset_applied)
        self.assertEqual("confirmed", wrapped[-1].active_events[0].state)

    def test_maximum_candidate_frame_is_bounded(self) -> None:
        frame = self._run("maximum_candidate_frame")[0]
        self.assertEqual(64, len(frame.active_events))
        self.assertEqual(1288, frame.dropped_candidates)

    def test_ended_history_is_a_bounded_ring(self) -> None:
        frame = self._run("ended_history_ring_eviction")[-1]
        self.assertEqual(2, frame.evicted_history_count)
        self.assertEqual(2, len(frame.ended_events))


if __name__ == "__main__":
    unittest.main()
