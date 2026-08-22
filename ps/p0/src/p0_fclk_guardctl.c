// SPDX-License-Identifier: GPL-2.0-only

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include "p0_fclk_guard_uapi.h"

#define P0_FCLK_GUARD_DEVICE "/dev/p0-fclk-guard"
#define P0_FPGA_MANAGER_STATE "/sys/class/fpga_manager/fpga0/state"

static const char *p0_state_name(__u32 state)
{
    switch (state) {
    case P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_RELEASED:
        return "GOLDEN_100_RESET_RELEASED";
    case P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED:
        return "50MHZ_RESET_ASSERTED";
    case P0_FCLK_GUARD_STATE_50MHZ_RESET_RELEASED:
        return "50MHZ_RESET_RELEASED";
    case P0_FCLK_GUARD_STATE_GOLDEN_100_RESET_ASSERTED:
        return "GOLDEN_100_RESET_ASSERTED";
    default:
        return "UNKNOWN";
    }
}

static const char *p0_status_stage_name(__u32 stage)
{
    switch (stage) {
    case P0_FCLK_GUARD_STATUS_STAGE_NONE:
        return "NONE";
    case P0_FCLK_GUARD_STATUS_STAGE_ENTER:
        return "ENTER";
    case P0_FCLK_GUARD_STATUS_STAGE_IO_PLL_ENTER:
        return "IO_PLL_ENTER";
    case P0_FCLK_GUARD_STATUS_STAGE_IO_PLL_OK:
        return "IO_PLL_OK";
    case P0_FCLK_GUARD_STATUS_STAGE_FPGA0_CLK_ENTER:
        return "FPGA0_CLK_ENTER";
    case P0_FCLK_GUARD_STATUS_STAGE_FPGA0_CLK_OK:
        return "FPGA0_CLK_OK";
    case P0_FCLK_GUARD_STATUS_STAGE_FPGA_RST_ENTER:
        return "FPGA_RST_ENTER";
    case P0_FCLK_GUARD_STATUS_STAGE_FPGA_RST_OK:
        return "FPGA_RST_OK";
    case P0_FCLK_GUARD_STATUS_STAGE_LVL_SHFTR_ENTER:
        return "LVL_SHFTR_ENTER";
    case P0_FCLK_GUARD_STATUS_STAGE_LVL_SHFTR_OK:
        return "LVL_SHFTR_OK";
    case P0_FCLK_GUARD_STATUS_STAGE_CCF_LOOKUP_ENTER:
        return "CCF_LOOKUP_ENTER";
    case P0_FCLK_GUARD_STATUS_STAGE_CCF_LOOKUP_OK:
        return "CCF_LOOKUP_OK";
    case P0_FCLK_GUARD_STATUS_STAGE_CCF_RATE_ENTER:
        return "CCF_RATE_ENTER";
    case P0_FCLK_GUARD_STATUS_STAGE_CCF_RATE_OK:
        return "CCF_RATE_OK";
    case P0_FCLK_GUARD_STATUS_STAGE_CCF_ROUND_ENTER:
        return "CCF_ROUND_ENTER";
    case P0_FCLK_GUARD_STATUS_STAGE_CCF_ROUND_OK:
        return "CCF_ROUND_OK";
    case P0_FCLK_GUARD_STATUS_STAGE_COMPLETE:
        return "COMPLETE";
    default:
        return "UNKNOWN";
    }
}

static const char *p0_apply_stage_name(__u32 stage)
{
    switch (stage) {
    case P0_FCLK_GUARD_APPLY_STAGE_NONE:
        return "NONE";
    case P0_FCLK_GUARD_APPLY_STAGE_01_PRECHECK:
        return "APPLY_STAGE_01_PRECHECK";
    case P0_FCLK_GUARD_APPLY_STAGE_02_ASSERT_RESET_ENTER:
        return "APPLY_STAGE_02_ASSERT_RESET_ENTER";
    case P0_FCLK_GUARD_APPLY_STAGE_03_ASSERT_RESET_OK:
        return "APPLY_STAGE_03_ASSERT_RESET_OK";
    case P0_FCLK_GUARD_APPLY_STAGE_04_CCF_LOOKUP:
        return "APPLY_STAGE_04_CCF_LOOKUP";
    case P0_FCLK_GUARD_APPLY_STAGE_05_ROUND_RATE:
        return "APPLY_STAGE_05_ROUND_RATE";
    case P0_FCLK_GUARD_APPLY_STAGE_06_SET_RATE_ENTER:
        return "APPLY_STAGE_06_SET_RATE_ENTER";
    case P0_FCLK_GUARD_APPLY_STAGE_07_SET_RATE_OK:
        return "APPLY_STAGE_07_SET_RATE_OK";
    case P0_FCLK_GUARD_APPLY_STAGE_08_REGISTER_READBACK:
        return "APPLY_STAGE_08_REGISTER_READBACK";
    case P0_FCLK_GUARD_APPLY_STAGE_09_DIRECT_RATE_VERIFY:
        return "APPLY_STAGE_09_DIRECT_RATE_VERIFY";
    case P0_FCLK_GUARD_APPLY_STAGE_10_CCF_RATE_VERIFY:
        return "APPLY_STAGE_10_CCF_RATE_VERIFY";
    case P0_FCLK_GUARD_APPLY_STAGE_COMPLETE:
        return "APPLY_STAGE_COMPLETE";
    default:
        return "UNKNOWN";
    }
}

