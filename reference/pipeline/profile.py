"""Path-free canonical profile validation and allowlisted runtime construction."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from reference.detection import DetectionFrameResult, DetectionPipeline, DetectorConfig, LinearPowerDetector
from reference.spectrum import SpectrumConfig, SpectrumProcessor, SpectrumResult


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE_PATH = ROOT / "profiles" / "phase03" / "operation-default.json"
BLOCK_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
Lifecycle = Literal["experimental", "validated"]


class ProfileError(ValueError):
    """Raised for a typed processing-profile contract violation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PortDefinition:
    name: str
    data_type: str


@dataclass(frozen=True)
class BlockDefinition:
    type_id: str
    version: int
    inputs: tuple[PortDefinition, ...]
    outputs: tuple[PortDefinition, ...]
    required_parameters: frozenset[str]
    allowed_parameters: frozenset[str]


@dataclass(frozen=True)
class BlockInstance:
    block_id: str
    type_id: str
    version: int
    parameters: dict[str, Any]
    validated_parameter_envelope: dict[str, tuple[Any, ...]]


@dataclass(frozen=True)
class Connection:
    source_block: str
    source_port: str
    target_block: str
    target_port: str

    @property
    def key(self) -> tuple[str, str, str, str]:
        return self.source_block, self.source_port, self.target_block, self.target_port


@dataclass(frozen=True)
class ProcessingProfile:
    schema_version: int
    profile_id: str
    profile_version: int
    lifecycle: Lifecycle
    blocks: tuple[BlockInstance, ...]
    connections: tuple[Connection, ...]

    @property
    def detector_block(self) -> BlockInstance:
        matches = [block for block in self.blocks if block.type_id.startswith("detector.")]
        if len(matches) != 1:
            raise ProfileError("detector_count", "profile must contain exactly one detector block")
        return matches[0]

    @property
    def detector_method(self) -> str:
        return {
            "detector.regional": "regional",
            "detector.ca-cfar": "ca_cfar",
            "detector.os-cfar": "os_cfar",
            "detector.os-regional-cap": "os_regional_cap",
        }[self.detector_block.type_id]

    @property
    def display_name(self) -> str:
        return f"{self.profile_id} v{self.profile_version}"


@dataclass(frozen=True)
class RuntimeFrameResult:
    spectrum: SpectrumResult
    detection: DetectionFrameResult


BLOCK_DEFINITIONS: dict[tuple[str, int], BlockDefinition] = {
    ("source.sigmf-recorded", 1): BlockDefinition(
        "source.sigmf-recorded",
        1,
        (),
        (PortDefinition("frame", "iq.frame/v1"),),
        frozenset({"frame_length"}),
        frozenset({"frame_length"}),
    ),
    ("dsp.phase02-spectrum", 1): BlockDefinition(
        "dsp.phase02-spectrum",
        1,
        (PortDefinition("frame", "iq.frame/v1"),),
        (PortDefinition("spectrum", "spectrum.power/v1"),),
        frozenset({"frame_length", "remove_dc"}),
        frozenset({"frame_length", "remove_dc"}),
    ),
    ("detector.regional", 1): BlockDefinition(
        "detector.regional",
        1,
        (PortDefinition("spectrum", "spectrum.power/v1"),),
        (PortDefinition("cells", "detection.cells/v1"),),
        frozenset({"pfa", "evaluate_center", "region_size"}),
        frozenset({"pfa", "evaluate_center", "region_size"}),
    ),
    ("detector.ca-cfar", 1): BlockDefinition(
        "detector.ca-cfar",
        1,
        (PortDefinition("spectrum", "spectrum.power/v1"),),
        (PortDefinition("cells", "detection.cells/v1"),),
        frozenset({"pfa", "evaluate_center", "training_cells_per_side", "guard_cells_per_side"}),
        frozenset({"pfa", "evaluate_center", "training_cells_per_side", "guard_cells_per_side"}),
    ),
    ("detector.os-cfar", 1): BlockDefinition(
        "detector.os-cfar",
        1,
        (PortDefinition("spectrum", "spectrum.power/v1"),),
        (PortDefinition("cells", "detection.cells/v1"),),
        frozenset({"pfa", "evaluate_center", "training_cells_per_side", "guard_cells_per_side", "rank"}),
        frozenset({"pfa", "evaluate_center", "training_cells_per_side", "guard_cells_per_side", "rank"}),
    ),
    ("detector.os-regional-cap", 1): BlockDefinition(
        "detector.os-regional-cap",
        1,
        (PortDefinition("spectrum", "spectrum.power/v1"),),
        (PortDefinition("cells", "detection.cells/v1"),),
        frozenset(
            {"pfa", "evaluate_center", "training_cells_per_side", "guard_cells_per_side", "rank", "region_size"}
        ),
        frozenset(
            {"pfa", "evaluate_center", "training_cells_per_side", "guard_cells_per_side", "rank", "region_size"}
        ),
    ),
    ("detection.group-regions", 1): BlockDefinition(
        "detection.group-regions",
        1,
        (PortDefinition("cells", "detection.cells/v1"),),
        (PortDefinition("regions", "detection.regions/v1"),),
        frozenset({"max_gap_bins"}),
        frozenset({"max_gap_bins"}),
    ),
    ("detection.temporal-m-of-n", 1): BlockDefinition(
        "detection.temporal-m-of-n",
        1,
        (PortDefinition("regions", "detection.regions/v1"),),
        (PortDefinition("events", "detection.events/v1"),),
        frozenset(
            {
                "confirmations_required",
                "confirmation_window",
                "association_tolerance_bins",
                "max_active_tracks",
                "max_ended_history",
            }
        ),
        frozenset(
            {
                "confirmations_required",
                "confirmation_window",
                "association_tolerance_bins",
                "max_active_tracks",
                "max_ended_history",
            }
        ),
    ),
    ("sink.operator-console", 1): BlockDefinition(
        "sink.operator-console",
        1,
        (
            PortDefinition("spectrum", "spectrum.power/v1"),
            PortDefinition("events", "detection.events/v1"),
        ),
        (PortDefinition("view", "operation.view/v1"),),
        frozenset({"max_visible_events", "max_waterfall_rows"}),
        frozenset({"max_visible_events", "max_waterfall_rows"}),
    ),
}


