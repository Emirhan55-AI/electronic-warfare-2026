#include "p0_pl_os_cfar.h"

#include <string.h>

#define P0_POWER_MASK ((UINT64_C(1) << 58) - UINT64_C(1))
#define P0_EVALUATED_MASK (UINT64_C(1) << 58)
#define P0_DETECTED_MASK (UINT64_C(1) << 59)
#define P0_FORMAT_MARKER (UINT64_C(0xA) << 60)
#define P0_FORMAT_MASK (UINT64_C(0xF) << 60)
#define P0_V2_MARKER (UINT64_C(0xC) << 60)
#define P0_V2_MASK (UINT64_C(0xE) << 60)
#define P0_WEAK_MASK (UINT64_C(1) << 60)
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

static int decode_frame(
    const uint8_t *natural_words,
    size_t frame_bytes,
    uint64_t *shifted_power_uq28_30,
    double *shifted_power,
    uint8_t *shifted_detections,
    int *pl_decisions_present, int include_weak
)
{
    size_t natural_bin;
    uint64_t first_word;
    int marked;
    int version2;

    if (natural_words == NULL || shifted_power_uq28_30 == NULL || shifted_power == NULL ||
        shifted_detections == NULL || pl_decisions_present == NULL ||
        frame_bytes != P0_PL_OS_CFAR_FRAME_BYTES)
        return P0_PL_OS_CFAR_INVALID_ARGUMENT;

    first_word = load_u64_le(natural_words);
    marked = (first_word & P0_FORMAT_MASK) == P0_FORMAT_MARKER;
    version2 = (first_word & P0_V2_MASK) == P0_V2_MARKER;
    marked = marked || version2;
    if (version2) {
        for (natural_bin = 0U; natural_bin < P0_PL_OS_CFAR_FRAME_BINS; ++natural_bin) {
            size_t shifted_bin = natural_bin ^ (P0_PL_OS_CFAR_FRAME_BINS / 2U);
            uint64_t word = load_u64_le(natural_words + natural_bin * 8U);
            uint64_t power = word & P0_POWER_MASK;
            int expected_evaluated =
                shifted_bin >= P0_PL_OS_CFAR_RADIUS &&
                shifted_bin < P0_PL_OS_CFAR_FRAME_BINS - P0_PL_OS_CFAR_RADIUS;
            int evaluated = (word & P0_EVALUATED_MASK) != 0U;
            int detected = (word & P0_DETECTED_MASK) != 0U;
            int weak = (word & P0_WEAK_MASK) != 0U;

            if ((word & P0_V2_MASK) != P0_V2_MARKER ||
                evaluated != expected_evaluated || (detected && !evaluated) ||
                (weak && !evaluated) || (detected && !weak))
                return P0_PL_OS_CFAR_INVALID_FRAME;
            shifted_power_uq28_30[shifted_bin] = power;
            /* ARMv7 has native uint32->double conversion; uint64 uses a helper.
             * Both terms are exact binary scalings and sum with one rounding. */
            shifted_power[shifted_bin] =
                (double)(uint32_t)(power >> 32U) * 4.0 +
                (double)(uint32_t)power / (double)P0_POWER_SCALE;
            shifted_detections[shifted_bin] = detected ? 1U : 0U;
            if (include_weak && weak)
                shifted_detections[shifted_bin] |= 2U;
        }
    } else if (marked) {
        for (natural_bin = 0U; natural_bin < P0_PL_OS_CFAR_FRAME_BINS; ++natural_bin) {
            size_t shifted_bin = natural_bin ^ (P0_PL_OS_CFAR_FRAME_BINS / 2U);
            uint64_t word = load_u64_le(natural_words + natural_bin * 8U);
            uint64_t power = word & P0_POWER_MASK;
            int expected_evaluated =
                shifted_bin >= P0_PL_OS_CFAR_RADIUS &&
                shifted_bin < P0_PL_OS_CFAR_FRAME_BINS - P0_PL_OS_CFAR_RADIUS;
            int evaluated = (word & P0_EVALUATED_MASK) != 0U;
            int detected = (word & P0_DETECTED_MASK) != 0U;

            if ((word & P0_FORMAT_MASK) != P0_FORMAT_MARKER ||
                evaluated != expected_evaluated || (detected && !evaluated))
                return P0_PL_OS_CFAR_INVALID_FRAME;
            shifted_power_uq28_30[shifted_bin] = power;
            shifted_power[shifted_bin] =
                (double)(uint32_t)(power >> 32U) * 4.0 +
                (double)(uint32_t)power / (double)P0_POWER_SCALE;
            shifted_detections[shifted_bin] = detected ? 1U : 0U;
        }
    } else {
        for (natural_bin = 0U; natural_bin < P0_PL_OS_CFAR_FRAME_BINS; ++natural_bin) {
            size_t shifted_bin = natural_bin ^ (P0_PL_OS_CFAR_FRAME_BINS / 2U);
            uint64_t word = load_u64_le(natural_words + natural_bin * 8U);

            if (word >= (UINT64_C(1) << 58))
                return P0_PL_OS_CFAR_INVALID_FRAME;
            shifted_power_uq28_30[shifted_bin] = word;
            shifted_power[shifted_bin] =
                (double)(uint32_t)(word >> 32U) * 4.0 +
                (double)(uint32_t)word / (double)P0_POWER_SCALE;
            shifted_detections[shifted_bin] = 0U;
        }
    }
    *pl_decisions_present = marked;
    return P0_PL_OS_CFAR_OK;
}

