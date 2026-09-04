#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "p0_ed_pipeline.h"

static uint32_t load_le32(const uint8_t bytes[4])
{
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8U) |
           ((uint32_t)bytes[2] << 16U) | ((uint32_t)bytes[3] << 24U);
}

int main(int argc, char **argv)
{
    FILE *input;
    p0_ed_pipeline_t pipeline;
    uint8_t length_bytes[4];
    uint8_t *packet = NULL;
    size_t capacity = 0U;
    unsigned int packet_index = 0U;

    if (argc != 2)
        return 2;
    input = fopen(argv[1], "rb");
    if (input == NULL || p0_ed_pipeline_init(&pipeline) != 0)
        return 3;

    while (fread(length_bytes, 1U, sizeof(length_bytes), input) == sizeof(length_bytes)) {
        uint32_t packet_bytes = load_le32(length_bytes);
        phase06j_frame_result_v1 result;
        size_t raw_candidate_count = 0U;
        uint32_t frame_id = 0U;
        phase06j_event_v1 empty_event = {0};
        const phase06j_event_v1 *active = result.active;
        const phase06j_event_v1 *last_active = result.active;
        const phase06j_event_v1 *ended = result.ended;

        if (packet_bytes == 0U || packet_bytes > PHASE06I_MAX_FRAME_BYTES) {
            fclose(input);
            p0_ed_pipeline_release(&pipeline);
            free(packet);
            return 4;
        }
        if (packet_bytes > capacity) {
            uint8_t *expanded = realloc(packet, packet_bytes);
            if (expanded == NULL) {
                fclose(input);
                p0_ed_pipeline_release(&pipeline);
                free(packet);
                return 5;
            }
            packet = expanded;
            capacity = packet_bytes;
        }
        if (fread(packet, 1U, packet_bytes, input) != packet_bytes ||
            p0_ed_pipeline_process_packet(
                &pipeline, packet_index == 0U, packet, packet_bytes, &result,
                &raw_candidate_count, &frame_id) != 0) {
            fclose(input);
            p0_ed_pipeline_release(&pipeline);
            free(packet);
            return 6;
        }
        if (result.active_count == 0U) {
            active = &empty_event;
            last_active = &empty_event;
        } else {
            last_active = &result.active[result.active_count - 1U];
        }
        if (result.ended_count == 0U)
            ended = &empty_event;
        printf("%u,%zu,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\n",
               frame_id, raw_candidate_count, result.active_count,
               result.ended_count, result.reset_applied, active->state,
               active->candidate.flags, active->candidate.peak_shifted_bin,
               ended->state, ended->candidate.peak_shifted_bin,
               result.dropped_candidates,
               last_active->candidate.peak_shifted_bin);
        ++packet_index;
    }
    if (!feof(input)) {
        fclose(input);
        p0_ed_pipeline_release(&pipeline);
        free(packet);
        return 7;
    }
    fclose(input);
    p0_ed_pipeline_release(&pipeline);
    free(packet);
    return 0;
}
