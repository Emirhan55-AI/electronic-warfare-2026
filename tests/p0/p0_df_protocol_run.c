#define _CRT_SECURE_NO_WARNINGS

#include "p0_ed_service_protocol.h"

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    uint8_t *request_bytes;
    uint8_t response_bytes[P0_DF_BATCH_RESPONSE_BYTES];
    p0_df_batch_request_t request;
    p0_df_result_t result;
    FILE *stream;
    int code;
    if (argc != 3) return 2;
    request_bytes = malloc(P0_DF_BATCH_REQUEST_BYTES);
    if (request_bytes == NULL) return 2;
    stream = fopen(argv[1], "rb");
    if (stream == NULL || fread(request_bytes, 1U, P0_DF_BATCH_REQUEST_BYTES, stream) !=
                              P0_DF_BATCH_REQUEST_BYTES || fgetc(stream) != EOF) {
        if (stream != NULL) fclose(stream);
        free(request_bytes);
        return 2;
    }
    fclose(stream);
    if (p0_df_batch_decode(request_bytes, P0_DF_BATCH_REQUEST_BYTES, &request) != 0) {
        free(request_bytes);
        return 3;
    }
    free(request_bytes);
    code = p0_amplitude_df_estimate(
        request.measurements, request.measurement_count,
        p0_amplitude_df_field_profile(), &result);
    if (code != 0 || p0_df_batch_response_encode(
            &request, P0_DF_BATCH_OK, &result, response_bytes) != 0 ||
        p0_df_batch_response_check(response_bytes, sizeof(response_bytes), request.token) != 0)
        return 4;
    stream = fopen(argv[2], "wb");
    if (stream == NULL || fwrite(response_bytes, 1U, sizeof(response_bytes), stream) !=
                              sizeof(response_bytes) || fclose(stream) != 0)
        return 5;
    puts("P0_DF_PROTOCOL=PASS");
    return 0;
}
