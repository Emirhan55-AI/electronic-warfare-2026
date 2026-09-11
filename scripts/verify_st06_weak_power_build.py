"""Validate the isolated weak-metadata FPGA/ARM build without rewriting v1 evidence."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VARIANT = "st06-weak-power-20260910"
BUILD = ROOT / "build/p0" / VARIANT
OUTPUT = ROOT / "results/evidence/phase08/st06-weak-power-20260910.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checkpoint_test():
    prefix = ["wsl.exe"] if os.name == "nt" else []
    target = f"build/p0/{VARIANT}/weak-checkpoint-test"
    sources = ["platforms/embedded/p0/src/p0_persistent_weak.c",
               "tests/p0/p0_weak_checkpoint_run.c"]
    subprocess.run([*prefix, "gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                    "-pedantic", "-Iplatforms/embedded/p0/include", *sources, "-o", target],
                   cwd=ROOT, check=True)
    run = subprocess.run([*prefix, target], cwd=ROOT, check=True, text=True, capture_output=True)
    match = re.search(r"WEAK_STATE_BYTES=(\d+) WEAK_CHECKPOINT_BYTES=(\d+) FRAMES=(\d+)", run.stdout)
    if not match or "ST06_PRODUCT_PIPELINE=PASS" not in run.stdout:
        raise ValueError("Zayıf durum geri alma eşitliği doğrulanamadı.")
    return {"status": "passed", "scope": "host byte-exact rollback and repeated-update comparison",
            "state_bytes": int(match[1]), "checkpoint_bytes": int(match[2]), "frames": int(match[3]),
            "source_sha256": {name: digest(ROOT / name) for name in sources + [
                "platforms/embedded/p0/include/p0_persistent_weak.h"]}}


def evaluate():
    spec = importlib.util.spec_from_file_location("weak_build_checks", ROOT / "scripts/verify_st06_power_vivado.py")
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
    checks.VARIANT = VARIANT
    checks.VARIANT_ROOT = BUILD
    checks.REPORT_ROOT = BUILD / "vivado/reports"
    checks.DSP_SYNTHESIS_LOG = BUILD / "vivado/p0_runtime.runs/p0_system_p0_dsp_runtime_0_0_synth_1/runme.log"
    checks.BITSTREAM = BUILD / "vivado/p0_runtime.runs/impl_1/p0_system_wrapper.bit"
    checks.XSA = BUILD / "hardware/p0_system_50mhz.xsa"
    result = checks.evaluate()
    if result["status"] != "passed":
        raise ValueError("Yeni FPGA yerleşim/zamanlama kontrolleri geçmedi.")
    export_log = ROOT / "build/st06-weak-power-export.log"
    export_text = export_log.read_text(encoding="utf-8", errors="replace")
    for marker in ("P0:LOCKED_IP_COUNT=0", "P0:RUN=synth_1 NEEDS_REFRESH=0",
                   "P0:RUN=impl_1 NEEDS_REFRESH=0", "P0:EXPORT_BOARD_METADATA=PASS"):
        if marker not in export_text:
            raise ValueError(f"Donanım dışa aktarımı doğrulanamadı: {marker}")
    with zipfile.ZipFile(checks.XSA) as archive:
        bitstreams = [name for name in archive.namelist() if name.endswith(".bit")]
        if len(bitstreams) != 1 or hashlib.sha256(archive.read(bitstreams[0])).hexdigest() != digest(checks.BITSTREAM):
            raise ValueError("XSA içindeki bitstream yerleştirilmiş çıktı ile eşleşmiyor.")
    result["hardware_export"] = {"status": "passed", "embedded_bitstream_matches": True,
                                 "log_sha256": digest(export_log)}
    result.update(schema="phase08-st06-weak-power-build-v1", product_algorithm_changed=True)
    result["data_path"][4] = "OS-CFAR strong + weak cell metadata (C/D format)"
    arm = json.loads((BUILD / "service-build.json").read_text(encoding="utf-8"))
    for name, expected in arm["sources"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"ARM derlemesinden sonra kaynak değişti: {name}")
    if digest(ROOT / arm["binary"]["path"]) != arm["binary"]["sha256"]:
        raise ValueError("ARM hizmeti hash'i eşleşmiyor.")
    result["arm_build"] = arm
    rtl_path = ROOT / "outputs/sinyal-tespiti-inceleme-20260910/weak-v2-rtl.json"
    rtl = json.loads(rtl_path.read_text(encoding="utf-8-sig"))
    for name, expected in rtl["sources"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"RTL simülasyonundan sonra kaynak değişti: {name}")
    result["rtl_simulation"] = rtl
    service_path = ROOT / "outputs/sinyal-tespiti-inceleme-20260910/weak-v2-service.json"
    service = json.loads(service_path.read_text(encoding="utf-8-sig"))
    if service.get("weak_power_service_status") != "passed":
        raise ValueError("Zayıf yol hizmet testi geçmedi.")
    for name, expected in service["weak_power_source_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"Hizmet testinden sonra kaynak değişti: {name}")
    result["host_service_test"] = service
    result["weak_checkpoint_test"] = checkpoint_test()
    result["physical_acceptance"] = {
        "board_service_identity_verified": False, "new_bitstream_loaded": False,
        "arm_throughput_measured": False, "gui_rx_soak_passed": False,
        "rf_pd_pfa_passed": False, "cold_boot_passed": False,
    }
    result["source_sha256"].update({name: digest(ROOT / name) for name in (
        "scripts/build_st06_weak_service.py", "scripts/check_st06_weak_power_rtl.py",
        "scripts/build_st06_weak_power.tcl", "scripts/resume_st06_weak_power.tcl",
        "scripts/export_st06_weak_power.tcl",
        "scripts/verify_st06_weak_power_build.py",
    )})
    result["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    return result


if __name__ == "__main__":
    result = evaluate()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "timing": result["timing"],
                      "resources": result["post_route_resources"],
                      "st06_complete": False}, indent=2))
