#include "phase06j_temporal.h"

#include <limits.h>
#include <string.h>

#define PHASE06J_STATE_MAGIC 0x4A363050u

typedef struct {
  uint16_t start_bin;
  uint16_t end_bin;
  uint16_t peak_bin;
  uint16_t span_bins;
  uint8_t pfa_select;
  uint8_t evaluate_center;
  uint64_t peak_power;
  uint64_t noise_power;
  uint64_t threshold_power;
} candidate_t;

typedef struct {
  uint64_t event_id;
  uint32_t first_frame_id;
  uint32_t last_seen_frame_id;
  uint64_t seen_count;
  candidate_t candidate;
  uint8_t history[PHASE06J_CONFIRMATION_WINDOW];
  uint8_t history_length;
  uint8_t consecutive_misses;
  uint8_t confirmed;
  uint8_t observed;
} track_t;

typedef struct {
  const uint8_t *payload;
  uint32_t frame_id;
  uint16_t candidate_count;
} packet_view_t;

typedef struct {
  candidate_t candidate;
  int overlap;
  uint16_t distance;
  uint16_t region_index;
  uint8_t valid;
} match_choice_t;

typedef struct {
  uint32_t magic;
  uint8_t has_last_frame;
  uint8_t reserved[3];
  uint32_t last_frame_id;
  uint64_t next_event_id;
  uint16_t track_count;
  uint16_t ended_count;
  uint16_t ended_start;
  uint16_t reserved2;
  uint64_t evicted_history_count;
  track_t tracks[PHASE06J_MAX_ACTIVE_TRACKS];
  phase06j_event_v1 ended_history[PHASE06J_MAX_ENDED_HISTORY];
} state_t;

typedef struct {
  uint64_t high;
  uint64_t low;
} uint128_pair_t;

