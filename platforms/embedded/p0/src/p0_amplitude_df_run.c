#define _CRT_SECURE_NO_WARNINGS

#include "p0_amplitude_df.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    FILE *stream;
    p0_df_measurement_t measurements[P0_DF_MAX_MEASUREMENTS];
    p0_df_result_t result;
    unsigned long raw_count;
    size_t count;
    size_t index;
    int code;
    if (argc == 3 && strcmp(argv[1], "--rms") == 0) {
        double estimates[P0_DF_MAX_MEASUREMENTS];
        double truths[P0_DF_MAX_MEASUREMENTS];
        stream = fopen(argv[2], "r");
        if (stream == NULL || fscanf(stream, "%lu", &raw_count) != 1 ||
            raw_count == 0UL || raw_count > P0_DF_MAX_MEASUREMENTS) {
            if (stream != NULL) fclose(stream);
            fprintf(stderr, "invalid RMS file\n");
            return 2;
        }
        count = (size_t)raw_count;
        for (index = 0U; index < count; ++index) {
            if (fscanf(stream, "%lf %lf", &estimates[index], &truths[index]) != 2) {
                fclose(stream);
                fprintf(stderr, "invalid RMS row %lu\n", (unsigned long)index);
                return 2;
            }
        }
        fclose(stream);
        printf("RMS %.17g\n", p0_df_rms_error_deg(estimates, truths, count));
        return 0;
    }
    if (argc != 2) {
        fprintf(stderr, "usage: p0-amplitude-df-run measurements.txt | --rms pairs.txt\n");
        return 2;
    }
    stream = fopen(argv[1], "r");
    if (stream == NULL || fscanf(stream, "%lu", &raw_count) != 1 ||
        raw_count == 0UL || raw_count > P0_DF_MAX_MEASUREMENTS) {
        if (stream != NULL) fclose(stream);
        fprintf(stderr, "invalid measurement file\n");
        return 2;
    }
    count = (size_t)raw_count;
    for (index = 0U; index < count; ++index) {
        unsigned int bandwidth_valid;
        unsigned int binding_valid;
        unsigned int frame_valid;
        unsigned int observation_count;
        unsigned int frame_id;
        uint64_t binding_hash;
        if (fscanf(stream, "%lf %lf %lf %lf %lf %u %lf %u %" SCNu64 " %u %u %u",
                   &measurements[index].angle_deg,
                   &measurements[index].relative_power_db,
                   &measurements[index].frequency_hz,
                   &measurements[index].confidence,
                   &measurements[index].power_spread_db,
                   &observation_count,
                   &measurements[index].channel_bandwidth_hz,
                   &bandwidth_valid,
                   &binding_hash,
                   &binding_valid,
                   &frame_id,
                   &frame_valid) != 12) {
            fclose(stream);
            fprintf(stderr, "invalid measurement row %lu\n", (unsigned long)index);
            return 2;
        }
        measurements[index].observation_count = observation_count;
        measurements[index].channel_bandwidth_valid = (uint8_t)(bandwidth_valid != 0U);
        measurements[index].receiver_binding_hash = binding_hash;
        measurements[index].receiver_binding_valid = (uint8_t)(binding_valid != 0U);
        measurements[index].frame_id = frame_id;
        measurements[index].frame_id_valid = (uint8_t)(frame_valid != 0U);
    }
    fclose(stream);
    code = p0_amplitude_df_estimate(
        measurements, count, p0_amplitude_df_field_profile(), &result);
    if (code != 0) {
        printf("ERROR %d\n", code);
        return code == -2 ? 3 : 2;
    }
    printf("RESULT %d %s %.17g %.17g %.17g %.17g %u %u %.17g %.17g %u %.17g %u %.17g\n",
           (int)result.status, p0_df_status_name(result.status),
           result.raw_maximum_angle_deg, result.estimated_angle_deg,
           result.peak_power_db, result.confidence,
           result.measurement_count, result.distinct_angle_count,
           result.maximum_angular_gap_deg, result.peak_prominence_db,
           (unsigned int)result.front_to_back_valid, result.front_to_back_db,
           (unsigned int)result.angular_sampling_rms_valid,
           result.angular_sampling_rms_deg);
    return 0;
}
