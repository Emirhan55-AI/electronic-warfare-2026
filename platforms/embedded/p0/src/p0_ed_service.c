#define _GNU_SOURCE

#include <errno.h>
#include <grp.h>
#include <pthread.h>
#include <pwd.h>
#include <sched.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

#include "p0_dma_runtime.h"
#include "p0_ed_pipeline.h"
#include "p0_pl_os_cfar.h"
#include "p0_ed_service_protocol.h"

#define P0_ED_DEFAULT_DEVICE "/dev/p0-dma"
#define P0_ED_DEFAULT_SOCKET "/run/p0-ed/p0-ed.sock"
#define P0_ED_RUNTIME_DIRECTORY "/run/p0-ed"
#ifndef P0_ED_SERVICE_ACCOUNT
#define P0_ED_SERVICE_ACCOUNT "p0ed"
#endif
#ifndef P0_ED_OPERATOR_GROUP
#define P0_ED_OPERATOR_GROUP "petalinux"
#endif
#define P0_ED_IO_TIMEOUT_SECONDS 2
#define P0_ED_PIPELINE_DEPTH 4U
#define P0_ED_DMA_CPU 0
#define P0_ED_DETECTOR_CPU 1
#define P0_ED_ST06_POWER_FRAME_BYTES (4096U * 8U)

static volatile sig_atomic_t stop_requested;

typedef struct {
    p0_ed_request_view_t request;
    uint8_t iq[P0_ED_IQ_FRAME_BYTES];
    uint8_t *power;
    size_t power_bytes;
    struct p0_dma_status dma_status;
    int dma_succeeded;
    int decode_succeeded;
    int pl_decisions_present;
    uint64_t *decoded_raw;
    double *decoded_power;
    uint8_t *decoded_detections;
} p0_ed_work_slot_t;

typedef struct {
    pthread_mutex_t mutex;
    pthread_cond_t can_produce;
    pthread_cond_t can_consume;
    p0_ed_work_slot_t slots[P0_ED_PIPELINE_DEPTH];
    size_t head;
    size_t tail;
    size_t count;
    int producer_done;
    int failed;
    int client;
    p0_ed_pipeline_t *pipeline;
    uint8_t *response_buffer;
} p0_ed_worker_t;

static int pin_current_thread(int cpu)
{
    cpu_set_t set;

    if (sysconf(_SC_NPROCESSORS_CONF) <= cpu)
        return 0;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    return sched_setaffinity(0, sizeof(set), &set);
}

static void handle_signal(int signal_number)
{
    (void)signal_number;
    stop_requested = 1;
}

static int install_signal_handlers(void)
{
    struct sigaction action;

    memset(&action, 0, sizeof(action));
    action.sa_handler = handle_signal;
    if (sigemptyset(&action.sa_mask) != 0 || sigaction(SIGINT, &action, NULL) != 0 ||
        sigaction(SIGTERM, &action, NULL) != 0 || signal(SIGPIPE, SIG_IGN) == SIG_ERR)
        return -1;
    return 0;
}

static uint32_t dma_status_flags(const struct p0_dma_status *status)
{
    uint32_t flags = 0U;

    if (status->mm2s_completed != 0U)
        flags |= 1U << 0;
    if (status->s2mm_completed != 0U)
        flags |= 1U << 1;
    if (status->output_valid != 0U)
        flags |= 1U << 2;
    if (status->timed_out != 0U)
        flags |= 1U << 3;
    if (status->dma_error != 0U)
        flags |= 1U << 4;
    return flags;
}

static int configure_socket_path(const char *socket_path, uid_t service_uid, gid_t operator_gid)
{
    if (strcmp(socket_path, P0_ED_DEFAULT_SOCKET) == 0) {
        if (mkdir(P0_ED_RUNTIME_DIRECTORY, 0750) != 0 && errno != EEXIST)
            return -1;
        if (chown(P0_ED_RUNTIME_DIRECTORY, service_uid, operator_gid) != 0 ||
            chmod(P0_ED_RUNTIME_DIRECTORY, 0750) != 0)
            return -1;
    }
    if (unlink(socket_path) != 0 && errno != ENOENT)
        return -1;
    return 0;
}