class RuntimePipeline:
    """Actual operation pipeline constructed exclusively from a validated profile."""

    def __init__(
        self,
        profile: ProcessingProfile,
        *,
        pfa: float | None = None,
        evaluate_center: bool | None = None,
        remove_dc: bool | None = None,
        allow_experimental: bool = False,
    ) -> None:
        if profile.lifecycle != "validated" and not allow_experimental:
            raise ProfileError("profile_not_validated", "operation requires a validated processing profile")
        detector_block = profile.detector_block
        dsp_block = next(block for block in profile.blocks if block.type_id == "dsp.phase02-spectrum")
        source_block = next(block for block in profile.blocks if block.type_id == "source.sigmf-recorded")
        sink_block = next(block for block in profile.blocks if block.type_id == "sink.operator-console")
        detector_pfa = float(detector_block.parameters["pfa"] if pfa is None else pfa)
        detector_center = bool(
            detector_block.parameters["evaluate_center"] if evaluate_center is None else evaluate_center
        )
        dc_setting = bool(dsp_block.parameters["remove_dc"] if remove_dc is None else remove_dc)
        _validate_override(detector_block, "pfa", detector_pfa)
        _validate_override(detector_block, "evaluate_center", detector_center)
        _validate_override(dsp_block, "remove_dc", dc_setting)

        self.profile = profile
        self.pfa = detector_pfa
        self.evaluate_center = detector_center
        self.remove_dc = dc_setting
        frame_length = int(dsp_block.parameters["frame_length"])
        if int(source_block.parameters["frame_length"]) != frame_length:
            raise ProfileError("frame_length_mismatch", "source and spectrum frame lengths differ")
        if (
            int(sink_block.parameters["max_visible_events"]) != DetectionPipeline.MAX_VISIBLE_EVENTS
            or int(sink_block.parameters["max_waterfall_rows"]) != 128
        ):
            raise ProfileError("sink_bounds_invalid", "operation sink violates bounded UI limits")
        self.processor = SpectrumProcessor(SpectrumConfig(frame_length=frame_length, remove_dc=dc_setting))
        detector_config = DetectorConfig(
            method=profile.detector_method,  # type: ignore[arg-type]
            pfa=detector_pfa,
            frame_length=frame_length,
            training_cells_per_side=int(detector_block.parameters.get("training_cells_per_side", 16)),
            guard_cells_per_side=int(detector_block.parameters.get("guard_cells_per_side", 4)),
            os_rank=int(detector_block.parameters.get("rank", 24)),
            region_size=int(detector_block.parameters.get("region_size", 256)),
            evaluate_center=detector_center,
        )
        detector = LinearPowerDetector(detector_config)
        group_block = next(block for block in profile.blocks if block.type_id == "detection.group-regions")
        temporal_block = next(block for block in profile.blocks if block.type_id == "detection.temporal-m-of-n")
        if (
            int(temporal_block.parameters["max_active_tracks"]) != DetectionPipeline.MAX_ACTIVE_TRACKS
            or int(temporal_block.parameters["max_ended_history"]) != DetectionPipeline.MAX_ENDED_HISTORY
        ):
            raise ProfileError("temporal_bounds_invalid", "operation temporal block violates memory limits")
        self.detection = DetectionPipeline(
            detector,
            max_gap_bins=int(group_block.parameters["max_gap_bins"]),
            association_tolerance_bins=int(temporal_block.parameters["association_tolerance_bins"]),
            confirmations_required=int(temporal_block.parameters["confirmations_required"]),
            confirmation_window=int(temporal_block.parameters["confirmation_window"]),
        )

    @property
    def detector_method(self) -> str:
        return self.profile.detector_method

    @property
    def validated_summary(self) -> str:
        return f"{self.profile.display_name} · {self.detector_method} · Pfa/CUT {self.pfa:g}"

    def process(
        self,
        samples: object,
        *,
        sample_rate_hz: float,
        center_frequency_hz: float,
        frame_index: int,
    ) -> RuntimeFrameResult:
        spectrum = self.processor.process(
            samples,
            sample_rate_hz=sample_rate_hz,
            center_frequency_hz=center_frequency_hz,
        )
        detection = self.detection.process(spectrum, frame_index=frame_index)
        return RuntimeFrameResult(spectrum=spectrum, detection=detection)


