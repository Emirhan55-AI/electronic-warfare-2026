#!/usr/bin/env python3
"""Record the cold-boot physical acceptance of the ADR-0040 P0 pipeline."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import verify_p0_phase07_physical as transport_gate


EVIDENCE_PATH = ROOT / "results/evidence/p0/adr0040-physical-acceptance.json"
EXPECTED_FUNCTIONAL = (
    (104, 50, 0, 0, 0),
    (104, 50, 0, 0, 0),
    (104, 50, 0, 0, 0),
    (0, 50, 0, 0, 0),
    (0, 0, 50, 0, 0),
)
SOURCE_PATHS = (
    "algorithms/ps/persistent_weak_cfar.py",
    "platforms/embedded/p0/include/p0_persistent_weak.h",
    "platforms/embedded/p0/src/p0_persistent_weak.c",
    "platforms/embedded/p0/src/p0_ed_pipeline.c",
    "platforms/embedded/phase06j/src/phase06j_temporal.c",
    "platforms/embedded/p0/src/p0_ed_network_bridge.c",
    "algorithms/p0/transport.py",
    "scripts/verify_p0_phase07_physical.py",
    "scripts/verify_p0_adr0040_physical.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validated_sha256(value: str, label: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{label} geçerli bir SHA-256 özeti değildir.")
    return normalized


def evaluate(
    host: str,
    port: int,
    *,
    image_sha256: str,
    service_sha256: str,
    bridge_sha256: str,
    boot_id: str,
    network_interface: str,
) -> dict[str, object]:
    image_sha256 = _validated_sha256(image_sha256, "İmaj")
    service_sha256 = _validated_sha256(service_sha256, "Hizmet")
    bridge_sha256 = _validated_sha256(bridge_sha256, "Köprü")
    if not boot_id.strip() or not network_interface.strip():
        raise ValueError("Soğuk açılış kimliği ve ağ arayüzü zorunludur.")

    known = transport_gate._load_known_frame()
    previous_expected = transport_gate.EXPECTED_FUNCTIONAL
    transport_gate.EXPECTED_FUNCTIONAL = EXPECTED_FUNCTIONAL
    try:
        functional = transport_gate._functional_acceptance(host, port, known)
        runs = [
            transport_gate._throughput_acceptance(host, port, known)
            for _ in range(transport_gate.REPEAT_RUNS)
        ]
    finally:
        transport_gate.EXPECTED_FUNCTIONAL = previous_expected

    rates = [float(run["measured_frames_per_second"]) for run in runs]
    margins = [float(run["real_time_margin"]) for run in runs]
    passed = (
        len(runs) == transport_gate.REPEAT_RUNS
        and all(math.isfinite(rate) for rate in rates)
        and min(rates) >= transport_gate.REQUIRED_FRAMES_PER_SECOND
        and sum(int(run["client_sequence_errors"]) for run in runs) == 0
        and all(int(item["dropped_candidates"]) == 0 for item in functional)
    )
    if not passed:
        raise RuntimeError("ADR-0040 fiziksel kabul sonuçları geçiş koşullarını sağlamadı.")

    return {
        "schema": "p0-adr0040-physical-acceptance-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "scope": "P09 soğuk açılış; Ethernet→ARM→DMA→FPGA→ARM aday ve zaman doğrulama zinciri",
        "endpoint": {"host": host, "port": port},
        "persistent_image": {
            "image_ub_sha256": image_sha256,
            "service_sha256": service_sha256,
            "bridge_sha256": bridge_sha256,
            "boot_id": boot_id,
            "network_interface": network_interface,
            "link_speed_mbps": 1000,
            "duplex": "full",
            "automatic_service_start": True,
            "automatic_bridge_start": True,
        },
        "profile": {
            "sample_rate_hz": transport_gate.SAMPLE_RATE_HZ,
            "fft_size": transport_gate.FRAME_SAMPLES,
            "required_frames_per_second": transport_gate.REQUIRED_FRAMES_PER_SECOND,
            "weak_threshold_db": 6.0,
            "weak_window_frames": 32,
            "weak_required_frames": 24,
            "maximum_tracked_weak_nominations_per_frame": 8,
            "known_frame_sha256": hashlib.sha256(known).hexdigest(),
        },
        "functional_acceptance": functional,
        "throughput_acceptance": {
            "repeat_runs": len(runs),
            "measured_frames_per_run": transport_gate.MEASURED_FRAMES,
            "completed_measured_frames": transport_gate.MEASURED_FRAMES * len(runs),
            "minimum_frames_per_second": min(rates),
            "mean_frames_per_second": sum(rates) / len(rates),
            "maximum_frames_per_second": max(rates),
            "minimum_real_time_margin": min(margins),
            "client_sequence_errors": sum(
                int(run["client_sequence_errors"]) for run in runs
            ),
            "runs": runs,
        },
        "source_sha256": {name: _sha256(ROOT / name) for name in SOURCE_PATHS},
        "claim_boundary": (
            "Bu kanıt, kalıcı P09 imajındaki sayısal aday zincirinin ZedBoard üzerinde "
            "işlev ve sürekli 2 MS/s hız koşullarını karşıladığını gösterir. Canlı, kör RF "
            "tespit olasılığı, yanlış alarm oranı ve kalibre dBm doğruluğu ayrıca saha "
            "kabulü gerektirir."
        ),
    }


def check() -> bool:
    try:
        evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        sources = evidence.get("source_sha256", {})
        functional = evidence.get("functional_acceptance", [])
        observed_functional = tuple(
            (
                int(item["raw_candidate_count"]),
                int(item["active_count"]),
                int(item["ended_count"]),
                int(item["dropped_candidates"]),
                int(item["reset_applied"]),
            )
            for item in functional
        )
        throughput = evidence.get("throughput_acceptance", {})
        return (
            evidence.get("schema") == "p0-adr0040-physical-acceptance-v1"
            and evidence.get("status") == "passed"
            and set(sources) == set(SOURCE_PATHS)
            and all(_sha256(ROOT / name) == sources[name] for name in SOURCE_PATHS)
            and observed_functional == EXPECTED_FUNCTIONAL
            and all(int(item["dma_status_flags"]) == 7 for item in functional)
            and int(throughput.get("repeat_runs", 0)) == transport_gate.REPEAT_RUNS
            and int(throughput.get("completed_measured_frames", 0))
            == transport_gate.MEASURED_FRAMES * transport_gate.REPEAT_RUNS
            and throughput.get("minimum_frames_per_second", 0.0)
            >= transport_gate.REQUIRED_FRAMES_PER_SECOND
            and throughput.get("client_sequence_errors") == 0
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--host", default="192.168.7.2")
    parser.add_argument("--port", type=int, default=47007)
    parser.add_argument("--image-sha256")
    parser.add_argument("--service-sha256")
    parser.add_argument("--bridge-sha256")
    parser.add_argument("--boot-id")
    parser.add_argument("--network-interface")
    args = parser.parse_args()

    if args.write:
        required = {
            "--image-sha256": args.image_sha256,
            "--service-sha256": args.service_sha256,
            "--bridge-sha256": args.bridge_sha256,
            "--boot-id": args.boot_id,
            "--network-interface": args.network_interface,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            parser.error(f"--write için zorunlu alanlar eksik: {', '.join(missing)}")
        document = evaluate(
            args.host,
            args.port,
            image_sha256=args.image_sha256,
            service_sha256=args.service_sha256,
            bridge_sha256=args.bridge_sha256,
            boot_id=args.boot_id,
            network_interface=args.network_interface,
        )
        EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE_PATH.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    passed = check()
    print(f"ADR-0040 fiziksel kabul: {'başarılı' if passed else 'başarısız'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
