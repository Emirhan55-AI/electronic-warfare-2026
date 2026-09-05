#include "p0_pl_os_cfar.h"

#include <string.h>

#define P0_POWER_MASK ((UINT64_C(1) << 58) - UINT64_C(1))
#define P0_EVALUATED_MASK (UINT64_C(1) << 58)
#define P0_DETECTED_MASK (UINT64_C(1) << 59)
#define P0_FORMAT_MARKER (UINT64_C(0xA) << 60)
#define P0_FORMAT_MASK (UINT64_C(0xF) << 60)
#define P0_POWER_SCALE (UINT64_C(1) << 30)

static uint64_t load_u64_le(const uint8_t *source)
{
    uint64_t value;

    /* memcpy also permits unaligned DMA/test buffers without aliasing. */
    memcpy(&value, source, sizeof(value));
#if defined(__BYTE_ORDER__) && __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
    value = __builtin_bswap64(value);
#elif !defined(__BYTE_ORDER__) && !defined(_WIN32)
    /* Preserve the portable byte-order contract on unidentified targets. */
    const uint16_t endian_probe = 1U;
    if (*(const uint8_t *)&endian_probe == 0U) {
        unsigned int index;
        value = 0U;
        for (index = 0U; index < 8U; ++index)
            value |= (uint64_t)source[index] << (index * 8U);
    }
#endif
    return value;
}

int p0_pl_os_cfar_decode(
    const uint8_t *natural_words,
    size_t frame_bytes,
    uint64_t *shifted_power_uq28_30,
    double *shifted_power,
    uint8_t *shifted_detections,
    int *pl_decisions_present
)
{
    size_t natural_bin;
    int marked;

    if (natural_words == NULL || shifted_power_uq28_30 == NULL || shifted_power == NULL ||
        shifted_detections == NULL || pl_decisions_present == NULL ||
        frame_bytes != P0_PL_OS_CFAR_FRAME_BYTES)
        return P0_PL_OS_CFAR_INVALID_ARGUMENT;

    marked = (load_u64_le(natural_words) & P0_FORMAT_MASK) == P0_FORMAT_MARKER;
    for (natural_bin = 0U; natural_bin < P0_PL_OS_CFAR_FRAME_BINS; ++natural_bin) {
        size_t shifted_bin = natural_bin ^ (P0_PL_OS_CFAR_FRAME_BINS / 2U);
        uint64_t word = load_u64_le(natural_words + natural_bin * 8U);
        uint64_t power = word & P0_POWER_MASK;

        if (marked ? (word & P0_FORMAT_MASK) != P0_FORMAT_MARKER
                   : word >= (UINT64_C(1) << 58))
            return P0_PL_OS_CFAR_INVALID_FRAME;
        shifted_power_uq28_30[shifted_bin] = power;
        /* ARMv7 has native uint32->double conversion; uint64 uses a helper.
         * Both terms are exact binary scalings; the sum rounds once, exactly
         * as uint64->double followed by the power-of-two UQ30 scaling. */
        shifted_power[shifted_bin] =
            (double)(uint32_t)(power >> 32U) * 4.0 +
            (double)(uint32_t)power / (double)P0_POWER_SCALE;
        shifted_detections[shifted_bin] = 0U;
        if (marked) {
            int expected_evaluated =
                shifted_bin >= P0_PL_OS_CFAR_RADIUS &&
                shifted_bin < P0_PL_OS_CFAR_FRAME_BINS - P0_PL_OS_CFAR_RADIUS;
            int evaluated = (word & P0_EVALUATED_MASK) != 0U;
            int detected = (word & P0_DETECTED_MASK) != 0U;

            if (evaluated != expected_evaluated || (detected && !evaluated))
                return P0_PL_OS_CFAR_INVALID_FRAME;
            shifted_detections[shifted_bin] = detected ? 1U : 0U;
        }
    }
    *pl_decisions_present = marked;
    return P0_PL_OS_CFAR_OK;
}
