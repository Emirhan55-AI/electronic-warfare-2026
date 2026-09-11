"""Exercise Python -> TCP bridge -> daemon -> simulated DMA configuration."""
from pathlib import Path
import json
import os
import pwd
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import importlib.util
import struct
import zlib
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

control = load_module('control_wire', 'algorithms/p0/detection_config.py')
transport_module = load_module('iq_wire', 'algorithms/p0/transport.py')
DetectionProfile, DetectionConfigError = control.DetectionProfile, control.DetectionConfigError
exchange_profile, encode_request = control.exchange_profile, control.encode_request
IQFrame, TCPClientIQTransport = transport_module.IQFrame, transport_module.TCPClientIQTransport
from scripts.verify_p0_ed_service_linux import _compile, P0, P06J


def verify():
    if os.name != 'posix' or os.geteuid() != 0:
        raise RuntimeError('Root Linux test ortamı gerekli.')
    with tempfile.TemporaryDirectory(prefix='st06-control-') as raw:
        directory = Path(raw)
        directory.chmod(0o755)
        nobody = pwd.getpwnam('nobody')
        run_dir = directory/'run'
        run_dir.mkdir(mode=0o750)
        os.chown(run_dir, nobody.pw_uid, nobody.pw_gid)
        service, bridge = directory/'service', directory/'bridge'
        compiler = shutil.which('gcc')
        sources = ['p0_parameter_runtime', 'p0_ed_pipeline', 'p0_ed_service_protocol',
                   'p0_ed_service', 'p0_os_cfar', 'p0_pl_os_cfar', 'p0_multiscale_detector',
                   'p0_candidate_packet', 'p0_persistent_weak', 'p0_st05_wideband', 'p0_st05_stream']
        _compile(compiler, service, [ROOT/'tests/p0/p0_ed_fake_dma_runtime.c',
                 *(P0/'src'/f'{name}.c' for name in sources), P06J/'src/phase06j_temporal.c'],
                 ['-DP0_ED_SERVICE_ACCOUNT="nobody"', '-DP0_ED_OPERATOR_GROUP="nogroup"', '-lm', '-pthread'])
        _compile(compiler, bridge, [P0/'src'/f'{name}.c' for name in
                 ['p0_ed_network_bridge', 'p0_ed_service_protocol', 'p0_iq_transport']],
                 ['-DP0_NETWORK_SERVICE_ACCOUNT="nobody"'])
        results = []
        for mode in ('unsupported', 'legacy-config', 'runtime-profile'):
            supported = mode != 'unsupported'
            runtime_profile = mode == 'runtime-profile'
            unix = run_dir/(mode + '.sock')
            env = os.environ.copy()
            env.pop('P0_FAKE_CONFIG', None)
            env.pop('P0_FAKE_PROFILE', None)
            if mode == 'legacy-config': env['P0_FAKE_CONFIG'] = '1'
            if runtime_profile: env['P0_FAKE_PROFILE'] = '1'
            daemon = subprocess.Popen([str(service), '/dev/fake', str(unix)], env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            network = None
            try:
                deadline = time.monotonic()+8
                while not unix.exists():
                    if daemon.poll() is not None: raise RuntimeError(daemon.communicate())
                    if time.monotonic()>deadline: raise TimeoutError('daemon')
                    time.sleep(.02)
                with socket.socket() as probe:
                    probe.bind(('127.0.0.1',0)); port=probe.getsockname()[1]
                network = subprocess.Popen([str(bridge),'127.0.0.1','127.0.0.1',str(port),str(unix)],
                                            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                deadline=time.monotonic()+8
                while True:
                    if network.poll() is not None: raise RuntimeError(network.communicate())
                    try:
                        with socket.create_connection(('127.0.0.1',port), timeout=.1): pass
                        break
                    except OSError:
                        if time.monotonic()>deadline: raise
                        time.sleep(.02)
                if not supported:
                    try: exchange_profile('127.0.0.1',port)
                    except DetectionConfigError as exc: assert 'desteklemiyor' in str(exc)
                    else: raise AssertionError('legacy accepted settings')
                    results.append('legacy reports unsupported')
                    continue
                initial=exchange_profile('127.0.0.1',port)
                expected_initial=DetectionProfile(0,36851433755,17098572778,
                                                  4096,runtime_profile)
                assert initial==expected_initial
                if runtime_profile:
                    iq = bytes([16]) * 32768
                    header = struct.pack('<4sHHIIIqQHHII', b'P0PM', 1, 64, 7, 20,
                                         2_000_000, 100_000_000, 11, 2268, 2343, zlib.crc32(iq), 0)
                    header += bytes(12)
                    request = header + struct.pack('<I', zlib.crc32(header)) + iq
                    try:
                        with socket.create_connection(('127.0.0.1', port), timeout=5) as connection:
                            connection.sendall(request)
                            response = bytearray()
                            while len(response) < 176:
                                chunk = connection.recv(176-len(response))
                                assert chunk, 'batch response missing'
                                response.extend(chunk)
                    except (OSError, AssertionError) as exc:
                        detail = []
                        for label, process in (('bridge', network), ('service', daemon)):
                            if process is not None and process.poll() is not None:
                                out, err = process.communicate()
                                detail.append(f'{label} rc={process.returncode} out={out!r} err={err!r}')
                        raise RuntimeError(f'parameter batch connection failed: {exc}; {detail}') from exc
                    assert response[:4] == b'P0PR' and struct.unpack_from('<I', response, 12)[0] == 0
                    assert zlib.crc32(response[:172]) == struct.unpack_from('<I', response, 172)[0]
                    assert struct.unpack_from('<QQIB', response, 16) == (7, 11, 23, 4)
                    assert struct.unpack_from('<I', response, 160)[0] == zlib.crc32(iq)
                    # Fake PL power is deliberately unrelated to constant input IQ.
                    # This fails if the service silently redoes the Hann FFT in ARM.
                    expected_power = 10*math.log10((999900 + 48*9900)/(1536*4096))
                    assert response[88] == 1
                    assert abs(struct.unpack_from('<d', response, 92)[0]-expected_power) < 1e-8
                    bad = bytearray(request); bad[-1] ^= 1
                    with socket.create_connection(('127.0.0.1', port), timeout=5) as connection:
                        connection.sendall(bad)
                        assert connection.recv(176) == b''
                    assert exchange_profile('127.0.0.1', port) == initial
                    results.extend(['parameter batch uses PL power', 'parameter batch input CRC rejected'])
                requested=DetectionProfile(0,2<<32,1<<32,4096,runtime_profile)
                changed=exchange_profile('127.0.0.1',port,profile=requested)
                expected_changed=DetectionProfile(1,2<<32,1<<32,4096,runtime_profile)
                assert changed==exchange_profile('127.0.0.1',port)==expected_changed
                try: exchange_profile('127.0.0.1',port,profile=initial)
                except DetectionConfigError as exc: assert 'yeniden okuyun' in str(exc)
                else: raise AssertionError('stale applied')
                # Corrupt CRC closes only that connection; profile is retained.
                with socket.create_connection(('127.0.0.1',port), timeout=3) as connection:
                    bad=bytearray(encode_request(1,123));bad[-1]^=1
                    connection.sendall(bad)
                    assert connection.recv(48)==b''
                assert exchange_profile('127.0.0.1',port)==changed
                transport=TCPClientIQTransport()
                try:
                    transport.connect('127.0.0.1',port)
                    events=[]
                    for i in range(4):
                        frame=IQFrame(i,2_000_000,100_000_000,bytes([0x55])+bytes(8191),frame_id=i)
                        payload=transport.exchange(frame).payload
                        summary=transport_module.decode_local_ed_response(payload,i)
                        for index in range(summary.active_count):
                            offset=68+index*68
                            events.append((struct.unpack_from('<H',payload,offset+32)[0],
                                           payload[offset+24],payload[offset+36],
                                           struct.unpack_from('<Q',payload,offset+56)[0]/(1<<30)))
                    matches=[e for e in events if e[0]==2600]
                    assert matches and any(e[1]==2 for e in matches)
                    assert all(e[2]==3 and abs(e[3]-200)<1e-6 for e in matches), matches
                finally: transport.close()
                restored=exchange_profile('127.0.0.1',port,profile=DetectionProfile(
                    1,36851433755,17098572778,4096,runtime_profile))
                assert restored.generation==2
                results.extend([f'{mode} startup', f'{mode} apply and readback',
                                f'{mode} stale rejected', f'{mode} CRC rejected',
                                f'{mode} custom threshold in real ARM event',
                                f'{mode} restore defaults'])
            finally:
                for process in (network,daemon):
                    if process is not None:
                        process.terminate()
                        try: process.communicate(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill(); process.communicate()
        return {'status':'passed','cases':results,'physical_fpga':False,
                'scope':'actual service/bridge/ARM pipeline with simulated DMA'}


if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
