"""Linux TCP → SOCK_SEQPACKET P0PM-v1/v2/v3/v4 tam paket bütünlüğü."""
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


def run(bridge_path, version):
    count = 16 if version == 3 else 4
    payload = bytes((i % 256 for i in range(count * 8192)))
    header = bytearray(64)
    struct.pack_into('<4sHHIIIqQHHI', header, 0, b'P0PM', version, 64, 7, 8,
                     2000000, 820000000, 17, 2000, 2100, zlib.crc32(payload))
    struct.pack_into('<I', header, 60, zlib.crc32(header[:60]))
    packet = bytes(header) + payload
    response = bytearray(176)
    struct.pack_into('<4sHHII', response, 0, b'P0PR', version if version in (3, 4) else 2, 176, 7, 1)
    struct.pack_into('<I', response, 172, zlib.crc32(response[:172]))
    errors = []
    with tempfile.TemporaryDirectory(prefix='parameter-bridge-') as raw:
        local_path = str(Path(raw) / 'service.sock')
        server = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        server.bind(local_path); server.listen(1); server.settimeout(10)
        def serve():
            try:
                connection, _ = server.accept()
                with connection:
                    connection.settimeout(10)
                    received = connection.recv(len(packet) + 1)
                    assert received == packet
                    connection.sendall(response)
            except BaseException as exc:
                errors.append(repr(exc))
        worker = threading.Thread(target=serve)
        worker.start()
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1',0)); port = reservation.getsockname()[1]
        bridge = subprocess.Popen([str(bridge_path), '127.0.0.1', '127.0.0.1', str(port), local_path],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while True:
                try:
                    client = socket.create_connection(('127.0.0.1',port),timeout=.5)
                    break
                except OSError:
                    if time.monotonic() > deadline: raise
                    time.sleep(.02)
            with client:
                client.settimeout(10)
                # Parçalı TCP girdisi; yerel paket tek ve eksiksiz kalmalıdır.
                for i in range(0,len(packet),997): client.sendall(packet[i:i+997])
                received = bytearray()
                while len(received) < 176:
                    chunk = client.recv(176-len(received))
                    if not chunk: raise AssertionError('Yanıt kesildi')
                    received.extend(chunk)
                assert received == response
        finally:
            bridge.terminate()
            try: bridge.wait(timeout=3)
            except subprocess.TimeoutExpired: bridge.kill(); bridge.wait(timeout=3)
            server.close(); worker.join(timeout=11)
        assert not errors, errors


if __name__ == '__main__':
    for version in (1,2,3,4): run(Path(sys.argv[1]).resolve(), version)
    print('P0_PARAMETER_BRIDGE_LOOPBACK_TEST=PASS')