static int create_server_socket(const char *socket_path, uid_t service_uid, gid_t operator_gid)
{
    struct sockaddr_un address;
    int descriptor;

    if (strlen(socket_path) >= sizeof(address.sun_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    descriptor = socket(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC, 0);
    if (descriptor < 0)
        return -1;
    memset(&address, 0, sizeof(address));
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, socket_path, strlen(socket_path) + 1U);
    if (bind(descriptor, (const struct sockaddr *)&address, sizeof(address)) != 0 ||
        chown(socket_path, service_uid, operator_gid) != 0 || chmod(socket_path, 0660) != 0 ||
        listen(descriptor, 4) != 0) {
        int saved = errno;
        close(descriptor);
        unlink(socket_path);
        errno = saved;
        return -1;
    }
    return descriptor;
}

static int drop_privileges(uid_t uid, gid_t gid)
{
    if (setgroups(0U, NULL) != 0 || setgid(gid) != 0 || setuid(uid) != 0)
        return -1;
    return getuid() == uid && geteuid() == uid && getgid() == gid && getegid() == gid ? 0 : -1;
}

static int send_response(int client, p0_ed_response_t *response, uint8_t *buffer)
{
    size_t message_bytes = 0U;

    if (p0_ed_response_encode(response, buffer, P0_ED_RESPONSE_BYTES, &message_bytes) != 0)
        return -1;
    return send(client, buffer, message_bytes, MSG_NOSIGNAL) == (ssize_t)message_bytes ? 0 : -1;
}

static void worker_fail_locked(p0_ed_worker_t *worker)
{
    worker->failed = 1;
    pthread_cond_broadcast(&worker->can_produce);
    pthread_cond_broadcast(&worker->can_consume);
}

static void *consume_requests(void *argument)
{
    p0_ed_worker_t *worker = argument;

    if (pin_current_thread(P0_ED_DETECTOR_CPU) != 0) {
        pthread_mutex_lock(&worker->mutex);
        worker_fail_locked(worker);
        pthread_mutex_unlock(&worker->mutex);
        return NULL;
    }
    for (;;) {
        p0_ed_work_slot_t *slot;
        p0_ed_response_t response;
        size_t candidate_count = 0U;
        int fatal_response = 0;

        pthread_mutex_lock(&worker->mutex);
        while (worker->count == 0U && !worker->producer_done && !worker->failed)
            pthread_cond_wait(&worker->can_consume, &worker->mutex);
        if (worker->failed || (worker->count == 0U && worker->producer_done)) {
            pthread_mutex_unlock(&worker->mutex);
            break;
        }
        slot = &worker->slots[worker->head];
        pthread_mutex_unlock(&worker->mutex);

        if (slot->decode_succeeded) {
            uint64_t *raw = worker->pipeline->raw_power;
            double *power = worker->pipeline->power;
            uint8_t *detections = worker->pipeline->detections;
            worker->pipeline->raw_power = slot->decoded_raw;
            worker->pipeline->power = slot->decoded_power;
            worker->pipeline->detections = slot->decoded_detections;
            slot->decoded_raw = raw;
            slot->decoded_power = power;
            slot->decoded_detections = detections;
        }
        memset(&response, 0, sizeof(response));
        response.abi_version = slot->request.abi_version;
        response.frame_id = slot->request.frame_id;
        response.dma_status_flags = dma_status_flags(&slot->dma_status);
        if (!slot->dma_succeeded) {
            response.status = P0_ED_SERVICE_DMA_FAILURE;
            fatal_response = 1;
        } else if (!slot->decode_succeeded ||
                   p0_ed_pipeline_process_decoded_trusted(
                       worker->pipeline, slot->request.frame_id,
                       (slot->request.flags & P0_ED_REQUEST_FLAG_RESET) != 0U,
                       slot->pl_decisions_present, &response.result,
                       &candidate_count) != 0) {
            response.status = P0_ED_SERVICE_PIPELINE_FAILURE;
            fatal_response = 1;
        } else {
            response.result.frame_id = slot->request.frame_id;
            response.status = P0_ED_SERVICE_OK;
            response.raw_candidate_count = (uint32_t)candidate_count;
            if ((slot->request.flags & P0_ED_REQUEST_FLAG_PARAMETER) != 0U) {
                if (p0_ed_pipeline_measure(
                        worker->pipeline,
                        (slot->request.flags & P0_ED_REQUEST_FLAG_PARAMETER_START) != 0U,
                        slot->request.parameter_intent_id,
                        slot->request.parameter_event_id,
                        slot->request.frame_id, slot->request.sample_rate_hz,
                        slot->request.center_frequency_hz,
                        slot->request.parameter_lower_shifted_bin,
                        slot->request.parameter_upper_shifted_bin, slot->iq,
                        P0_ED_IQ_FRAME_BYTES, &response.result,
                        &response.parameter) != 0) {
                    p0_parameter_runtime_reset(&worker->pipeline->parameter_runtime);
                    response.status = P0_ED_SERVICE_INTERNAL_FAILURE;
                    fatal_response = 1;
                } else {
                    response.parameter_present = 1U;
                }
            } else {
                p0_parameter_runtime_reset(&worker->pipeline->parameter_runtime);
            }
        }
        if (send_response(worker->client, &response, worker->response_buffer) != 0)
            fatal_response = 1;

        pthread_mutex_lock(&worker->mutex);
        worker->head = (worker->head + 1U) % P0_ED_PIPELINE_DEPTH;
        --worker->count;
        pthread_cond_signal(&worker->can_produce);
        if (fatal_response)
            worker_fail_locked(worker);
        pthread_mutex_unlock(&worker->mutex);
        if (fatal_response)
            break;
    }
    return NULL;
}

static int wait_for_worker_empty(p0_ed_worker_t *worker)
{
    int result;

    pthread_mutex_lock(&worker->mutex);
    while (worker->count != 0U && !worker->failed)
        pthread_cond_wait(&worker->can_produce, &worker->mutex);
    result = worker->failed ? -1 : 0;
    pthread_mutex_unlock(&worker->mutex);
    return result;
}

static void serve_client(int client, p0_dma_runtime_t *dma, p0_ed_pipeline_t *pipeline,
                         uint8_t *request_buffer, uint8_t *response_buffer)
{
    p0_ed_worker_t worker;
    pthread_t consumer;
    struct timeval timeout;
    size_t index;
    int mutex_initialized = 0;
    int can_produce_initialized = 0;
    int can_consume_initialized = 0;
    int consumer_started = 0;

    memset(&worker, 0, sizeof(worker));
    worker.client = client;
    worker.pipeline = pipeline;
    worker.response_buffer = response_buffer;
    for (index = 0U; index < P0_ED_PIPELINE_DEPTH; ++index) {
        worker.slots[index].power = malloc(P0_DMA_OUTPUT_CAPACITY_BYTES);
        worker.slots[index].decoded_raw = malloc(P0_ED_ST06_POWER_FRAME_BYTES);
        worker.slots[index].decoded_power = malloc(P0_ED_ST06_POWER_FRAME_BYTES);
        worker.slots[index].decoded_detections = malloc(4096U);
        if (worker.slots[index].power == NULL || worker.slots[index].decoded_raw == NULL ||
            worker.slots[index].decoded_power == NULL || worker.slots[index].decoded_detections == NULL)
            goto done;
    }
    if (pthread_mutex_init(&worker.mutex, NULL) != 0)
        goto done;
    mutex_initialized = 1;
    if (pthread_cond_init(&worker.can_produce, NULL) != 0)
        goto done;
    can_produce_initialized = 1;
    if (pthread_cond_init(&worker.can_consume, NULL) != 0)
        goto done;
    can_consume_initialized = 1;
    if (pthread_create(&consumer, NULL, consume_requests, &worker) != 0)
        goto done;
    consumer_started = 1;

    timeout.tv_sec = P0_ED_IO_TIMEOUT_SECONDS;
    timeout.tv_usec = 0;
    (void)setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    (void)setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    while (!stop_requested) {
        p0_ed_request_view_t request;
        p0_ed_work_slot_t *slot;
        int dma_succeeded;
        ssize_t received = recv(client, request_buffer, P0_ED_REQUEST_BYTES_V2,
                                MSG_TRUNC);

        if (received <= 0)
            break;
        if (p0_ed_request_decode(request_buffer, (size_t)received, &request) != 0) {
            p0_ed_response_t response;

            if (wait_for_worker_empty(&worker) != 0)
                break;
            memset(&response, 0, sizeof(response));
            response.abi_version = P0_ED_SERVICE_ABI_VERSION_V1;
            response.status = P0_ED_SERVICE_INVALID_REQUEST;
            (void)send_response(client, &response, response_buffer);
            break;
        }

        pthread_mutex_lock(&worker.mutex);
        while (worker.count == P0_ED_PIPELINE_DEPTH && !worker.failed)
            pthread_cond_wait(&worker.can_produce, &worker.mutex);
        if (worker.failed) {
            pthread_mutex_unlock(&worker.mutex);
            break;
        }
        slot = &worker.slots[worker.tail];
        pthread_mutex_unlock(&worker.mutex);

        slot->request = request;
        memcpy(slot->iq, request.iq, P0_ED_IQ_FRAME_BYTES);
        slot->request.iq = slot->iq;
        slot->power_bytes = 0U;
        memset(&slot->dma_status, 0, sizeof(slot->dma_status));
        slot->dma_succeeded =
            p0_dma_runtime_run(
                dma, slot->iq, P0_ED_IQ_FRAME_BYTES, slot->power,
                P0_DMA_OUTPUT_CAPACITY_BYTES, &slot->power_bytes,
                &slot->dma_status) == 0;
        slot->decode_succeeded = slot->dma_succeeded &&
            p0_pl_os_cfar_decode(slot->power, slot->power_bytes, slot->decoded_raw,
                slot->decoded_power, slot->decoded_detections,
                &slot->pl_decisions_present) == P0_PL_OS_CFAR_OK;
        dma_succeeded = slot->dma_succeeded;

        pthread_mutex_lock(&worker.mutex);
        if (worker.failed) {
            pthread_mutex_unlock(&worker.mutex);
            break;
        }
        worker.tail = (worker.tail + 1U) % P0_ED_PIPELINE_DEPTH;
        ++worker.count;
        pthread_cond_signal(&worker.can_consume);
        pthread_mutex_unlock(&worker.mutex);
        if (!dma_succeeded)
            break;
    }

done:
    if (consumer_started) {
        pthread_mutex_lock(&worker.mutex);
        worker.producer_done = 1;
        pthread_cond_broadcast(&worker.can_consume);
        pthread_mutex_unlock(&worker.mutex);
        pthread_join(consumer, NULL);
    }
    if (can_consume_initialized)
        pthread_cond_destroy(&worker.can_consume);
    if (can_produce_initialized)
        pthread_cond_destroy(&worker.can_produce);
    if (mutex_initialized)
        pthread_mutex_destroy(&worker.mutex);
    for (index = 0U; index < P0_ED_PIPELINE_DEPTH; ++index) {
        free(worker.slots[index].power);
        free(worker.slots[index].decoded_raw);
        free(worker.slots[index].decoded_power);
        free(worker.slots[index].decoded_detections);
    }
}

int main(int argc, char **argv)
{
    const char *device_path = argc > 1 ? argv[1] : P0_ED_DEFAULT_DEVICE;
    const char *socket_path = argc > 2 ? argv[2] : P0_ED_DEFAULT_SOCKET;
    struct passwd *account;
    struct group *operator_group;
    p0_dma_runtime_t dma = {-1};
    p0_ed_pipeline_t pipeline;
    uint8_t *request_buffer = NULL;
    uint8_t *response_buffer = NULL;
    int server = -1;
    int result = EXIT_FAILURE;

    if (argc > 3) {
        fprintf(stderr, "Kullanım: %s [DMA_AYGITI] [YEREL_SOKET]\n", argv[0]);
        return EXIT_FAILURE;
    }
    account = getpwnam(P0_ED_SERVICE_ACCOUNT);
    if (account == NULL) {
        fputs("p0ed hizmet hesabı bulunamadı.\n", stderr);
        return EXIT_FAILURE;
    }
    operator_group = getgrnam(P0_ED_OPERATOR_GROUP);
    if (operator_group == NULL) {
        fputs("petalinux operatör grubu bulunamadı.\n", stderr);
        return EXIT_FAILURE;
    }
    if (p0_dma_runtime_open(&dma, device_path) != 0) {
        fprintf(stderr, "DMA aygıtı açılamadı: %s\n", strerror(errno));
        return EXIT_FAILURE;
    }
    if (p0_ed_pipeline_init(&pipeline) != 0) {
        fputs("ED işleme zinciri başlatılamadı.\n", stderr);
        goto done;
    }
    request_buffer = malloc(P0_ED_REQUEST_BYTES_V2);
    response_buffer = malloc(P0_ED_RESPONSE_BYTES);
    if (request_buffer == NULL || response_buffer == NULL) {
        fputs("Hizmet belleği ayrılamadı.\n", stderr);
        goto release_pipeline;
    }
    if (configure_socket_path(socket_path, account->pw_uid, operator_group->gr_gid) != 0 ||
        (server = create_server_socket(socket_path, account->pw_uid,
                                       operator_group->gr_gid)) < 0) {
        fprintf(stderr, "Yerel hizmet soketi açılamadı: %s\n", strerror(errno));
        goto release_pipeline;
    }
    if (drop_privileges(account->pw_uid, account->pw_gid) != 0) {
        fprintf(stderr, "Hizmet yetkileri düşürülemedi: %s\n", strerror(errno));
        goto release_pipeline;
    }
    if (install_signal_handlers() != 0) {
        fprintf(stderr, "Sinyal işleyicileri kurulamadı: %s\n", strerror(errno));
        goto release_pipeline;
    }
    if (pin_current_thread(P0_ED_DMA_CPU) != 0) {
        fprintf(stderr, "Hizmet CPU yerleşimi uygulanamadı: %s\n", strerror(errno));
        goto release_pipeline;
    }
    puts("P0 ED kart hizmeti hazır.");
    fflush(stdout);
    while (!stop_requested) {
        int client = accept4(server, NULL, NULL, SOCK_CLOEXEC);

        if (client < 0) {
            if (errno == EINTR)
                continue;
            fprintf(stderr, "İstemci kabul edilemedi: %s\n", strerror(errno));
            break;
        }
        serve_client(client, &dma, &pipeline, request_buffer, response_buffer);
        close(client);
    }
    result = EXIT_SUCCESS;

release_pipeline:
    if (server >= 0)
        close(server);
    unlink(socket_path);
    free(response_buffer);
    free(request_buffer);
    p0_ed_pipeline_release(&pipeline);
done:
    p0_dma_runtime_close(&dma);
    return result;
}
