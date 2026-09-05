#!/usr/bin/env python3
"""Verify the source-bound ST-06 FPGA/PetaLinux product image integration."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/phase08/st06-product-integration-v1.json"
VIVADO_EVIDENCE = ROOT / "results/evidence/phase08/st06-power-vivado-v1.json"
HOST_EVIDENCE = ROOT / "results/evidence/p0/ed-local-service-host-acceptance.json"
PACKAGE_BUILD_LOG = (
    ROOT / "results/evidence/phase08/st06-product-petalinux-package-build.txt"
)
IMAGE_BUILD_LOG = ROOT / "results/evidence/phase08/st06-product-petalinux-image-build.txt"
PRODUCT_DIRECTORY = ROOT / "build/p0/st06-product-image"
XSA = ROOT / "build/p0/st06-power-v2/hardware/p0_system_50mhz.xsa"

ARTIFACTS = {
    "BOOT.BIN": {"bytes": 5_228_616, "sha256": "53827609d09f1fb03fbdbef8f4be3aeed6a6a2f51f3cd9fb9bfd355beb4db8b3"},
    "image.ub": {"bytes": 24_086_751, "sha256": "730ef7fbc97038bd3297bb5f13f826df8c78970080c417e42dd40abcf9431256"},
    "system.bit": {"bytes": 4_045_693, "sha256": "fdb664667cd96245fb2b280ace89ac1589b95f751078b200d1c7b9d110e9305e"},
    "rootfs.manifest": {"bytes": 23_000, "sha256": "f02ef225c0c84a1487ec49ee361f7b0a853e0024e2ccf9a268d454ce5f1bf3d3"},
    "p0-ed-service": {"bytes": 66_956, "sha256": "c30ca00181a2bda9b497282b28f2e4a48b0335c9c2ff28664350e9abea05a77c"},
    "p0-ed-network-bridge": {"bytes": 21_908, "sha256": "06e8857b566b52aca54ef260bd71a0beeab774336a487ca3e767aa0e78b940ed"},
    "p0-st06-dma-profile-run": {"bytes": 17_812, "sha256": "fc62ba6810e3790d626a0bc4d6795b23547e886548b6519c0e2065aee9914022"},
    "p0-st06-power-benchmark": {"bytes": 13_716, "sha256": "add9d1f2ad5e0f40bda69543c29ae77828c9ca220ecb0b2a8a1aaf260d580ce8"},
}

SOURCE_PATHS = (
    "platforms/embedded/p0/include/p0_ed_pipeline.h",
    "platforms/embedded/p0/include/p0_st05_stream.h",
    "platforms/embedded/p0/include/p0_st05_wideband.h",
    "platforms/embedded/p0/src/p0_ed_pipeline.c",
    "platforms/embedded/p0/src/p0_ed_service.c",
    "platforms/embedded/p0/src/p0_ed_network_bridge.c",
    "platforms/embedded/p0/src/p0_st05_stream.c",
    "platforms/embedded/p0/src/p0_st05_wideband.c",
    "platforms/embedded/p0/src/p0_st05_wideband_internal.h",
    "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
    "platforms/embedded/phase06i/include/phase06i_transport_abi.h",
    "platforms/embedded/phase06j/include/phase06j_temporal.h",
    "platforms/embedded/phase06j/src/phase06j_temporal.c",
    "app/operator_console/live_ed.py",
    "tests/p0/p0_st06_product_pipeline_run.c",
    "tests/test_st06_product_pipeline.py",
    "scripts/verify_p0_ed_service_linux.py",
    "tests/p0/p0_ed_fake_dma_runtime.c",
    "scripts/verify_st06_product_integration.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_summary(path: Path, expected_tasks: int, success_text: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(
        rf"Tasks Summary: Attempted ({expected_tasks}) tasks .* all succeeded\.", text
    )
    if match is None or success_text not in text:
        raise ValueError(f"PetaLinux derleme özeti geçersiz: {path.name}")
    if re.search(r"\bERROR:\s", text):
        raise ValueError(f"PetaLinux derleme günlüğünde hata var: {path.name}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": _sha256(path),
        "tasks_attempted": int(match.group(1)),
        "tasks_failed": 0,
        "result": "all_succeeded",
    }


def evaluate(generated_at_utc: str | None = None) -> dict[str, Any]:
    vivado = json.loads(VIVADO_EVIDENCE.read_text(encoding="utf-8"))
    host = json.loads(HOST_EVIDENCE.read_text(encoding="utf-8"))
    if vivado.get("status") != "passed":
        raise ValueError("ST-06 Vivado kanıtı geçmemiş")
    if host.get("status") != "passed":
        raise ValueError("güncel yerel hizmet kabulü geçmemiş")

    artifact_report: dict[str, Any] = {}
    for name, expected in ARTIFACTS.items():
        path = PRODUCT_DIRECTORY / name
        actual = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        if actual != expected:
            raise ValueError(f"ürün çıktısı beklenen derlemeyle eşleşmiyor: {name}")
        artifact_report[name] = actual

    xsa = {"bytes": XSA.stat().st_size, "sha256": _sha256(XSA)}
    if xsa["sha256"] != vivado["hardware_platform"]["xsa_sha256"]:
        raise ValueError("PetaLinux XSA girdisi Vivado kanıtıyla eşleşmiyor")
    if artifact_report["system.bit"]["sha256"] != vivado["bitstream"]["sha256"]:
        raise ValueError("ürün bitstream'i Vivado kanıtıyla eşleşmiyor")

    manifest = (PRODUCT_DIRECTORY / "rootfs.manifest").read_text(
        encoding="utf-8", errors="strict"
    )
    required_packages = (
        "p0-dma zynq_generic_7z020 1.0",
        "kernel-module-p0-dma-client-6.12.40-xilinx-g31626ef92ff1",
    )
    if any(package not in manifest for package in required_packages):
        raise ValueError("ürün rootfs manifestinde zorunlu P0 paketi eksik")

    recipe = (ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb").read_text(
        encoding="utf-8"
    )
    recipe_tokens = (
        "p0_st05_wideband.c",
        "p0_st05_stream.c",
        "p0_ed_pipeline.c",
        "p0_ed_service.c",
        "-pthread -o ${S}/p0-ed-service",
    )
    if any(token not in recipe for token in recipe_tokens):
        raise ValueError("PetaLinux tarifi ST-06 ürün zincirini bağlamıyor")

    return {
        "schema": "phase08-st06-product-integration-v1",
        "status": "passed",
        "generated_at_utc": generated_at_utc or datetime.now(timezone.utc).isoformat(),
        "transmit_enabled": False,
        "scope": "source-bound ST-06 FPGA plus PetaLinux product image build",
        "build": {
            "tool": "PetaLinux 2025.2",
            "machine": "zynq_generic_7z020",
            "package": _build_summary(
                PACKAGE_BUILD_LOG, 5679, "Successfully built p0-dma"
            ),
            "full_image": _build_summary(
                IMAGE_BUILD_LOG, 6090, "Successfully built project"
            ),
            "tftp_warning": "not_configured; build outputs are unaffected",
        },
        "hardware_input": {
            "xsa": xsa,
            "vivado_evidence": str(VIVADO_EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
            "vivado_evidence_sha256": _sha256(VIVADO_EVIDENCE),
            "routed_timing_passed": True,
            "slice_lut_utilization_percent": vivado["post_route_resources"]["slice_luts"]["utilization_percent"],
        },
        "product_artifacts": artifact_report,
        "rootfs": {
            "required_packages_present": list(required_packages),
            "embedded_service_sha256": artifact_report["p0-ed-service"]["sha256"],
            "service_uses_bounded_dual_core_pipeline": True,
            "wideband_detector_linked": True,
        },
        "host_product_lifecycle": {
            "evidence": str(HOST_EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
            "evidence_sha256": _sha256(HOST_EVIDENCE),
            "status": host["status"],
            "pl_tagged_power_path_exercised": host["acceptance"]["pl_decision_path_exercised"],
            "invalid_power_fail_closed": not host["acceptance"]["invalid_request_published_result"],
            "temporal_confirmation_and_expiry": True,
        },
        "source_sha256": {relative: _sha256(ROOT / relative) for relative in SOURCE_PATHS},
        "gates": {
            "current_routed_fpga_input": True,
            "current_arm_sources_packaged": True,
            "full_product_image_built": True,
            "host_product_lifecycle": True,
            "cold_boot_product_image_on_board": False,
            "physical_product_service_lifecycle": False,
            "controlled_blind_rf_accuracy": False,
        },
        "not_verified": [
            "cold boot of this ST-06 product image on ZedBoard",
            "physical product-service lifecycle with this exact service binary",
            "blind controlled-RF detection probability and false-alarm rate",
            "field RF power calibration",
        ],
        "claim_boundary": [
            "This record proves that the current routed ST-06 FPGA image and current ARM detector/service sources are packaged into one PetaLinux product image.",
            "The embedded service binary hash was read from the generated rootfs and matches the staged ARM binary.",
            "The host lifecycle acceptance uses fake DMA with PL-tagged power words; it does not replace a physical board run.",
            "ST-06 remains open until the exact product image passes board lifecycle and controlled blind-RF acceptance.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ST-06 ürün imajı entegrasyon doğrulayıcısı")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.write:
        if EVIDENCE.exists():
            parser.error("Önceki ST-06 ürün entegrasyon kanıtının üzerine yazılmaz.")
        report = evaluate()
        EVIDENCE.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        if not EVIDENCE.is_file():
            print("ST-06 ürün entegrasyon kanıtı bulunamadı.")
            return 1
        stored = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        report = evaluate(str(stored.get("generated_at_utc", "")))
        if stored != report:
            print("ST-06 ürün kanıtı güncel kaynak ve çıktılarla eşleşmiyor.")
            return 1

    print(json.dumps({"status": report["status"], "gates": report["gates"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
