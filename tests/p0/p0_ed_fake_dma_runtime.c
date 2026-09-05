#include "p0_dma_runtime.h"

#include <errno.h>
#include <string.h>

#define P0_FAKE_POWER_BYTES (4096U * 8U)
#define P0_FAKE_POWER_MASK ((UINT64_C(1) << 58U) - UINT64_C(1))
#define P0_FAKE_EVALUATED_MASK (UINT64_C(1) << 58U)
#define P0_FAKE_DETECTED_MASK (UINT64_C(1) << 59U)
#define P0_FAKE_FORMAT_MARKER (UINT64_C(0xA) << 60U)

static void store_u64_le(uint8_t *target, uint64_t value)
{
    unsigned int index;

    for (index = 0U; index < 8U; ++index)
        target[index] = (uint8_t)(value >> (index * 8U));
}

int p0_dma_runtime_open(p0_dma_runtime_t *runtime, const char *device_path)
{
    if (runtime == NULL || device_path == NULL) {
        errno = EINVAL;
        return -1;
    }
    runtime->descriptor = 101;
    return 0;
}

void p0_dma_runtime_close(p0_dma_runtime_t *runtime)
{
    if (runtime != NULL)
        runtime->descriptor = -1;
}

int p0_dma_runtime_run(p0_dma_runtime_t *runtime, const uint8_t *input, size_t input_bytes,
                       uint8_t *output, size_t output_capacity,
                       size_t *actual_output_bytes, struct p0_dma_status *status)
{
    size_t index;
    int empty = 1;

    if (runtime == NULL || runtime->descriptor < 0 || input == NULL || output == NULL ||
        actual_output_bytes == NULL || status == NULL || input_bytes != P0_DMA_INPUT_BYTES ||
        output_capacity < P0_DMA_OUTPUT_CAPACITY_BYTES) {
        errno = EINVAL;
        return -1;
    }
    for (index = 0U; index < input_bytes; ++index) {
        if (input[index] != 0U) {
            empty = 0;
            break;
        }
    }
    memset(output, 0, output_capacity);
    if (input[0] == 0x7EU) {
        *actual_output_bytes = P0_DMA_OUTPUT_MINIMUM_BYTES;
    } else {
        for (index = 0U; index < 4096U; ++index) {
            size_t shifted_bin = index ^ 2048U;
            uint64_t power = UINT64_C(100) << 30U;
            uint64_t word = P0_FAKE_FORMAT_MARKER;

            if (shifted_bin >= 20U && shifted_bin < 4076U)
                word |= P0_FAKE_EVALUATED_MASK;
            if (!empty && shifted_bin >= 2280U && shifted_bin <= 2328U) {
                power = (shifted_bin == 2304U ? UINT64_C(1000000)
                                              : UINT64_C(10000)) << 30U;
                word |= P0_FAKE_DETECTED_MASK;
            }
            word |= power & P0_FAKE_POWER_MASK;
            store_u64_le(output + index * 8U, word);
        }
        *actual_output_bytes = P0_FAKE_POWER_BYTES;
    }
    memset(status, 0, sizeof(*status));
    status->abi_version = P0_DMA_ABI_VERSION;
    status->input_bytes = P0_DMA_INPUT_BYTES;
    status->output_capacity_bytes = P0_DMA_OUTPUT_CAPACITY_BYTES;
    status->output_bytes = (uint32_t)*actual_output_bytes;
    status->input_loaded = 1U;
    status->output_valid = 1U;
    status->mm2s_completed = 1U;
    status->s2mm_completed = 1U;
    return 0;
}
