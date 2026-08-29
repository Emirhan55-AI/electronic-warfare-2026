#define _GNU_SOURCE

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

#include "p0_ed_service_protocol.h"

#define P0_ED_DEFAULT_SOCKET "/run/p0-ed/p0-ed.sock"
#define P0_ED_FRAME_SAMPLES 4096U
#define P0_ED_EXPECTED_DMA_FLAGS 7U
#define P0_ED_MAX_MEASURED_FRAMES 1000000U
#define P0_ED_THROUGHPUT_CPU 0
#define P0_ED_REQUEST_PIPELINE_DEPTH 4U

typedef struct {
    uint64_t request_failures;
    uint64_t service_failures;
    uint64_t sequence_failures;
    uint64_t dma_flag_failures;
    uint64_t dropped_candidates;
} failure_counts_t;

typedef struct {
    int descriptor;
    uint8_t *request;
    uint8_t *reply;
} service_connection_t;

static int pin_throughput_cpu(void)
{
    cpu_set_t set;

    if (sysconf(_SC_NPROCESSORS_CONF) <= P0_ED_THROUGHPUT_CPU)
        return 0;
    CPU_ZERO(&set);
    CPU_SET(P0_ED_THROUGHPUT_CPU, &set);
    return sched_setaffinity(0, sizeof(set), &set);
}

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
    if (fread(buffer, 1U, P0_ED_IQ_FRAME_BYTES, file) != P0_ED_IQ_FRAME_BYTES) {
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

static double seconds_between(const struct timespec *start, const struct timespec *end)
{
    return (double)(end->tv_sec - start->tv_sec) +
           (double)(end->tv_nsec - start->tv_nsec) / 1000000000.0;
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

static void close_connection(service_connection_t *connection)
{
    if (connection->descriptor >= 0)
        close(connection->descriptor);
    free(connection->reply);
    free(connection->request);
    connection->descriptor = -1;
    connection->reply = NULL;
    connection->request = NULL;
}

static int open_connection(service_connection_t *connection, const char *socket_path)
{
    struct sockaddr_un address;
    struct timeval timeout;

    memset(connection, 0, sizeof(*connection));
    connection->descriptor = -1;
    if (strlen(socket_path) >= sizeof(address.sun_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    connection->request = malloc(P0_ED_REQUEST_BYTES);
    connection->reply = malloc(P0_ED_RESPONSE_BYTES);
    if (connection->request == NULL || connection->reply == NULL)
        goto done;
    connection->descriptor = socket(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC, 0);
    if (connection->descriptor < 0)
        goto done;
    timeout.tv_sec = 3;
    timeout.tv_usec = 0;
    if (setsockopt(connection->descriptor, SOL_SOCKET, SO_RCVTIMEO,
                   &timeout, sizeof(timeout)) != 0 ||
        setsockopt(connection->descriptor, SOL_SOCKET, SO_SNDTIMEO,
                   &timeout, sizeof(timeout)) != 0)
        goto done;
    memset(&address, 0, sizeof(address));
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, socket_path, strlen(socket_path) + 1U);
    if (connect(connection->descriptor, (const struct sockaddr *)&address,
                sizeof(address)) != 0)
        goto done;
    return 0;

done:
    close_connection(connection);
    return -1;
}

static int send_frame(service_connection_t *connection, uint32_t frame_id,
                      uint32_t flags, const uint8_t *iq,
                      struct timespec *started)
{
    if (p0_ed_request_encode_compact(frame_id, flags, iq, P0_ED_IQ_FRAME_BYTES,
                                     connection->request, P0_ED_REQUEST_BYTES) != 0 ||
        clock_gettime(CLOCK_MONOTONIC, started) != 0)
        return -1;
    return send(connection->descriptor, connection->request, P0_ED_REQUEST_BYTES,
                MSG_NOSIGNAL) == (ssize_t)P0_ED_REQUEST_BYTES ? 0 : -1;
}

static int receive_frame(service_connection_t *connection,
                         const struct timespec *started,
                         p0_ed_response_t *response, double *latency_seconds)
{
    struct timespec finished;
    ssize_t received = recv(connection->descriptor, connection->reply,
                            P0_ED_RESPONSE_BYTES, MSG_TRUNC);

    if (received < 0 ||
        p0_ed_response_decode(connection->reply, (size_t)received, response) != 0 ||
        clock_gettime(CLOCK_MONOTONIC, &finished) != 0)
        return -1;
    *latency_seconds = seconds_between(started, &finished);
    return 0;
}

static int validate_response(const p0_ed_response_t *response, uint32_t frame_id,
                             failure_counts_t *failures)
{
    if (response->status != P0_ED_SERVICE_OK) {
        failures->service_failures += 1U;
        return -1;
    }
    if (response->frame_id != frame_id) {
        failures->sequence_failures += 1U;
        return -1;
    }
    if (response->dma_status_flags != P0_ED_EXPECTED_DMA_FLAGS) {
        failures->dma_flag_failures += 1U;
        return -1;
    }
    failures->dropped_candidates += response->result.dropped_candidates;
    return 0;
}

static size_t execute_batch(service_connection_t *connection,
                            uint32_t first_frame_id, size_t frame_count,
                            int reset_first, const uint8_t *iq,
                            double *latencies, failure_counts_t *failures)
{
    struct timespec started[P0_ED_REQUEST_PIPELINE_DEPTH];
    size_t index;

    if (frame_count == 0U || frame_count > P0_ED_REQUEST_PIPELINE_DEPTH)
        return 0U;
    for (index = 0U; index < frame_count; ++index) {
        uint32_t flags = reset_first && index == 0U
                             ? P0_ED_REQUEST_FLAG_RESET
                             : 0U;

        if (send_frame(connection, first_frame_id + (uint32_t)index,
                       flags, iq, &started[index]) != 0) {
            failures->request_failures += 1U;
            return 0U;
        }
    }
    for (index = 0U; index < frame_count; ++index) {
        p0_ed_response_t response;

        memset(&response, 0, sizeof(response));
        if (receive_frame(connection, &started[index], &response,
                          &latencies[index]) != 0) {
            failures->request_failures += 1U;
            return index;
        }
        if (validate_response(&response, first_frame_id + (uint32_t)index,
                              failures) != 0)
            return index;
    }
    return frame_count;
}

static void write_result(uint64_t measured_frames, uint64_t warmup_frames,
                         uint64_t sample_rate_hz, uint64_t completed_frames,
                         double elapsed, double *latencies,
                         const failure_counts_t *failures)
{
    double required_frames_per_second =
        (double)sample_rate_hz / (double)P0_ED_FRAME_SAMPLES;
    double measured_frames_per_second =
        elapsed > 0.0 ? (double)completed_frames / elapsed : 0.0;
    double minimum = 0.0;
    double maximum = 0.0;
    double p50 = 0.0;
    double p95 = 0.0;
    double p99 = 0.0;
    int passed;

    if (completed_frames != 0U) {
        qsort(latencies, (size_t)completed_frames, sizeof(*latencies), compare_double);
        minimum = latencies[0U];
        maximum = latencies[completed_frames - 1U];
        p50 = percentile(latencies, (size_t)completed_frames, 0.50);
        p95 = percentile(latencies, (size_t)completed_frames, 0.95);
        p99 = percentile(latencies, (size_t)completed_frames, 0.99);
    }
    passed = completed_frames == measured_frames &&
             failures->request_failures == 0U && failures->service_failures == 0U &&
             failures->sequence_failures == 0U && failures->dma_flag_failures == 0U &&
             failures->dropped_candidates == 0U &&
             measured_frames_per_second >= required_frames_per_second;
    printf(
        "{\n"
        "  \"schema_version\": 1,\n"
        "  \"status\": \"%s\",\n"
        "  \"scope\": \"yerel PL-DMA-ARM ED hizmeti\",\n"
        "  \"request_pipeline_depth\": %u,\n"
        "  \"profile\": {\"sample_rate_hz\": %" PRIu64
        ", \"frame_samples\": %u, \"warmup_frames\": %" PRIu64
        ", \"measured_frames\": %" PRIu64 "},\n"
        "  \"completion\": {\"completed_frames\": %" PRIu64
        ", \"request_failures\": %" PRIu64
        ", \"service_failures\": %" PRIu64
        ", \"sequence_failures\": %" PRIu64
        ", \"dma_flag_failures\": %" PRIu64
        ", \"dropped_candidates\": %" PRIu64 "},\n"
        "  \"throughput\": {\"elapsed_seconds\": %.9f, "
        "\"required_frames_per_second\": %.9f, "
        "\"measured_frames_per_second\": %.9f, "
        "\"real_time_margin\": %.9f},\n"
        "  \"latency_seconds\": {\"minimum\": %.9f, \"p50\": %.9f, "
        "\"p95\": %.9f, \"p99\": %.9f, \"maximum\": %.9f},\n"
        "  \"expected_dma_status_flags\": 7,\n"
        "  \"claim_boundary\": \"Deterministik yerel hizmet yükü; canlı RF, "
        "USB/Ethernet aktarımı, kalibrasyon veya saha doğruluğu değildir.\"\n"
        "}\n",
        passed ? "passed" : "failed", P0_ED_REQUEST_PIPELINE_DEPTH,
        sample_rate_hz, P0_ED_FRAME_SAMPLES,
        warmup_frames, measured_frames, completed_frames,
        failures->request_failures, failures->service_failures,
        failures->sequence_failures, failures->dma_flag_failures,
        failures->dropped_candidates, elapsed, required_frames_per_second,
        measured_frames_per_second,
        required_frames_per_second > 0.0
            ? measured_frames_per_second / required_frames_per_second
            : 0.0,
        minimum, p50, p95, p99, maximum);
}

int main(int argc, char **argv)
{
    const char *socket_path;
    uint8_t *iq = NULL;
    double *latencies = NULL;
    failure_counts_t failures = {0U, 0U, 0U, 0U, 0U};
    service_connection_t connection = {-1, NULL, NULL};
    struct timespec started;
    struct timespec finished;
    uint64_t measured_frames;
    uint64_t warmup_frames;
    uint64_t sample_rate_hz;
    uint64_t index;
    uint64_t completed = 0U;
    double elapsed = 0.0;
    int result = EXIT_FAILURE;

    if (argc < 5 || argc > 6 ||
        parse_u64(argv[1], 1U, P0_ED_MAX_MEASURED_FRAMES, &measured_frames) != 0 ||
        parse_u64(argv[2], 0U, P0_ED_MAX_MEASURED_FRAMES, &warmup_frames) != 0 ||
        parse_u64(argv[3], 1U, UINT64_MAX, &sample_rate_hz) != 0) {
        fprintf(stderr,
                "Kullanım: %s ÖLÇÜM_KARESİ ISINMA_KARESİ ÖRNEKLEME_HIZI_HZ "
                "GİRİŞ_CI8 [YEREL_SOKET]\n",
                argv[0]);
        return EXIT_FAILURE;
    }
    socket_path = argc == 6 ? argv[5] : P0_ED_DEFAULT_SOCKET;
    if (pin_throughput_cpu() != 0) {
        fprintf(stderr, "Ölçüm CPU yerleşimi uygulanamadı: %s\n", strerror(errno));
        return EXIT_FAILURE;
    }
    iq = malloc(P0_ED_IQ_FRAME_BYTES);
    latencies = calloc((size_t)measured_frames, sizeof(*latencies));
    if (iq == NULL || latencies == NULL) {
        fputs("Ölçüm belleği ayrılamadı.\n", stderr);
        goto done;
    }
    if (read_exact_frame(argv[4], iq) != 0) {
        fprintf(stderr, "I/Q kabul karesi okunamadı: %s\n", strerror(errno));
        goto done;
    }
    if (open_connection(&connection, socket_path) != 0) {
        fprintf(stderr, "Yerel ED hizmetine bağlanılamadı: %s\n", strerror(errno));
        goto done;
    }
    for (index = 0U; index < warmup_frames;) {
        double ignored_latency[P0_ED_REQUEST_PIPELINE_DEPTH];
        size_t batch = (size_t)(warmup_frames - index);
        size_t completed_batch;

        if (batch > P0_ED_REQUEST_PIPELINE_DEPTH)
            batch = P0_ED_REQUEST_PIPELINE_DEPTH;
        completed_batch = execute_batch(
            &connection, (uint32_t)index, batch, index == 0U, iq,
            ignored_latency, &failures);
        index += completed_batch;
        if (completed_batch != batch)
            break;
    }
    if (index != warmup_frames)
        goto report;
    if (clock_gettime(CLOCK_MONOTONIC, &started) != 0)
        goto done;
    for (index = 0U; index < measured_frames;) {
        size_t batch = (size_t)(measured_frames - index);
        size_t completed_batch;

        if (batch > P0_ED_REQUEST_PIPELINE_DEPTH)
            batch = P0_ED_REQUEST_PIPELINE_DEPTH;
        completed_batch = execute_batch(
            &connection, (uint32_t)index, batch, index == 0U, iq,
            &latencies[index], &failures);
        index += completed_batch;
        completed += completed_batch;
        if (completed_batch != batch)
            break;
    }
    if (clock_gettime(CLOCK_MONOTONIC, &finished) != 0)
        goto done;
    elapsed = seconds_between(&started, &finished);

report:
    write_result(measured_frames, warmup_frames, sample_rate_hz, completed,
                 elapsed, latencies, &failures);
    if (completed == measured_frames && failures.request_failures == 0U &&
        failures.service_failures == 0U && failures.sequence_failures == 0U &&
        failures.dma_flag_failures == 0U && failures.dropped_candidates == 0U &&
        elapsed > 0.0 && (double)completed / elapsed >=
            (double)sample_rate_hz / (double)P0_ED_FRAME_SAMPLES)
        result = EXIT_SUCCESS;

done:
    close_connection(&connection);
    free(latencies);
    free(iq);
    return result;
}
