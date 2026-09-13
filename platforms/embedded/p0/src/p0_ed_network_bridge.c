#define _GNU_SOURCE

#include <arpa/inet.h>
#include <errno.h>
#include <grp.h>
#include <poll.h>
#include <pwd.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/uio.h>
#include <sys/un.h>
#include <netinet/tcp.h>
#include <unistd.h>

#include "p0_ed_service_protocol.h"
#include "p0_iq_transport.h"

#define P0_NETWORK_PIPELINE_DEPTH 4U
#define P0_NETWORK_IO_TIMEOUT_SECONDS 2
#ifndef P0_NETWORK_SERVICE_ACCOUNT
#define P0_NETWORK_SERVICE_ACCOUNT "p0ed"
#endif

typedef struct {
    uint8_t network_request[P0_PARAMETER_BATCH_REQUEST_BYTES];
    uint8_t local_request_header[P0_ED_REQUEST_HEADER_BYTES_V2];
    uint8_t local_response[P0_ED_RESPONSE_BYTES];
    uint8_t network_response[P0_IQ_RESPONSE_HEADER_BYTES + P0_ED_RESPONSE_BYTES];
    p0_iq_frame_view_t frame;
} bridge_slot_t;

static volatile sig_atomic_t stop_requested;

static uint32_t load_le32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8U) |
           ((uint32_t)data[2] << 16U) | ((uint32_t)data[3] << 24U);
}

static uint16_t load_le16(const uint8_t *data)
{
    return (uint16_t)data[0] | (uint16_t)((uint16_t)data[1] << 8U);
}

static void store_le16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8U);
}

static void store_le32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8U);
    data[2] = (uint8_t)(value >> 16U);
    data[3] = (uint8_t)(value >> 24U);
}

static void store_le64(uint8_t *data, uint64_t value)
{
    store_le32(data, (uint32_t)value);
    store_le32(data + 4U, (uint32_t)(value >> 32U));
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
    return sigemptyset(&action.sa_mask) == 0 &&
                   sigaction(SIGINT, &action, NULL) == 0 &&
                   sigaction(SIGTERM, &action, NULL) == 0 &&
                   signal(SIGPIPE, SIG_IGN) != SIG_ERR
               ? 0 : -1;
}

static int drop_privileges(void)
{
    struct passwd *account = getpwnam(P0_NETWORK_SERVICE_ACCOUNT);

    if (account == NULL || setgroups(0U, NULL) != 0 ||
        setgid(account->pw_gid) != 0 || setuid(account->pw_uid) != 0)
        return -1;
    return getuid() == account->pw_uid && geteuid() == account->pw_uid &&
                   getgid() == account->pw_gid && getegid() == account->pw_gid
               ? 0 : -1;
}

static int pin_to_network_cpu(void)
{
    cpu_set_t affinity;

    CPU_ZERO(&affinity);
    CPU_SET(0, &affinity);
    return sched_setaffinity(0, sizeof(affinity), &affinity);
}

static int set_io_timeout_seconds(int descriptor, int seconds)
{
    struct timeval timeout;

    timeout.tv_sec = seconds;
    timeout.tv_usec = 0;
    return setsockopt(descriptor, SOL_SOCKET, SO_RCVTIMEO,
                      &timeout, sizeof(timeout)) == 0 &&
                   setsockopt(descriptor, SOL_SOCKET, SO_SNDTIMEO,
                              &timeout, sizeof(timeout)) == 0
               ? 0 : -1;
}

static int set_io_timeouts(int descriptor)
{
    return set_io_timeout_seconds(descriptor, P0_NETWORK_IO_TIMEOUT_SECONDS);
}

static int configure_tcp_client(int descriptor)
{
    int enabled = 1;

    return set_io_timeouts(descriptor) == 0 &&
                   setsockopt(descriptor, IPPROTO_TCP, TCP_NODELAY,
                              &enabled, sizeof(enabled)) == 0
               ? 0 : -1;
}

