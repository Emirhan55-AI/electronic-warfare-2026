#define _GNU_SOURCE

#include "p0_dma_runtime.h"
#include "p0_st06_power_runtime.h"

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

enum {
    P0_ST06_QUEUE_DEPTH = 4,
    P0_ST06_PRODUCER_CPU = 0,
    P0_ST06_CONSUMER_CPU = 1,
    P0_ST06_EXPECTED_OUTPUT_BYTES = 4096 * 8
};

typedef struct {
    uint8_t *packet;
    size_t packet_bytes;
    uint32_t frame_id;
    int reset_requested;
} p0_st06_slot_t;

typedef struct {
    pthread_mutex_t mutex;
    pthread_cond_t can_produce;
    pthread_cond_t can_consume;
    p0_st06_slot_t slots[P0_ST06_QUEUE_DEPTH];
    size_t head;
    size_t tail;
    size_t count;
    int producer_done;
    int failed;
    uint64_t warmup_frames;
    uint64_t measured_frames;
    uint64_t completed_frames;
    uint64_t checksum;
    double *processing_ms;
    p0_st06_power_runtime_t runtime;
} p0_st06_profile_t;

typedef struct {
    double minimum;
    double p50;
    double p95;
    double p99;
    double maximum;
    double mean;
} p0_st06_summary_t;

static double milliseconds(const struct timespec *start, const struct timespec *stop)
{
    return ((double)(stop->tv_sec - start->tv_sec) * 1000.0) +
           ((double)(stop->tv_nsec - start->tv_nsec) / 1000000.0);
}

static double seconds(const struct timespec *start, const struct timespec *stop)
{
    return ((double)(stop->tv_sec - start->tv_sec)) +
           ((double)(stop->tv_nsec - start->tv_nsec) / 1000000000.0);
}

static int compare_double(const void *left, const void *right)
{
    const double first = *(const double *)left;
    const double second = *(const double *)right;
    return (first > second) - (first < second);
}

static size_t percentile_index(size_t count, double percentile)
{
    size_t index = (size_t)ceil(percentile * (double)count);
    return index == 0U ? 0U : index - 1U;
}

static p0_st06_summary_t summarize(const double *values, size_t count)
{
    p0_st06_summary_t result = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    double *sorted;
    size_t index;

    if (count == 0U)
        return result;
    sorted = malloc(count * sizeof(*sorted));
    if (sorted == NULL)
        return result;
    memcpy(sorted, values, count * sizeof(*sorted));
    qsort(sorted, count, sizeof(*sorted), compare_double);
    for (index = 0U; index < count; ++index)
        result.mean += sorted[index];
    result.mean /= (double)count;
    result.minimum = sorted[0U];
    result.p50 = sorted[percentile_index(count, 0.50)];
    result.p95 = sorted[percentile_index(count, 0.95)];
    result.p99 = sorted[percentile_index(count, 0.99)];
    result.maximum = sorted[count - 1U];
    free(sorted);
    return result;
}

static int pin_current_thread(int cpu)
{
    cpu_set_t set;

    if (sysconf(_SC_NPROCESSORS_CONF) <= cpu)
        return 0;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    return sched_setaffinity(0, sizeof(set), &set);
}

static int read_iq(const char *path, uint8_t *iq)
{
    FILE *file = fopen(path, "rb");
    int result = -1;

    if (file != NULL && fread(iq, 1U, P0_DMA_INPUT_BYTES, file) == P0_DMA_INPUT_BYTES &&
        fgetc(file) == EOF && !ferror(file))
        result = 0;
    if (file != NULL)
        fclose(file);
    return result;
}

static int parse_u64(const char *text, uint64_t minimum, uint64_t maximum,
                     uint64_t *value)
{
    char *end = NULL;
    unsigned long long parsed;

    errno = 0;
    parsed = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || parsed < minimum ||
        parsed > maximum)
        return -1;
    *value = (uint64_t)parsed;
    return 0;
}

static void set_failed(p0_st06_profile_t *profile)
{
    profile->failed = 1;
    pthread_cond_broadcast(&profile->can_produce);
    pthread_cond_broadcast(&profile->can_consume);
}

