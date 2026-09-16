from types import SimpleNamespace
import unittest

from algorithms.p0.transport import IQFrame, InlineParameterField, InlineParameterResult
from app.operator_console.automatic_parameter import AutomaticParameterScheduler


def event(event_id: int, power: float, lower: int, upper: int):
    return SimpleNamespace(
        event_id=event_id,
        state="confirmed",
        observed_this_frame=True,
        peak_power=power,
        peak_shifted_bin=(lower + upper) // 2,
        start_shifted_bin=lower,
        end_shifted_bin=upper,
    )


def result(intent: int, event_id: int, frame_id: int, count: int, *, reason=None):
    state = "valid" if reason is None else "insufficient_quality"
    value = InlineParameterField(state, -30.0 if reason is None else None, reason)
    return InlineParameterResult(
        intent,
        event_id,
        frame_id,
        count,
        value,
        value,
        value,
        value,
        value,
        value,
        1.0,
        2.0,
        0.1,
        0.2,
    )


class AutomaticParameterSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scheduler = AutomaticParameterScheduler(center_frequency_hz=820_000_000)

    @staticmethod
    def frame(sequence: int) -> IQFrame:
        return IQFrame(sequence, 2_000_000, 820_000_000, b"\x01\x02" * 4096, frame_id=sequence)

    def test_strongest_first_and_eventually_measures_each_eligible_signal(self) -> None:
        self.scheduler.observe_events((event(1, 10.0, 1000, 1020), event(2, 30.0, 2000, 2020)))
        decorated = [self.scheduler.decorate(self.frame(index)) for index in range(4)]
        self.assertEqual({item.parameter_request.event_id for item in decorated}, {2})
        outcomes = ()
        for index, item in enumerate(decorated, 1):
            request = item.parameter_request
            outcomes = self.scheduler.observe_response(
                item.sequence_number,
                result(request.intent_id, request.event_id, item.frame_id, index),
            )
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].event_id, 2)
        self.assertEqual(outcomes[0].channel_power_dbfs, -30.0)
        next_frame = self.scheduler.decorate(self.frame(4))
        self.assertEqual(next_frame.parameter_request.event_id, 1)

    def test_wide_edge_and_neighbor_cases_are_logged_not_fabricated(self) -> None:
        self.scheduler.observe_events(
            (
                event(1, 40.0, 100, 700),
                event(2, 30.0, 20, 30),
                event(3, 20.0, 2000, 2010),
                event(4, 10.0, 2030, 2040),
            )
        )
        undecorated = self.scheduler.decorate(self.frame(0))
        self.assertIsNone(undecorated.parameter_request)
        outcomes = self.scheduler.drain_outcomes()
        self.assertEqual({item.event_id for item in outcomes}, {1, 2, 3, 4})
        self.assertEqual(
            {item.reason for item in outcomes},
            {
                "live_span_exceeds_512_bins",
                "reference_window_outside_fft",
                "neighbor_in_reference_window",
            },
        )

    def test_context_loss_retries_are_bounded(self) -> None:
        target = event(5, 50.0, 1000, 1010)
        self.scheduler.observe_events((target,))
        for retry in range(3):
            decorated = self.scheduler.decorate(self.frame(retry))
            request = decorated.parameter_request
            outcomes = self.scheduler.observe_response(
                decorated.sequence_number,
                result(
                    request.intent_id,
                    request.event_id,
                    decorated.frame_id,
                    0,
                    reason="event_ownership_lost",
                ),
            )
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].status, "not_observed")
        self.assertIsNone(self.scheduler.decorate(self.frame(4)).parameter_request)

    def test_unscheduled_ended_events_are_telemetry_not_catalog_outcomes(self) -> None:
        ended = tuple(event(index, float(index), 1000, 1010) for index in range(1, 65))
        self.scheduler.observe_events((), ended)

        self.assertEqual(self.scheduler.drain_outcomes(), ())
        self.assertEqual(self.scheduler.expired_before_measurement_count, 64)
        self.assertEqual(self.scheduler.completed_event_count, 64)


if __name__ == "__main__":
    unittest.main()
