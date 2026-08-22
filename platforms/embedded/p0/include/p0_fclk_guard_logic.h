#ifndef P0_FCLK_GUARD_LOGIC_H
#define P0_FCLK_GUARD_LOGIC_H

/*
 * P0 FCLK guard saf çözümleme/doğrulama sözleşmesi.
 *
 * Bu başlık hem çekirdek modülü hem de host birim testi tarafından kullanılır.
 * Donanım erişimi, MMIO adresi veya yan etkili işlem içermez.
 */

#ifdef __KERNEL__
#include <linux/math64.h>
#include <linux/types.h>
#else
#include <stdint.h>
typedef uint32_t u32;
typedef uint64_t u64;
#endif

#define P0_FCLK_GUARD_PS_CLK_NUM_HZ 100000000ULL
#define P0_FCLK_GUARD_PS_CLK_DEN 3ULL

#define P0_FCLK_GUARD_IO_PLL_FBDIV_SHIFT 12U
#define P0_FCLK_GUARD_IO_PLL_FBDIV_MASK 0x0007f000U

#define P0_FCLK_GUARD_FCLK_SRCSEL_SHIFT 4U
#define P0_FCLK_GUARD_FCLK_SRCSEL_MASK 0x00000030U
#define P0_FCLK_GUARD_FCLK_DIV0_SHIFT 8U
#define P0_FCLK_GUARD_FCLK_DIV0_MASK 0x00003f00U
#define P0_FCLK_GUARD_FCLK_DIV1_SHIFT 20U
#define P0_FCLK_GUARD_FCLK_DIV1_MASK 0x03f00000U
#define P0_FCLK_GUARD_FCLK_CTRL_DOCUMENTED_MASK \
    (P0_FCLK_GUARD_FCLK_SRCSEL_MASK | P0_FCLK_GUARD_FCLK_DIV0_MASK | \
     P0_FCLK_GUARD_FCLK_DIV1_MASK)

#define P0_FCLK_GUARD_IO_PLL_HZ 1000000000ULL
#define P0_FCLK_GUARD_GOLDEN_IO_PLL_FBDIV 30U
#define P0_FCLK_GUARD_GOLDEN_FCLK_CTRL 0x00200500U
/* A reference encoding only; 50 MHz is semantically validated, not matched. */
#define P0_FCLK_GUARD_50MHZ_FCLK_CTRL 0x00400500U
#define P0_FCLK_GUARD_PHYSICAL_50MHZ_FCLK_CTRL 0x00101400U
#define P0_FCLK_GUARD_GOLDEN_FCLK_HZ 100000000ULL
#define P0_FCLK_GUARD_TARGET_FCLK_HZ 50000000ULL
/*
 * The golden DT describes ps_clk as the integer 33333333 Hz.  The Zynq CCF
 * therefore recalculates fclk0 as 33333333 * 30 / 5 / 2 = 99999999 Hz,
 * while the guard's exact hardware decode uses the board's 100000000 / 3
 * source-clock rational and obtains 100000000 Hz.  This bound is only for
 * comparing a CCF observed rate with an independently decoded hardware rate;
 * requested/rounded rates remain exact requirements.
 */
#define P0_FCLK_GUARD_CCF_RATE_COMPARE_TOLERANCE_HZ 1ULL

#define P0_FCLK_GUARD_GOLDEN_DIV0 5U
#define P0_FCLK_GUARD_GOLDEN_DIV1 2U
#define P0_FCLK_GUARD_TARGET_DIV1 4U
#define P0_FCLK_GUARD_SRCSEL_IO_PLL 0U

#define P0_FCLK_GUARD_FPGA0_OUT_RST_BIT 0U
#define P0_FCLK_GUARD_FPGA0_OUT_RST_MASK 0x00000001U

#ifndef P0_FCLK_GUARD_STATE_UNKNOWN
#define P0_FCLK_GUARD_STATE_UNKNOWN 0U
#define P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED 1U
#define P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED 2U
#define P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED 3U
#define P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_ASSERTED 4U
#endif

#define P0_FCLK_GUARD_OPERATION_APPLY_50MHZ 1U
#define P0_FCLK_GUARD_OPERATION_ASSERT_PL_RESET 2U
#define P0_FCLK_GUARD_OPERATION_RELEASE_PL_RESET 3U
#define P0_FCLK_GUARD_OPERATION_RESTORE_100MHZ 4U

