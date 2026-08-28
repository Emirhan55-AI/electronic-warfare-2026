#include "p0_multiscale_detector.h"

#include <math.h>
#include <string.h>

#define P0_REGIONAL_NOISE_MULTIPLIER 2.5

static void max_heap_sift_down(double *values, size_t count, size_t root)
{
    for (;;) {
        size_t largest = root;
        size_t left = 2U * root + 1U;
        size_t right = left + 1U;
        double temporary;

        if (left < count && values[left] > values[largest])
            largest = left;
        if (right < count && values[right] > values[largest])
            largest = right;
        if (largest == root)
            return;
        temporary = values[root];
        values[root] = values[largest];
        values[largest] = temporary;
        root = largest;
    }
}

static void regional_median_pair(const double *values, double *lower, double *upper)
{
    enum { MEDIAN_HEAP_COUNT = P0_MULTISCALE_REGION_BINS / 2U + 1U };
    double heap[MEDIAN_HEAP_COUNT];
    size_t index;

    memcpy(heap, values, sizeof(heap));
    for (index = MEDIAN_HEAP_COUNT / 2U; index > 0U; --index)
        max_heap_sift_down(heap, MEDIAN_HEAP_COUNT, index - 1U);
    for (index = MEDIAN_HEAP_COUNT; index < P0_MULTISCALE_REGION_BINS; ++index) {
        if (values[index] < heap[0U]) {
            heap[0U] = values[index];
            max_heap_sift_down(heap, MEDIAN_HEAP_COUNT, 0U);
        }
    }
    *upper = heap[0U];
    *lower = heap[1U] > heap[2U] ? heap[1U] : heap[2U];
}

static int overlaps(const p0_candidate_region_t *first, const p0_candidate_region_t *second)
{
    return first->start_bin <= second->end_bin && second->start_bin <= first->end_bin;
}

static int candidate_after(const p0_candidate_region_t *first, const p0_candidate_region_t *second)
{
    if (first->start_bin != second->start_bin)
        return first->start_bin > second->start_bin;
    if (first->end_bin != second->end_bin)
        return first->end_bin > second->end_bin;
    return first->peak_bin > second->peak_bin;
}

static void sort_candidates(p0_candidate_region_t *candidates, size_t count)
{
    size_t index;

    for (index = 1U; index < count; ++index) {
        p0_candidate_region_t key = candidates[index];
        size_t position = index;

        while (position > 0U && candidate_after(&candidates[position - 1U], &key)) {
            candidates[position] = candidates[position - 1U];
            --position;
        }
        candidates[position] = key;
    }
}

static int append_recovery(
    const double *power,
    const double *regional_noise,
    const double *regional_threshold,
    size_t start,
    size_t end,
    size_t peak,
    p0_candidate_region_t *recoveries,
    size_t *count
)
{
    p0_candidate_region_t *candidate;

    if (end < start || end - start + 1U < P0_MULTISCALE_MINIMUM_RECOVERY_SPAN)
        return P0_MULTISCALE_OK;
    if (*count >= P0_MULTISCALE_MAX_RECOVERIES)
        return P0_MULTISCALE_CANDIDATE_OVERFLOW;
    candidate = &recoveries[*count];
    candidate->start_bin = (uint32_t)start;
    candidate->end_bin = (uint32_t)end;
    candidate->peak_bin = (uint32_t)peak;
    candidate->peak_power = power[peak];
    candidate->noise_power_per_bin = regional_noise[peak / P0_MULTISCALE_REGION_BINS];
    candidate->threshold_power = regional_threshold[peak / P0_MULTISCALE_REGION_BINS];
    ++*count;
    return P0_MULTISCALE_OK;
}

