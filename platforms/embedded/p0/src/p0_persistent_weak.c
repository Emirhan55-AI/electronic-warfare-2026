#include "p0_persistent_weak.h"

#include <string.h>

#define P0_WEAK_STATE_MAGIC UINT32_C(0x4B575030)
#define P0_WEAK_EVALUATED_FIRST 20u
#define P0_WEAK_EVALUATED_LAST 4075u
#define P0_WEAK_RING_MAX_BINS \
  (P0_WEAK_MAX_TRACKED_PER_FRAME * \
   (2u * P0_WEAK_PEAK_TOLERANCE_BINS + 1u))

typedef struct {
  uint32_t magic;
  uint16_t frame_count;
  uint16_t write_index;
  uint16_t counts[P0_WEAK_FFT_SIZE];
  uint32_t ratio_sums[P0_WEAK_FFT_SIZE];
  uint16_t exact_counts[P0_WEAK_FFT_SIZE];
  uint32_t exact_ratio_sums[P0_WEAK_FFT_SIZE];
  uint16_t ratio_work[P0_WEAK_FFT_SIZE];
  uint16_t ratio_ring_count[P0_WEAK_WINDOW_FRAMES];
  uint16_t ratio_ring_bin[P0_WEAK_WINDOW_FRAMES][P0_WEAK_RING_MAX_BINS];
  uint16_t ratio_ring_value[P0_WEAK_WINDOW_FRAMES][P0_WEAK_RING_MAX_BINS];
  uint16_t exact_count_ring[P0_WEAK_WINDOW_FRAMES];
  uint16_t exact_peak_ring[P0_WEAK_WINDOW_FRAMES]
                          [P0_WEAK_MAX_TRACKED_PER_FRAME];
  uint16_t exact_ratio_ring[P0_WEAK_WINDOW_FRAMES]
                           [P0_WEAK_MAX_TRACKED_PER_FRAME];
} p0_persistent_weak_state_t;

static uint16_t ratio_q8(uint64_t numerator, uint64_t denominator) {
  uint64_t whole;
  uint64_t remainder;
  uint16_t fraction = 0u;
  unsigned bit;
  if (denominator == 0u) return numerator == 0u ? 0u : UINT16_MAX;
  whole = numerator / denominator;
  if (whole >= 256u) return UINT16_MAX;
  remainder = numerator % denominator;
  for (bit = 0u; bit < 8u; ++bit) {
    remainder <<= 1u;
    fraction <<= 1u;
    if (remainder >= denominator) {
      remainder -= denominator;
      fraction |= 1u;
    }
  }
  return (uint16_t)((whole << 8u) | fraction);
}

size_t p0_persistent_weak_state_bytes(void) {
  return sizeof(p0_persistent_weak_state_t);
}

int p0_persistent_weak_last_seen_age(const void *memory, size_t bytes, uint16_t peak) {
  const p0_persistent_weak_state_t *state = memory;
  uint16_t age;
  if (!state || bytes < sizeof(*state) || state->magic != P0_WEAK_STATE_MAGIC ||
      peak >= P0_WEAK_FFT_SIZE) return -1;
  for (age = 0; age < state->frame_count; ++age) {
    uint16_t slot = (uint16_t)((state->write_index + P0_WEAK_WINDOW_FRAMES - 1u - age)
                              % P0_WEAK_WINDOW_FRAMES);
    uint16_t index;
    for (index = 0; index < state->exact_count_ring[slot]; ++index) {
      int delta = (int)state->exact_peak_ring[slot][index] - (int)peak;
      if (delta >= -(int)P0_WEAK_PEAK_TOLERANCE_BINS &&
          delta <= (int)P0_WEAK_PEAK_TOLERANCE_BINS) return age;
    }
  }
  return -1;
}

int p0_persistent_weak_init(void *memory, size_t bytes) {
  p0_persistent_weak_state_t *state = (p0_persistent_weak_state_t *)memory;
  if (state == NULL || bytes < sizeof(*state)) return -1;
  memset(state, 0, sizeof(*state));
  state->magic = P0_WEAK_STATE_MAGIC;
  return 0;
}

static int validate_nomination(const p0_weak_nomination_v1 *item) {
  return item->reserved == 0u &&
         item->start_shifted_bin >= P0_WEAK_EVALUATED_FIRST &&
         item->start_shifted_bin <= item->peak_shifted_bin &&
         item->peak_shifted_bin <= item->end_shifted_bin &&
         item->end_shifted_bin <= P0_WEAK_EVALUATED_LAST;
}

