// SPDX-License-Identifier: GPL-2.0-only
/*
 * P0 FCLK guard
 *
 * This module intentionally never maps or accesses the P0 AXI DMA window.
 * Module insertion only registers /dev/p0-fclk-guard; all hardware writes
 * require one of the explicit ioctl operations below.
 */

#include <linux/clk.h>
#include <linux/build_bug.h>
#include <linux/fs.h>
#include <linux/io.h>
#include <linux/miscdevice.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_clk.h>
#include <linux/string.h>
#include <linux/uaccess.h>

#include "p0_fclk_guard_logic.h"
#include "p0_fclk_guard_uapi.h"

#define P0_SLCR_PHYS 0xf8000000UL
#define P0_SLCR_SIZE 0x1000UL

#define P0_SLCR_LOCK_OFFSET 0x0004U
#define P0_SLCR_UNLOCK_OFFSET 0x0008U
#define P0_SLCR_IO_PLL_CTRL_OFFSET 0x0108U
#define P0_SLCR_FPGA0_CLK_CTRL_OFFSET 0x0170U
#define P0_SLCR_FPGA_RST_CTRL_OFFSET 0x0240U
#define P0_SLCR_LVL_SHFTR_EN_OFFSET 0x0900U

#define P0_SLCR_UNLOCK_KEY 0x0000df0dU
#define P0_SLCR_LOCK_KEY 0x0000767bU
#define P0_FCLK0_CLOCK_INDEX 15U

/* Keep every default-status MMIO offset within the one SLCR mapping. */
static_assert(P0_SLCR_LOCK_OFFSET <= P0_SLCR_SIZE - sizeof(u32));
static_assert(P0_SLCR_UNLOCK_OFFSET <= P0_SLCR_SIZE - sizeof(u32));
static_assert(P0_SLCR_IO_PLL_CTRL_OFFSET <= P0_SLCR_SIZE - sizeof(u32));
static_assert(P0_SLCR_FPGA0_CLK_CTRL_OFFSET <= P0_SLCR_SIZE - sizeof(u32));
static_assert(P0_SLCR_FPGA_RST_CTRL_OFFSET <= P0_SLCR_SIZE - sizeof(u32));
static_assert(P0_SLCR_LVL_SHFTR_EN_OFFSET <= P0_SLCR_SIZE - sizeof(u32));

struct p0_fclk_guard {
    void __iomem *slcr;
    struct mutex lock;
    struct miscdevice misc;
    bool active_transaction;
    bool clock_enable_owned;
    u32 last_status_stage;
};

static struct p0_fclk_guard p0_guard;
static bool p0_status_trace;

module_param_named(status_trace, p0_status_trace, bool, 0644);
MODULE_PARM_DESC(status_trace,
                 "Log bounded p0-fclk-guard status stage markers");

static void p0_fclk_guard_status_mark(struct p0_fclk_guard *guard,
                                       u32 stage, const char *name)
{
    WRITE_ONCE(guard->last_status_stage, stage);
    if (READ_ONCE(p0_status_trace))
        pr_info("p0-fclk-guard: STATUS_STAGE_%02u_%s\n", stage, name);
}

static void p0_fclk_guard_apply_mark(
    struct p0_fclk_guard_transition *transition, u32 stage,
    const char *name)
{
    transition->apply.last_stage = stage;
    if (READ_ONCE(p0_status_trace))
        pr_info("p0-fclk-guard: APPLY_STAGE_%02u_%s\n", stage, name);
}

static void p0_fclk_guard_capture_apply_status(
    struct p0_fclk_guard_apply_diagnostics *diagnostics,
    const struct p0_fclk_guard_status *status, bool after)
{
    if (after) {
        diagnostics->ccf_rate_after_hz = status->ccf_current_rate_hz;
        diagnostics->fpga0_clk_ctrl_after = status->fpga0_clk_ctrl;
        diagnostics->decoded_fclk0_after_hz = status->decoded_fclk0_hz;
        diagnostics->fpga_rst_ctrl_after = status->fpga_rst_ctrl;
        return;
    }

    diagnostics->ccf_rate_before_hz = status->ccf_current_rate_hz;
    diagnostics->fpga0_clk_ctrl_before = status->fpga0_clk_ctrl;
    diagnostics->decoded_fclk0_before_hz = status->decoded_fclk0_hz;
    diagnostics->fpga_rst_ctrl_before = status->fpga_rst_ctrl;
}

