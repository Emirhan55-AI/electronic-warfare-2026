"""Board result integrity and absence of host estimator fallback."""
from dataclasses import replace
import struct
import zlib
from unittest.mock import patch

import numpy as np
import pytest

from algorithms.p0.parameter_client import encode_request, decode_response
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
    assert document['processing_location']=='zedboard_arm'
    assert document['spectrum_origin']=='physical_pl_replay_of_recorded_ci8'
    assert document['calibration']['dbm_available'] is False
    assert document['fields']['signal_domain']['method_id'] is None
    assert document['board_measurement']['input_ci8_sha256']==records.digest(iq)
    with patch.object(records,'measure_on_board',side_effect=RuntimeError('kart kapalı')), \
         patch.object(records.F5ParameterEstimator,'measure',side_effect=AssertionError('fallback')):
        with pytest.raises(RuntimeError,match='kart kapalı'):
            records.measure_and_record(intent,samples,**kwargs)
    assert len(list(tmp_path.glob('*.zip')))==1
