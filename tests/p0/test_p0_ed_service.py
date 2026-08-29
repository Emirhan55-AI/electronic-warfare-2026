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
    assert result["request_bytes_v3"] == 8224
    assert result["maximum_response_bytes_v1"] == 8772
    assert result["maximum_response_bytes_v2"] == 8916
    assert result["maximum_response_bytes_v3"] == 8772
    assert result["compact_response_bytes_for_two_events_v3"] == 204
    assert result["network_listener"] is False


def test_candidate_packet_dma_runtime_contract_is_variable_length_and_fail_closed() -> None:
    uapi = (ROOT / "platforms/embedded/p0/include/p0_dma_uapi.h").read_text(encoding="utf-8")
    driver = (ROOT / "platforms/embedded/p0/src/p0_dma_client.c").read_text(encoding="utf-8")
    runtime = (ROOT / "platforms/embedded/p0/src/p0_dma_runtime.c").read_text(encoding="utf-8")

    assert "#define P0_DMA_ABI_VERSION 2U" in uapi
    assert "#define P0_DMA_OUTPUT_CAPACITY_BYTES 54144U" in uapi
    assert "__u32 output_capacity_bytes;" in uapi
    assert "P0_S2MM_LENGTH" in driver
    assert "P0_DMA_OUTPUT_CAPACITY_BYTES" in driver
    assert "dma->status.output_bytes = p0_read(dma, P0_S2MM_LENGTH)" in driver
    assert "status->output_bytes > P0_DMA_OUTPUT_CAPACITY_BYTES" in runtime
    assert "status->output_bytes % P0_DMA_OUTPUT_ALIGNMENT_BYTES" in runtime
    assert "read_packet(runtime->descriptor" in runtime


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
    for name, expected in evidence["acceptance_source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    assert evidence["acceptance"]["pl_decision_path_exercised"] is True
    assert "cold-boot persistence of the ABI v3 service image" in evidence["not_verified"]


def test_petalinux_build_evidence_matches_packaging_sources() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/ed-local-service-petalinux-build.json").read_text(
            encoding="utf-8"
        )
    )
    paths = {
        "p0-dma_1.0.bb": ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
        "p0_ed_service.c": ROOT / "platforms/embedded/p0/src/p0_ed_service.c",
        "p0_ed_service_protocol.c": ROOT / "platforms/embedded/p0/src/p0_ed_service_protocol.c",
        "p0_ed_service_protocol.h": ROOT / "platforms/embedded/p0/include/p0_ed_service_protocol.h",
        "p0_ed_client.c": ROOT / "platforms/embedded/p0/src/p0_ed_client.c",
        "p0_ed_throughput_run.c": ROOT / "platforms/embedded/p0/src/p0_ed_throughput_run.c",
        "p0_parameter_runtime.c": ROOT / "platforms/embedded/p0/src/p0_parameter_runtime.c",
        "p0_parameter_run.c": ROOT / "platforms/embedded/p0/src/p0_parameter_run.c",
        "p0_parameter_client.c": ROOT / "platforms/embedded/p0/src/p0_parameter_client.c",
        "p0_multiscale_detector.c": ROOT / "platforms/embedded/p0/src/p0_multiscale_detector.c",
        "p0_multiscale_detector.h": ROOT / "platforms/embedded/p0/include/p0_multiscale_detector.h",
        "p0_ed_pipeline.c": ROOT / "platforms/embedded/p0/src/p0_ed_pipeline.c",
        "p0_ed_runtime_run.c": ROOT / "platforms/embedded/p0/src/p0_ed_runtime_run.c",
        "p0_os_cfar.c": ROOT / "platforms/embedded/p0/src/p0_os_cfar.c",
        "p0_os_cfar.h": ROOT / "platforms/embedded/p0/include/p0_os_cfar.h",
        "p0_pl_os_cfar.c": ROOT / "platforms/embedded/p0/src/p0_pl_os_cfar.c",
        "p0_pl_os_cfar.h": ROOT / "platforms/embedded/p0/include/p0_pl_os_cfar.h",
        "p0_ed_stage_profile_run.c": ROOT / "platforms/embedded/p0/src/p0_ed_stage_profile_run.c",
        "p0_candidate_packet.c": ROOT / "platforms/embedded/p0/src/p0_candidate_packet.c",
    }

    assert evidence["status"] == "passed"
    assert evidence["build"]["tasks_failed"] == 0
    assert evidence["current_source_status"] in {
        "current_sources_petalinux_build_passed",
        "baseline_build_superseded_pending_adr0032_rebuild",
        "baseline_build_superseded_pending_candidate_packet_runtime_rebuild",
        "baseline_build_superseded_pending_service_v3_rebuild",
    }
    assert evidence["build"]["full_image_tasks_failed"] == 0
    vivado = json.loads(
        (ROOT / "results/evidence/p0/vivado-50mhz.json").read_text(encoding="utf-8")
    )
    if evidence.get("hardware_input_current", True):
        assert evidence["hardware_input"]["xsa_sha256"] == vivado["hardware_platform"]["xsa_sha256"]
        assert evidence["hardware_input"]["system_bit_sha256"] == vivado["bitstream"]["sha256"]
    else:
        assert evidence["current_source_status"].startswith("baseline_build_superseded_pending_")
        assert evidence["superseded_by_hardware_input"]["xsa_sha256"] == vivado["hardware_platform"]["xsa_sha256"]
        assert evidence["superseded_by_hardware_input"]["system_bit_sha256"] == vivado["bitstream"]["sha256"]
    if evidence["current_source_status"] == "current_sources_petalinux_build_passed":
        for name, source in paths.items():
            assert hashlib.sha256(source.read_bytes()).hexdigest() == evidence["source_sha256"][name]
    else:
        assert evidence["current_source_status"].startswith("baseline_build_superseded_pending_")
    assert evidence["prior_physical_acceptance"] == (
        "results/evidence/p0/multiscale-detector-physical-acceptance.json"
    )
    assert evidence["cold_boot_acceptance"] == (
        "results/evidence/p0/ed-service-v3-cold-boot-acceptance.json"
    )
    assert "cold-boot persistence of the ABI v3 service image" not in evidence["not_verified"]