static void *consume_frames(void *argument)
{
    p0_st06_profile_t *profile = argument;

    if (pin_current_thread(P0_ST06_CONSUMER_CPU) != 0) {
        pthread_mutex_lock(&profile->mutex);
        set_failed(profile);
        pthread_mutex_unlock(&profile->mutex);
        return NULL;
    }
    for (;;) {
        p0_st06_slot_t *slot;
        struct timespec started;
        struct timespec finished;
        p0_st05_result_t result;
        int result_valid = 0;
        int context_reset = 0;
        int code;

        pthread_mutex_lock(&profile->mutex);
        while (profile->count == 0U && !profile->producer_done && !profile->failed)
            pthread_cond_wait(&profile->can_consume, &profile->mutex);
        if (profile->failed || (profile->count == 0U && profile->producer_done)) {
            pthread_mutex_unlock(&profile->mutex);
            break;
        }
        slot = &profile->slots[profile->head];
        pthread_mutex_unlock(&profile->mutex);

        if (clock_gettime(CLOCK_MONOTONIC, &started) != 0) {
            pthread_mutex_lock(&profile->mutex);
            set_failed(profile);
            pthread_mutex_unlock(&profile->mutex);
            break;
        }
        code = p0_st06_power_runtime_process(
            &profile->runtime, slot->frame_id, slot->reset_requested,
            slot->packet, slot->packet_bytes, &result, &result_valid,
            &context_reset);
        if (clock_gettime(CLOCK_MONOTONIC, &finished) != 0 || code != 0 ||
            context_reset != slot->reset_requested) {
            pthread_mutex_lock(&profile->mutex);
            set_failed(profile);
            pthread_mutex_unlock(&profile->mutex);
            break;
        }
        if (slot->frame_id >= profile->warmup_frames) {
            size_t index = (size_t)(slot->frame_id - profile->warmup_frames);
            profile->processing_ms[index] = milliseconds(&started, &finished);
            profile->checksum += (uint64_t)result_valid +
                                 result.candidate_count * UINT64_C(17) +
                                 result.unresolved_count * UINT64_C(31);
            if (result_valid)
                profile->checksum += result.decision;
            ++profile->completed_frames;
        }

        pthread_mutex_lock(&profile->mutex);
        profile->head = (profile->head + 1U) % P0_ST06_QUEUE_DEPTH;
        --profile->count;
        pthread_cond_signal(&profile->can_produce);
        pthread_mutex_unlock(&profile->mutex);
    }
    return NULL;
}

static int enqueue_frame(p0_st06_profile_t *profile, p0_dma_runtime_t *dma,
                         const uint8_t *iq, uint32_t frame_id,
                         double *dma_ms)
{
    p0_st06_slot_t *slot;
    struct p0_dma_status dma_status;
    struct timespec started;
    struct timespec finished;
    size_t packet_bytes = 0U;

    pthread_mutex_lock(&profile->mutex);
    while (profile->count == P0_ST06_QUEUE_DEPTH && !profile->failed)
        pthread_cond_wait(&profile->can_produce, &profile->mutex);
    if (profile->failed) {
        pthread_mutex_unlock(&profile->mutex);
        return -1;
    }
    slot = &profile->slots[profile->tail];
    pthread_mutex_unlock(&profile->mutex);

    if (clock_gettime(CLOCK_MONOTONIC, &started) != 0 ||
        p0_dma_runtime_run(dma, iq, P0_DMA_INPUT_BYTES, slot->packet,
                           P0_DMA_OUTPUT_CAPACITY_BYTES, &packet_bytes,
                           &dma_status) != 0 ||
        clock_gettime(CLOCK_MONOTONIC, &finished) != 0 ||
        packet_bytes != P0_ST06_EXPECTED_OUTPUT_BYTES ||
        dma_status.mm2s_completed == 0U || dma_status.s2mm_completed == 0U ||
        dma_status.output_valid == 0U || dma_status.timed_out != 0U ||
        dma_status.dma_error != 0U)
        return -1;
    slot->packet_bytes = packet_bytes;
    slot->frame_id = frame_id;
    slot->reset_requested = frame_id == 0U;
    if (frame_id >= profile->warmup_frames)
        dma_ms[frame_id - profile->warmup_frames] = milliseconds(&started, &finished);

    pthread_mutex_lock(&profile->mutex);
    profile->tail = (profile->tail + 1U) % P0_ST06_QUEUE_DEPTH;
    ++profile->count;
    pthread_cond_signal(&profile->can_consume);
    pthread_mutex_unlock(&profile->mutex);
    return 0;
}

