#include "p0_ed_pipeline.h"
#include "p0_pl_os_cfar.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BINS 4096U
#define BYTES (BINS * 8U)
static void frame_make(uint64_t *words, int weak, int legacy)
{
    unsigned n;
    for (n = 0; n < BINS; ++n) {
        unsigned b = n ^ 2048U;
        words[n] = ((uint64_t)(legacy ? 0xA : 0xC) << 60) | ((uint64_t)100 << 30);
        if (b >= 20 && b < 4076) words[n] |= (uint64_t)1 << 58;
        if (b == 2600 && weak) {
            words[n] = (words[n] & ~(((uint64_t)1 << 58) - 1)) | ((uint64_t)500 << 30);
            if (!legacy) words[n] |= (uint64_t)1 << 60;
        }
    }
}
int main(void)
{
    p0_ed_pipeline_t ordinary, trusted;
    phase06j_frame_result_v1 a, b;
    uint64_t words[BINS];
    size_t ac, bc;
    unsigned i;
    int marked;
    if (p0_ed_pipeline_init(&ordinary) || p0_ed_pipeline_init(&trusted)) return 1;
    /* Same physical DMA words through both public and service-owned buffer paths. */
    for (i = 0; i < 96; ++i) {
        frame_make(words, i < 40, 0);
        if (i == 16) {
            uint64_t saved = words[0];
            words[0] = 0; /* Rejected frame must not age/reset weak history. */
            if (!p0_ed_pipeline_process(&ordinary, i, 0, (uint8_t *)words, BYTES, &a, &ac)) return 11;
            words[0] = saved;
        }
        if (p0_pl_os_cfar_decode_with_weak((uint8_t *)words, BYTES, trusted.raw_power,
                trusted.power, trusted.detections, &marked) ||
            p0_ed_pipeline_process(&ordinary, i, i == 0, (uint8_t *)words, BYTES, &a, &ac) ||
            p0_ed_pipeline_process_decoded_trusted(&trusted, i, i == 0, marked, &b, &bc) ||
            ac != bc || memcmp(&a, &b, sizeof(a))) return 2;
        if (i < 23 && a.active_count != 0) return 3;
        if (i < 40 && ac != 1) return 14;
        if (i == 39 && (a.active_count != 1 ||
            !(a.active[0].candidate.flags & PHASE06I_RECORD_WEAK_EVIDENCE))) return 4;
        if (i == 39 && a.active[0].candidate.peak_power_uq28_30 != ((uint64_t)500 << 30)) return 12;
        if (i == 40 && (a.active_count != 1 || a.active[0].observed_this_frame ||
            a.active[0].last_seen_frame_id != 39 ||
            a.active[0].candidate.peak_power_uq28_30 != ((uint64_t)100 << 30))) return 13;
        if (i == 95 && a.active_count != 0) return 5;
    }
    /* A sequence gap must discard accumulated weak evidence. */
    for (i = 0; i < 23; ++i) {
        frame_make(words, 1, 0);
        if (p0_ed_pipeline_process(&ordinary, 100 + i, i == 0,
                (uint8_t *)words, BYTES, &a, &ac) || a.active_count) return 6;
    }
    if (p0_ed_pipeline_process(&ordinary, 200, 0, (uint8_t *)words, BYTES, &a, &ac) ||
        a.active_count || !a.reset_applied) return 7;
    /* Legacy A words must never acquire invented weak nominations. */
    for (i = 0; i < 40; ++i) {
        frame_make(words, 1, 1);
        if (p0_ed_pipeline_process(&ordinary, 300 + i, i == 0,
                (uint8_t *)words, BYTES, &a, &ac) || a.active_count) return 8;
    }
    frame_make(words, 0, 0);
    words[0] = ((uint64_t)0xA << 60); /* mixed versions */
    if (!p0_pl_os_cfar_decode_with_weak((uint8_t *)words, BYTES, trusted.raw_power,
        trusted.power, trusted.detections, &marked)) return 9;
    frame_make(words, 0, 0);
    words[20 ^ 2048] |= (uint64_t)1 << 59; /* strong without weak is inconsistent */
    if (!p0_pl_os_cfar_decode_with_weak((uint8_t *)words, BYTES, trusted.raw_power,
        trusted.power, trusted.detections, &marked)) return 10;
    p0_ed_pipeline_release(&ordinary); p0_ed_pipeline_release(&trusted);
    puts("ST06_PRODUCT_PIPELINE=PASS");
    return 0;
}
