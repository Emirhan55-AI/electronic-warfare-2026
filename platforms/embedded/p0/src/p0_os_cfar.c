#include "p0_os_cfar.h"

#include <math.h>
#include <string.h>

#define P0_CANONICAL_REFERENCE_PER_SIDE 16U
#define P0_CANONICAL_GUARD_PER_SIDE 4U
#define P0_CANONICAL_RANK 24U
#define P0_CANONICAL_PFA 1.0e-4
#define P0_CANONICAL_MAXIMUM_GAP 1U

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

static double false_alarm_probability(double coefficient, uint32_t reference_count, uint32_t rank) {
    uint32_t index;
    double probability = 1.0;
    for (index = 0U; index < rank; ++index) {
        double remaining = (double)(reference_count - index);
        probability *= remaining / (remaining + coefficient);
    }
    return probability;
}

P0_API int p0_os_cfar_threshold_coefficient(
    double desired_pfa,
    uint32_t reference_count,
    uint32_t order_statistic_rank,
    double *coefficient
) {
    double low = 0.0;
    double high = 1.0;
    uint32_t iteration;
    if (coefficient == NULL || !isfinite(desired_pfa) || desired_pfa <= 0.0 || desired_pfa >= 1.0 ||
        reference_count == 0U || order_statistic_rank == 0U || order_statistic_rank > reference_count) {
        return P0_OS_CFAR_INVALID_ARGUMENT;
    }
    while (false_alarm_probability(high, reference_count, order_statistic_rank) > desired_pfa) {
        high *= 2.0;
        if (!isfinite(high)) {
            return P0_OS_CFAR_INVALID_ARGUMENT;
        }
    }
    for (iteration = 0U; iteration < 160U; ++iteration) {
        double midpoint = (low + high) / 2.0;
        if (false_alarm_probability(midpoint, reference_count, order_statistic_rank) > desired_pfa) {
            low = midpoint;
        } else {
            high = midpoint;
        }
    }
    *coefficient = (low + high) / 2.0;
    return P0_OS_CFAR_OK;
}

P0_API int p0_os_cfar_canonical_config(p0_os_cfar_config_t *config) {
    if (config == NULL) {
        return P0_OS_CFAR_INVALID_ARGUMENT;
    }
    config->reference_cells_per_side = P0_CANONICAL_REFERENCE_PER_SIDE;
    config->guard_cells_per_side = P0_CANONICAL_GUARD_PER_SIDE;
    config->order_statistic_rank = P0_CANONICAL_RANK;
    config->maximum_gap_bins = P0_CANONICAL_MAXIMUM_GAP;
    return p0_os_cfar_threshold_coefficient(
        P0_CANONICAL_PFA,
        2U * P0_CANONICAL_REFERENCE_PER_SIDE,
        P0_CANONICAL_RANK,
        &config->threshold_coefficient
    );
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