enum p0_fclk_guard_validation_error {
    P0_FCLK_GUARD_VALIDATE_IO_PLL = 1U << 0,
    P0_FCLK_GUARD_VALIDATE_FCLK_CTRL = 1U << 1,
    P0_FCLK_GUARD_VALIDATE_FPGA_RESET = 1U << 2,
    P0_FCLK_GUARD_VALIDATE_LEVEL_SHIFTER = 1U << 3,
    P0_FCLK_GUARD_VALIDATE_GP0_SECURITY = 1U << 4,
    P0_FCLK_GUARD_VALIDATE_HP0_AFI = 1U << 5,
    P0_FCLK_GUARD_VALIDATE_CCF_ROUND_RATE = 1U << 6,
    P0_FCLK_GUARD_VALIDATE_CCF_CURRENT_RATE = 1U << 7,
    P0_FCLK_GUARD_VALIDATE_CCF_ENABLED = 1U << 8,
};

static inline u64 p0_fclk_guard_divide_u64(u64 dividend, u32 divisor)
{
#ifdef __KERNEL__
    return div_u64(dividend, divisor);
#else
    return dividend / divisor;
#endif
}

static inline int p0_fclk_guard_ccf_rate_matches_decoded(u64 ccf_rate,
                                                          u64 decoded_rate)
{
    if (ccf_rate >= decoded_rate)
        return ccf_rate - decoded_rate <=
               P0_FCLK_GUARD_CCF_RATE_COMPARE_TOLERANCE_HZ;

    return decoded_rate - ccf_rate <=
           P0_FCLK_GUARD_CCF_RATE_COMPARE_TOLERANCE_HZ;
}

static inline u32 p0_fclk_guard_io_pll_fbdiv(u32 value)
{
    return (value & P0_FCLK_GUARD_IO_PLL_FBDIV_MASK) >>
           P0_FCLK_GUARD_IO_PLL_FBDIV_SHIFT;
}

static inline u32 p0_fclk_guard_fclk_srcsel(u32 value)
{
    return (value & P0_FCLK_GUARD_FCLK_SRCSEL_MASK) >>
           P0_FCLK_GUARD_FCLK_SRCSEL_SHIFT;
}

static inline u32 p0_fclk_guard_fclk_div0(u32 value)
{
    return (value & P0_FCLK_GUARD_FCLK_DIV0_MASK) >>
           P0_FCLK_GUARD_FCLK_DIV0_SHIFT;
}

static inline u32 p0_fclk_guard_fclk_div1(u32 value)
{
    return (value & P0_FCLK_GUARD_FCLK_DIV1_MASK) >>
           P0_FCLK_GUARD_FCLK_DIV1_SHIFT;
}

static inline u64 p0_fclk_guard_io_pll_hz(u32 io_pll_ctrl)
{
    return p0_fclk_guard_divide_u64(
        P0_FCLK_GUARD_PS_CLK_NUM_HZ *
        p0_fclk_guard_io_pll_fbdiv(io_pll_ctrl),
        P0_FCLK_GUARD_PS_CLK_DEN);
}

static inline u64 p0_fclk_guard_fclk_hz(u32 io_pll_ctrl, u32 fclk_ctrl)
{
    u32 div0 = p0_fclk_guard_fclk_div0(fclk_ctrl);
    u32 div1 = p0_fclk_guard_fclk_div1(fclk_ctrl);

    if (p0_fclk_guard_fclk_srcsel(fclk_ctrl) !=
        P0_FCLK_GUARD_SRCSEL_IO_PLL || !div0 || !div1)
        return 0;

    return p0_fclk_guard_divide_u64(
        p0_fclk_guard_divide_u64(
            p0_fclk_guard_io_pll_hz(io_pll_ctrl), div0), div1);
}

static inline int p0_fclk_guard_fclk_ctrl_has_only_documented_fields(
    u32 fclk_ctrl)
{
    return !(fclk_ctrl & ~P0_FCLK_GUARD_FCLK_CTRL_DOCUMENTED_MASK);
}

static inline int p0_fclk_guard_fclk_ctrl_is_legal_50mhz(
    u32 io_pll_ctrl, u32 fclk_ctrl)
{
    u32 div0 = p0_fclk_guard_fclk_div0(fclk_ctrl);
    u32 div1 = p0_fclk_guard_fclk_div1(fclk_ctrl);

    return p0_fclk_guard_fclk_ctrl_has_only_documented_fields(fclk_ctrl) &&
           p0_fclk_guard_fclk_srcsel(fclk_ctrl) ==
               P0_FCLK_GUARD_SRCSEL_IO_PLL &&
           div0 && div1 &&
           p0_fclk_guard_fclk_hz(io_pll_ctrl, fclk_ctrl) ==
               P0_FCLK_GUARD_TARGET_FCLK_HZ;
}

