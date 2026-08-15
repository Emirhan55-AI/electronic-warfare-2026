#include "phase06i_transport_abi.h"

/* Structural validation for a completed coherent DMA buffer. CRC32 is checked
 * by the platform adapter before this routine is accepted as deployment-ready. */
int phase06i_validate_packet_shape(const void *buffer, size_t length) {
  const uint8_t *bytes = (const uint8_t *)buffer;
  const phase06i_header_v1 *header;
  const phase06i_trailer_v1 *trailer;
  size_t payload_bytes;
  if (bytes == NULL || length < 64u || length > PHASE06I_MAX_FRAME_BYTES) return -1;
  header = (const phase06i_header_v1 *)bytes;
  trailer = (const phase06i_trailer_v1 *)(bytes + length - sizeof(*trailer));
  if (header->magic != PHASE06I_HEADER_MAGIC || header->version != PHASE06I_ABI_VERSION ||
      header->header_bytes != sizeof(*header) || header->fft_size != PHASE06I_FFT_SIZE ||
      header->record_bytes != sizeof(phase06i_candidate_v1)) return -2;
  if (trailer->magic != PHASE06I_TRAILER_MAGIC || trailer->version != PHASE06I_ABI_VERSION ||
      trailer->trailer_bytes != sizeof(*trailer) || trailer->frame_id != header->frame_id) return -3;
  payload_bytes = length - sizeof(*header) - sizeof(*trailer);
  if (trailer->candidate_count > PHASE06I_MAX_CANDIDATES ||
      trailer->payload_bytes != payload_bytes || trailer->packet_bytes != length ||
      payload_bytes != (size_t)trailer->candidate_count * sizeof(phase06i_candidate_v1)) return -4;
  return 0;
}
