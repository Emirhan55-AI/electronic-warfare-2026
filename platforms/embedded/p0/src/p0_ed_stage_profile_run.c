#define _GNU_SOURCE

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "p0_dma_runtime.h"
#include "p0_candidate_packet.h"
#include "p0_ed_pipeline.h"
#include "p0_multiscale_detector.h"
#include "p0_pl_os_cfar.h"

#define P0_PROFILE_MAX_FRAMES 100000U
#define P0_PROFILE_EXPECTED_DMA_FLAGS 7U
#define P0_PROFILE_FRAME_BINS 4096U

typedef struct {
    double minimum;
    double p50;
    double p95;
    double p99;
    double maximum;
    double mean;
} timing_summary_t;

typedef struct {
    uint64_t dma_failures;
    uint64_t pipeline_failures;
    uint64_t dma_flag_failures;
    uint64_t dropped_candidates;
    uint64_t probe_failures;
} failure_counts_t;

typedef struct {
    p0_ed_pipeline_t pipeline;
    int pipeline_ready;
} algorithm_probe_t;

static int parse_u64(const char *text, uint64_t minimum, uint64_t maximum,
                     uint64_t *value)
{
    char *end = NULL;
    unsigned long long parsed;

    errno = 0;
    parsed = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' ||
        parsed < minimum || parsed > maximum)
        return -1;
    *value = (uint64_t)parsed;
    return 0;
}

