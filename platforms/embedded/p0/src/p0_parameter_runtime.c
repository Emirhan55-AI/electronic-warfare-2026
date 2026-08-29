#include "p0_parameter_runtime.h"

#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define P0_PARAMETER_IQ_BYTES (P0_PARAMETER_FFT_SIZE * 2U)
#define P0_PARAMETER_POWER_FRACTION_BITS 30U
#define P0_PARAMETER_HANN_POWER_SUM 1536.0
#define P0_PARAMETER_PI 3.14159265358979323846264338327950288

static void set_field(p0_parameter_field_t *field, uint8_t state, uint8_t reason,
                      double value)
{
    field->state = state;
    field->reason = reason;
    field->value = value;
}

static void initialize_result(p0_parameter_result_t *result, uint64_t intent_id,
                              uint64_t event_id, uint32_t frame_id,
                              uint8_t observations, uint8_t state, uint8_t reason)
{
    memset(result, 0, sizeof(*result));
    result->intent_id = intent_id;
    result->event_id = event_id;
    result->frame_id = frame_id;
    result->observation_count = observations;
    set_field(&result->emission_center_frequency_hz, state, reason, 0.0);
    set_field(&result->lower_occupied_edge_hz, state, reason, 0.0);
    set_field(&result->upper_occupied_edge_hz, state, reason, 0.0);
    set_field(&result->occupied_bandwidth_hz, state, reason, 0.0);
    set_field(&result->channel_power_dbfs, state, reason, 0.0);
    set_field(&result->snr_estimate_db, state, reason, 0.0);
    result->reference_difference_db = NAN;
    result->detection_significance = NAN;
    result->center_uncertainty_bins = NAN;
    result->temporal_edge_range_bins = NAN;
}

static int valid_span(uint16_t lower, uint16_t upper)
{
    unsigned int width;

    if (lower > upper)
        return 0;
    width = (unsigned int)upper - (unsigned int)lower + 1U;
    return width >= P0_PARAMETER_MINIMUM_SPAN_BINS &&
           width <= P0_PARAMETER_MAXIMUM_SPAN_BINS &&
           lower >= 20U + P0_PARAMETER_LOCAL_PADDING &&
           upper <= 4075U - P0_PARAMETER_LOCAL_PADDING;
}

static void fft(p0_parameter_complex_t *values, size_t count, int inverse)
{
    size_t index;
    size_t swap_index = 0U;
    size_t length;

    for (index = 1U; index < count; ++index) {
        size_t bit = count >> 1U;

        while ((swap_index & bit) != 0U) {
            swap_index ^= bit;
            bit >>= 1U;
        }
        swap_index ^= bit;
        if (index < swap_index) {
            p0_parameter_complex_t temporary = values[index];
            values[index] = values[swap_index];
            values[swap_index] = temporary;
        }
    }
    for (length = 2U; length <= count; length <<= 1U) {
        double angle = (inverse ? 2.0 : -2.0) * P0_PARAMETER_PI / (double)length;
        double step_real = cos(angle);
        double step_imag = sin(angle);
        size_t start;

        for (start = 0U; start < count; start += length) {
            double root_real = 1.0;
            double root_imag = 0.0;
            size_t offset;

            for (offset = 0U; offset < length / 2U; ++offset) {
                p0_parameter_complex_t even = values[start + offset];
                p0_parameter_complex_t odd = values[start + offset + length / 2U];
                double odd_real = odd.real * root_real - odd.imag * root_imag;
                double odd_imag = odd.real * root_imag + odd.imag * root_real;
                double next_real = root_real * step_real - root_imag * step_imag;

                values[start + offset].real = even.real + odd_real;
                values[start + offset].imag = even.imag + odd_imag;
                values[start + offset + length / 2U].real = even.real - odd_real;
                values[start + offset + length / 2U].imag = even.imag - odd_imag;
                root_imag = root_real * step_imag + root_imag * step_real;
                root_real = next_real;
            }
        }
    }
    if (inverse) {
        for (index = 0U; index < count; ++index) {
            values[index].real /= (double)count;
            values[index].imag /= (double)count;
        }
    }
}

static double magnitude_squared(p0_parameter_complex_t value)
{
    return value.real * value.real + value.imag * value.imag;
}

