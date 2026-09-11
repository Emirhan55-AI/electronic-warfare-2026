#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "p0_runtime_fft_bridge.h"

int main(void)
{
    static const size_t lengths[] = {4096U, 8192U, 16384U};
    uint64_t canonical_power[4096];
    uint8_t canonical_decisions[4096];
    size_t case_index;

    for (case_index = 0U; case_index < 3U; ++case_index) {
        size_t length = lengths[case_index];
        size_t factor = length / 4096U;
        uint64_t *power = calloc(length, sizeof(*power));
        uint8_t *decisions = calloc(length, sizeof(*decisions));
        size_t index;

        if (power == NULL || decisions == NULL) return 2;
        for (index = 0U; index < length; ++index) {
            power[index] = (index % 101U) + 1U;
            decisions[index] = index % 257U == 0U ? 2U : 0U;
        }
        if (p0_runtime_fft_collapse(power, decisions, length,
                                    canonical_power, canonical_decisions) != 0)
            return 3;
        for (index = 0U; index < 4096U; ++index) {
            uint64_t expected = 0U;
            uint8_t expected_decision = 0U;
            size_t offset;
            for (offset = 0U; offset < factor; ++offset) {
                expected += power[index * factor + offset];
                expected_decision |= decisions[index * factor + offset];
            }
            if (canonical_power[index] != expected ||
                canonical_decisions[index] != expected_decision)
                return 4;
        }
        free(decisions);
        free(power);
    }
    puts("RUNTIME_FFT_BRIDGE_PASS");
    return 0;
}
