"""Koşullu taşıyıcı kestirimi gözlenen çizgiyle karıştırılmamalıdır."""
from dataclasses import replace
import struct
from unittest.mock import patch
import zlib

import numpy as np
import pytest

from algorithms.p0.parameter_client import decode_response, encode_request
from algorithms.p0.transport import IQCapabilityCodec, TransportCapabilities
from algorithms.parameters.carrier_recovery import recover_carrier, METHOD_ID
from algorithms.spectrum import SpectrumConfig
from app.operator_console import measurement_record as records
from test_extended_parameter_record import setup


def response_v5(order):
    intent, source, iq, response = setup()
    response = bytearray(response)
    struct.pack_into('<H', response, 4, 5)
    response[37] = order
    if order:
        struct.pack_into('<BBHd', response, 144, 1, 0, 0, 100001234.5)
    struct.pack_into('<I', response, 172, zlib.crc32(response[:172]))
    source['carrier_recovery_supported'] = True
    return intent, source, iq, bytes(response)


@pytest.mark.parametrize('order', [0, 2, 4])
def test_origin_and_legacy_fail_closed(order):
    intent, _, iq, response = response_v5(order)
    assert encode_request(intent, iq, 2000000, 100000000, 7, recover_carrier=True)[4:6] == b'\x05\x00'
    result = decode_response(response, intent, iq, 7, recover_carrier=True).result
    assert result.carrier_line_frequency.state == 'not_observed'
    if order:
        assert result.recovered_carrier_frequency.state == 'uncertain'
        assert result.recovered_carrier_frequency.value == 100001234.5
        assert result.recovered_carrier_frequency.reason == f'recovered_carrier_order{order}'
    else:
        assert result.recovered_carrier_frequency is None
    with pytest.raises(ValueError):
        decode_response(response, intent, iq, 7)
    with pytest.raises(ValueError):
        encode_request(intent, iq, 2000000, 100000000, 7, recover_carrier=True, locked_channel_power=True)


def test_bad_origin_and_capability():
    intent, _, iq, response = response_v5(2)
    for index, value in [(37, 3), (38, 1), (144, 4)]:
        broken = bytearray(response)
        broken[index] = value
        struct.pack_into('<I', broken, 172, zlib.crc32(broken[:172]))
        with pytest.raises(ValueError):
            decode_response(bytes(broken), intent, iq, 7, recover_carrier=True)
    cap = TransportCapabilities(extended_parameter=True, carrier_recovery=True)
    assert IQCapabilityCodec.decode_response(IQCapabilityCodec.encode_response(cap)) == cap


def test_archive_preserves_conditional_estimate_and_board_only(tmp_path):
    intent, source, iq, response = response_v5(2)
    board = decode_response(response, intent, iq, 7, recover_carrier=True)
    with patch.object(records, 'measure_on_board', return_value=board) as call, patch.object(
            records, 'SpectrumProcessor', side_effect=AssertionError('host FFT')):
        measurement = records.measure_and_record(
            intent, tuple(np.zeros((16, 4096), complex)), sample_rate_hz=2000000,
            center_frequency_hz=100000000, spectrum_config=SpectrumConfig(), source=source,
            requested_utc='2026-09-18T00:00:00Z', directory=tmp_path, board_endpoint=('127.0.0.1', 47007))
    assert call.call_args.kwargs['recover_carrier'] is True
    doc, _ = records.read_measurement(measurement.path)
    assert doc['board_measurement']['protocol'] == 'P0PM-v5'
    assert doc['board_measurement']['carrier_origin'] == 'conditional_power_order2'
    assert METHOD_ID in doc['board_measurement']['executed_methods']
    field = doc['fields']['recovered_carrier_frequency']
    assert field['state'] == 'uncertain' and field['value'] == 100001234.5
    assert field['method_id'] == METHOD_ID
    assert records.replay_measurement(measurement.path).recovered_carrier_frequency.value == 100001234.5


def test_reference_abstains_on_low_snr_and_alias_ambiguity():
    args = dict(sample_rate_hz=2000000, center_frequency_hz=100000000,
                lower_shifted_bin=1000, upper_shifted_bin=3000,
                lower_band_edge_hz=99900000, upper_band_edge_hz=100100000, snr_db=5.9)
    samples = np.zeros((16, 4096), complex)
    assert recover_carrier(samples, **args).reason == 'low_snr'
    args.update(snr_db=12, lower_band_edge_hz=99400000, upper_band_edge_hz=100600000)
    assert recover_carrier(samples, **args).reason == 'alias_ambiguity'
