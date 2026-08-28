#if defined(_MSC_VER)
#define _CRT_SECURE_NO_WARNINGS
#endif

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "p0_candidate_packet.h"
#include "p0_multiscale_detector.h"
#include "p0_os_cfar.h"
#include "phase06i_transport_abi.h"
#include "phase06j_temporal.h"

#define P0_FRAME_BINS PHASE06I_FFT_SIZE
#define P0_POWER_BYTES_PER_BIN 8U
#define P0_POWER_FRAME_BYTES (P0_FRAME_BINS * P0_POWER_BYTES_PER_BIN)
#define P0_POWER_FRACTION_BITS 30U
#define P0_MAX_CANDIDATES PHASE06I_MAX_CANDIDATES

typedef struct {
    double *power;
    uint64_t *raw_power;
    double *noise;
    double *threshold;
    uint8_t *detections;
    p0_candidate_region_t *candidates;
    uint8_t *packet;
    void *temporal_state;
} runtime_memory_t;

static uint64_t load_u64_le(const uint8_t *source)
{
    uint64_t value = 0U;
    unsigned int index;

    for (index = 0U; index < P0_POWER_BYTES_PER_BIN; ++index)
        value |= (uint64_t)source[index] << (index * 8U);
    return value;
}

static int read_power_frame(const char *path, double *shifted_power, uint64_t *shifted_raw)
{
    uint8_t *bytes = NULL;
    FILE *file = NULL;
    size_t natural_bin;
    int result = -1;

    bytes = malloc(P0_POWER_FRAME_BYTES);
    if (bytes == NULL) {
        errno = ENOMEM;
        return -1;
    }
    file = fopen(path, "rb");
    if (file == NULL)
        goto done;
    if (fread(bytes, 1U, P0_POWER_FRAME_BYTES, file) != P0_POWER_FRAME_BYTES) {
        errno = EINVAL;
        goto done;
    }
    if (fgetc(file) != EOF) {
        errno = EFBIG;
        goto done;
    }
    for (natural_bin = 0U; natural_bin < P0_FRAME_BINS; ++natural_bin) {
        size_t shifted_bin = natural_bin ^ (P0_FRAME_BINS / 2U);
        uint64_t raw = load_u64_le(bytes + natural_bin * P0_POWER_BYTES_PER_BIN);

        if (raw >= (UINT64_C(1) << 58)) {
            errno = ERANGE;
            goto done;
        }
        shifted_raw[shifted_bin] = raw;
        shifted_power[shifted_bin] = (double)raw / (double)(UINT64_C(1) << P0_POWER_FRACTION_BITS);
    }
    result = 0;

done:
    if (file != NULL)
        fclose(file);
    free(bytes);
    return result;
}

static int allocate_runtime(runtime_memory_t *memory)
{
    memset(memory, 0, sizeof(*memory));
    memory->power = calloc(P0_FRAME_BINS, sizeof(*memory->power));
    memory->raw_power = calloc(P0_FRAME_BINS, sizeof(*memory->raw_power));
    memory->noise = calloc(P0_FRAME_BINS, sizeof(*memory->noise));
    memory->threshold = calloc(P0_FRAME_BINS, sizeof(*memory->threshold));
    memory->detections = calloc(P0_FRAME_BINS, sizeof(*memory->detections));
    memory->candidates = calloc(P0_MAX_CANDIDATES, sizeof(*memory->candidates));
    memory->packet = malloc(PHASE06I_MAX_FRAME_BYTES);
    memory->temporal_state = calloc(1U, phase06j_state_bytes());
    return memory->power != NULL && memory->raw_power != NULL && memory->noise != NULL &&
           memory->threshold != NULL && memory->detections != NULL && memory->candidates != NULL &&
           memory->packet != NULL && memory->temporal_state != NULL ? 0 : -1;
}

static void release_runtime(runtime_memory_t *memory)
{
    free(memory->temporal_state);
    free(memory->packet);
    free(memory->candidates);
    free(memory->detections);
    free(memory->threshold);
    free(memory->noise);
    free(memory->raw_power);
    free(memory->power);
}

static const char *state_name(uint8_t state)
{
    if (state == PHASE06J_EVENT_TENTATIVE)
        return "tentative";
    if (state == PHASE06J_EVENT_CONFIRMED)
        return "confirmed";
    return "ended";
}

static void write_event(FILE *file, const phase06j_event_v1 *event)
{
    fprintf(file,
            "{\"event_id\":%" PRIu64 ",\"state\":\"%s\",\"first_frame_id\":%" PRIu32
            ",\"last_seen_frame_id\":%" PRIu32 ",\"seen_count\":%" PRIu64
            ",\"observed_this_frame\":%s,\"start_bin\":%" PRIu16
            ",\"end_bin\":%" PRIu16 ",\"peak_bin\":%" PRIu16
            ",\"peak_power_uq28_30\":%" PRIu64 ",\"noise_power_uq28_30\":%" PRIu64
            ",\"threshold_power_uq32_30\":%" PRIu64 "}",
            event->event_id, state_name(event->state), event->first_frame_id,
            event->last_seen_frame_id, event->seen_count,
            event->observed_this_frame != 0U ? "true" : "false",
            event->candidate.start_shifted_bin, event->candidate.end_shifted_bin,
            event->candidate.peak_shifted_bin, event->candidate.peak_power_uq28_30,
            event->candidate.regional_noise_uq28_30, event->candidate.threshold_uq32_30);
}

