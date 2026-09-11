#include "p0_amplitude_df.h"

#include <float.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    double angle_deg;
    double power_db;
    double confidence;
    double spread_db;
    uint32_t repeat_count;
} p0_df_point_t;

static const p0_df_profile_t P0_FIELD_PROFILE = {
    24U,
    15.0,
    3.0,
    3.0,
    1U,
};

static int compare_double(const void *left, const void *right)
{
    const double a = *(const double *)left;
    const double b = *(const double *)right;
    return (a > b) - (a < b);
}

static int compare_point_power(const void *left, const void *right)
{
    const p0_df_point_t *a = (const p0_df_point_t *)left;
    const p0_df_point_t *b = (const p0_df_point_t *)right;
    if (a->power_db != b->power_db) {
        return a->power_db < b->power_db ? 1 : -1;
    }
    return (a->angle_deg > b->angle_deg) - (a->angle_deg < b->angle_deg);
}

static double median_of(double *values, size_t count)
{
    qsort(values, count, sizeof(values[0]), compare_double);
    if ((count & 1U) != 0U) {
        return values[count / 2U];
    }
    return (values[count / 2U - 1U] + values[count / 2U]) / 2.0;
}

static double normalized_angle(double angle_deg)
{
    double result = fmod(angle_deg, 360.0);
    if (result < 0.0) {
        result += 360.0;
    }
    return result;
}

static int valid_profile(const p0_df_profile_t *profile)
{
    return profile != NULL && profile->minimum_distinct_angles > 0U &&
           profile->minimum_distinct_angles <= P0_DF_MAX_MEASUREMENTS &&
           isfinite(profile->maximum_angular_gap_deg) &&
           profile->maximum_angular_gap_deg > 0.0 &&
           profile->maximum_angular_gap_deg <= 360.0 &&
           isfinite(profile->minimum_peak_prominence_db) &&
           profile->minimum_peak_prominence_db >= 0.0 &&
           isfinite(profile->minimum_front_to_back_db) &&
           profile->minimum_front_to_back_db >= 0.0 &&
           profile->minimum_measurements_per_angle > 0U;
}

static int valid_measurement(const p0_df_measurement_t *measurement)
{
    return isfinite(measurement->angle_deg) &&
           isfinite(measurement->relative_power_db) &&
           isfinite(measurement->frequency_hz) &&
           measurement->frequency_hz > 0.0 &&
           isfinite(measurement->confidence) &&
           measurement->confidence >= 0.0 && measurement->confidence <= 1.0 &&
           isfinite(measurement->power_spread_db) &&
           measurement->power_spread_db >= 0.0 &&
           measurement->observation_count > 0U &&
           (!measurement->channel_bandwidth_valid ||
            (isfinite(measurement->channel_bandwidth_hz) &&
             measurement->channel_bandwidth_hz > 0.0));
}

const p0_df_profile_t *p0_amplitude_df_field_profile(void)
{
    return &P0_FIELD_PROFILE;
}

double p0_df_angular_error_deg(double estimated_deg, double ground_truth_deg)
{
    double error;
    if (!isfinite(estimated_deg) || !isfinite(ground_truth_deg)) {
        return NAN;
    }
    error = normalized_angle(estimated_deg - ground_truth_deg + 180.0) - 180.0;
    return fabs(error);
}

double p0_df_rms_error_deg(const double *estimates_deg,
                           const double *ground_truths_deg,
                           size_t count)
{
    size_t index;
    double square_sum = 0.0;
    if (estimates_deg == NULL || ground_truths_deg == NULL || count == 0U) {
        return NAN;
    }
    for (index = 0U; index < count; ++index) {
        const double error = p0_df_angular_error_deg(estimates_deg[index], ground_truths_deg[index]);
        if (!isfinite(error)) {
            return NAN;
        }
        square_sum += error * error;
    }
    return sqrt(square_sum / (double)count);
}

const char *p0_df_status_name(p0_df_status_t status)
{
    switch (status) {
    case P0_DF_STATUS_INSUFFICIENT_ANGLES: return "INSUFFICIENT_ANGLES";
    case P0_DF_STATUS_INSUFFICIENT_COVERAGE: return "INSUFFICIENT_COVERAGE";
    case P0_DF_STATUS_INSUFFICIENT_REPEATS: return "INSUFFICIENT_REPEATS";
    case P0_DF_STATUS_RECEIVER_CHANGED: return "RECEIVER_CHANGED";
    case P0_DF_STATUS_TARGET_CHANGED: return "TARGET_CHANGED";
    case P0_DF_STATUS_FRONT_BACK_AMBIGUOUS: return "FRONT_BACK_AMBIGUOUS";
    case P0_DF_STATUS_AMBIGUOUS_MAXIMUM: return "AMBIGUOUS_MAXIMUM";
    case P0_DF_STATUS_LOB_READY: return "LOB_READY";
    default: return "INVALID";
    }
}