def _validate_override(block: BlockInstance, name: str, value: Any) -> None:
    envelope = block.validated_parameter_envelope.get(name)
    if envelope is None or value not in envelope:
        raise ProfileError(
            "parameter_outside_validated_envelope",
            f"{block.block_id}.{name} is outside the validated parameter envelope",
        )


def load_profile(path: Path = DEFAULT_PROFILE_PATH) -> ProcessingProfile:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProfileError("profile_unreadable", "processing profile cannot be read") from exc
    return profile_from_document(document)


def profile_from_document(document: dict[str, Any]) -> ProcessingProfile:
    expected_keys = ["schema_version", "profile_id", "profile_version", "lifecycle", "blocks", "connections"]
    if list(document) != expected_keys:
        raise ProfileError("profile_key_order", "profile keys are missing, extra, or out of canonical order")
    if document["schema_version"] != 1:
        raise ProfileError("unsupported_profile_schema", "profile schema_version must be one")
    profile_id = document["profile_id"]
    if not isinstance(profile_id, str) or not BLOCK_ID_PATTERN.fullmatch(profile_id):
        raise ProfileError("invalid_profile_id", "profile_id has an invalid format")
    profile_version = document["profile_version"]
    if not isinstance(profile_version, int) or isinstance(profile_version, bool) or profile_version <= 0:
        raise ProfileError("invalid_profile_version", "profile_version must be a positive integer")
    lifecycle = document["lifecycle"]
    if lifecycle not in {"experimental", "validated"}:
        raise ProfileError("invalid_lifecycle", "profile lifecycle must be experimental or validated")

    raw_blocks = document["blocks"]
    if not isinstance(raw_blocks, list):
        raise ProfileError("invalid_blocks", "blocks must be a list")
    blocks: list[BlockInstance] = []
    for raw in raw_blocks:
        if not isinstance(raw, dict) or list(raw) != [
            "id",
            "type",
            "version",
            "parameters",
            "validated_parameter_envelope",
        ]:
            raise ProfileError("invalid_block_shape", "block fields violate the canonical schema")
        block_id = raw["id"]
        if not isinstance(block_id, str) or not BLOCK_ID_PATTERN.fullmatch(block_id):
            raise ProfileError("invalid_block_id", "block id has an invalid format")
        definition = BLOCK_DEFINITIONS.get((raw["type"], raw["version"]))
        if definition is None:
            raise ProfileError("block_not_allowlisted", f"block is not allowlisted: {raw['type']}")
        parameters = raw["parameters"]
        envelope = raw["validated_parameter_envelope"]
        if not isinstance(parameters, dict) or not isinstance(envelope, dict):
            raise ProfileError("invalid_parameters", "block parameters and envelope must be objects")
        if set(parameters) != definition.required_parameters or not set(parameters) <= definition.allowed_parameters:
            raise ProfileError("invalid_parameter_schema", f"invalid parameters for {block_id}")
        if not set(envelope) <= set(parameters):
            raise ProfileError("invalid_parameter_envelope", f"invalid parameter envelope for {block_id}")
        converted_envelope: dict[str, tuple[Any, ...]] = {}
        for name, values in envelope.items():
            if not isinstance(values, list) or not values or parameters[name] not in values:
                raise ProfileError("invalid_parameter_envelope", f"invalid envelope for {block_id}.{name}")
            converted_envelope[name] = tuple(values)
        blocks.append(
            BlockInstance(
                block_id=block_id,
                type_id=definition.type_id,
                version=definition.version,
                parameters=dict(parameters),
                validated_parameter_envelope=converted_envelope,
            )
        )
    if [block.block_id for block in blocks] != sorted(block.block_id for block in blocks):
        raise ProfileError("block_order", "blocks must be sorted by id")
    if len({block.block_id for block in blocks}) != len(blocks):
        raise ProfileError("duplicate_block_id", "block ids must be unique")

    raw_connections = document["connections"]
    if not isinstance(raw_connections, list):
        raise ProfileError("invalid_connections", "connections must be a list")
    connections: list[Connection] = []
    for raw in raw_connections:
        if not isinstance(raw, dict) or list(raw) != ["source_block", "source_port", "target_block", "target_port"]:
            raise ProfileError("invalid_connection_shape", "connection fields violate the canonical schema")
        connections.append(Connection(**raw))
    if [item.key for item in connections] != sorted(item.key for item in connections):
        raise ProfileError("connection_order", "connections must be in canonical order")

    profile = ProcessingProfile(
        schema_version=1,
        profile_id=profile_id,
        profile_version=profile_version,
        lifecycle=lifecycle,
        blocks=tuple(blocks),
        connections=tuple(connections),
    )
    _validate_graph(profile)
    return profile


