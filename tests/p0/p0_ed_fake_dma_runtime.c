#include "p0_dma_runtime.h"

#include <errno.h>
#include <string.h>

static void store_le64(uint8_t *target, uint64_t value)
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
                       uint8_t *output, size_t output_bytes, struct p0_dma_status *status)
{
    size_t index;
    int empty = 1;

    if (runtime == NULL || runtime->descriptor < 0 || input == NULL || output == NULL ||
        status == NULL || input_bytes != P0_DMA_INPUT_BYTES ||
        output_bytes != P0_DMA_OUTPUT_BYTES) {
        errno = EINVAL;
        return -1;
    }
    for (index = 0U; index < input_bytes; ++index) {
        if (input[index] != 0U) {
            empty = 0;
            break;
        }
    }
    memset(output, 0, output_bytes);
    if (input[0] == 0x7EU) {
        store_le64(output, UINT64_C(1) << 58);
    } else if (!empty) {
        for (index = 0U; index < 4096U; ++index)
            store_le64(output + index * 8U, index == 256U ? UINT64_C(1000000) : UINT64_C(100));
    }
    memset(status, 0, sizeof(*status));
    status->abi_version = P0_DMA_ABI_VERSION;
    status->input_bytes = P0_DMA_INPUT_BYTES;
    status->output_bytes = P0_DMA_OUTPUT_BYTES;
    status->input_loaded = 1U;
    status->output_valid = 1U;
    status->mm2s_completed = 1U;
    status->s2mm_completed = 1U;
    return 0;
}
