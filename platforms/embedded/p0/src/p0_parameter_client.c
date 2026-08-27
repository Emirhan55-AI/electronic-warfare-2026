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

static int parse_u64(const char *text, uint64_t maximum, uint64_t *value)
{
    char *end = NULL;
    unsigned long long parsed = strtoull(text, &end, 10);

    if (end == text || *end != '\0' || parsed > maximum)
        return -1;
    *value = (uint64_t)parsed;
    return 0;
}

static int parse_i64(const char *text, int64_t *value)
{
    char *end = NULL;
    long long parsed = strtoll(text, &end, 10);

    if (end == text || *end != '\0')
        return -1;
    *value = (int64_t)parsed;
    return 0;
}

static const char *state_name(uint8_t state)
{
    if (state == P0_PARAMETER_FIELD_VALID)
        return "valid";
    if (state == P0_PARAMETER_FIELD_INSUFFICIENT_QUALITY)
        return "insufficient_quality";
    if (state == P0_PARAMETER_FIELD_UNCERTAIN)
        return "uncertain";
    return "not_available";
}

static const char *reason_name(uint8_t reason)
{
    static const char *const names[] = {
        "none", "accumulating", "context_lost", "reference_power",
        "reference_mismatch", "excess_power", "center_temporal_uncertainty",
        "span_edge_clipping", "obw_temporal_instability"
    };

    return reason < sizeof(names) / sizeof(names[0]) ? names[reason] : "invalid";
}

static void write_field(FILE *file, const char *name,
                        const p0_parameter_field_t *field, int comma)
{
    fprintf(file, "    \"%s\":{\"state\":\"%s\",\"reason\":\"%s\"",
            name, state_name(field->state), reason_name(field->reason));
    if (field->state == P0_PARAMETER_FIELD_VALID)
        fprintf(file, ",\"value\":%.17g", field->value);
    fprintf(file, "}%s\n", comma ? "," : "");
}

