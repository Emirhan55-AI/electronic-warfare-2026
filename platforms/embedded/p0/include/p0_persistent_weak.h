#ifndef P0_PERSISTENT_WEAK_H
#define P0_PERSISTENT_WEAK_H

#include <stddef.h>
#include <stdint.h>

#define P0_WEAK_FFT_SIZE 4096u
#define P0_WEAK_WINDOW_FRAMES 32u
#define P0_WEAK_REQUIRED_FRAMES 24u
#define P0_WEAK_PEAK_TOLERANCE_BINS 2u
#define P0_WEAK_MAX_NOMINATIONS 1352u
#define P0_WEAK_MAX_RESULTS 64u
#define P0_WEAK_MAX_TRACKED_PER_FRAME 8u
#define P0_WEAK_MAX_EMITTED 8u

typedef struct {
  uint16_t start_shifted_bin;
  uint16_t end_shifted_bin;
  uint16_t peak_shifted_bin;
  uint16_t reserved;
  uint64_t peak_power;
  uint64_t order_statistic;
} p0_weak_nomination_v1;

typedef struct {
  uint16_t start_shifted_bin;
  uint16_t end_shifted_bin;
  uint16_t peak_shifted_bin;
  uint16_t observed_frames;
  uint16_t total_frames;
  uint16_t mean_ratio_q8;
} p0_persistent_weak_candidate_v1;

typedef struct {
  uint16_t count;
  p0_persistent_weak_candidate_v1 candidates[P0_WEAK_MAX_RESULTS];
} p0_persistent_weak_result_v1;

size_t p0_persistent_weak_state_bytes(void);
int p0_persistent_weak_init(void *memory, size_t bytes);
int p0_persistent_weak_update(
    void *memory, size_t bytes,
    const p0_weak_nomination_v1 *nominations, uint16_t nomination_count,
    p0_persistent_weak_result_v1 *result);

#endif