static void p0_fclk_guard_slcr_unlock(struct p0_fclk_guard *guard)
{
    writel(P0_SLCR_UNLOCK_KEY, guard->slcr + P0_SLCR_UNLOCK_OFFSET);
}

static void p0_fclk_guard_slcr_lock(struct p0_fclk_guard *guard)
{
    writel(P0_SLCR_LOCK_KEY, guard->slcr + P0_SLCR_LOCK_OFFSET);
}

static struct clk *p0_fclk_guard_get_fclk(void)
{
    struct device_node *node;
    struct of_phandle_args clkspec = { };
    struct clk *clock;

    node = of_find_compatible_node(NULL, NULL, "xlnx,ps7-clkc");
    if (!node)
        return ERR_PTR(-ENODEV);

    /*
     * node is the clock provider, not a consumer with a "clocks" property.
     * Pass its onecell provider argument directly instead of using of_clk_get.
     */
    clkspec.np = node;
    clkspec.args_count = 1;
    clkspec.args[0] = P0_FCLK0_CLOCK_INDEX;
    clock = of_clk_get_from_provider(&clkspec);
    of_node_put(node);
    return clock;
}

static void p0_fclk_guard_read_registers(struct p0_fclk_guard *guard,
                                          struct p0_fclk_guard_status *status)
{
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_IO_PLL_ENTER,
                              "IO_PLL_ENTER");
    status->io_pll_ctrl = readl(guard->slcr + P0_SLCR_IO_PLL_CTRL_OFFSET);
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_IO_PLL_OK,
                              "IO_PLL_OK");
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_FPGA0_CLK_ENTER,
                              "FPGA0_CLK_ENTER");
    status->fpga0_clk_ctrl =
        readl(guard->slcr + P0_SLCR_FPGA0_CLK_CTRL_OFFSET);
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_FPGA0_CLK_OK,
                              "FPGA0_CLK_OK");
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_FPGA_RST_ENTER,
                              "FPGA_RST_ENTER");
    status->fpga_rst_ctrl =
        readl(guard->slcr + P0_SLCR_FPGA_RST_CTRL_OFFSET);
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_FPGA_RST_OK,
                              "FPGA_RST_OK");
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_LVL_SHFTR_ENTER,
                              "LVL_SHFTR_ENTER");
    status->lvl_shftr_en =
        readl(guard->slcr + P0_SLCR_LVL_SHFTR_EN_OFFSET);
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_LVL_SHFTR_OK,
                              "LVL_SHFTR_OK");

    status->io_pll_fbdiv =
        p0_fclk_guard_io_pll_fbdiv(status->io_pll_ctrl);
    status->fclk_srcsel =
        p0_fclk_guard_fclk_srcsel(status->fpga0_clk_ctrl);
    status->fclk_div0 =
        p0_fclk_guard_fclk_div0(status->fpga0_clk_ctrl);
    status->fclk_div1 =
        p0_fclk_guard_fclk_div1(status->fpga0_clk_ctrl);
    status->decoded_io_pll_hz =
        p0_fclk_guard_io_pll_hz(status->io_pll_ctrl);
    status->decoded_fclk0_hz =
        p0_fclk_guard_fclk_hz(status->io_pll_ctrl,
                               status->fpga0_clk_ctrl);
}

static int p0_fclk_guard_read_ccf(struct p0_fclk_guard *guard,
                                  struct p0_fclk_guard_status *status)
{
    struct clk *clock;
    long rounded;