static int write_result(const char *path, const p0_ed_response_t *response)
{
    char *temporary = malloc(strlen(path) + 5U);
    FILE *file = NULL;
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
            ",\n  \"parameter\":{\n"
            "    \"intent_id\":%" PRIu64 ",\n    \"event_id\":%" PRIu64
            ",\n    \"observation_count\":%u,\n",
            response->frame_id, response->raw_candidate_count,
            response->dma_status_flags, response->parameter.intent_id,
            response->parameter.event_id,
            (unsigned int)response->parameter.observation_count);
    write_field(file, "emission_center_frequency_hz",
                &response->parameter.emission_center_frequency_hz, 1);
    write_field(file, "lower_occupied_edge_hz",
                &response->parameter.lower_occupied_edge_hz, 1);
    write_field(file, "upper_occupied_edge_hz",
                &response->parameter.upper_occupied_edge_hz, 1);
    write_field(file, "occupied_bandwidth_hz",
                &response->parameter.occupied_bandwidth_hz, 1);
    write_field(file, "channel_power_dbfs",
                &response->parameter.channel_power_dbfs, 1);
    write_field(file, "snr_estimate_db", &response->parameter.snr_estimate_db, 0);
    fputs("  }\n}\n", file);
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
    const char *socket_path = P0_ED_DEFAULT_SOCKET;
    struct sockaddr_un address;
    struct timeval timeout;
    p0_ed_response_t response;
    uint8_t *request = NULL;
    uint8_t *reply = NULL;
    uint8_t *iq = NULL;
    uint64_t frame_id;
    uint64_t intent_id;
    uint64_t event_id;
    uint64_t sample_rate_hz;
    uint64_t lower;
    uint64_t upper;
    int64_t center_frequency_hz;
    uint32_t flags = P0_ED_REQUEST_FLAG_PARAMETER;
    ssize_t received;
    int descriptor = -1;
    int result = EXIT_FAILURE;
    int argument;
    int socket_overridden = 0;

    if (argc < 10 || argc > 12) {
        fprintf(stderr,
                "Kullanım: %s KARE_ID GIRIS_CI8 SONUC_JSON NIYET_ID OLAY_ID "
                "ORNEKLEME_HZ MERKEZ_HZ ALT_BIN UST_BIN [--start] [YEREL_SOKET]\n",
                argv[0]);
        return EXIT_FAILURE;
    }
    if (parse_u64(argv[1], UINT32_MAX, &frame_id) != 0 ||
        parse_u64(argv[4], UINT64_MAX, &intent_id) != 0 ||
        parse_u64(argv[5], UINT64_MAX, &event_id) != 0 ||
        parse_u64(argv[6], UINT64_MAX, &sample_rate_hz) != 0 ||
        parse_i64(argv[7], &center_frequency_hz) != 0 ||
        parse_u64(argv[8], UINT16_MAX, &lower) != 0 ||
        parse_u64(argv[9], UINT16_MAX, &upper) != 0) {
        fputs("Ölçüm üstverisi geçersiz.\n", stderr);
        return EXIT_FAILURE;
    }
    for (argument = 10; argument < argc; ++argument) {
        if (strcmp(argv[argument], "--start") == 0) {
            if ((flags & P0_ED_REQUEST_FLAG_PARAMETER_START) != 0U) {
                fputs("--start birden fazla kullanılamaz.\n", stderr);
                return EXIT_FAILURE;
            }
            flags |= P0_ED_REQUEST_FLAG_PARAMETER_START;
        } else if (!socket_overridden) {
            socket_path = argv[argument];
            socket_overridden = 1;
        } else {
            fputs("İstemci seçeneği geçersiz.\n", stderr);
            return EXIT_FAILURE;
        }
    }
    if (strlen(socket_path) >= sizeof(address.sun_path)) {
        fputs("Yerel soket yolu çok uzun.\n", stderr);
        return EXIT_FAILURE;
    }
    iq = malloc(P0_ED_IQ_FRAME_BYTES);
    request = malloc(P0_ED_REQUEST_BYTES_V2);
    reply = malloc(P0_ED_RESPONSE_BYTES_V2);
    if (iq == NULL || request == NULL || reply == NULL) {
        fputs("İstemci belleği ayrılamadı.\n", stderr);
        goto done;
    }
    if (read_exact_file(argv[2], iq, P0_ED_IQ_FRAME_BYTES) != 0 ||
        p0_ed_request_encode_v2(
            (uint32_t)frame_id, flags, sample_rate_hz, center_frequency_hz,
            intent_id, event_id, (uint16_t)lower, (uint16_t)upper,
            iq, P0_ED_IQ_FRAME_BYTES, request, P0_ED_REQUEST_BYTES_V2) != 0) {
        fprintf(stderr, "Ölçüm isteği hazırlanamadı: %s\n", strerror(errno));
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
        send(descriptor, request, P0_ED_REQUEST_BYTES_V2, MSG_NOSIGNAL) !=
            (ssize_t)P0_ED_REQUEST_BYTES_V2)
        goto socket_failure;
    received = recv(descriptor, reply, P0_ED_RESPONSE_BYTES_V2, MSG_TRUNC);
    if (received < 0 || p0_ed_response_decode(reply, (size_t)received, &response) != 0) {
        fputs("Kart hizmeti yanıtı doğrulanamadı.\n", stderr);
        goto done;
    }
    if (response.status != P0_ED_SERVICE_OK || response.parameter_present == 0U) {
        fprintf(stderr, "Kart hizmeti ölçümü reddetti: durum=%" PRIu32 "\n",
                response.status);
        goto done;
    }
    if (write_result(argv[3], &response) != 0) {
        fprintf(stderr, "Sonuç yazılamadı: %s\n", strerror(errno));
        goto done;
    }
    printf("P0_PARAMETER_SERVICE_RESULT=PASS\nFRAME_ID=%" PRIu32
           "\nOBSERVATIONS=%u\n",
           response.frame_id, (unsigned int)response.parameter.observation_count);
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
