import hashlib
import json
from pathlib import Path

from scripts.verify_p0_ed_service import verify


ROOT = Path(__file__).resolve().parents[2]


def test_bounded_local_ed_service_protocol() -> None:
    result = verify()

    assert result["status"] == "passed"
    assert result["request_bytes_v1"] == 8224
    assert result["request_bytes_v2"] == 8272
    assert result["maximum_response_bytes_v1"] == 8772
    assert result["maximum_response_bytes_v2"] == 8916
    assert result["network_listener"] is False


def test_linux_host_acceptance_evidence_matches_sources() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/ed-local-service-host-acceptance.json").read_text(
            encoding="utf-8"
        )
    )

    assert evidence["status"] == "passed"
    assert evidence["scope"] == "host-only local service boundary"
    for name, expected in evidence["source_sha256"].items():
        source = ROOT / "platforms/embedded/p0/src" / name
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    assert "physical DMA through the service" in evidence["not_verified"]


def test_petalinux_build_evidence_matches_packaging_sources() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/ed-local-service-petalinux-build.json").read_text(
            encoding="utf-8"
        )
    )
    paths = {
        "p0-dma_1.0.bb": ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
        "p0_ed_service.c": ROOT / "platforms/embedded/p0/src/p0_ed_service.c",
        "p0_ed_client.c": ROOT / "platforms/embedded/p0/src/p0_ed_client.c",
        "p0_parameter_runtime.c": ROOT / "platforms/embedded/p0/src/p0_parameter_runtime.c",
        "p0_parameter_run.c": ROOT / "platforms/embedded/p0/src/p0_parameter_run.c",
        "p0_parameter_client.c": ROOT / "platforms/embedded/p0/src/p0_parameter_client.c",
    }

    assert evidence["status"] == "passed"
    assert evidence["build"]["tasks_failed"] == 0
    for name, source in paths.items():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == evidence["source_sha256"][name]
    assert evidence["physical_acceptance"] == (
        "results/evidence/p0/multiscale-detector-physical-acceptance.json"
    )
    assert "real-time throughput" in evidence["not_verified"]


def test_parameter_host_evidence_matches_sources() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/parameter-runtime-host-acceptance.json").read_text(
            encoding="utf-8"
        )
    )
    paths = {
        "p0_parameter_runtime.c": ROOT / "platforms/embedded/p0/src/p0_parameter_runtime.c",
        "p0_parameter_runtime.h": ROOT / "platforms/embedded/p0/include/p0_parameter_runtime.h",
        "verify_p0_parameter_runtime.py": ROOT / "scripts/verify_p0_parameter_runtime.py",
    }

    assert evidence["status"] == "passed"
    assert evidence["equivalence"]["maximum_absolute_error"] == 0.0
    assert evidence["equivalence"]["noise_only_fields_rejected"] == 6
    for name, source in paths.items():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == evidence["source_sha256"][name]


def test_parameter_petalinux_build_evidence_matches_sources() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/parameter-runtime-petalinux-build.json").read_text(
            encoding="utf-8"
        )
    )
    paths = {
        "p0-dma_1.0.bb": ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
        "p0_parameter_runtime.c": ROOT / "platforms/embedded/p0/src/p0_parameter_runtime.c",
        "p0_parameter_run.c": ROOT / "platforms/embedded/p0/src/p0_parameter_run.c",
        "p0_parameter_client.c": ROOT / "platforms/embedded/p0/src/p0_parameter_client.c",
    }

    assert evidence["status"] == "passed"
    assert evidence["build"]["tasks_attempted"] == 5679
    assert evidence["build"]["tasks_failed"] == 0
    for name, source in paths.items():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == evidence["source_sha256"][name]


def test_parameter_physical_evidence_is_bounded_and_traceable() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/parameter-runtime-physical-acceptance.json").read_text(
            encoding="utf-8"
        )
    )
    paths = {
        "p0_parameter_runtime.c": ROOT / "platforms/embedded/p0/src/p0_parameter_runtime.c",
        "p0_ed_service.c": ROOT / "platforms/embedded/p0/src/p0_ed_service.c",
        "p0_parameter_client.c": ROOT / "platforms/embedded/p0/src/p0_parameter_client.c",
        "verify_p0_parameter_runtime_physical.py":
            ROOT / "scripts/verify_p0_parameter_runtime_physical.py",
    }

    assert evidence["status"] == "passed"
    assert evidence["platform"]["fpga_manager_state"] == "operating"
    assert evidence["measurement"]["observations"] == [1, 2, 3, 4]
    assert evidence["measurement"]["dma_status_flags"] == [7, 7, 7, 7]
    assert evidence["measurement"]["premature_numeric_publication"] is False
    assert evidence["measurement"]["final_valid_fields"] == 6
    assert evidence["cross_architecture_equivalence"]["maximum_absolute_error"] == 0.0
    assert evidence["ideal_fft_characterization"]["pass_fail_gate"] is None
    for name, source in paths.items():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == evidence["source_sha256"][name]
    assert "one deterministic AM sequence" in evidence["claim_boundary"]


def test_physical_service_evidence_is_bounded_and_traceable() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/ed-local-service-physical-acceptance.json").read_text(
            encoding="utf-8"
        )
    )

    assert evidence["status"] == "passed"
    assert evidence["acceptance"]["frames"] == 5
    assert evidence["acceptance"]["dma_status_flags_all_frames"] == 7
    assert evidence["acceptance"]["host_reference_event_field_equivalence"] is True
    assert evidence["privilege_boundary"]["unprivileged_client"] == "passed"
    assert evidence["service_lifecycle"]["pid_before_restart"] != evidence["service_lifecycle"]["pid_after_restart"]
    assert "does not establish detector accuracy" in evidence["claim_boundary"]
