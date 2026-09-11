#ifndef P0_PL_OS_CFAR_H
#define P0_PL_OS_CFAR_H

#include <stddef.h>
#include <stdint.h>

#ifdef _WIN32
#define P0_PL_API __declspec(dllexport)
#else
#define P0_PL_API
#endif

/* v2: bit 0 strong, bit 1 weak nomination. Legacy formats yield bit 0 only. */
P0_PL_API int p0_pl_os_cfar_decode_with_weak(
    const uint8_t *words, size_t bytes, uint64_t *raw,
    double *power, uint8_t *detections, int *present);

/* Runtime FFT v2 frames are reduced onto the established 4096-bin ARM grid. */
P0_PL_API int p0_pl_os_cfar_decode_runtime_with_weak(
    const uint8_t *words, size_t bytes, size_t native_bins,
    uint64_t *canonical_raw, double *canonical_power,
    uint8_t *canonical_detections, int *present);

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
