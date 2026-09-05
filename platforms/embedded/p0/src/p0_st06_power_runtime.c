#include "p0_st06_power_runtime.h"

#include <errno.h>
#include <stdlib.h>
#include <string.h>

#include "p0_pl_os_cfar.h"
#include "p0_st05_stream.h"

#define P0_ST06_POWER_MASK ((UINT64_C(1) << 58U) - UINT64_C(1))
#define P0_ST06_EVALUATED_MASK (UINT64_C(1) << 58U)
#define P0_ST06_DETECTED_MASK (UINT64_C(1) << 59U)
#define P0_ST06_FORMAT_MARKER (UINT64_C(0xA) << 60U)
#define P0_ST06_FORMAT_MASK (UINT64_C(0xF) << 60U)
#define P0_ST06_POWER_SCALE (UINT64_C(1) << 30U)

static uint64_t load_u64_le(const uint8_t *source)
{
    uint64_t value;

    memcpy(&value, source, sizeof(value));
#if defined(__BYTE_ORDER__) && __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    value = __builtin_bswap64(value);
#endif
    return value;
}

static int decode_marked_power_frame(
    const uint8_t *natural_words,
    p0_st06_power_runtime_t *runtime
)
{
    size_t natural_bin;

    for (natural_bin = 0U; natural_bin < P0_PL_OS_CFAR_FRAME_BINS; ++natural_bin) {
        size_t shifted_bin = natural_bin ^ (P0_PL_OS_CFAR_FRAME_BINS / 2U);
        uint64_t word = load_u64_le(natural_words + natural_bin * 8U);
        uint64_t power = word & P0_ST06_POWER_MASK;
        int expected_evaluated =
            shifted_bin >= P0_PL_OS_CFAR_RADIUS &&
            shifted_bin < P0_PL_OS_CFAR_FRAME_BINS - P0_PL_OS_CFAR_RADIUS;
        int evaluated = (word & P0_ST06_EVALUATED_MASK) != 0U;
        int detected = (word & P0_ST06_DETECTED_MASK) != 0U;

        if ((word & P0_ST06_FORMAT_MASK) != P0_ST06_FORMAT_MARKER ||
            evaluated != expected_evaluated || (detected && !evaluated))
            return -1;
        runtime->shifted_power_uq28_30[shifted_bin] = power;
        runtime->shifted_power[shifted_bin] =
            (double)power / (double)P0_ST06_POWER_SCALE;
        runtime->shifted_detections[shifted_bin] = detected ? 1U : 0U;
    }
    return 0;
}

static int runtime_ready(const p0_st06_power_runtime_t *runtime)
{
    return runtime != NULL && runtime->shifted_power != NULL &&
           runtime->shifted_power_uq28_30 != NULL &&
           runtime->shifted_detections != NULL && runtime->stream_state != NULL &&
           runtime->stream_state_bytes == p0_st05_stream_state_bytes();
}

int p0_st06_power_runtime_init(p0_st06_power_runtime_t *runtime)
{
    if (runtime == NULL) {
        errno = EINVAL;
        return -1;
    }
    memset(runtime, 0, sizeof(*runtime));
    runtime->stream_state_bytes = p0_st05_stream_state_bytes();
    runtime->shifted_power = calloc(P0_PL_OS_CFAR_FRAME_BINS,
                                    sizeof(*runtime->shifted_power));
    runtime->shifted_power_uq28_30 = calloc(
        P0_PL_OS_CFAR_FRAME_BINS, sizeof(*runtime->shifted_power_uq28_30));
    runtime->shifted_detections = calloc(
        P0_PL_OS_CFAR_FRAME_BINS, sizeof(*runtime->shifted_detections));
    runtime->stream_state = calloc(1U, runtime->stream_state_bytes);
    if (!runtime_ready(runtime) ||
        p0_st05_stream_init(runtime->stream_state,
                            runtime->stream_state_bytes) != P0_ST05_OK) {
        p0_st06_power_runtime_release(runtime);
        errno = ENOMEM;
        return -1;
    }
    return 0;
}

void p0_st06_power_runtime_release(p0_st06_power_runtime_t *runtime)
{
    if (runtime == NULL)
        return;
    free(runtime->stream_state);
    free(runtime->shifted_detections);
    free(runtime->shifted_power_uq28_30);
    free(runtime->shifted_power);
    memset(runtime, 0, sizeof(*runtime));
}

int p0_st06_power_runtime_reset(p0_st06_power_runtime_t *runtime)
{
    if (!runtime_ready(runtime)) {
        errno = EINVAL;
        return -1;
    }
    if (p0_st05_stream_reset(runtime->stream_state,
                             runtime->stream_state_bytes) != P0_ST05_OK) {
        errno = EPROTO;
        return -1;
    }
    runtime->last_frame_id = 0U;
    runtime->has_frame_id = 0;
    return 0;
}

int p0_st06_power_runtime_process(
    p0_st06_power_runtime_t *runtime,
    uint32_t frame_id,
    int reset_requested,
    const uint8_t *natural_power_words,
    size_t power_bytes,
    p0_st05_result_t *result,
    int *result_valid,
    int *context_reset_applied
)
{
    int discontinuity;
    int code;

    if (!runtime_ready(runtime) || natural_power_words == NULL || result == NULL ||
        result_valid == NULL || context_reset_applied == NULL ||
        power_bytes != P0_PL_OS_CFAR_FRAME_BYTES) {
        errno = EINVAL;
        return -1;
    }
    code = decode_marked_power_frame(natural_power_words, runtime);
    if (code != 0) {
        errno = EPROTO;
        return -1;
    }

    discontinuity = runtime->has_frame_id &&
                    frame_id != runtime->last_frame_id + UINT32_C(1);
    *context_reset_applied = reset_requested || discontinuity;
    if (*context_reset_applied && p0_st06_power_runtime_reset(runtime) != 0)
        return -1;
    code = p0_st05_stream_update(
        runtime->stream_state, runtime->stream_state_bytes,
        runtime->shifted_power, P0_PL_OS_CFAR_FRAME_BINS, result, result_valid);
    if (code != P0_ST05_OK) {
        errno = EPROTO;
        return -1;
    }
    runtime->last_frame_id = frame_id;
    runtime->has_frame_id = 1;
    return 0;
}
