"""Evidence repair must preserve measurements and keep unmeasured gates open."""
import hashlib
import json

import pytest

from scripts import verify_phase08_evidence_recovery as recovery


def test_review_preserves_failures_and_only_accepts_headless_integrity():
    paths=[recovery.ROOT/name for name in recovery.FROZEN_EVIDENCE]
    paths += [recovery.ROOT/recovery.REPORT]
    before={path:recovery.file_hash(path) for path in paths}
    result=recovery.verify()
    assert result['prior_usb_overrun_runs']==2
    assert result['headless_integrity_runs']==1
    assert result['observed_fps'] < result['required_fps']
    assert not result['acceptance']['gui_acceptance']
    assert not result['acceptance']['rf_detection_acceptance']
    assert not result['acceptance']['ST06_complete']
    assert before=={path:recovery.file_hash(path) for path in paths}


@pytest.mark.parametrize('relative',recovery.FROZEN_EVIDENCE)
def test_rewritten_historical_evidence_is_rejected(relative,tmp_path):
    destination=tmp_path/relative
    destination.parent.mkdir(parents=True)
    if relative.endswith('.json'):
        report=json.loads((recovery.ROOT/relative).read_text(encoding='utf-8'))
        report['source_sha256']['app/operator_console/live_ed.py']=hashlib.sha256(b'new').hexdigest()
        report['source_revalidated_at']='2026-09-06T00:00:00Z'
        destination.write_text(json.dumps(report),encoding='utf-8')
    else:
        destination.write_bytes(b'repacked historical archive')
    with pytest.raises(ValueError,match='Tarihsel kanıt değiştirildi'):
        recovery.verify_frozen_file(relative,root=tmp_path)
