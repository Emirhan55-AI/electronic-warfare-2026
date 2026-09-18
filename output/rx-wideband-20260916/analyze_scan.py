"""Read-only diagnosis of a bounded receive survey audit."""
from pathlib import Path
import collections
import hashlib
import json
import sys

path = Path(sys.argv[1])
raw = path.read_bytes()
records = []
for line in raw.splitlines():
    try:
        records.append(json.loads(line))
    except json.JSONDecodeError:
        break  # The live writer may have an incomplete last line.
begin = records[0]
windows = [r for r in records if r['type'] == 'window_complete']
observations = [dict(o, window_index=w['window']['index']) for w in windows for o in w['observations']]
possible = begin['config']['frames_per_window'] - begin['config']['guard_frames']
counter_overflow = [o['key'] for o in observations if o['observed_frames'] > possible]
wide_to_narrow = [o['key'] for o in observations
                  if o.get('bandwidth_hz', 0) >= 125488.28125
                  and 0 < o.get('verification', {}).get('bandwidth_hz', 0) < o['bandwidth_hz'] / 10]
results = [w['result'] for w in windows]
results += [o['verification']['result'] for o in observations if 'result' in o.get('verification', {})]
counters = {key: sum(r.get('transport_statistics', {}).get(key, 0) for r in results)
            for key in ('crc_errors', 'sequence_errors', 'queue_drops')}
counters['usb_overruns'] = sum(r.get('hackrf_statistics', {}).get('overruns', 0) for r in results)
counters['input_saturated_components'] = sum(r.get('input_saturated_components', 0) for r in results)
histogram = collections.Counter(int(o['frequency_hz'] // 100_000_000) for o in observations)
summary = {
    'audit': str(path.resolve()), 'snapshot_sha256': hashlib.sha256(raw).hexdigest(),
    'snapshot_bytes': len(raw), 'config': begin['config'], 'serial': begin['serial'],
    'record_counts': dict(collections.Counter(r['type'] for r in records)),
    'completed_windows': len(windows), 'total_windows': begin['total_windows'],
    'last_window': windows[-1]['window'] if windows else None,
    'observations': len(observations), 'possible_frames_per_window': possible,
    'counter_overflow_keys': counter_overflow, 'wide_to_narrow_keys': wide_to_narrow,
    'completed_primary_and_accepted_verification_counters': counters,
    'observations_by_100MHz': {f'{k*100}-{(k+1)*100}': v for k,v in sorted(histogram.items())},
    'end': next((r for r in reversed(records) if r['type'] == 'end'), None),
    'limitations': ['Observations are not emitter identities.',
                   'Broad-to-narrow matches are diagnostic flags, not proven false positives.',
                   'Counters cover completed primary and accepted verification results only.',
                   'Running process and board image hashes have not been independently matched.'],
}
out = Path(__file__).with_name('scan-analysis.json')
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
