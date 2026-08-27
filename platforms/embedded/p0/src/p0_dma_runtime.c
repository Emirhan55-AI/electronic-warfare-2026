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

static ssize_t read_all(int descriptor, uint8_t *buffer, size_t size)
{
    size_t received = 0U;

    while (received < size) {
        ssize_t result = read(descriptor, buffer + received, size - received);

        if (result < 0 && errno == EINTR)
            continue;
        if (result <= 0)
            return result;
        received += (size_t)result;
    }
    return (ssize_t)received;
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

int p0_dma_runtime_run(p0_dma_runtime_t *runtime, const uint8_t *input, size_t input_bytes,
                       uint8_t *output, size_t output_bytes, struct p0_dma_status *status)
{
    int saved;

    if (runtime == NULL || runtime->descriptor < 0 || input == NULL || output == NULL ||
        status == NULL || input_bytes != P0_DMA_INPUT_BYTES ||
        output_bytes != P0_DMA_OUTPUT_BYTES) {
        errno = EINVAL;
        return -1;
    }
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
    if (status->abi_version != P0_DMA_ABI_VERSION || status->input_bytes != P0_DMA_INPUT_BYTES ||
        status->output_bytes != P0_DMA_OUTPUT_BYTES || status->mm2s_completed == 0U ||
        status->s2mm_completed == 0U || status->timed_out != 0U ||
        status->dma_error != 0U || status->output_valid == 0U) {
        errno = EIO;
        return -1;
    }
    if (read_all(runtime->descriptor, output, output_bytes) != (ssize_t)output_bytes)
        return -1;
    return 0;
}