    /*
     * The target kernel does not export a live clock-name or enable-state
     * query to external modules.  The fixed DT clock index below is the
     * supported identity; do not fabricate either unavailable observation.
     */
    strscpy(status->ccf_clock_name, "fclk0",
            sizeof(status->ccf_clock_name));
    status->ccf_enabled = P0_FCLK_GUARD_CCF_ENABLED_UNKNOWN;
    status->status_flags |=
        P0_FCLK_GUARD_STATUS_CCF_ENABLED_STATE_UNAVAILABLE |
        P0_FCLK_GUARD_STATUS_CCF_ROUND_NOT_PROBED;
    status->ccf_round_50mhz_hz = -ENODATA;
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_CCF_LOOKUP_ENTER,
                              "CCF_LOOKUP_ENTER");
    clock = p0_fclk_guard_get_fclk();
    if (IS_ERR(clock)) {
        status->ccf_errno = PTR_ERR(clock);
        return status->ccf_errno;
    }

    status->status_flags |= P0_FCLK_GUARD_STATUS_CCF_RESOLVED;
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_CCF_LOOKUP_OK,
                              "CCF_LOOKUP_OK");
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_CCF_RATE_ENTER,
                              "CCF_RATE_ENTER");
    status->ccf_current_rate_hz = clk_get_rate(clock);
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_CCF_RATE_OK,
                              "CCF_RATE_OK");
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_CCF_ROUND_ENTER,
                              "CCF_ROUND_ENTER");
    rounded = clk_round_rate(clock, P0_FCLK_GUARD_TARGET_FCLK_HZ);
    status->ccf_round_50mhz_hz = rounded;
    status->status_flags &= ~P0_FCLK_GUARD_STATUS_CCF_ROUND_NOT_PROBED;
    if (rounded < 0) {
        status->ccf_errno = rounded;
        clk_put(clock);
        return status->ccf_errno;
    }
    if (p0_fclk_guard_clock_rounds_exact(
            rounded, P0_FCLK_GUARD_TARGET_FCLK_HZ))
        status->status_flags |= P0_FCLK_GUARD_STATUS_CCF_ROUND_50_EXACT;
    p0_fclk_guard_status_mark(guard,
                              P0_FCLK_GUARD_STATUS_STAGE_CCF_ROUND_OK,
                              "CCF_ROUND_OK");
    clk_put(clock);
    return 0;
}

static int p0_fclk_guard_collect_status(struct p0_fclk_guard *guard,
                                        struct p0_fclk_guard_status *status)
{
    u32 golden_errors;
    u32 safe_50_errors;
    int ccf_result;

    memset(status, 0, sizeof(*status));
    status->abi_version = P0_FCLK_GUARD_ABI_VERSION;
    status->security_fssw_s0 = P0_FCLK_GUARD_REGISTER_UNKNOWN;
    status->tz_fpga_afi = P0_FCLK_GUARD_REGISTER_UNKNOWN;
    status->status_flags |=
        P0_FCLK_GUARD_STATUS_GP0_SECURITY_NOT_SAFELY_PROBED |
        P0_FCLK_GUARD_STATUS_HP0_SECURITY_NOT_SAFELY_PROBED;
    p0_fclk_guard_status_mark(guard, P0_FCLK_GUARD_STATUS_STAGE_ENTER,
                              "ENTER");
    p0_fclk_guard_read_registers(guard, status);
    status->current_state = p0_fclk_guard_classify_clock_state(
        status->io_pll_ctrl, status->fpga0_clk_ctrl,
        status->fpga_rst_ctrl, status->lvl_shftr_en);
    ccf_result = p0_fclk_guard_read_ccf(guard, status);

