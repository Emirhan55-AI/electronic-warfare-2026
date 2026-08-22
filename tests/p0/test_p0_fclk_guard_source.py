from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "ps" / "p0" / "src" / "p0_fclk_guard.c"
TOOL = ROOT / "ps" / "p0" / "src" / "p0_fclk_guardctl.c"
RECIPE = ROOT / "ps" / "p0" / "petalinux" / "p0-fclk-guard_1.0.bb"
LOGIC = ROOT / "ps" / "p0" / "include" / "p0_fclk_guard_logic.h"


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\([^)]*\)\s*\n\{{", source)
    if not match:
        raise AssertionError(f"{name} bulunamadı")
    start = match.end()
    depth = 1
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index]
    raise AssertionError(f"{name} gövdesi sonlanmadı")


class P0FclkGuardSourceTest(unittest.TestCase):
    def test_module_load_is_read_only(self) -> None:
        init = function_body(MODULE.read_text(encoding="utf-8"),
                             "p0_fclk_guard_init")
        self.assertNotRegex(init, r"\b(writel|clk_set_rate|clk_prepare_enable)\b")
        self.assertNotIn("p0_fclk_guard_set_reset0", init)

    def test_no_axi_dma_access_surface(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("0x40400000", source)
        self.assertNotIn("devm_platform_ioremap_resource", source)
        self.assertNotRegex(source, r"\b(MM2S|S2MM)\b")

    def test_default_status_excludes_unproven_security_mmio(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        status = function_body(source, "p0_fclk_guard_collect_status")
        reads = function_body(source, "p0_fclk_guard_read_registers")

        self.assertNotIn("0xf890", source.lower())
        self.assertNotIn("P0_SECURITY_PHYS", source)
        self.assertNotIn("P0_SECURITY_FSSW_S0_OFFSET", source)
        self.assertNotIn("P0_SLCR_TZ_FPGA_AFI_OFFSET", source)
        self.assertNotIn("readl(guard->security", source)
        self.assertNotIn("p0_fclk_guard_collect_axi_prereq_status", status)
        self.assertNotIn("writel", status)
        self.assertNotIn("clk_round_rate", status)
        for offset in (
            "P0_SLCR_LOCK_OFFSET",
            "P0_SLCR_UNLOCK_OFFSET",
        ):
            self.assertIn(
                f"static_assert({offset} <= P0_SLCR_SIZE - sizeof(u32));",
                source,
            )
        for offset in (
            "P0_SLCR_IO_PLL_CTRL_OFFSET",
            "P0_SLCR_FPGA0_CLK_CTRL_OFFSET",
            "P0_SLCR_FPGA_RST_CTRL_OFFSET",
            "P0_SLCR_LVL_SHFTR_EN_OFFSET",
        ):
            self.assertIn(offset, reads)
            self.assertIn(
                f"static_assert({offset} <= P0_SLCR_SIZE - sizeof(u32));",
                source,
            )

    def test_ccf_provider_lookup_and_failure_reporting(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        get_fclk = function_body(source, "p0_fclk_guard_get_fclk")
        ccf = function_body(source, "p0_fclk_guard_read_ccf")
        status = function_body(source, "p0_fclk_guard_collect_status")
        require_rate = function_body(source, "p0_fclk_guard_require_ccf_rate")

        self.assertIn("struct of_phandle_args clkspec", get_fclk)
        self.assertIn("clkspec.args_count = 1", get_fclk)
        self.assertIn("clkspec.args[0] = P0_FCLK0_CLOCK_INDEX", get_fclk)
        self.assertIn("of_clk_get_from_provider(&clkspec)", get_fclk)
        self.assertNotIn("of_clk_get(node", get_fclk)
        self.assertIn("IS_ERR(clock)", ccf)
        self.assertIn("return status->ccf_errno;", ccf)
        self.assertIn("clk_round_rate", ccf)
        self.assertNotIn("clk_set_rate", ccf)
        self.assertNotIn("writel", ccf)
        self.assertIn("p0_fclk_guard_ccf_rate_matches_decoded", status)
        logic = LOGIC.read_text(encoding="utf-8")
        self.assertIn("P0_FCLK_GUARD_CCF_RATE_COMPARE_TOLERANCE_HZ", logic)
        self.assertIn("ccf_rate - decoded_rate <=", logic)
        self.assertIn("decoded_rate - ccf_rate <=", logic)
        self.assertNotIn("clk_set_rate", status)
        self.assertIn("clk_round_rate", require_rate)
        self.assertIn("p0_fclk_guard_clock_rounds_exact", require_rate)
        self.assertNotIn("CCF_RATE_COMPARE_TOLERANCE", require_rate)
        self.assertIn("P0_FCLK_GUARD_STATUS_CCF_ROUND_50_EXACT", status)
        self.assertNotIn("safe_50_errors |= P0_FCLK_GUARD_VALIDATE_CCF_ENABLED",
                         status)
        self.assertIn("result = p0_fclk_guard_collect_status(guard, &status);",
                      source)

    def test_50mhz_status_requires_observed_ccf_contract_only(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        status = function_body(source, "p0_fclk_guard_collect_status")
        logic = LOGIC.read_text(encoding="utf-8")

        self.assertIn(
            "if (!(status->status_flags & P0_FCLK_GUARD_STATUS_CCF_RESOLVED) ||\n"
            "        !(status->status_flags & P0_FCLK_GUARD_STATUS_CCF_ROUND_50_EXACT))\n"
            "        safe_50_errors |= P0_FCLK_GUARD_VALIDATE_CCF_ROUND_RATE;",
            status,
        )
        self.assertNotIn(
            "safe_50_errors |= P0_FCLK_GUARD_VALIDATE_CCF_ENABLED;",
            status,
        )
        self.assertIn(
            "if (status->current_state == P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED &&\n"
            "        safe_50_errors)\n"
            "        status->current_state = P0_FCLK_GUARD_STATE_UNKNOWN;",
            status,
        )
        self.assertIn("p0_fclk_guard_fclk_ctrl_is_legal_50mhz", logic)
        self.assertIn("P0_FCLK_GUARD_PHYSICAL_50MHZ_FCLK_CTRL 0x00101400U",
                      logic)

    def test_axi_prerequisites_are_a_non_mmio_explicit_operation(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        header = (ROOT / "ps" / "p0" / "include" /
                  "p0_fclk_guard_uapi.h").read_text(encoding="utf-8")
        tool = TOOL.read_text(encoding="utf-8")
        axi = function_body(source, "p0_fclk_guard_collect_axi_prereq_status")

        self.assertIn("P0_FCLK_GUARD_IOC_GET_AXI_PREREQ_STATUS", header)
        self.assertIn("P0_FCLK_GUARD_REGISTER_UNKNOWN", axi)
        self.assertNotIn("readl", axi)
        self.assertIn('"axi-prereq-status"', tool)

    def test_status_has_bounded_opt_in_forensic_markers(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        self.assertIn("module_param_named(status_trace", source)
        self.assertIn("P0_FCLK_GUARD_STATUS_STAGE_IO_PLL_ENTER", source)
        self.assertIn("P0_FCLK_GUARD_STATUS_STAGE_CCF_RATE_OK", source)
        self.assertIn("P0_FCLK_GUARD_STATUS_STAGE_COMPLETE", source)

    def test_target_kernel_uses_exported_external_module_api(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("__clk_get_name", source)
        self.assertNotIn("clk_is_enabled", source)
        self.assertNotIn(".llseek = no_llseek", source)
        self.assertIn(".llseek = noop_llseek", source)

    def test_recipe_never_autoloads_module(self) -> None:
        recipe = RECIPE.read_text(encoding="utf-8")
        self.assertNotIn("KERNEL_MODULE_AUTOLOAD", recipe)
        self.assertIn("p0_fclk_guard.ko", recipe)

    def test_userspace_default_is_read_only_status(self) -> None:
        tool = TOOL.read_text(encoding="utf-8")
        self.assertIn('const char *operation = "status"', tool)
        self.assertNotIn("0x40400000", tool)

    def test_apply_is_diagnosed_and_never_releases_reset_on_failure(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        apply = function_body(source, "p0_fclk_guard_apply_50mhz")
        tool = TOOL.read_text(encoding="utf-8")

        stages = (
            "APPLY_STAGE_01_PRECHECK",
            "APPLY_STAGE_02_ASSERT_RESET_ENTER",
            "APPLY_STAGE_03_ASSERT_RESET_OK",
            "APPLY_STAGE_06_SET_RATE_ENTER",
            "APPLY_STAGE_07_SET_RATE_OK",
            "APPLY_STAGE_08_REGISTER_READBACK",
            "APPLY_STAGE_09_DIRECT_RATE_VERIFY",
            "APPLY_STAGE_10_CCF_RATE_VERIFY",
            "APPLY_STAGE_COMPLETE",
        )
        positions = [apply.index(stage) for stage in stages]

        self.assertEqual(positions, sorted(positions))
        self.assertLess(
            apply.index("APPLY_STAGE_03_ASSERT_RESET_OK"),
            apply.index("p0_fclk_guard_require_ccf_rate"),
        )
        self.assertLess(
            apply.index("p0_fclk_guard_require_ccf_rate"),
            apply.index("APPLY_STAGE_06_SET_RATE_ENTER"),
        )
        self.assertIn("p0_fclk_guard_slcr_unlock(guard)", apply)
        self.assertIn("p0_fclk_guard_slcr_lock(guard)", apply)
        self.assertNotIn("p0_fclk_guard_set_reset0(guard, false)", apply)
        self.assertIn("APPLY son aşaması", tool)
        self.assertIn("FPGA0_CLK_CTRL", tool)

    def test_restore_from_verified_golden_reset_asserted_skips_set_rate(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        restore = function_body(source, "p0_fclk_guard_restore_100mhz")

        self.assertIn("P0_FCLK_GUARD_STATE_50MHZ_RESET_ASSERTED", restore)
        self.assertIn("else if (p0_fclk_guard_validate_golden_clock", restore)
        self.assertIn("p0_fclk_guard_set_reset0(guard, false)", restore)
        self.assertGreater(
            restore.index("p0_fclk_guard_set_reset0(guard, false)"),
            restore.index("p0_fclk_guard_validate_golden_clock"),
        )


if __name__ == "__main__":
    unittest.main()