static int read_exact(int descriptor, uint8_t *buffer, size_t bytes,
                      int allow_clean_eof)
{
    size_t offset = 0U;

    while (offset < bytes) {
        ssize_t count = recv(descriptor, buffer + offset, bytes - offset, 0);

        if (count == 0)
            return allow_clean_eof && offset == 0U ? 1 : -1;
        if (count < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        offset += (size_t)count;
    }
    return 0;
}

static int write_exact(int descriptor, const uint8_t *buffer, size_t bytes)
{
    size_t offset = 0U;

    while (offset < bytes) {
        ssize_t count = send(descriptor, buffer + offset, bytes - offset,
                             MSG_NOSIGNAL);

        if (count < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        if (count == 0)
            return -1;
        offset += (size_t)count;
    }
    return 0;
}

static int read_processing_frame(int client, bridge_slot_t *slot,
                                 int allow_clean_eof)
{
    uint16_t header_bytes;
    uint32_t payload_bytes;
    int status = read_exact(client, slot->network_request, P0_IQ_HEADER_BYTES,
                            allow_clean_eof);

    if (status != 0)
        return status;
    if (memcmp(slot->network_request, "P0CQ", 4U) == 0)
        return p0_iq_capability_query_check(slot->network_request) == 0 ? 5 : -1;
    if (memcmp(slot->network_request, "P0PM", 4U) == 0) {
        p0_parameter_batch_request_t batch;
        if (read_exact(client, slot->network_request + P0_IQ_HEADER_BYTES,
                       P0_PARAMETER_BATCH_REQUEST_BYTES - P0_IQ_HEADER_BYTES, 0) != 0)
            return -1;
        return p0_parameter_batch_decode(slot->network_request, P0_PARAMETER_BATCH_REQUEST_BYTES,
                                         &batch) == 0 ? 3 : -1;
    }
    if (memcmp(slot->network_request, "P0DF", 4U) == 0) {
        p0_df_batch_request_t batch;
        if (read_exact(client, slot->network_request + P0_IQ_HEADER_BYTES,
                       P0_DF_BATCH_REQUEST_BYTES - P0_IQ_HEADER_BYTES, 0) != 0)
            return -1;
        return p0_df_batch_decode(slot->network_request, P0_DF_BATCH_REQUEST_BYTES,
                                  &batch) == 0 ? 4 : -1;
    }
    if (memcmp(slot->network_request, "P0DC", 4U) == 0) {
        p0_detection_message_t message;
        return p0_detection_message_decode(slot->network_request, P0_IQ_HEADER_BYTES,
                                            0, &message) == 0 ? 2 : -1;
    }
    header_bytes = load_le16(slot->network_request + 6U);
    if (memcmp(slot->network_request, "P0IQ", 4U) != 0 ||
        slot->network_request[4] != P0_IQ_TRANSPORT_VERSION ||
        slot->network_request[5] != P0_IQ_SAMPLE_FORMAT_CI8 ||
        (header_bytes != P0_IQ_HEADER_BYTES &&
         header_bytes != P0_IQ_PARAMETER_HEADER_BYTES))
        return -1;
    if (header_bytes > P0_IQ_HEADER_BYTES &&
        read_exact(client, slot->network_request + P0_IQ_HEADER_BYTES,
                   header_bytes - P0_IQ_HEADER_BYTES, 0) != 0)
        return -1;
    payload_bytes = load_le32(slot->network_request + 36U);
    if (payload_bytes != 8192U && payload_bytes != 16384U &&
        payload_bytes != P0_IQ_PROCESSING_MAX_PAYLOAD_BYTES)
        return -1;
    if (read_exact(client, slot->network_request + header_bytes,
                   payload_bytes, 0) != 0)
        return -1;
    return p0_iq_processing_frame_decode(slot->network_request,
                                         header_bytes + payload_bytes,
                                         &slot->frame);
}

static int connect_local_service(const char *socket_path)
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
    if (set_io_timeouts(descriptor) != 0) {
        close(descriptor);
        return -1;
    }
    memset(&address, 0, sizeof(address));
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, socket_path, strlen(socket_path) + 1U);
    if (connect(descriptor, (const struct sockaddr *)&address,
                sizeof(address)) != 0) {
        int saved = errno;
        close(descriptor);
        errno = saved;
        return -1;
    }
    return descriptor;
}