static int read_exact_frame(const char *path, uint8_t *buffer)
{
    FILE *file = fopen(path, "rb");
    int extra;

    if (file == NULL)
        return -1;
    if (fread(buffer, 1U, P0_DMA_INPUT_BYTES, file) != P0_DMA_INPUT_BYTES) {
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

static double milliseconds_between(const struct timespec *start,
                                   const struct timespec *end)
{
    return (double)(end->tv_sec - start->tv_sec) * 1000.0 +
           (double)(end->tv_nsec - start->tv_nsec) / 1000000.0;
}

static int compare_double(const void *left, const void *right)
{
    double first = *(const double *)left;
    double second = *(const double *)right;

    return first < second ? -1 : first > second ? 1 : 0;
}

static double percentile(const double *sorted, size_t count, double probability)
{
    size_t rank = (size_t)ceil(probability * (double)count);

    if (rank == 0U)
        rank = 1U;
    if (rank > count)
        rank = count;
    return sorted[rank - 1U];
}

static timing_summary_t summarize(double *samples, size_t count)
{
    timing_summary_t summary = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    size_t index;

    if (count == 0U)
        return summary;
    for (index = 0U; index < count; ++index)
        summary.mean += samples[index];
    summary.mean /= (double)count;
    qsort(samples, count, sizeof(*samples), compare_double);
    summary.minimum = samples[0U];
    summary.p50 = percentile(samples, count, 0.50);
    summary.p95 = percentile(samples, count, 0.95);
    summary.p99 = percentile(samples, count, 0.99);
    summary.maximum = samples[count - 1U];
    return summary;
}

static unsigned int dma_flags(const struct p0_dma_status *status)
{
    return (status->mm2s_completed != 0U ? 1U : 0U) |
           (status->s2mm_completed != 0U ? 2U : 0U) |
           (status->output_valid != 0U ? 4U : 0U);
}

static int execute_frame(p0_dma_runtime_t *dma, p0_ed_pipeline_t *pipeline,
                         uint32_t frame_id, int reset_requested,
                         const uint8_t *iq, uint8_t *power,
                         double *dma_ms, double *pipeline_ms, double *combined_ms,
                         failure_counts_t *failures)
{
    struct p0_dma_status status;
    phase06j_frame_result_v1 result;
    struct timespec started;
    struct timespec dma_finished;
    struct timespec pipeline_finished;
    size_t candidate_count = 0U;

    memset(&status, 0, sizeof(status));
    memset(&result, 0, sizeof(result));
    if (clock_gettime(CLOCK_MONOTONIC, &started) != 0)
        return -1;
    if (p0_dma_runtime_run(dma, iq, P0_DMA_INPUT_BYTES, power,
                           P0_DMA_OUTPUT_BYTES, &status) != 0) {
        failures->dma_failures += 1U;
        return -1;
    }
    if (clock_gettime(CLOCK_MONOTONIC, &dma_finished) != 0)
        return -1;
    if (dma_flags(&status) != P0_PROFILE_EXPECTED_DMA_FLAGS) {
        failures->dma_flag_failures += 1U;
        return -1;
    }
    if (p0_ed_pipeline_process(pipeline, frame_id, reset_requested,
                               power, P0_DMA_OUTPUT_BYTES, &result,
                               &candidate_count) != 0) {
        failures->pipeline_failures += 1U;
        return -1;
    }
    if (clock_gettime(CLOCK_MONOTONIC, &pipeline_finished) != 0)
        return -1;
    failures->dropped_candidates += result.dropped_candidates;
    *dma_ms = milliseconds_between(&started, &dma_finished);
    *pipeline_ms = milliseconds_between(&dma_finished, &pipeline_finished);
    *combined_ms = milliseconds_between(&started, &pipeline_finished);
    return 0;
}

static int profile_algorithm_stages(
    const uint8_t *natural_power,
    uint32_t frame_id,
    int reset_requested,
    algorithm_probe_t *probe,
    double *decode_ms,
    double *grouping_ms,
    double *detection_ms,
    double *packet_ms,
    double *temporal_ms)
{
    struct timespec started;
    struct timespec decode_finished;
    struct timespec grouping_finished;
    struct timespec detection_finished;
    struct timespec packet_finished;
    struct timespec temporal_finished;
    phase06j_frame_result_v1 result;
    size_t candidate_count = 0U;
    size_t recovery_count = 0U;
    int pl_decisions_present = 0;
    int code;

    memset(&result, 0, sizeof(result));
    memcpy(probe->pipeline.temporal_backup, probe->pipeline.temporal_state,
           phase06j_state_bytes());
    if (reset_requested && p0_ed_pipeline_reset(&probe->pipeline) != 0)
        goto rollback;
    if (clock_gettime(CLOCK_MONOTONIC, &started) != 0)
        goto rollback;
    code = p0_pl_os_cfar_decode(
        natural_power, P0_DMA_OUTPUT_BYTES, probe->pipeline.raw_power,
        probe->pipeline.power, probe->pipeline.detections,
        &pl_decisions_present);
    if (code != P0_PL_OS_CFAR_OK || !pl_decisions_present)
        goto rollback;
    if (clock_gettime(CLOCK_MONOTONIC, &decode_finished) != 0)
        goto rollback;
    code = p0_os_cfar_group_detections_trusted(
        probe->pipeline.power, P0_PROFILE_FRAME_BINS, &probe->pipeline.config,
        probe->pipeline.detections, probe->pipeline.noise,
        probe->pipeline.threshold, probe->pipeline.candidates,
        PHASE06I_MAX_CANDIDATES, &candidate_count);
    if (code != P0_OS_CFAR_OK ||
        clock_gettime(CLOCK_MONOTONIC, &grouping_finished) != 0)
        goto rollback;
    code = p0_multiscale_process_pl_trusted(
        probe->pipeline.power, P0_PROFILE_FRAME_BINS, &probe->pipeline.config,
        probe->pipeline.detections, probe->pipeline.noise,
        probe->pipeline.threshold, probe->pipeline.candidates,
        PHASE06I_MAX_CANDIDATES, &candidate_count, &recovery_count);
    if (code != P0_MULTISCALE_OK ||
        clock_gettime(CLOCK_MONOTONIC, &detection_finished) != 0)
        goto rollback;
    code = p0_candidate_records_encode(
        probe->pipeline.raw_power, P0_PROFILE_FRAME_BINS,
        &probe->pipeline.config, probe->pipeline.candidates, candidate_count,
        probe->pipeline.candidate_records, PHASE06I_MAX_CANDIDATES);
    if (code != P0_CANDIDATE_PACKET_OK ||
        clock_gettime(CLOCK_MONOTONIC, &packet_finished) != 0)
        goto rollback;
    code = phase06j_process_candidates(
        probe->pipeline.temporal_state, phase06j_state_bytes(),
        frame_id, probe->pipeline.candidate_records,
        (uint16_t)candidate_count, &result);
    if (code != PHASE06J_OK ||
        clock_gettime(CLOCK_MONOTONIC, &temporal_finished) != 0)
        goto rollback;
    *decode_ms = milliseconds_between(&started, &decode_finished);
    *grouping_ms = milliseconds_between(&decode_finished, &grouping_finished);
    *detection_ms = milliseconds_between(&grouping_finished, &detection_finished);
    *packet_ms = milliseconds_between(&detection_finished, &packet_finished);
    *temporal_ms = milliseconds_between(&packet_finished, &temporal_finished);
    return 0;

rollback:
    memcpy(probe->pipeline.temporal_state, probe->pipeline.temporal_backup,
           phase06j_state_bytes());
    return -1;
}

static void print_summary(const char *name, const timing_summary_t *summary)
{
    printf(
        "    \"%s\": {\"minimum\": %.6f, \"p50\": %.6f, "
        "\"p95\": %.6f, \"p99\": %.6f, \"maximum\": %.6f, "
        "\"mean\": %.6f}",
        name, summary->minimum, summary->p50, summary->p95, summary->p99,
        summary->maximum, summary->mean);
}

int main(int argc, char **argv)
{
    p0_dma_runtime_t dma = {-1};
    p0_ed_pipeline_t pipeline;
    failure_counts_t failures = {0U, 0U, 0U, 0U, 0U};
    algorithm_probe_t probe;
    timing_summary_t dma_summary;
    timing_summary_t pipeline_summary;
    timing_summary_t combined_summary;
    timing_summary_t decode_summary;
    timing_summary_t grouping_summary;
    timing_summary_t detection_summary;
    timing_summary_t packet_summary;
    timing_summary_t temporal_summary;
    uint8_t *iq = NULL;
    uint8_t *power = NULL;
    double *dma_samples = NULL;
    double *pipeline_samples = NULL;
    double *combined_samples = NULL;
    double *decode_samples = NULL;
    double *grouping_samples = NULL;
    double *detection_samples = NULL;
    double *packet_samples = NULL;
    double *temporal_samples = NULL;
    uint64_t measured_frames;
    uint64_t warmup_frames;
    uint64_t index;
    uint64_t completed = 0U;
    int pipeline_ready = 0;
    int exit_code = EXIT_FAILURE;

    memset(&pipeline, 0, sizeof(pipeline));
    memset(&probe, 0, sizeof(probe));
    if (argc != 4 ||
        parse_u64(argv[1], 1U, P0_PROFILE_MAX_FRAMES, &measured_frames) != 0 ||
        parse_u64(argv[2], 0U, P0_PROFILE_MAX_FRAMES, &warmup_frames) != 0) {
        fprintf(stderr,
                "Kullanım: %s ÖLÇÜM_KARESİ ISINMA_KARESİ GİRİŞ_CI8\n",
                argv[0]);
        return EXIT_FAILURE;
    }
    iq = malloc(P0_DMA_INPUT_BYTES);
    power = malloc(P0_DMA_OUTPUT_BYTES);
    dma_samples = calloc((size_t)measured_frames, sizeof(*dma_samples));
    pipeline_samples = calloc((size_t)measured_frames, sizeof(*pipeline_samples));
    combined_samples = calloc((size_t)measured_frames, sizeof(*combined_samples));
    decode_samples = calloc((size_t)measured_frames, sizeof(*decode_samples));
    grouping_samples = calloc((size_t)measured_frames, sizeof(*grouping_samples));
    detection_samples = calloc((size_t)measured_frames, sizeof(*detection_samples));
    packet_samples = calloc((size_t)measured_frames, sizeof(*packet_samples));
    temporal_samples = calloc((size_t)measured_frames, sizeof(*temporal_samples));
    if (iq == NULL || power == NULL || dma_samples == NULL ||
        pipeline_samples == NULL || combined_samples == NULL ||
        decode_samples == NULL || grouping_samples == NULL || detection_samples == NULL ||
        packet_samples == NULL || temporal_samples == NULL) {
        fputs("Profil belleği ayrılamadı.\n", stderr);
        goto done;
    }
    if (read_exact_frame(argv[3], iq) != 0) {
        fprintf(stderr, "I/Q profil karesi okunamadı: %s\n", strerror(errno));
        goto done;
    }
    if (p0_dma_runtime_open(&dma, "/dev/p0-dma") != 0) {
        fprintf(stderr, "/dev/p0-dma açılamadı: %s\n", strerror(errno));
        goto done;
    }
    if (p0_ed_pipeline_init(&pipeline) != 0) {
        fprintf(stderr, "ED boruhattı başlatılamadı: %s\n", strerror(errno));
        goto done;
    }
    pipeline_ready = 1;
    if (p0_ed_pipeline_init(&probe.pipeline) != 0) {
        fprintf(stderr, "Profil ED boruhattı başlatılamadı: %s\n", strerror(errno));
        goto done;
    }
    probe.pipeline_ready = 1;
    for (index = 0U; index < warmup_frames; ++index) {
        double ignored_dma = 0.0;
        double ignored_pipeline = 0.0;
        double ignored_combined = 0.0;

        if (execute_frame(&dma, &pipeline, (uint32_t)index, index == 0U,
                          iq, power, &ignored_dma, &ignored_pipeline,
                          &ignored_combined, &failures) != 0)
            goto report;
    }
    for (index = 0U; index < measured_frames; ++index) {
        if (execute_frame(&dma, &pipeline, (uint32_t)index, index == 0U,
                          iq, power, &dma_samples[index],
                          &pipeline_samples[index], &combined_samples[index],
                          &failures) != 0)
            break;
        completed += 1U;
    }
    if (completed == measured_frames) {
        for (index = 0U; index < measured_frames; ++index) {
            if (profile_algorithm_stages(
                    power, (uint32_t)index, index == 0U, &probe,
                    &decode_samples[index], &grouping_samples[index],
                    &detection_samples[index],
                    &packet_samples[index], &temporal_samples[index]) != 0) {
                failures.probe_failures += 1U;
                break;
            }
        }
    }

report:
    dma_summary = summarize(dma_samples, (size_t)completed);
    pipeline_summary = summarize(pipeline_samples, (size_t)completed);
    combined_summary = summarize(combined_samples, (size_t)completed);
    decode_summary = summarize(decode_samples,
                               failures.probe_failures == 0U ? (size_t)completed : 0U);
    grouping_summary = summarize(grouping_samples,
                                 failures.probe_failures == 0U ? (size_t)completed : 0U);
    detection_summary = summarize(detection_samples,
                                  failures.probe_failures == 0U ? (size_t)completed : 0U);
    packet_summary = summarize(packet_samples,
                               failures.probe_failures == 0U ? (size_t)completed : 0U);
    temporal_summary = summarize(temporal_samples,
                                 failures.probe_failures == 0U ? (size_t)completed : 0U);
    printf(
        "{\n"
        "  \"schema_version\": 1,\n"
        "  \"status\": \"%s\",\n"
        "  \"scope\": \"fiziksel ZedBoard PL-DMA-ARM aşama karakterizasyonu\",\n"
        "  \"profile\": {\"warmup_frames\": %" PRIu64
        ", \"measured_frames\": %" PRIu64 ", \"frame_samples\": 4096},\n"
        "  \"completion\": {\"completed_frames\": %" PRIu64
        ", \"dma_failures\": %" PRIu64
        ", \"pipeline_failures\": %" PRIu64
        ", \"dma_flag_failures\": %" PRIu64
        ", \"dropped_candidates\": %" PRIu64
        ", \"probe_failures\": %" PRIu64 "},\n"
        "  \"timing_milliseconds\": {\n",
        completed == measured_frames && failures.dma_failures == 0U &&
                failures.pipeline_failures == 0U &&
                failures.dma_flag_failures == 0U &&
                failures.dropped_candidates == 0U &&
                failures.probe_failures == 0U
            ? "passed"
            : "failed",
        warmup_frames, measured_frames, completed, failures.dma_failures,
        failures.pipeline_failures, failures.dma_flag_failures,
        failures.dropped_candidates, failures.probe_failures);
    print_summary("dma", &dma_summary);
    puts(",");
    print_summary("arm_pipeline", &pipeline_summary);
    puts(",");
    print_summary("combined", &combined_summary);
    printf(
        "\n  },\n"
        "  \"algorithm_probe_milliseconds\": {\n");
    print_summary("pl_frame_decode", &decode_summary);
    puts(",");
    print_summary("os_candidate_grouping", &grouping_summary);
    puts(",");
    print_summary("multiscale_detection_total", &detection_summary);
    puts(",");
    print_summary("candidate_record_encode", &packet_summary);
    puts(",");
    print_summary("temporal_association", &temporal_summary);
    printf(
        "\n  },\n"
        "  \"expected_dma_status_flags\": 7,\n"
        "  \"claim_boundary\": \"Aynı süreçte aşama süreleri; servis soketi, "
        "canlı RF, Ethernet, kalibrasyon veya RF doğruluğu değildir.\"\n"
        "}\n");
    if (completed == measured_frames && failures.dma_failures == 0U &&
        failures.pipeline_failures == 0U && failures.dma_flag_failures == 0U &&
        failures.dropped_candidates == 0U && failures.probe_failures == 0U)
        exit_code = EXIT_SUCCESS;

done:
    if (probe.pipeline_ready)
        p0_ed_pipeline_release(&probe.pipeline);
    if (pipeline_ready)
        p0_ed_pipeline_release(&pipeline);
    p0_dma_runtime_close(&dma);
    free(temporal_samples);
    free(packet_samples);
    free(detection_samples);
    free(grouping_samples);
    free(decode_samples);
    free(combined_samples);
    free(pipeline_samples);
    free(dma_samples);
    free(power);
    free(iq);
    return exit_code;
}
