"""Board result integrity and absence of host estimator fallback."""
from dataclasses import replace
import struct
import zlib
from unittest.mock import patch

import numpy as np
import pytest

from algorithms.p0.parameter_client import encode_request, decode_response, BoardAnalysisSpan, BOARD_PERSISTENT_PAYLOAD_BYTES
from algorithms.parameters.f1_development import _intent
from algorithms.spectrum import SpectrumConfig
from app.operator_console import measurement_record as records


def response(intent, iq, token=7):
    payload = bytearray(176)
    struct.pack_into('<4sHHIIQQIB', payload, 0, b'P0PR', 1, 176, token, 0,
                     token, intent.event_id, intent.start_frame+3, 4)
    for offset, value in zip(range(40,112,12), (100e6, 99.99e6, 100.01e6, 20000, -30, 12)):
        struct.pack_into('<BBHd', payload, offset, 1, 0, 0, value)
    struct.pack_into('<BBHd', payload, 144, 4, 9, 0, 0.)
    struct.pack_into('<IIII', payload, 156, 25000, zlib.crc32(iq), 3, 4096)
    struct.pack_into('<I', payload, 172, zlib.crc32(payload[:172]))
    return bytes(payload)


def test_result_binding_and_carrier_absence():
    intent = _intent((2180, 2238), 1, 1)
    iq = bytes(32768)
    request = encode_request(intent, iq, 2_000_000, 100_000_000, 7)
    assert len(request) == 32832 and zlib.crc32(request[:60]) == struct.unpack_from('<I',request,60)[0]
    measured = decode_response(response(intent, iq), intent, iq, 7)
    assert measured.result.carrier_line_frequency.state == 'not_observed'
    assert measured.result.emission_center_frequency.value == 100e6
    assert measured.result.signal_domain.state == 'not_applicable'
    with pytest.raises(ValueError): decode_response(response(intent, iq), intent, iq, 8)
    with pytest.raises(ValueError): decode_response(response(intent, iq), intent, b'1'*32768, 7)
    with pytest.raises(ValueError): decode_response(response(intent, iq)[:-1], intent, iq, 7)
    corrupted = bytearray(response(intent, iq)); corrupted[92] ^= 1
    with pytest.raises(ValueError): decode_response(bytes(corrupted), intent, iq, 7)


@pytest.mark.parametrize('offset,value', [(40, 9), (41, 11), (42, 1), (144, 7)])
def test_invalid_field_rejected_even_with_correct_crc(offset, value):
    intent = _intent((2180,2238), 1, 1); iq=bytes(32768)
    payload=bytearray(response(intent,iq)); payload[offset]=value
    struct.pack_into('<I', payload, 172, zlib.crc32(payload[:172]))
    with pytest.raises(ValueError): decode_response(bytes(payload), intent, iq, 7)


def test_live_record_uses_board_and_never_host_fallback(tmp_path):
    intent = _intent((2180,2238), 1, 1)
    samples = tuple(np.zeros(4096, dtype=complex) for _ in range(4))
    iq=bytes(32768)
    board = decode_response(response(intent,iq),intent,iq,7)
    kwargs=dict(sample_rate_hz=2_000_000, center_frequency_hz=100_000_000,
                spectrum_config=SpectrumConfig(), source={'kind':'hackrf'},
                requested_utc='2026-09-11T00:00:00Z', directory=tmp_path,
                board_endpoint=('127.0.0.1',47007))
    with patch.object(records, 'measure_on_board', return_value=board), \
         patch.object(records, 'SpectrumProcessor', side_effect=AssertionError('host FFT called')), \
         patch.object(records.F5ParameterEstimator, 'measure', side_effect=AssertionError('host estimator called')):
        saved=records.measure_and_record(intent,samples,**kwargs)
        document,_=records.read_measurement(saved.path)
    assert document['processing_location']=='hybrid_zedboard_arm_host'
    assert document['spectrum_origin']=='physical_pl_replay_of_recorded_ci8'
    assert document['calibration']['dbm_available'] is False
    assert document['fields']['signal_domain']['method_id']=='domain.digital-analog-logreg-pc-v1'
    assert document['fields']['signal_domain']['state']=='uncertain'
    assert document['automatic_signal_domain']['physical_acceptance'] is False
    assert document['automatic_signal_domain']['product_acceptance'] is False
    assert records.replay_measurement(saved.path).signal_domain.state == 'uncertain'
    assert document['board_measurement']['input_ci8_sha256']==records.digest(iq)
    with patch.object(records,'measure_on_board',side_effect=RuntimeError('kart kapalı')), \
         patch.object(records.F5ParameterEstimator,'measure',side_effect=AssertionError('fallback')):
        with pytest.raises(RuntimeError,match='kart kapalı'):
            records.measure_and_record(intent,samples,**kwargs)
    assert len(list(tmp_path.glob('*.zip')))==1


