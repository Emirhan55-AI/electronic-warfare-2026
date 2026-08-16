#include "p0_os_cfar.h"

#include <math.h>
#include <string.h>

static void insertion_sort(double *values, size_t count) {
    size_t index;
    for (index = 1U; index < count; ++index) {
        double key = values[index];
        size_t position = index;
        while (position > 0U && values[position - 1U] > key) {
            values[position] = values[position - 1U];
            --position;
        }
        values[position] = key;
    }
}
static int valid_config(const p0_os_cfar_config_t *config) {
    uint64_t reference_total;
    if (config == NULL || config->reference_cells_per_side == 0U ||
        config->reference_cells_per_side > P0_OS_CFAR_MAX_REFERENCE_CELLS / 2U ||
        !isfinite(config->threshold_coefficient) || config->threshold_coefficient <= 0.0) {
        return 0;
    }
    reference_total = 2ULL * config->reference_cells_per_side;
    return config->order_statistic_rank >= 1U && config->order_statistic_rank <= reference_total;
}

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
) {
    size_t index;
    size_t radius;
    size_t output_count = 0U;
    double references[P0_OS_CFAR_MAX_REFERENCE_CELLS];

    if (power == NULL || power_count < 3U || !valid_config(config) || detections == NULL ||
        noise_power == NULL || threshold_power == NULL || candidates == NULL || candidate_count == NULL) {
        return P0_OS_CFAR_INVALID_ARGUMENT;
    }
    radius = (size_t)config->reference_cells_per_side + config->guard_cells_per_side;
    memset(detections, 0, power_count * sizeof(*detections));
    for (index = 0U; index < power_count; ++index) {
        if (!isfinite(power[index]) || power[index] < 0.0) {
            return P0_OS_CFAR_NONFINITE_POWER;
        }
        noise_power[index] = NAN;
        threshold_power[index] = NAN;
    }
    if (power_count <= 2U * radius) {
        *candidate_count = 0U;
        return P0_OS_CFAR_OK;
    }

    for (index = radius; index < power_count - radius; ++index) {
        size_t reference_index = 0U;
        size_t source;
        size_t right_start = index + config->guard_cells_per_side + 1U;
        double noise;
        for (source = index - radius; source < index - config->guard_cells_per_side; ++source) {
            references[reference_index++] = power[source];
        }
        for (source = right_start; source < right_start + config->reference_cells_per_side; ++source) {
            references[reference_index++] = power[source];
        }
        insertion_sort(references, reference_index);
        noise = references[config->order_statistic_rank - 1U];
        noise_power[index] = noise;
        threshold_power[index] = noise * config->threshold_coefficient;
        detections[index] = power[index] > threshold_power[index] ? 1U : 0U;
    }

    index = radius;
    while (index < power_count - radius) {
        size_t start;
        size_t end;
        size_t peak;
        if (detections[index] == 0U) {
            ++index;
            continue;
        }
        start = index;
        end = index;
        peak = index;
        ++index;
        while (index < power_count - radius) {
            if (detections[index] != 0U) {
                if (index - end > (size_t)config->maximum_gap_bins + 1U) {
                    break;
                }
                end = index;
                if (power[index] > power[peak]) {
                    peak = index;
                }
            } else if (index - end > (size_t)config->maximum_gap_bins + 1U) {
                break;
            }
            ++index;
        }
        if (output_count >= candidate_capacity) {
            *candidate_count = output_count;
            return P0_OS_CFAR_CANDIDATE_OVERFLOW;
        }
        candidates[output_count].start_bin = (uint32_t)start;
        candidates[output_count].end_bin = (uint32_t)end;
        candidates[output_count].peak_bin = (uint32_t)peak;
        candidates[output_count].peak_power = power[peak];
        candidates[output_count].noise_power_per_bin = noise_power[peak];
        candidates[output_count].threshold_power = threshold_power[peak];
        ++output_count;
    }
    *candidate_count = output_count;
    return P0_OS_CFAR_OK;
}