static void p0_print_status(const struct p0_fclk_guard_status *status)
{
    printf("ABI sürümü: %u\n", status->abi_version);
    printf("Durum: %s\n", p0_state_name(status->current_state));
    printf("IO_PLL_CTRL: 0x%08" PRIx32 "\n", status->io_pll_ctrl);
    printf("IO PLL: %" PRIu64 " Hz (FBDIV=%" PRIu32 ")\n",
           (uint64_t)status->decoded_io_pll_hz, status->io_pll_fbdiv);
    printf("FPGA0_CLK_CTRL: 0x%08" PRIx32 "\n", status->fpga0_clk_ctrl);
    printf("FCLK0: SRCSEL=%" PRIu32 " DIV0=%" PRIu32
           " DIV1=%" PRIu32 " = %" PRIu64 " Hz\n",
           status->fclk_srcsel, status->fclk_div0, status->fclk_div1,
           (uint64_t)status->decoded_fclk0_hz);
    printf("FPGA_RST_CTRL: 0x%08" PRIx32 "\n", status->fpga_rst_ctrl);
    printf("LVL_SHFTR_EN: 0x%08" PRIx32 "\n", status->lvl_shftr_en);
    printf("AXI güvenlik önkoşulları: güvenle sorgulanmadı\n");
    printf("CCF clock: %s\n", status->ccf_clock_name);
    printf("CCF current rate: %" PRIu64 " Hz\n",
           (uint64_t)status->ccf_current_rate_hz);
    if (status->ccf_round_50mhz_hz == -ENODATA)
        printf("CCF round(50000000): sorgulanmadı\n");
    else
        printf("CCF round(50000000): %" PRId64 " Hz\n",
               (int64_t)status->ccf_round_50mhz_hz);
    if (status->ccf_enabled == P0_FCLK_GUARD_CCF_ENABLED_UNKNOWN)
        printf("CCF enabled: mevcut çekirdek API'sinde erişilemez\n");
    else
        printf("CCF enabled: %u\n", status->ccf_enabled);
    printf("Durum bayrakları: 0x%08" PRIx32 "\n", status->status_flags);
    printf("Golden doğrulama hataları: 0x%08" PRIx32 "\n",
           status->golden_validation_errors);
    printf("50 MHz doğrulama hataları: 0x%08" PRIx32 "\n",
           status->safe_50_validation_errors);
    if (status->ccf_errno)
        printf("CCF hata kodu: %" PRId32 "\n", status->ccf_errno);
    printf("Son STATUS aşaması: %s (%" PRIu32 ")\n",
           p0_status_stage_name(status->last_status_stage),
           status->last_status_stage);
}

static void p0_print_axi_prereq_status(
    const struct p0_fclk_guard_axi_prereq_status *status)
{
    printf("ABI sürümü: %u\n", status->abi_version);
    printf("M_AXI_GP0 güvenlik durumu: UNKNOWN / güvenle sorgulanmadı\n");
    printf("S_AXI_HP0 güvenlik durumu: UNKNOWN / güvenle sorgulanmadı\n");
    printf("Durum bayrakları: 0x%08" PRIx32 "\n", status->status_flags);
}

static void p0_print_transition(
    const struct p0_fclk_guard_transition *transition)
{
    printf("Önceki durum: %s\n", p0_state_name(transition->previous_state));
    printf("Sonraki durum: %s\n", p0_state_name(transition->resulting_state));
    printf("İşlem hata kodu: %" PRId32 "\n", transition->operation_errno);
    if (transition->apply.last_stage == P0_FCLK_GUARD_APPLY_STAGE_NONE)
        return;
    printf("APPLY son aşaması: %s\n",
           p0_apply_stage_name(transition->apply.last_stage));
    printf("APPLY aşama hata kodu: %" PRId32 "\n",
           transition->apply.stage_errno);
    printf("İstenen oran: %" PRIu64 " Hz\n",
           (uint64_t)transition->apply.requested_rate_hz);
    printf("CCF oranı: %" PRIu64 " -> %" PRIu64 " Hz\n",
           (uint64_t)transition->apply.ccf_rate_before_hz,
           (uint64_t)transition->apply.ccf_rate_after_hz);
    printf("FPGA0_CLK_CTRL: 0x%08" PRIx32 " -> 0x%08" PRIx32 "\n",
           transition->apply.fpga0_clk_ctrl_before,
           transition->apply.fpga0_clk_ctrl_after);
    printf("Doğrudan FCLK0: %" PRIu64 " -> %" PRIu64 " Hz\n",
           (uint64_t)transition->apply.decoded_fclk0_before_hz,
           (uint64_t)transition->apply.decoded_fclk0_after_hz);
    printf("FPGA_RST_CTRL: 0x%08" PRIx32 " -> 0x%08" PRIx32 "\n",
           transition->apply.fpga_rst_ctrl_before,
           transition->apply.fpga_rst_ctrl_after);
}

