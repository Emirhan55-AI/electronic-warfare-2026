#ifndef P0_OS_CFAR_H
#define P0_OS_CFAR_H

#include <stddef.h>
#include <stdint.h>

#ifdef _WIN32
#define P0_API __declspec(dllexport)
#else
#define P0_API
#endif
#ifdef __cplusplus
extern "C" {
#endif

enum {
    P0_OS_CFAR_OK = 0,
    P0_OS_CFAR_INVALID_ARGUMENT = -1,
    P0_OS_CFAR_NONFINITE_POWER = -2,
    P0_OS_CFAR_CANDIDATE_OVERFLOW = -3,
    P0_OS_CFAR_MAX_REFERENCE_CELLS = 128
};

typedef struct {
    uint32_t reference_cells_per_side;
    uint32_t guard_cells_per_side;
    uint32_t order_statistic_rank;
    double threshold_coefficient;
    uint32_t maximum_gap_bins;
} p0_os_cfar_config_t;

typedef struct {
    uint32_t start_bin;
    uint32_t end_bin;
    uint32_t peak_bin;
    double peak_power;
    double noise_power_per_bin;
    double threshold_power;
} p0_candidate_region_t;

P0_API int p0_os_cfar_process(
    const double *power,
    size_t power_count,
    const p0_os_cfar_config_t *config,
    uint8_t *detections,
    double *noise_power,
    double *threshold_power,
    p0_candidate_region_t *candidates,
    size_t candidate_capacity,
    size_t *candidate_count
);

#ifdef __cplusplus
}
#endif

#endif