int p0_amplitude_df_estimate(const p0_df_measurement_t *measurements,
                             size_t measurement_count,
                             const p0_df_profile_t *profile,
                             p0_df_result_t *result)
{
    p0_df_point_t points[P0_DF_MAX_MEASUREMENTS];
    double angles[P0_DF_MAX_MEASUREMENTS];
    double gaps[P0_DF_MAX_MEASUREMENTS];
    size_t point_count = 0U;
    size_t index;
    double maximum_gap;
    double nominal_step;
    double competitor_power = -DBL_MAX;
    double prominence;
    double opposite_target;
    size_t opposite_index = 0U;
    double front_to_back = 0.0;
    int front_to_back_valid = 0;
    double coverage_confidence;
    double stability_confidence;
    double prominence_confidence;
    double confidence;
    int receiver_changed = 0;
    int target_changed = 0;

    if (measurements == NULL || result == NULL || measurement_count == 0U ||
        measurement_count > P0_DF_MAX_MEASUREMENTS || !valid_profile(profile)) {
        return -1;
    }
    memset(result, 0, sizeof(*result));
    for (index = 0U; index < measurement_count; ++index) {
        size_t previous;
        if (!valid_measurement(&measurements[index])) {
            return -1;
        }
        for (previous = 0U; previous < index; ++previous) {
            if (measurements[index].frame_id_valid && measurements[previous].frame_id_valid &&
                measurements[index].frame_id == measurements[previous].frame_id &&
                measurements[index].receiver_binding_valid == measurements[previous].receiver_binding_valid &&
                (!measurements[index].receiver_binding_valid ||
                 measurements[index].receiver_binding_hash == measurements[previous].receiver_binding_hash)) {
                return -2;
            }
        }
    }

    for (index = 0U; index < measurement_count; ++index) {
        const double angle = normalized_angle(measurements[index].angle_deg);
        size_t point_index;
        for (point_index = 0U; point_index < point_count; ++point_index) {
            if (points[point_index].angle_deg == angle) {
                break;
            }
        }
        if (point_index == point_count) {
            points[point_count].angle_deg = angle;
            ++point_count;
        }
    }

    for (index = 0U; index < point_count; ++index) {
        double powers[P0_DF_MAX_MEASUREMENTS];
        double deviations[P0_DF_MAX_MEASUREMENTS];
        size_t repeats = 0U;
        size_t measurement_index;
        double weight_sum = 0.0;
        double linear_sum = 0.0;
        double confidence_sum = 0.0;
        double spread_square_sum = 0.0;
        double centre;
        double between_repeat_spread;
        for (measurement_index = 0U; measurement_index < measurement_count; ++measurement_index) {
            const p0_df_measurement_t *measurement = &measurements[measurement_index];
            double weight;
            if (normalized_angle(measurement->angle_deg) != points[index].angle_deg) {
                continue;
            }
            weight = fmax(measurement->confidence, 0.01) * (double)measurement->observation_count;
            powers[repeats++] = measurement->relative_power_db;
            weight_sum += weight;
            linear_sum += pow(10.0, measurement->relative_power_db / 10.0) * weight;
            confidence_sum += measurement->confidence;
            spread_square_sum += measurement->power_spread_db * measurement->power_spread_db;
        }
        centre = median_of(powers, repeats);
        for (measurement_index = 0U; measurement_index < repeats; ++measurement_index) {
            deviations[measurement_index] = fabs(powers[measurement_index] - centre);
        }
        between_repeat_spread = 1.4826 * median_of(deviations, repeats);
        points[index].power_db = 10.0 * log10(fmax(linear_sum / weight_sum, 1.0e-300));
        points[index].confidence = confidence_sum / (double)repeats;
        points[index].spread_db = hypot(
            between_repeat_spread,
            sqrt(spread_square_sum / (double)repeats));
        points[index].repeat_count = (uint32_t)repeats;
        angles[index] = points[index].angle_deg;
    }

    qsort(points, point_count, sizeof(points[0]), compare_point_power);
    qsort(angles, point_count, sizeof(angles[0]), compare_double);
    for (index = 0U; index < point_count; ++index) {
        gaps[index] = index + 1U < point_count
            ? angles[index + 1U] - angles[index]
            : angles[0] + 360.0 - angles[index];
    }
    maximum_gap = gaps[0];
    for (index = 1U; index < point_count; ++index) {
        maximum_gap = fmax(maximum_gap, gaps[index]);
    }
    nominal_step = median_of(gaps, point_count);

    for (index = 1U; index < point_count; ++index) {
        if (p0_df_angular_error_deg(points[index].angle_deg, points[0].angle_deg) >
            fmax(15.0, nominal_step * 1.5)) {
            competitor_power = fmax(competitor_power, points[index].power_db);
        }
    }
    if (competitor_power == -DBL_MAX) {
        competitor_power = point_count > 1U ? points[1].power_db : points[0].power_db;
    }
    prominence = fmax(0.0, points[0].power_db - competitor_power);

    opposite_target = normalized_angle(points[0].angle_deg + 180.0);
    for (index = 1U; index < point_count; ++index) {
        if (p0_df_angular_error_deg(points[index].angle_deg, opposite_target) <
            p0_df_angular_error_deg(points[opposite_index].angle_deg, opposite_target)) {
            opposite_index = index;
        }
    }
    if (p0_df_angular_error_deg(points[opposite_index].angle_deg, opposite_target) <=
        fmax(7.5, nominal_step / 2.0 + 1.0e-9)) {
        front_to_back = points[0].power_db - points[opposite_index].power_db;
        front_to_back_valid = 1;
    }

    for (index = 1U; index < measurement_count; ++index) {
        if (measurements[index].receiver_binding_valid) {
            size_t previous;
            for (previous = 0U; previous < index; ++previous) {
                if (measurements[previous].receiver_binding_valid &&
                    measurements[previous].receiver_binding_hash != measurements[index].receiver_binding_hash) {
                    receiver_changed = 1;
                }
            }
        }
    }
    {
        double minimum_frequency = measurements[0].frequency_hz;
        double maximum_frequency = measurements[0].frequency_hz;
        double minimum_bandwidth = DBL_MAX;
        int bandwidth_available = 0;
        for (index = 0U; index < measurement_count; ++index) {
            minimum_frequency = fmin(minimum_frequency, measurements[index].frequency_hz);
            maximum_frequency = fmax(maximum_frequency, measurements[index].frequency_hz);
            if (measurements[index].channel_bandwidth_valid) {
                minimum_bandwidth = fmin(minimum_bandwidth, measurements[index].channel_bandwidth_hz);
                bandwidth_available = 1;
            }
        }
        target_changed = bandwidth_available &&
                         maximum_frequency - minimum_frequency > minimum_bandwidth / 2.0;
    }

    coverage_confidence = fmin(1.0, profile->maximum_angular_gap_deg / maximum_gap);
    stability_confidence = 1.0 / (1.0 + points[0].spread_db);
    prominence_confidence = fmin(
        1.0, prominence / fmax(6.0, profile->minimum_peak_prominence_db));
    confidence = points[0].confidence * coverage_confidence *
                 stability_confidence * prominence_confidence;

    if (point_count < profile->minimum_distinct_angles) {
        result->status = P0_DF_STATUS_INSUFFICIENT_ANGLES;
    } else if (maximum_gap > profile->maximum_angular_gap_deg + 1.0e-9) {
        result->status = P0_DF_STATUS_INSUFFICIENT_COVERAGE;
    } else {
        int insufficient_repeats = 0;
        for (index = 0U; index < point_count; ++index) {
            if (points[index].repeat_count < profile->minimum_measurements_per_angle) {
                insufficient_repeats = 1;
            }
        }
        if (insufficient_repeats) {
            result->status = P0_DF_STATUS_INSUFFICIENT_REPEATS;
        } else if (receiver_changed) {
            result->status = P0_DF_STATUS_RECEIVER_CHANGED;
        } else if (target_changed) {
            result->status = P0_DF_STATUS_TARGET_CHANGED;
        } else if (!front_to_back_valid ||
                   front_to_back < profile->minimum_front_to_back_db) {
            result->status = P0_DF_STATUS_FRONT_BACK_AMBIGUOUS;
        } else if (prominence < fmax(profile->minimum_peak_prominence_db,
                                    2.0 * points[0].spread_db) ||
                   confidence < 0.15) {
            result->status = P0_DF_STATUS_AMBIGUOUS_MAXIMUM;
        } else {
            result->status = P0_DF_STATUS_LOB_READY;
        }
    }

    result->raw_maximum_angle_deg = points[0].angle_deg;
    result->estimated_angle_deg = points[0].angle_deg;
    result->peak_power_db = points[0].power_db;
    result->confidence = confidence;
    result->measurement_count = (uint32_t)measurement_count;
    result->distinct_angle_count = (uint32_t)point_count;
    result->maximum_angular_gap_deg = maximum_gap;
    result->peak_prominence_db = prominence;
    result->front_to_back_db = front_to_back;
    result->front_to_back_valid = (uint8_t)front_to_back_valid;
    {
        double minimum_gap = gaps[0];
        for (index = 1U; index < point_count; ++index) {
            minimum_gap = fmin(minimum_gap, gaps[index]);
        }
        if (maximum_gap - minimum_gap <= 1.0e-6) {
            result->angular_sampling_rms_deg = nominal_step / sqrt(12.0);
            result->angular_sampling_rms_valid = 1U;
        }
    }
    return 0;
}