int p0_pl_os_cfar_decode(const uint8_t *words, size_t bytes, uint64_t *raw,
    double *power, uint8_t *detections, int *present)
{
    return decode_frame(words, bytes, raw, power, detections, present, 0);
}

int p0_pl_os_cfar_decode_with_weak(const uint8_t *words, size_t bytes, uint64_t *raw,
    double *power, uint8_t *detections, int *present)
{
    return decode_frame(words, bytes, raw, power, detections, present, 1);
}

int p0_pl_os_cfar_decode_runtime_with_weak(
    const uint8_t *words, size_t bytes, size_t native_bins,
    uint64_t *canonical_raw, double *canonical_power,
    uint8_t *canonical_detections, int *present)
{
    size_t natural_bin;
    unsigned int reduction_shift;

    if (words == NULL || canonical_raw == NULL || canonical_power == NULL ||
        canonical_detections == NULL || present == NULL ||
        (native_bins != 4096U && native_bins != 8192U && native_bins != 16384U) ||
        bytes != native_bins * 8U)
        return P0_PL_OS_CFAR_INVALID_ARGUMENT;

    /* Keep the nominal 4096-bin path as lean as the established fixed-size
     * product.  The generic reducer clears and accumulates the canonical grid
     * and performs a division for every native bin; none of that work is
     * needed when the two grids are identical. */
    if (native_bins == P0_PL_OS_CFAR_FRAME_BINS)
        return decode_frame(words, bytes, canonical_raw, canonical_power,
                            canonical_detections, present, 1);

    reduction_shift = native_bins == 8192U ? 1U : 2U;
    memset(canonical_raw, 0, P0_PL_OS_CFAR_FRAME_BINS * sizeof(*canonical_raw));
    memset(canonical_detections, 0,
           P0_PL_OS_CFAR_FRAME_BINS * sizeof(*canonical_detections));
    for (natural_bin = 0U; natural_bin < native_bins; ++natural_bin) {
        size_t shifted_bin = natural_bin ^ (native_bins / 2U);
        size_t canonical_bin = shifted_bin >> reduction_shift;
        uint64_t word = load_u64_le(words + natural_bin * 8U);
        uint64_t value = word & P0_POWER_MASK;
        int evaluated = (word & P0_EVALUATED_MASK) != 0U;
        int detected = (word & P0_DETECTED_MASK) != 0U;
        int weak = (word & P0_WEAK_MASK) != 0U;
        int expected_evaluated = shifted_bin >= P0_PL_OS_CFAR_RADIUS &&
                                 shifted_bin < native_bins - P0_PL_OS_CFAR_RADIUS;

        if ((word & P0_V2_MASK) != P0_V2_MARKER ||
            evaluated != expected_evaluated || (detected && !evaluated) ||
            (weak && !evaluated) || (detected && !weak))
            return P0_PL_OS_CFAR_INVALID_FRAME;
        if (value > P0_POWER_MASK - canonical_raw[canonical_bin])
            canonical_raw[canonical_bin] = P0_POWER_MASK;
        else
            canonical_raw[canonical_bin] += value;
        if (detected)
            canonical_detections[canonical_bin] |= 1U;
        if (weak)
            canonical_detections[canonical_bin] |= 2U;
    }
    for (natural_bin = 0U; natural_bin < P0_PL_OS_CFAR_FRAME_BINS; ++natural_bin) {
        uint64_t value = canonical_raw[natural_bin];
        canonical_power[natural_bin] =
            (double)(uint32_t)(value >> 32U) * 4.0 +
            (double)(uint32_t)value / (double)P0_POWER_SCALE;
    }
    *present = 1;
    return P0_PL_OS_CFAR_OK;
}
