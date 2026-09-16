#!/usr/bin/env python3
"""Linux loopback integration for the P0 TCP-to-local-service bridge."""

from __future__ import annotations

import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib


IQ_PREFIX = struct.Struct("<4sBBHIIHHQIIII")
RESPONSE_HEADER = struct.Struct("<4sBBHIIII")
FRAME_COUNT = 4
PAYLOAD_BYTES = 8192
LOCAL_REQUEST_BYTES = 8224


def iq_packet(sequence: int, frame_id: int) -> bytes:
    payload = bytes(((index * 17 + frame_id) & 0xFF) for index in range(PAYLOAD_BYTES))
    prefix = IQ_PREFIX.pack(
        b"P0IQ",
        2,
        1,
        48,
        sequence,
        frame_id,
        0,
        1,
        101_500_000,
        10_000_000,
        4096,
        PAYLOAD_BYTES,
        zlib.crc32(payload) & 0xFFFFFFFF,
    )
    return prefix + struct.pack("<I", zlib.crc32(prefix) & 0xFFFFFFFF) + payload


def local_error_response(frame_id: int) -> bytes:
    header = bytearray(48)
    struct.pack_into("<IHHIIII", header, 0, 0x31534550, 3, 48, 48, frame_id, 1, 0)
    struct.pack_into("<I", header, 44, zlib.crc32(header[:44]) & 0xFFFFFFFF)
    return bytes(header)


def read_exact(connection: socket.socket, byte_count: int) -> bytes:
    result = bytearray()
    while len(result) < byte_count:
        block = connection.recv(byte_count - len(result))
        if not block:
            raise RuntimeError("TCP yanıtı erken kapandı.")
        result.extend(block)
    return bytes(result)


def fake_local_service(socket_path: Path, ready: threading.Event, result: dict[str, object]) -> None:
    server = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        server.bind(str(socket_path))
        server.listen(1)
        ready.set()
        connection, _ = server.accept()
        with connection:
            requests = [connection.recv(LOCAL_REQUEST_BYTES + 1) for _ in range(FRAME_COUNT)]
            result["request_lengths"] = [len(item) for item in requests]
            result["frame_ids"] = [struct.unpack_from("<I", item, 12)[0] for item in requests]
            result["flags"] = [struct.unpack_from("<I", item, 20)[0] for item in requests]
            for frame_id in result["frame_ids"]:
                connection.send(local_error_response(int(frame_id)))
    except Exception as exc:
        result["error"] = repr(exc)
        ready.set()
    finally:
        server.close()


def main() -> int:
    if len(sys.argv) != 3:
        print("Kullanım: p0_iq_bridge_loopback_test.py KOPRU_IKILISI PORT", file=sys.stderr)
        return 2
    bridge_path = Path(sys.argv[1])
    port = int(sys.argv[2])
    with tempfile.TemporaryDirectory(prefix="p0-iq-bridge-") as raw:
        local_socket = Path(raw) / "p0-ed.sock"
        ready = threading.Event()
        service_result: dict[str, object] = {}
        service = threading.Thread(
            target=fake_local_service,
            args=(local_socket, ready, service_result),
            daemon=True,
        )
        service.start()
        if not ready.wait(2.0) or "error" in service_result:
            raise RuntimeError(f"Sahte yerel hizmet başlamadı: {service_result}")
        bridge = subprocess.Popen(
            [str(bridge_path), "127.0.0.1", "127.0.0.1", str(port), str(local_socket)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.monotonic() + 2.0
            client: socket.socket | None = None
            while time.monotonic() < deadline:
                try:
                    client = socket.create_connection(("127.0.0.1", port), timeout=0.2)
                    break
                except OSError:
                    time.sleep(0.02)
            if client is None:
                raise RuntimeError("TCP ağ köprüsüne bağlanılamadı.")
            with client:
                client.settimeout(3.0)
                client.sendall(b"".join(iq_packet(index, 100 + index) for index in range(FRAME_COUNT)))
                received: list[tuple[int, int]] = []
                for _ in range(FRAME_COUNT):
                    header = read_exact(client, RESPONSE_HEADER.size)
                    magic, version, kind, header_bytes, sequence, payload_bytes, payload_crc, header_crc = RESPONSE_HEADER.unpack(header)
                    if (
                        magic != b"P0RS"
                        or version != 2
                        or kind != 1
                        or header_bytes != RESPONSE_HEADER.size
                        or zlib.crc32(header[:20]) & 0xFFFFFFFF != header_crc
                    ):
                        raise RuntimeError("Ağ köprüsü yanıt başlığı geçersiz.")
                    payload = read_exact(client, payload_bytes)
                    if zlib.crc32(payload) & 0xFFFFFFFF != payload_crc:
                        raise RuntimeError("Ağ köprüsü yanıt payload CRC değeri geçersiz.")
                    received.append((sequence, struct.unpack_from("<I", payload, 12)[0]))
            service.join(timeout=2.0)
            expected = [(index, 100 + index) for index in range(FRAME_COUNT)]
            if received != expected:
                raise RuntimeError(f"Yanıt sırası eşleşmedi: {received}")
            if service_result.get("request_lengths") != [LOCAL_REQUEST_BYTES] * FRAME_COUNT:
                raise RuntimeError(f"Yerel istek uzunluğu eşleşmedi: {service_result}")
            if service_result.get("frame_ids") != [100, 101, 102, 103]:
                raise RuntimeError(f"Yerel frame kimliği eşleşmedi: {service_result}")
            if service_result.get("flags") != [1, 0, 0, 0]:
                raise RuntimeError(f"Temporal reset sınırı eşleşmedi: {service_result}")
            if "error" in service_result:
                raise RuntimeError(str(service_result["error"]))
        finally:
            bridge.terminate()
            try:
                bridge.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                bridge.kill()
                bridge.wait(timeout=2.0)
            if bridge.returncode not in {0, -15}:
                stdout, stderr = bridge.communicate()
                raise RuntimeError(f"Ağ köprüsü başarısız: {stdout}\n{stderr}")
    print("P0_IQ_BRIDGE_LOOPBACK_TEST=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
