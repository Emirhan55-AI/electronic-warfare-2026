"""Numerical architecture tests for PHASE-06C."""

from __future__ import annotations

import unittest

from reference.rtl.fft_model import (
    OUTPUT_COMPONENT_WIDTH,
    OUTPUT_WORD_WIDTH,
    PHASE_FACTOR_WIDTH,
    architecture_decision_study,
    build_numerical_study,
    quantized_unscaled_fft,
    selected_ip_configuration,
    sign_extend_input_word,
    unpack_fft_word,
)
from reference.rtl.fft_vectors import build_frames


class Phase06CModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frames = build_frames()
        cls.study = build_numerical_study(cls.frames)

    def test_architecture_selects_amd_ip_without_claiming_real_integration(self) -> None:
        decision = architecture_decision_study()
        self.assertEqual("amd_xilinx_fft_logicore", decision["selection"])
        self.assertIn("not exercised", decision["selection_boundary"])
        self.assertFalse(decision["product_guide"]["local_copy_available"])

    def test_selected_configuration_is_fixed_forward_natural_and_unscaled(self) -> None:
        config = selected_ip_configuration()
        self.assertEqual(4096, config["transform_length"])
        self.assertFalse(config["runtime_configurable_transform_length"])
        self.assertEqual("pipelined_streaming_io", config["architecture"])
        self.assertEqual("non_realtime", config["mode"])
        self.assertEqual("natural_unshifted_k0_to_k4095", config["output_order"])
        self.assertEqual("unscaled_full_precision_fixed_point", config["arithmetic"])
        self.assertEqual("0x01_forward", config["configuration_payload"])
        self.assertEqual(
            "expected_logical_channel0_fwd_inv_bit0",
            config["configuration_payload_status"],
        )
        self.assertIn("not_verified", config["generated_ip_config_bus_width"])

    def test_required_vector_scenarios_are_present(self) -> None:
        self.assertEqual(
            {
                "zero",
                "impulse",
                "positive_dc",
                "negative_dc",
                "single_tone",
                "two_tone",
                "multiple_tones",
                "alternating_extrema",
                "complex_extrema",
                "representative_hann",
            },
            set(self.frames),
        )
        self.assertTrue(all(len(words) == 4096 for words in self.frames.values()))

    def test_known_fft_impulse_dc_and_tone_results(self) -> None:
        impulse = quantized_unscaled_fft(self.frames["impulse"])
        self.assertEqual({(32767, 0)}, {unpack_fft_word(word) for word in impulse})
        positive_dc = quantized_unscaled_fft(self.frames["positive_dc"])
        self.assertEqual((67108864, 0), unpack_fft_word(positive_dc[0]))
        self.assertEqual({(0, 0)}, {unpack_fft_word(word) for word in positive_dc[1:]})
        tone = quantized_unscaled_fft(self.frames["single_tone"])
        powers = [i_value * i_value + q_value * q_value for i_value, q_value in map(unpack_fft_word, tone)]
        self.assertEqual(256, powers.index(max(powers)))

    def test_unscaled_candidate_freezes_29_bit_q15_in_64_bit_payload(self) -> None:
        selected = next(item for item in self.study["candidate_arithmetic"] if item["selected"])
        self.assertEqual("unscaled_full_precision", selected["id"])
        self.assertEqual(OUTPUT_COMPONENT_WIDTH, selected["output_component_width"])
        self.assertEqual(OUTPUT_WORD_WIDTH, selected["output_payload_width"])
        self.assertFalse(selected["overflow_possible_with_frozen_input_contract"])
        self.assertLessEqual(selected["metrics"]["maximum_component_error_input_lsb"], 0.5)

    def test_scaled_and_block_floating_candidates_are_quantified_but_not_selected(self) -> None:
        candidates = {item["id"]: item for item in self.study["candidate_arithmetic"]}
        self.assertEqual("81920 pooled real/imaginary output components", self.study["metric_definition"]["population"])
        self.assertEqual(13, candidates["scaled_fixed_point"]["total_right_shift"])
        self.assertFalse(candidates["scaled_fixed_point"]["overflow_in_study"])
        self.assertFalse(candidates["block_floating_point"]["overflow_in_study"])
        self.assertGreater(len(set(candidates["block_floating_point"]["block_exponents"].values())), 1)
        self.assertIn("4096-LSB", candidates["scaled_fixed_point"]["error_interpretation"])
        self.assertIn("not overflow or wrap", candidates["block_floating_point"]["error_interpretation"])

    def test_phase_factor_proxy_supports_the_24_bit_decision(self) -> None:
        by_width = {item["phase_factor_width"]: item for item in self.study["phase_factor_study"]}
        self.assertEqual(PHASE_FACTOR_WIDTH, self.study["selected_phase_factor_width"])
        self.assertLess(
            by_width[24]["maximum_component_error_input_lsb"],
            by_width[20]["maximum_component_error_input_lsb"],
        )
        self.assertLessEqual(
            by_width[24]["maximum_component_error_input_lsb"],
            self.study["phase_factor_planning_criterion"]["maximum_component_error_input_lsb"],
        )
        self.assertGreater(
            by_width[20]["maximum_component_error_input_lsb"],
            self.study["phase_factor_planning_criterion"]["maximum_component_error_input_lsb"],
        )
        self.assertIn(
            "not a pre-existing",
            self.study["phase_factor_planning_criterion"]["origin"],
        )
        self.assertIn("not_amd_c_model", by_width[24]["model_boundary"])

    def test_transport_stub_mapping_is_explicitly_non_fft_sign_extension(self) -> None:
        self.assertEqual(0xFFFF800000007FFF, sign_extend_input_word(0x80007FFF))


if __name__ == "__main__":
    unittest.main()
