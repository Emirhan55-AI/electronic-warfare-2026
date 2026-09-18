"""Deploy the verified P0PM-v4 services to volatile ZedBoard runtime."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build" / "parameter-deploy-python"))

import paramiko


HOST = "192.168.7.2"
USERNAME = "petalinux"
PASSWORD = os.environ["TEKNO_BOARD_SETUP_PASSWORD"]
KNOWN_HOSTS = ROOT / "tmp" / "zedboard-current-known-hosts"
PRODUCTS = ROOT / "build" / "p0" / "p0pm-v4-direction-20260916" / "software"
REMOTE_STAGE = "/tmp/p0pm-v4-direction-20260916"
BACKUP = "/var/backups/p0pm-v4-direction-20260916-live-recovery"
SERVICE_HASH = "4deca35b208a9e9a50f6132ad89a40658819b800a0be218b90543ad0c7443f19"
BRIDGE_HASH = "4797d7c300fb38e09869984b13bece5618f7ebcb34b459a4df5d96c601bb6bc1"
OLD_SERVICE_HASH = "20c151ea1291c0653432573595a7f3f20a08720a8330472642bd1d843f6822d7"
OLD_BRIDGE_HASH = "beb168b6a87188c82f63d5b5310240bd83fe89ddfea2dbe84943199253493d0c"


def run(client: paramiko.SSHClient, command: str, *, sudo: bool = False) -> str:
    actual = command
    if sudo:
        actual = "sudo -S -p '' sh -c " + shlex.quote(command)
    stdin, stdout, stderr = client.exec_command(actual, timeout=45)
    if sudo:
        stdin.write(PASSWORD + "\n")
        stdin.flush()
    stdin.channel.shutdown_write()
    output = stdout.read().decode(errors="replace")
    errors = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    safe_output = output.replace(PASSWORD, "[REDACTED]")
    safe_errors = errors.replace(PASSWORD, "[REDACTED]")
    if safe_output:
        print(safe_output, end="", flush=True)
    if safe_errors:
        print(safe_errors, end="", file=sys.stderr, flush=True)
    if code:
        raise RuntimeError(f"Kart komutu başarısız oldu ({code}).")
    return output


client = paramiko.SSHClient()
client.load_host_keys(str(KNOWN_HOSTS))
client.set_missing_host_key_policy(paramiko.RejectPolicy())
client.connect(
    HOST,
    username=USERNAME,
    password=PASSWORD,
    timeout=8,
    allow_agent=False,
    look_for_keys=False,
)
try:
    run(
        client,
        "set -eu; "
        "test \"$(uname -m)\" = armv7l; "
        "test \"$(tr -d '\\000' </proc/device-tree/model)\" = 'Zynq Zed Development Board'; "
        "test \"$(cat /sys/class/fpga_manager/fpga0/state)\" = operating; "
        f"printf '%s\\n' '{OLD_SERVICE_HASH}  /usr/sbin/p0-ed-service' "
        f"'{OLD_BRIDGE_HASH}  /usr/sbin/p0-ed-network-bridge' | sha256sum -c -",
    )
    run(client, f"umask 077; mkdir -p {REMOTE_STAGE}; chmod 700 {REMOTE_STAGE}")
    with client.open_sftp() as transfer:
        transfer.put(str(PRODUCTS / "p0-ed-service"), f"{REMOTE_STAGE}/p0-ed-service")
        transfer.put(str(PRODUCTS / "p0-ed-network-bridge"), f"{REMOTE_STAGE}/p0-ed-network-bridge")
    run(
        client,
        f"printf '%s\\n' '{SERVICE_HASH}  {REMOTE_STAGE}/p0-ed-service' "
        f"'{BRIDGE_HASH}  {REMOTE_STAGE}/p0-ed-network-bridge' | sha256sum -c -",
    )
    run(
        client,
        "set -eu; "
        f"if [ ! -e {BACKUP} ]; then mkdir -m 700 {BACKUP}; "
        f"cp -p /usr/sbin/p0-ed-service /usr/sbin/p0-ed-network-bridge {BACKUP}/; fi; "
        f"printf '%s\\n' '{OLD_SERVICE_HASH}  {BACKUP}/p0-ed-service' "
        f"'{OLD_BRIDGE_HASH}  {BACKUP}/p0-ed-network-bridge' | sha256sum -c -",
        sudo=True,
    )
    run(
        client,
        "set -eu; "
        f"backup={BACKUP}; stage={REMOTE_STAGE}; "
        "rollback() { /etc/init.d/p0-ed-service stop || true; "
        "cp -p \"$backup/p0-ed-service\" \"$backup/p0-ed-network-bridge\" /usr/sbin/; "
        "chmod 755 /usr/sbin/p0-ed-service /usr/sbin/p0-ed-network-bridge; "
        "/etc/init.d/p0-ed-service start; }; "
        "trap 'rollback' EXIT; "
        "/etc/init.d/p0-ed-service stop; "
        "cp \"$stage/p0-ed-service\" /usr/sbin/p0-ed-service; "
        "cp \"$stage/p0-ed-network-bridge\" /usr/sbin/p0-ed-network-bridge; "
        "chmod 755 /usr/sbin/p0-ed-service /usr/sbin/p0-ed-network-bridge; "
        "/etc/init.d/p0-ed-service start; sleep 1; "
        "kill -0 $(cat /run/p0-ed-service.pid); "
        "kill -0 $(cat /run/p0-ed-network-bridge.pid); "
        f"printf '%s\\n' '{SERVICE_HASH}  /usr/sbin/p0-ed-service' "
        f"'{BRIDGE_HASH}  /usr/sbin/p0-ed-network-bridge' | sha256sum -c -; "
        "test -S /run/p0-ed/p0-ed.sock; trap - EXIT",
        sudo=True,
    )
    run(
        client,
        "printf 'service_pid='; cat /run/p0-ed-service.pid; "
        "printf 'bridge_pid='; cat /run/p0-ed-network-bridge.pid",
    )
finally:
    client.close()