static uint16_t read_le16(const uint8_t *p) {
  return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t read_le32(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
         ((uint32_t)p[3] << 24);
}

static uint64_t read_le64(const uint8_t *p) {
  return (uint64_t)read_le32(p) | ((uint64_t)read_le32(p + 4) << 32);
}

static uint32_t crc32_ieee(const uint8_t *data, size_t length) {
  static const uint32_t table[16] = {
      UINT32_C(0x00000000), UINT32_C(0x1DB71064), UINT32_C(0x3B6E20C8),
      UINT32_C(0x26D930AC), UINT32_C(0x76DC4190), UINT32_C(0x6B6B51F4),
      UINT32_C(0x4DB26158), UINT32_C(0x5005713C), UINT32_C(0xEDB88320),
      UINT32_C(0xF00F9344), UINT32_C(0xD6D6A3E8), UINT32_C(0xCB61B38C),
      UINT32_C(0x9B64C2B0), UINT32_C(0x86D3D2D4), UINT32_C(0xA00AE278),
      UINT32_C(0xBDBDF21C),
  };
  uint32_t crc = UINT32_MAX;
  size_t i;
  for (i = 0; i < length; ++i) {
    crc ^= data[i];
    crc = (crc >> 4) ^ table[crc & 0x0fu];
    crc = (crc >> 4) ^ table[crc & 0x0fu];
  }
  return crc ^ UINT32_MAX;
}

static int all_zero(const uint8_t *data, size_t length) {
  size_t i;
  for (i = 0; i < length; ++i) {
    if (data[i] != 0u) return 0;
  }
  return 1;
}

static void read_candidate(const packet_view_t *view, uint16_t index, candidate_t *out) {
  const uint8_t *p = view->payload + (size_t)index * sizeof(phase06i_candidate_v1);
  out->start_bin = read_le16(p + 0);
  out->end_bin = read_le16(p + 2);
  out->peak_bin = read_le16(p + 4);
  out->span_bins = read_le16(p + 6);
  out->pfa_select = p[8];
  out->evaluate_center = (uint8_t)((p[9] & 2u) != 0u);
  out->peak_power = read_le64(p + 16);
  out->noise_power = read_le64(p + 24);
  out->threshold_power = read_le64(p + 32);
}

static int validate_candidate_records(const packet_view_t *view) {
  uint16_t i;
  for (i = 0; i < view->candidate_count; ++i) {
    const uint8_t *p = view->payload + (size_t)i * sizeof(phase06i_candidate_v1);
    candidate_t candidate;
    read_candidate(view, i, &candidate);
    if ((p[9] & ~3u) != 0u || (p[9] & 1u) == 0u || !all_zero(p + 10, 6u) ||
        candidate.start_bin > candidate.peak_bin || candidate.peak_bin > candidate.end_bin ||
        candidate.end_bin >= PHASE06I_FFT_SIZE ||
        candidate.span_bins != (uint16_t)(candidate.end_bin - candidate.start_bin + 1u) ||
        candidate.pfa_select > 2u || candidate.peak_power >= (UINT64_C(1) << 58) ||
        candidate.noise_power >= (UINT64_C(1) << 58) ||
        candidate.threshold_power >= (UINT64_C(1) << 62)) {
      return PHASE06J_ERR_CANDIDATE;
    }
  }
  return PHASE06J_OK;
}

static int decode_packet(const void *packet, size_t packet_bytes, packet_view_t *view) {
  const uint8_t *bytes = (const uint8_t *)packet;
  const uint8_t *trailer;
  uint32_t flags;
  uint32_t payload_bytes;
  uint16_t count;
  uint16_t status;
  if (bytes == NULL || view == NULL || packet_bytes < 64u || packet_bytes > PHASE06I_MAX_FRAME_BYTES) {
    return PHASE06J_ERR_PACKET_BOUNDS;
  }
  if (read_le32(bytes) != PHASE06I_HEADER_MAGIC || read_le16(bytes + 4) != PHASE06I_ABI_VERSION ||
      read_le16(bytes + 6) != 32u || read_le16(bytes + 12) != PHASE06I_FFT_SIZE ||
      read_le16(bytes + 14) != sizeof(phase06i_candidate_v1)) {
    return PHASE06J_ERR_HEADER;
  }
  flags = read_le32(bytes + 16);
  if ((flags & ~1u) != 0u || !all_zero(bytes + 20, 12u)) return PHASE06J_ERR_RESERVED;
  trailer = bytes + packet_bytes - sizeof(phase06i_trailer_v1);
  if (read_le32(trailer) != PHASE06I_TRAILER_MAGIC ||
      read_le16(trailer + 4) != PHASE06I_ABI_VERSION || read_le16(trailer + 6) != 32u ||
      read_le32(trailer + 8) != read_le32(bytes + 8)) {
    return PHASE06J_ERR_TRAILER;
  }
  count = read_le16(trailer + 12);
  status = read_le16(trailer + 14);
  payload_bytes = read_le32(trailer + 16);
  if (count > PHASE06I_MAX_CANDIDATES || payload_bytes != (uint32_t)count * 40u ||
      read_le32(trailer + 20) != packet_bytes || packet_bytes != (size_t)payload_bytes + 64u) {
    return PHASE06J_ERR_LENGTH;
  }
  if (read_le32(trailer + 28) != 0u || ((flags & 1u) != 0u) != (count == 0u)) {
    return PHASE06J_ERR_RESERVED;
  }
  if (status != 0u) return PHASE06J_ERR_STATUS;
  if (crc32_ieee(bytes + 32, payload_bytes) != read_le32(trailer + 24)) return PHASE06J_ERR_CRC;
  view->payload = bytes + 32;
  view->frame_id = read_le32(bytes + 8);
  view->candidate_count = count;
  return validate_candidate_records(view);
}

static uint128_pair_t multiply_u64(uint64_t a, uint64_t b) {
  const uint64_t mask = UINT64_C(0xFFFFFFFF);
  uint64_t a0 = a & mask;
  uint64_t a1 = a >> 32;
  uint64_t b0 = b & mask;
  uint64_t b1 = b >> 32;
  uint64_t p0 = a0 * b0;
  uint64_t p1 = a0 * b1;
  uint64_t p2 = a1 * b0;
  uint64_t p3 = a1 * b1;
  uint64_t middle = (p0 >> 32) + (p1 & mask) + (p2 & mask);
  uint128_pair_t result;
  result.low = (p0 & mask) | (middle << 32);
  result.high = p3 + (p1 >> 32) + (p2 >> 32) + (middle >> 32);
  return result;
}

static int compare_u128(uint128_pair_t a, uint128_pair_t b) {
  if (a.high != b.high) return a.high > b.high ? 1 : -1;
  if (a.low != b.low) return a.low > b.low ? 1 : -1;
  return 0;
}

static int compare_snr(const candidate_t *a, const candidate_t *b) {
  uint64_t an, ad, bn, bd;
  int a_inf = a->peak_power > 0u && a->noise_power == 0u;
  int b_inf = b->peak_power > 0u && b->noise_power == 0u;
  if (a_inf != b_inf) return a_inf ? 1 : -1;
  if (a_inf) return 0;
  an = a->peak_power == 0u ? 1u : a->peak_power;
  ad = a->peak_power == 0u ? 1u : a->noise_power;
  bn = b->peak_power == 0u ? 1u : b->peak_power;
  bd = b->peak_power == 0u ? 1u : b->noise_power;
  return compare_u128(multiply_u64(an, bd), multiply_u64(bn, ad));
}

static int candidate_admission_better(const candidate_t *a, uint16_t ai,
                                      const candidate_t *b, uint16_t bi) {
  int snr = compare_snr(a, b);
  if (snr != 0) return snr > 0;
  if (a->peak_bin != b->peak_bin) return a->peak_bin < b->peak_bin;
  if (a->start_bin != b->start_bin) return a->start_bin < b->start_bin;
  return ai < bi;
}

static int association_overlap(const candidate_t *previous, const candidate_t *current) {
  int start = (int)previous->start_bin - (int)PHASE06J_ASSOCIATION_TOLERANCE_BINS;
  int end = (int)previous->end_bin + (int)PHASE06J_ASSOCIATION_TOLERANCE_BINS;
  if (start < (int)current->start_bin) start = current->start_bin;
  if (end > (int)current->end_bin) end = current->end_bin;
  return end >= start ? end - start + 1 : 0;
}

static uint16_t peak_distance(const candidate_t *previous, const candidate_t *current) {
  return previous->peak_bin > current->peak_bin
             ? (uint16_t)(previous->peak_bin - current->peak_bin)
             : (uint16_t)(current->peak_bin - previous->peak_bin);
}

static int track_choice_better(const match_choice_t *candidate,
                               const match_choice_t *current) {
  if (!current->valid) return candidate->valid != 0u;
  if (!candidate->valid) return 0;
  if (candidate->overlap != current->overlap) return candidate->overlap > current->overlap;
  if (candidate->distance != current->distance) return candidate->distance < current->distance;
  if (candidate->candidate.start_bin != current->candidate.start_bin) {
    return candidate->candidate.start_bin < current->candidate.start_bin;
  }
  return candidate->region_index < current->region_index;
}

static void refresh_match_choice(const track_t *track, const packet_view_t *view,
                                 const uint8_t *matched_regions, match_choice_t *choice) {
  uint16_t ri;
  memset(choice, 0, sizeof(*choice));
  for (ri = 0; ri < view->candidate_count; ++ri) {
    match_choice_t candidate_choice;
    if (matched_regions[ri]) continue;
    memset(&candidate_choice, 0, sizeof(candidate_choice));
    read_candidate(view, ri, &candidate_choice.candidate);
    candidate_choice.overlap = association_overlap(&track->candidate, &candidate_choice.candidate);
    if (candidate_choice.overlap <= 0) continue;
    candidate_choice.distance = peak_distance(&track->candidate, &candidate_choice.candidate);
    candidate_choice.region_index = ri;
    candidate_choice.valid = 1u;
    if (track_choice_better(&candidate_choice, choice)) *choice = candidate_choice;
  }
}

static int global_choice_better(const state_t *state, uint16_t candidate_track,
                                const match_choice_t *candidate, uint16_t current_track,
                                const match_choice_t *current) {
  if (!current->valid) return candidate->valid != 0u;
  if (!candidate->valid) return 0;
  if (candidate->overlap != current->overlap) return candidate->overlap > current->overlap;
  if (candidate->distance != current->distance) return candidate->distance < current->distance;
  if (state->tracks[candidate_track].event_id != state->tracks[current_track].event_id) {
    return state->tracks[candidate_track].event_id < state->tracks[current_track].event_id;
  }
  if (candidate->candidate.start_bin != current->candidate.start_bin) {
    return candidate->candidate.start_bin < current->candidate.start_bin;
  }
  return candidate->region_index < current->region_index;
}

static void append_history(track_t *track, uint8_t observed) {
  unsigned i;
  if (track->history_length < PHASE06J_CONFIRMATION_WINDOW) {
    track->history[track->history_length++] = observed;
  } else {
    for (i = 1; i < PHASE06J_CONFIRMATION_WINDOW; ++i) track->history[i - 1] = track->history[i];
    track->history[PHASE06J_CONFIRMATION_WINDOW - 1u] = observed;
  }
}

static unsigned history_sum(const track_t *track) {
  unsigned total = 0;
  unsigned i;
  for (i = 0; i < track->history_length; ++i) total += track->history[i] != 0u;
  return total;
}

static void write_candidate(phase06i_candidate_v1 *out, const candidate_t *candidate) {
  memset(out, 0, sizeof(*out));
  out->start_shifted_bin = candidate->start_bin;
  out->end_shifted_bin = candidate->end_bin;
  out->peak_shifted_bin = candidate->peak_bin;
  out->coarse_span_bins = candidate->span_bins;
  out->pfa_select = candidate->pfa_select;
  out->flags = (uint8_t)(1u | (candidate->evaluate_center ? 2u : 0u));
  out->peak_power_uq28_30 = candidate->peak_power;
  out->regional_noise_uq28_30 = candidate->noise_power;
  out->threshold_uq32_30 = candidate->threshold_power;
}

static void write_event(phase06j_event_v1 *out, const track_t *track, uint8_t state) {
  memset(out, 0, sizeof(*out));
  out->event_id = track->event_id;
  out->first_frame_id = track->first_frame_id;
  out->last_seen_frame_id = track->last_seen_frame_id;
  out->seen_count = track->seen_count;
  out->state = state;
  out->observed_this_frame = track->observed;
  write_candidate(&out->candidate, &track->candidate);
}

static void append_ended(state_t *state, const phase06j_event_v1 *event) {
  uint16_t index;
  if (state->ended_count < PHASE06J_MAX_ENDED_HISTORY) {
    index = (uint16_t)((state->ended_start + state->ended_count) % PHASE06J_MAX_ENDED_HISTORY);
    state->ended_count++;
  } else {
    index = state->ended_start;
    state->ended_start = (uint16_t)((state->ended_start + 1u) % PHASE06J_MAX_ENDED_HISTORY);
    state->evicted_history_count++;
  }
  state->ended_history[index] = *event;
}

static void reset_state(state_t *state) {
  memset(state, 0, sizeof(*state));
  state->magic = PHASE06J_STATE_MAGIC;
  state->next_event_id = 1u;
}

size_t phase06j_state_bytes(void) { return sizeof(state_t); }

int phase06j_state_init(void *memory, size_t bytes) {
  if (memory == NULL || bytes < sizeof(state_t)) return PHASE06J_ERR_STATE;
  reset_state((state_t *)memory);
  return PHASE06J_OK;
}

int phase06j_state_reset(void *memory, size_t bytes) {
  return phase06j_state_init(memory, bytes);
}

int phase06j_validate_packet(const void *packet, size_t packet_bytes,
                             uint32_t *frame_id, uint16_t *candidate_count) {
  packet_view_t view;
  int code = decode_packet(packet, packet_bytes, &view);
  if (code != PHASE06J_OK) return code;
  if (frame_id != NULL) *frame_id = view.frame_id;
  if (candidate_count != NULL) *candidate_count = view.candidate_count;
  return PHASE06J_OK;
}

static int process_view(void *memory, size_t bytes, const packet_view_t *input,
                        phase06j_frame_result_v1 *result) {
  state_t *state = (state_t *)memory;
  packet_view_t view;
  uint8_t matched_tracks[PHASE06J_MAX_ACTIVE_TRACKS] = {0};
  uint8_t matched_regions[PHASE06I_MAX_CANDIDATES] = {0};
  match_choice_t track_choices[PHASE06J_MAX_ACTIVE_TRACKS] = {0};
  uint16_t original_tracks;
  uint16_t match_count = 0;
  uint16_t i;
  if (state == NULL || input == NULL || result == NULL || bytes < sizeof(state_t) ||
      state->magic != PHASE06J_STATE_MAGIC) {
    return PHASE06J_ERR_STATE;
  }
  view = *input;
  memset(result, 0, sizeof(*result));
  result->frame_id = view.frame_id;
  if (state->has_last_frame && view.frame_id != state->last_frame_id + 1u) {
    reset_state(state);
    result->reset_applied = 1u;
  }
  original_tracks = state->track_count;
  for (i = 0; i < original_tracks; ++i) {
    refresh_match_choice(&state->tracks[i], &view, matched_regions, &track_choices[i]);
  }
  while (match_count < original_tracks && match_count < view.candidate_count) {
    uint16_t best_track = 0;
    match_choice_t best_choice = {0};
    uint16_t ti;
    for (ti = 0; ti < original_tracks; ++ti) {
      if (matched_tracks[ti]) continue;
      if (global_choice_better(state, ti, &track_choices[ti], best_track, &best_choice)) {
        best_track = ti;
        best_choice = track_choices[ti];
      }
    }
    if (!best_choice.valid) break;
    matched_tracks[best_track] = 1u;
    matched_regions[best_choice.region_index] = 1u;
    state->tracks[best_track].candidate = best_choice.candidate;
    state->tracks[best_track].last_seen_frame_id = view.frame_id;
    state->tracks[best_track].seen_count++;
    state->tracks[best_track].consecutive_misses = 0u;
    state->tracks[best_track].observed = 1u;
    append_history(&state->tracks[best_track], 1u);
    if (history_sum(&state->tracks[best_track]) >= PHASE06J_CONFIRMATIONS_REQUIRED) {
      state->tracks[best_track].confirmed = 1u;
    }
    for (ti = 0; ti < original_tracks; ++ti) {
      if (!matched_tracks[ti] && track_choices[ti].valid &&
          track_choices[ti].region_index == best_choice.region_index) {
        refresh_match_choice(&state->tracks[ti], &view, matched_regions, &track_choices[ti]);
      }
    }
    match_count++;
  }
  {
    uint16_t write_index = 0;
    for (i = 0; i < original_tracks; ++i) {
      track_t track = state->tracks[i];
      if (!matched_tracks[i]) {
        track.observed = 0u;
        track.consecutive_misses++;
        append_history(&track, 0u);
      }
      if (!matched_tracks[i] && track.consecutive_misses >= PHASE06J_EXPIRY_CONSECUTIVE_MISSES) {
        phase06j_event_v1 ended;
        write_event(&ended, &track, PHASE06J_EVENT_ENDED);
        result->ended[result->ended_count++] = ended;
        append_ended(state, &ended);
      } else {
        state->tracks[write_index++] = track;
      }
    }
    state->track_count = write_index;
  }
  {
    uint16_t unmatched = 0;
    uint16_t capacity = (uint16_t)(PHASE06J_MAX_ACTIVE_TRACKS - state->track_count);
    uint16_t admitted = 0;
    for (i = 0; i < view.candidate_count; ++i) unmatched += matched_regions[i] == 0u;
    while (admitted < capacity && admitted < unmatched) {
      int have_best = 0;
      uint16_t best_index = 0;
      candidate_t best = {0};
      for (i = 0; i < view.candidate_count; ++i) {
        candidate_t current;
        if (matched_regions[i]) continue;
        read_candidate(&view, i, &current);
        if (!have_best || candidate_admission_better(&current, i, &best, best_index)) {
          have_best = 1;
          best_index = i;
          best = current;
        }
      }
      if (!have_best || state->next_event_id == UINT64_MAX) return PHASE06J_ERR_STATE;
      matched_regions[best_index] = 1u;
      {
        track_t *track = &state->tracks[state->track_count++];
        memset(track, 0, sizeof(*track));
        track->event_id = state->next_event_id++;
        track->first_frame_id = view.frame_id;
        track->last_seen_frame_id = view.frame_id;
        track->seen_count = 1u;
        track->candidate = best;
        track->history[0] = 1u;
        track->history_length = 1u;
        track->observed = 1u;
      }
      admitted++;
    }
    result->dropped_candidates = (uint16_t)(unmatched - admitted);
  }
  result->active_count = state->track_count;
  for (i = 0; i < state->track_count; ++i) {
    write_event(&result->active[i], &state->tracks[i],
                state->tracks[i].confirmed ? PHASE06J_EVENT_CONFIRMED : PHASE06J_EVENT_TENTATIVE);
  }
  result->evicted_history_count = state->evicted_history_count;
  state->has_last_frame = 1u;
  state->last_frame_id = view.frame_id;
  return PHASE06J_OK;
}

int phase06j_process_packet(void *memory, size_t bytes, const void *packet,
                            size_t packet_bytes, phase06j_frame_result_v1 *result) {
  state_t *state = (state_t *)memory;
  packet_view_t view;
  int code;
  if (state == NULL || result == NULL || bytes < sizeof(state_t) ||
      state->magic != PHASE06J_STATE_MAGIC) {
    return PHASE06J_ERR_STATE;
  }
  code = decode_packet(packet, packet_bytes, &view);
  if (code != PHASE06J_OK) return code;
  return process_view(memory, bytes, &view, result);
}

int phase06j_process_candidates(void *memory, size_t bytes, uint32_t frame_id,
                                const phase06i_candidate_v1 *candidates,
                                uint16_t candidate_count,
                                phase06j_frame_result_v1 *result) {
  state_t *state = (state_t *)memory;
  packet_view_t view;
  int code;
  if (state == NULL || result == NULL || bytes < sizeof(state_t) ||
      state->magic != PHASE06J_STATE_MAGIC) {
    return PHASE06J_ERR_STATE;
  }
  if (candidate_count > PHASE06I_MAX_CANDIDATES ||
      (candidate_count != 0u && candidates == NULL)) {
    return PHASE06J_ERR_PACKET_BOUNDS;
  }
  view.payload = (const uint8_t *)candidates;
  view.frame_id = frame_id;
  view.candidate_count = candidate_count;
  code = validate_candidate_records(&view);
  if (code != PHASE06J_OK) return code;
  return process_view(memory, bytes, &view, result);
}

const char *phase06j_error_string(int code) {
  switch (code) {
    case PHASE06J_OK: return "ok";
    case PHASE06J_ERR_PACKET_BOUNDS: return "packet_bounds";
    case PHASE06J_ERR_HEADER: return "header";
    case PHASE06J_ERR_TRAILER: return "trailer";
    case PHASE06J_ERR_LENGTH: return "length";
    case PHASE06J_ERR_RESERVED: return "reserved_or_flags";
    case PHASE06J_ERR_CRC: return "crc32";
    case PHASE06J_ERR_CANDIDATE: return "candidate";
    case PHASE06J_ERR_STATUS: return "status_marked_packet";
    case PHASE06J_ERR_STATE: return "state";
    default: return "unknown";
  }
}
