#include "p0_multiframe_narrowband.h"

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    FILE *stream;
    double *power;
    p0_multiframe_narrowband_candidate_t candidates[16];
    size_t frame_count;
    size_t bin_count;
    double sample_rate_hz;
    size_t first_bin;
    size_t last_bin;
    size_t candidate_count = 0u;
    size_t index;
    int code;
    if (argc != 7) {
        return 2;
    }
    frame_count = (size_t)strtoul(argv[2], NULL, 10);
    bin_count = (size_t)strtoul(argv[3], NULL, 10);
    sample_rate_hz = strtod(argv[4], NULL);
    first_bin = (size_t)strtoul(argv[5], NULL, 10);
    last_bin = (size_t)strtoul(argv[6], NULL, 10);
    if (frame_count == 0u || bin_count == 0u || frame_count > ((size_t)-1) / bin_count) {
        return 2;
    }
    power = malloc(frame_count * bin_count * sizeof(*power));
    if (power == NULL) {
        return 3;
    }
    stream = fopen(argv[1], "rb");
    if (stream == NULL || fread(power, sizeof(*power), frame_count * bin_count, stream)
            != frame_count * bin_count) {
        if (stream != NULL) fclose(stream);
        free(power);
        return 4;
    }
    fclose(stream);
    code = p0_multiframe_narrowband_process(
        power, frame_count, bin_count, sample_rate_hz, first_bin, last_bin,
        candidates, 16u, &candidate_count
    );
    free(power);
    if (code != P0_MFNB_OK) {
        return 5;
    }
    for (index = 0u; index < candidate_count; ++index) {
        const p0_multiframe_narrowband_candidate_t *item = &candidates[index];
        printf("%.12f,%u,%u,%u,%.12f,%u,%u,%u\n",
               item->center_bin, item->peak_bin, item->lower_bin, item->upper_bin,
               item->peak_to_noise_db, item->observed_frames, item->total_frames,
               item->component_count);
    }
    return 0;
}