int p0_parameter_power_from_ci8(const uint8_t *iq_ci8, size_t iq_bytes,
                                uint64_t *shifted_power_uq28_30,
                                size_t power_count)
{
    p0_parameter_complex_t *work;
    size_t index;

    if (iq_ci8 == NULL || shifted_power_uq28_30 == NULL ||
        iq_bytes != P0_PARAMETER_IQ_BYTES || power_count != P0_PARAMETER_FFT_SIZE) {
        errno = EINVAL;
        return -1;
    }
    work = malloc(P0_PARAMETER_FFT_SIZE * sizeof(*work));
    if (work == NULL)
        return -1;
    for (index = 0U; index < P0_PARAMETER_FFT_SIZE; ++index) {
        double window = 0.5 - 0.5 * cos(2.0 * P0_PARAMETER_PI * (double)index /
                                        (double)P0_PARAMETER_FFT_SIZE);

        work[index].real = (double)(int8_t)iq_ci8[2U * index] * window / 128.0;
        work[index].imag = (double)(int8_t)iq_ci8[2U * index + 1U] * window / 128.0;
    }
    fft(work, P0_PARAMETER_FFT_SIZE, 0);
    for (index = 0U; index < P0_PARAMETER_FFT_SIZE; ++index) {
        double scaled = magnitude_squared(work[index]) *
                        (double)(UINT64_C(1) << P0_PARAMETER_POWER_FRACTION_BITS);
        size_t shifted = index ^ (P0_PARAMETER_FFT_SIZE / 2U);

        if (!isfinite(scaled) || scaled < 0.0 ||
            scaled >= (double)(UINT64_C(1) << 58)) {
            free(work);
            errno = ERANGE;
            return -1;
        }
        shifted_power_uq28_30[shifted] = (uint64_t)floor(scaled + 0.5);
    }
    free(work);
    return 0;
}

static int store_rectangular_fft(p0_parameter_runtime_t *runtime, const uint8_t *iq_ci8,
                                 unsigned int observation)
{
    p0_parameter_complex_t *work;
    unsigned int local;
    size_t index;

    work = malloc(P0_PARAMETER_FFT_SIZE * sizeof(*work));
    if (work == NULL)
        return -1;
    for (index = 0U; index < P0_PARAMETER_FFT_SIZE; ++index) {
        work[index].real = (double)(int8_t)iq_ci8[2U * index] / 128.0;
        work[index].imag = (double)(int8_t)iq_ci8[2U * index + 1U] / 128.0;
    }
    fft(work, P0_PARAMETER_FFT_SIZE, 0);
    for (local = 0U; local < runtime->local_bin_count; ++local) {
        unsigned int shifted = (unsigned int)runtime->local_start_bin + local;
        unsigned int natural = shifted ^ (P0_PARAMETER_FFT_SIZE / 2U);

        runtime->local_rectangular_fft[
            observation * P0_PARAMETER_MAXIMUM_LOCAL_BINS + local] = work[natural];
    }
    free(work);
    return 0;
}

static double local_psd(const p0_parameter_runtime_t *runtime, unsigned int frame,
                        unsigned int shifted_bin)
{
    unsigned int local = shifted_bin - runtime->local_start_bin;
    return runtime->local_psd[frame * P0_PARAMETER_MAXIMUM_LOCAL_BINS + local];
}

static p0_parameter_complex_t local_rectangular_fft(
    const p0_parameter_runtime_t *runtime, unsigned int frame, unsigned int shifted_bin)
{
    unsigned int local = shifted_bin - runtime->local_start_bin;
    return runtime->local_rectangular_fft[
        frame * P0_PARAMETER_MAXIMUM_LOCAL_BINS + local];
}

static double average_psd(const p0_parameter_runtime_t *runtime, unsigned int shifted_bin,
                          int omitted)
{
    double total = 0.0;
    unsigned int count = 0U;
    unsigned int frame;

    for (frame = 0U; frame < P0_PARAMETER_REQUIRED_FRAMES; ++frame) {
        if ((int)frame == omitted)
            continue;
        total += local_psd(runtime, frame, shifted_bin);
        ++count;
    }
    return total / (double)count;
}

static double reference_noise(const p0_parameter_runtime_t *runtime, int omitted,
                              double *left, double *right)
{
    unsigned int lower = runtime->lower_shifted_bin;
    unsigned int upper = runtime->upper_shifted_bin;
    unsigned int index;
    double left_total = 0.0;
    double right_total = 0.0;

    for (index = lower - 36U; index <= lower - 5U; ++index)
        left_total += average_psd(runtime, index, omitted);
    for (index = upper + 5U; index <= upper + 36U; ++index)
        right_total += average_psd(runtime, index, omitted);
    *left = left_total / 32.0;
    *right = right_total / 32.0;
    return 0.5 * (*left + *right);
}

