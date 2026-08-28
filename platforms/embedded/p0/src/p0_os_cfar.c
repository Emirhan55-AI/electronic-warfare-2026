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

static size_t sorted_lower_bound(const double *values, size_t count, double value) {
    size_t first = 0U;

    while (first < count) {
        size_t middle = first + (count - first) / 2U;

        if (values[middle] < value) {
            first = middle + 1U;
        } else {
            count = middle;
        }
    }
    return first;
}

static size_t sorted_upper_bound(const double *values, size_t count, double value) {
    size_t first = 0U;

    while (first < count) {
        size_t middle = first + (count - first) / 2U;

        if (values[middle] <= value) {
            first = middle + 1U;
        } else {
            count = middle;
        }
    }
    return first;
}

static int sorted_remove_one(double *values, size_t count, double value) {
    size_t position = sorted_lower_bound(values, count, value);

    if (position == count || values[position] != value)
        return -1;
    if (position + 1U < count) {
        memmove(values + position, values + position + 1U,
                (count - position - 1U) * sizeof(*values));
    }
    return 0;
}

static void sorted_insert(double *values, size_t count, double value) {
    size_t position = sorted_upper_bound(values, count, value);
    if (position < count) {
        memmove(values + position + 1U, values + position,
                (count - position) * sizeof(*values));
    }
    values[position] = value;
}

