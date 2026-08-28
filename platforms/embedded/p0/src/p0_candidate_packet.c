#include "p0_candidate_packet.h"

#include <math.h>
#include <string.h>

#include "phase06i_transport_abi.h"

#define P0_CANONICAL_PFA_SELECT 1U
#define P0_RECORD_VALID 1U
#define P0_HEADER_EMPTY 1U

static void store_le16(uint8_t *target, uint16_t value)
{
    target[0] = (uint8_t)value;
    target[1] = (uint8_t)(value >> 8);
}

static void store_le32(uint8_t *target, uint32_t value)
{
    target[0] = (uint8_t)value;
    target[1] = (uint8_t)(value >> 8);
    target[2] = (uint8_t)(value >> 16);
    target[3] = (uint8_t)(value >> 24);
}

static void store_le64(uint8_t *target, uint64_t value)
{
    store_le32(target, (uint32_t)value);
    store_le32(target + 4, (uint32_t)(value >> 32));
}

static uint32_t crc32_ieee(const uint8_t *data, size_t length)
{
    uint32_t crc = UINT32_MAX;
    size_t index;
    unsigned int bit;

    for (index = 0U; index < length; ++index) {
        crc ^= data[index];
        for (bit = 0U; bit < 8U; ++bit)
            crc = (crc >> 1) ^ (0xEDB88320U & (uint32_t)-(int32_t)(crc & 1U));
    }
    return crc ^ UINT32_MAX;
}

static int rounded_uq30(double value, unsigned int width, uint64_t *encoded)
{
    double scaled = value * (double)(UINT64_C(1) << 30);

    if (encoded == NULL || !isfinite(scaled) || scaled < 0.0 ||
        width > 63U || scaled >= (double)(UINT64_C(1) << width))
        return P0_CANDIDATE_PACKET_RANGE;
    *encoded = (uint64_t)floor(scaled + 0.5);
    return P0_CANDIDATE_PACKET_OK;
}

size_t p0_candidate_packet_bytes(size_t candidate_count)
{
    if (candidate_count > PHASE06I_MAX_CANDIDATES)
        return 0U;
    return sizeof(phase06i_header_v1) + candidate_count * sizeof(phase06i_candidate_v1) +
           sizeof(phase06i_trailer_v1);
}

int p0_candidate_packet_encode(
    uint32_t frame_id,
    const uint64_t *shifted_power_uq28_30,
    size_t power_count,
    const p0_os_cfar_config_t *config,
    const p0_candidate_region_t *candidates,
    size_t candidate_count,
    uint8_t *packet,
    size_t packet_capacity,
    size_t *packet_bytes
)
{
    size_t required = p0_candidate_packet_bytes(candidate_count);
    size_t payload_bytes = candidate_count * sizeof(phase06i_candidate_v1);
    size_t index;
    uint8_t *payload;
    uint8_t *trailer;

    if (packet == NULL || packet_bytes == NULL || config == NULL ||
        (candidate_count != 0U && (shifted_power_uq28_30 == NULL || candidates == NULL)) ||
        power_count != PHASE06I_FFT_SIZE || required == 0U)
        return P0_CANDIDATE_PACKET_INVALID_ARGUMENT;
    if (packet_capacity < required)
        return P0_CANDIDATE_PACKET_CAPACITY;
    memset(packet, 0, required);
    store_le32(packet, PHASE06I_HEADER_MAGIC);
    store_le16(packet + 4, PHASE06I_ABI_VERSION);
    store_le16(packet + 6, (uint16_t)sizeof(phase06i_header_v1));
    store_le32(packet + 8, frame_id);
    store_le16(packet + 12, PHASE06I_FFT_SIZE);
    store_le16(packet + 14, (uint16_t)sizeof(phase06i_candidate_v1));
    store_le32(packet + 16, candidate_count == 0U ? P0_HEADER_EMPTY : 0U);
    payload = packet + sizeof(phase06i_header_v1);
    for (index = 0U; index < candidate_count; ++index) {
        const p0_candidate_region_t *candidate = &candidates[index];
        uint8_t *record = payload + index * sizeof(phase06i_candidate_v1);
        uint64_t noise;
        uint64_t threshold;

        if (candidate->start_bin > candidate->peak_bin ||
            candidate->peak_bin > candidate->end_bin || candidate->end_bin >= power_count ||
            shifted_power_uq28_30[candidate->peak_bin] >= (UINT64_C(1) << 58) ||
            !isfinite(config->threshold_coefficient) || config->threshold_coefficient <= 0.0 ||
            rounded_uq30(candidate->noise_power_per_bin, 58U, &noise) !=
                P0_CANDIDATE_PACKET_OK ||
            rounded_uq30(candidate->threshold_power, 62U, &threshold) !=
                P0_CANDIDATE_PACKET_OK)
            return P0_CANDIDATE_PACKET_RANGE;
        store_le16(record, (uint16_t)candidate->start_bin);
        store_le16(record + 2, (uint16_t)candidate->end_bin);
        store_le16(record + 4, (uint16_t)candidate->peak_bin);
        store_le16(record + 6, (uint16_t)(candidate->end_bin - candidate->start_bin + 1U));
        record[8] = P0_CANONICAL_PFA_SELECT;
        record[9] = P0_RECORD_VALID;
        store_le64(record + 16, shifted_power_uq28_30[candidate->peak_bin]);
        store_le64(record + 24, noise);
        store_le64(record + 32, threshold);
    }
    trailer = payload + payload_bytes;
    store_le32(trailer, PHASE06I_TRAILER_MAGIC);
    store_le16(trailer + 4, PHASE06I_ABI_VERSION);
    store_le16(trailer + 6, (uint16_t)sizeof(phase06i_trailer_v1));
    store_le32(trailer + 8, frame_id);
    store_le16(trailer + 12, (uint16_t)candidate_count);
    store_le32(trailer + 16, (uint32_t)payload_bytes);
    store_le32(trailer + 20, (uint32_t)required);
    store_le32(trailer + 24, crc32_ieee(payload, payload_bytes));
    *packet_bytes = required;
    return P0_CANDIDATE_PACKET_OK;
}
