"""Package the Windows operator application using the release asset manifest."""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "app/operator_console/pysidedeploy.spec"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist/operator-console-20260918")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    evidence_dir = ROOT / "build/app-package-20260918"
    work = evidence_dir / "pyinstaller"
    work.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "config/app/product-package.json").read_text(encoding="utf-8"))
    source_paths = {ROOT / "baz_operator_console.py", SPEC, ROOT / "config/app/product-package.json"}
    for source_root in manifest["allowed_source_roots"]:
        source_paths.update((ROOT / source_root).rglob("*.py"))
    inputs = {path.relative_to(ROOT).as_posix(): sha256(path) for path in sorted(source_paths)}
    (evidence_dir / "source-inputs.json").write_text(
        json.dumps(inputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    spec = configparser.ConfigParser(interpolation=None)
    spec.read(SPEC, encoding="utf-8")
    command = [sys.executable, "-m", "PyInstaller", "--onedir", "--windowed",
               "--contents-directory=.", "--name=BAZ", "--noupx",
               f"--distpath={output}", f"--workpath={work}", f"--specpath={work}",
               f"--icon={SPEC.parent / 'assets/baz-logo.ico'}",
               f"--paths={ROOT}", "--hidden-import=serial.tools.list_ports"]
    excluded = {"pytest", "tkinter", "matplotlib", "pandas", "sklearn", "zmq",
                "PyQt5", "PyQt6", "PySide2", "IPython", "ipykernel", "notebook",
                "jupyter", "jupyter_client", "jupyter_core", "torch", "torchvision",
                "torchaudio", "tensorflow", "cupy", "numba", "black", "jedi", "OpenGL"}
    excluded.update(path.removesuffix(".py").replace("/", ".")
                    for path in manifest["excluded_paths"] if path.endswith(".py"))
    for name in sorted(excluded):
        command.append(f"--exclude-module={name}")
    for option in shlex.split(spec["nuitka"]["extra_args"]):
        if option.startswith("--include-data-files="):
            source, destination = option.removeprefix("--include-data-files=").split("=", 1)
            source_path = (SPEC.parent / source).resolve()
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            flag = "--add-binary" if source_path.suffix.lower() == ".dll" else "--add-data"
            command.append(f"{flag}={source_path}:{Path(destination).parent.as_posix()}")
        elif option.startswith("--include-data-dir="):
            source, destination = option.removeprefix("--include-data-dir=").split("=", 1)
            command.append(f"--add-data={(SPEC.parent / source).resolve()}:{destination}")
    command.append(str(ROOT / "baz_operator_console.py"))
    (evidence_dir / "build-command-pyinstaller.json").write_text(
        json.dumps(command, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    with (evidence_dir / "build-pyinstaller.log").open("w", encoding="utf-8") as log:
        environment = os.environ.copy()
        environment["PATH"] = os.pathsep.join((str(Path(os.environ["WINDIR"]) / "System32"), str(Path(sys.executable).parent)))
        completed = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
    if completed.returncode:
        print(f"EXE paketlemesi başarısız: {evidence_dir / 'build-pyinstaller.log'}")
        return completed.returncode
    if any(sha256(ROOT / path) != digest for path, digest in inputs.items()):
        raise RuntimeError("Paketleme sırasında kaynak değişti; paket yeniden üretilmelidir.")
    package = output / "BAZ"
    # Qt on Windows uses the OS ICU ABI. A third-party ICU has incompatible exports.
    for filename in ("icuuc.dll", "icuin.dll", "icudt.dll"):
        unexpected_icu = package / filename
        if unexpected_icu.is_file():
            unexpected_icu.unlink()
    (package / "BAŞLATMA.txt").write_text(
        "BÂZ — Elektronik Harp Operatör Uygulaması\n\n"
        "BAZ.exe dosyasına çift tıklayarak açın. Ayrıca Python kurulumu gerekmez.\n"
        "Bu klasördeki EXE ve destek dosyalarını birlikte koruyun.\n"
        "Donanım kullanımı için HackRF araçları/USB sürücüsü ve ZedBoard hizmeti gerekir.\n"
        "Uygulamanın açılması alım veya RF yayını başlatmaz.\n",
        encoding="utf-8", newline="\n",
    )
    print(f"EXE paketi hazır: {package / 'BAZ.exe'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
