#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <new>
#include <immintrin.h>

#if defined(_WIN32)
#define P0_EXPORT __declspec(dllexport)
#else
#define P0_EXPORT __attribute__((visibility("default")))
#endif

namespace {
constexpr std::size_t kInputSamples = 16384;
constexpr std::size_t kOutputSamples = 4096;
constexpr std::size_t kTapCount = 193;
constexpr std::size_t kDelaySamples = kTapCount - 1;
constexpr double kScale = 128.0;
constexpr double kTwoPi = 6.283185307179586476925286766559;

struct State {
    std::array<double, kTapCount> taps{};
    std::array<double, kInputSamples> nco_real{};
    std::array<double, kInputSamples> nco_imag{};
    std::array<double, kDelaySamples + kInputSamples> extended_real{};
    std::array<double, kDelaySamples + kInputSamples> extended_imag{};
    double phase = 0.0;
};

inline std::int8_t quantize(double value, std::uint64_t& saturated) {
    const double rounded = std::nearbyint(value * kScale);
    if (rounded < -128.0) {
        ++saturated;
        return static_cast<std::int8_t>(-128);
    }
    if (rounded > 127.0) {
        ++saturated;
        return static_cast<std::int8_t>(127);
    }
    return static_cast<std::int8_t>(rounded);
}

inline double avx2_symmetric_dot_193(const double* taps, const double* newest) {
    __m256d accumulated = _mm256_setzero_pd();
    for (std::size_t tap = 0; tap < 96; tap += 4) {
        const __m256d coefficients = _mm256_loadu_pd(taps + tap);
        const __m256d recent_ascending =
            _mm256_loadu_pd(newest - static_cast<std::ptrdiff_t>(tap) - 3);
        const __m256d recent =
            _mm256_permute4x64_pd(recent_ascending, _MM_SHUFFLE(0, 1, 2, 3));
        const __m256d distant =
            _mm256_loadu_pd(newest - 192 + static_cast<std::ptrdiff_t>(tap));
        accumulated = _mm256_fmadd_pd(coefficients, _mm256_add_pd(recent, distant), accumulated);
    }
    alignas(32) double lanes[4];
    _mm256_store_pd(lanes, accumulated);
    return lanes[0] + lanes[1] + lanes[2] + lanes[3] + taps[96] * newest[-96];
}
}  // namespace

extern "C" {

P0_EXPORT std::uint32_t p0_channelizer_abi_version() { return 1U; }

P0_EXPORT void* p0_channelizer_create(
    const double* taps,
    std::size_t tap_count,
    double phase_step_radians) {
    if (taps == nullptr || tap_count != kTapCount || !std::isfinite(phase_step_radians)) {
        return nullptr;
    }
    for (std::size_t index = 0; index < kTapCount; ++index) {
        if (!std::isfinite(taps[index]) || taps[index] != taps[kTapCount - 1 - index]) {
            return nullptr;
        }
    }
    auto* state = new (std::nothrow) State();
    if (state == nullptr) {
        return nullptr;
    }
    std::copy_n(taps, kTapCount, state->taps.begin());
    for (std::size_t index = 0; index < kInputSamples; ++index) {
        const double phase = phase_step_radians * static_cast<double>(index);
        state->nco_real[index] = std::cos(phase);
        state->nco_imag[index] = std::sin(phase);
    }
    return state;
}

P0_EXPORT void p0_channelizer_reset(void* opaque) {
    auto* state = static_cast<State*>(opaque);
    if (state == nullptr) {
        return;
    }
    std::fill_n(state->extended_real.begin(), kDelaySamples, 0.0);
    std::fill_n(state->extended_imag.begin(), kDelaySamples, 0.0);
    state->phase = 0.0;
}

P0_EXPORT void p0_channelizer_destroy(void* opaque) {
    delete static_cast<State*>(opaque);
}

P0_EXPORT int p0_channelizer_process_ci8(
    void* opaque,
    const std::int8_t* input,
    std::size_t input_bytes,
    std::int8_t* output,
    std::size_t output_bytes,
    std::uint64_t* input_saturated,
    std::uint64_t* output_saturated) {
    auto* state = static_cast<State*>(opaque);
    if (state == nullptr || input == nullptr || output == nullptr ||
        input_saturated == nullptr || output_saturated == nullptr ||
        input_bytes != kInputSamples * 2 || output_bytes != kOutputSamples * 2) {
        return -1;
    }

    *input_saturated = 0;
    *output_saturated = 0;
    const double phase_real = std::cos(state->phase);
    const double phase_imag = std::sin(state->phase);
    for (std::size_t index = 0; index < kInputSamples; ++index) {
        const std::int8_t raw_real = input[2 * index];
        const std::int8_t raw_imag = input[2 * index + 1];
        *input_saturated += static_cast<std::uint64_t>(raw_real == -128 || raw_real == 127);
        *input_saturated += static_cast<std::uint64_t>(raw_imag == -128 || raw_imag == 127);
        const double sample_real = static_cast<double>(raw_real) / kScale;
        const double sample_imag = static_cast<double>(raw_imag) / kScale;
        const double nco_real = state->nco_real[index] * phase_real - state->nco_imag[index] * phase_imag;
        const double nco_imag = state->nco_real[index] * phase_imag + state->nco_imag[index] * phase_real;
        state->extended_real[kDelaySamples + index] =
            sample_real * nco_real - sample_imag * nco_imag;
        state->extended_imag[kDelaySamples + index] =
            sample_real * nco_imag + sample_imag * nco_real;
    }

    if (*input_saturated != 0) {
        std::fill_n(output, output_bytes, static_cast<std::int8_t>(0));
    } else {
        for (std::size_t output_index = 0; output_index < kOutputSamples; ++output_index) {
            const std::size_t newest = kDelaySamples + 4 * output_index;
            const double accumulated_real =
                avx2_symmetric_dot_193(state->taps.data(), state->extended_real.data() + newest);
            const double accumulated_imag =
                avx2_symmetric_dot_193(state->taps.data(), state->extended_imag.data() + newest);
            output[2 * output_index] = quantize(accumulated_real, *output_saturated);
            output[2 * output_index + 1] = quantize(accumulated_imag, *output_saturated);
        }
    }

    std::copy_n(
        state->extended_real.begin() + kInputSamples,
        kDelaySamples,
        state->extended_real.begin());
    std::copy_n(
        state->extended_imag.begin() + kInputSamples,
        kDelaySamples,
        state->extended_imag.begin());
    // The block phase advance is supplied through the precomputed NCO. All
    // production offsets are integer-Hz values; retain a bounded phase value.
    const double step_real = state->nco_real[1];
    const double step_imag = state->nco_imag[1];
    const double step = std::atan2(step_imag, step_real);
    state->phase = std::remainder(
        state->phase + step * static_cast<double>(kInputSamples),
        kTwoPi);
    return 0;
}

}  // extern "C"