def _validate_graph(profile: ProcessingProfile) -> None:
    by_id = {block.block_id: block for block in profile.blocks}
    incoming: set[tuple[str, str]] = set()
    for connection in profile.connections:
        source = by_id.get(connection.source_block)
        target = by_id.get(connection.target_block)
        if source is None or target is None:
            raise ProfileError("connection_block_missing", "connection refers to a missing block")
        source_definition = BLOCK_DEFINITIONS[(source.type_id, source.version)]
        target_definition = BLOCK_DEFINITIONS[(target.type_id, target.version)]
        source_type = next(
            (port.data_type for port in source_definition.outputs if port.name == connection.source_port),
            None,
        )
        target_type = next(
            (port.data_type for port in target_definition.inputs if port.name == connection.target_port),
            None,
        )
        if source_type is None or target_type is None:
            raise ProfileError("unknown_port", "connection refers to an unknown port")
        if source_type != target_type:
            raise ProfileError("port_type_mismatch", "connection port data types do not match")
        target_key = (connection.target_block, connection.target_port)
        if target_key in incoming:
            raise ProfileError("duplicate_input_connection", "an input port has more than one connection")
        incoming.add(target_key)

    for block in profile.blocks:
        definition = BLOCK_DEFINITIONS[(block.type_id, block.version)]
        for port in definition.inputs:
            if (block.block_id, port.name) not in incoming:
                raise ProfileError("unconnected_input", f"required input is unconnected: {block.block_id}.{port.name}")
    required_types = {
        "source.sigmf-recorded",
        "dsp.phase02-spectrum",
        "detection.group-regions",
        "detection.temporal-m-of-n",
        "sink.operator-console",
    }
    present = {block.type_id for block in profile.blocks}
    if not required_types <= present:
        raise ProfileError("pipeline_block_missing", "profile lacks a required operation block")
    _ = profile.detector_block


