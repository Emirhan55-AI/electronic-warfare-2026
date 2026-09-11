#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

#include "p0_parameter_runtime.h"

#define IQ_BYTES (P0_PARAMETER_FFT_SIZE * 2U)
#define REQUIRE(condition) do { if (!(condition)) { \
    fprintf(stderr, "test failure at line %d\n", __LINE__); return 1; } } while (0)

static int observe(p0_parameter_runtime_t *runtime, p0_parameter_result_t *result,
                   int start, uint32_t frame, int confirmed,
                   uint16_t lower, uint16_t upper,
                   const uint8_t *iq, const uint64_t *power)
{
    return p0_parameter_runtime_observe(
        runtime, start, UINT64_C(17), UINT64_C(23), frame,
        UINT64_C(2000000), INT64_C(2600000000), lower, upper,
        confirmed, iq, IQ_BYTES, power, P0_PARAMETER_FFT_SIZE, result);
}

int main(void)
{
    p0_parameter_runtime_t runtime;
    p0_parameter_result_t result;
    uint8_t *iq = calloc(IQ_BYTES, 1U);
    uint64_t *power = calloc(P0_PARAMETER_FFT_SIZE, sizeof(*power));
    volatile size_t payload_bytes = P0_PARAMETER_REQUIRED_FRAMES *
                                    P0_PARAMETER_MAXIMUM_LOCAL_BINS *
                                    (sizeof(double) + sizeof(p0_parameter_complex_t));
    unsigned int index;

    /* Artificial calibration fixtures validate arithmetic and rejection only;
     * they must never be deployed as an actual receiver calibration. */
    {
        p0_power_calibration_t calibration = {0};
        p0_parameter_field_t measured_power = {P0_PARAMETER_FIELD_VALID, P0_PARAMETER_REASON_NONE, -30.0};
        p0_calibrated_power_t calibrated;
        uint8_t context[32] = {1};
        memcpy(calibration.context_sha256, context, sizeof(context));
        calibration.reference_dbfs = -40.0;
        calibration.reference_dbm = -70.0;
        calibration.minimum_dbfs = -50.0;
        calibration.maximum_dbfs = -20.0;
        calibration.uncertainty_db = 1.5;
        calibration.measured_at_unix = 100U;
        calibration.valid_until_unix = 200U;
        REQUIRE(p0_parameter_calibrate_power(&measured_power, &calibration, context, 150U, &calibrated) == 0);
        REQUIRE(calibrated.valid && fabs(calibrated.dbm - (-60.0)) < 1e-12);
        REQUIRE(calibrated.uncertainty_db == 1.5);
        context[31] = 1U;
        REQUIRE(p0_parameter_calibrate_power(&measured_power, &calibration, context, 150U, &calibrated) == -1);
        REQUIRE(!calibrated.valid && isnan(calibrated.dbm));
        context[31] = 0U;
        REQUIRE(p0_parameter_calibrate_power(&measured_power, NULL, context, 150U, &calibrated) == -1);
        REQUIRE(!calibrated.valid && isnan(calibrated.dbm));
        REQUIRE(p0_parameter_calibrate_power(&measured_power, &calibration, context, 99U, &calibrated) == -1);
        REQUIRE(p0_parameter_calibrate_power(&measured_power, &calibration, context, 201U, &calibrated) == -1);
        measured_power.value = -51.0;
        REQUIRE(p0_parameter_calibrate_power(&measured_power, &calibration, context, 150U, &calibrated) == -1);
        measured_power.value = NAN;
        REQUIRE(p0_parameter_calibrate_power(&measured_power, &calibration, context, 150U, &calibrated) == -1);
        measured_power.value = -30.0;
        measured_power.state = P0_PARAMETER_FIELD_UNCERTAIN;
        REQUIRE(p0_parameter_calibrate_power(&measured_power, &calibration, context, 150U, &calibrated) == -1);
        measured_power.state = P0_PARAMETER_FIELD_VALID;
        calibration.uncertainty_db = 0.0;
        REQUIRE(p0_parameter_calibrate_power(&measured_power, &calibration, context, 150U, &calibrated) == -1);
    }

    REQUIRE(payload_bytes == P0_PARAMETER_PERSISTENT_PAYLOAD_BYTES);
    REQUIRE(payload_bytes <= 65536U);
    REQUIRE(iq != NULL && power != NULL);
    for (index = 0U; index < P0_PARAMETER_FFT_SIZE; ++index)
        power[index] = UINT64_C(1) << 30;
    REQUIRE(p0_parameter_runtime_init(&runtime) == 0);

    REQUIRE(observe(&runtime, &result, 1, 10U, 1, 2000U, 2031U, iq, power) == 0);
    REQUIRE(result.observation_count == 1U);
    REQUIRE(result.emission_center_frequency_hz.state == P0_PARAMETER_FIELD_NOT_AVAILABLE);
    REQUIRE(result.emission_center_frequency_hz.reason == P0_PARAMETER_REASON_ACCUMULATING);
    REQUIRE(observe(&runtime, &result, 0, 11U, 0, 2000U, 2031U, iq, power) == 0);
    REQUIRE(result.observation_count == 0U);
    REQUIRE(result.emission_center_frequency_hz.state ==
            P0_PARAMETER_FIELD_INSUFFICIENT_QUALITY);
    REQUIRE(result.emission_center_frequency_hz.reason == P0_PARAMETER_REASON_CONTEXT_LOST);
    REQUIRE(runtime.active == 0U);

    REQUIRE(observe(&runtime, &result, 1, 20U, 1, 2000U, 2031U, iq, power) == 0);
    errno = 0;
    REQUIRE(observe(&runtime, &result, 0, 21U, 1, 2000U, 2006U, iq, power) == -1);
    REQUIRE(errno == EINVAL && runtime.active == 1U && runtime.observation_count == 1U);
    REQUIRE(observe(&runtime, &result, 0, 21U, 1, 2000U, 2031U, iq, power) == 0);
    REQUIRE(result.observation_count == 2U);
    REQUIRE(observe(&runtime, &result, 0, 22U, 1, 2000U, 2031U, iq, power) == 0);
    REQUIRE(result.observation_count == 3U);
    REQUIRE(observe(&runtime, &result, 0, 23U, 1, 2000U, 2031U, iq, power) == 0);
    REQUIRE(result.observation_count == P0_PARAMETER_REQUIRED_FRAMES);
    REQUIRE(runtime.active == 0U);

    REQUIRE(observe(&runtime, &result, 1, 30U, 1, 2000U, 2031U, iq, power) == 0);
    REQUIRE(p0_parameter_runtime_observe(
                &runtime, 0, UINT64_C(17), UINT64_C(23), 32U,
                UINT64_C(2000000), INT64_C(2600000000), 2000U, 2031U, 1,
                iq, IQ_BYTES, power, P0_PARAMETER_FFT_SIZE, &result) == 0);
    REQUIRE(result.emission_center_frequency_hz.reason == P0_PARAMETER_REASON_CONTEXT_LOST);
    REQUIRE(runtime.active == 0U);

    p0_parameter_runtime_release(&runtime);
    free(power);
    free(iq);
    puts("P0_PARAMETER_RUNTIME_STATE_TEST=PASS");
    return 0;
}