def test_wide_span_is_versioned_and_does_not_change_frozen_host_span():
    from algorithms.parameters import AnalysisSpan
    with pytest.raises(ValueError):
        AnalysisSpan(1000, 3400, "auto_suggested")
    for bounds in ((55, 4039), (56, 4040), (56, 62)):
        with pytest.raises(ValueError):
            BoardAnalysisSpan(*bounds, "auto_suggested")
    intent = replace(_intent((2180, 2238), 1, 1), span=BoardAnalysisSpan(56, 4039, "auto_suggested"))
    iq = bytes(32768)
    request = encode_request(intent, iq, 2_000_000, 100_000_000, 7)
    assert struct.unpack_from('<H', request, 4)[0] == 2
    with pytest.raises(ValueError):
        decode_response(response(intent, iq), intent, iq, 7)
    payload = bytearray(response(intent, iq))
    struct.pack_into('<H', payload, 4, 2)
    struct.pack_into('<I', payload, 172, zlib.crc32(payload[:172]))
    assert decode_response(bytes(payload), intent, iq, 7).result.persistent_payload_bytes == BOARD_PERSISTENT_PAYLOAD_BYTES


def test_wide_board_record_roundtrip_never_uses_host_numeric_estimator(tmp_path):
    intent = replace(_intent((2180, 2238), 1, 1), span=BoardAnalysisSpan(1000, 3400, "auto_suggested"))
    iq = bytes(32768)
    payload = bytearray(response(intent, iq))
    struct.pack_into('<H', payload, 4, 2)
    struct.pack_into('<I', payload, 172, zlib.crc32(payload[:172]))
    board = decode_response(bytes(payload), intent, iq, 7)
    with patch.object(records, 'measure_on_board', return_value=board), \
         patch.object(records.F5ParameterEstimator, 'measure', side_effect=AssertionError('host numerical fallback')):
        saved = records.measure_and_record(intent, tuple(np.zeros(4096, complex) for _ in range(4)),
            sample_rate_hz=2_000_000, center_frequency_hz=100_000_000, spectrum_config=SpectrumConfig(),
            source={'kind': 'hackrf'}, requested_utc='2026-09-12T00:00:00Z', directory=tmp_path,
            board_endpoint=('127.0.0.1', 47007))
        assert saved.persistent_payload_limit == BOARD_PERSISTENT_PAYLOAD_BYTES
        assert records.replay_measurement(saved.path).channel_power_dbfs.value == -30
        document, _ = records.read_measurement(saved.path)
        assert document['board_measurement']['protocol'] == 'P0PM-v2'
        assert document['board_measurement']['persistent_payload_bytes'] == 389376
        assert document['fields']['signal_domain']['state'] == 'uncertain'


def test_truncated_owner_is_rejected_before_card_measurement(tmp_path):
    intent = _intent((2180, 2238), 1, 1)
    owner = replace(intent.context.candidates[0], lower_shifted_bin=1109, upper_shifted_bin=3394)
    intent = replace(intent, context=replace(intent.context, candidates=(owner,)))
    with patch.object(records, 'measure_on_board', side_effect=AssertionError('must reject before board')):
        with pytest.raises(ValueError, match='tamamını kapsamıyor'):
            records.measure_and_record(intent, tuple(np.zeros(4096, complex) for _ in range(4)),
                sample_rate_hz=2_000_000, center_frequency_hz=100_000_000, spectrum_config=SpectrumConfig(),
                source={'kind': 'hackrf'}, requested_utc='2026-09-12T00:00:00Z', directory=tmp_path,
                board_endpoint=('127.0.0.1', 47007))
    assert not list(tmp_path.glob('*.zip'))
