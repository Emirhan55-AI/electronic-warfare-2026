#include "p0_persistent_weak.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
  void *state = calloc(1u, p0_persistent_weak_state_bytes());
  p0_persistent_weak_result_v1 result;
  unsigned frame_count;
  unsigned frame;
  if (state == NULL || scanf("%u", &frame_count) != 1 ||
      p0_persistent_weak_init(state, p0_persistent_weak_state_bytes()) != 0) {
    free(state);
    return 2;
  }
  for (frame = 0u; frame < frame_count; ++frame) {
    unsigned count;
    unsigned index;
    p0_weak_nomination_v1 *items;
    int code;
    if (scanf("%u", &count) != 1 || count > UINT16_MAX) {
      free(state);
      return 3;
    }
    items = count == 0u ? NULL : calloc(count, sizeof(*items));
    if (count != 0u && items == NULL) {
      free(state);
      return 4;
    }
    for (index = 0u; index < count; ++index) {
      unsigned start;
      unsigned end;
      unsigned peak;
      if (scanf("%u %u %u %" SCNu64 " %" SCNu64,
                &start, &end, &peak, &items[index].peak_power,
                &items[index].order_statistic) != 5 ||
          start > UINT16_MAX || end > UINT16_MAX || peak > UINT16_MAX) {
        free(items);
        free(state);
        return 5;
      }
      items[index].start_shifted_bin = (uint16_t)start;
      items[index].end_shifted_bin = (uint16_t)end;
      items[index].peak_shifted_bin = (uint16_t)peak;
    }
    code = p0_persistent_weak_update(
        state, p0_persistent_weak_state_bytes(), items, (uint16_t)count, &result);
    free(items);
    if (code != 0) {
      free(state);
      return 6;
    }
  }
  for (frame = 0u; frame < result.count; ++frame) {
    const p0_persistent_weak_candidate_v1 *item = &result.candidates[frame];
    printf("%u,%u,%u,%u,%u,%u\n", item->start_shifted_bin,
           item->end_shifted_bin, item->peak_shifted_bin,
           item->observed_frames, item->total_frames, item->mean_ratio_q8);
  }
  free(state);
  return 0;
}