static int append_integrated_recovery(
    const double *power,
    const double *regional_noise,
    const double *regional_threshold,
    size_t group_start,
    size_t group_end,
    p0_candidate_region_t *recoveries,
    size_t *count
)
{
    size_t support_start;
    size_t support_end;
    size_t peak;
    size_t index;

    if (group_end < group_start ||
        group_end - group_start + 1U <=
            P0_MULTISCALE_INTEGRATION_LEFT + P0_MULTISCALE_INTEGRATION_RIGHT)
        return P0_MULTISCALE_OK;
    support_start = group_start + P0_MULTISCALE_INTEGRATION_LEFT;
    support_end = group_end - P0_MULTISCALE_INTEGRATION_RIGHT;
    peak = support_start;
    for (index = support_start + 1U; index <= support_end; ++index) {
        if (power[index] > power[peak])
            peak = index;
    }
    return append_recovery(power, regional_noise, regional_threshold,
                           support_start, support_end, peak, recoveries, count);
}

static int complete_multiscale(
    const double *power,
    size_t power_count,
    const p0_os_cfar_config_t *os_config,
    uint8_t *detections,
    double *noise_power,
    double *threshold_power,
    p0_candidate_region_t *candidates,
    size_t candidate_capacity,
    size_t os_count,
    size_t *candidate_count,
    size_t *recovery_count
)
{
    p0_candidate_region_t recoveries[P0_MULTISCALE_MAX_RECOVERIES];
    double regional_noise[P0_MULTISCALE_FRAME_BINS / P0_MULTISCALE_REGION_BINS];
    double regional_threshold[P0_MULTISCALE_FRAME_BINS / P0_MULTISCALE_REGION_BINS];
    size_t found_recoveries = 0U;
    size_t radius;
    size_t evaluated_start;
    size_t evaluated_stop;
    size_t region;
    size_t index;
    size_t output_count = 0U;
    size_t start = 0U;
    size_t end = 0U;
    int active = 0;
    double integration_sum = 0.0;
    int code;

    if (power == NULL || os_config == NULL || detections == NULL || noise_power == NULL ||
        threshold_power == NULL || candidates == NULL || candidate_count == NULL ||
        recovery_count == NULL || power_count != P0_MULTISCALE_FRAME_BINS ||
        candidate_capacity == 0U || os_count > candidate_capacity)
        return P0_MULTISCALE_INVALID_ARGUMENT;

    for (region = 0U; region < P0_MULTISCALE_FRAME_BINS / P0_MULTISCALE_REGION_BINS; ++region) {
        size_t base = region * P0_MULTISCALE_REGION_BINS;
        double median_lower;
        double median_upper;
        double median_twice;

        regional_median_pair(power + base, &median_lower, &median_upper);
        median_twice = median_lower + median_upper;
        regional_noise[region] = median_twice / (2.0 * log(2.0));
        regional_threshold[region] = regional_noise[region] * P0_REGIONAL_NOISE_MULTIPLIER;
    }

    radius = (size_t)os_config->reference_cells_per_side + os_config->guard_cells_per_side;
    evaluated_start = radius > P0_MULTISCALE_INTEGRATION_LEFT
                          ? radius : P0_MULTISCALE_INTEGRATION_LEFT;
    evaluated_stop = power_count -
                     (radius > P0_MULTISCALE_INTEGRATION_RIGHT
                          ? radius : P0_MULTISCALE_INTEGRATION_RIGHT);
    for (index = evaluated_start - P0_MULTISCALE_INTEGRATION_LEFT;
         index <= evaluated_start + P0_MULTISCALE_INTEGRATION_RIGHT; ++index)
        integration_sum += power[index];
    for (index = evaluated_start; index < evaluated_stop; ++index) {
        size_t region_index = index / P0_MULTISCALE_REGION_BINS;
        int detected = integration_sum >
                       regional_threshold[region_index] * P0_MULTISCALE_INTEGRATION_BINS;

        if (detected) {
            if (!active) {
                start = end = index;
                active = 1;
            } else if (index - end <= (size_t)os_config->maximum_gap_bins + 1U) {
                end = index;
            } else {
                code = append_integrated_recovery(power, regional_noise,
                                                  regional_threshold, start, end,
                                                  recoveries, &found_recoveries);
                if (code != P0_MULTISCALE_OK)
                    return code;
                start = end = index;
            }
        } else if (active && index - end > (size_t)os_config->maximum_gap_bins + 1U) {
            code = append_integrated_recovery(power, regional_noise,
                                              regional_threshold, start, end,
                                              recoveries, &found_recoveries);
            if (code != P0_MULTISCALE_OK)
                return code;
            active = 0;
        }
        if (index + 1U < evaluated_stop) {
            integration_sum -= power[index - P0_MULTISCALE_INTEGRATION_LEFT];
            integration_sum += power[index + P0_MULTISCALE_INTEGRATION_RIGHT + 1U];
        }
    }
    if (active) {
        code = append_integrated_recovery(power, regional_noise,
                                          regional_threshold, start, end,
                                          recoveries, &found_recoveries);
        if (code != P0_MULTISCALE_OK)
            return code;
    }

    for (index = 0U; index < os_count; ++index) {
        size_t recovery_index;
        int suppressed = 0;

        for (recovery_index = 0U; recovery_index < found_recoveries; ++recovery_index) {
            if (overlaps(&candidates[index], &recoveries[recovery_index])) {
                suppressed = 1;
                break;
            }
        }
        if (!suppressed)
            candidates[output_count++] = candidates[index];
    }
    if (output_count + found_recoveries > candidate_capacity)
        return P0_MULTISCALE_CANDIDATE_OVERFLOW;
    for (index = 0U; index < found_recoveries; ++index) {
        size_t bin;
        p0_candidate_region_t recovery = recoveries[index];

        candidates[output_count++] = recovery;
        for (bin = recovery.start_bin; bin <= recovery.end_bin; ++bin) {
            size_t region_index = bin / P0_MULTISCALE_REGION_BINS;
            detections[bin] = 1U;
            noise_power[bin] = regional_noise[region_index];
            threshold_power[bin] = regional_threshold[region_index];
        }
    }
    sort_candidates(candidates, output_count);
    *candidate_count = output_count;
    *recovery_count = found_recoveries;
    return P0_MULTISCALE_OK;
}

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
)
{
    size_t os_count = 0U;
    int code;

    if (power == NULL || os_config == NULL || detections == NULL || noise_power == NULL ||
        threshold_power == NULL || candidates == NULL || candidate_count == NULL ||
        recovery_count == NULL || power_count != P0_MULTISCALE_FRAME_BINS ||
        candidate_capacity == 0U)
        return P0_MULTISCALE_INVALID_ARGUMENT;
    code = p0_os_cfar_process(power, power_count, os_config, detections, noise_power,
                              threshold_power, candidates, candidate_capacity, &os_count);
    if (code == P0_OS_CFAR_CANDIDATE_OVERFLOW)
        return P0_MULTISCALE_CANDIDATE_OVERFLOW;
    if (code != P0_OS_CFAR_OK)
        return P0_MULTISCALE_INVALID_ARGUMENT;
    return complete_multiscale(power, power_count, os_config, detections, noise_power,
                               threshold_power, candidates, candidate_capacity, os_count,
                               candidate_count, recovery_count);
}

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
)
{
    size_t os_count = 0U;
    int code;

    if (power == NULL || os_config == NULL || detections == NULL || noise_power == NULL ||
        threshold_power == NULL || candidates == NULL || candidate_count == NULL ||
        recovery_count == NULL || power_count != P0_MULTISCALE_FRAME_BINS ||
        candidate_capacity == 0U)
        return P0_MULTISCALE_INVALID_ARGUMENT;
    code = p0_os_cfar_group_detections(power, power_count, os_config, detections,
                                        noise_power, threshold_power, candidates,
                                        candidate_capacity, &os_count);
    if (code == P0_OS_CFAR_CANDIDATE_OVERFLOW)
        return P0_MULTISCALE_CANDIDATE_OVERFLOW;
    if (code != P0_OS_CFAR_OK)
        return P0_MULTISCALE_INVALID_ARGUMENT;
    return complete_multiscale(power, power_count, os_config, detections, noise_power,
                               threshold_power, candidates, candidate_capacity, os_count,
                               candidate_count, recovery_count);
}