def test_vivado_build_evidence_matches_current_sources() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/vivado-50mhz.json").read_text(encoding="utf-8")
    )

    assert evidence["status"] == "passed"
    assert evidence["block_design_validation"] == "PASS"
    assert evidence["hann_memory_initialization"]["status"] == "PASS"
    assert evidence["hann_memory_initialization"]["failure_count"] == 0
    assert evidence["route"]["routing_errors"] == 0
    assert evidence["timing"]["setup_failing_endpoints"] == 0
    assert evidence["timing"]["hold_failing_endpoints"] == 0
    assert evidence["drc_errors"] == 0
    assert evidence["drc_critical_warnings"] == 0
    assert evidence["bitstream"]["status"] == "PASS"
    assert evidence["scope"] == "ZedBoard CI8-to-candidate-packet Vivado build"
    assert evidence["dma"]["candidate_packet_bytes"] == {"minimum": 64, "maximum": 54144}
    assert evidence["dma"]["software_contract"] == (
        "petalinux_rebuild_passed_pending_board_acceptance"
    )
    for resource in evidence["post_route_resources"].values():
        assert 0 < resource["used"] <= resource["available"]
        assert 0.0 < resource["utilization_percent"] <= 100.0
    for name, expected in evidence["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected


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
    assert evidence["current_source_status"] in {
        "current_sources_petalinux_build_passed",
        "baseline_build_superseded_pending_service_v3_rebuild",
    }
    assert evidence["build"]["full_image_tasks_failed"] == 0
    if evidence["current_source_status"] == "current_sources_petalinux_build_passed":
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
    if evidence["current_source_status"].startswith("historical_"):
        assert evidence["current_source_status"].endswith("candidate_packet_board_acceptance")
    else:
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


def test_physical_throughput_evidence_is_repeatable_and_traceable() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/ed-throughput-physical-acceptance.json").read_text(
            encoding="utf-8"
        )
    )
    paths = {
        "p0_ed_throughput_run.c": ROOT / "platforms/embedded/p0/src/p0_ed_throughput_run.c",
        "p0_ed_service.c": ROOT / "platforms/embedded/p0/src/p0_ed_service.c",
        "p0_ed_service_protocol.c": ROOT / "platforms/embedded/p0/src/p0_ed_service_protocol.c",
        "p0_ed_pipeline.c": ROOT / "platforms/embedded/p0/src/p0_ed_pipeline.c",
        "p0-dma_1.0.bb": ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
    }

    assert evidence["status"] == "passed"
    assert evidence["repeatability"]["runs"] == 5
    assert evidence["repeatability"]["passed_runs"] == 5
    assert evidence["repeatability"]["completed_frames"] == 20_480
    assert evidence["repeatability"]["minimum_frames_per_second"] >= 2_000_000 / 4096
    assert evidence["repeatability"]["minimum_real_time_margin"] >= 1.0
    assert all(run["real_time_margin"] >= 1.0 for run in evidence["runs"])
    assert evidence["functional_regression"]["event_field_equivalence"] is True
    for name, source in paths.items():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == evidence["source_sha256"][name]
    assert "live HackRF throughput" in evidence["claim_boundary"]


def test_persistent_service_image_cold_boot_evidence_is_traceable() -> None:
    evidence = json.loads(
        (ROOT / "results/evidence/p0/ed-service-v3-cold-boot-acceptance.json").read_text(
            encoding="utf-8"
        )
    )
    paths = {
        "p0_ed_service.c": ROOT / "platforms/embedded/p0/src/p0_ed_service.c",
        "p0_ed_service_protocol.c": ROOT / "platforms/embedded/p0/src/p0_ed_service_protocol.c",
        "p0_ed_client.c": ROOT / "platforms/embedded/p0/src/p0_ed_client.c",
        "p0_ed_throughput_run.c": ROOT / "platforms/embedded/p0/src/p0_ed_throughput_run.c",
        "p0_ed_pipeline.c": ROOT / "platforms/embedded/p0/src/p0_ed_pipeline.c",
        "p0-dma_1.0.bb": ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
    }

    assert evidence["status"] == "passed"
    assert evidence["boot"]["fpga_manager_state"] == "operating"
    assert evidence["boot"]["service_started_by_image"] is True
    assert evidence["functional_acceptance"]["candidate_field_equivalence"] is True
    assert evidence["functional_acceptance"]["event_field_equivalence"] is True
    assert evidence["throughput_acceptance"]["completed_frames"] == 4096
    assert evidence["throughput_acceptance"]["measured_frames_per_second"] >= 2_000_000 / 4096
    assert evidence["throughput_acceptance"]["real_time_margin"] >= 1.0
    for name, source in paths.items():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == evidence["source_sha256"][name]
    assert "live HackRF throughput" in evidence["claim_boundary"]