static inline u32 p0_fclk_guard_validate_clock_common(u32 io_pll_ctrl,
                                                        u32 fpga_rst_ctrl,
                                                        u32 lvl_shftr_en)
{
    u32 errors = 0;

    if (p0_fclk_guard_io_pll_fbdiv(io_pll_ctrl) !=
            P0_FCLK_GUARD_GOLDEN_IO_PLL_FBDIV ||
        p0_fclk_guard_io_pll_hz(io_pll_ctrl) !=
            P0_FCLK_GUARD_IO_PLL_HZ)
        errors |= P0_FCLK_GUARD_VALIDATE_IO_PLL;
    if (fpga_rst_ctrl != 0)
        errors |= P0_FCLK_GUARD_VALIDATE_FPGA_RESET;
    if ((lvl_shftr_en & 0x0000000fU) != 0x0000000fU)
        errors |= P0_FCLK_GUARD_VALIDATE_LEVEL_SHIFTER;

    return errors;
}

static inline u32 p0_fclk_guard_validate_axi_prereqs(u32 security_fssw_s0,
                                                       u32 tz_fpga_afi)
{
    u32 errors = 0;

    if (!(security_fssw_s0 & 0x00000001U))
        errors |= P0_FCLK_GUARD_VALIDATE_GP0_SECURITY;
    if (tz_fpga_afi & 0x00000001U)
        errors |= P0_FCLK_GUARD_VALIDATE_HP0_AFI;

    return errors;
}

static inline u32 p0_fclk_guard_validate_common(u32 io_pll_ctrl,
                                                  u32 fpga_rst_ctrl,
                                                  u32 lvl_shftr_en,
                                                  u32 security_fssw_s0,
                                                  u32 tz_fpga_afi)
{
    return p0_fclk_guard_validate_clock_common(io_pll_ctrl, fpga_rst_ctrl,
                                                lvl_shftr_en) |
           p0_fclk_guard_validate_axi_prereqs(security_fssw_s0,
                                              tz_fpga_afi);
}

static inline u32 p0_fclk_guard_validate_golden_clock(u32 io_pll_ctrl,
                                                        u32 fclk_ctrl,
                                                        u32 fpga_rst_ctrl,
                                                        u32 lvl_shftr_en)
{
    u32 errors = p0_fclk_guard_validate_clock_common(io_pll_ctrl,
                                                      fpga_rst_ctrl,
                                                      lvl_shftr_en);

    if (fclk_ctrl != P0_FCLK_GUARD_GOLDEN_FCLK_CTRL ||
        p0_fclk_guard_fclk_hz(io_pll_ctrl, fclk_ctrl) !=
            P0_FCLK_GUARD_GOLDEN_FCLK_HZ)
        errors |= P0_FCLK_GUARD_VALIDATE_FCLK_CTRL;

    return errors;
}

static inline u32 p0_fclk_guard_validate_50mhz_clock(
    u32 io_pll_ctrl, u32 fclk_ctrl, u32 fpga_rst_ctrl, u32 lvl_shftr_en,
    int require_reset_asserted)
{
    u32 errors = p0_fclk_guard_validate_clock_common(
        io_pll_ctrl,
        require_reset_asserted ?
            (fpga_rst_ctrl & ~P0_FCLK_GUARD_FPGA0_OUT_RST_MASK) :
            fpga_rst_ctrl,
        lvl_shftr_en);

    if (!p0_fclk_guard_fclk_ctrl_is_legal_50mhz(io_pll_ctrl, fclk_ctrl))
        errors |= P0_FCLK_GUARD_VALIDATE_FCLK_CTRL;
    if (require_reset_asserted &&
        !(fpga_rst_ctrl & P0_FCLK_GUARD_FPGA0_OUT_RST_MASK))
        errors |= P0_FCLK_GUARD_VALIDATE_FPGA_RESET;

    return errors;
}

static inline u32 p0_fclk_guard_validate_golden(u32 io_pll_ctrl,
                                                  u32 fclk_ctrl,
                                                  u32 fpga_rst_ctrl,
                                                  u32 lvl_shftr_en,
                                                  u32 security_fssw_s0,
                                                  u32 tz_fpga_afi)
{
    u32 errors = p0_fclk_guard_validate_common(io_pll_ctrl, fpga_rst_ctrl,
                                                lvl_shftr_en,
                                                security_fssw_s0,
                                                tz_fpga_afi);

    if (fclk_ctrl != P0_FCLK_GUARD_GOLDEN_FCLK_CTRL ||
        p0_fclk_guard_fclk_hz(io_pll_ctrl, fclk_ctrl) !=
            P0_FCLK_GUARD_GOLDEN_FCLK_HZ)
        errors |= P0_FCLK_GUARD_VALIDATE_FCLK_CTRL;

    return errors;
}

