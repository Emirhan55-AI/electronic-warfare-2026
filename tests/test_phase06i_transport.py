from __future__ import annotations

import struct
import unittest

from reference.ps.candidate_transport import (
    ABI_VERSION,
    HEADER_BYTES,
    MAX_FRAME_BYTES,
    RECORD_BYTES,
    TRAILER_BYTES,
    decode_packet,
    encode_packet,
)
from reference.rtl.candidate_grouping import group_detector_cells
from reference.rtl.candidate_vectors import grouping_vectors


class Phase06ITransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = grouping_vectors()

    def test_abi_sizes_empty_one_and_maximum_frames(self) -> None:
        empty = encode_packet(0, ())
        self.assertEqual(HEADER_BYTES + TRAILER_BYTES, len(empty))
        self.assertEqual((), decode_packet(empty).candidates)
        one = group_detector_cells(next(v for v in self.vectors if v.vector_id == "one_bin").cells)
        self.assertEqual(HEADER_BYTES + RECORD_BYTES + TRAILER_BYTES, len(encode_packet(1, one)))
        maximum = group_detector_cells(next(v for v in self.vectors if v.vector_id == "maximum_candidate_count").cells)
        self.assertEqual(MAX_FRAME_BYTES, len(encode_packet(0xFFFF_FFFF, maximum)))
        self.assertEqual(maximum, decode_packet(encode_packet(0xFFFF_FFFF, maximum)).candidates)

    def test_version_length_crc_reserved_and_record_corruption_are_rejected(self) -> None:
        candidate = group_detector_cells(next(v for v in self.vectors if v.vector_id == "one_bin").cells)
        packet = bytearray(encode_packet(9, candidate))
        cases = []
        changed = bytearray(packet); struct.pack_into("<H", changed, 4, ABI_VERSION + 1); cases.append(changed)
        changed = bytearray(packet); changed[20] = 1; cases.append(changed)
        changed = bytearray(packet); changed[HEADER_BYTES + 16] ^= 1; cases.append(changed)
        changed = bytearray(packet); struct.pack_into("<I", changed, len(changed) - 12, len(changed) + 8); cases.append(changed)
        for changed in cases:
            with self.assertRaises(ValueError):
                decode_packet(bytes(changed))
        with self.assertRaises(ValueError):
            decode_packet(bytes(packet[:-1]))

    def test_frame_id_boundary_is_explicit_and_modulo_uint32(self) -> None:
        self.assertEqual(0xFFFF_FFFF, decode_packet(encode_packet(0xFFFF_FFFF, ())).frame_id)
        self.assertEqual(0, decode_packet(encode_packet(0, ())).frame_id)
        with self.assertRaises(ValueError):
            encode_packet(1 << 32, ())

    def test_physical_units_remain_outside_wire_abi(self) -> None:
        packet = encode_packet(0, ())
        self.assertNotIn(b"Hz", packet)
        self.assertNotIn(b"dBm", packet)


if __name__ == "__main__":
    unittest.main()
