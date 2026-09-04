#include "p0_multiframe_narrowband.h"

#include <math.h>
#include <stdlib.h>

#define P0_MFNB_SEED_RATIO 3.9810717055349722
#define P0_MFNB_COMPONENT_RATIO 1.4125375446227544
#define P0_MFNB_MINIMUM_OCCUPANCY 0.75
#define P0_MFNB_REFERENCE_INNER_HZ 50000.0
#define P0_MFNB_REFERENCE_OUTER_HZ 250000.0
#define P0_MFNB_COMPONENT_GAP_HZ 5000.0
#define P0_MFNB_CLUSTER_HZ 50000.0

typedef struct {
    size_t index;
    double noise;
} p0_mfnb_component_t;

static int compare_double(const void *left, const void *right) {
    const double a = *(const double *)left;
    const double b = *(const double *)right;
    return (a > b) - (a < b);
}

static double median(double *values, size_t count) {
    qsort(values, count, sizeof(*values), compare_double);
    if ((count & 1u) != 0u) {
        return values[count / 2u];
    }
    return 0.5 * (values[count / 2u - 1u] + values[count / 2u]);
}

static size_t reference_values(
    const double *power,
    size_t bin_count,
    size_t index,
    size_t inner_bins,
    size_t outer_bins,
    double *scratch
) {
    size_t count = 0u;
    size_t bin;
    const size_t left = index > outer_bins ? index - outer_bins : 0u;
    const size_t right = index + outer_bins < bin_count ? index + outer_bins : bin_count - 1u;
    for (bin = left; bin <= right; ++bin) {
        const size_t distance = bin > index ? bin - index : index - bin;
        if (distance >= inner_bins && distance <= outer_bins) {
            scratch[count++] = power[bin];
        }
    }
    return count;
}

static int compare_strength(const void *left, const void *right) {
    const p0_multiframe_narrowband_candidate_t *a = left;
    const p0_multiframe_narrowband_candidate_t *b = right;
    if (a->peak_to_noise_db != b->peak_to_noise_db) {
        return a->peak_to_noise_db < b->peak_to_noise_db ? 1 : -1;
    }
    if (a->component_count != b->component_count) {
        return a->component_count < b->component_count ? 1 : -1;
    }
    return (a->center_bin > b->center_bin) - (a->center_bin < b->center_bin);
}

static int compare_frequency(const void *left, const void *right) {
    const p0_multiframe_narrowband_candidate_t *a = left;
    const p0_multiframe_narrowband_candidate_t *b = right;
    return (a->center_bin > b->center_bin) - (a->center_bin < b->center_bin);
}