static int submit_local_request(int local, bridge_slot_t *slot,
                                uint32_t *expected_sequence,
                                int *sequence_bound, int *first_request)
{
    uint32_t flags = *first_request ? P0_ED_REQUEST_FLAG_RESET : 0U;
    size_t header_bytes = P0_ED_REQUEST_HEADER_BYTES_V4;
    struct iovec vectors[2];
    struct msghdr message;
    ssize_t sent;

    if (*sequence_bound && slot->frame.sequence_number != *expected_sequence)
        return -1;
    *expected_sequence = slot->frame.sequence_number + 1U;
    *sequence_bound = 1;
    if (slot->frame.parameter_flags != 0U) {
        flags |= P0_ED_REQUEST_FLAG_PARAMETER;
        if ((slot->frame.parameter_flags & P0_IQ_PARAMETER_FLAG_START) != 0U)
            flags |= P0_ED_REQUEST_FLAG_PARAMETER_START;
        header_bytes = P0_ED_REQUEST_HEADER_BYTES_V2;
    }
    memset(slot->local_request_header, 0, sizeof(slot->local_request_header));
    store_le32(slot->local_request_header + 0U, P0_ED_REQUEST_MAGIC);
    store_le16(slot->local_request_header + 4U,
               header_bytes == P0_ED_REQUEST_HEADER_BYTES_V2
                   ? P0_ED_SERVICE_ABI_VERSION_V2
                   : P0_ED_SERVICE_ABI_VERSION_V4);
    store_le16(slot->local_request_header + 6U, (uint16_t)header_bytes);
    store_le32(slot->local_request_header + 8U, (uint32_t)header_bytes +
                                                   slot->frame.payload_bytes);
    store_le32(slot->local_request_header + 12U, slot->frame.frame_id);
    store_le32(slot->local_request_header + 16U, slot->frame.payload_bytes);
    store_le32(slot->local_request_header + 20U, flags);
    if (header_bytes == P0_ED_REQUEST_HEADER_BYTES_V2) {
        store_le32(slot->local_request_header + 24U,
                   p0_ed_crc32(slot->frame.payload, slot->frame.payload_bytes));
        store_le64(slot->local_request_header + 32U,
                   slot->frame.sample_rate_hz);
        store_le64(slot->local_request_header + 40U,
                   slot->frame.center_frequency_hz);
        store_le64(slot->local_request_header + 48U,
                   slot->frame.parameter_intent_id);
        store_le64(slot->local_request_header + 56U,
                   slot->frame.parameter_event_id);
        store_le16(slot->local_request_header + 64U,
                   slot->frame.parameter_lower_shifted_bin);
        store_le16(slot->local_request_header + 66U,
                   slot->frame.parameter_upper_shifted_bin);
        store_le32(slot->local_request_header + 76U,
                   p0_ed_crc32(slot->local_request_header, 76U));
    } else {
        store_le32(slot->local_request_header + 28U,
                   p0_ed_crc32(slot->local_request_header, 28U));
    }
    vectors[0].iov_base = slot->local_request_header;
    vectors[0].iov_len = header_bytes;
    vectors[1].iov_base = (void *)slot->frame.payload;
    vectors[1].iov_len = slot->frame.payload_bytes;
    memset(&message, 0, sizeof(message));
    message.msg_iov = vectors;
    message.msg_iovlen = 2U;
    do {
        sent = sendmsg(local, &message, MSG_NOSIGNAL);
    } while (sent < 0 && errno == EINTR);
    if (sent != (ssize_t)(header_bytes + slot->frame.payload_bytes))
        return -1;
    *first_request = 0;
    return 0;
}

static int complete_local_request(int client, int local, bridge_slot_t *slot)
{
    p0_ed_response_t response;
    size_t network_bytes = 0U;
    ssize_t local_bytes = recv(local, slot->local_response,
                               sizeof(slot->local_response), MSG_TRUNC);

    if (local_bytes <= 0 ||
        (size_t)local_bytes > sizeof(slot->local_response) ||
        p0_ed_response_decode(slot->local_response, (size_t)local_bytes,
                              &response) != 0 ||
        response.frame_id != slot->frame.frame_id ||
        p0_iq_response_encode(
            slot->frame.sequence_number, slot->local_response,
            (size_t)local_bytes, slot->network_response,
            sizeof(slot->network_response), &network_bytes) != 0 ||
        write_exact(client, slot->network_response, network_bytes) != 0)
        return -1;
    return 0;
}