static int p0_fpga_manager_is_operating(void)
{
    char state[32];
    FILE *file;

    file = fopen(P0_FPGA_MANAGER_STATE, "re");
    if (!file) {
        fprintf(stderr, "FPGA Manager durumu okunamadı: %s\n",
                strerror(errno));
        return 0;
    }
    if (!fgets(state, sizeof(state), file)) {
        fprintf(stderr, "FPGA Manager durumu boş veya okunamadı\n");
        fclose(file);
        return 0;
    }
    fclose(file);
    if (strcmp(state, "operating\n") != 0) {
        fprintf(stderr, "FPGA Manager operating değil: %s", state);
        return 0;
    }
    return 1;
}

int main(int argc, char **argv)
{
    struct p0_fclk_guard_status status;
    struct p0_fclk_guard_axi_prereq_status axi_prereq_status;
    struct p0_fclk_guard_transition transition;
    const char *operation = "status";
    unsigned long command;
    int device;

    if (argc > 2) {
        fprintf(stderr, "Kullanım: %s [status|axi-prereq-status|apply-50mhz|assert-pl-reset|release-pl-reset|restore-100mhz]\n",
                argv[0]);
        return EXIT_FAILURE;
    }
    if (argc == 2)
        operation = argv[1];

    device = open(P0_FCLK_GUARD_DEVICE, O_RDWR | O_CLOEXEC);
    if (device < 0) {
        fprintf(stderr, "%s açılamadı: %s\n", P0_FCLK_GUARD_DEVICE,
                strerror(errno));
        return EXIT_FAILURE;
    }

    if (strcmp(operation, "status") == 0) {
        memset(&status, 0, sizeof(status));
        if (ioctl(device, P0_FCLK_GUARD_IOC_GET_STATUS, &status) < 0) {
            p0_print_status(&status);
            fprintf(stderr, "Durum alınamadı: %s\n", strerror(errno));
            close(device);
            return EXIT_FAILURE;
        }
        p0_print_status(&status);
        close(device);
        return EXIT_SUCCESS;
    }

    if (strcmp(operation, "axi-prereq-status") == 0) {
        memset(&axi_prereq_status, 0, sizeof(axi_prereq_status));
        if (ioctl(device, P0_FCLK_GUARD_IOC_GET_AXI_PREREQ_STATUS,
                  &axi_prereq_status) < 0) {
            fprintf(stderr, "AXI önkoşul durumu alınamadı: %s\n",
                    strerror(errno));
            close(device);
            return EXIT_FAILURE;
        }
        p0_print_axi_prereq_status(&axi_prereq_status);
        close(device);
        return EXIT_SUCCESS;
    }

    if (strcmp(operation, "apply-50mhz") == 0)
        command = P0_FCLK_GUARD_IOC_APPLY_50MHZ;
    else if (strcmp(operation, "assert-pl-reset") == 0)
        command = P0_FCLK_GUARD_IOC_ASSERT_PL_RESET;
    else if (strcmp(operation, "release-pl-reset") == 0) {
        if (!p0_fpga_manager_is_operating()) {
            close(device);
            return EXIT_FAILURE;
        }
        command = P0_FCLK_GUARD_IOC_RELEASE_PL_RESET;
    } else if (strcmp(operation, "restore-100mhz") == 0)
        command = P0_FCLK_GUARD_IOC_RESTORE_100MHZ;
    else {
        fprintf(stderr, "Bilinmeyen işlem: %s\n", operation);
        close(device);
        return EXIT_FAILURE;
    }

    memset(&transition, 0, sizeof(transition));
    if (ioctl(device, command, &transition) < 0) {
        p0_print_transition(&transition);
        fprintf(stderr, "İşlem reddedildi: %s\n", strerror(errno));
        close(device);
        return EXIT_FAILURE;
    }
    p0_print_transition(&transition);
    printf("İşlem tamamlandı. Sonuç için '%s status' çalıştırın.\n", argv[0]);
    close(device);
    return EXIT_SUCCESS;
}