static void write_frame_result(FILE *file, const phase06j_frame_result_v1 *frame,
                               size_t raw_candidate_count)
{
    uint16_t index;

    fprintf(file,
            "    {\"frame_id\":%" PRIu32 ",\"raw_candidate_count\":%zu,"
            "\"active_count\":%" PRIu16 ",\"ended_count\":%" PRIu16
            ",\"dropped_candidates\":%" PRIu16 ",\"reset_applied\":%s,\"active\":[",
            frame->frame_id, raw_candidate_count, frame->active_count, frame->ended_count,
            frame->dropped_candidates, frame->reset_applied != 0U ? "true" : "false");
    for (index = 0U; index < frame->active_count; ++index) {
        if (index != 0U)
            fputc(',', file);
        write_event(file, &frame->active[index]);
    }
    fputs("],\"ended\":[", file);
    for (index = 0U; index < frame->ended_count; ++index) {
        if (index != 0U)
            fputc(',', file);
        write_event(file, &frame->ended[index]);
    }
    fputs("]}", file);
}

int main(int argc, char **argv)
{
    runtime_memory_t memory;
    p0_os_cfar_config_t config;
    FILE *output = NULL;
    char *output_temporary = NULL;
    uint32_t frame_id;
    int result = EXIT_FAILURE;

    if (argc < 3) {
        fprintf(stderr, "Kullanım: %s SONUC_JSON FPGA_GUC_U64|- [FPGA_GUC_U64|- ...]\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (allocate_runtime(&memory) != 0) {
        fputs("Çalışma belleği ayrılamadı.\n", stderr);
        return EXIT_FAILURE;
    }
    if (p0_os_cfar_canonical_config(&config) != P0_OS_CFAR_OK ||
        phase06j_state_init(memory.temporal_state, phase06j_state_bytes()) != PHASE06J_OK) {
        fputs("ED çalışma profili başlatılamadı.\n", stderr);
        goto done;
    }
    output_temporary = malloc(strlen(argv[1]) + 5U);
    if (output_temporary == NULL) {
        fputs("Sonuç yolu için bellek ayrılamadı.\n", stderr);
        goto done;
    }
    sprintf(output_temporary, "%s.tmp", argv[1]);
    remove(output_temporary);
    output = fopen(output_temporary, "wb");
    if (output == NULL) {
        fprintf(stderr, "Sonuç dosyası açılamadı: %s\n", strerror(errno));
        goto done;
    }
    fputs("{\n  \"schema_version\":1,\n  \"status\":\"passed\",\n"
          "  \"detector\":\"p0_multiscale_os_cfar_integrated_energy\",\n  \"temporal_rule\":\"2_of_3\",\n"
          "  \"frames\":[\n", output);
    for (frame_id = 0U; frame_id < (uint32_t)(argc - 2); ++frame_id) {
        const char *input = argv[frame_id + 2U];
        size_t candidate_count = 0U;
        size_t recovery_count = 0U;
        size_t packet_bytes = 0U;
        phase06j_frame_result_v1 frame_result;
        int code;

        if (strcmp(input, "-") == 0) {
            memset(memory.power, 0, P0_FRAME_BINS * sizeof(*memory.power));
            memset(memory.raw_power, 0, P0_FRAME_BINS * sizeof(*memory.raw_power));
        } else {
            if (read_power_frame(input, memory.power, memory.raw_power) != 0) {
                fprintf(stderr, "FPGA güç çerçevesi okunamadı (%s): %s\n", input, strerror(errno));
                goto done;
            }
            code = p0_multiscale_process(memory.power, P0_FRAME_BINS, &config,
                                         memory.detections, memory.noise, memory.threshold,
                                         memory.candidates, P0_MAX_CANDIDATES,
                                         &candidate_count, &recovery_count);
            if (code != P0_MULTISCALE_OK) {
                fprintf(stderr, "Çok ölçekli tespit çalıştırılamadı: %d\n", code);
                goto done;
            }
        }
        code = p0_candidate_packet_encode(frame_id, memory.raw_power, P0_FRAME_BINS, &config,
                                          memory.candidates, candidate_count, memory.packet,
                                          PHASE06I_MAX_FRAME_BYTES, &packet_bytes);
        if (code != P0_CANDIDATE_PACKET_OK) {
            fprintf(stderr, "Aday paketi oluşturulamadı: %d\n", code);
            goto done;
        }
        code = phase06j_process_packet(memory.temporal_state, phase06j_state_bytes(),
                                       memory.packet, packet_bytes, &frame_result);
        if (code != PHASE06J_OK) {
            fprintf(stderr, "Zamansal doğrulama çalıştırılamadı: %s\n", phase06j_error_string(code));
            goto done;
        }
        if (frame_id != 0U)
            fputs(",\n", output);
        write_frame_result(output, &frame_result, candidate_count);
    }
    fputs("\n  ]\n}\n", output);
    if (fclose(output) != 0) {
        output = NULL;
        fputs("Sonuç dosyası kapatılamadı.\n", stderr);
        goto done;
    }
    output = NULL;
    remove(argv[1]);
    if (rename(output_temporary, argv[1]) != 0) {
        fprintf(stderr, "Sonuç dosyası yayınlanamadı: %s\n", strerror(errno));
        goto done;
    }
    printf("P0_ED_TEMPORAL_RESULT=PASS\nFRAME_COUNT=%d\n", argc - 2);
    result = EXIT_SUCCESS;

done:
    if (output != NULL)
        fclose(output);
    if (result != EXIT_SUCCESS && output_temporary != NULL)
        remove(output_temporary);
    free(output_temporary);
    release_runtime(&memory);
    return result;
}