    golden_errors = p0_fclk_guard_validate_golden_clock(
        status->io_pll_ctrl, status->fpga0_clk_ctrl,
        status->fpga_rst_ctrl, status->lvl_shftr_en);
    safe_50_errors = p0_fclk_guard_validate_50mhz_clock(
        status->io_pll_ctrl, status->fpga0_clk_ctrl,
        status->fpga_rst_ctrl, status->lvl_shftr_en, 1);
    if (!(status->status_flags & P0_FCLK_GUARD_STATUS_CCF_RESOLVED))
        golden_errors |= P0_FCLK_GUARD_VALIDATE_CCF_ROUND_RATE;
    if (!p0_fclk_guard_ccf_rate_matches_decoded(
            status->ccf_current_rate_hz, P0_FCLK_GUARD_GOLDEN_FCLK_HZ))
        golden_errors |= P0_FCLK_GUARD_VALIDATE_CCF_CURRENT_RATE;
    if (!p0_fclk_guard_ccf_rate_matches_decoded(
            status->ccf_current_rate_hz, P0_FCLK_GUARD_TARGET_FCLK_HZ))
        safe_50_errors |= P0_FCLK_GUARD_VALIDATE_CCF_CURRENT_RATE;
    if (!p0_fclk_guard_ccf_rate_matches_decoded(
            status->ccf_current_rate_hz, status->decoded_fclk0_hz)) {
        golden_errors |= P0_FCLK_GUARD_VALIDATE_CCF_CURRENT_RATE;
        safe_50_errors |= P0_FCLK_GUARD_VALIDATE_CCF_CURRENT_RATE;
    }
    if (!(status->status_flags & P0_FCLK_GUARD_STATUS_CCF_RESOLVED) ||
        !(status->status_flags & P0_FCLK_GUARD_STATUS_CCF_ROUND_50_EXACT))
        safe_50_errors |= P0_FCLK_GUARD_VALIDATE_CCF_ROUND_RATE;
    /*
     * The external module cannot inspect CCF's internal enable reference.
     * Keep that fact visible in status_flags, but do not reject an otherwise
     * fully observed reset-asserted hardware state on an unavailable API.
     */
    status->golden_validation_errors = golden_errors;
    status->safe_50_validation_errors = safe_50_errors;
    if (!golden_errors)
        status->status_flags |= P0_FCLK_GUARD_STATUS_GOLDEN_PRECONDITIONS;
    if (!safe_50_errors)
        status->status_flags |= P0_FCLK_GUARD_STATUS_SAFE_50MHZ;
    if (status->current_state == P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED &&
        safe_50_errors)
        status->current_state = P0_FCLK_GUARD_STATE_UNKNOWN;
    if (status->fpga_rst_ctrl & P0_FCLK_GUARD_FPGA0_OUT_RST_MASK)
        status->status_flags |= P0_FCLK_GUARD_STATUS_RESET0_ASSERTED;
    if (guard->clock_enable_owned)
        status->status_flags |= P0_FCLK_GUARD_STATUS_GUARD_OWNS_CLOCK_ENABLE;
    if (guard->active_transaction)
        status->status_flags |= P0_FCLK_GUARD_STATUS_ACTIVE_TRANSACTION;
    if (!ccf_result)
        p0_fclk_guard_status_mark(guard,
                                  P0_FCLK_GUARD_STATUS_STAGE_COMPLETE,
                                  "COMPLETE");
    status->last_status_stage = READ_ONCE(guard->last_status_stage);
    return ccf_result;
}

static void p0_fclk_guard_collect_axi_prereq_status(
    struct p0_fclk_guard_axi_prereq_status *status)
{
    memset(status, 0, sizeof(*status));
    status->abi_version = P0_FCLK_GUARD_ABI_VERSION;
    status->m_axi_gp0_security_fssw_s0 =
        P0_FCLK_GUARD_REGISTER_UNKNOWN;
    status->s_axi_hp0_tz_fpga_afi = P0_FCLK_GUARD_REGISTER_UNKNOWN;
    status->status_flags =
        P0_FCLK_GUARD_STATUS_GP0_SECURITY_NOT_SAFELY_PROBED |
        P0_FCLK_GUARD_STATUS_HP0_SECURITY_NOT_SAFELY_PROBED;
}

static int p0_fclk_guard_set_reset0(struct p0_fclk_guard *guard, bool assert)
{
    u32 old_value;
    u32 new_value;
    u32 readback;

    p0_fclk_guard_slcr_unlock(guard);
    old_value = readl(guard->slcr + P0_SLCR_FPGA_RST_CTRL_OFFSET);
    if (assert)
        new_value = old_value | P0_FCLK_GUARD_FPGA0_OUT_RST_MASK;
    else
        new_value = old_value & ~P0_FCLK_GUARD_FPGA0_OUT_RST_MASK;
    writel(new_value, guard->slcr + P0_SLCR_FPGA_RST_CTRL_OFFSET);
    readback = readl(guard->slcr + P0_SLCR_FPGA_RST_CTRL_OFFSET);
    p0_fclk_guard_slcr_lock(guard);

    if (readback != new_value)
        return -EIO;
    return 0;
}