static int wait_until_empty(p0_st06_profile_t *profile)
{
    pthread_mutex_lock(&profile->mutex);
    while (profile->count != 0U && !profile->failed)
        pthread_cond_wait(&profile->can_produce, &profile->mutex);
    if (profile->failed) {
        pthread_mutex_unlock(&profile->mutex);
        return -1;
    }
    pthread_mutex_unlock(&profile->mutex);
    return 0;
}

static void print_summary(const char *name, const p0_st06_summary_t *summary)
{
    printf(
        "\"%s\":{\"minimum_ms\":%.9f,\"p50_ms\":%.9f,"
        "\"p95_ms\":%.9f,\"p99_ms\":%.9f,\"maximum_ms\":%.9f,"
        "\"mean_ms\":%.9f}",
        name, summary->minimum, summary->p50, summary->p95, summary->p99,
        summary->maximum, summary->mean);
}

int main(int argc, char **argv)
{
    const char *device_path;
    p0_dma_runtime_t dma = {-1};
    p0_st06_profile_t profile;
    pthread_t consumer;
    uint8_t *iq = NULL;
    double *dma_ms = NULL;
    p0_st06_summary_t dma_summary;
    p0_st06_summary_t processing_summary;
    struct timespec started;
    struct timespec finished;
    struct timespec cpu_started;
    struct timespec cpu_finished;
    uint64_t measured_frames;
    uint64_t warmup_frames;
    uint64_t sample_rate_hz;
    uint64_t frame;
    double elapsed = 0.0;
    double process_cpu_seconds = 0.0;
    double cpu_core_equivalents = 0.0;
    double measured_fps = 0.0;
    double required_fps = 0.0;
    int consumer_started = 0;
    int mutex_initialized = 0;
    int can_produce_initialized = 0;
    int can_consume_initialized = 0;
    int result = EXIT_FAILURE;
    size_t index;

    if (argc < 5 || argc > 6 ||
        parse_u64(argv[1], 1U, UINT32_MAX / 2U, &measured_frames) != 0 ||
        parse_u64(argv[2], 8U, UINT32_MAX / 2U, &warmup_frames) != 0 ||
        parse_u64(argv[3], 1U, UINT64_MAX, &sample_rate_hz) != 0) {
        fprintf(stderr,
                "Kullanım: %s ÖLÇÜM_KARESİ ISINMA_KARESİ ÖRNEKLEME_HIZI_HZ "
                "GİRİŞ_CI8 [DMA_AYGITI]\n",
                argv[0]);
        return EXIT_FAILURE;
    }
    device_path = argc == 6 ? argv[5] : "/dev/p0-dma";
    memset(&profile, 0, sizeof(profile));
    profile.warmup_frames = warmup_frames;
    profile.measured_frames = measured_frames;
    iq = malloc(P0_DMA_INPUT_BYTES);
    dma_ms = calloc((size_t)measured_frames, sizeof(*dma_ms));
    profile.processing_ms = calloc((size_t)measured_frames,
                                   sizeof(*profile.processing_ms));
    for (index = 0U; index < P0_ST06_QUEUE_DEPTH; ++index)
        profile.slots[index].packet = malloc(P0_DMA_OUTPUT_CAPACITY_BYTES);
    if (iq == NULL || dma_ms == NULL || profile.processing_ms == NULL ||
        read_iq(argv[4], iq) != 0 ||
        p0_dma_runtime_open(&dma, device_path) != 0 ||
        p0_st06_power_runtime_init(&profile.runtime) != 0)
        goto done;
    if (pthread_mutex_init(&profile.mutex, NULL) != 0)
        goto done;
    mutex_initialized = 1;
    if (pthread_cond_init(&profile.can_produce, NULL) != 0)
        goto done;
    can_produce_initialized = 1;
    if (pthread_cond_init(&profile.can_consume, NULL) != 0)
        goto done;
    can_consume_initialized = 1;
    for (index = 0U; index < P0_ST06_QUEUE_DEPTH; ++index) {
        if (profile.slots[index].packet == NULL)
            goto done;
    }
    if (pin_current_thread(P0_ST06_PRODUCER_CPU) != 0 ||
        pthread_create(&consumer, NULL, consume_frames, &profile) != 0)
        goto done;
    consumer_started = 1;

    for (frame = 0U; frame < warmup_frames; ++frame) {
        if (enqueue_frame(&profile, &dma, iq, (uint32_t)frame, dma_ms) != 0)
            goto stop_consumer;
    }
    if (wait_until_empty(&profile) != 0 ||
        clock_gettime(CLOCK_MONOTONIC, &started) != 0 ||
        clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &cpu_started) != 0)
        goto stop_consumer;
    for (frame = 0U; frame < measured_frames; ++frame) {
        uint32_t frame_id = (uint32_t)(warmup_frames + frame);
        if (enqueue_frame(&profile, &dma, iq, frame_id, dma_ms) != 0)
            goto stop_consumer;
    }
    if (wait_until_empty(&profile) != 0 ||
        clock_gettime(CLOCK_MONOTONIC, &finished) != 0 ||
        clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &cpu_finished) != 0)
        goto stop_consumer;
    elapsed = seconds(&started, &finished);
    process_cpu_seconds = seconds(&cpu_started, &cpu_finished);
    cpu_core_equivalents = elapsed > 0.0 ? process_cpu_seconds / elapsed : 0.0;
    result = EXIT_SUCCESS;

