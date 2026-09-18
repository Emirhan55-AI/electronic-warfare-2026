#if defined(_MSC_VER)
#define _CRT_SECURE_NO_WARNINGS
#endif

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "p0_parameter_runtime.h"

#define P0_PARAMETER_POWER_BYTES (P0_PARAMETER_FFT_SIZE * 8U)

static int read_exact(const char *path, uint8_t *buffer, size_t bytes)
{
    FILE *file = fopen(path, "rb");
    int extra;

    if (file == NULL)
        return -1;
    if (fread(buffer, 1U, bytes, file) != bytes) {
        fclose(file);
        errno = EINVAL;
        return -1;
    }
    extra = fgetc(file);
    fclose(file);
    if (extra != EOF) {
        errno = EFBIG;
        return -1;
    }
    return 0;
}

static uint64_t load_le64(const uint8_t *source)
{
    uint64_t value = 0U;
    unsigned int byte;

    for (byte = 0U; byte < 8U; ++byte)
        value |= (uint64_t)source[byte] << (8U * byte);
    return value;
}

static int parse_u64(const char *text, uint64_t *value)
{
    char *end = NULL;
    unsigned long long parsed = strtoull(text, &end, 10);

    if (end == text || *end != '\0')
        return -1;
    *value = (uint64_t)parsed;
    return 0;
}

static int parse_i64(const char *text, int64_t *value)
{
    char *end = NULL;
    long long parsed = strtoll(text, &end, 10);

    if (end == text || *end != '\0')
        return -1;
    *value = (int64_t)parsed;
    return 0;
}

static void write_field(FILE *file, const char *name, const p0_parameter_field_t *field,
                        int comma)
{
    fprintf(file, "  \"%s\":{\"state\":%u,\"reason\":%u,\"value\":",
            name, (unsigned int)field->state, (unsigned int)field->reason);
    if (isfinite(field->value))
        fprintf(file, "%.17g", field->value);
    else
        fputs("null", file);
    fprintf(file, "}%s\n", comma ? "," : "");
}

static void write_json_double(FILE *file, double value)
{
    if (isfinite(value))
        fprintf(file, "%.17g", value);
    else
        fputs("null", file);
}

static int write_result(const char *path, const p0_parameter_result_t *result)
{
    FILE *file = fopen(path, "wb");

    if (file == NULL)
        return -1;
    fprintf(file,
            "{\n  \"schema_version\":1,\n  \"intent_id\":%" PRIu64
            ",\n  \"event_id\":%" PRIu64 ",\n  \"frame_id\":%" PRIu32
            ",\n  \"observation_count\":%u,\n",
            result->intent_id, result->event_id, result->frame_id,
            (unsigned int)result->observation_count);
    write_field(file, "emission_center_frequency_hz",
                &result->emission_center_frequency_hz, 1);
    write_field(file, "lower_occupied_edge_hz", &result->lower_occupied_edge_hz, 1);
    write_field(file, "upper_occupied_edge_hz", &result->upper_occupied_edge_hz, 1);
    write_field(file, "occupied_bandwidth_hz", &result->occupied_bandwidth_hz, 1);
    write_field(file, "channel_power_dbfs", &result->channel_power_dbfs, 1);
    write_field(file, "snr_estimate_db", &result->snr_estimate_db, 1);
    write_field(file, "carrier_line_frequency_hz", &result->carrier_line_frequency_hz, 1);
    write_field(file, "recovered_carrier_frequency_hz", &result->recovered_carrier_frequency_hz, 1);
    fprintf(file, "  \"carrier_recovery_order\":%u,\n", (unsigned int)result->carrier_recovery_order);
    fputs("  \"quality\":{\"reference_difference_db\":", file);
    write_json_double(file, result->reference_difference_db);
    fputs(",\"detection_significance\":", file);
    write_json_double(file, result->detection_significance);
    fputs(",\"center_uncertainty_bins\":", file);
    write_json_double(file, result->center_uncertainty_bins);
    fputs(",\"temporal_edge_range_bins\":", file);
    write_json_double(file, result->temporal_edge_range_bins);
    fputs("}\n}\n", file);
    return fclose(file);
}

