#define _GNU_SOURCE

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

#include "p0_ed_service_protocol.h"

#define P0_ED_DEFAULT_SOCKET "/run/p0-ed/p0-ed.sock"

static int read_exact_file(const char *path, uint8_t *buffer, size_t bytes)
{
    FILE *file = fopen(path, "rb");
    int extra;

    if (file == NULL)
        return -1;
    if (fread(buffer, 1U, bytes, file) != bytes) {
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

static int write_result(const char *path, const p0_ed_response_t *response)
{
    char *temporary = malloc(strlen(path) + 5U);
    FILE *file;
    uint16_t index;
    int result = -1;

    if (temporary == NULL)
        return -1;
    sprintf(temporary, "%s.tmp", path);
    remove(temporary);
    file = fopen(temporary, "wb");
    if (file == NULL)
        goto done;
    fprintf(file,
            "{\n  \"schema_version\":1,\n  \"frame_id\":%" PRIu32
            ",\n  \"raw_candidate_count\":%" PRIu32
            ",\n  \"dma_status_flags\":%" PRIu32
            ",\n  \"active_count\":%" PRIu16 ",\n  \"ended_count\":%" PRIu16
            ",\n  \"dropped_candidates\":%" PRIu16 ",\n  \"active\":[",
            response->frame_id, response->raw_candidate_count, response->dma_status_flags,
            response->result.active_count, response->result.ended_count,
            response->result.dropped_candidates);
    for (index = 0U; index < response->result.active_count; ++index) {
        if (index != 0U)
            fputc(',', file);
        write_event(file, &response->result.active[index]);
    }
    fputs("],\n  \"ended\":[", file);
    for (index = 0U; index < response->result.ended_count; ++index) {
        if (index != 0U)
            fputc(',', file);
        write_event(file, &response->result.ended[index]);
    }
    fputs("]\n}\n", file);
    if (fclose(file) != 0) {
        file = NULL;
        goto done;
    }
    file = NULL;
    if (rename(temporary, path) != 0)
        goto done;
    result = 0;

done:
    if (file != NULL)
        fclose(file);
    if (result != 0)
        remove(temporary);
    free(temporary);
    return result;
}

int main(int argc, char **argv)
{
    const char *socket_path;
    struct sockaddr_un address;
    struct timeval timeout;
    p0_ed_response_t response;
    uint8_t *request = NULL;
    uint8_t *reply = NULL;
    uint8_t *iq = NULL;
    char *end = NULL;
    unsigned long parsed_frame;
    uint32_t flags = 0U;
    ssize_t received;
    int descriptor = -1;
    int result = EXIT_FAILURE;

    if (argc < 4 || argc > 6) {
        fprintf(stderr, "Kullanım: %s KARE_ID GIRIS_CI8 SONUC_JSON [--reset] [YEREL_SOKET]\n",
                argv[0]);
        return EXIT_FAILURE;
    }
    parsed_frame = strtoul(argv[1], &end, 10);
    if (end == argv[1] || *end != '\0' || parsed_frame > UINT32_MAX) {
        fputs("Kare kimliği geçersiz.\n", stderr);
        return EXIT_FAILURE;
    }
    if (argc >= 5 && strcmp(argv[4], "--reset") == 0)
        flags = P0_ED_REQUEST_FLAG_RESET;
    else if (argc >= 5 && argv[4][0] == '-') {
        fputs("İstemci seçeneği geçersiz.\n", stderr);
        return EXIT_FAILURE;
    }
    socket_path = argc == 6 ? argv[5] :
                  (argc == 5 && flags == 0U ? argv[4] : P0_ED_DEFAULT_SOCKET);
    if (strlen(socket_path) >= sizeof(address.sun_path)) {
        fputs("Yerel soket yolu çok uzun.\n", stderr);
        return EXIT_FAILURE;
    }
    iq = malloc(P0_ED_IQ_FRAME_BYTES);
    request = malloc(P0_ED_REQUEST_BYTES);
    reply = malloc(P0_ED_RESPONSE_BYTES);
    if (iq == NULL || request == NULL || reply == NULL) {
        fputs("İstemci belleği ayrılamadı.\n", stderr);
        goto done;
    }
    if (read_exact_file(argv[2], iq, P0_ED_IQ_FRAME_BYTES) != 0 ||
        p0_ed_request_encode((uint32_t)parsed_frame, flags, iq, P0_ED_IQ_FRAME_BYTES,
                             request, P0_ED_REQUEST_BYTES) != 0) {
        fprintf(stderr, "I/Q çerçevesi hazırlanamadı: %s\n", strerror(errno));
        goto done;
    }
    descriptor = socket(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC, 0);
    if (descriptor < 0)
        goto socket_failure;
    timeout.tv_sec = 3;
    timeout.tv_usec = 0;
    if (setsockopt(descriptor, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) != 0 ||
        setsockopt(descriptor, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout)) != 0)
        goto socket_failure;
    memset(&address, 0, sizeof(address));
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, socket_path, strlen(socket_path) + 1U);
    if (connect(descriptor, (const struct sockaddr *)&address, sizeof(address)) != 0 ||
        send(descriptor, request, P0_ED_REQUEST_BYTES, MSG_NOSIGNAL) !=
            (ssize_t)P0_ED_REQUEST_BYTES)
        goto socket_failure;
    received = recv(descriptor, reply, P0_ED_RESPONSE_BYTES, MSG_TRUNC);
    if (received < 0 || p0_ed_response_decode(reply, (size_t)received, &response) != 0) {
        fputs("Kart hizmeti yanıtı doğrulanamadı.\n", stderr);
        goto done;
    }
    if (response.status != P0_ED_SERVICE_OK) {
        fprintf(stderr, "Kart hizmeti isteği reddetti: durum=%" PRIu32 "\n", response.status);
        goto done;
    }
    if (write_result(argv[3], &response) != 0) {
        fprintf(stderr, "Sonuç yazılamadı: %s\n", strerror(errno));
        goto done;
    }
    printf("P0_ED_SERVICE_RESULT=PASS\nFRAME_ID=%" PRIu32
           "\nRAW_CANDIDATES=%" PRIu32 "\nACTIVE=%" PRIu16 "\nENDED=%" PRIu16 "\n",
           response.frame_id, response.raw_candidate_count, response.result.active_count,
           response.result.ended_count);
    result = EXIT_SUCCESS;
    goto done;

socket_failure:
    fprintf(stderr, "Kart hizmetine bağlanılamadı: %s\n", strerror(errno));
done:
    if (descriptor >= 0)
        close(descriptor);
    free(reply);
    free(request);
    free(iq);
    return result;
}
