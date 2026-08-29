#include "p0_dma_runtime.h"

#include "p0_candidate_packet.h"

#include <errno.h>
#include <string.h>

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
    static uint32_t next_frame_id;
    p0_candidate_region_t candidate;
    p0_os_cfar_config_t config;
    uint64_t shifted_power[4096];
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
        memset(&config, 0, sizeof(config));
        config.threshold_coefficient = 2.0;
        memset(&candidate, 0, sizeof(candidate));
        for (index = 0U; index < 4096U; ++index)
            shifted_power[index] = UINT64_C(100) << 30;
        candidate.start_bin = 2280U;
        candidate.end_bin = 2328U;
        candidate.peak_bin = 2304U;
        candidate.peak_power = 1000000.0;
        candidate.noise_power_per_bin = 100.0;
        candidate.threshold_power = 200.0;
        shifted_power[candidate.peak_bin] = UINT64_C(1000000) << 30;
        if (p0_candidate_packet_encode(
                next_frame_id, shifted_power, 4096U, &config,
                empty ? NULL : &candidate, empty ? 0U : 1U, output,
                output_capacity, actual_output_bytes) != P0_CANDIDATE_PACKET_OK) {
            errno = EIO;
            return -1;
        }
        ++next_frame_id;
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
