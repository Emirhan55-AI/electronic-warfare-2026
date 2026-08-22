#ifndef P0_FCLK_GUARD_UAPI_H
#define P0_FCLK_GUARD_UAPI_H

#include <linux/ioctl.h>
#include <linux/types.h>

#define P0_FCLK_GUARD_ABI_VERSION 6U
#define P0_FCLK_GUARD_DEVICE_NAME "p0-fclk-guard"
#define P0_FCLK_GUARD_CCF_NAME_MAX 32U
#define P0_FCLK_GUARD_REGISTER_UNKNOWN 0xffffffffU

#ifndef P0_FCLK_GUARD_STATE_UNKNOWN
#define P0_FCLK_GUARD_STATE_UNKNOWN 0U
#define P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED 1U
#define P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED 2U
#define P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED 3U
#define P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_ASSERTED 4U
#endif

#define P0_FCLK_GUARD_STATUS_CCF_RESOLVED (1U << 0)
#define P0_FCLK_GUARD_STATUS_CCF_ENABLED (1U << 1)
#define P0_FCLK_GUARD_STATUS_CCF_ROUND_50_EXACT (1U << 2)
#define P0_FCLK_GUARD_STATUS_GOLDEN_PRECONDITIONS (1U << 3)
#define P0_FCLK_GUARD_STATUS_SAFE_50MHZ (1U << 4)
#define P0_FCLK_GUARD_STATUS_RESET0_ASSERTED (1U << 5)
#define P0_FCLK_GUARD_STATUS_GUARD_OWNS_CLOCK_ENABLE (1U << 6)
#define P0_FCLK_GUARD_STATUS_ACTIVE_TRANSACTION (1U << 7)
#define P0_FCLK_GUARD_STATUS_CCF_ENABLED_STATE_UNAVAILABLE (1U << 8)
#define P0_FCLK_GUARD_STATUS_CCF_ROUND_NOT_PROBED (1U << 9)
#define P0_FCLK_GUARD_STATUS_GP0_SECURITY_NOT_SAFELY_PROBED (1U << 10)
#define P0_FCLK_GUARD_STATUS_HP0_SECURITY_NOT_SAFELY_PROBED (1U << 11)

#define P0_FCLK_GUARD_CCF_DISABLED 0U
#define P0_FCLK_GUARD_CCF_ENABLED 1U
#define P0_FCLK_GUARD_CCF_ENABLED_UNKNOWN 2U

#define P0_FCLK_GUARD_STATUS_STAGE_NONE 0U
#define P0_FCLK_GUARD_STATUS_STAGE_ENTER 1U
#define P0_FCLK_GUARD_STATUS_STAGE_IO_PLL_ENTER 2U
#define P0_FCLK_GUARD_STATUS_STAGE_IO_PLL_OK 3U
#define P0_FCLK_GUARD_STATUS_STAGE_FPGA0_CLK_ENTER 4U
#define P0_FCLK_GUARD_STATUS_STAGE_FPGA0_CLK_OK 5U
#define P0_FCLK_GUARD_STATUS_STAGE_FPGA_RST_ENTER 6U
#define P0_FCLK_GUARD_STATUS_STAGE_FPGA_RST_OK 7U
#define P0_FCLK_GUARD_STATUS_STAGE_LVL_SHFTR_ENTER 8U
#define P0_FCLK_GUARD_STATUS_STAGE_LVL_SHFTR_OK 9U
#define P0_FCLK_GUARD_STATUS_STAGE_CCF_LOOKUP_ENTER 10U
#define P0_FCLK_GUARD_STATUS_STAGE_CCF_LOOKUP_OK 11U
#define P0_FCLK_GUARD_STATUS_STAGE_CCF_RATE_ENTER 12U
#define P0_FCLK_GUARD_STATUS_STAGE_CCF_RATE_OK 13U
#define P0_FCLK_GUARD_STATUS_STAGE_CCF_ROUND_ENTER 14U
#define P0_FCLK_GUARD_STATUS_STAGE_CCF_ROUND_OK 15U
#define P0_FCLK_GUARD_STATUS_STAGE_COMPLETE 16U

