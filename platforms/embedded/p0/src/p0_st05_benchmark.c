#define _POSIX_C_SOURCE 200809L

#include "p0_st05_stream.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

enum {
    WARMUP_FRAMES = 16,
    MEASURED_FRAMES = 256
};

typedef struct {
    double minimum_ms;
    double median_ms;
    double p95_ms;
    double p99_ms;
    double maximum_ms;
    double mean_ms;
    double frames_per_second;
    uint64_t checksum;
} benchmark_result_t;

static int compare_double(const void *left, const void *right)
{
    const double first = *(const double *)left;
    const double second = *(const double *)right;
    return (first > second) - (first < second);
}

static uint32_t xorshift32(uint32_t *state)
{
    uint32_t value = *state;
    value ^= value << 13U;
    value ^= value >> 17U;
    value ^= value << 5U;
    *state = value;
    return value;
}

static void fill_frame(double *power, uint32_t frame_id, int wide_signal)
{
    uint32_t state = UINT32_C(0x9e3779b9) ^ (frame_id * UINT32_C(0x85ebca6b));
    size_t index;

    for (index = 0U; index < P0_ST05_FRAME_BINS; ++index) {
        double random_component = (double)(xorshift32(&state) & UINT32_C(0xffff)) /
                                  65535.0;
        double slope = 0.1 * (double)index / (double)P0_ST05_FRAME_BINS;
        power[index] = 0.95 + 0.10 * random_component + slope;
        if (wide_signal && index >= 1400U && index <= 2200U)
            power[index] += 3.5 + 0.05 * (double)((index + frame_id) & 7U);
    }
}

static double milliseconds(const struct timespec *start, const struct timespec *stop)
{
    return ((double)(stop->tv_sec - start->tv_sec) * 1000.0) +
           ((double)(stop->tv_nsec - start->tv_nsec) / 1000000.0);
}

static size_t percentile_index(size_t count, double percentile)
{
    size_t index = (size_t)ceil(percentile * (double)count);
    return index == 0U ? 0U : index - 1U;
}

static int run_scenario(int wide_signal, benchmark_result_t *measurement)
{
    const size_t state_bytes = p0_st05_stream_state_bytes();
    void *state = calloc(1U, state_bytes);
    double *power = calloc(P0_ST05_FRAME_BINS, sizeof(*power));
    double durations[MEASURED_FRAMES];
    p0_st05_result_t result;
    uint64_t checksum = 0U;
    double total_ms = 0.0;
    size_t frame;

    if (state == NULL || power == NULL || measurement == NULL) {
        free(power);
        free(state);
        return -1;
    }
    if (p0_st05_stream_init(state, state_bytes) != P0_ST05_OK) {
        free(power);
        free(state);
        return -1;
    }
    for (frame = 0U; frame < WARMUP_FRAMES + MEASURED_FRAMES; ++frame) {
        struct timespec start;
        struct timespec stop;
        int result_valid = 0;
        int code;

        fill_frame(power, (uint32_t)frame, wide_signal);
        if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) {
            free(power);
            free(state);
            return -1;
        }
        code = p0_st05_stream_update(
            state, state_bytes, power, P0_ST05_FRAME_BINS, &result, &result_valid);
        if (clock_gettime(CLOCK_MONOTONIC, &stop) != 0 || code != P0_ST05_OK) {
            free(power);
            free(state);
            return -1;
        }
        if (result_valid) {
            checksum += (uint64_t)result.decision + result.candidate_count * UINT64_C(17) +
                        result.unresolved_count * UINT64_C(31);
            if (result.candidate_count != 0U)
                checksum += result.candidates[0U].peak_bin;
        }
        if (frame >= WARMUP_FRAMES) {
            double elapsed_ms = milliseconds(&start, &stop);
            durations[frame - WARMUP_FRAMES] = elapsed_ms;
            total_ms += elapsed_ms;
        }
    }
    qsort(durations, MEASURED_FRAMES, sizeof(*durations), compare_double);
    measurement->minimum_ms = durations[0U];
    measurement->median_ms = durations[MEASURED_FRAMES / 2U];
    measurement->p95_ms = durations[percentile_index(MEASURED_FRAMES, 0.95)];
    measurement->p99_ms = durations[percentile_index(MEASURED_FRAMES, 0.99)];
    measurement->maximum_ms = durations[MEASURED_FRAMES - 1U];
    measurement->mean_ms = total_ms / (double)MEASURED_FRAMES;
    measurement->frames_per_second = 1000.0 / measurement->mean_ms;
    measurement->checksum = checksum;
    free(power);
    free(state);
    return 0;
}

static void print_result(const char *name, const benchmark_result_t *result)
{
    printf(
        "\"%s\":{\"minimum_ms\":%.9f,\"median_ms\":%.9f,"
        "\"p95_ms\":%.9f,\"p99_ms\":%.9f,\"maximum_ms\":%.9f,"
        "\"mean_ms\":%.9f,\"frames_per_second\":%.9f,\"checksum\":%llu}",
        name,
        result->minimum_ms,
        result->median_ms,
        result->p95_ms,
        result->p99_ms,
        result->maximum_ms,
        result->mean_ms,
        result->frames_per_second,
        (unsigned long long)result->checksum);
}

int main(void)
{
    benchmark_result_t noise;
    benchmark_result_t wide;

    if (run_scenario(0, &noise) != 0 || run_scenario(1, &wide) != 0) {
        fputs("ST-06 ARM ölçümü çalıştırılamadı.\n", stderr);
        return 1;
    }
    printf("{\"schema\":\"p0-st06-arm-benchmark-v3\",\"warmup_frames\":%d,"
           "\"measured_frames_per_scenario\":%d,\"state_bytes\":%lu,",
           WARMUP_FRAMES,
           MEASURED_FRAMES,
           (unsigned long)p0_st05_stream_state_bytes());
    print_result("noise", &noise);
    putchar(',');
    print_result("wide_signal", &wide);
    puts("}");
    return 0;
}