stop_consumer:
    pthread_mutex_lock(&profile.mutex);
    profile.producer_done = 1;
    if (result != EXIT_SUCCESS)
        set_failed(&profile);
    pthread_cond_broadcast(&profile.can_consume);
    pthread_mutex_unlock(&profile.mutex);
    pthread_join(consumer, NULL);
    consumer_started = 0;
    if (profile.failed || profile.completed_frames != measured_frames)
        result = EXIT_FAILURE;

    dma_summary = summarize(dma_ms, (size_t)profile.completed_frames);
    processing_summary = summarize(
        profile.processing_ms, (size_t)profile.completed_frames);
    measured_fps = elapsed > 0.0 ? (double)profile.completed_frames / elapsed : 0.0;
    required_fps = (double)sample_rate_hz / 4096.0;
    if (measured_fps < required_fps)
        result = EXIT_FAILURE;
    printf(
        "{\"schema\":\"p0-st06-pipelined-dma-profile-v1\","
        "\"status\":\"%s\",\"queue_depth\":%d,\"warmup_frames\":%" PRIu64
        ",\"measured_frames\":%" PRIu64 ",\"completed_frames\":%" PRIu64
        ",\"output_bytes_per_frame\":%d,\"elapsed_seconds\":%.9f,"
        "\"process_cpu_seconds\":%.9f,\"cpu_core_equivalents\":%.9f,"
        "\"dual_core_cpu_percent\":%.9f,"
        "\"required_frames_per_second\":%.9f,"
        "\"measured_frames_per_second\":%.9f,\"real_time_margin\":%.9f,",
        result == EXIT_SUCCESS ? "passed" : "failed", P0_ST06_QUEUE_DEPTH,
        warmup_frames, measured_frames, profile.completed_frames,
        P0_ST06_EXPECTED_OUTPUT_BYTES, elapsed, process_cpu_seconds,
        cpu_core_equivalents, cpu_core_equivalents * 50.0,
        required_fps, measured_fps,
        required_fps > 0.0 ? measured_fps / required_fps : 0.0);
    print_summary("dma_and_pl", &dma_summary);
    putchar(',');
    print_summary("arm_decode_and_detector", &processing_summary);
    printf(",\"checksum\":%" PRIu64 "}\n", profile.checksum);

done:
    if (consumer_started) {
        pthread_mutex_lock(&profile.mutex);
        profile.producer_done = 1;
        set_failed(&profile);
        pthread_mutex_unlock(&profile.mutex);
        pthread_join(consumer, NULL);
    }
    p0_st06_power_runtime_release(&profile.runtime);
    p0_dma_runtime_close(&dma);
    if (can_consume_initialized)
        pthread_cond_destroy(&profile.can_consume);
    if (can_produce_initialized)
        pthread_cond_destroy(&profile.can_produce);
    if (mutex_initialized)
        pthread_mutex_destroy(&profile.mutex);
    for (index = 0U; index < P0_ST06_QUEUE_DEPTH; ++index)
        free(profile.slots[index].packet);
    free(profile.processing_ms);
    free(dma_ms);
    free(iq);
    return result;
}