#define P0_FCLK_GUARD_APPLY_STAGE_NONE 0U
#define P0_FCLK_GUARD_APPLY_STAGE_01_PRECHECK 1U
#define P0_FCLK_GUARD_APPLY_STAGE_02_ASSERT_RESET_ENTER 2U
#define P0_FCLK_GUARD_APPLY_STAGE_03_ASSERT_RESET_OK 3U
#define P0_FCLK_GUARD_APPLY_STAGE_04_CCF_LOOKUP 4U
#define P0_FCLK_GUARD_APPLY_STAGE_05_ROUND_RATE 5U
#define P0_FCLK_GUARD_APPLY_STAGE_06_SET_RATE_ENTER 6U
#define P0_FCLK_GUARD_APPLY_STAGE_07_SET_RATE_OK 7U
#define P0_FCLK_GUARD_APPLY_STAGE_08_REGISTER_READBACK 8U
#define P0_FCLK_GUARD_APPLY_STAGE_09_DIRECT_RATE_VERIFY 9U
#define P0_FCLK_GUARD_APPLY_STAGE_10_CCF_RATE_VERIFY 10U
#define P0_FCLK_GUARD_APPLY_STAGE_COMPLETE 11U

struct p0_fclk_guard_status {
    __u32 abi_version;
    __u32 status_flags;
    __u32 current_state;
    __u32 golden_validation_errors;
    __u32 safe_50_validation_errors;
    __s32 ccf_errno;

    __u32 io_pll_ctrl;
    __u32 fpga0_clk_ctrl;
    __u32 fpga_rst_ctrl;
    __u32 lvl_shftr_en;
    __u32 security_fssw_s0;
    __u32 tz_fpga_afi;

    __u32 io_pll_fbdiv;
    __u32 fclk_srcsel;
    __u32 fclk_div0;
    __u32 fclk_div1;

    __u64 decoded_io_pll_hz;
    __u64 decoded_fclk0_hz;
    __u64 ccf_current_rate_hz;
    __s64 ccf_round_50mhz_hz;
    __u32 ccf_enabled;
    __u32 last_status_stage;
    char ccf_clock_name[P0_FCLK_GUARD_CCF_NAME_MAX];
};

struct p0_fclk_guard_axi_prereq_status {
    __u32 abi_version;
    __u32 status_flags;
    __u32 m_axi_gp0_security_fssw_s0;
    __u32 s_axi_hp0_tz_fpga_afi;
};

struct p0_fclk_guard_apply_diagnostics {
    __u32 last_stage;
    __s32 stage_errno;
    __u64 requested_rate_hz;
    __u64 ccf_rate_before_hz;
    __u64 ccf_rate_after_hz;
    __u32 fpga0_clk_ctrl_before;
    __u32 fpga0_clk_ctrl_after;
    __u64 decoded_fclk0_before_hz;
    __u64 decoded_fclk0_after_hz;
    __u32 fpga_rst_ctrl_before;
    __u32 fpga_rst_ctrl_after;
};

struct p0_fclk_guard_transition {
    __u32 previous_state;
    __u32 resulting_state;
    __s32 operation_errno;
    __u32 reserved;
    struct p0_fclk_guard_apply_diagnostics apply;
};

#define P0_FCLK_GUARD_IOC_MAGIC 'F'
#define P0_FCLK_GUARD_IOC_GET_STATUS \
    _IOR(P0_FCLK_GUARD_IOC_MAGIC, 0, struct p0_fclk_guard_status)
#define P0_FCLK_GUARD_IOC_APPLY_50MHZ \
    _IOWR(P0_FCLK_GUARD_IOC_MAGIC, 1, struct p0_fclk_guard_transition)
#define P0_FCLK_GUARD_IOC_ASSERT_PL_RESET \
    _IOWR(P0_FCLK_GUARD_IOC_MAGIC, 2, struct p0_fclk_guard_transition)
#define P0_FCLK_GUARD_IOC_RELEASE_PL_RESET \
    _IOWR(P0_FCLK_GUARD_IOC_MAGIC, 3, struct p0_fclk_guard_transition)
#define P0_FCLK_GUARD_IOC_RESTORE_100MHZ \
    _IOWR(P0_FCLK_GUARD_IOC_MAGIC, 4, struct p0_fclk_guard_transition)
#define P0_FCLK_GUARD_IOC_GET_AXI_PREREQ_STATUS \
    _IOR(P0_FCLK_GUARD_IOC_MAGIC, 5, \
         struct p0_fclk_guard_axi_prereq_status)

#endif
