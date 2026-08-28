#ifndef P0_MULTISCALE_DETECTOR_H
#define P0_MULTISCALE_DETECTOR_H

#include <stddef.h>
#include <stdint.h>

#include "p0_os_cfar.h"

enum {
    P0_MULTISCALE_OK = 0,
    P0_MULTISCALE_INVALID_ARGUMENT = -1,
    P0_MULTISCALE_CANDIDATE_OVERFLOW = -2,
    P0_MULTISCALE_FRAME_BINS = 4096,
    P0_MULTISCALE_REGION_BINS = 256,
    P0_MULTISCALE_INTEGRATION_BINS = 32,
    P0_MULTISCALE_INTEGRATION_LEFT = 15,
    P0_MULTISCALE_INTEGRATION_RIGHT = 16,
    P0_MULTISCALE_MINIMUM_RECOVERY_SPAN = 41,
    P0_MULTISCALE_MAX_RECOVERIES = 96
};

P0_API int p0_multiscale_process(
    const double *power,
    size_t power_count,
    const p0_os_cfar_config_t *os_config,
    uint8_t *detections,
    double *noise_power,
    double *threshold_power,
    p0_candidate_region_t *candidates,
    size_t candidate_capacity,
    size_t *candidate_count,
    size_t *recovery_count
);

P0_API int p0_multiscale_process_pl(
    const double *power,
    size_t power_count,
    const p0_os_cfar_config_t *os_config,
    uint8_t *detections,
    double *noise_power,
    double *threshold_power,
    p0_candidate_region_t *candidates,
    size_t candidate_capacity,
    size_t *candidate_count,
    size_t *recovery_count
);

/*
 * p0_pl_os_cfar_decode() sonrasında kullanılan doğrulanmış PL kısa yolu.
 * Dışarıdan sağlanan karar/güç dizilerinde kullanılmaz; strict API yukarıdaki
 * p0_multiscale_process_pl() olarak korunur.
 */
P0_API int p0_multiscale_process_pl_trusted(
    const double *power,
    size_t power_count,
    const p0_os_cfar_config_t *os_config,
    uint8_t *detections,
    double *noise_power,
    double *threshold_power,
    p0_candidate_region_t *candidates,
    size_t candidate_capacity,
    size_t *candidate_count,
    size_t *recovery_count
);

#endif
