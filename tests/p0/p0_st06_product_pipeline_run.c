#include "p0_ed_pipeline.h"
#include "p0_pl_os_cfar.h"

#include <stdint.h>
#include <float.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FRAME_BINS 4096U
#define FRAME_BYTES (FRAME_BINS * 8U)
#define POWER_MASK ((UINT64_C(1) << 58U) - UINT64_C(1))
#define EVALUATED_MASK (UINT64_C(1) << 58U)
#define DETECTED_MASK (UINT64_C(1) << 59U)
#define FORMAT_MARKER (UINT64_C(0xA) << 60U)

static void store_u64_le(uint8_t *target, uint64_t value)
{
    unsigned int index;

    for (index = 0U; index < 8U; ++index)
        target[index] = (uint8_t)(value >> (index * 8U));
}

static void make_frame(uint8_t *frame, uint32_t start, uint32_t end,
                       uint32_t peak, int mark_narrow)
{
    uint32_t natural_bin;

    for (natural_bin = 0U; natural_bin < FRAME_BINS; ++natural_bin) {
        uint32_t shifted_bin = natural_bin ^ (FRAME_BINS / 2U);
        uint64_t power = UINT64_C(100) << 30U;
        uint64_t word = FORMAT_MARKER;

        if (shifted_bin >= 20U && shifted_bin < FRAME_BINS - 20U)
            word |= EVALUATED_MASK;
        if (start <= end && shifted_bin >= start && shifted_bin <= end) {
            power = (shifted_bin == peak ? UINT64_C(1000000)
                                         : UINT64_C(10000)) << 30U;
            if (mark_narrow)
                word |= DETECTED_MASK;
        }
        store_u64_le(frame + natural_bin * 8U, word | (power & POWER_MASK));
    }
}

static int process(p0_ed_pipeline_t *pipeline, uint32_t frame_id, int reset,
                   const uint8_t *frame, phase06j_frame_result_v1 *result,
                   size_t *raw_candidates)
{
    return p0_ed_pipeline_process(pipeline, frame_id, reset, frame, FRAME_BYTES,
                                  result, raw_candidates);
}

static int decoded_path_equivalence(void)
{
    p0_ed_pipeline_t ordinary, decoded;
    uint8_t frame[FRAME_BYTES];
    phase06j_frame_result_v1 a, b;
    size_t ac, bc;
    uint32_t i;
    int marked, status = -1;
    if (p0_ed_pipeline_init(&ordinary) != 0) return -1;
    if (p0_ed_pipeline_init(&decoded) != 0) {
        p0_ed_pipeline_release(&ordinary); return -1;
    }
    for (i = 0; i < 48; ++i) {
        uint32_t id = i < 24 ? i : i + 3;
        make_frame(frame, i < 16 ? 2300 : 3072, i < 16 ? 2500 : 3072,
                   i < 16 ? 2400 : 3072, 1);
        if (p0_pl_os_cfar_decode(frame, FRAME_BYTES, decoded.raw_power,
                decoded.power, decoded.detections, &marked) != 0 ||
            process(&ordinary, id, i == 0 || i == 32, frame, &a, &ac) != 0 ||
            p0_ed_pipeline_process_decoded_trusted(&decoded, id, i == 0 || i == 32,
                marked, &b, &bc) != 0 || ac != bc || memcmp(&a, &b, sizeof(a)) != 0 ||
            memcmp(ordinary.wideband_stream_state, decoded.wideband_stream_state,
                ordinary.wideband_stream_state_bytes) != 0)
            goto done;
    }
    status = 0;
done:
    p0_ed_pipeline_release(&ordinary);
    p0_ed_pipeline_release(&decoded);
    return status;
}

static int checkpoint_roundtrip(void)
{
    size_t bytes = p0_st05_stream_state_bytes();
    size_t checkpoint_bytes = p0_st05_stream_checkpoint_bytes();
    void *state = malloc(bytes);
    void *before = malloc(bytes);
    void *checkpoint = malloc(checkpoint_bytes);
    double *power = malloc(FRAME_BINS * sizeof(*power));
    p0_st05_result_t expected, actual;
    int expected_valid, actual_valid;
    uint32_t frame, bin;
    int status = -1;
    if (!state || !before || !checkpoint || !power || checkpoint_bytes >= bytes)
        goto done;
    if (p0_st05_stream_init(state, bytes) != P0_ST05_OK)
        goto done;
    for (frame = 0; frame < 25; ++frame) {
        for (bin = 0; bin < FRAME_BINS; ++bin)
            power[bin] = 100.0 + (double)((bin * 13U + frame * 7U) % 19U) +
                         (bin >= 2300U && bin <= 2500U ? 2000.0 : 0.0);
        memcpy(before, state, bytes);
        if (p0_st05_stream_checkpoint_save(state, bytes, checkpoint, checkpoint_bytes) != 0 ||
            p0_st05_stream_update(state, bytes, power, FRAME_BINS, &expected, &expected_valid) != 0 ||
            p0_st05_stream_checkpoint_restore(state, bytes, checkpoint, checkpoint_bytes) != 0 ||
            memcmp(before, state, bytes) != 0 ||
            p0_st05_stream_update(state, bytes, power, FRAME_BINS, &actual, &actual_valid) != 0 ||
            actual_valid != expected_valid || memcmp(&actual, &expected, sizeof(actual)) != 0)
            goto done;
    }
    status = 0;
done:
    free(power); free(checkpoint); free(before); free(state);
    return status;
}

