"""16 kareli kayıt/protokol sınırı, bütünlük ve PC geri dönüş yasağı."""
from dataclasses import replace
import struct
from unittest.mock import patch
import zlib

import numpy as np
import pytest

from algorithms.p0.parameter_client import encode_request, decode_response, EXTENDED_BOARD_PAYLOAD_BYTES
from algorithms.p0.transport import IQCapabilityCodec, TransportCapabilities
from algorithms.parameters.f1_development import _intent
from algorithms.spectrum import SpectrumConfig
from app.operator_console import measurement_record as records


def setup():
    intent = _intent((2180,2238),1,1)
    intent = replace(intent,context=replace(intent.context,owner_observed_frames=(True,)*16))
    events=[dict(event_id=intent.event_id,seen_count=intent.event_revision,state='confirmed',observed_this_frame=True,
                 start_shifted_bin=2205,peak_shifted_bin=2208,end_shifted_bin=2211) for _ in range(16)]
    sequences=list(range(intent.start_frame,intent.start_frame+16))
    source={'kind':'hackrf','sequence_numbers':sequences,'frame_ids':sequences,'owner_observations':events,
            'channel_capture':dict(binding='operator_selected_channel_v1',frame_count=16,span=[2180,2238],
                emitter_identity_verified=False,fresh_after_operator_request=True,
                host_capture_sequence_floor=intent.start_frame-1,event_ids=[intent.event_id]*16)}
    iq=bytes(131072)
    response=bytearray(176)
    struct.pack_into('<4sHHIIQQIB',response,0,b'P0PR',3,176,7,0,7,intent.event_id,intent.start_frame+15,16)
    for offset,value in zip(range(40,112,12),(100e6,99.99e6,100.01e6,20000,-30,12)):
        struct.pack_into('<BBHd',response,offset,1,0,0,value)
    struct.pack_into('<BBHd',response,144,4,9,0,0.)
    struct.pack_into('<IIII',response,156,25000,zlib.crc32(iq),3,4096)
    struct.pack_into('<I',response,172,zlib.crc32(response[:172]))
    return intent,source,iq,bytes(response)


def test_extended_protocol_capability_and_crc():
    cap=TransportCapabilities(extended_parameter=True)
    assert IQCapabilityCodec.decode_response(IQCapabilityCodec.encode_response(cap)) == cap
    intent,_,iq,response=setup()
    request=encode_request(intent,iq,2000000,100000000,7)
    assert len(request)==131136 and request[4:6] == b'\x03\x00'
    assert decode_response(response,intent,iq,7).result.quality.observed_frames==16
    for broken in (response[:-1],response[:16]+bytes(1)+response[17:]):
        with pytest.raises(ValueError): decode_response(broken,intent,iq,7)
    with pytest.raises(ValueError): decode_response(response,intent,iq[:32768],7)
    with pytest.raises(ValueError): encode_request(replace(intent,start_frame=2**32-15),iq,2000000,100000000,7)


def test_extended_archive_replay_and_no_host_fallback(tmp_path):
    intent,source,iq,response=setup()
    board=decode_response(response,intent,iq,7)
    samples=tuple(np.zeros((16,4096),complex))
    with patch.object(records,'measure_on_board',return_value=board), patch.object(records,'SpectrumProcessor',side_effect=AssertionError('host FFT')):
        result=records.measure_and_record(intent,samples,sample_rate_hz=2000000,center_frequency_hz=100000000,
            spectrum_config=SpectrumConfig(),source=source,requested_utc='2026-09-16T00:00:00Z',directory=tmp_path,
            board_endpoint=('127.0.0.1',47007))
    doc,frames=records.read_measurement(result.path)
    assert len(frames)==16 and doc['observation_duration_s']==.032768
    assert doc['classification_frame_indices']==[12,13,14,15]
    assert doc['board_measurement']['protocol']=='P0PM-v3'
    assert doc['board_measurement']['span_contract']=='board-extended-v3'
    assert doc['fields']['occupied_bandwidth']['method_id'].endswith('.groups16-v1')
    assert records.replay_measurement(result.path).persistent_payload_bytes==EXTENDED_BOARD_PAYLOAD_BYTES
    source['sequence_numbers'][5] += 1
    with pytest.raises(ValueError): records.validate_measurement_ownership(intent,source)
