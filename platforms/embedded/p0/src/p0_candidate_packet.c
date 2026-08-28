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
    static const uint32_t table[16] = {
        UINT32_C(0x00000000), UINT32_C(0x1DB71064),
        UINT32_C(0x3B6E20C8), UINT32_C(0x26D930AC),
        UINT32_C(0x76DC4190), UINT32_C(0x6B6B51F4),
        UINT32_C(0x4DB26158), UINT32_C(0x5005713C),
        UINT32_C(0xEDB88320), UINT32_C(0xF00F9344),
        UINT32_C(0xD6D6A3E8), UINT32_C(0xCB61B38C),
        UINT32_C(0x9B64C2B0), UINT32_C(0x86D3D2D4),
        UINT32_C(0xA00AE278), UINT32_C(0xBDBDF21C),
    };
    uint32_t crc = UINT32_MAX;
    size_t index;

    for (index = 0U; index < length; ++index) {
        crc ^= data[index];
        crc = (crc >> 4) ^ table[crc & 0x0FU];
        crc = (crc >> 4) ^ table[crc & 0x0FU];
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

int p0_candidate_records_encode(
    const uint64_t *shifted_power_uq28_30,
    size_t power_count,
    const p0_os_cfar_config_t *config,
    const p0_candidate_region_t *candidates,
    size_t candidate_count,
    phase06i_candidate_v1 *records,
    size_t record_capacity
)
{
    size_t index;
    uint8_t *payload = (uint8_t *)records;

    if (config == NULL || records == NULL ||
        (candidate_count != 0U &&
         (shifted_power_uq28_30 == NULL || candidates == NULL)) ||
        power_count != PHASE06I_FFT_SIZE ||
        candidate_count > PHASE06I_MAX_CANDIDATES)
        return P0_CANDIDATE_PACKET_INVALID_ARGUMENT;
    if (record_capacity < candidate_count)
        return P0_CANDIDATE_PACKET_CAPACITY;
    memset(records, 0, candidate_count * sizeof(*records));
    for (index = 0U; index < candidate_count; ++index) {
        const p0_candidate_region_t *candidate = &candidates[index];
        uint8_t *record = payload + index * sizeof(*records);
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
    return P0_CANDIDATE_PACKET_OK;
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
    if (p0_candidate_records_encode(
            shifted_power_uq28_30, power_count, config, candidates,
            candidate_count, (phase06i_candidate_v1 *)payload,
            candidate_count) != P0_CANDIDATE_PACKET_OK)
        return P0_CANDIDATE_PACKET_RANGE;
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
