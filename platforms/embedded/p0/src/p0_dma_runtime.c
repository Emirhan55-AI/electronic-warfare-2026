#define _GNU_SOURCE

#include "p0_dma_runtime.h"

#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static ssize_t write_all(int descriptor, const uint8_t *buffer, size_t size)
{
    size_t written = 0U;

    while (written < size) {
        ssize_t result = write(descriptor, buffer + written, size - written);

        if (result < 0 && errno == EINTR)
            continue;
        if (result <= 0)
            return result;
        written += (size_t)result;
    }
    return (ssize_t)written;
}

static ssize_t read_packet(int descriptor, uint8_t *buffer, size_t capacity)
{
    ssize_t result;

    do {
        result = read(descriptor, buffer, capacity);
    } while (result < 0 && errno == EINTR);
    return result;
}

int p0_dma_runtime_open(p0_dma_runtime_t *runtime, const char *device_path)
{
    if (runtime == NULL || device_path == NULL) {
        errno = EINVAL;
        return -1;
    }
    runtime->descriptor = open(device_path, O_RDWR | O_CLOEXEC);
    return runtime->descriptor < 0 ? -1 : 0;
}

void p0_dma_runtime_close(p0_dma_runtime_t *runtime)
{
    if (runtime != NULL && runtime->descriptor >= 0) {
        close(runtime->descriptor);
        runtime->descriptor = -1;
    }
}

int p0_dma_runtime_get_detection_config(p0_dma_runtime_t *runtime,
                                        struct p0_detection_config *config)
{
    if (runtime == NULL || runtime->descriptor < 0 || config == NULL) {
        errno = EINVAL;
        return -1;
    }
    memset(config, 0, sizeof(*config));
    if (ioctl(runtime->descriptor, P0_DMA_IOC_GET_DETECTION_CONFIG, config) != 0)
        return -1;
    if (config->abi_version != P0_DETECTION_CONFIG_ABI) {
        errno = EPROTO;
        return -1;
    }
    return 0;
}

int p0_dma_runtime_set_detection_config(p0_dma_runtime_t *runtime,
                                        struct p0_detection_config *config)
{
    struct p0_detection_config requested;
    if (runtime == NULL || runtime->descriptor < 0 || config == NULL ||
        config->abi_version != P0_DETECTION_CONFIG_ABI ||
        config->alpha_q32 < (UINT64_C(1) << 32) || config->alpha_q32 >= (UINT64_C(1) << 36) ||
        config->weak_alpha_q32 < (UINT64_C(1) << 32) || config->weak_alpha_q32 >= (UINT64_C(1) << 34) ||
        config->weak_alpha_q32 > config->alpha_q32) {
        errno = EINVAL;
        return -1;
    }
    requested = *config;
    if (ioctl(runtime->descriptor, P0_DMA_IOC_SET_DETECTION_CONFIG, config) != 0)
        return -1;
    if (config->abi_version != P0_DETECTION_CONFIG_ABI ||
        config->generation != (uint32_t)(requested.generation + 1U) ||
        config->alpha_q32 != requested.alpha_q32 || config->weak_alpha_q32 != requested.weak_alpha_q32) {
        errno = EPROTO;
        return -1;
    }
    return 0;
}

int p0_dma_runtime_get_detection_profile(p0_dma_runtime_t *runtime,
                                         struct p0_detection_profile *profile)
{
    if (runtime == NULL || runtime->descriptor < 0 || profile == NULL) {
        errno = EINVAL;
        return -1;
    }
    memset(profile, 0, sizeof(*profile));
    if (ioctl(runtime->descriptor, P0_DMA_IOC_GET_DETECTION_PROFILE, profile) != 0)
        return -1;
    if (profile->abi_version != P0_DETECTION_PROFILE_ABI || profile->reserved != 0U ||
        (profile->fft_size != 4096U && profile->fft_size != 8192U &&
         profile->fft_size != 16384U)) {
        errno = EPROTO;
        return -1;
    }
    return 0;
}

