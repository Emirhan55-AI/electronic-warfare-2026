#include "p0_st05_wideband.h"

#include "p0_st05_wideband_internal.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

enum {
    P0_ST05_REFERENCE_REGION_RANK = 4,
    P0_ST05_SUPPORT_INTEGRATION_BINS = 8,
    P0_ST05_MINIMUM_SPAN_BINS = 41,
    P0_ST05_FLANK_BINS = 64,
    P0_ST05_MAXIMUM_SUPPORT_GAP_BINS = 4
};

static const size_t P0_ST05_SEED_WIDTHS[] = {32U, 64U, 128U, 256U};
static const double P0_ST05_SEED_MULTIPLIER = 2.5;
static const double P0_ST05_SUPPORT_MULTIPLIER = 1.5;
static const double P0_ST05_MAXIMUM_FLANK_DIFFERENCE_DB = 3.0;
static const double P0_ST05_MINIMUM_OCCUPANCY = 0.75;

static int compare_double(const void *left, const void *right)
{
    const double first = *(const double *)left;
    const double second = *(const double *)right;
    return (first > second) - (first < second);
}

static void swap_double(double *left, double *right)
{
    double temporary = *left;
    *left = *right;
    *right = temporary;
}

static double select_kth(double *values, size_t count, size_t wanted)
{
    size_t left = 0U;
    size_t right = count - 1U;

    while (left < right) {
        size_t middle = left + (right - left) / 2U;
        double pivot;
        size_t lower;
        size_t scan;
        size_t upper;

        if (values[left] > values[middle])
            swap_double(&values[left], &values[middle]);
        if (values[middle] > values[right])
            swap_double(&values[middle], &values[right]);
        if (values[left] > values[middle])
            swap_double(&values[left], &values[middle]);
        pivot = values[middle];
        lower = left;
        scan = left;
        upper = right;
        while (scan <= upper) {
            if (values[scan] < pivot) {
                swap_double(&values[lower], &values[scan]);
                ++lower;
                ++scan;
            } else if (values[scan] > pivot) {
                swap_double(&values[scan], &values[upper]);
                if (upper == 0U)
                    break;
                --upper;
            } else {
                ++scan;
            }
        }
        if (wanted < lower)
            right = lower - 1U;
        else if (wanted > upper)
            left = upper + 1U;
        else
            return values[wanted];
    }
    return values[left];
}

static double median(const double *values, size_t count)
{
    double sorted[P0_ST05_INTERNAL_REGION_BINS];
    double upper;
    double lower;
    size_t index;

    memcpy(sorted, values, count * sizeof(*values));
    if ((count & 1U) != 0U)
        return select_kth(sorted, count, count / 2U);
    upper = select_kth(sorted, count, count / 2U);
    lower = sorted[0U];
    for (index = 1U; index < count / 2U; ++index) {
        if (sorted[index] > lower)
            lower = sorted[index];
    }
    return 0.5 * (lower + upper);
}

static double range_mean(const double *values, size_t start, size_t stop)
{
    double total = 0.0;
    size_t index;

    for (index = start; index < stop; ++index)
        total += values[index];
    return total / (double)(stop - start);
}

static int has_seed(const double *prefix, double reference,
                    size_t start, size_t end)
{
    size_t scale;

    for (scale = 0U;
         scale < sizeof(P0_ST05_SEED_WIDTHS) / sizeof(P0_ST05_SEED_WIDTHS[0U]);
         ++scale) {
        size_t width = P0_ST05_SEED_WIDTHS[scale];
        size_t left = (width - 1U) / 2U;
        size_t right = width - left - 1U;
        size_t first = start > left ? start : left;
        size_t last_available = P0_ST05_FRAME_BINS - right - 1U;
        size_t last = end < last_available ? end : last_available;
        double integrated_threshold =
            reference * P0_ST05_SEED_MULTIPLIER * (double)width;
        size_t index;

        if (first > last)
            continue;
        for (index = first; index <= last; ++index) {
            double integrated =
                prefix[index + right + 1U] - prefix[index - left];
            if (integrated > integrated_threshold)
                return 1;
        }
    }
    return 0;
}

