#ifndef P0_PL_OS_CFAR_H
#define P0_PL_OS_CFAR_H

#include <stddef.h>
#include <stdint.h>

#ifdef _WIN32
#define P0_PL_API __declspec(dllexport)
#else
#define P0_PL_API
#endif

enum {
    P0_PL_OS_CFAR_OK = 0,
    P0_PL_OS_CFAR_INVALID_ARGUMENT = -1,
    P0_PL_OS_CFAR_INVALID_FRAME = -2,
    P0_PL_OS_CFAR_FRAME_BINS = 4096,
    P0_PL_OS_CFAR_FRAME_BYTES = P0_PL_OS_CFAR_FRAME_BINS * 8,
    P0_PL_OS_CFAR_RADIUS = 20
};

P0_PL_API int p0_pl_os_cfar_decode(
    const uint8_t *natural_words,
    size_t frame_bytes,
    uint64_t *shifted_power_uq28_30,
    double *shifted_power,
    uint8_t *shifted_detections,
    int *pl_decisions_present
);

#endif
