#define _GNU_SOURCE

#include <errno.h>
#include <grp.h>
#include <pwd.h>
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

static volatile sig_atomic_t stop_requested;

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

static void serve_client(int client, p0_dma_runtime_t *dma, p0_ed_pipeline_t *pipeline,
                         uint8_t *request_buffer, uint8_t *response_buffer,
                         uint8_t *packet_buffer)
{
    struct timeval timeout;

    timeout.tv_sec = P0_ED_IO_TIMEOUT_SECONDS;
    timeout.tv_usec = 0;
    (void)setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    (void)setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    while (!stop_requested) {
        struct p0_dma_status dma_status;
        p0_ed_request_view_t request;
        p0_ed_response_t response;
        ssize_t received;
        size_t candidate_count = 0U;
        size_t packet_bytes = 0U;
        uint32_t packet_frame_id = 0U;

        memset(&response, 0, sizeof(response));
        received = recv(client, request_buffer, P0_ED_REQUEST_BYTES_V2, MSG_TRUNC);
        if (received <= 0)
            return;
        if (p0_ed_request_decode(request_buffer, (size_t)received, &request) != 0) {
            response.status = P0_ED_SERVICE_INVALID_REQUEST;
            (void)send_response(client, &response, response_buffer);
            return;
        }
        response.abi_version = request.abi_version;
        response.frame_id = request.frame_id;
        if (p0_dma_runtime_run(dma, request.iq, P0_ED_IQ_FRAME_BYTES, packet_buffer,
                               P0_DMA_OUTPUT_CAPACITY_BYTES, &packet_bytes,
                               &dma_status) != 0) {
            response.status = P0_ED_SERVICE_DMA_FAILURE;
            response.dma_status_flags = dma_status_flags(&dma_status);
            (void)send_response(client, &response, response_buffer);
            return;
        }
        response.dma_status_flags = dma_status_flags(&dma_status);
        if (p0_ed_pipeline_process_packet(
                pipeline, (request.flags & P0_ED_REQUEST_FLAG_RESET) != 0U,
                packet_buffer, packet_bytes, &response.result, &candidate_count,
                &packet_frame_id) != 0) {
            response.status = P0_ED_SERVICE_PIPELINE_FAILURE;
            (void)send_response(client, &response, response_buffer);
            return;
        }
        /* The socket ABI correlates results to the request frame.  The
         * packetizer's independent frame counter remains internal to the
         * temporal state machine and is not exposed as a second wire ID. */
        (void)packet_frame_id;
        response.result.frame_id = request.frame_id;
        response.status = P0_ED_SERVICE_OK;
        response.raw_candidate_count = (uint32_t)candidate_count;
        if ((request.flags & P0_ED_REQUEST_FLAG_PARAMETER) != 0U) {
            if (p0_ed_pipeline_measure(
                    pipeline,
                    (request.flags & P0_ED_REQUEST_FLAG_PARAMETER_START) != 0U,
                    request.parameter_intent_id, request.parameter_event_id,
                    request.frame_id, request.sample_rate_hz,
                    request.center_frequency_hz,
                    request.parameter_lower_shifted_bin,
                    request.parameter_upper_shifted_bin, request.iq,
                    P0_ED_IQ_FRAME_BYTES, &response.result,
                    &response.parameter) != 0) {
                p0_parameter_runtime_reset(&pipeline->parameter_runtime);
                response.status = P0_ED_SERVICE_INTERNAL_FAILURE;
                (void)send_response(client, &response, response_buffer);
                return;
            }
            response.parameter_present = 1U;
        } else {
            p0_parameter_runtime_reset(&pipeline->parameter_runtime);
        }
        if (send_response(client, &response, response_buffer) != 0)
            return;
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
    uint8_t *packet_buffer = NULL;
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
    packet_buffer = malloc(P0_DMA_OUTPUT_CAPACITY_BYTES);
    if (request_buffer == NULL || response_buffer == NULL || packet_buffer == NULL) {
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
        serve_client(client, &dma, &pipeline, request_buffer, response_buffer, packet_buffer);
        close(client);
    }
    result = EXIT_SUCCESS;

release_pipeline:
    if (server >= 0)
        close(server);
    unlink(socket_path);
    free(packet_buffer);
    free(response_buffer);
    free(request_buffer);
    p0_ed_pipeline_release(&pipeline);
done:
    p0_dma_runtime_close(&dma);
    return result;
}