static int p0_fclk_guard_require_ccf_rate(
    u64 rate, bool require_exact, struct clk **clock_out,
    struct p0_fclk_guard_transition *transition)
{
    struct clk *clock;
    long rounded;

    if (transition)
        p0_fclk_guard_apply_mark(
            transition, P0_FCLK_GUARD_APPLY_STAGE_04_CCF_LOOKUP,
            "CCF_LOOKUP");
    clock = p0_fclk_guard_get_fclk();
    if (IS_ERR(clock))
        return PTR_ERR(clock);
    if (transition)
        p0_fclk_guard_apply_mark(
            transition, P0_FCLK_GUARD_APPLY_STAGE_05_ROUND_RATE,
            "ROUND_RATE");
    rounded = clk_round_rate(clock, rate);
    if (rounded < 0 || (require_exact &&
        !p0_fclk_guard_clock_rounds_exact(rounded, rate)) ||
        (!require_exact && !p0_fclk_guard_ccf_rate_matches_decoded(
            rounded, rate))) {
        clk_put(clock);
        return -ERANGE;
    }
    *clock_out = clock;
    return 0;
}

static bool p0_fclk_guard_has_50mhz_clock(
    const struct p0_fclk_guard *guard,
    const struct p0_fclk_guard_status *status)
{
    return guard->clock_enable_owned &&
           !p0_fclk_guard_validate_50mhz_clock(
        status->io_pll_ctrl, status->fpga0_clk_ctrl,
        status->fpga_rst_ctrl, status->lvl_shftr_en, 0) &&
           !status->ccf_errno &&
           (status->status_flags & P0_FCLK_GUARD_STATUS_CCF_RESOLVED) &&
           (status->status_flags & P0_FCLK_GUARD_STATUS_CCF_ROUND_50_EXACT) &&
           p0_fclk_guard_ccf_rate_matches_decoded(
               status->ccf_current_rate_hz,
               P0_FCLK_GUARD_TARGET_FCLK_HZ);
}

static bool p0_fclk_guard_transition_is_allowed(
    const struct p0_fclk_guard_status *status, u32 operation, u32 expected)
{
    u32 resulting_state;

    return p0_fclk_guard_transition_allowed(status->current_state, operation,
                                             &resulting_state) &&
           resulting_state == expected;
}

static int p0_fclk_guard_apply_50mhz(
    struct p0_fclk_guard *guard,
    struct p0_fclk_guard_transition *transition)
{
    struct p0_fclk_guard_status status;
    struct clk *clock;
    bool slcr_unlocked = false;
    int result;

    transition->apply.requested_rate_hz = P0_FCLK_GUARD_TARGET_FCLK_HZ;
    p0_fclk_guard_apply_mark(transition,
                             P0_FCLK_GUARD_APPLY_STAGE_01_PRECHECK,
                             "PRECHECK");
    result = p0_fclk_guard_collect_status(guard, &status);
    if (result)
        return result;
    if (!p0_fclk_guard_transition_is_allowed(
            &status, P0_FCLK_GUARD_OPERATION_APPLY_50MHZ,
            P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED) ||
        !(status.status_flags & P0_FCLK_GUARD_STATUS_GOLDEN_PRECONDITIONS))
        return -EPERM;

    p0_fclk_guard_apply_mark(transition,
                             P0_FCLK_GUARD_APPLY_STAGE_02_ASSERT_RESET_ENTER,
                             "ASSERT_RESET_ENTER");
    result = p0_fclk_guard_set_reset0(guard, true);
    if (result)
        return result;
    if (!guard->active_transaction) {
        __module_get(THIS_MODULE);
        guard->active_transaction = true;
    }
    p0_fclk_guard_apply_mark(transition,
                             P0_FCLK_GUARD_APPLY_STAGE_03_ASSERT_RESET_OK,
                             "ASSERT_RESET_OK");