#define P0_WEAK_CHECKPOINT_MAGIC UINT32_C(0x57435032)
#define P0_WEAK_CHECKPOINT_CELLS (2u * P0_WEAK_RING_MAX_BINS + P0_WEAK_MAX_TRACKED_PER_FRAME)
typedef struct {
  uint16_t bin, count, exact_count;
  uint32_t sum, exact_sum;
} p0_weak_saved_cell_t;
typedef struct {
  uint32_t magic;
  uint16_t frame_count, write_index, cells, row_count, exact_count;
  uint16_t row_bin[P0_WEAK_RING_MAX_BINS], row_value[P0_WEAK_RING_MAX_BINS];
  uint16_t exact_peak[P0_WEAK_MAX_TRACKED_PER_FRAME], exact_ratio[P0_WEAK_MAX_TRACKED_PER_FRAME];
  p0_weak_saved_cell_t cell[P0_WEAK_CHECKPOINT_CELLS];
} p0_weak_checkpoint_t;

size_t p0_persistent_weak_checkpoint_bytes(void) { return sizeof(p0_weak_checkpoint_t); }

static void save_cell(const p0_persistent_weak_state_t *state,
                      p0_weak_checkpoint_t *backup, uint16_t bin) {
  p0_weak_saved_cell_t *cell = &backup->cell[backup->cells++];
  cell->bin = bin;
  cell->count = state->counts[bin];
  cell->sum = state->ratio_sums[bin];
  cell->exact_count = state->exact_counts[bin];
  cell->exact_sum = state->exact_ratio_sums[bin];
}

int p0_persistent_weak_checkpoint_save(const void *memory, size_t bytes,
    const p0_weak_nomination_v1 *nominations, uint16_t count, void *target, size_t target_bytes) {
  const p0_persistent_weak_state_t *state = memory;
  p0_weak_checkpoint_t *backup = target;
  uint16_t index, slot;
  if (!state || !backup || bytes < sizeof(*state) || target_bytes < sizeof(*backup) ||
      state->magic != P0_WEAK_STATE_MAGIC || state->write_index >= P0_WEAK_WINDOW_FRAMES ||
      count > P0_WEAK_MAX_TRACKED_PER_FRAME || (count && !nominations)) return -1;
  for (index = 0; index < count; ++index) {
    if (!validate_nomination(&nominations[index]) || (index &&
        nominations[index].start_shifted_bin <= nominations[index - 1u].end_shifted_bin)) return -2;
  }
  slot = state->write_index;
  backup->magic = P0_WEAK_CHECKPOINT_MAGIC;
  backup->frame_count = state->frame_count;
  backup->write_index = slot;
  backup->cells = 0;
  backup->row_count = state->ratio_ring_count[slot];
  backup->exact_count = state->exact_count_ring[slot];
  memcpy(backup->row_bin, state->ratio_ring_bin[slot], sizeof(backup->row_bin));
  memcpy(backup->row_value, state->ratio_ring_value[slot], sizeof(backup->row_value));
  memcpy(backup->exact_peak, state->exact_peak_ring[slot], sizeof(backup->exact_peak));
  memcpy(backup->exact_ratio, state->exact_ratio_ring[slot], sizeof(backup->exact_ratio));
  /* Duplicates are harmless: every snapshot precedes the update. Avoid a search. */
  for (index = 0; index < backup->row_count; ++index) save_cell(state, backup, backup->row_bin[index]);
  for (index = 0; index < backup->exact_count; ++index) save_cell(state, backup, backup->exact_peak[index]);
  for (index = 0; index < count; ++index) {
    uint16_t peak = nominations[index].peak_shifted_bin;
    uint16_t first = peak - P0_WEAK_PEAK_TOLERANCE_BINS;
    uint16_t last = peak + P0_WEAK_PEAK_TOLERANCE_BINS;
    uint16_t bin;
    if (first < P0_WEAK_EVALUATED_FIRST) first = P0_WEAK_EVALUATED_FIRST;
    if (last > P0_WEAK_EVALUATED_LAST) last = P0_WEAK_EVALUATED_LAST;
    for (bin = first; bin <= last; ++bin) save_cell(state, backup, bin);
  }
  return 0;
}

