#include "p0_persistent_weak.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    size_t bytes = p0_persistent_weak_state_bytes();
    size_t checkpoint_bytes = p0_persistent_weak_checkpoint_bytes();
    void *state = malloc(bytes), *before = malloc(bytes), *after = malloc(bytes);
    void *checkpoint = malloc(checkpoint_bytes);
    p0_weak_nomination_v1 nominations[8];
    p0_persistent_weak_result_v1 first, second;
    unsigned frame, index;
    unsigned random = 0x12345678U;
    if (!state || !before || !after || !checkpoint || checkpoint_bytes >= 2048 ||
        p0_persistent_weak_init(state, bytes)) return 1;
    for (frame = 0; frame < 4096; ++frame) {
        unsigned count = frame % 9;
        for (index = 0; index < count; ++index) {
            unsigned peak;
            random = random * 1664525U + 1013904223U;
            peak = 20 + index * 500 + random % 480;
            if (index == 0) peak = frame % 3 == 0 ? 20 : 100;
            if (index == 7) peak = 4075;
            nominations[index].start_shifted_bin = (uint16_t)peak;
            nominations[index].end_shifted_bin = (uint16_t)peak;
            nominations[index].peak_shifted_bin = (uint16_t)peak;
            nominations[index].reserved = 0;
            nominations[index].peak_power = frame % 7 ? ((uint64_t)500 << 30) : 0;
            nominations[index].order_statistic = frame % 5 ? ((uint64_t)100 << 30) : 0;
        }
        memcpy(before, state, bytes);
        if (p0_persistent_weak_checkpoint_save(state, bytes, nominations,
                (uint16_t)count, checkpoint, checkpoint_bytes)) return 2;
        if (p0_persistent_weak_update(state, bytes, nominations, (uint16_t)count, &first)) return 3;
        memcpy(after, state, bytes);
        if (p0_persistent_weak_checkpoint_restore(state, bytes, checkpoint, checkpoint_bytes) ||
            memcmp(before, state, bytes)) return 4;
        if (p0_persistent_weak_update(state, bytes, nominations, (uint16_t)count, &second) ||
            memcmp(&first, &second, sizeof(first)) || memcmp(after, state, bytes)) return 5;
    }
    if (!p0_persistent_weak_checkpoint_save(state, bytes, nominations, 9,
            checkpoint, checkpoint_bytes)) return 6;
    if (!p0_persistent_weak_checkpoint_restore(state, bytes, checkpoint, checkpoint_bytes - 1)) return 7;
    printf("WEAK_STATE_BYTES=%zu WEAK_CHECKPOINT_BYTES=%zu FRAMES=4096\n", bytes, checkpoint_bytes);
    puts("ST06_PRODUCT_PIPELINE=PASS");
    free(state); free(before); free(after); free(checkpoint);
    return 0;
}
