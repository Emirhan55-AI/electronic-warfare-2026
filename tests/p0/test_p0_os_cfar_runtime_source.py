from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "platforms/embedded/p0/src/p0_os_cfar_run.c"
RECIPE = ROOT / "platforms/embedded/p0/petalinux/p0-dma_1.0.bb"
TEMPORAL_SOURCE = ROOT / "platforms/embedded/p0/src/p0_ed_runtime_run.c"
PACKET_SOURCE = ROOT / "platforms/embedded/p0/src/p0_candidate_packet.c"
MULTISCALE_SOURCE = ROOT / "platforms/embedded/p0/src/p0_multiscale_detector.c"
PL_SOURCE = ROOT / "platforms/embedded/p0/src/p0_pl_os_cfar.c"
PIPELINE_SOURCE = ROOT / "platforms/embedded/p0/src/p0_ed_pipeline.c"


def test_arm_runtime_uses_fixed_physical_power_contract() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "#define P0_FRAME_BINS 4096U" in source
    assert "#define P0_POWER_BYTES_PER_BIN 8U" in source
    assert "#define P0_POWER_FRACTION_BITS 30U" in source
    assert "natural_bin ^ (P0_FRAME_BINS / 2U)" in source
    assert "load_u64_le" in source


def test_arm_runtime_uses_canonical_os_cfar_and_bounded_candidates() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "p0_os_cfar_canonical_config(&config)" in source
    assert "p0_os_cfar_process(" in source
    assert "P0_MAX_CANDIDATES P0_FRAME_BINS" in source
    assert '\\"output_bin_order\\"' in source


def test_petalinux_recipe_builds_and_installs_arm_runtime() -> None:
    recipe = RECIPE.read_text(encoding="utf-8")

    for required in ("p0_os_cfar.c", "p0_os_cfar.h", "p0_os_cfar_run.c"):
        assert f"file://{required}" in recipe
    assert "-lm -o ${S}/p0-os-cfar-run" in recipe
    assert "install -m 0755 ${S}/p0-os-cfar-run ${D}${bindir}/p0-os-cfar-run" in recipe
    assert "${bindir}/p0-os-cfar-run" in recipe


def test_pl_dma_format_is_validated_before_accelerated_processing() -> None:
    decoder = PL_SOURCE.read_text(encoding="utf-8")
    pipeline = PIPELINE_SOURCE.read_text(encoding="utf-8")

    for token in (
        "P0_FORMAT_MARKER", "marked_words != 0U && marked_words != P0_PL_OS_CFAR_FRAME_BINS",
        "evaluated != expected_evaluated", "detected && !evaluated",
    ):
        assert token in decoder
    assert pipeline.index("p0_pl_os_cfar_decode(") < pipeline.index("p0_multiscale_process_pl_trusted(")
    assert "p0_multiscale_process(" in pipeline
    assert "p0_multiscale_process_pl_trusted(" in pipeline


def test_temporal_runtime_preserves_versioned_packet_boundary() -> None:
    runtime = TEMPORAL_SOURCE.read_text(encoding="utf-8")
    packet = PACKET_SOURCE.read_text(encoding="utf-8")

    assert "p0_multiscale_process(" in runtime
    assert "p0_candidate_packet_encode(" in runtime
    assert "phase06j_process_packet(" in runtime

    pipeline = (ROOT / "platforms/embedded/p0/src/p0_ed_pipeline.c").read_text(
        encoding="utf-8"
    )
    assert "p0_candidate_records_encode(" in pipeline
    assert "phase06j_process_candidates(" in pipeline
    assert "phase06j_state_init(" in runtime
    assert "rename(output_temporary, argv[1])" in runtime
    assert "remove(output_temporary)" in runtime
    assert "PHASE06I_HEADER_MAGIC" in packet
    assert "crc32_ieee(" in packet
    assert "P0_CANONICAL_PFA_SELECT 1U" in packet


def test_petalinux_recipe_builds_and_installs_temporal_runtime() -> None:
    recipe = RECIPE.read_text(encoding="utf-8")

    for required in (
        "p0_candidate_packet.c", "p0_candidate_packet.h", "p0_ed_runtime_run.c",
        "p0_multiscale_detector.c", "p0_multiscale_detector.h",
        "p0_pl_os_cfar.c", "p0_pl_os_cfar.h",
        "phase06i_transport_abi.h", "phase06j_temporal.c", "phase06j_temporal.h",
    ):
        assert f"file://{required}" in recipe
    assert "-o ${S}/p0-ed-runtime-run" in recipe
    assert "install -m 0755 ${S}/p0-ed-runtime-run ${D}${bindir}/p0-ed-runtime-run" in recipe


def test_multiscale_source_keeps_locked_recovery_boundary() -> None:
    source = MULTISCALE_SOURCE.read_text(encoding="utf-8")

    assert "P0_MULTISCALE_MINIMUM_RECOVERY_SPAN" in source
    assert "P0_MULTISCALE_INTEGRATION_BINS" in source
    assert "P0_REGIONAL_NOISE_MULTIPLIER 2.5" in source
    assert "append_integrated_recovery" in source
    assert "p0_os_cfar_process(" in source
    assert "P0_MULTISCALE_REGION_BINS" in source
    assert "overlaps(&candidates[index], &recoveries[recovery_index])" in source
