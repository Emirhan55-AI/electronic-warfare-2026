#define _POSIX_C_SOURCE 200809L

#include "p0_st06_power_runtime.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "p0_pl_os_cfar.h"

enum {
    WARMUP_FRAMES = 16,
    MEASURED_FRAMES = 256
};

#define OUTPUT_MARKER (UINT64_C(0xA) << 60U)
#define EVALUATED_MASK (UINT64_C(1) << 58U)
#define POWER_SCALE (UINT64_C(1) << 30U)

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

static void store_u64_le(uint8_t *target, uint64_t value)
{
    unsigned int index;
    for (index = 0U; index < 8U; ++index)
        target[index] = (uint8_t)(value >> (index * 8U));
}

static void fill_packet(uint8_t *packet, uint32_t frame_id, int wide_signal)
{
    uint32_t state = UINT32_C(0x9e3779b9) ^
                     (frame_id * UINT32_C(0x85ebca6b));
    size_t shifted;

    for (shifted = 0U; shifted < P0_PL_OS_CFAR_FRAME_BINS; ++shifted) {
        size_t natural = shifted ^ (P0_PL_OS_CFAR_FRAME_BINS / 2U);
        double random_component =
            (double)(xorshift32(&state) & UINT32_C(0xffff)) / 65535.0;
        double slope = 0.1 * (double)shifted /
                       (double)P0_PL_OS_CFAR_FRAME_BINS;
        double power = 0.95 + 0.10 * random_component + slope;
        uint64_t word;

        if (wide_signal && shifted >= 1400U && shifted <= 2200U)
            power += 3.5 + 0.05 * (double)((shifted + frame_id) & 7U);
        word = OUTPUT_MARKER | (uint64_t)floor(power * (double)POWER_SCALE + 0.5);
        if (shifted >= P0_PL_OS_CFAR_RADIUS &&
            shifted < P0_PL_OS_CFAR_FRAME_BINS - P0_PL_OS_CFAR_RADIUS)
            word |= EVALUATED_MASK;
        store_u64_le(packet + natural * 8U, word);
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
    p0_st06_power_runtime_t runtime;
    uint8_t *packet = calloc(P0_PL_OS_CFAR_FRAME_BYTES, 1U);
    double durations[MEASURED_FRAMES];
    p0_st05_result_t result;
    uint64_t checksum = 0U;
    double total_ms = 0.0;
    size_t frame;

    if (packet == NULL || measurement == NULL ||
        p0_st06_power_runtime_init(&runtime) != 0) {
        free(packet);
        return -1;
    }
    for (frame = 0U; frame < WARMUP_FRAMES + MEASURED_FRAMES; ++frame) {
        struct timespec start;
        struct timespec stop;
        int result_valid = 0;
        int context_reset = 0;
        int code;

        fill_packet(packet, (uint32_t)frame, wide_signal);
        if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) {
            p0_st06_power_runtime_release(&runtime);
            free(packet);
            return -1;
        }
        code = p0_st06_power_runtime_process(
            &runtime, (uint32_t)frame, frame == 0U, packet,
            P0_PL_OS_CFAR_FRAME_BYTES, &result, &result_valid, &context_reset);
        if (clock_gettime(CLOCK_MONOTONIC, &stop) != 0 || code != 0 ||
            (frame == 0U ? !context_reset : context_reset)) {
            p0_st06_power_runtime_release(&runtime);
            free(packet);
            return -1;
        }
        if (result_valid) {
            checksum += (uint64_t)result.decision +
                        result.candidate_count * UINT64_C(17) +
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
    p0_st06_power_runtime_release(&runtime);
    free(packet);
    return 0;
}

static void print_result(const char *name, const benchmark_result_t *result)
{
    printf(
        "\"%s\":{\"minimum_ms\":%.9f,\"median_ms\":%.9f,"
        "\"p95_ms\":%.9f,\"p99_ms\":%.9f,\"maximum_ms\":%.9f,"
        "\"mean_ms\":%.9f,\"frames_per_second\":%.9f,\"checksum\":%llu}",
        name, result->minimum_ms, result->median_ms, result->p95_ms,
        result->p99_ms, result->maximum_ms, result->mean_ms,
        result->frames_per_second, (unsigned long long)result->checksum);
}

int main(void)
{
    benchmark_result_t noise;
    benchmark_result_t wide;

    if (run_scenario(0, &noise) != 0 || run_scenario(1, &wide) != 0) {
        fputs("ST-06 güç çalışma ölçümü çalıştırılamadı.\n", stderr);
        return 1;
    }
    printf("{\"schema\":\"p0-st06-power-runtime-benchmark-v3\","
           "\"warmup_frames\":%d,\"measured_frames_per_scenario\":%d,",
           WARMUP_FRAMES, MEASURED_FRAMES);
    print_result("noise", &noise);
    putchar(',');
    print_result("wide_signal", &wide);
    puts("}");
    return 0;
}
