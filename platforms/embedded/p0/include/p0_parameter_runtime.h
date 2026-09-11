#ifndef P0_PARAMETER_RUNTIME_H
#define P0_PARAMETER_RUNTIME_H

#include <stddef.h>
#include <stdint.h>

#define P0_PARAMETER_FFT_SIZE 4096U
#define P0_PARAMETER_REQUIRED_FRAMES 4U
#define P0_PARAMETER_MINIMUM_SPAN_BINS 8U
#define P0_PARAMETER_MAXIMUM_SPAN_BINS 512U
#define P0_PARAMETER_REFERENCE_BINS 32U
#define P0_PARAMETER_REFERENCE_GAP 4U
#define P0_PARAMETER_LOCAL_PADDING \
    (P0_PARAMETER_REFERENCE_BINS + P0_PARAMETER_REFERENCE_GAP)
#define P0_PARAMETER_MAXIMUM_LOCAL_BINS \
    (P0_PARAMETER_MAXIMUM_SPAN_BINS + 2U * P0_PARAMETER_LOCAL_PADDING)
#define P0_PARAMETER_PERSISTENT_PAYLOAD_BYTES 56064U

typedef enum {
    P0_PARAMETER_FIELD_NOT_AVAILABLE = 0,
    P0_PARAMETER_FIELD_VALID = 1,
    P0_PARAMETER_FIELD_INSUFFICIENT_QUALITY = 2,
    P0_PARAMETER_FIELD_UNCERTAIN = 3,
    P0_PARAMETER_FIELD_NOT_OBSERVED = 4
} p0_parameter_field_state_t;

typedef enum {
    P0_PARAMETER_REASON_NONE = 0,
    P0_PARAMETER_REASON_ACCUMULATING = 1,
    P0_PARAMETER_REASON_CONTEXT_LOST = 2,
    P0_PARAMETER_REASON_REFERENCE_POWER = 3,
    P0_PARAMETER_REASON_REFERENCE_MISMATCH = 4,
    P0_PARAMETER_REASON_EXCESS_POWER = 5,
    P0_PARAMETER_REASON_CENTER_TEMPORAL_UNCERTAINTY = 6,
    P0_PARAMETER_REASON_SPAN_EDGE_CLIPPING = 7,
    P0_PARAMETER_REASON_OBW_TEMPORAL_INSTABILITY = 8,
    P0_PARAMETER_REASON_CARRIER_THRESHOLD = 9,
    P0_PARAMETER_REASON_CARRIER_LOW_SNR = 10
} p0_parameter_reason_t;

typedef struct {
    uint8_t state;
    uint8_t reason;
    double value;
} p0_parameter_field_t;

/* A calibration is valid only for the receiver configuration identified by
 * context_sha256 (device, tuning, sample rate, gains, filter and sample scale).
 * Bounds must come from measured calibration coverage, never extrapolation.
 * This API does not establish that the supplied reference is calibrated. */
typedef struct {
    uint8_t context_sha256[32];
    double reference_dbfs;
    double reference_dbm;
    double minimum_dbfs;
    double maximum_dbfs;
    double uncertainty_db; /* Calibration contribution, not total measurement uncertainty. */
    uint64_t measured_at_unix;
    uint64_t valid_until_unix;
} p0_power_calibration_t;

typedef struct {
    uint8_t valid;
    double dbm;
    double uncertainty_db;
} p0_calibrated_power_t;

/* Returns 0 only for an applicable measured calibration; otherwise -1 and
 * NaN output. Neither missing profiles nor changed gains fall back to dBm. */
int p0_parameter_calibrate_power(
    const p0_parameter_field_t *power_dbfs,
    const p0_power_calibration_t *calibration,
    const uint8_t context_sha256[32], uint64_t now_unix,
    p0_calibrated_power_t *result);

typedef struct {
    uint64_t intent_id;
    uint64_t event_id;
    uint32_t frame_id;
    uint8_t observation_count;
    p0_parameter_field_t emission_center_frequency_hz;
    p0_parameter_field_t lower_occupied_edge_hz;
    p0_parameter_field_t upper_occupied_edge_hz;
    p0_parameter_field_t occupied_bandwidth_hz;
    p0_parameter_field_t channel_power_dbfs;
    p0_parameter_field_t snr_estimate_db;
    double reference_difference_db;
    double detection_significance;
    double center_uncertainty_bins;
    double temporal_edge_range_bins;
    /* Local extension: the legacy 128-byte service result does not carry this field. */
    p0_parameter_field_t carrier_line_frequency_hz;
} p0_parameter_result_t;

typedef struct {
    double real;
    double imag;
} p0_parameter_complex_t;

typedef struct {
    double *local_psd;
    p0_parameter_complex_t *local_rectangular_fft;
    uint64_t intent_id;
    uint64_t event_id;
    uint64_t sample_rate_hz;
    int64_t center_frequency_hz;
    uint32_t first_frame_id;
    uint32_t last_frame_id;
    uint16_t lower_shifted_bin;
    uint16_t upper_shifted_bin;
    uint16_t local_start_bin;
    uint16_t local_bin_count;
    uint8_t observation_count;
    uint8_t active;
} p0_parameter_runtime_t;

int p0_parameter_runtime_init(p0_parameter_runtime_t *runtime);
void p0_parameter_runtime_release(p0_parameter_runtime_t *runtime);
void p0_parameter_runtime_reset(p0_parameter_runtime_t *runtime);

int p0_parameter_power_from_ci8(const uint8_t *iq_ci8, size_t iq_bytes,
                                uint64_t *shifted_power_uq28_30,
                                size_t power_count);

int p0_parameter_runtime_observe(
    p0_parameter_runtime_t *runtime,
    int start_measurement,
    uint64_t intent_id,
    uint64_t event_id,
    uint32_t frame_id,
    uint64_t sample_rate_hz,
    int64_t center_frequency_hz,
    uint16_t lower_shifted_bin,
    uint16_t upper_shifted_bin,
    int confirmed_and_observed,
    const uint8_t *iq_ci8,
    size_t iq_bytes,
    const uint64_t *shifted_power_uq28_30,
    size_t power_count,
    p0_parameter_result_t *result);

#endif
