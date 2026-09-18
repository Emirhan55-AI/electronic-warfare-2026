#ifndef P0_AMPLITUDE_DF_H
#define P0_AMPLITUDE_DF_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define P0_DF_MAX_MEASUREMENTS 96U

typedef enum {
    P0_DF_STATUS_INSUFFICIENT_ANGLES = 0,
    P0_DF_STATUS_INSUFFICIENT_COVERAGE = 1,
    P0_DF_STATUS_INSUFFICIENT_REPEATS = 2,
    P0_DF_STATUS_RECEIVER_CHANGED = 3,
    P0_DF_STATUS_TARGET_CHANGED = 4,
    P0_DF_STATUS_FRONT_BACK_AMBIGUOUS = 5,
    P0_DF_STATUS_AMBIGUOUS_MAXIMUM = 6,
    P0_DF_STATUS_LOB_READY = 7
} p0_df_status_t;

typedef struct {
    uint32_t minimum_distinct_angles;
    double maximum_angular_gap_deg;
    double minimum_peak_prominence_db;
    double minimum_front_to_back_db;
    uint32_t minimum_measurements_per_angle;
} p0_df_profile_t;

typedef struct {
    double angle_deg;
    double relative_power_db;
    double frequency_hz;
    double confidence;
    double power_spread_db;
    uint32_t observation_count;
    double channel_bandwidth_hz;
    uint8_t channel_bandwidth_valid;
    uint64_t receiver_binding_hash;
    uint8_t receiver_binding_valid;
    uint32_t frame_id;
    uint8_t frame_id_valid;
} p0_df_measurement_t;

typedef struct {
    p0_df_status_t status;
    double raw_maximum_angle_deg;
    double estimated_angle_deg;
    double peak_power_db;
    double confidence;
    uint32_t measurement_count;
    uint32_t distinct_angle_count;
    double maximum_angular_gap_deg;
    double peak_prominence_db;
    double front_to_back_db;
    uint8_t front_to_back_valid;
    double angular_sampling_rms_deg;
    uint8_t angular_sampling_rms_valid;
} p0_df_result_t;

/* Product profile: adaptive lobe bracket/refinement plus opposite-point gate. */
const p0_df_profile_t *p0_amplitude_df_field_profile(void);

/* Returns 0 on success, -1 for invalid input and -2 for a duplicate source frame. */
int p0_amplitude_df_estimate(const p0_df_measurement_t *measurements,
                             size_t measurement_count,
                             const p0_df_profile_t *profile,
                             p0_df_result_t *result);

double p0_df_angular_error_deg(double estimated_deg, double ground_truth_deg);
double p0_df_rms_error_deg(const double *estimates_deg,
                           const double *ground_truths_deg,
                           size_t count);
const char *p0_df_status_name(p0_df_status_t status);

#ifdef __cplusplus
}
#endif

#endif
