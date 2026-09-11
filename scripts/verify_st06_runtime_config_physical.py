"""Bounded physical proof of live CFAR control and FPGA processing; no RF claim."""
from dataclasses import asdict
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BUILD = ROOT / 'build/p0/st06-runtime-config-v2-20260910'

from algorithms.p0 import IQFrame, TCPClientIQTransport, decode_local_ed_response
from algorithms.p0.detection_config import (
    DetectionProfile, NORMAL_DEFAULT, WEAK_DEFAULT, exchange_profile,
)


def stimuli() -> tuple[bytes, ...]:
    rng = random.Random(0x53540601)
    frames = []
    for _ in range(4):
        signed = [rng.randrange(-48, 49) for _ in range(8192)]
        frames.append(bytes(value & 0xff for value in signed))
    return tuple(frames)


def artifact_sha256(relative: str) -> str:
    return hashlib.sha256((BUILD / relative).read_bytes()).hexdigest()


def exchange_iq(host: str, port: int, payloads: tuple[bytes, ...]):
    transport = TCPClientIQTransport()
    raw = bytearray()
    summaries = []
    try:
        transport.connect(host, port, timeout_seconds=5)
        frames = tuple(IQFrame(index, 2_000_000, 101_500_000, payload,
                               frame_id=index)
                       for index, payload in enumerate(payloads))
        responses = transport.exchange_batch(frames)
        for frame, response in zip(frames, responses, strict=True):
            raw += len(response.payload).to_bytes(4, 'little') + response.payload
            summaries.append(asdict(decode_local_ed_response(response.payload,
                                                              frame.frame_id)))
    finally:
        transport.close()
    return summaries, bytes(raw), asdict(transport.stats)


def main(host: str, port: int, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    payloads = stimuli()
    initial = exchange_profile(host, port)
    profiles = {'initial': asdict(initial)}
    cases = {}
    final = initial
    try:
        if (initial.alpha_q32, initial.weak_alpha_q32) != (NORMAL_DEFAULT, WEAK_DEFAULT):
            initial = exchange_profile(host, port, profile=DetectionProfile(
                initial.generation, NORMAL_DEFAULT, WEAK_DEFAULT))
            profiles['normalized'] = asdict(initial)

        summaries, raw, stats = exchange_iq(host, port, payloads)
        cases['default'] = {'frames': summaries, 'transport': stats,
                            'response_sha256': hashlib.sha256(raw).hexdigest()}
        (output / 'default.responses.bin').write_bytes(raw)

        sensitive = exchange_profile(host, port, profile=DetectionProfile(
            initial.generation, 2 * (1 << 32), (3 * (1 << 32)) // 2))
        profiles['sensitive'] = asdict(sensitive)
        summaries, raw, stats = exchange_iq(host, port, payloads)
        cases['sensitive'] = {'frames': summaries, 'transport': stats,
                              'response_sha256': hashlib.sha256(raw).hexdigest()}
        (output / 'sensitive.responses.bin').write_bytes(raw)

        restored = exchange_profile(host, port, profile=DetectionProfile(
            sensitive.generation, NORMAL_DEFAULT, WEAK_DEFAULT))
        profiles['restored'] = asdict(restored)
        summaries, raw, stats = exchange_iq(host, port, payloads)
        cases['restored'] = {'frames': summaries, 'transport': stats,
                             'response_sha256': hashlib.sha256(raw).hexdigest()}
        (output / 'restored.responses.bin').write_bytes(raw)
        final = exchange_profile(host, port)
        profiles['final'] = asdict(final)
    finally:
        actual = exchange_profile(host, port)
        if (actual.alpha_q32, actual.weak_alpha_q32) != (NORMAL_DEFAULT, WEAK_DEFAULT):
            actual = exchange_profile(host, port, profile=DetectionProfile(
                actual.generation, NORMAL_DEFAULT, WEAK_DEFAULT))
        final = actual

    default_raw = sum(item['raw_candidate_count'] for item in cases['default']['frames'])
    sensitive_raw = sum(item['raw_candidate_count'] for item in cases['sensitive']['frames'])
    restored_raw = sum(item['raw_candidate_count'] for item in cases['restored']['frames'])
    checks = {
        'initial_defaults_read_from_card': (
            profiles['initial']['alpha_q32'], profiles['initial']['weak_alpha_q32']) ==
            (NORMAL_DEFAULT, WEAK_DEFAULT),
        'custom_profile_exact_readback': (
            profiles['sensitive']['alpha_q32'], profiles['sensitive']['weak_alpha_q32']) ==
            (2 * (1 << 32), (3 * (1 << 32)) // 2),
        'generation_advanced_on_each_apply':
            profiles['restored']['generation'] == (profiles['sensitive']['generation'] + 1) & 0xffffffff,
        'threshold_changes_fpga_decisions': sensitive_raw > default_raw,
        'restored_decisions_match_default': restored_raw == default_raw,
        'final_defaults_read_from_card': (final.alpha_q32, final.weak_alpha_q32) ==
            (NORMAL_DEFAULT, WEAK_DEFAULT),
        'all_dma_responses_valid': all(
            item['dma_status_flags'] == 7
            for case in cases.values() for item in case['frames']),
        'transport_integrity': all(
            case['transport']['crc_errors'] == 0 and
            case['transport']['sequence_errors'] == 0 and
            case['transport']['queue_drops'] == 0 for case in cases.values()),
    }
    result = {
        'schema': 'phase08-st06-runtime-config-physical-v1',
        'status': 'passed' if all(checks.values()) else 'failed',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'ZedBoard live register control plus bounded digital I/Q processing',
        'host': host, 'port': port,
        'profiles': profiles,
        'candidate_totals': {'default': default_raw, 'sensitive': sensitive_raw,
                             'restored': restored_raw},
        'checks': checks, 'cases': cases,
        'stimulus_sha256': hashlib.sha256(b''.join(payloads)).hexdigest(),
        'hardware_identity': {
            'detection_control_id': '0x53540601',
            'identity_source': 'local staged artifacts; board-side hashes are recorded by the evidence manifest',
            'bitstream_bin_sha256': artifact_sha256('hardware/p0_system_wrapper.bit.bin'),
            'module_sha256': artifact_sha256('software/p0_dma_client.ko'),
            'service_sha256': artifact_sha256('software/p0-ed-service'),
            'bridge_sha256': artifact_sha256('software/p0-ed-network-bridge'),
        },
        'claim_boundary': {
            'rf_input_used': False, 'hackrf_used': False, 'throughput_acceptance': False,
            'pd_pfa_acceptance': False, 'cold_boot_acceptance': False,
        },
    }
    (output / 'physical.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'candidate_totals': result['candidate_totals'],
                      'checks': checks}, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='192.168.7.2')
    parser.add_argument('--port', type=int, default=47007)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if main(args.host, args.port, args.output)['status'] == 'passed' else 1)