static double convolved(const double *values, unsigned int count, unsigned int index)
{
    double result = 0.5 * values[index];

    if (index != 0U)
        result += 0.25 * values[index - 1U];
    if (index + 1U < count)
        result += 0.25 * values[index + 1U];
    return result;
}

static int fractional_edge(const double *weights, unsigned int count, unsigned int offset,
                           double fraction, double *edge)
{
    double total = 0.0;
    double cumulative = 0.0;
    double target;
    unsigned int index;

    for (index = 0U; index < count; ++index)
        total += weights[index];
    if (!(total > 0.0) || !isfinite(total))
        return -1;
    target = total * fraction;
    for (index = 0U; index < count; ++index) {
        double before = cumulative;

        cumulative += weights[index];
        if (cumulative >= target || index + 1U == count) {
            double cell = weights[index] > 0.0 ? weights[index] : 0x1p-1022;
            *edge = (double)offset + (double)index - 0.5 + (target - before) / cell;
            return 0;
        }
    }
    return -1;
}

static double median_four(double values[4])
{
    unsigned int outer;

    for (outer = 1U; outer < 4U; ++outer) {
        double value = values[outer];
        unsigned int inner = outer;

        while (inner > 0U && values[inner - 1U] > value) {
            values[inner] = values[inner - 1U];
            --inner;
        }
        values[inner] = value;
    }
    return 0.5 * (values[1] + values[2]);
}

static int calculate_edges(const p0_parameter_runtime_t *runtime, int omitted,
                           double tail_fraction, double shrink_sigma,
                           double *lower_edge, double *upper_edge)
{
    unsigned int lower = runtime->lower_shifted_bin;
    unsigned int width = (unsigned int)runtime->upper_shifted_bin - lower + 1U;
    unsigned int frame_count = omitted < 0 ? 4U : 3U;
    double left;
    double right;
    double noise = reference_noise(runtime, omitted, &left, &right);
    double sigma = noise / sqrt((double)frame_count) * sqrt(0.375);
    double excess[P0_PARAMETER_MAXIMUM_SPAN_BINS];
    double weights[P0_PARAMETER_MAXIMUM_SPAN_BINS];
    unsigned int index;

    for (index = 0U; index < width; ++index)
        excess[index] = average_psd(runtime, lower + index, omitted) - noise;
    for (index = 0U; index < width; ++index) {
        double value = convolved(excess, width, index) - shrink_sigma * sigma;
        weights[index] = value > 0.0 ? value : 0.0;
    }
    return fractional_edge(weights, width, lower, tail_fraction, lower_edge) != 0 ||
                   fractional_edge(weights, width, lower, 1.0 - tail_fraction,
                                   upper_edge) != 0
               ? -1
               : 0;
}