static int append_support(
    const double *frames,
    size_t frame_count,
    const double *mean_power,
    size_t start,
    size_t end,
    p0_st05_result_t *result
)
{
    double left_noise[P0_ST05_MAXIMUM_FRAMES];
    double right_noise[P0_ST05_MAXIMUM_FRAMES];
    double left_mean = 0.0;
    double right_mean = 0.0;
    double support_mean = 0.0;
    double reference;
    double threshold;
    double difference_db;
    size_t frame;
    size_t observed = 0U;
    size_t required;
    size_t peak;
    size_t index;

    if (end - start + 1U < P0_ST05_MINIMUM_SPAN_BINS)
        return P0_ST05_OK;
    if (start < P0_ST05_FLANK_BINS ||
        end + 1U + P0_ST05_FLANK_BINS > P0_ST05_FRAME_BINS) {
        p0_st05_unresolved_t *unresolved;
        if (result->unresolved_count >= P0_ST05_MAXIMUM_UNRESOLVED)
            return P0_ST05_OUTPUT_OVERFLOW;
        unresolved = &result->unresolved[result->unresolved_count++];
        unresolved->start_bin = (uint32_t)start;
        unresolved->end_bin = (uint32_t)end;
        unresolved->reason = P0_ST05_INDEPENDENT_FLANKS_UNAVAILABLE;
        return P0_ST05_OK;
    }

    for (frame = 0U; frame < frame_count; ++frame) {
        const double *power = frames + frame * P0_ST05_FRAME_BINS;
        left_noise[frame] = median(power + start - P0_ST05_FLANK_BINS,
                                   P0_ST05_FLANK_BINS) / log(2.0);
        right_noise[frame] = median(power + end + 1U,
                                    P0_ST05_FLANK_BINS) / log(2.0);
        left_mean += left_noise[frame];
        right_mean += right_noise[frame];
    }
    left_mean /= (double)frame_count;
    right_mean /= (double)frame_count;
    difference_db = fabs(10.0 * log10(left_mean / right_mean));
    if (difference_db > P0_ST05_MAXIMUM_FLANK_DIFFERENCE_DB) {
        p0_st05_unresolved_t *unresolved;
        if (result->unresolved_count >= P0_ST05_MAXIMUM_UNRESOLVED)
            return P0_ST05_OUTPUT_OVERFLOW;
        unresolved = &result->unresolved[result->unresolved_count++];
        unresolved->start_bin = (uint32_t)start;
        unresolved->end_bin = (uint32_t)end;
        unresolved->reason = P0_ST05_NONHOMOGENEOUS_FLANKS;
        return P0_ST05_OK;
    }

    reference = left_mean > right_mean ? left_mean : right_mean;
    threshold = reference * P0_ST05_SEED_MULTIPLIER;
    for (frame = 0U; frame < frame_count; ++frame) {
        const double *power = frames + frame * P0_ST05_FRAME_BINS;
        double frame_reference = left_noise[frame] > right_noise[frame]
                                     ? left_noise[frame] : right_noise[frame];
        double frame_support = range_mean(power, start, end + 1U);
        if (frame_support > frame_reference * P0_ST05_SEED_MULTIPLIER)
            ++observed;
    }
    required = (size_t)ceil(P0_ST05_MINIMUM_OCCUPANCY * (double)frame_count);
    if (observed < required)
        return P0_ST05_OK;
    support_mean = range_mean(mean_power, start, end + 1U);
    if (support_mean <= threshold)
        return P0_ST05_OK;
    if (result->candidate_count >= P0_ST05_MAXIMUM_CANDIDATES)
        return P0_ST05_OUTPUT_OVERFLOW;

    peak = start;
    for (index = start + 1U; index <= end; ++index) {
        if (mean_power[index] > mean_power[peak])
            peak = index;
    }
    result->candidates[result->candidate_count].start_bin = (uint32_t)start;
    result->candidates[result->candidate_count].end_bin = (uint32_t)end;
    result->candidates[result->candidate_count].peak_bin = (uint32_t)peak;
    result->candidates[result->candidate_count].peak_power = mean_power[peak];
    result->candidates[result->candidate_count].reference_power_per_bin = reference;
    result->candidates[result->candidate_count].threshold_power_per_bin = threshold;
    result->candidates[result->candidate_count].observed_frames = (uint32_t)observed;
    result->candidates[result->candidate_count].total_frames = (uint32_t)frame_count;
    ++result->candidate_count;
    return P0_ST05_OK;
}

void p0_st05_region_noise_trusted(const double *power, double *region_noise)
{
    size_t region;

    for (region = 0U; region < P0_ST05_INTERNAL_REGION_COUNT; ++region) {
        region_noise[region] =
            median(power + region * P0_ST05_INTERNAL_REGION_BINS,
                   P0_ST05_INTERNAL_REGION_BINS) /
            log(2.0);
    }
}

