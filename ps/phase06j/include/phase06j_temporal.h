#ifndef PHASE06J_TEMPORAL_H
#define PHASE06J_TEMPORAL_H

#include <stddef.h>
#include <stdint.h>

#include "phase06i_transport_abi.h"

#if defined(_WIN32)
#define PHASE06J_API __declspec(dllexport)
#else
#define PHASE06J_API __attribute__((visibility("default")))
#endif

#define PHASE06J_MAX_ACTIVE_TRACKS 64u
#define PHASE06J_MAX_ENDED_HISTORY 128u
#define PHASE06J_ASSOCIATION_TOLERANCE_BINS 2u
#define PHASE06J_CONFIRMATIONS_REQUIRED 2u
#define PHASE06J_CONFIRMATION_WINDOW 3u
#define PHASE06J_EXPIRY_CONSECUTIVE_MISSES 2u

enum phase06j_event_state {
  PHASE06J_EVENT_TENTATIVE = 1,
  PHASE06J_EVENT_CONFIRMED = 2,
  PHASE06J_EVENT_ENDED = 3
};

enum phase06j_result_code {
  PHASE06J_OK = 0,
  PHASE06J_ERR_PACKET_BOUNDS = -1,
  PHASE06J_ERR_HEADER = -2,
  PHASE06J_ERR_TRAILER = -3,
  PHASE06J_ERR_LENGTH = -4,
  PHASE06J_ERR_RESERVED = -5,
  PHASE06J_ERR_CRC = -6,
  PHASE06J_ERR_CANDIDATE = -7,
  PHASE06J_ERR_STATUS = -8,
  PHASE06J_ERR_STATE = -9
};

#pragma pack(push, 1)
typedef struct {
  uint64_t event_id;
  uint32_t first_frame_id;
  uint32_t last_seen_frame_id;
  uint64_t seen_count;
  uint8_t state;
  uint8_t observed_this_frame;
  uint16_t reserved;
  phase06i_candidate_v1 candidate;
} phase06j_event_v1;

typedef struct {
  uint32_t frame_id;
  uint16_t active_count;
  uint16_t ended_count;
  uint16_t dropped_candidates;
  uint8_t reset_applied;
  uint8_t reserved;
  uint64_t evicted_history_count;
  phase06j_event_v1 active[PHASE06J_MAX_ACTIVE_TRACKS];
  phase06j_event_v1 ended[PHASE06J_MAX_ACTIVE_TRACKS];
} phase06j_frame_result_v1;
#pragma pack(pop)

_Static_assert(sizeof(phase06j_event_v1) == 68, "PHASE-06J event layout drift");
_Static_assert(sizeof(phase06j_frame_result_v1) == 8724, "PHASE-06J result layout drift");

PHASE06J_API size_t phase06j_state_bytes(void);
PHASE06J_API int phase06j_state_init(void *memory, size_t bytes);
PHASE06J_API int phase06j_state_reset(void *memory, size_t bytes);
PHASE06J_API int phase06j_validate_packet(const void *packet, size_t packet_bytes,
                                          uint32_t *frame_id, uint16_t *candidate_count);
PHASE06J_API int phase06j_process_packet(void *memory, size_t bytes,
                                        const void *packet, size_t packet_bytes,
                                        phase06j_frame_result_v1 *result);
PHASE06J_API const char *phase06j_error_string(int code);

#endif