static int broad_emission_bin(const p0_parameter_runtime_t *runtime,
                              double fallback_lower, double fallback_upper,
                              double *emission_bin)
{
    unsigned int lower = runtime->lower_shifted_bin;
    unsigned int upper = runtime->upper_shifted_bin;
    unsigned int width = upper - lower + 1U;
    unsigned int support_lower = lower;
    unsigned int support_upper = upper;
    unsigned int index;
    unsigned int frame;
    int found = 0;
    double broad[P0_PARAMETER_MAXIMUM_SPAN_BINS] = {0.0};
    p0_parameter_complex_t *work;
    double average_rectangular_noise = 0.0;
    double total = 0.0;
    double moment = 0.0;

    for (frame = 0U; frame < 4U; ++frame) {
        unsigned int sample;
        for (sample = lower - 36U; sample <= lower - 5U; ++sample)
            average_rectangular_noise +=
                magnitude_squared(local_rectangular_fft(runtime, frame, sample));
        for (sample = upper + 5U; sample <= upper + 36U; ++sample)
            average_rectangular_noise +=
                magnitude_squared(local_rectangular_fft(runtime, frame, sample));
    }
    average_rectangular_noise /= 256.0;
    for (index = lower; index <= upper; ++index) {
        double power = 0.0;
        for (frame = 0U; frame < 4U; ++frame)
            power += magnitude_squared(local_rectangular_fft(runtime, frame, index));
        power /= 4.0;
        if (power >= 6.0 * average_rectangular_noise) {
            if (!found)
                support_lower = index;
            support_upper = index;
            found = 1;
        }
    }
    if (!found) {
        support_lower = (unsigned int)ceil(fallback_lower + 0.5);
        support_upper = (unsigned int)floor(fallback_upper - 0.5);
        if (support_lower < lower)
            support_lower = lower;
        if (support_upper > upper)
            support_upper = upper;
    }
    if (support_lower > support_upper)
        return -1;
    work = calloc(P0_PARAMETER_FFT_SIZE, sizeof(*work));
    if (work == NULL)
        return -1;
    for (frame = 0U; frame < 4U; ++frame) {
        double noise_total = 0.0;
        double selected_total = 0.0;
        double signal_amplitude;

        memset(work, 0, P0_PARAMETER_FFT_SIZE * sizeof(*work));
        for (index = lower - 36U; index <= lower - 5U; ++index)
            noise_total += magnitude_squared(local_rectangular_fft(runtime, frame, index));
        for (index = upper + 5U; index <= upper + 36U; ++index)
            noise_total += magnitude_squared(local_rectangular_fft(runtime, frame, index));
        noise_total /= 64.0;
        for (index = support_lower; index <= support_upper; ++index)
            selected_total += magnitude_squared(local_rectangular_fft(runtime, frame, index));
        selected_total /= (double)(support_upper - support_lower + 1U);
        signal_amplitude = sqrt(fmax(selected_total - noise_total, 0.0));
        for (index = support_lower; index <= support_upper; ++index) {
            p0_parameter_complex_t selected = local_rectangular_fft(runtime, frame, index);
            double magnitude = sqrt(magnitude_squared(selected));
            unsigned int natural = index ^ (P0_PARAMETER_FFT_SIZE / 2U);

            if (magnitude > 0.0) {
                work[natural].real = signal_amplitude * selected.real / magnitude;
                work[natural].imag = signal_amplitude * selected.imag / magnitude;
            }
        }
        fft(work, P0_PARAMETER_FFT_SIZE, 1);
        for (index = 0U; index < P0_PARAMETER_FFT_SIZE; ++index) {
            double hann = 0.5 - 0.5 * cos(2.0 * P0_PARAMETER_PI * (double)index /
                                         (double)P0_PARAMETER_FFT_SIZE);
            work[index].real *= hann;
            work[index].imag *= hann;
        }
        fft(work, P0_PARAMETER_FFT_SIZE, 0);
        for (index = lower; index <= upper; ++index) {
            unsigned int natural = index ^ (P0_PARAMETER_FFT_SIZE / 2U);
            broad[index - lower] += magnitude_squared(work[natural]) / 4.0;
        }
    }
    free(work);
    for (index = 0U; index < width; ++index) {
        total += broad[index];
        moment += (double)(lower + index) * broad[index];
    }
    if (!(total > 0.0) || !isfinite(total))
        return -1;
    *emission_bin = moment / total;
    return 0;
}

static void fail_common(p0_parameter_result_t *result, uint8_t state, uint8_t reason)
{
    set_field(&result->emission_center_frequency_hz, state, reason, 0.0);
    set_field(&result->lower_occupied_edge_hz, state, reason, 0.0);
    set_field(&result->upper_occupied_edge_hz, state, reason, 0.0);
    set_field(&result->occupied_bandwidth_hz, state, reason, 0.0);
    set_field(&result->channel_power_dbfs, state, reason, 0.0);
    set_field(&result->snr_estimate_db, state, reason, 0.0);
}

