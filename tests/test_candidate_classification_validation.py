"""KTR-4.2-F1: sınıf kabulünde payda ve model kimliği korunur."""
import pytest
from scripts.validate_candidate_classification import summarize, run


def test_abstentions_and_wrong_decisions_cannot_hide_failed_gate():
    rows = [{'reference': {'family': 'BPSK'}, 'decision': d}
            for d in ['Sayısal'] * 7 + ['Analog'] + ['Belirsiz'] * 2]
    result = summarize(rows)
    assert result['BPSK']['decision_coverage'] == .8
    assert result['BPSK']['definite_precision'] == .875
    assert result['BPSK']['wrong_definite'] == 1
    assert not result['BPSK']['gate_pass']
    assert not result['QPSK']['gate_pass']


def test_cw_abstention_is_correct_negative_control():
    result = summarize([{'reference': {'family': 'CW'}, 'decision': 'Belirsiz'}])['CW']
    assert result['gate_pass']
    assert result['decision_coverage'] == 0
    assert result['definite_precision'] is None


def test_changed_model_rejected_before_creating_output(tmp_path):
    model = tmp_path / 'model.json'
    model.write_text('{}', encoding='utf-8')
    output = tmp_path / 'run'
    with pytest.raises(ValueError, match='Model özeti'):
        run(output, model, '0' * 64)
    assert not output.exists()
