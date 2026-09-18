"""Yerel Linux protokol ve TCP taşıma regresyonu; kart üzerinde çalışmaz."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
common = ['gcc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
    '-Iplatforms/embedded/p0/include', '-Iplatforms/embedded/phase06i/include',
    '-Iplatforms/embedded/phase06j/include']
with tempfile.TemporaryDirectory() as raw:
    directory = Path(raw)
    bridge = directory / 'bridge'
    protocol = directory / 'protocol'
    subprocess.run([*common, '-include', 'output/parameter-fix-20260916/loopback_account.h',
        *[f'platforms/embedded/p0/src/{name}.c' for name in
          ('p0_ed_network_bridge','p0_ed_service_protocol','p0_iq_transport')],
        '-o', str(bridge)], cwd=root, check=True)
    subprocess.run([*common, 'platforms/embedded/p0/src/p0_iq_transport.c',
        'tests/p0/p0_iq_transport_test.c', '-o', str(protocol)], cwd=root, check=True)
    outputs = []
    for args in ([str(protocol)], [sys.executable,'tests/p0/p0_parameter_bridge_loopback_test.py',str(bridge)],
                 [sys.executable,'tests/p0/p0_iq_bridge_loopback_test.py',str(bridge),'47739']):
        value = subprocess.run(args, cwd=root, check=True, capture_output=True, text=True)
        outputs.append(value.stdout.strip())
report = dict(status='passed', physical_execution=False, results=outputs)
with (root/'output/parameter-fix-20260916/transport.json').open('x') as stream:
    json.dump(report,stream,indent=2)
print(json.dumps(report))