static inline u32 p0_fclk_guard_validate_50mhz(u32 io_pll_ctrl,
                                                 u32 fclk_ctrl,
                                                 u32 fpga_rst_ctrl,
                                                 u32 lvl_shftr_en,
                                                 u32 security_fssw_s0,
                                                 u32 tz_fpga_afi,
                                                 int require_reset_asserted)
{
    u32 errors = p0_fclk_guard_validate_common(io_pll_ctrl,
                                                require_reset_asserted ?
                                                    (fpga_rst_ctrl &
                                                     ~P0_FCLK_GUARD_FPGA0_OUT_RST_MASK) :
                                                    fpga_rst_ctrl,
                                                lvl_shftr_en,
                                                security_fssw_s0,
                                                tz_fpga_afi);

    if (!p0_fclk_guard_fclk_ctrl_is_legal_50mhz(io_pll_ctrl, fclk_ctrl))
        errors |= P0_FCLK_GUARD_VALIDATE_FCLK_CTRL;
    if (require_reset_asserted &&
        !(fpga_rst_ctrl & P0_FCLK_GUARD_FPGA0_OUT_RST_MASK))
        errors |= P0_FCLK_GUARD_VALIDATE_FPGA_RESET;

    return errors;
}

static inline u32 p0_fclk_guard_classify_state(u32 io_pll_ctrl,
                                                u32 fclk_ctrl,
                                                u32 fpga_rst_ctrl,
                                                u32 lvl_shftr_en,
                                                u32 security_fssw_s0,
                                                u32 tz_fpga_afi)
{
    u32 common_without_reset = p0_fclk_guard_validate_common(
        io_pll_ctrl,
        fpga_rst_ctrl & ~P0_FCLK_GUARD_FPGA0_OUT_RST_MASK,
        lvl_shftr_en, security_fssw_s0, tz_fpga_afi);

    if (fclk_ctrl == P0_FCLK_GUARD_GOLDEN_FCLK_CTRL &&
        !common_without_reset) {
        if (fpga_rst_ctrl & P0_FCLK_GUARD_FPGA0_OUT_RST_MASK)
            return P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_ASSERTED;
        return P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED;
    }
    if (p0_fclk_guard_fclk_ctrl_is_legal_50mhz(io_pll_ctrl, fclk_ctrl) &&
        !common_without_reset) {
        if (fpga_rst_ctrl & P0_FCLK_GUARD_FPGA0_OUT_RST_MASK)
            return P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED;
        return P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED;
    }
    return P0_FCLK_GUARD_STATE_UNKNOWN;
}

static inline u32 p0_fclk_guard_classify_clock_state(u32 io_pll_ctrl,
                                                      u32 fclk_ctrl,
                                                      u32 fpga_rst_ctrl,
                                                      u32 lvl_shftr_en)
{
    u32 common_without_reset = p0_fclk_guard_validate_clock_common(
        io_pll_ctrl,
        fpga_rst_ctrl & ~P0_FCLK_GUARD_FPGA0_OUT_RST_MASK,
        lvl_shftr_en);

    if (fclk_ctrl == P0_FCLK_GUARD_GOLDEN_FCLK_CTRL &&
        !common_without_reset) {
        if (fpga_rst_ctrl & P0_FCLK_GUARD_FPGA0_OUT_RST_MASK)
            return P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_ASSERTED;
        return P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED;
    }
    if (p0_fclk_guard_fclk_ctrl_is_legal_50mhz(io_pll_ctrl, fclk_ctrl) &&
        !common_without_reset) {
        if (fpga_rst_ctrl & P0_FCLK_GUARD_FPGA0_OUT_RST_MASK)
            return P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED;
        return P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED;
    }
    return P0_FCLK_GUARD_STATE_UNKNOWN;
}

static inline int p0_fclk_guard_transition_allowed(u32 previous_state,
                                                    u32 operation,
                                                    u32 *resulting_state)
{
    switch (operation) {
    case P0_FCLK_GUARD_OPERATION_APPLY_50MHZ:
        if (previous_state ==
            P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED) {
            *resulting_state = P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED;
            return 1;
        }
        break;
    case P0_FCLK_GUARD_OPERATION_ASSERT_PL_RESET:
        if (previous_state ==
            P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED) {
            *resulting_state = P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED;
            return 1;
        }
        break;
    case P0_FCLK_GUARD_OPERATION_RELEASE_PL_RESET:
        if (previous_state ==
            P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED) {
            *resulting_state = P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED;
            return 1;
        }
        break;
    case P0_FCLK_GUARD_OPERATION_RESTORE_100MHZ:
        if (previous_state == P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED ||
            previous_state ==
            P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_ASSERTED) {
            *resulting_state =
                P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED;
            return 1;
        }
        break;
    default:
        break;
    }
    *resulting_state = P0_FCLK_GUARD_STATE_UNKNOWN;
    return 0;
}

static inline int p0_fclk_guard_clock_rounds_exact(long rounded_rate,
                                                     u64 expected_rate)
{
    return rounded_rate >= 0 && (u64)rounded_rate == expected_rate;
}

#endif