int main(int argc, char **argv)
{
    p0_parameter_runtime_t runtime;
    p0_parameter_result_t result;
    uint8_t *iq = NULL;
    uint8_t *power_bytes = NULL;
    uint64_t *shifted_power = NULL;
    uint64_t sample_rate;
    int64_t center_frequency;
    uint64_t lower;
    uint64_t upper;
    unsigned int frame;
    int exit_code = EXIT_FAILURE;

    if (argc != 14 && argc != 38) {
        fprintf(stderr,
                "Kullanım: %s ORNEKLEME_HZ MERKEZ_HZ ALT_BIN UST_BIN "
                "IQ0 GUC0 IQ1 GUC1 IQ2 GUC2 IQ3 GUC3 SONUC_JSON\n",
                argv[0]);
        return EXIT_FAILURE;
    }
    if (parse_u64(argv[1], &sample_rate) != 0 ||
        parse_i64(argv[2], &center_frequency) != 0 ||
        parse_u64(argv[3], &lower) != 0 || parse_u64(argv[4], &upper) != 0 ||
        lower > UINT16_MAX || upper > UINT16_MAX) {
        fputs("Ölçüm üstverisi geçersiz.\n", stderr);
        return EXIT_FAILURE;
    }
    iq = malloc(P0_PARAMETER_FFT_SIZE * 2U);
    power_bytes = malloc(P0_PARAMETER_POWER_BYTES);
    shifted_power = malloc(P0_PARAMETER_FFT_SIZE * sizeof(*shifted_power));
    if (iq == NULL || power_bytes == NULL || shifted_power == NULL ||
        p0_parameter_runtime_init(&runtime) != 0) {
        fputs("Ölçüm belleği ayrılamadı.\n", stderr);
        goto done;
    }
    for (frame = 0U; frame < (unsigned int)(argc - 6) / 2U; ++frame) {
        const char *iq_path = argv[5 + frame * 2U];
        const char *power_path = argv[6 + frame * 2U];
        unsigned int natural;

        if (read_exact(iq_path, iq, P0_PARAMETER_FFT_SIZE * 2U) != 0 ||
            read_exact(power_path, power_bytes, P0_PARAMETER_POWER_BYTES) != 0) {
            fprintf(stderr, "Kare %u okunamadı: %s\n", frame, strerror(errno));
            goto release;
        }
        for (natural = 0U; natural < P0_PARAMETER_FFT_SIZE; ++natural)
            shifted_power[natural ^ (P0_PARAMETER_FFT_SIZE / 2U)] =
                load_le64(power_bytes + natural * 8U);
        if (p0_parameter_runtime_observe(
                &runtime, frame == 0U ? (argc == 38 ? (getenv("P0_PARAMETER_RECOVERY") != NULL ? 4 : 2) : 1) : 0, 1U, 1U, frame, sample_rate,
                center_frequency, (uint16_t)lower, (uint16_t)upper, 1,
                iq, P0_PARAMETER_FFT_SIZE * 2U, shifted_power,
                P0_PARAMETER_FFT_SIZE, &result) != 0) {
            fprintf(stderr, "Kare %u ölçülemedi: %s\n", frame, strerror(errno));
            goto release;
        }
    }
    if (write_result(argv[argc - 1], &result) != 0) {
        fprintf(stderr, "Sonuç yazılamadı: %s\n", strerror(errno));
        goto release;
    }
    puts("P0_PARAMETER_RESULT=PASS");
    exit_code = EXIT_SUCCESS;

release:
    p0_parameter_runtime_release(&runtime);
done:
    free(shifted_power);
    free(power_bytes);
    free(iq);
    return exit_code;
}