int p0_multiframe_narrowband_process(
    const double *frame_power,
    size_t frame_count,
    size_t bin_count,
    double sample_rate_hz,
    size_t first_bin,
    size_t last_bin,
    p0_multiframe_narrowband_candidate_t *candidates,
    size_t candidate_capacity,
    size_t *candidate_count
) {
    double *mean_power = NULL;
    double *scratch = NULL;
    p0_mfnb_component_t *components = NULL;
    p0_multiframe_narrowband_candidate_t *ranked = NULL;
    uint8_t *seed = NULL;
    uint16_t *observed = NULL;
    size_t inner_bins;
    size_t outer_bins;
    size_t gap_bins;
    size_t cluster_bins;
    size_t component_count = 0u;
    size_t output_count = 0u;
    size_t bin;
    size_t frame;

    if (candidate_count != NULL) {
        *candidate_count = 0u;
    }
    if (frame_power == NULL || candidates == NULL || candidate_count == NULL ||
        frame_count < P0_MFNB_MINIMUM_FRAMES || frame_count > P0_MFNB_MAXIMUM_FRAMES ||
        bin_count < 3u || bin_count > 65536u || !(sample_rate_hz > 0.0) ||
        first_bin >= last_bin || last_bin >= bin_count || candidate_capacity == 0u) {
        return P0_MFNB_INVALID_ARGUMENT;
    }

    inner_bins = (size_t)ceil(P0_MFNB_REFERENCE_INNER_HZ * (double)bin_count / sample_rate_hz);
    outer_bins = (size_t)floor(P0_MFNB_REFERENCE_OUTER_HZ * (double)bin_count / sample_rate_hz);
    gap_bins = (size_t)floor(P0_MFNB_COMPONENT_GAP_HZ * (double)bin_count / sample_rate_hz);
    cluster_bins = (size_t)floor(P0_MFNB_CLUSTER_HZ * (double)bin_count / sample_rate_hz);
    if (inner_bins == 0u || outer_bins < inner_bins || gap_bins == 0u || cluster_bins < gap_bins) {
        return P0_MFNB_INVALID_ARGUMENT;
    }

    mean_power = calloc(bin_count, sizeof(*mean_power));
    scratch = malloc((2u * outer_bins + 2u) * sizeof(*scratch));
    components = malloc(bin_count * sizeof(*components));
    ranked = malloc(bin_count * sizeof(*ranked));
    seed = calloc(bin_count, sizeof(*seed));
    observed = calloc(bin_count, sizeof(*observed));
    if (mean_power == NULL || scratch == NULL || components == NULL || ranked == NULL ||
        seed == NULL || observed == NULL) {
        free(mean_power); free(scratch); free(components); free(ranked); free(seed); free(observed);
        return P0_MFNB_ALLOCATION_FAILED;
    }

    for (frame = 0u; frame < frame_count; ++frame) {
        for (bin = 0u; bin < bin_count; ++bin) {
            const double value = frame_power[frame * bin_count + bin];
            if (!isfinite(value) || value < 0.0) {
                free(mean_power); free(scratch); free(components); free(ranked); free(seed); free(observed);
                return P0_MFNB_INVALID_ARGUMENT;
            }
            mean_power[bin] += value / (double)frame_count;
        }
    }

    for (bin = first_bin > 0u ? first_bin : 1u; bin <= last_bin && bin + 1u < bin_count; ++bin) {
        size_t reference_count;
        double noise;
        if (!(mean_power[bin] >= mean_power[bin - 1u] && mean_power[bin] > mean_power[bin + 1u])) {
            continue;
        }
        reference_count = reference_values(mean_power, bin_count, bin, inner_bins, outer_bins, scratch);
        if (reference_count < 32u) {
            continue;
        }
        noise = median(scratch, reference_count);
        if (!(noise > 0.0) || mean_power[bin] <= noise * P0_MFNB_COMPONENT_RATIO) {
            continue;
        }
        components[component_count].index = bin;
        components[component_count].noise = noise;
        ++component_count;
        if (mean_power[bin] >= noise * P0_MFNB_SEED_RATIO) {
            size_t hit_count = 0u;
            for (frame = 0u; frame < frame_count; ++frame) {
                const double *row = frame_power + frame * bin_count;
                reference_count = reference_values(row, bin_count, bin, inner_bins, outer_bins, scratch);
                if (reference_count >= 32u && row[bin] > median(scratch, reference_count) * P0_MFNB_SEED_RATIO) {
                    ++hit_count;
                }
            }
            if ((double)hit_count >= ceil(P0_MFNB_MINIMUM_OCCUPANCY * (double)frame_count)) {
                seed[bin] = 1u;
                observed[bin] = (uint16_t)hit_count;
            }
        }
    }

    for (bin = 0u; bin < component_count;) {
        size_t end = bin + 1u;
        size_t cursor;
        size_t strongest = (size_t)-1;
        double strongest_ratio = 0.0;
        double weight_sum = 0.0;
        double weighted_bin_sum = 0.0;
        while (end < component_count &&
               components[end].index - components[end - 1u].index <= gap_bins &&
               components[end].index - components[bin].index <= cluster_bins) {
            ++end;
        }
        for (cursor = bin; cursor < end; ++cursor) {
            const size_t index = components[cursor].index;
            const double weight = mean_power[index] - components[cursor].noise;
            if (weight > 0.0) {
                weight_sum += weight;
                weighted_bin_sum += weight * (double)index;
            }
            if (seed[index] != 0u && mean_power[index] / components[cursor].noise > strongest_ratio) {
                strongest = cursor;
                strongest_ratio = mean_power[index] / components[cursor].noise;
            }
        }
        if (strongest != (size_t)-1) {
            const size_t peak = components[strongest].index;
            p0_multiframe_narrowband_candidate_t *output = &ranked[output_count++];
            output->center_bin = end - bin == 1u ? (double)peak : weighted_bin_sum / weight_sum;
            output->peak_bin = (uint16_t)peak;
            output->lower_bin = (uint16_t)components[bin].index;
            output->upper_bin = (uint16_t)components[end - 1u].index;
            output->peak_to_noise_db = 10.0 * log10(strongest_ratio);
            output->observed_frames = observed[peak];
            output->total_frames = (uint16_t)frame_count;
            output->component_count = (uint16_t)(end - bin);
        }
        bin = end;
    }

    qsort(ranked, output_count, sizeof(*ranked), compare_strength);
    if (output_count > candidate_capacity) {
        output_count = candidate_capacity;
    }
    for (bin = 0u; bin < output_count; ++bin) {
        candidates[bin] = ranked[bin];
    }
    qsort(candidates, output_count, sizeof(*candidates), compare_frequency);
    *candidate_count = output_count;
    free(mean_power); free(scratch); free(components); free(ranked); free(seed); free(observed);
    return P0_MFNB_OK;
}