def build_operation_profile(
    detector_method: str,
    *,
    lifecycle: Lifecycle = "validated",
) -> ProcessingProfile:
    detector_type = {
        "regional": "detector.regional",
        "ca_cfar": "detector.ca-cfar",
        "os_cfar": "detector.os-cfar",
        "os_regional_cap": "detector.os-regional-cap",
    }.get(detector_method)
    if detector_type is None:
        raise ProfileError("unsupported_detector", "unknown detector method")
    detector_parameters: dict[str, Any] = {"pfa": 0.0001, "evaluate_center": True}
    if detector_method in {"ca_cfar", "os_cfar", "os_regional_cap"}:
        detector_parameters.update({"training_cells_per_side": 16, "guard_cells_per_side": 4})
    if detector_method in {"os_cfar", "os_regional_cap"}:
        detector_parameters["rank"] = 24
    if detector_method in {"regional", "os_regional_cap"}:
        detector_parameters["region_size"] = 256

    document = {
        "schema_version": 1,
        "profile_id": "phase03-operation-default",
        "profile_version": 1,
        "lifecycle": lifecycle,
        "blocks": [
            {
                "id": "detector",
                "type": detector_type,
                "version": 1,
                "parameters": detector_parameters,
                "validated_parameter_envelope": {
                    "pfa": [0.001, 0.0001, 0.00001],
                    "evaluate_center": [True, False],
                },
            },
            {
                "id": "grouping",
                "type": "detection.group-regions",
                "version": 1,
                "parameters": {"max_gap_bins": 1},
                "validated_parameter_envelope": {},
            },
            {
                "id": "sink",
                "type": "sink.operator-console",
                "version": 1,
                "parameters": {"max_visible_events": 12, "max_waterfall_rows": 128},
                "validated_parameter_envelope": {},
            },
            {
                "id": "source",
                "type": "source.sigmf-recorded",
                "version": 1,
                "parameters": {"frame_length": 4096},
                "validated_parameter_envelope": {},
            },
            {
                "id": "spectrum",
                "type": "dsp.phase02-spectrum",
                "version": 1,
                "parameters": {"frame_length": 4096, "remove_dc": False},
                "validated_parameter_envelope": {"remove_dc": [False, True]},
            },
            {
                "id": "temporal",
                "type": "detection.temporal-m-of-n",
                "version": 1,
                "parameters": {
                    "confirmations_required": 2,
                    "confirmation_window": 3,
                    "association_tolerance_bins": 2,
                    "max_active_tracks": 64,
                    "max_ended_history": 128,
                },
                "validated_parameter_envelope": {},
            },
        ],
        "connections": [
            {
                "source_block": "detector",
                "source_port": "cells",
                "target_block": "grouping",
                "target_port": "cells",
            },
            {
                "source_block": "grouping",
                "source_port": "regions",
                "target_block": "temporal",
                "target_port": "regions",
            },
            {
                "source_block": "source",
                "source_port": "frame",
                "target_block": "spectrum",
                "target_port": "frame",
            },
            {
                "source_block": "spectrum",
                "source_port": "spectrum",
                "target_block": "detector",
                "target_port": "spectrum",
            },
            {
                "source_block": "spectrum",
                "source_port": "spectrum",
                "target_block": "sink",
                "target_port": "spectrum",
            },
            {
                "source_block": "temporal",
                "source_port": "events",
                "target_block": "sink",
                "target_port": "events",
            },
        ],
    }
    document["blocks"] = sorted(document["blocks"], key=lambda item: item["id"])
    document["connections"] = sorted(
        document["connections"],
        key=lambda item: (
            item["source_block"],
            item["source_port"],
            item["target_block"],
            item["target_port"],
        ),
    )
    return profile_from_document(document)


def profile_to_document(profile: ProcessingProfile) -> dict[str, Any]:
    return {
        "schema_version": profile.schema_version,
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
        "lifecycle": profile.lifecycle,
        "blocks": [
            {
                "id": block.block_id,
                "type": block.type_id,
                "version": block.version,
                "parameters": block.parameters,
                "validated_parameter_envelope": {
                    name: list(values) for name, values in block.validated_parameter_envelope.items()
                },
            }
            for block in profile.blocks
        ],
        "connections": [
            {
                "source_block": item.source_block,
                "source_port": item.source_port,
                "target_block": item.target_block,
                "target_port": item.target_port,
            }
            for item in profile.connections
        ],
    }


def canonical_profile_bytes(profile: ProcessingProfile) -> bytes:
    document = profile_to_document(profile)
    text = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    return text.encode("utf-8")
