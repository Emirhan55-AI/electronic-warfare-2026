from __future__ import annotations

import struct
import unittest

from reference.p0 import IQFrame, IQFrameCodec, LoopbackIQTransport, TransportError


class P0TransportTests(unittest.TestCase):
    def test_round_trip_and_statistics(self) -> None:
        transport = LoopbackIQTransport(queue_capacity=2)
        transport.connect()
        frame = IQFrame(0, 8_000_000, 100_000_000, bytes(range(32)))
        self.assertTrue(transport.send(frame))
        self.assertEqual(transport.receive(), frame)
        self.assertEqual(transport.stats.frames_sent, 1)
        self.assertEqual(transport.stats.frames_received, 1)

    def test_frame_chunk_identity_round_trip(self) -> None:
        frame = IQFrame(17, 20_000_000, 2_430_000_000, b"\x01\x02" * 4096, frame_id=9, chunk_index=1, chunk_count=3)
        decoded = IQFrameCodec.decode(IQFrameCodec.encode(frame))
        self.assertEqual(decoded, frame)
        self.assertEqual(decoded.complex_sample_count, 4096)

    def test_crc_and_bounded_queue(self) -> None:
        packet = bytearray(IQFrameCodec.encode(IQFrame(0, 8_000_000, 100_000_000, b"\x01\x02" * 16)))
        packet[-1] ^= 1
        with self.assertRaisesRegex(TransportError, "CRC"):
            IQFrameCodec.decode(bytes(packet))
        transport = LoopbackIQTransport(queue_capacity=1)
        transport.connect()
        self.assertTrue(transport.send(IQFrame(0, 8_000_000, 100_000_000, b"\x00\x00")))
        self.assertFalse(transport.send(IQFrame(1, 8_000_000, 100_000_000, b"\x00\x00")))
        self.assertEqual(transport.stats.queue_drops, 1)

    def test_decoder_rejects_zero_length_payload(self) -> None:
        packet = struct.pack("<4sBBHIIHHQIIII", b"P0IQ", 1, 1, 44, 0, 0, 0, 1, 100_000_000, 8_000_000, 0, 0, 0)
        with self.assertRaisesRegex(TransportError, "yük uzunluğu"):
            IQFrameCodec.decode(packet)


if __name__ == "__main__":
    unittest.main()