static int serve_peer(int client, const char *local_socket)
{
    bridge_slot_t *slots = calloc(P0_NETWORK_PIPELINE_DEPTH, sizeof(*slots));
    uint32_t expected_sequence = 0U;
    size_t head = 0U;
    size_t tail = 0U;
    size_t outstanding = 0U;
    int sequence_bound = 0;
    int first_request = 1;
    int input_closed = 0;
    int local = -1;
    int result = -1;

    if (slots == NULL)
        return -1;
    local = connect_local_service(local_socket);
    if (local < 0)
        goto done;
    while (!stop_requested) {
        struct pollfd descriptors[2];
        int poll_status;

        if (input_closed && outstanding == 0U) {
            result = 0;
            goto done;
        }
        descriptors[0].fd = client;
        descriptors[0].events = !input_closed &&
                                        outstanding < P0_NETWORK_PIPELINE_DEPTH
                                    ? POLLIN
                                    : 0;
        descriptors[0].revents = 0;
        descriptors[1].fd = local;
        descriptors[1].events = outstanding > 0U ? POLLIN : 0;
        descriptors[1].revents = 0;
        do {
            poll_status = poll(descriptors, 2U,
                               P0_NETWORK_IO_TIMEOUT_SECONDS * 1000);
        } while (poll_status < 0 && errno == EINTR && !stop_requested);
        if (stop_requested)
            break;
        if (poll_status <= 0 ||
            (descriptors[0].revents & (POLLERR | POLLNVAL)) != 0 ||
            (descriptors[1].revents & (POLLERR | POLLNVAL)) != 0 ||
            ((descriptors[1].revents & POLLHUP) != 0 &&
             (descriptors[1].revents & POLLIN) == 0))
            goto done;

        if (!input_closed && outstanding < P0_NETWORK_PIPELINE_DEPTH &&
            (descriptors[0].revents & (POLLIN | POLLHUP)) != 0) {
            int read_status = read_processing_frame(client, &slots[tail], 1);

            if (read_status == 5) {
                uint8_t response[P0_IQ_CAPABILITY_BYTES];
                if (!first_request || outstanding != 0U ||
                    p0_iq_capability_response_encode(response) != 0 ||
                    write_exact(client, response, sizeof(response)) != 0)
                    goto done;
                result = 0;
                goto done;
            } else if (read_status == 3) {
                p0_parameter_batch_request_t batch;
                ssize_t count;
                if (!first_request || outstanding != 0U ||
                    p0_parameter_batch_decode(slots[tail].network_request,
                        P0_PARAMETER_BATCH_REQUEST_BYTES, &batch) != 0) goto done;
                if (set_io_timeout_seconds(client, 30) != 0 ||
                    set_io_timeout_seconds(local, 30) != 0) goto done;
                count = send(local, slots[tail].network_request, P0_PARAMETER_BATCH_REQUEST_BYTES, MSG_NOSIGNAL);
                if (count != P0_PARAMETER_BATCH_REQUEST_BYTES) goto done;
                count = recv(local, slots[tail].local_response, sizeof(slots[tail].local_response), MSG_TRUNC);
                if (p0_parameter_batch_response_check(slots[tail].local_response,
                        (size_t)count, batch.token) != 0 ||
                    write_exact(client, slots[tail].local_response, (size_t)count) != 0) goto done;
                result = 0;
                goto done;
            } else if (read_status == 4) {
                p0_df_batch_request_t batch;
                ssize_t count;
                if (!first_request || outstanding != 0U ||
                    p0_df_batch_decode(slots[tail].network_request,
                        P0_DF_BATCH_REQUEST_BYTES, &batch) != 0) goto done;
                if (set_io_timeout_seconds(client, 10) != 0 ||
                    set_io_timeout_seconds(local, 10) != 0) goto done;
                count = send(local, slots[tail].network_request,
                             P0_DF_BATCH_REQUEST_BYTES, MSG_NOSIGNAL);
                if (count != P0_DF_BATCH_REQUEST_BYTES) goto done;
                count = recv(local, slots[tail].local_response,
                             sizeof(slots[tail].local_response), MSG_TRUNC);
                if (p0_df_batch_response_check(slots[tail].local_response,
                        (size_t)count, batch.token) != 0 ||
                    write_exact(client, slots[tail].local_response,
                                (size_t)count) != 0) goto done;
                result = 0;
                goto done;
            } else if (read_status == 2) {
                p0_detection_message_t request, response;
                ssize_t count;
                if (!first_request || outstanding != 0U ||
                    p0_detection_message_decode(slots[tail].network_request,
                        P0_DETECTION_MESSAGE_BYTES, 0, &request) != 0)
                    goto done;
                count = send(local, slots[tail].network_request, P0_DETECTION_MESSAGE_BYTES, MSG_NOSIGNAL);
                if (count != P0_DETECTION_MESSAGE_BYTES) goto done;
                count = recv(local, slots[tail].local_response, sizeof(slots[tail].local_response), MSG_TRUNC);
                if (count != P0_DETECTION_MESSAGE_BYTES ||
                    p0_detection_message_decode(slots[tail].local_response, (size_t)count, 1, &response) != 0 ||
                    response.request_id != request.request_id || response.operation != request.operation ||
                    write_exact(client, slots[tail].local_response, (size_t)count) != 0)
                    goto done;
                result = 0;
                goto done;
            } else if (read_status == 1) {
                input_closed = 1;
            } else if (read_status != 0 ||
                       submit_local_request(local, &slots[tail],
                                            &expected_sequence, &sequence_bound,
                                            &first_request) != 0) {
                goto done;
            } else {
                tail = (tail + 1U) % P0_NETWORK_PIPELINE_DEPTH;
                ++outstanding;
                continue;
            }
        }

        if (outstanding > 0U && (descriptors[1].revents & POLLIN) != 0) {
            if (complete_local_request(client, local, &slots[head]) != 0)
                goto done;
            head = (head + 1U) % P0_NETWORK_PIPELINE_DEPTH;
            --outstanding;
        }
    }
    result = 0;

done:
    if (local >= 0)
        close(local);
    free(slots);
    return result;
}

