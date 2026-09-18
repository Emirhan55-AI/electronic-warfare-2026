"""Read the connected ZedBoard identity from the pinned COM6 console."""

from __future__ import annotations

import os
import re
import time

import serial


USERNAME = "petalinux"
PASSWORD = os.environ["TEKNO_BOARD_SETUP_PASSWORD"]
COMMAND = (
    "printf '__CODEX_%s__\\n' 'BOARD_BEGIN'; "
    "uname -m; "
    "tr -d '\\000' </proc/device-tree/model; printf '\\n'; "
    "cat /sys/class/fpga_manager/fpga0/state; "
    "ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256; "
    "cat /etc/ssh/ssh_host_ed25519_key.pub; "
    "sha256sum /usr/sbin/p0-ed-service /usr/sbin/p0-ed-network-bridge; "
    "printf '__CODEX_%s__\\n' 'BOARD_END'"
)


def read_until(connection: serial.Serial, patterns: tuple[str, ...], timeout: float) -> str:
    deadline = time.monotonic() + timeout
    output = ""
    while time.monotonic() < deadline:
        output += connection.read(4096).decode(errors="replace")
        if any(pattern in output for pattern in patterns):
            return output
        time.sleep(0.05)
    return output


with serial.Serial("COM6", 115200, timeout=0.2) as connection:
    connection.reset_input_buffer()
    connection.write(b"\r")
    initial = read_until(connection, ("login:", "$ ", "# "), 2.0)
    if "login:" in initial:
        connection.write(USERNAME.encode() + b"\r")
        prompt = read_until(connection, ("Password:", "password:"), 2.0)
        if "assword:" not in prompt:
            raise SystemExit("Seri konsolda parola istemi görülmedi.")
        connection.write(PASSWORD.encode() + b"\r")
        shell = read_until(connection, ("$ ", "# "), 3.0)
        if "$ " not in shell and "# " not in shell:
            raise SystemExit(
                "Seri konsol oturumu açılamadı: "
                + shell.replace(PASSWORD, "[REDACTED]").strip()
            )
    elif "$ " not in initial and "# " not in initial:
        raise SystemExit(
            "Seri konsol hazır kabuk veya giriş isteminde değil: "
            + initial.replace(PASSWORD, "[REDACTED]").strip()
        )

    connection.write(COMMAND.encode() + b"\r")
    output = read_until(connection, ("__CODEX_BOARD_END__",), 5.0)

match = re.search(
    r"__CODEX_BOARD_BEGIN__\s*(.*?)\s*__CODEX_BOARD_END__",
    output,
    flags=re.DOTALL,
)
if match is None:
    raise SystemExit("Kart kimlik çıktısı tamamlanmadı.")
print(match.group(1).replace(PASSWORD, "[REDACTED]").strip())