static double sorted_union_order_statistic(
    const double *first,
    size_t first_count,
    const double *second,
    size_t second_count,
    size_t rank
)
{
    size_t low;
    size_t high;

    if (first_count > second_count)
        return sorted_union_order_statistic(second, second_count,
                                            first, first_count, rank);
    low = rank > second_count ? rank - second_count : 0U;
    high = rank < first_count ? rank : first_count;
    for (;;) {
        size_t first_partition = low + (high - low) / 2U;
        size_t second_partition = rank - first_partition;

        if (first_partition > 0U && second_partition < second_count &&
            first[first_partition - 1U] > second[second_partition]) {
            high = first_partition - 1U;
            continue;
        }
        if (second_partition > 0U && first_partition < first_count &&
            second[second_partition - 1U] > first[first_partition]) {
            low = first_partition + 1U;
            continue;
        }
        if (first_partition == 0U)
            return second[second_partition - 1U];
        if (second_partition == 0U)
            return first[first_partition - 1U];
        return first[first_partition - 1U] > second[second_partition - 1U]
                   ? first[first_partition - 1U]
                   : second[second_partition - 1U];
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
    size_t reference_per_side;
    size_t output_count = 0U;
    double left_references[P0_OS_CFAR_MAX_REFERENCE_CELLS / 2U];
    double right_references[P0_OS_CFAR_MAX_REFERENCE_CELLS / 2U];

    if (power == NULL || power_count < 3U || !valid_config(config) || detections == NULL ||
        noise_power == NULL || threshold_power == NULL || candidates == NULL || candidate_count == NULL) {
        return P0_OS_CFAR_INVALID_ARGUMENT;
    }
    radius = (size_t)config->reference_cells_per_side + config->guard_cells_per_side;
    reference_per_side = config->reference_cells_per_side;
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

    {
        size_t left_index = 0U;
        size_t right_index = 0U;
        size_t source;
        size_t right_start;

        index = radius;
        right_start = index + config->guard_cells_per_side + 1U;
        for (source = index - radius;
             source < index - config->guard_cells_per_side; ++source) {
            left_references[left_index++] = power[source];
        }
        for (source = right_start;
             source < right_start + config->reference_cells_per_side; ++source) {
            right_references[right_index++] = power[source];
        }
        insertion_sort(left_references, left_index);
        insertion_sort(right_references, right_index);
    }
    for (index = radius; index < power_count - radius; ++index) {
        double noise;

        noise = sorted_union_order_statistic(
            left_references, reference_per_side,
            right_references, reference_per_side,
            config->order_statistic_rank);
        noise_power[index] = noise;
        threshold_power[index] = noise * config->threshold_coefficient;
        detections[index] = power[index] > threshold_power[index] ? 1U : 0U;
        if (index + 1U < power_count - radius) {
            size_t right_start = index + config->guard_cells_per_side + 1U;
            double left_out = power[index - radius];
            double right_out = power[right_start];
            double left_in = power[index - config->guard_cells_per_side];
            double right_in =
                power[right_start + config->reference_cells_per_side];

            if (sorted_remove_one(left_references, reference_per_side, left_out) != 0 ||
                sorted_remove_one(right_references, reference_per_side, right_out) != 0) {
                return P0_OS_CFAR_INVALID_ARGUMENT;
            }
            sorted_insert(left_references, reference_per_side - 1U, left_in);
            sorted_insert(right_references, reference_per_side - 1U, right_in);
        }
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

static int group_detections_impl(
    const double *power,
    size_t power_count,
    const p0_os_cfar_config_t *config,
    const uint8_t *detections,
    double *noise_power,
    double *threshold_power,
    p0_candidate_region_t *candidates,
    size_t candidate_capacity,
    size_t *candidate_count,
    int trusted_input
) {
    double references[P0_OS_CFAR_MAX_REFERENCE_CELLS];
    size_t radius;
    size_t index;
    size_t output_count = 0U;

    if (power == NULL || power_count < 3U || !valid_config(config) || detections == NULL ||
        noise_power == NULL || threshold_power == NULL || candidates == NULL ||
        candidate_count == NULL) {
        return P0_OS_CFAR_INVALID_ARGUMENT;
    }
    radius = (size_t)config->reference_cells_per_side + config->guard_cells_per_side;
    for (index = 0U; index < power_count; ++index) {
        if (!trusted_input) {
            if (!isfinite(power[index]) || power[index] < 0.0)
                return P0_OS_CFAR_NONFINITE_POWER;
            if (detections[index] > 1U ||
                (detections[index] != 0U &&
                 (index < radius || index >= power_count - radius)))
                return P0_OS_CFAR_INVALID_ARGUMENT;
        }
        noise_power[index] = NAN;
        threshold_power[index] = NAN;
    }
    if (power_count <= 2U * radius) {
        *candidate_count = 0U;
        return P0_OS_CFAR_OK;
    }

    index = radius;
    while (index < power_count - radius) {
        size_t start;
        size_t end;
        size_t peak;
        size_t reference_count = 0U;
        size_t source;
        size_t right_start;
        double noise;

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
                if (index - end > (size_t)config->maximum_gap_bins + 1U)
                    break;
                end = index;
                if (power[index] > power[peak])
                    peak = index;
            } else if (index - end > (size_t)config->maximum_gap_bins + 1U) {
                break;
            }
            ++index;
        }
        if (output_count >= candidate_capacity) {
            *candidate_count = output_count;
            return P0_OS_CFAR_CANDIDATE_OVERFLOW;
        }
        for (source = peak - radius; source < peak - config->guard_cells_per_side; ++source)
            references[reference_count++] = power[source];
        right_start = peak + config->guard_cells_per_side + 1U;
        for (source = right_start;
             source < right_start + config->reference_cells_per_side; ++source)
            references[reference_count++] = power[source];
        insertion_sort(references, reference_count);
        noise = references[config->order_statistic_rank - 1U];
        noise_power[peak] = noise;
        threshold_power[peak] = noise * config->threshold_coefficient;
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

P0_API int p0_os_cfar_group_detections(
    const double *power,
    size_t power_count,
    const p0_os_cfar_config_t *config,
    const uint8_t *detections,
    double *noise_power,
    double *threshold_power,
    p0_candidate_region_t *candidates,
    size_t candidate_capacity,
    size_t *candidate_count
) {
    return group_detections_impl(power, power_count, config, detections,
                                 noise_power, threshold_power, candidates,
                                 candidate_capacity, candidate_count, 0);
}

P0_API int p0_os_cfar_group_detections_trusted(
    const double *power,
    size_t power_count,
    const p0_os_cfar_config_t *config,
    const uint8_t *detections,
    double *noise_power,
    double *threshold_power,
    p0_candidate_region_t *candidates,
    size_t candidate_capacity,
    size_t *candidate_count
) {
    return group_detections_impl(power, power_count, config, detections,
                                 noise_power, threshold_power, candidates,
                                 candidate_capacity, candidate_count, 1);
}