    result = p0_fclk_guard_require_ccf_rate(P0_FCLK_GUARD_TARGET_FCLK_HZ,
                                             true, &clock, transition);
    if (result)
        return result;

    p0_fclk_guard_apply_mark(transition,
                             P0_FCLK_GUARD_APPLY_STAGE_06_SET_RATE_ENTER,
                             "SET_RATE_ENTER");
    /* The Zynq CCF divider driver writes SLCR directly and does not unlock it. */
    p0_fclk_guard_slcr_unlock(guard);
    slcr_unlocked = true;
    result = clk_set_rate(clock, P0_FCLK_GUARD_TARGET_FCLK_HZ);
    if (result)
        goto out_lock_slcr;
    /* Take one explicit CCF reference and release only this reference later. */
    result = clk_prepare_enable(clock);
    if (result)
        goto out_lock_slcr;
    guard->clock_enable_owned = true;
    p0_fclk_guard_slcr_lock(guard);
    slcr_unlocked = false;
    p0_fclk_guard_apply_mark(transition,
                             P0_FCLK_GUARD_APPLY_STAGE_07_SET_RATE_OK,
                             "SET_RATE_OK");

    p0_fclk_guard_apply_mark(transition,
                             P0_FCLK_GUARD_APPLY_STAGE_08_REGISTER_READBACK,
                             "REGISTER_READBACK");
    result = p0_fclk_guard_collect_status(guard, &status);
    if (result)
        goto out_put_clock;
    p0_fclk_guard_apply_mark(transition,
                             P0_FCLK_GUARD_APPLY_STAGE_09_DIRECT_RATE_VERIFY,
                             "DIRECT_RATE_VERIFY");
    if (status.current_state != P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED ||
        status.decoded_fclk0_hz != P0_FCLK_GUARD_TARGET_FCLK_HZ) {
        result = -EIO;
        goto out_put_clock;
    }
    p0_fclk_guard_apply_mark(transition,
                             P0_FCLK_GUARD_APPLY_STAGE_10_CCF_RATE_VERIFY,
                             "CCF_RATE_VERIFY");
    if (!p0_fclk_guard_ccf_rate_matches_decoded(
            status.ccf_current_rate_hz, P0_FCLK_GUARD_TARGET_FCLK_HZ) ||
        !p0_fclk_guard_has_50mhz_clock(guard, &status)) {
        result = -EIO;
        goto out_put_clock;
    }

    result = 0;
    p0_fclk_guard_apply_mark(transition,
                             P0_FCLK_GUARD_APPLY_STAGE_COMPLETE,
                             "COMPLETE");
    goto out_put_clock;
out_lock_slcr:
    if (slcr_unlocked)
        p0_fclk_guard_slcr_lock(guard);
out_put_clock:
    clk_put(clock);
    return result;
}

static int p0_fclk_guard_assert_pl_reset(struct p0_fclk_guard *guard)
{
    struct p0_fclk_guard_status status;
    int result;

    result = p0_fclk_guard_collect_status(guard, &status);
    if (result)
        return result;
    if (!p0_fclk_guard_transition_is_allowed(
            &status, P0_FCLK_GUARD_OPERATION_ASSERT_PL_RESET,
            P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED) ||
        !guard->active_transaction ||
        !p0_fclk_guard_has_50mhz_clock(guard, &status))
        return -EPERM;

    result = p0_fclk_guard_set_reset0(guard, true);
    if (result)
        return result;
    result = p0_fclk_guard_collect_status(guard, &status);
    if (result)
        return result;
    if (status.current_state !=
            P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED ||
        !guard->active_transaction ||
        !p0_fclk_guard_has_50mhz_clock(guard, &status))
        return -EIO;
    return 0;
}