int main(void)
{
    p0_ed_pipeline_t pipeline;
    phase06j_frame_result_v1 result;
    uint8_t *frame = malloc(FRAME_BYTES);
    size_t raw_candidates = 0U;
    uint32_t frame_id;

    if (frame == NULL || p0_ed_pipeline_init(&pipeline) != 0)
        return EXIT_FAILURE;
    if (decoded_path_equivalence() != 0 || checkpoint_roundtrip() != 0) {
        fputs("checkpoint rollback or repeated update changed state\n", stderr);
        goto failed;
    }

    make_frame(frame, 2600U, 2600U, 2600U, 1);
    if (process(&pipeline, 0U, 1, frame, &result, &raw_candidates) != 0 ||
        result.active_count != 1U || result.active[0].state != PHASE06J_EVENT_TENTATIVE ||
        process(&pipeline, 1U, 0, frame, &result, &raw_candidates) != 0 ||
        result.active_count != 1U || result.active[0].state != PHASE06J_EVENT_CONFIRMED ||
        (result.active[0].candidate.flags & PHASE06I_RECORD_WIDEBAND_EVIDENCE) != 0U) {
        fputs("narrowband lifecycle failed\n", stderr);
        goto failed;
    }

    {
        void *before = malloc(pipeline.wideband_stream_state_bytes);
        void *temporal = malloc(phase06j_state_bytes());
        double coefficient = pipeline.config.threshold_coefficient;
        int reset;
        if (!before || !temporal) { free(before); free(temporal); goto failed; }
        memcpy(before, pipeline.wideband_stream_state, pipeline.wideband_stream_state_bytes);
        memcpy(temporal, pipeline.temporal_state, phase06j_state_bytes());
        for (reset = 0; reset <= 1; ++reset) {
            /* Failure after stream update exercises both compact/full rollback. */
            pipeline.config.threshold_coefficient = DBL_MAX;
            if (process(&pipeline, 2U, reset, frame, &result, &raw_candidates) == 0 ||
                memcmp(before, pipeline.wideband_stream_state,
                       pipeline.wideband_stream_state_bytes) != 0 ||
                memcmp(temporal, pipeline.temporal_state, phase06j_state_bytes()) != 0 ||
                pipeline.wideband_last_frame_id != 1U) {
                free(before); free(temporal);
                fputs("pipeline post-update rollback failed\n", stderr);
                goto failed;
            }
        }
        pipeline.config.threshold_coefficient = coefficient;
        free(before); free(temporal);
    }

    make_frame(frame, 2300U, 2500U, 2400U, 0);
    for (frame_id = 10U; frame_id < 18U; ++frame_id) {
        if (process(&pipeline, frame_id, frame_id == 10U, frame, &result,
                    &raw_candidates) != 0)
            goto failed;
    }
    if (raw_candidates != 1U || result.active_count != 1U ||
        result.active[0].state != PHASE06J_EVENT_TENTATIVE ||
        (result.active[0].candidate.flags & PHASE06I_RECORD_WIDEBAND_EVIDENCE) == 0U ||
        result.active[0].candidate.start_shifted_bin > 2400U ||
        result.active[0].candidate.end_shifted_bin < 2400U ||
        result.active[0].candidate.regional_noise_uq28_30 == 0U ||
        result.active[0].candidate.threshold_uq32_30 <=
            result.active[0].candidate.regional_noise_uq28_30) {
        fputs("wideband warmup failed\n", stderr);
        goto failed;
    }
    if (process(&pipeline, 18U, 0, frame, &result, &raw_candidates) != 0 ||
        result.active_count != 1U || result.active[0].state != PHASE06J_EVENT_CONFIRMED ||
        (result.active[0].candidate.flags & PHASE06I_RECORD_WIDEBAND_EVIDENCE) == 0U) {
        fputs("wideband confirmation failed\n", stderr);
        goto failed;
    }

    make_frame(frame, 1U, 0U, 0U, 0);
    for (frame_id = 19U; frame_id <= 22U; ++frame_id) {
        if (process(&pipeline, frame_id, 0, frame, &result, &raw_candidates) != 0)
            goto failed;
    }
    if (result.active_count != 0U || result.ended_count != 1U ||
        result.ended[0].state != PHASE06J_EVENT_ENDED ||
        (result.ended[0].candidate.flags & PHASE06I_RECORD_WIDEBAND_EVIDENCE) == 0U) {
        fputs("wideband expiry failed\n", stderr);
        goto failed;
    }

    make_frame(frame, 2300U, 2500U, 2400U, 1);
    for (frame_id = 30U; frame_id < 38U; ++frame_id) {
        if (process(&pipeline, frame_id, frame_id == 30U, frame, &result,
                    &raw_candidates) != 0)
            goto failed;
    }
    if (raw_candidates != 1U || result.active_count != 1U ||
        result.active[0].state != PHASE06J_EVENT_CONFIRMED ||
        (result.active[0].candidate.flags & PHASE06I_RECORD_WIDEBAND_EVIDENCE) == 0U) {
        fputs("wideband suppression failed\n", stderr);
        goto failed;
    }

    make_frame(frame, 1U, 0U, 0U, 0);
    if (process(&pipeline, 50U, 0, frame, &result, &raw_candidates) != 0 ||
        result.reset_applied == 0U || result.active_count != 0U) {
        fputs("discontinuity reset failed\n", stderr);
        goto failed;
    }

    puts("ST06_PRODUCT_PIPELINE=PASS");
    p0_ed_pipeline_release(&pipeline);
    free(frame);
    return EXIT_SUCCESS;

failed:
    p0_ed_pipeline_release(&pipeline);
    free(frame);
    return EXIT_FAILURE;
}
