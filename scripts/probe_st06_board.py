"""Bounded digital board probe; no HackRF, RF transmission or throughput claim."""
from dataclasses import asdict
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from algorithms.p0 import IQFrame, TCPClientIQTransport, decode_local_ed_response


def probe(host, port, output, service_sha256):
    output.mkdir(parents=True, exist_ok=False)
    known_path = ROOT / 'datasets/fixtures/phase01/known-tone-ci8.sigmf-data'
    with known_path.open('rb') as stream:
        known = stream.read(8192)
    if len(known) != 8192:
        raise ValueError('Bilinen I/Q karesi eksik.')
    stimuli = [bytes(8192)] * 4 + [known] * 8 + [bytes(8192)] * 20
    transport = TCPClientIQTransport()
    summaries = []
    raw = bytearray()
    error = None
    try:
        transport.connect(host, port, timeout_seconds=5)
        for start in range(0, len(stimuli), 4):
            frames = tuple(IQFrame(i, 2_000_000, 101_500_000, stimuli[i], frame_id=i)
                           for i in range(start, start + 4))
            responses = transport.exchange_batch(frames)
            for frame, response in zip(frames, responses, strict=True):
                raw += len(response.payload).to_bytes(4, 'little') + response.payload
                summaries.append(asdict(decode_local_ed_response(response.payload, frame.frame_id)))
    except Exception as exc:
        error = str(exc)
    finally:
        transport.close()
    checks = {
        'all_32_frames_returned': len(summaries) == 32,
        'dma_flags_valid': bool(summaries) and all(s['dma_status_flags'] == 7 for s in summaries),
        'zero_input_initially_quiet': len(summaries) >= 4 and all(s['active_count'] == 0 for s in summaries[:4]),
        'known_input_produces_candidates': any(s['raw_candidate_count'] > 0 for s in summaries[4:12]),
        'known_input_produces_active_events': any(s['active_count'] > 0 for s in summaries[4:12]),
        'zero_tail_clears_events': len(summaries) == 32 and summaries[-1]['active_count'] == 0,
        'transport_integrity': transport.stats.crc_errors == 0 and transport.stats.sequence_errors == 0 and transport.stats.queue_drops == 0,
        'no_dropped_candidates': bool(summaries) and all(s['dropped_candidates'] == 0 for s in summaries),
    }
    inputs = b''.join(stimuli)
    (output / 'input.ci8').write_bytes(inputs)
    (output / 'responses.bin').write_bytes(raw)
    result = {'status': 'passed' if error is None and all(checks.values()) else 'failed',
              'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'scope': '32-frame physical digital-chain smoke probe only',
              'host': host, 'port': port, 'operator_supplied_installed_service_sha256': service_sha256,
              'checks': checks, 'error': error, 'frames': summaries, 'transport': asdict(transport.stats),
              'input_sha256': hashlib.sha256(inputs).hexdigest(),
              'response_sha256': hashlib.sha256(raw).hexdigest(),
              'sources': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                          ['scripts/probe_st06_board.py', 'algorithms/p0/transport.py']},
              'fpga_image_identity_verified': False, 'new_runtime_configuration_exercised': False,
              'rf_acceptance': False, 'throughput_acceptance': False, 'st06_complete': False}
    (output / 'probe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='192.168.7.2')
    parser.add_argument('--port', type=int, default=47007)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--service-sha256', required=True)
    args = parser.parse_args()
    result = probe(args.host, args.port, args.output, args.service_sha256)
    print(json.dumps({'status': result['status'], 'checks': result['checks'], 'error': result['error']}, indent=2))
    raise SystemExit(0 if result['status'] == 'passed' else 1)