static int finalize_result(p0_parameter_runtime_t *runtime, p0_parameter_result_t *result)
{
    unsigned int lower = runtime->lower_shifted_bin;
    unsigned int upper = runtime->upper_shifted_bin;
    unsigned int width = upper - lower + 1U;
    unsigned int index;
    unsigned int omitted;
    double left;
    double right;
    double noise = reference_noise(runtime, -1, &left, &right);
    double reference_difference;
    double signed_excess[P0_PARAMETER_MAXIMUM_SPAN_BINS];
    double center_weights[P0_PARAMETER_MAXIMUM_SPAN_BINS];
    double positive[P0_PARAMETER_MAXIMUM_SPAN_BINS];
    double total = 0.0;
    double corrected_significance;
    double center_weight_total = 0.0;
    double emission_bin = 0.0;
    double leave_centers[4];
    double center_mean = 0.0;
    double center_uncertainty = NAN;
    double base_lower;
    double base_upper;
    double base_lower_differences[4];
    double base_upper_differences[4];
    double temporal_range = NAN;
    double bin_spacing = (double)runtime->sample_rate_hz / P0_PARAMETER_FFT_SIZE;
    double noise_sigma;
    double positive_total = 0.0;
    double positive_center = 0.0;
    double spectral_variance = 0.0;
    int centers_valid = 1;
    int base_edges_valid;

    if (!(left > 0.0) || !(right > 0.0) || !isfinite(noise)) {
        fail_common(result, P0_PARAMETER_FIELD_INSUFFICIENT_QUALITY,
                    P0_PARAMETER_REASON_REFERENCE_POWER);
        return 0;
    }
    reference_difference = fabs(10.0 * log10(left / right));
    result->reference_difference_db = reference_difference;
    if (reference_difference > 3.0) {
        fail_common(result, P0_PARAMETER_FIELD_UNCERTAIN,
                    P0_PARAMETER_REASON_REFERENCE_MISMATCH);
        return 0;
    }
    for (index = 0U; index < width; ++index) {
        signed_excess[index] = average_psd(runtime, lower + index, -1) - noise;
        total += signed_excess[index];
    }
    result->detection_significance = total / (noise * sqrt((double)width / 4.0));
    corrected_significance = total /
        (noise * sqrt((double)width / 4.0 + (double)(width * width) / 256.0));
    if (!(total > 0.0) || !isfinite(total) || result->detection_significance < 12.0 ||
        !isfinite(corrected_significance) || corrected_significance < 6.25) {
        result->detection_significance = corrected_significance;
        fail_common(result, P0_PARAMETER_FIELD_INSUFFICIENT_QUALITY,
                    P0_PARAMETER_REASON_EXCESS_POWER);
        return 0;
    }
    result->detection_significance = corrected_significance;
    noise_sigma = noise * 0.5 * sqrt(0.375);
    for (index = 0U; index < width; ++index) {
        double value = convolved(signed_excess, width, index) - noise_sigma;
        center_weights[index] = value > 0.0 ? value : 0.0;
        center_weight_total += center_weights[index];
        emission_bin += (double)(lower + index) * center_weights[index];
    }
    if (!(center_weight_total > 0.0)) {
        fail_common(result, P0_PARAMETER_FIELD_INSUFFICIENT_QUALITY,
                    P0_PARAMETER_REASON_EXCESS_POWER);
        return 0;
    }
    emission_bin /= center_weight_total;
    for (omitted = 0U; omitted < 4U; ++omitted) {
        double subset_left;
        double subset_right;
        double subset_noise = reference_noise(runtime, (int)omitted, &subset_left, &subset_right);
        double subset_total = 0.0;
        double subset_moment = 0.0;

        for (index = 0U; index < width; ++index) {
            double value = average_psd(runtime, lower + index, (int)omitted) - subset_noise;
            subset_total += value;
            subset_moment += (double)(lower + index) * value;
        }
        if (!(subset_total > 0.0)) {
            centers_valid = 0;
            break;
        }
        leave_centers[omitted] = subset_moment / subset_total;
        center_mean += leave_centers[omitted] / 4.0;
    }
    if (centers_valid) {
        center_uncertainty = 0.0;
        for (omitted = 0U; omitted < 4U; ++omitted) {
            double delta = leave_centers[omitted] - center_mean;
            center_uncertainty += delta * delta;
        }
        center_uncertainty = sqrt(0.75 * center_uncertainty);
    }
    result->center_uncertainty_bins = center_uncertainty;
    base_edges_valid = calculate_edges(runtime, -1, 0.005, 2.5,
                                       &base_lower, &base_upper) == 0;
    if (width >= 100U &&
        (!base_edges_valid ||
         broad_emission_bin(runtime, base_lower, base_upper, &emission_bin) != 0))
        emission_bin = NAN;
    if (isfinite(emission_bin) && isfinite(center_uncertainty) && center_uncertainty <= 4.0) {
        set_field(&result->emission_center_frequency_hz, P0_PARAMETER_FIELD_VALID,
                  P0_PARAMETER_REASON_NONE,
                  (double)runtime->center_frequency_hz +
                      (emission_bin - 2048.0) * bin_spacing);
    } else {
        set_field(&result->emission_center_frequency_hz,
                  P0_PARAMETER_FIELD_INSUFFICIENT_QUALITY,
                  P0_PARAMETER_REASON_CENTER_TEMPORAL_UNCERTAINTY, 0.0);
    }

    if (!base_edges_valid) {
        set_field(&result->lower_occupied_edge_hz, P0_PARAMETER_FIELD_UNCERTAIN,
                  P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY, 0.0);
        set_field(&result->upper_occupied_edge_hz, P0_PARAMETER_FIELD_UNCERTAIN,
                  P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY, 0.0);
        set_field(&result->occupied_bandwidth_hz, P0_PARAMETER_FIELD_UNCERTAIN,
                  P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY, 0.0);
    } else {
        int clipping = base_lower <= (double)lower + 0.5 ||
                       base_upper >= (double)upper - 0.5;

        int temporal_edges_valid = 1;

        for (omitted = 0U; omitted < 4U; ++omitted) {
            double subset_lower;
            double subset_upper;
            if (calculate_edges(runtime, (int)omitted, 0.005, 2.5,
                                &subset_lower, &subset_upper) != 0) {
                temporal_edges_valid = 0;
                break;
            }
            base_lower_differences[omitted] = fabs(subset_lower - base_lower);
            base_upper_differences[omitted] = fabs(subset_upper - base_upper);
        }
        if (temporal_edges_valid)
            temporal_range = fmax(median_four(base_lower_differences),
                                  median_four(base_upper_differences));
        result->temporal_edge_range_bins = temporal_range;
        if (clipping) {
            set_field(&result->lower_occupied_edge_hz, P0_PARAMETER_FIELD_UNCERTAIN,
                      P0_PARAMETER_REASON_SPAN_EDGE_CLIPPING, 0.0);
            set_field(&result->upper_occupied_edge_hz, P0_PARAMETER_FIELD_UNCERTAIN,
                      P0_PARAMETER_REASON_SPAN_EDGE_CLIPPING, 0.0);
            set_field(&result->occupied_bandwidth_hz, P0_PARAMETER_FIELD_UNCERTAIN,
                      P0_PARAMETER_REASON_SPAN_EDGE_CLIPPING, 0.0);
        } else {
            uint8_t state = isfinite(temporal_range) && temporal_range <= 2.0
                                ? P0_PARAMETER_FIELD_VALID
                                : P0_PARAMETER_FIELD_UNCERTAIN;
            uint8_t reason = state == P0_PARAMETER_FIELD_VALID
                                 ? P0_PARAMETER_REASON_NONE
                                 : P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY;
            set_field(&result->lower_occupied_edge_hz, state, reason,
                      state == P0_PARAMETER_FIELD_VALID
                          ? (double)runtime->center_frequency_hz +
                                (base_lower - 2048.0) * bin_spacing
                          : 0.0);
            set_field(&result->upper_occupied_edge_hz, state, reason,
                      state == P0_PARAMETER_FIELD_VALID
                          ? (double)runtime->center_frequency_hz +
                                (base_upper - 2048.0) * bin_spacing
                          : 0.0);
            set_field(&result->occupied_bandwidth_hz, state, reason,
                      state == P0_PARAMETER_FIELD_VALID
                          ? (base_upper - base_lower) * bin_spacing
                          : 0.0);
        }
    }

    set_field(&result->channel_power_dbfs, P0_PARAMETER_FIELD_VALID,
              P0_PARAMETER_REASON_NONE, 10.0 * log10(fmax(total * bin_spacing, 0x1p-1022)));
    for (index = 0U; index < width; ++index) {
        positive[index] = signed_excess[index] > 0.0 ? signed_excess[index] : 0.0;
        positive_total += positive[index];
        positive_center += (double)(lower + index) * positive[index];
    }
    positive_center /= positive_total;
    for (index = 0U; index < width; ++index) {
        double delta = (double)(lower + index) - positive_center;
        spectral_variance += delta * delta * positive[index];
    }
    spectral_variance /= positive_total;
    {
        double equivalent_width = fmax(4.0 * sqrt(spectral_variance), 1.0);
        double raw_snr = 10.0 * log10(fmax(total / (noise * equivalent_width), 0x1p-1022));
        set_field(&result->snr_estimate_db, P0_PARAMETER_FIELD_VALID,
                  P0_PARAMETER_REASON_NONE, 0.8 * raw_snr + 1.6);
    }

    if (result->emission_center_frequency_hz.state == P0_PARAMETER_FIELD_VALID &&
        result->occupied_bandwidth_hz.reason != P0_PARAMETER_REASON_SPAN_EDGE_CLIPPING) {
        double corrected_lower;
        double corrected_upper;
        double lower_differences[4];
        double upper_differences[4];

        if (calculate_edges(runtime, -1, 0.0075, 2.5,
                            &corrected_lower, &corrected_upper) == 0) {
            int valid = 1;

            for (omitted = 0U; omitted < 4U; ++omitted) {
                double subset_lower;
                double subset_upper;
                if (calculate_edges(runtime, (int)omitted, 0.0075, 2.5,
                                    &subset_lower, &subset_upper) != 0) {
                    valid = 0;
                    break;
                }
                lower_differences[omitted] = fabs(subset_lower - corrected_lower);
                upper_differences[omitted] = fabs(subset_upper - corrected_upper);
            }
            if (valid) {
                temporal_range = fmax(median_four(lower_differences),
                                      median_four(upper_differences));
                corrected_lower -= 0.375;
                corrected_upper += 0.375;
                result->temporal_edge_range_bins = temporal_range;
                if (corrected_lower <= (double)lower + 0.5 ||
                    corrected_upper >= (double)upper - 0.5) {
                    set_field(&result->lower_occupied_edge_hz,
                              P0_PARAMETER_FIELD_UNCERTAIN,
                              P0_PARAMETER_REASON_SPAN_EDGE_CLIPPING, 0.0);
                    set_field(&result->upper_occupied_edge_hz,
                              P0_PARAMETER_FIELD_UNCERTAIN,
                              P0_PARAMETER_REASON_SPAN_EDGE_CLIPPING, 0.0);
                    set_field(&result->occupied_bandwidth_hz,
                              P0_PARAMETER_FIELD_UNCERTAIN,
                              P0_PARAMETER_REASON_SPAN_EDGE_CLIPPING, 0.0);
                } else if (temporal_range > 7.0) {
                    set_field(&result->lower_occupied_edge_hz,
                              P0_PARAMETER_FIELD_UNCERTAIN,
                              P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY, 0.0);
                    set_field(&result->upper_occupied_edge_hz,
                              P0_PARAMETER_FIELD_UNCERTAIN,
                              P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY, 0.0);
                    set_field(&result->occupied_bandwidth_hz,
                              P0_PARAMETER_FIELD_UNCERTAIN,
                              P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY, 0.0);
                } else {
                    set_field(&result->lower_occupied_edge_hz, P0_PARAMETER_FIELD_VALID,
                              P0_PARAMETER_REASON_NONE,
                              (double)runtime->center_frequency_hz +
                                  (corrected_lower - 2048.0) * bin_spacing);
                    set_field(&result->upper_occupied_edge_hz, P0_PARAMETER_FIELD_VALID,
                              P0_PARAMETER_REASON_NONE,
                              (double)runtime->center_frequency_hz +
                                  (corrected_upper - 2048.0) * bin_spacing);
                    set_field(&result->occupied_bandwidth_hz, P0_PARAMETER_FIELD_VALID,
                              P0_PARAMETER_REASON_NONE,
                              (corrected_upper - corrected_lower) * bin_spacing);
                }
            }
        }
    }
    return 0;
}

