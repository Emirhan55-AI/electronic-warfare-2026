#include <assert.h>
#include <stdio.h>

#include "p0_fclk_guard_logic.h"

static const u32 golden_io_pll = 0x0001e000U;
static const u32 golden_clk = P0_FCLK_GUARD_GOLDEN_FCLK_CTRL;
static const u32 target_clk = P0_FCLK_GUARD_50MHZ_FCLK_CTRL;
static const u32 physical_target_clk =
    P0_FCLK_GUARD_PHYSICAL_50MHZ_FCLK_CTRL;

static void test_golden_decode(void)
{
    assert(p0_fclk_guard_io_pll_fbdiv(golden_io_pll) == 30U);
    assert(p0_fclk_guard_fclk_srcsel(golden_clk) == 0U);
    assert(p0_fclk_guard_fclk_div0(golden_clk) == 5U);
    assert(p0_fclk_guard_fclk_div1(golden_clk) == 2U);
    assert(p0_fclk_guard_io_pll_hz(golden_io_pll) == 1000000000ULL);
    assert(p0_fclk_guard_fclk_hz(golden_io_pll, golden_clk) ==
           100000000ULL);
    assert(p0_fclk_guard_validate_golden(golden_io_pll, golden_clk, 0U,
                                          0x0000000fU, 1U, 0U) == 0U);
}

static void test_target_decode(void)
{
    assert(p0_fclk_guard_fclk_div0(target_clk) == 5U);
    assert(p0_fclk_guard_fclk_div1(target_clk) == 4U);
    assert(p0_fclk_guard_fclk_hz(golden_io_pll, target_clk) ==
           50000000ULL);
    assert(p0_fclk_guard_validate_50mhz(golden_io_pll, target_clk, 1U,
                                         0x0000000fU, 1U, 0U, 1) == 0U);
    assert(p0_fclk_guard_fclk_srcsel(physical_target_clk) == 0U);
    assert(p0_fclk_guard_fclk_div0(physical_target_clk) == 20U);
    assert(p0_fclk_guard_fclk_div1(physical_target_clk) == 1U);
    assert(p0_fclk_guard_fclk_hz(golden_io_pll, physical_target_clk) ==
           50000000ULL);
    assert(p0_fclk_guard_fclk_ctrl_is_legal_50mhz(golden_io_pll,
                                                   physical_target_clk));
    assert(p0_fclk_guard_validate_50mhz(golden_io_pll, physical_target_clk,
                                         1U, 0x0000000fU, 1U, 0U, 1) == 0U);
}

static void test_ccf_rate_comparison_contract(void)
{
    assert(p0_fclk_guard_ccf_rate_matches_decoded(99999999ULL,
                                                   100000000ULL));
    assert(p0_fclk_guard_ccf_rate_matches_decoded(100000000ULL,
                                                   100000000ULL));
    assert(!p0_fclk_guard_ccf_rate_matches_decoded(99999998ULL,
                                                    100000000ULL));
    assert(p0_fclk_guard_ccf_rate_matches_decoded(100000001ULL,
                                                   100000000ULL));
    assert(!p0_fclk_guard_ccf_rate_matches_decoded(100000002ULL,
                                                    100000000ULL));
    assert(p0_fclk_guard_ccf_rate_matches_decoded(50000000ULL,
                                                   50000000ULL));
    assert(p0_fclk_guard_ccf_rate_matches_decoded(49999999ULL,
                                                   50000000ULL));
    assert(!p0_fclk_guard_ccf_rate_matches_decoded(49999998ULL,
                                                    50000000ULL));
}

static void test_state_classification(void)
{
    assert(p0_fclk_guard_classify_state(golden_io_pll, golden_clk, 0U,
                                         0x0000000fU, 1U, 0U) ==
           P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED);
    assert(p0_fclk_guard_classify_state(golden_io_pll, golden_clk, 1U,
                                         0x0000000fU, 1U, 0U) ==
           P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_ASSERTED);
    assert(p0_fclk_guard_classify_state(golden_io_pll, target_clk, 1U,
                                         0x0000000fU, 1U, 0U) ==
           P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED);
    assert(p0_fclk_guard_classify_state(golden_io_pll, target_clk, 0U,
                                         0x0000000fU, 1U, 0U) ==
           P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED);
    assert(p0_fclk_guard_classify_state(golden_io_pll, physical_target_clk,
                                         1U, 0x0000000fU, 1U, 0U) ==
           P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED);
    assert(p0_fclk_guard_classify_state(golden_io_pll, 0x00400800U, 0U,
                                         0x0000000fU, 1U, 0U) ==
           P0_FCLK_GUARD_STATE_UNKNOWN);

    /* Clock STATUS must not depend on an unsafe AXI-security MMIO read. */
    assert(p0_fclk_guard_classify_clock_state(golden_io_pll, golden_clk, 0U,
                                               0x0000000fU) ==
           P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED);
    assert(p0_fclk_guard_classify_clock_state(golden_io_pll, target_clk, 1U,
                                               0x0000000fU) ==
           P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED);
    assert(p0_fclk_guard_classify_clock_state(golden_io_pll,
                                               physical_target_clk, 1U,
                                               0x0000000fU) ==
           P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED);
}

