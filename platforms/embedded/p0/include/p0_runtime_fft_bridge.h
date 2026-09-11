#ifndef P0_RUNTIME_FFT_BRIDGE_H
#define P0_RUNTIME_FFT_BRIDGE_H

#include <stddef.h>
#include <stdint.h>

enum {
    P0_RUNTIME_FFT_CANONICAL_BINS = 4096,
    P0_RUNTIME_FFT_POWER_BITS = 58
};

int p0_runtime_fft_collapse(const uint64_t *native_power,
                            const uint8_t *native_decisions,
                            size_t native_bins,
                            uint64_t *canonical_power,
                            uint8_t *canonical_decisions);

#endif