int p0_st05_wideband_process_precomputed_trusted(
    const double *frame_power,
    size_t frame_count,
    const double *mean_power,
    const double *region_noise,
    p0_st05_result_t *result
)
{
    double prefix[P0_ST05_FRAME_BINS + 1U];
    double sorted_regions[P0_ST05_INTERNAL_REGION_COUNT];
    size_t group_start = 0U;
    size_t group_end = 0U;
    size_t last_support = 0U;
    int support_open = 0;
    double reference;
    size_t index;
    int code;

    memset(result, 0, sizeof(*result));
    memcpy(sorted_regions, region_noise, sizeof(sorted_regions));
    qsort(sorted_regions, P0_ST05_INTERNAL_REGION_COUNT,
          sizeof(*sorted_regions), compare_double);
    reference = sorted_regions[P0_ST05_REFERENCE_REGION_RANK - 1U];
    result->relative_reference_power_per_bin = reference;
    result->absolute_absence_supported = 0U;
    if (!isfinite(reference) || reference <= 0.0) {
        result->decision = P0_ST05_REFERENCE_UNAVAILABLE;
        result->relative_reference_power_per_bin = NAN;
        return P0_ST05_OK;
    }

    prefix[0U] = 0.0;
    for (index = 0U; index < P0_ST05_FRAME_BINS; ++index)
        prefix[index + 1U] = prefix[index] + mean_power[index];

    {
        size_t width = P0_ST05_SUPPORT_INTEGRATION_BINS;
        size_t left = (width - 1U) / 2U;
        size_t right = width - left - 1U;
        double integrated_threshold =
            reference * P0_ST05_SUPPORT_MULTIPLIER * (double)width;
        for (index = left; index < P0_ST05_FRAME_BINS - right; ++index) {
            double integrated =
                prefix[index + right + 1U] - prefix[index - left];
            if (integrated <= integrated_threshold)
                continue;
            if (!support_open) {
                group_start = index;
                group_end = index;
                last_support = index;
                support_open = 1;
                continue;
            }
            if (index - last_support > P0_ST05_MAXIMUM_SUPPORT_GAP_BINS + 1U) {
                if (has_seed(prefix, reference, group_start, group_end)) {
                    code = append_support(frame_power, frame_count, mean_power,
                                          group_start, group_end, result);
                    if (code != P0_ST05_OK)
                        return code;
                }
                group_start = index;
            }
            group_end = index;
            last_support = index;
        }
    }
    if (support_open && has_seed(prefix, reference, group_start, group_end)) {
        code = append_support(frame_power, frame_count, mean_power,
                              group_start, group_end, result);
        if (code != P0_ST05_OK)
            return code;
    }

    if (result->candidate_count != 0U)
        result->decision = P0_ST05_BOUNDED_CANDIDATES;
    else if (result->unresolved_count != 0U)
        result->decision = P0_ST05_RETUNE_REQUIRED;
    else
        result->decision = P0_ST05_NO_BOUNDED_EMISSION;
    return P0_ST05_OK;
}

int p0_st05_wideband_process(
    const double *frame_power,
    size_t frame_count,
    size_t frame_bins,
    p0_st05_result_t *result
)
{
    double mean_power[P0_ST05_FRAME_BINS];
    double region_noise[P0_ST05_INTERNAL_REGION_COUNT];
    double frame_regions[P0_ST05_INTERNAL_REGION_COUNT];
    size_t frame;
    size_t index;
    size_t region;

    if (frame_power == NULL || result == NULL ||
        frame_count < P0_ST05_MINIMUM_FRAMES ||
        frame_count > P0_ST05_MAXIMUM_FRAMES ||
        frame_bins != P0_ST05_FRAME_BINS)
        return P0_ST05_INVALID_ARGUMENT;
    memset(mean_power, 0, sizeof(mean_power));
    memset(region_noise, 0, sizeof(region_noise));
    for (frame = 0U; frame < frame_count; ++frame) {
        const double *power = frame_power + frame * P0_ST05_FRAME_BINS;
        for (index = 0U; index < P0_ST05_FRAME_BINS; ++index) {
            double value = power[index];
            if (!isfinite(value) || value < 0.0)
                return P0_ST05_INVALID_ARGUMENT;
            mean_power[index] += value;
        }
        p0_st05_region_noise_trusted(power, frame_regions);
        for (region = 0U; region < P0_ST05_INTERNAL_REGION_COUNT; ++region)
            region_noise[region] += frame_regions[region];
    }
    for (index = 0U; index < P0_ST05_FRAME_BINS; ++index)
        mean_power[index] /= (double)frame_count;
    for (region = 0U; region < P0_ST05_INTERNAL_REGION_COUNT; ++region)
        region_noise[region] /= (double)frame_count;
    return p0_st05_wideband_process_precomputed_trusted(
        frame_power, frame_count, mean_power, region_noise, result);
}