int p0_dma_runtime_set_detection_profile(p0_dma_runtime_t *runtime,
                                         struct p0_detection_profile *profile)
{
    struct p0_detection_profile requested;

    if (runtime == NULL || runtime->descriptor < 0 || profile == NULL ||
        profile->abi_version != P0_DETECTION_PROFILE_ABI || profile->reserved != 0U ||
        (profile->fft_size != 4096U && profile->fft_size != 8192U &&
         profile->fft_size != 16384U) ||
        profile->alpha_q32 < (UINT64_C(1) << 32) ||
        profile->alpha_q32 >= (UINT64_C(1) << 36) ||
        profile->weak_alpha_q32 < (UINT64_C(1) << 32) ||
        profile->weak_alpha_q32 >= (UINT64_C(1) << 34) ||
        profile->weak_alpha_q32 > profile->alpha_q32) {
        errno = EINVAL;
        return -1;
    }
    requested = *profile;
    if (ioctl(runtime->descriptor, P0_DMA_IOC_SET_DETECTION_PROFILE, profile) != 0)
        return -1;
    if (profile->abi_version != P0_DETECTION_PROFILE_ABI ||
        profile->generation != (uint32_t)(requested.generation + 1U) ||
        profile->fft_size != requested.fft_size || profile->reserved != 0U ||
        profile->alpha_q32 != requested.alpha_q32 ||
        profile->weak_alpha_q32 != requested.weak_alpha_q32) {
        errno = EPROTO;
        return -1;
    }
    return 0;
}

int p0_dma_runtime_run(p0_dma_runtime_t *runtime, const uint8_t *input, size_t input_bytes,
                       uint8_t *output, size_t output_capacity,
                       size_t *actual_output_bytes, struct p0_dma_status *status)
{
    int saved;
    ssize_t received;

    if (runtime == NULL || runtime->descriptor < 0 || input == NULL || output == NULL ||
        actual_output_bytes == NULL || status == NULL ||
        (input_bytes != P0_DMA_INPUT_BYTES && input_bytes != 16384U &&
         input_bytes != P0_DMA_MAX_INPUT_BYTES) ||
        output_capacity < input_bytes * 4U) {
        errno = EINVAL;
        return -1;
    }
    *actual_output_bytes = 0U;
    memset(status, 0, sizeof(*status));
    if (write_all(runtime->descriptor, input, input_bytes) != (ssize_t)input_bytes)
        return -1;
    if (ioctl(runtime->descriptor, P0_DMA_IOC_RUN) != 0) {
        saved = errno;
        (void)ioctl(runtime->descriptor, P0_DMA_IOC_GET_STATUS, status);
        errno = saved;
        return -1;
    }
    if (ioctl(runtime->descriptor, P0_DMA_IOC_GET_STATUS, status) != 0)
        return -1;
    if ((status->abi_version != P0_DMA_ABI_VERSION &&
         status->abi_version != P0_DMA_RUNTIME_ABI_VERSION) ||
        status->input_bytes != input_bytes ||
        status->output_capacity_bytes < input_bytes * 4U ||
        status->output_bytes < P0_DMA_OUTPUT_MINIMUM_BYTES ||
        status->output_bytes > status->output_capacity_bytes ||
        status->output_bytes > output_capacity ||
        status->output_bytes % P0_DMA_OUTPUT_ALIGNMENT_BYTES != 0U ||
        status->mm2s_completed == 0U ||
        status->s2mm_completed == 0U || status->timed_out != 0U ||
        status->dma_error != 0U || status->output_valid == 0U) {
        errno = EIO;
        return -1;
    }
    received = read_packet(runtime->descriptor, output, output_capacity);
    if (received < 0)
        return -1;
    if ((size_t)received != status->output_bytes) {
        errno = EIO;
        return -1;
    }
    *actual_output_bytes = (size_t)received;
    return 0;
}
