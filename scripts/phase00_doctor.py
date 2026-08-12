#!/usr/bin/env python3
"""Record a read-only PHASE-00 development toolchain inventory."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "evidence" / "phase00" / "toolchain.json"


def _first_line(value: str) -> str | None:
    for line in value.splitlines():
        clean = line.strip()
        if clean:
            return clean
    return None


def executable_tool(
    name: str,
    candidates: Iterable[str],
    version_arguments: Iterable[str] = ("--version",),
    run_version: bool = True,
) -> dict[str, object]:
    """Locate an executable without installing software or touching hardware."""
    candidate_list = list(candidates)
    try:
        found = [(candidate, shutil.which(candidate)) for candidate in candidate_list]
    except OSError as exc:
        return {
            "name": name,
            "status": "unknown",
            "version": None,
            "evidence": f"PATH inspection failed: {type(exc).__name__}: {exc}",
        }

    matches = [(candidate, path) for candidate, path in found if path]
    if not matches:
        return {
            "name": name,
            "status": "unavailable",
            "version": None,
            "evidence": "no executable found in PATH: " + ", ".join(candidate_list),
        }

    candidate, path = matches[0]
    version = None
    note = ""
    if run_version:
        try:
            completed = subprocess.run(
                [path, *version_arguments],
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
            version = _first_line(completed.stdout) or _first_line(completed.stderr)
            if completed.returncode != 0:
                note = f"; version probe exited {completed.returncode}"
        except (OSError, subprocess.SubprocessError) as exc:
            note = f"; version unavailable: {type(exc).__name__}: {exc}"

    alternatives = ", ".join(item for item, _ in matches[1:])
    if alternatives:
        note += f"; also found: {alternatives}"
    return {
        "name": name,
        "status": "available",
        "version": version,
        "evidence": f"executable: {Path(path).resolve()} ({candidate}){note}",
    }


def python_package(name: str, module: str, distributions: Iterable[str]) -> dict[str, object]:
    """Inspect package metadata without importing third-party code."""
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, AttributeError, ValueError) as exc:
        return {
            "name": name,
            "status": "unknown",
            "version": None,
            "evidence": f"module inspection failed: {type(exc).__name__}: {exc}",
        }

    if spec is None:
        return {
            "name": name,
            "status": "unavailable",
            "version": None,
            "evidence": f"python module not found: {module}",
        }

    version = None
    for distribution in distributions:
        try:
            version = importlib.metadata.version(distribution)
            break
        except importlib.metadata.PackageNotFoundError:
            continue
    origin = spec.origin or "namespace/built-in module"
    return {
        "name": name,
        "status": "available",
        "version": version,
        "evidence": f"python-module: {module}; origin: {origin}",
    }


def collect_inventory() -> list[dict[str, object]]:
    return [
        executable_tool("Git", ["git"]),
        {
            "name": "Python",
            "status": "available",
            "version": sys.version.split()[0],
            "evidence": f"executable: {Path(sys.executable).resolve()} (current interpreter)",
        },
        python_package("NumPy", "numpy", ["numpy"]),
        python_package("SciPy", "scipy", ["scipy"]),
        python_package("pytest", "pytest", ["pytest"]),
        executable_tool("CMake", ["cmake"]),
        executable_tool("Ninja", ["ninja"]),
        executable_tool(
            "C/C++ compiler",
            ["cc", "c++", "gcc", "g++", "clang", "clang++", "clang-cl", "cl"],
        ),
        executable_tool("Qt", ["qmake6", "qmake", "qtpaths6", "qtpaths"]),
        executable_tool("GHDL", ["ghdl"]),
        python_package("VUnit", "vunit", ["vunit_hdl", "vunit"]),
        executable_tool("Verilator", ["verilator"]),
        executable_tool("Icarus Verilog", ["iverilog"], ["-V"]),
        executable_tool("Vivado", ["vivado"], ["-version"]),
        executable_tool("XSim", ["xsim"]),
        executable_tool(
            "HackRF command-line tools",
            ["hackrf_info", "hackrf_transfer", "hackrf_sweep"],
            run_version=False,
        ),
    ]


def main() -> int:
    payload = {
        "schema_version": 1,
        "phase": "PHASE-00",
        "tools": collect_inventory(),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    available = sum(tool["status"] == "available" for tool in payload["tools"])
    unavailable = sum(tool["status"] == "unavailable" for tool in payload["tools"])
    unknown = sum(tool["status"] == "unknown" for tool in payload["tools"])
    print(f"Toolchain inventory written to {OUTPUT}")
    print(f"available={available} unavailable={unavailable} unknown={unknown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
