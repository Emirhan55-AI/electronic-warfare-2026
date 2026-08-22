"""PHASE-06C numerical FFT contract and architecture study.

This module models the selected external numerical contract.  It is not the
AMD FFT C model and must not be described as bit-accurate vendor-IP behavior.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np
import numpy.typing as npt


FRAME_LENGTH = 4096
INPUT_COMPONENT_WIDTH = 16
INPUT_FRACTION_BITS = 15
INPUT_WORD_WIDTH = 32
OUTPUT_COMPONENT_WIDTH = 29
OUTPUT_CONTAINER_WIDTH = 32
OUTPUT_FRACTION_BITS = 15
OUTPUT_WORD_WIDTH = 64
THEORETICAL_GROWTH_BITS = 13
CONFIG_WIDTH = 8
CONFIG_FORWARD_FIXED = 0x01
PHASE_FACTOR_WIDTH = 24


def _signed(value: int, width: int) -> int:
    mask = (1 << width) - 1
    narrowed = int(value) & mask
    return narrowed - (1 << width) if narrowed & (1 << (width - 1)) else narrowed


def unpack_sq1_15_word(word: int) -> tuple[int, int]:
    """Unpack PHASE-06B low-I/high-Q signed 16-bit components."""
    if not 0 <= int(word) <= 0xFFFFFFFF:
        raise ValueError("FFT giriş sözcüğü 32 bit olmalıdır.")
    return _signed(word, 16), _signed(word >> 16, 16)


def pack_sq1_15_word(i_value: int, q_value: int) -> int:
    if not -32768 <= int(i_value) <= 32767 or not -32768 <= int(q_value) <= 32767:
        raise ValueError("FFT giriş bileşenleri signed 16 bit olmalıdır.")
    return (int(i_value) & 0xFFFF) | ((int(q_value) & 0xFFFF) << 16)


def sign_extend_input_word(word: int) -> int:
    """Transport-stub response: sign-extend each input component into a 32-bit lane."""
    i_value, q_value = unpack_sq1_15_word(word)
    return (i_value & 0xFFFFFFFF) | ((q_value & 0xFFFFFFFF) << 32)


def unpack_fft_word(word: int) -> tuple[int, int]:
    if not 0 <= int(word) <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("FFT çıkış sözcüğü 64 bit olmalıdır.")
    return _signed(word, 32), _signed(word >> 32, 32)


def _pack_fft_components(i_value: int, q_value: int) -> int:
    lower = -(1 << (OUTPUT_COMPONENT_WIDTH - 1))
    upper = (1 << (OUTPUT_COMPONENT_WIDTH - 1)) - 1
    if not lower <= int(i_value) <= upper or not lower <= int(q_value) <= upper:
        raise ArithmeticError("İdeal unscaled FFT sonucu signed 29 bit sözleşmesini aştı.")
    return (int(i_value) & 0xFFFFFFFF) | ((int(q_value) & 0xFFFFFFFF) << 32)


def frame_components(words: Sequence[int]) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.int64]]:
    if len(words) != FRAME_LENGTH:
        raise ValueError("FFT frame'i tam 4096 kompleks örnek içermelidir.")
    i_values = np.empty(FRAME_LENGTH, dtype=np.int64)
    q_values = np.empty(FRAME_LENGTH, dtype=np.int64)
    for index, word in enumerate(words):
        i_values[index], q_values[index] = unpack_sq1_15_word(word)
    return i_values, q_values


def floating_unscaled_fft(words: Sequence[int]) -> npt.NDArray[np.complex128]:
    """PHASE-02-sign forward FFT applied to exact SQ1.15 integer inputs."""
    i_values, q_values = frame_components(words)
    samples = i_values.astype(np.float64) + 1j * q_values.astype(np.float64)
    return np.asarray(np.fft.fft(samples), dtype=np.complex128)


def quantized_unscaled_fft(words: Sequence[int]) -> tuple[int, ...]:
    """Idealized convergent-rounded Q15 external contract, not AMD-IP bit accuracy."""
    result = floating_unscaled_fft(words)
    real = np.rint(result.real).astype(np.int64)
    imag = np.rint(result.imag).astype(np.int64)
    return tuple(_pack_fft_components(int(i_value), int(q_value)) for i_value, q_value in zip(real, imag, strict=True))


def _error_metrics(reference: npt.NDArray[np.complex128], reconstructed: npt.NDArray[np.complex128]) -> dict[str, float]:
    component_errors = np.concatenate(
        ((reconstructed.real - reference.real), (reconstructed.imag - reference.imag))
    )
    return {
        "maximum_component_error_input_lsb": round(float(np.max(np.abs(component_errors))), 12),
        "rms_component_error_input_lsb": round(float(np.sqrt(np.mean(component_errors * component_errors))), 12),
    }


def _scaled_fixed(reference: npt.NDArray[np.complex128]) -> tuple[npt.NDArray[np.complex128], bool]:
    scale = 1 << THEORETICAL_GROWTH_BITS
    real = np.rint(reference.real / scale)
    imag = np.rint(reference.imag / scale)
    overflow = bool(np.any(real < -32768) or np.any(real > 32767) or np.any(imag < -32768) or np.any(imag > 32767))
    quantized = np.clip(real, -32768, 32767) + 1j * np.clip(imag, -32768, 32767)
    return np.asarray(quantized * scale, dtype=np.complex128), overflow


def _block_floating(reference: npt.NDArray[np.complex128]) -> tuple[npt.NDArray[np.complex128], int, bool]:
    maximum = float(max(np.max(np.abs(reference.real)), np.max(np.abs(reference.imag))))
    exponent = 0 if maximum == 0.0 else max(0, int(math.ceil(math.log2(maximum / 32767.0))))
    exponent = min(exponent, 15)
    scale = 1 << exponent
    real = np.rint(reference.real / scale)
    imag = np.rint(reference.imag / scale)
    overflow = bool(np.any(real < -32768) or np.any(real > 32767) or np.any(imag < -32768) or np.any(imag > 32767))
    quantized = np.clip(real, -32768, 32767) + 1j * np.clip(imag, -32768, 32767)
    return np.asarray(quantized * scale, dtype=np.complex128), exponent, overflow


def _bit_reversed_indices(length: int) -> npt.NDArray[np.int64]:
    bits = int(math.log2(length))
    values = np.arange(length, dtype=np.uint32)
    reversed_values = np.zeros(length, dtype=np.uint32)
    for _ in range(bits):
        reversed_values = (reversed_values << 1) | (values & 1)
        values >>= 1
    return reversed_values.astype(np.int64)


def quantized_twiddle_fft(words: Sequence[int], phase_factor_width: int) -> npt.NDArray[np.complex128]:
    """Radix-2 architectural proxy with quantized twiddles; not an AMD C-model substitute."""
    if phase_factor_width < 8:
        raise ValueError("Phase-factor genişliği en az 8 bit olmalıdır.")
    i_values, q_values = frame_components(words)
    values = (i_values.astype(np.float64) + 1j * q_values.astype(np.float64))[
        _bit_reversed_indices(FRAME_LENGTH)
    ].copy()
    scale = float(1 << (phase_factor_width - 2))
    size = 2
    while size <= FRAME_LENGTH:
        half = size // 2
        angles = -2.0 * np.pi * np.arange(half, dtype=np.float64) / size
        exact = np.cos(angles) + 1j * np.sin(angles)
        twiddles = np.rint(exact.real * scale) / scale + 1j * np.rint(exact.imag * scale) / scale
        blocks = values.reshape(-1, size)
        left = blocks[:, :half].copy()
        right = blocks[:, half:].copy() * twiddles[None, :]
        blocks[:, :half] = left + right
        blocks[:, half:] = left - right
        size *= 2
    return np.asarray(values, dtype=np.complex128)


def architecture_decision_study() -> dict[str, object]:
    return {
        "schema_version": 1,
        "phase": "PHASE-06C",
        "product_guide": {
            "document": "AMD Fast Fourier Transform LogiCORE IP Product Guide (PG109)",
            "version": "9.1",
            "release": "2026.1",
            "source": "https://docs.amd.com/r/en-US/2026.1/pg109-xfft/Pipelined-Streaming-I/O",
            "local_copy_available": False,
        },
        "candidates": [
            {
                "id": "custom_systemverilog_fft",
                "selected": False,
                "development_risk": "high",
                "verification_burden": "high",
                "zynq_7000_compatibility": "possible_but_unproven",
                "axi4_stream": "must_be_designed_and_verified",
                "n4096_fixed_point": "must_be_designed_and_verified",
                "throughput": "high_design_risk",
                "ordering_scaling": "fully_custom",
                "integration_complexity": "high",
                "resource_measurement": "requires_future_vivado",
            },
            {
                "id": "amd_xilinx_fft_logicore",
                "selected": True,
                "development_risk": "lower_after_vendor_ip_verification",
                "verification_burden": "wrapper_plus_vendor_model",
                "zynq_7000_compatibility": "listed_by_pg109; exact_part_and_generated_configuration_unverified",
                "axi4_stream": "native",
                "n4096_fixed_point": "supported_by_product_guide",
                "throughput": "continuous_with_pipelined_streaming_and_waitstates",
                "ordering_scaling": "configurable",
                "integration_complexity": "moderate_and_vendor_tool_dependent",
                "resource_measurement": "available_in_future_vivado_flow",
            },
        ],
        "selection": "amd_xilinx_fft_logicore",
        "selection_boundary": "architecture selected; real IP generation, C-model and XSim verification not exercised",
        "official_pg109_cross_check": {
            "status": "passed_for_documented_capabilities",
            "document_release_date": "2026-07-17",
            "verified_from_guide": [
                "Zynq-7000 family listed",
                "N=4096 and single-channel standard-sample-rate fixed point supported",
                "Pipelined Streaming I/O and Non-Realtime AXI wait states supported",
                "unscaled arithmetic, convergent rounding, 24-bit phase factors and natural output supported",
                "29-bit output rule for 16-bit N=4096 unscaled input",
                "logical XK_INDEX width 12 with byte padding",
                "FWD_INV channel-0 bit 0 equals forward when set",
                "TLAST is checked for events and does not control input framing",
            ],
            "expected_to_be_verified_in_vivado": [
                "exact ZedBoard part and generated IP availability",
                "generated config TDATA width and complete port map",
                "generated output TDATA/TUSER physical widths and padding",
                "actual AMD numerical behavior, latency, resources and timing",
            ],
        },
    }


def selected_ip_configuration() -> dict[str, object]:
    return {
        "channels": 1,
        "transform_length": FRAME_LENGTH,
        "runtime_configurable_transform_length": False,
        "direction": "forward_only_system_policy",
        "architecture": "pipelined_streaming_io",
        "mode": "non_realtime",
        "input_component_width": INPUT_COMPONENT_WIDTH,
        "phase_factor_width": PHASE_FACTOR_WIDTH,
        "output_order": "natural_unshifted_k0_to_k4095",
        "arithmetic": "unscaled_full_precision_fixed_point",
        "rounding": "convergent_rounding",
        "rounding_boundary": "legal PG109 selection; not every internal word-length reduction uses convergent rounding",
        "output_component_width": OUTPUT_COMPONENT_WIDTH,
        "output_container_width": OUTPUT_CONTAINER_WIDTH,
        "output_payload_width": OUTPUT_WORD_WIDTH,
        "xk_index": "enabled_12_bit",
        "blk_exp": "disabled_not_applicable",
        "ovflo": "disabled_not_applicable_to_unscaled_full_precision",
        "configuration_payload": "0x01_forward",
        "configuration_payload_status": "expected_logical_channel0_fwd_inv_bit0",
        "wrapper_logical_config_width": CONFIG_WIDTH,
        "generated_ip_config_bus_width": "not_verified_until_vivado_ip_generation",
        "configuration_policy": "issued_once_after_each_reset_before_input_acceptance; no runtime reconfiguration",
        "configuration_to_first_input": "at_least_one_clock_after_config_handshake",
        "generated_ip_port_map": "not_verified_until_vivado_ip_generation",
        "cyclic_prefix": "disabled",
        "xk_index_logical_width": 12,
        "generated_tuser_width": "not_verified; PG109 requires byte padding",
        "device_support": "PG109_lists_Zynq_7000; exact_generated_part_configuration_not_verified",
        "reset_assumption": "PG109_aresetn_active_for_at_least_two_cycles; generated_port_presence_not_verified",
    }


def build_numerical_study(frames: Mapping[str, Sequence[int]]) -> dict[str, object]:
    if not frames:
        raise ValueError("FFT sayısal çalışması en az bir frame gerektirir.")
    references = {identifier: floating_unscaled_fft(words) for identifier, words in frames.items()}

    unscaled_reconstructed = {
        identifier: np.rint(value.real) + 1j * np.rint(value.imag)
        for identifier, value in references.items()
    }
    scaled_results = {identifier: _scaled_fixed(value) for identifier, value in references.items()}
    block_results = {identifier: _block_floating(value) for identifier, value in references.items()}

    def combined_metrics(reconstructed: Mapping[str, npt.NDArray[np.complex128]]) -> dict[str, float]:
        reference_values = np.concatenate([references[key] for key in frames])
        reconstructed_values = np.concatenate([reconstructed[key] for key in frames])
        return _error_metrics(reference_values, reconstructed_values)

    phase_frames = [frames[key] for key in ("impulse", "single_tone", "representative_hann")]
    phase_study = []
    for width in (16, 20, 24, 32):
        maxima = []
        rms_values = []
        for words in phase_frames:
            exact = floating_unscaled_fft(words)
            proxy = quantized_twiddle_fft(words, width)
            metrics = _error_metrics(exact, proxy)
            maxima.append(metrics["maximum_component_error_input_lsb"])
            rms_values.append(metrics["rms_component_error_input_lsb"])
        phase_study.append(
            {
                "phase_factor_width": width,
                "maximum_component_error_input_lsb": round(max(maxima), 12),
                "maximum_frame_rms_component_error_input_lsb": round(max(rms_values), 12),
                "model_boundary": "radix2_quantized_twiddle_proxy_not_amd_c_model",
            }
        )

    block_exponents = {identifier: result[1] for identifier, result in block_results.items()}
    return {
        "schema_version": 1,
        "phase": "PHASE-06C",
        "algorithmic_reference": "PHASE-02 NumPy unscaled forward FFT",
        "frame_count": len(frames),
        "metric_definition": {
            "reference": "NumPy float64 unscaled FFT of exact signed Q15 integer codes",
            "unit": "one signed input-component integer code equals one input LSB",
            "population": f"{len(frames) * FRAME_LENGTH * 2} pooled real/imaginary output components",
            "maximum": "maximum absolute component error",
            "rms": "sqrt(mean(component_error_squared)) over the pooled component population",
            "rounding": "numpy.rint convergent ties-to-even",
            "scaled_candidates": "metrics are calculated after restoring the candidate scale/exponent",
            "randomness": "none",
        },
        "candidate_arithmetic": [
            {
                "id": "unscaled_full_precision",
                "selected": True,
                "output_component_width": OUTPUT_COMPONENT_WIDTH,
                "output_fraction_bits": OUTPUT_FRACTION_BITS,
                "output_payload_width": OUTPUT_WORD_WIDTH,
                "maximum_theoretical_growth_bits": THEORETICAL_GROWTH_BITS,
                "overflow_possible_with_frozen_input_contract": False,
                "metrics": combined_metrics(unscaled_reconstructed),
                "downstream_power_consequence": "wide exact-square candidate; power width remains unfrozen",
            },
            {
                "id": "scaled_fixed_point",
                "selected": False,
                "output_component_width": 16,
                "total_right_shift": THEORETICAL_GROWTH_BITS,
                "illustrative_schedule": "six pipelined stage-pairs shifted by [3,2,2,2,2,2]",
                "overflow_in_study": any(result[1] for result in scaled_results.values()),
                "metrics_after_inverse_scale": combined_metrics(
                    {identifier: result[0] for identifier, result in scaled_results.items()}
                ),
                "error_interpretation": (
                    "A 13-bit right shift has an 8192-input-LSB quantization step after scale restoration; "
                    "ties-to-even rounding therefore permits the observed half-step 4096-LSB maximum error."
                ),
                "downstream_power_consequence": "narrower payload but fixed normalization dependency",
            },
            {
                "id": "block_floating_point",
                "selected": False,
                "output_component_width": 16,
                "block_exponents": block_exponents,
                "overflow_in_study": any(result[2] for result in block_results.values()),
                "metrics_after_exponent_restore": combined_metrics(
                    {identifier: result[0] for identifier, result in block_results.items()}
                ),
                "error_interpretation": (
                    "Frames using exponent 13 have an 8192-input-LSB restored quantization step; "
                    "the observed 4096-LSB maximum is its half-step rounding bound, not overflow or wrap."
                ),
                "downstream_power_consequence": "per-frame exponent must accompany power and detector state",
            },
        ],
        "phase_factor_study": phase_study,
        "phase_factor_planning_criterion": {
            "maximum_component_error_input_lsb": 16.0,
            "maximum_frame_rms_component_error_input_lsb": 0.25,
            "origin": "PHASE-06C architecture-selection planning baseline; not a pre-existing repository acceptance gate",
            "scope": "architectural radix-2 proxy only; real AMD C-model acceptance remains future work",
        },
        "selected_phase_factor_width": PHASE_FACTOR_WIDTH,
        "selection_reason": (
            "Unscaled full precision preserves the PHASE-02 normalization relationship and deterministic Q15 binary point; "
            "29-bit components cover the vendor full-precision growth rule. A 24-bit phase factor materially reduces "
            "the architectural proxy error without imposing the 32-bit candidate width."
        ),
        "vendor_accuracy_boundary": "Actual AMD numerical behavior remains unproven until matching C-model/XSim execution.",
    }