static int p0_fclk_guard_release_pl_reset(struct p0_fclk_guard *guard)
{
    struct p0_fclk_guard_status status;
    int result;

    result = p0_fclk_guard_collect_status(guard, &status);
    if (result)
        return result;
    if (!p0_fclk_guard_transition_is_allowed(
            &status, P0_FCLK_GUARD_OPERATION_RELEASE_PL_RESET,
            P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED) ||
        !guard->active_transaction ||
        !p0_fclk_guard_has_50mhz_clock(guard, &status))
        return -EPERM;

    result = p0_fclk_guard_set_reset0(guard, false);
    if (result)
        return result;
    result = p0_fclk_guard_collect_status(guard, &status);
    if (result)
        return result;
    if (status.current_state !=
            P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED ||
        !p0_fclk_guard_has_50mhz_clock(guard, &status))
        return -EIO;
    return 0;
}

static int p0_fclk_guard_restore_100mhz(struct p0_fclk_guard *guard)
{
    struct p0_fclk_guard_status status;
    struct clk *clock = NULL;
    bool slcr_unlocked = false;
    int result;

    result = p0_fclk_guard_collect_status(guard, &status);
    if (result)
        return result;
    if (!p0_fclk_guard_transition_is_allowed(
            &status, P0_FCLK_GUARD_OPERATION_RESTORE_100MHZ,
            P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED) ||
        !guard->active_transaction)
        return -EPERM;

    if (status.current_state == P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED) {
        result = p0_fclk_guard_require_ccf_rate(
            P0_FCLK_GUARD_GOLDEN_FCLK_HZ, false, &clock, NULL);
        if (result)
            return result;
        p0_fclk_guard_slcr_unlock(guard);
        slcr_unlocked = true;
        result = clk_set_rate(clock, P0_FCLK_GUARD_GOLDEN_FCLK_HZ);
        if (result)
            goto out_put_clock;
        p0_fclk_guard_slcr_lock(guard);
        slcr_unlocked = false;
    } else if (p0_fclk_guard_validate_golden_clock(
                   status.io_pll_ctrl, status.fpga0_clk_ctrl,
                   status.fpga_rst_ctrl, status.lvl_shftr_en)) {
        return -EPERM;
    }

    result = p0_fclk_guard_collect_status(guard, &status);
    if (result)
        goto out_put_clock;
    if (status.current_state !=
            P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_ASSERTED ||
        p0_fclk_guard_validate_golden_clock(
            status.io_pll_ctrl, status.fpga0_clk_ctrl,
            status.fpga_rst_ctrl, status.lvl_shftr_en)) {
        result = -EIO;
        goto out_put_clock;
    }

    if (guard->clock_enable_owned) {
        if (!clock) {
            clock = p0_fclk_guard_get_fclk();
            if (IS_ERR(clock))
                return PTR_ERR(clock);
        }
        p0_fclk_guard_slcr_unlock(guard);
        slcr_unlocked = true;
        clk_disable_unprepare(clock);
        p0_fclk_guard_slcr_lock(guard);
        slcr_unlocked = false;
        guard->clock_enable_owned = false;
    }

    result = p0_fclk_guard_set_reset0(guard, false);
    if (result)
        goto out_put_clock;
    result = p0_fclk_guard_collect_status(guard, &status);
    if (result)
        goto out_put_clock;
    if (status.current_state !=
            P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED ||
        !(status.status_flags & P0_FCLK_GUARD_STATUS_GOLDEN_PRECONDITIONS)) {
        result = -EIO;
        goto out_put_clock;
    }

    if (guard->active_transaction) {
        guard->active_transaction = false;
        module_put(THIS_MODULE);
    }
    result = 0;
out_put_clock:
    if (slcr_unlocked)
        p0_fclk_guard_slcr_lock(guard);
    if (clock)
        clk_put(clock);
    return result;
}