int p0_persistent_weak_checkpoint_restore(void *memory, size_t bytes,
    const void *source, size_t source_bytes) {
  p0_persistent_weak_state_t *state = memory;
  const p0_weak_checkpoint_t *backup = source;
  uint16_t index, slot;
  if (!state || !backup || bytes < sizeof(*state) || source_bytes < sizeof(*backup) ||
      state->magic != P0_WEAK_STATE_MAGIC || backup->magic != P0_WEAK_CHECKPOINT_MAGIC ||
      backup->write_index >= P0_WEAK_WINDOW_FRAMES || backup->cells > P0_WEAK_CHECKPOINT_CELLS) return -1;
  for (index = 0; index < backup->cells; ++index) if (backup->cell[index].bin >= P0_WEAK_FFT_SIZE) return -1;
  slot = backup->write_index;
  state->frame_count = backup->frame_count;
  state->write_index = slot;
  state->ratio_ring_count[slot] = backup->row_count;
  state->exact_count_ring[slot] = backup->exact_count;
  memcpy(state->ratio_ring_bin[slot], backup->row_bin, sizeof(backup->row_bin));
  memcpy(state->ratio_ring_value[slot], backup->row_value, sizeof(backup->row_value));
  memcpy(state->exact_peak_ring[slot], backup->exact_peak, sizeof(backup->exact_peak));
  memcpy(state->exact_ratio_ring[slot], backup->exact_ratio, sizeof(backup->exact_ratio));
  for (index = 0; index < backup->cells; ++index) {
    const p0_weak_saved_cell_t *cell = &backup->cell[index];
    state->counts[cell->bin] = cell->count;
    state->ratio_sums[cell->bin] = cell->sum;
    state->exact_counts[cell->bin] = cell->exact_count;
    state->exact_ratio_sums[cell->bin] = cell->exact_sum;
  }
  /* Reconstruct the scratch row exactly from the previous completed ring slot. */
  memset(state->ratio_work, 0, sizeof(state->ratio_work));
  if (state->frame_count) {
    slot = (uint16_t)((slot + P0_WEAK_WINDOW_FRAMES - 1u) % P0_WEAK_WINDOW_FRAMES);
    for (index = 0; index < state->ratio_ring_count[slot]; ++index)
      state->ratio_work[state->ratio_ring_bin[slot][index]] = state->ratio_ring_value[slot][index];
  }
  return 0;
}

static uint16_t choose_peak(const p0_persistent_weak_state_t *state,
                            uint16_t start, uint16_t end) {
  uint16_t peak = start;
  uint16_t index;
  for (index = (uint16_t)(start + 1u); index <= end; ++index) {
    uint64_t left = (uint64_t)state->exact_ratio_sums[index] *
                    state->exact_counts[peak];
    uint64_t right = (uint64_t)state->exact_ratio_sums[peak] *
                     state->exact_counts[index];
    if (state->exact_counts[index] > state->exact_counts[peak] ||
        (state->exact_counts[index] == state->exact_counts[peak] && left > right) ||
        (state->exact_counts[index] == state->exact_counts[peak] && left == right &&
         state->counts[index] > state->counts[peak])) {
      peak = index;
    }
  }
  return peak;
}

static int emit_results(const p0_persistent_weak_state_t *state,
                        p0_persistent_weak_result_v1 *result) {
  uint16_t index = P0_WEAK_EVALUATED_FIRST;
  memset(result, 0, sizeof(*result));
  if (state->frame_count < P0_WEAK_WINDOW_FRAMES) return 0;
  while (index <= P0_WEAK_EVALUATED_LAST) {
    uint16_t start;
    uint16_t end;
    uint16_t peak;
    p0_persistent_weak_candidate_v1 *output;
    if (state->counts[index] < P0_WEAK_REQUIRED_FRAMES) {
      ++index;
      continue;
    }
    start = end = index;
    while (end < P0_WEAK_EVALUATED_LAST) {
      uint16_t next = (uint16_t)(end + 1u);
      if (state->counts[next] >= P0_WEAK_REQUIRED_FRAMES) {
        end = next;
      } else if (next < P0_WEAK_EVALUATED_LAST &&
                 state->counts[next + 1u] >= P0_WEAK_REQUIRED_FRAMES) {
        end = (uint16_t)(next + 1u);
      } else {
        break;
      }
    }
    if (result->count >= P0_WEAK_MAX_RESULTS) return -4;
    peak = choose_peak(state, start, end);
    output = &result->candidates[result->count++];
    output->start_shifted_bin = start;
    output->end_shifted_bin = end;
    output->peak_shifted_bin = peak;
    output->observed_frames = state->counts[peak];
    output->total_frames = P0_WEAK_WINDOW_FRAMES;
    output->mean_ratio_q8 = state->exact_counts[peak] == 0u ? 0u : (uint16_t)(
        state->exact_ratio_sums[peak] / state->exact_counts[peak]);
    index = (uint16_t)(end + 1u);
  }
  return 0;
}

