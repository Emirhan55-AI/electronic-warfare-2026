#ifndef PHASE06I_TRANSPORT_ABI_H
#define PHASE06I_TRANSPORT_ABI_H

#include <stddef.h>
#include <stdint.h>

#define PHASE06I_ABI_VERSION 1u
#define PHASE06I_HEADER_MAGIC 0x48493650u
#define PHASE06I_TRAILER_MAGIC 0x54493650u
#define PHASE06I_FFT_SIZE 4096u
#define PHASE06I_MAX_CANDIDATES 1352u
#define PHASE06I_MAX_FRAME_BYTES 54144u

#pragma pack(push, 1)
typedef struct {
  uint32_t magic;
  uint16_t version;
  uint16_t header_bytes;
  uint32_t frame_id;
  uint16_t fft_size;
  uint16_t record_bytes;
  uint32_t flags;
  uint32_t reserved0;
  uint32_t reserved1;
  uint32_t reserved2;
} phase06i_header_v1;

typedef struct {
  uint16_t start_shifted_bin;
  uint16_t end_shifted_bin;
  uint16_t peak_shifted_bin;
  uint16_t coarse_span_bins;
  uint8_t pfa_select;
  uint8_t flags;
  uint16_t reserved0;
  uint32_t reserved1;
  uint64_t peak_power_uq28_30;
  uint64_t regional_noise_uq28_30;
  uint64_t threshold_uq32_30;
} phase06i_candidate_v1;

typedef struct {
  uint32_t magic;
  uint16_t version;
  uint16_t trailer_bytes;
  uint32_t frame_id;
  uint16_t candidate_count;
  uint16_t status;
  uint32_t payload_bytes;
  uint32_t packet_bytes;
  uint32_t payload_crc32;
  uint32_t reserved;
} phase06i_trailer_v1;
#pragma pack(pop)

_Static_assert(sizeof(phase06i_header_v1) == 32, "PHASE-06I header ABI drift");
_Static_assert(sizeof(phase06i_candidate_v1) == 40, "PHASE-06I candidate ABI drift");
_Static_assert(sizeof(phase06i_trailer_v1) == 32, "PHASE-06I trailer ABI drift");
_Static_assert(offsetof(phase06i_candidate_v1, peak_power_uq28_30) == 16, "PHASE-06I offset drift");
_Static_assert(offsetof(phase06i_candidate_v1, regional_noise_uq28_30) == 24, "PHASE-06I offset drift");
_Static_assert(offsetof(phase06i_candidate_v1, threshold_uq32_30) == 32, "PHASE-06I offset drift");

#endif