static int parse_port(const char *text, uint16_t *port)
{
    char *end = NULL;
    unsigned long value;

    errno = 0;
    value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value < 1024U ||
        value > 65535U)
        return -1;
    *port = (uint16_t)value;
    return 0;
}

int main(int argc, char **argv)
{
    struct sockaddr_in bind_address;
    struct in_addr allowed_peer;
    uint16_t port;
    int enabled = 1;
    int server = -1;
    int result = EXIT_FAILURE;

    if (argc != 5) {
        fprintf(stderr,
                "Kullanım: %s BAGLAMA_IP IZINLI_PC_IP PORT YEREL_SOKET\n",
                argv[0]);
        return EXIT_FAILURE;
    }
    if (inet_pton(AF_INET, argv[1], &bind_address.sin_addr) != 1 ||
        inet_pton(AF_INET, argv[2], &allowed_peer) != 1 ||
        bind_address.sin_addr.s_addr == htonl(INADDR_ANY) ||
        allowed_peer.s_addr == htonl(INADDR_ANY) ||
        parse_port(argv[3], &port) != 0 || install_signal_handlers() != 0) {
        fputs("Ağ köprüsü yapılandırması geçersiz.\n", stderr);
        return EXIT_FAILURE;
    }
    memset(&bind_address, 0, sizeof(bind_address));
    bind_address.sin_family = AF_INET;
    bind_address.sin_port = htons(port);
    if (inet_pton(AF_INET, argv[1], &bind_address.sin_addr) != 1)
        return EXIT_FAILURE;
    server = socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (server < 0 ||
        setsockopt(server, SOL_SOCKET, SO_REUSEADDR, &enabled, sizeof(enabled)) != 0 ||
        bind(server, (const struct sockaddr *)&bind_address,
             sizeof(bind_address)) != 0 ||
        listen(server, 1) != 0) {
        fprintf(stderr, "Ağ dinleyicisi başlatılamadı: %s\n", strerror(errno));
        goto done;
    }
    if (pin_to_network_cpu() != 0 || drop_privileges() != 0) {
        fprintf(stderr, "Ağ köprüsü yetkileri düşürülemedi: %s\n", strerror(errno));
        goto done;
    }
    puts("P0 ED ağ köprüsü hazır.");
    fflush(stdout);
    while (!stop_requested) {
        struct sockaddr_in peer;
        socklen_t peer_bytes = sizeof(peer);
        int client = accept4(server, (struct sockaddr *)&peer, &peer_bytes,
                             SOCK_CLOEXEC);

        if (client < 0) {
            if (errno == EINTR)
                continue;
            goto done;
        }
        if (peer.sin_family != AF_INET || peer.sin_addr.s_addr != allowed_peer.s_addr ||
            configure_tcp_client(client) != 0) {
            close(client);
            continue;
        }
        (void)serve_peer(client, argv[4]);
        close(client);
    }
    result = EXIT_SUCCESS;

done:
    if (server >= 0)
        close(server);
    return result;
}
