#ifndef P0_DMA_RUNTIME_H
#define P0_DMA_RUNTIME_H

#include <stddef.h>
#include <stdint.h>

#include "p0_dma_uapi.h"

typedef struct {
    int descriptor;
} p0_dma_runtime_t;

int p0_dma_runtime_open(p0_dma_runtime_t *runtime, const char *device_path);
void p0_dma_runtime_close(p0_dma_runtime_t *runtime);
int p0_dma_runtime_run(p0_dma_runtime_t *runtime, const uint8_t *input, size_t input_bytes,
                       uint8_t *output, size_t output_capacity,
                       size_t *actual_output_bytes, struct p0_dma_status *status);

#endif
