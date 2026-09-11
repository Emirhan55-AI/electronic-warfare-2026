#include "p0_runtime_fft_bridge.h"

#include <errno.h>

#define P0_RUNTIME_FFT_POWER_MAX ((UINT64_C(1) << P0_RUNTIME_FFT_POWER_BITS) - 1U)

int p0_runtime_fft_collapse(const uint64_t *native_power,
                            const uint8_t *native_decisions,
                            size_t native_bins,
                            uint64_t *canonical_power,
                            uint8_t *canonical_decisions)
{
    size_t output;
    size_t factor;

    if (native_power == NULL || native_decisions == NULL ||
        canonical_power == NULL || canonical_decisions == NULL ||
        (native_bins != 4096U && native_bins != 8192U && native_bins != 16384U)) {
        errno = EINVAL;
        return -1;
    }
    factor = native_bins / P0_RUNTIME_FFT_CANONICAL_BINS;
    for (output = 0U; output < P0_RUNTIME_FFT_CANONICAL_BINS; ++output) {
        uint64_t sum = 0U;
        uint8_t decision = 0U;
        size_t offset;

        for (offset = 0U; offset < factor; ++offset) {
            size_t input = output * factor + offset;
            uint64_t value = native_power[input];

            if (value > P0_RUNTIME_FFT_POWER_MAX || native_decisions[input] > 3U) {
                errno = EPROTO;
                return -1;
            }
            if (value > P0_RUNTIME_FFT_POWER_MAX - sum)
                sum = P0_RUNTIME_FFT_POWER_MAX;
            else
                sum += value;
            decision |= native_decisions[input];
        }
        canonical_power[output] = sum;
        canonical_decisions[output] = decision;
    }
    return 0;
}