int p0_parameter_runtime_init(p0_parameter_runtime_t *runtime)
{
    size_t records = P0_PARAMETER_REQUIRED_FRAMES * P0_PARAMETER_MAXIMUM_LOCAL_BINS;

    if (runtime == NULL) {
        errno = EINVAL;
        return -1;
    }
    memset(runtime, 0, sizeof(*runtime));
    runtime->local_psd = calloc(records, sizeof(*runtime->local_psd));
    runtime->local_rectangular_fft = calloc(records, sizeof(*runtime->local_rectangular_fft));
    if (runtime->local_psd == NULL || runtime->local_rectangular_fft == NULL) {
        p0_parameter_runtime_release(runtime);
        errno = ENOMEM;
        return -1;
    }
    return 0;
}

void p0_parameter_runtime_release(p0_parameter_runtime_t *runtime)
{
    if (runtime == NULL)
        return;
    free(runtime->local_rectangular_fft);
    free(runtime->local_psd);
    memset(runtime, 0, sizeof(*runtime));
}

void p0_parameter_runtime_reset(p0_parameter_runtime_t *runtime)
{
    if (runtime == NULL)
        return;
    runtime->intent_id = 0U;
    runtime->event_id = 0U;
    runtime->sample_rate_hz = 0U;
    runtime->center_frequency_hz = 0;
    runtime->first_frame_id = 0U;
    runtime->last_frame_id = 0U;
    runtime->lower_shifted_bin = 0U;
    runtime->upper_shifted_bin = 0U;
    runtime->local_start_bin = 0U;
    runtime->local_bin_count = 0U;
    runtime->observation_count = 0U;
    runtime->active = 0U;
}