int p0_persistent_weak_update(
    void *memory, size_t bytes,
    const p0_weak_nomination_v1 *nominations, uint16_t nomination_count,
    p0_persistent_weak_result_v1 *result) {
  p0_persistent_weak_state_t *state = (p0_persistent_weak_state_t *)memory;
  uint16_t *row;
  uint16_t sparse_count = 0u;
  uint16_t index;
  if (state == NULL || result == NULL || bytes < sizeof(*state) ||
      state->magic != P0_WEAK_STATE_MAGIC ||
      nomination_count > P0_WEAK_MAX_NOMINATIONS ||
      nomination_count > P0_WEAK_MAX_TRACKED_PER_FRAME ||
      (nomination_count != 0u && nominations == NULL)) return -1;
  for (index = 0u; index < nomination_count; ++index) {
    if (!validate_nomination(&nominations[index]) ||
        (index != 0u && nominations[index].start_shifted_bin <=
                            nominations[index - 1u].end_shifted_bin)) return -2;
  }
  row = state->ratio_work;
  if (state->frame_count == P0_WEAK_WINDOW_FRAMES) {
    for (index = 0u; index < state->ratio_ring_count[state->write_index]; ++index) {
      uint16_t bin = state->ratio_ring_bin[state->write_index][index];
      uint16_t value = state->ratio_ring_value[state->write_index][index];
      --state->counts[bin];
      state->ratio_sums[bin] -= value;
    }
    for (index = 0u; index < state->exact_count_ring[state->write_index]; ++index) {
      uint16_t peak = state->exact_peak_ring[state->write_index][index];
      uint16_t value = state->exact_ratio_ring[state->write_index][index];
      --state->exact_counts[peak];
      state->exact_ratio_sums[peak] -= value;
    }
  } else {
    ++state->frame_count;
  }
  if (state->frame_count != 0u) {
    uint16_t previous_slot = (uint16_t)(
        (state->write_index + P0_WEAK_WINDOW_FRAMES - 1u) % P0_WEAK_WINDOW_FRAMES);
    for (index = 0u; index < state->ratio_ring_count[previous_slot]; ++index)
      row[state->ratio_ring_bin[previous_slot][index]] = 0u;
  }
  state->exact_count_ring[state->write_index] = nomination_count;
  for (index = 0u; index < nomination_count; ++index) {
    const p0_weak_nomination_v1 *item = &nominations[index];
    uint16_t start = item->peak_shifted_bin > P0_WEAK_PEAK_TOLERANCE_BINS
        ? (uint16_t)(item->peak_shifted_bin - P0_WEAK_PEAK_TOLERANCE_BINS)
        : P0_WEAK_EVALUATED_FIRST;
    uint16_t end = (uint16_t)(item->peak_shifted_bin + P0_WEAK_PEAK_TOLERANCE_BINS);
    uint16_t value = ratio_q8(item->peak_power, item->order_statistic);
    uint16_t bin;
    state->exact_peak_ring[state->write_index][index] = item->peak_shifted_bin;
    state->exact_ratio_ring[state->write_index][index] = value;
    ++state->exact_counts[item->peak_shifted_bin];
    state->exact_ratio_sums[item->peak_shifted_bin] += value;
    if (start < P0_WEAK_EVALUATED_FIRST) start = P0_WEAK_EVALUATED_FIRST;
    if (end > P0_WEAK_EVALUATED_LAST) end = P0_WEAK_EVALUATED_LAST;
    if (value == 0u) continue;
    for (bin = start; bin <= end; ++bin) {
      if (row[bin] == 0u) {
        state->ratio_ring_bin[state->write_index][sparse_count++] = bin;
      }
      if (value > row[bin]) row[bin] = value;
    }
  }
  state->ratio_ring_count[state->write_index] = sparse_count;
  for (index = 0u; index < sparse_count; ++index) {
    uint16_t bin = state->ratio_ring_bin[state->write_index][index];
    uint16_t value = row[bin];
    state->ratio_ring_value[state->write_index][index] = value;
    ++state->counts[bin];
    state->ratio_sums[bin] += value;
  }
  state->write_index = (uint16_t)(
      (state->write_index + 1u) % P0_WEAK_WINDOW_FRAMES);
  return emit_results(state, result);
}
