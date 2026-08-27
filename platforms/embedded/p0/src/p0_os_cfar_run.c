#if defined(_MSC_VER)
#define _CRT_SECURE_NO_WARNINGS
#endif

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "p0_os_cfar.h"

#define P0_FRAME_BINS 4096U
#define P0_POWER_BYTES_PER_BIN 8U
#define P0_POWER_FRAME_BYTES (P0_FRAME_BINS * P0_POWER_BYTES_PER_BIN)
#define P0_POWER_FRACTION_BITS 30U
#define P0_MAX_CANDIDATES P0_FRAME_BINS

static uint64_t load_u64_le(const uint8_t *source)
{
    uint64_t value = 0U;
    unsigned int index;

    for (index = 0U; index < P0_POWER_BYTES_PER_BIN; ++index)
        value |= (uint64_t)source[index] << (index * 8U);
    return value;
}

static int read_power_frame(const char *path, double *shifted_power)
{
    uint8_t *raw = NULL;
    FILE *file = NULL;
    size_t natural_bin;
    int result = -1;

    raw = malloc(P0_POWER_FRAME_BYTES);
    if (raw == NULL) {
        errno = ENOMEM;
        return -1;
    }
    file = fopen(path, "rb");
    if (file == NULL)
        goto done;
    if (fread(raw, 1U, P0_POWER_FRAME_BYTES, file) != P0_POWER_FRAME_BYTES) {
        errno = EINVAL;
        goto done;
    }
    if (fgetc(file) != EOF) {
        errno = EFBIG;
        goto done;
    }
    for (natural_bin = 0U; natural_bin < P0_FRAME_BINS; ++natural_bin) {
        size_t shifted_bin = natural_bin ^ (P0_FRAME_BINS / 2U);
        uint64_t raw_power = load_u64_le(raw + natural_bin * P0_POWER_BYTES_PER_BIN);

        shifted_power[shifted_bin] = (double)raw_power / (double)(1ULL << P0_POWER_FRACTION_BITS);
    }
    result = 0;

done:
    if (file != NULL)
        fclose(file);
    free(raw);
    return result;
}

static int write_result(const char *path,
                        const p0_os_cfar_config_t *config,
                        const p0_candidate_region_t *candidates,
                        size_t candidate_count)
{
    FILE *file;
    size_t index;

    file = fopen(path, "wb");
    if (file == NULL)
        return -1;
    fprintf(file,
            "{\n"
            "  \"schema_version\": 1,\n"
            "  \"status\": \"passed\",\n"
            "  \"input_layout\": \"4096 little-endian UQ28.30 bins in natural FFT order\",\n"
            "  \"output_bin_order\": \"fftshift\",\n"
            "  \"profile\": {\n"
            "    \"reference_cells_per_side\": %" PRIu32 ",\n"
            "    \"guard_cells_per_side\": %" PRIu32 ",\n"
            "    \"order_statistic_rank\": %" PRIu32 ",\n"
            "    \"threshold_coefficient\": %.17g,\n"
            "    \"maximum_gap_bins\": %" PRIu32 "\n"
            "  },\n"
            "  \"candidate_count\": %zu,\n"
            "  \"candidates\": [\n",
            config->reference_cells_per_side,
            config->guard_cells_per_side,
            config->order_statistic_rank,
            config->threshold_coefficient,
            config->maximum_gap_bins,
            candidate_count);
    for (index = 0U; index < candidate_count; ++index) {
        const p0_candidate_region_t *candidate = &candidates[index];

        fprintf(file,
                "    {\"start_bin\": %" PRIu32 ", \"end_bin\": %" PRIu32
                ", \"peak_bin\": %" PRIu32 ", \"peak_power\": %.17g"
                ", \"noise_power_per_bin\": %.17g, \"threshold_power\": %.17g}%s\n",
                candidate->start_bin,
                candidate->end_bin,
                candidate->peak_bin,
                candidate->peak_power,
                candidate->noise_power_per_bin,
                candidate->threshold_power,
                index + 1U == candidate_count ? "" : ",");
    }
    fputs("  ]\n}\n", file);
    if (fclose(file) != 0)
        return -1;
    return 0;
}

int main(int argc, char **argv)
{
    p0_os_cfar_config_t config;
    p0_candidate_region_t *candidates = NULL;
    double *power = NULL;
    double *noise = NULL;
    double *threshold = NULL;
    uint8_t *detections = NULL;
    size_t candidate_count = 0U;
    int detector_result;
    int result = EXIT_FAILURE;

    if (argc != 3) {
        fprintf(stderr, "Kullanım: %s FPGA_GUC_U64 SONUC_JSON\n", argv[0]);
        return EXIT_FAILURE;
    }
    power = calloc(P0_FRAME_BINS, sizeof(*power));
    noise = calloc(P0_FRAME_BINS, sizeof(*noise));
    threshold = calloc(P0_FRAME_BINS, sizeof(*threshold));
    detections = calloc(P0_FRAME_BINS, sizeof(*detections));
    candidates = calloc(P0_MAX_CANDIDATES, sizeof(*candidates));
    if (power == NULL || noise == NULL || threshold == NULL ||
        detections == NULL || candidates == NULL) {
        fprintf(stderr, "Bellek ayrılamadı.\n");
        goto done;
    }
    if (read_power_frame(argv[1], power) != 0) {
        fprintf(stderr, "FPGA güç çerçevesi okunamadı: %s\n", strerror(errno));
        goto done;
    }
    if (p0_os_cfar_canonical_config(&config) != P0_OS_CFAR_OK) {
        fputs("Kanonik OS-CFAR profili oluşturulamadı.\n", stderr);
        goto done;
    }
    detector_result = p0_os_cfar_process(
        power, P0_FRAME_BINS, &config, detections, noise, threshold,
        candidates, P0_MAX_CANDIDATES, &candidate_count);
    if (detector_result != P0_OS_CFAR_OK) {
        fprintf(stderr, "OS-CFAR çalıştırılamadı: %d\n", detector_result);
        goto done;
    }
    if (write_result(argv[2], &config, candidates, candidate_count) != 0) {
        fprintf(stderr, "Sonuç yazılamadı: %s\n", strerror(errno));
        goto done;
    }
    printf("P0_OS_CFAR_RESULT=PASS\nCANDIDATE_COUNT=%zu\n", candidate_count);
    result = EXIT_SUCCESS;

done:
    free(candidates);
    free(detections);
    free(threshold);
    free(noise);
    free(power);
    return result;
}