int p0_parameter_runtime_observe(
    p0_parameter_runtime_t *runtime, int start_measurement, uint64_t intent_id,
    uint64_t event_id, uint32_t frame_id, uint64_t sample_rate_hz,
    int64_t center_frequency_hz, uint16_t lower_shifted_bin,
    uint16_t upper_shifted_bin, int confirmed_and_observed, const uint8_t *iq_ci8,
    size_t iq_bytes, const uint64_t *shifted_power_uq28_30, size_t power_count,
    p0_parameter_result_t *result)
{
    unsigned int observation;
    unsigned int index;
    double normalization;

    if (runtime == NULL || runtime->local_psd == NULL ||
        runtime->local_rectangular_fft == NULL || result == NULL || iq_ci8 == NULL ||
        shifted_power_uq28_30 == NULL || iq_bytes != P0_PARAMETER_IQ_BYTES ||
        power_count != P0_PARAMETER_FFT_SIZE || intent_id == 0U || event_id == 0U ||
        sample_rate_hz == 0U || !valid_span(lower_shifted_bin, upper_shifted_bin)) {
        errno = EINVAL;
        return -1;
    }
    if (start_measurement) {
        p0_parameter_runtime_reset(runtime);
        runtime->intent_id = intent_id;
        runtime->event_id = event_id;
        runtime->sample_rate_hz = sample_rate_hz;
        runtime->center_frequency_hz = center_frequency_hz;
        runtime->first_frame_id = frame_id;
        runtime->last_frame_id = frame_id - 1U;
        runtime->lower_shifted_bin = lower_shifted_bin;
        runtime->upper_shifted_bin = upper_shifted_bin;
        runtime->local_start_bin = lower_shifted_bin - P0_PARAMETER_LOCAL_PADDING;
        runtime->local_bin_count = (uint16_t)(upper_shifted_bin - lower_shifted_bin + 1U +
                                              2U * P0_PARAMETER_LOCAL_PADDING);
        runtime->active = 1U;
    }
    if (!runtime->active || runtime->intent_id != intent_id || runtime->event_id != event_id ||
        runtime->sample_rate_hz != sample_rate_hz ||
        runtime->center_frequency_hz != center_frequency_hz ||
        runtime->lower_shifted_bin != lower_shifted_bin ||
        runtime->upper_shifted_bin != upper_shifted_bin ||
        frame_id != runtime->last_frame_id + 1U || !confirmed_and_observed) {
        p0_parameter_runtime_reset(runtime);
        initialize_result(result, intent_id, event_id, frame_id, 0U,
                          P0_PARAMETER_FIELD_INSUFFICIENT_QUALITY,
                          P0_PARAMETER_REASON_CONTEXT_LOST);
        return 0;
    }
    observation = runtime->observation_count;
    normalization = (double)sample_rate_hz * P0_PARAMETER_HANN_POWER_SUM;
    for (index = 0U; index < runtime->local_bin_count; ++index) {
        unsigned int shifted = runtime->local_start_bin + index;
        uint64_t raw = shifted_power_uq28_30[shifted];

        if (raw >= (UINT64_C(1) << 58)) {
            p0_parameter_runtime_reset(runtime);
            errno = ERANGE;
            return -1;
        }
        runtime->local_psd[observation * P0_PARAMETER_MAXIMUM_LOCAL_BINS + index] =
            ((double)raw / (double)(UINT64_C(1) << P0_PARAMETER_POWER_FRACTION_BITS)) /
            normalization;
    }
    if ((unsigned int)upper_shifted_bin - lower_shifted_bin + 1U >= 100U &&
        store_rectangular_fft(runtime, iq_ci8, observation) != 0) {
        p0_parameter_runtime_reset(runtime);
        return -1;
    }
    runtime->last_frame_id = frame_id;
    ++runtime->observation_count;
    if (runtime->observation_count < P0_PARAMETER_REQUIRED_FRAMES) {
        initialize_result(result, intent_id, event_id, frame_id,
                          runtime->observation_count,
                          P0_PARAMETER_FIELD_NOT_AVAILABLE,
                          P0_PARAMETER_REASON_ACCUMULATING);
        return 0;
    }
    initialize_result(result, intent_id, event_id, frame_id,
                      P0_PARAMETER_REQUIRED_FRAMES,
                      P0_PARAMETER_FIELD_NOT_AVAILABLE,
                      P0_PARAMETER_REASON_NONE);
    if (finalize_result(runtime, result) != 0) {
        p0_parameter_runtime_reset(runtime);
        return -1;
    }
    runtime->active = 0U;
    return 0;
}
