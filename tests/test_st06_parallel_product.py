import json
import pytest
from scripts import verify_st06_parallel_product as product
from scripts.verify_phase08_evidence_recovery import verify_frozen_file

def test_historical_parallel_product_evidence_and_separate_rf_gate():
    result=product.verify(historical=True)
    assert result['gates']['digital_product_throughput']
    assert not result['gates']['ST06_complete']


def test_current_source_gate_rejects_a_changed_source(tmp_path, monkeypatch):
    relative='results/evidence/phase08/st06-parallel-product-v1.json'
    original_root=product.ROOT
    original=json.loads((original_root/relative).read_text(encoding='utf-8'))
    report=tmp_path/relative
    report.parent.mkdir(parents=True)
    report.write_bytes((original_root/relative).read_bytes())
    archive=tmp_path/original['archive']['path']
    archive.hardlink_to(original_root/original['archive']['path'])
    changed=tmp_path/'app/operator_console/live_ed.py'
    changed.parent.mkdir(parents=True)
    changed.write_bytes(b'changed source\n')
    monkeypatch.setattr(product,'ROOT',tmp_path)
    monkeypatch.setattr(product,'EVIDENCE',report)
    with pytest.raises(AssertionError,match='Güncel kaynak'):
        product.verify()


def test_relabelled_manifest_cannot_pass_as_historical_evidence(tmp_path):
    relative='results/evidence/phase08/st06-parallel-product-v1.json'
    report=json.loads((product.ROOT/relative).read_text(encoding='utf-8'))
    report['source_sha256']['app/operator_console/live_ed.py']='0'*64
    report['source_revalidated_at']='2026-09-06T00:00:00Z'
    destination=tmp_path/relative
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(report),encoding='utf-8')
    with pytest.raises(ValueError,match='Tarihsel kanıt değiştirildi'):
        verify_frozen_file(relative,root=tmp_path)