static void test_state_transitions(void)
{
    u32 next;

    assert(p0_fclk_guard_transition_allowed(
        P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED,
        P0_FCLK_GUARD_OPERATION_APPLY_50MHZ, &next));
    assert(next == P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED);
    assert(p0_fclk_guard_transition_allowed(
        P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED,
        P0_FCLK_GUARD_OPERATION_RELEASE_PL_RESET, &next));
    assert(next == P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED);
    assert(p0_fclk_guard_transition_allowed(
        P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED,
        P0_FCLK_GUARD_OPERATION_ASSERT_PL_RESET, &next));
    assert(next == P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED);
    assert(p0_fclk_guard_transition_allowed(
        P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED,
        P0_FCLK_GUARD_OPERATION_RESTORE_100MHZ, &next));
    assert(next == P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED);
    assert(p0_fclk_guard_transition_allowed(
        P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_ASSERTED,
        P0_FCLK_GUARD_OPERATION_RESTORE_100MHZ, &next));
    assert(next == P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED);

    assert(!p0_fclk_guard_transition_allowed(
        P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED,
        P0_FCLK_GUARD_OPERATION_RELEASE_PL_RESET, &next));
    assert(!p0_fclk_guard_transition_allowed(
        P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED,
        P0_FCLK_GUARD_OPERATION_APPLY_50MHZ, &next));
    assert(!p0_fclk_guard_transition_allowed(
        P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED,
        P0_FCLK_GUARD_OPERATION_ASSERT_PL_RESET, &next));
    assert(!p0_fclk_guard_transition_allowed(
        P0_FCLK_GUARD_STATE_UNKNOWN,
        P0_FCLK_GUARD_OPERATION_RESTORE_100MHZ, &next));
}

static void test_rejections(void)
{
    assert(p0_fclk_guard_validate_golden(0x0001d000U, golden_clk, 0U,
                                          0x0000000fU, 1U, 0U) &
           P0_FCLK_GUARD_VALIDATE_IO_PLL);
    assert(p0_fclk_guard_validate_golden(golden_io_pll, golden_clk, 0U,
                                          0x0000000eU, 1U, 0U) &
           P0_FCLK_GUARD_VALIDATE_LEVEL_SHIFTER);
    assert(p0_fclk_guard_validate_golden(golden_io_pll, golden_clk, 0U,
                                          0x0000000fU, 0U, 0U) &
           P0_FCLK_GUARD_VALIDATE_GP0_SECURITY);
    assert(p0_fclk_guard_validate_golden(golden_io_pll, golden_clk, 0U,
                                          0x0000000fU, 1U, 1U) &
           P0_FCLK_GUARD_VALIDATE_HP0_AFI);
    assert(p0_fclk_guard_validate_golden_clock(golden_io_pll, golden_clk,
                                                0U, 0x0000000fU) == 0U);
    assert(p0_fclk_guard_validate_axi_prereqs(1U, 0U) == 0U);
    assert(p0_fclk_guard_validate_axi_prereqs(0U, 0U) &
           P0_FCLK_GUARD_VALIDATE_GP0_SECURITY);
    assert(p0_fclk_guard_validate_axi_prereqs(1U, 1U) &
           P0_FCLK_GUARD_VALIDATE_HP0_AFI);
    assert(p0_fclk_guard_validate_golden(golden_io_pll, 0x00400800U, 0U,
                                          0x0000000fU, 1U, 0U) &
           P0_FCLK_GUARD_VALIDATE_FCLK_CTRL);
    assert(!p0_fclk_guard_fclk_ctrl_is_legal_50mhz(golden_io_pll,
                                                    0x80101400U));
    assert(!p0_fclk_guard_fclk_ctrl_is_legal_50mhz(golden_io_pll,
                                                    0x00100000U));
    assert(p0_fclk_guard_classify_clock_state(golden_io_pll, 0x80101400U,
                                               1U, 0x0000000fU) ==
           P0_FCLK_GUARD_STATE_UNKNOWN);
    assert(!p0_fclk_guard_clock_rounds_exact(49999999L,
                                              P0_FCLK_GUARD_TARGET_FCLK_HZ));
    assert(!p0_fclk_guard_clock_rounds_exact(-1L,
                                              P0_FCLK_GUARD_TARGET_FCLK_HZ));
    assert(p0_fclk_guard_clock_rounds_exact(50000000L,
                                             P0_FCLK_GUARD_TARGET_FCLK_HZ));
}

int main(void)
{
    test_golden_decode();
    test_target_decode();
    test_ccf_rate_comparison_contract();
    test_state_classification();
    test_state_transitions();
    test_rejections();
    puts("p0_fclk_guard_logic: PASS");
    return 0;
}
