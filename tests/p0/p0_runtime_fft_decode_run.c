#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "p0_pl_os_cfar.h"

#define POWER_MASK ((UINT64_C(1) << 58) - 1U)
#define EVALUATED (UINT64_C(1) << 58)
#define DETECTED (UINT64_C(1) << 59)
#define WEAK (UINT64_C(1) << 60)
#define MARKER (UINT64_C(0xC) << 60)

int main(void)
{
    static const size_t lengths[] = {4096U, 8192U, 16384U};
    uint64_t raw[4096];
    double power[4096];
    uint8_t decisions[4096];
    size_t test_index;

    for (test_index = 0U; test_index < 3U; ++test_index) {
        size_t bins = lengths[test_index];
        size_t factor = bins / 4096U;
        uint64_t *words = calloc(bins, sizeof(*words));
        size_t natural;
        int present = 0;

        if (words == NULL) return 2;
        for (natural = 0U; natural < bins; ++natural) {
            size_t shifted = natural ^ (bins / 2U);
            uint64_t flags = shifted >= 20U && shifted < bins - 20U ? EVALUATED : 0U;
            if (shifted == factor * 123U + factor - 1U)
                flags |= DETECTED | WEAK;
            words[natural] = MARKER | flags | ((natural % 101U) + 1U);
        }
        if (p0_pl_os_cfar_decode_runtime_with_weak(
                (const uint8_t *)words, bins * 8U, bins,
                raw, power, decisions, &present) != P0_PL_OS_CFAR_OK ||
            !present || decisions[123] != 3U || raw[123] == 0U || power[123] <= 0.0) {
            free(words);
            return 3;
        }
        words[(bins / 2U) + factor * 123U] ^= UINT64_C(1) << 63U;
        if (p0_pl_os_cfar_decode_runtime_with_weak(
                (const uint8_t *)words, bins * 8U, bins,
                raw, power, decisions, &present) != P0_PL_OS_CFAR_INVALID_FRAME) {
            free(words);
            return 4;
        }
        free(words);
    }
    puts("RUNTIME_FFT_DECODE_PASS");
    return 0;
}