static long p0_fclk_guard_ioctl(struct file *file, unsigned int command,
                                 unsigned long argument)
{
    struct p0_fclk_guard *guard = container_of(
        file->private_data, struct p0_fclk_guard, misc);
    struct p0_fclk_guard_status status;
    struct p0_fclk_guard_axi_prereq_status axi_prereq_status;
    struct p0_fclk_guard_transition transition;
    long final_status_result;
    long result;

    if (_IOC_TYPE(command) != P0_FCLK_GUARD_IOC_MAGIC)
        return -ENOTTY;
    if (mutex_lock_interruptible(&guard->lock))
        return -ERESTARTSYS;

    switch (command) {
    case P0_FCLK_GUARD_IOC_GET_STATUS:
        result = p0_fclk_guard_collect_status(guard, &status);
        if (copy_to_user((void __user *)argument, &status, sizeof(status)))
            result = -EFAULT;
        break;
    case P0_FCLK_GUARD_IOC_GET_AXI_PREREQ_STATUS:
        p0_fclk_guard_collect_axi_prereq_status(&axi_prereq_status);
        result = copy_to_user((void __user *)argument, &axi_prereq_status,
                              sizeof(axi_prereq_status)) ? -EFAULT : 0;
        break;
    case P0_FCLK_GUARD_IOC_APPLY_50MHZ:
    case P0_FCLK_GUARD_IOC_ASSERT_PL_RESET:
    case P0_FCLK_GUARD_IOC_RELEASE_PL_RESET:
    case P0_FCLK_GUARD_IOC_RESTORE_100MHZ:
        memset(&transition, 0, sizeof(transition));
        result = p0_fclk_guard_collect_status(guard, &status);
        transition.previous_state = status.current_state;
        p0_fclk_guard_capture_apply_status(&transition.apply, &status, false);
        if (result)
            goto transition_complete;
        if (command == P0_FCLK_GUARD_IOC_APPLY_50MHZ)
            result = p0_fclk_guard_apply_50mhz(guard, &transition);
        else if (command == P0_FCLK_GUARD_IOC_ASSERT_PL_RESET)
            result = p0_fclk_guard_assert_pl_reset(guard);
        else if (command == P0_FCLK_GUARD_IOC_RELEASE_PL_RESET)
            result = p0_fclk_guard_release_pl_reset(guard);
        else
            result = p0_fclk_guard_restore_100mhz(guard);
transition_complete:
        final_status_result = p0_fclk_guard_collect_status(guard, &status);
        transition.resulting_state = status.current_state;
        if (command == P0_FCLK_GUARD_IOC_APPLY_50MHZ) {
            p0_fclk_guard_capture_apply_status(&transition.apply, &status,
                                                true);
            transition.apply.stage_errno = result;
        }
        transition.operation_errno = result;
        if (!result && final_status_result)
            result = final_status_result;
        if (copy_to_user((void __user *)argument, &transition,
                         sizeof(transition)))
            result = -EFAULT;
        break;
    default:
        result = -ENOTTY;
        break;
    }

    mutex_unlock(&guard->lock);
    return result;
}

static const struct file_operations p0_fclk_guard_fops = {
    .owner = THIS_MODULE,
    .unlocked_ioctl = p0_fclk_guard_ioctl,
    .llseek = noop_llseek,
};

static int __init p0_fclk_guard_init(void)
{
    int result;

    memset(&p0_guard, 0, sizeof(p0_guard));
    mutex_init(&p0_guard.lock);
    p0_guard.slcr = ioremap(P0_SLCR_PHYS, P0_SLCR_SIZE);
    if (!p0_guard.slcr)
        return -ENOMEM;

    p0_guard.misc.minor = MISC_DYNAMIC_MINOR;
    p0_guard.misc.name = P0_FCLK_GUARD_DEVICE_NAME;
    p0_guard.misc.fops = &p0_fclk_guard_fops;
    p0_guard.misc.mode = 0600;
    result = misc_register(&p0_guard.misc);
    if (result) {
        iounmap(p0_guard.slcr);
        return result;
    }

    pr_info("p0-fclk-guard yüklendi; donanım durumu değiştirilmedi\n");
    return 0;
}

static void __exit p0_fclk_guard_exit(void)
{
    if (p0_guard.active_transaction) {
        pr_err("p0-fclk-guard: etkin işlem varken kaldırılamaz\n");
        return;
    }
    misc_deregister(&p0_guard.misc);
    iounmap(p0_guard.slcr);
}

module_init(p0_fclk_guard_init);
module_exit(p0_fclk_guard_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("TEKNOFEST P0");
MODULE_DESCRIPTION("P0 FCLK0 guarded CCF runtime alignment helper");
