"""Yeni taşıyıcı hizmetinin kaynak, ikili, protokol ve kayıt kanıt bağını denetle."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.p0.transport import IQCapabilityCodec
from app.operator_console.measurement_record import read_measurement


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    base = ROOT / 'output/parameter-review-20260918'
    build_path = ROOT / 'build/p0/parameter-20260918/software-carrier-v1/build.json'
    build = json.loads(build_path.read_text(encoding='utf-8'))
    assert all(digest(ROOT / path) == expected for path, expected in build['sources'].items())
    assert all(digest(ROOT / item['path']) == item['sha256'] for item in build['binaries'].values())
    reports = {}
    for name in ('carrier-recovery-c-v3.json', 'extended-carrier-regression-v1.json',
                 'board-numeric-carrier-v1.json', 'board-direction-carrier-v1.json',
                 'real-820-carrier-board-v1.json', 'real-new820-carrier-board-v1.json'):
        path = base / name
        report = json.loads(path.read_text(encoding='utf-8'))
        assert report['status'] == 'passed', name
        reports[name] = {'sha256': digest(path), 'status': report['status']}
        sources = report.get('source_sha256', report.get('sources', {}))
        if isinstance(sources, dict):
            assert all(digest(ROOT / path) == expected for path, expected in sources.items()), name
        if name.startswith('real-'):
            record_path = Path(report['record_path'])
            assert digest(record_path) == report['record_sha256']
            assert report['protocol'] == 'P0PM-v5'
            assert report['fields']['carrier_line_frequency']['state'] == 'not_observed'
            field = report['fields']['recovered_carrier_frequency']
            assert field['state'] == 'uncertain' and field['reason'] == 'recovered_carrier_order2'
            reports[name].update(record_sha256=digest(record_path),
                                 conditional_carrier_hz=field['value'], elapsed_us=report['elapsed_us'])
    with socket.create_connection(('192.168.7.2', 47007), timeout=5) as connection:
        connection.sendall(IQCapabilityCodec.encode_query())
        response = bytearray()
        while len(response) < 48:
            part = connection.recv(48 - len(response))
            assert part, 'Capability connection closed'
            response.extend(part)
    capability = IQCapabilityCodec.decode_response(bytes(response))
    assert capability.extended_parameter and capability.carrier_recovery
    live_runs = []
    for name in ('live-820-carrier-v1.json', 'live-820-carrier-v2.json'):
        path = base / name
        report = json.loads(path.read_text(encoding='utf-8'))
        fields = report.get('measurement', {}).get('record_fields', {})
        invalid = [key for key in ('emission_center_frequency', 'occupied_bandwidth',
                                  'channel_power_dbfs', 'snr_estimate_db')
                   if fields.get(key, {}).get('state') != 'valid']
        entry = {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path),
                 'raw_status': report['status'], 'measurement_valid': not invalid,
                 'invalid_fields': invalid, 'reason': report.get('reason', 'quality_gate_rejected')}
        if fields:
            record_path = Path(report['measurement']['record_path'])
            document, _ = read_measurement(record_path)
            assert digest(record_path) == report['measurement']['record_sha256']
            entry['record_sha256'] = digest(record_path)
            entry['reference_difference_db'] = document['quality']['reference_difference_db']
            profile = document['source'].get('channelizer', {}).get('profile', {})
            if profile.get('passband_edge_hz'):
                span = document['intent']['span']
                spacing = document['sample_rate_hz'] / 4096
                offsets = [(span['lower_shifted_bin'] - padding - 2048) * spacing
                           for padding in (36, 5)] + [
                    (span['upper_shifted_bin'] + padding - 2048) * spacing for padding in (5, 36)]
                edge = profile['passband_edge_hz']
                entry['reference_offsets_hz'] = offsets
                entry['channelizer_passband_edge_hz'] = edge
                entry['references_inside_flat_passband'] = all(abs(offset) <= edge for offset in offsets)
        live_runs.append(entry)
    sources = ('algorithms/parameters/carrier_recovery.py', 'algorithms/p0/parameter_client.py',
               'algorithms/p0/transport.py', 'app/operator_console/live_ed.py',
               'app/operator_console/measurement_record.py',
               'app/operator_console/quick_measurement_actions.py',
               'app/operator_console/qml/ParameterMeasurementPanel.qml',
               'scripts/capture_live_parameter_once.py', 'scripts/replay_parameter_record_on_board.py',
               'scripts/verify_carrier_deployment_evidence.py', 'tests/test_carrier_recovery.py',
               'tests/test_app_f_quick_product.py', 'tests/p0/p0_ed_service_protocol_test.c',
               'tests/p0/p0_iq_transport_test.c', 'tests/p0/p0_parameter_runtime_test.c')
    return {'schema': 'carrier-deployment-evidence-v1', 'status': 'passed',
            'recorded_utc': datetime.now(timezone.utc).isoformat(), 'requirements': ['KTR-4.2'],
            'scope': 'source/binary/capability and existing physical record consistency; not global RF acceptance',
            'build_manifest_sha256': digest(build_path), 'products': build['binaries'],
            'capabilities': asdict(capability), 'capability_response_hex': bytes(response).hex(),
            'reports': reports, 'new_live_runs': live_runs,
            'sources': {name: digest(ROOT / name) for name in sources},
            'open_gates': ['new live RF conditional-carrier visibility', 'broader modulation coverage',
                           'calibrated absolute frequency', 'dBm calibration', 'cold boot persistence',
                           'PHASE-08/ST-06 and physical KTR-4.2 acceptance']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'reports': len(report['reports']),
                      'new_live_valid_count': sum(item['measurement_valid'] for item in report['new_live_runs']),
                      'capabilities': report['capabilities']}, ensure_ascii=False))
