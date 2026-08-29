from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import socket
import threading
import unittest
import zlib

from algorithms.p0 import (
    IQFrame,
    IQFrameCodec,
    IQResponse,
    IQResponseCodec,
    LoopbackIQTransport,
    TCPClientIQTransport,
    TransportError,
    decode_local_ed_response,
)


class P0TransportTests(unittest.TestCase):
    def test_live_hackrf_fpga_evidence_is_repeatable_and_source_bound(self) -> None:
        root = Path(__file__).resolve().parents[1]
        evidence = json.loads(
            (root / "results/evidence/p0/phase07-live-hackrf-fpga-acceptance.json")
            .read_text(encoding="utf-8")
        )
        repeatability = evidence["repeatability"]
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(repeatability["runs"], 5)
        self.assertEqual(repeatability["passed_runs"], 5)
        self.assertEqual(repeatability["completed_measured_frames"], 20_480)
        self.assertGreaterEqual(
            repeatability["minimum_frames_per_second"], 2_000_000 / 4_096
        )
        self.assertEqual(repeatability["total_hackrf_overruns"], 0)
        self.assertEqual(repeatability["total_transport_sequence_errors"], 0)
        self.assertGreater(repeatability["total_raw_candidates"], 0)
        self.assertFalse(evidence["hackrf_transmit_api_called"])
        for run in evidence["runs"]:
            self.assertEqual(run["hackrf_frames_received"], 4_160)
            self.assertEqual(run["transport_frames_received"], 4_160)
            self.assertEqual(run["input_saturated_components"], 0)
            self.assertEqual(run["output_saturated_components"], 0)
            self.assertLessEqual(
                run["channelized_queue_high_watermark"],
                run["channelized_queue_capacity"],
            )
        for relative, expected in evidence["source_sha256"].items():
            actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_local_service_response_decoder_validates_abi_v3(self) -> None:
        frame_id = 17
        result = bytearray(20)
        struct.pack_into("<IHHHBB", result, 0, frame_id, 0, 0, 0, 0, 0)
        header = bytearray(48)
        struct.pack_into(
            "<IHHIIIIII",
            header,
            0,
            0x31534550,
            3,
            48,
            68,
            frame_id,
            0,
            len(result),
            4,
            7,
        )
        struct.pack_into("<I", header, 44, zlib.crc32(header[:44]) & 0xFFFFFFFF)
        decoded = decode_local_ed_response(bytes(header + result), frame_id)
        self.assertEqual(decoded.frame_id, frame_id)
        self.assertEqual(decoded.raw_candidate_count, 4)
        self.assertEqual(decoded.dma_status_flags, 7)
        damaged = bytearray(header + result)
        damaged[44] ^= 1
        with self.assertRaisesRegex(TransportError, "başlığı"):
            decode_local_ed_response(bytes(damaged), frame_id)

    def test_network_bridge_boot_configuration_does_not_pin_a_volatile_mac_name(self) -> None:
        root = Path(__file__).resolve().parents[1]
        defaults = (
            root / "platforms/embedded/p0/petalinux/p0-ed-network-bridge.default"
        ).read_text(encoding="utf-8")
        init_script = (
            root / "platforms/embedded/p0/petalinux/p0-ed-network-bridge.init"
        ).read_text(encoding="utf-8")
        self.assertIn("P0_ED_NETWORK_INTERFACE=auto", defaults)
        self.assertIn("/sys/class/net/*", init_script)
        self.assertIn("Birden fazla fiziksel ağ arayüzü", init_script)

    def test_physical_ethernet_evidence_is_traceable(self) -> None:
        root = Path(__file__).resolve().parents[1]
        evidence = json.loads(
            (root / "results/evidence/p0/phase07-ethernet-physical-acceptance.json")
            .read_text(encoding="utf-8")
        )
        throughput = evidence["throughput_acceptance"]
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(throughput["repeat_runs"], 5)
        self.assertEqual(throughput["passed_runs"], 5)
        self.assertEqual(throughput["completed_frames"], 20_480)
        self.assertGreaterEqual(throughput["minimum_frames_per_second"], 2_000_000 / 4096)
        self.assertEqual(throughput["client_sequence_errors"], 0)
        persistent = evidence["persistent_image"]
        self.assertTrue(evidence["persistent_image_exercised"])
        self.assertTrue(persistent["exercised"])
        self.assertEqual(persistent["interface_selection"], "auto")
        self.assertFalse(persistent["safe_default_enabled"])
        self.assertTrue(persistent["authorized_test_activation"])
        for field in ("image_ub_sha256", "installed_bridge_sha256"):
            self.assertEqual(len(persistent[field]), 64)
            int(persistent[field], 16)
        self.assertTrue(persistent["boot_id"])
        self.assertTrue(persistent["network_interface"])
        for relative in (
            "platforms/embedded/p0/petalinux/p0-dma_1.0.bb",
            "platforms/embedded/p0/petalinux/p0-ed-network-bridge.default",
            "platforms/embedded/p0/petalinux/p0-ed-network-bridge.init",
        ):
            self.assertIn(relative, evidence["source_sha256"])
        for relative, expected in evidence["source_sha256"].items():
            actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

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
        packet = struct.pack("<4sBBHIIHHQIIIII", b"P0IQ", 2, 1, 48, 0, 0, 0, 1, 100_000_000, 8_000_000, 0, 0, 0, 0)
        with self.assertRaises(TransportError):
            IQFrameCodec.decode(packet)

    def test_header_crc_and_processing_profile_are_fail_closed(self) -> None:
        frame = IQFrame(5, 2_000_000, 101_500_000, b"\x01\x02" * 4096, frame_id=9)
        packet = bytearray(IQFrameCodec.encode(frame))
        packet[12] ^= 1
        with self.assertRaisesRegex(TransportError, "başlık CRC"):
            IQFrameCodec.decode(bytes(packet))
        IQFrameCodec.validate_processing_frame(frame)
        with self.assertRaisesRegex(TransportError, "4096 örnek"):
            IQFrameCodec.validate_processing_frame(
                IQFrame(5, 8_000_000, 101_500_000, b"\x01\x02" * 4096, frame_id=9)
            )

    def test_response_round_trip_and_crc(self) -> None:
        response = IQResponse(7, bytes(range(128)))
        packet = IQResponseCodec.encode(response)
        self.assertEqual(IQResponseCodec.decode(packet), response)
        damaged = bytearray(packet)
        damaged[-1] ^= 1
        with self.assertRaisesRegex(TransportError, "yanıt CRC"):
            IQResponseCodec.decode(bytes(damaged))

    def test_tcp_client_uses_four_frame_bounded_pipeline(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        server_error: list[Exception] = []

        def receive_exact(connection: socket.socket, count: int) -> bytes:
            result = bytearray()
            while len(result) < count:
                block = connection.recv(count - len(result))
                if not block:
                    raise RuntimeError("test connection closed")
                result.extend(block)
            return bytes(result)

        def server() -> None:
            try:
                connection, _ = listener.accept()
                with connection:
                    requests = []
                    for _ in range(4):
                        header = receive_exact(connection, 48)
                        payload_bytes = struct.unpack_from("<I", header, 36)[0]
                        requests.append(IQFrameCodec.decode(header + receive_exact(connection, payload_bytes)))
                    for frame in requests:
                        connection.sendall(IQResponseCodec.encode(IQResponse(frame.sequence_number, b"result")))
            except Exception as exc:
                server_error.append(exc)
            finally:
                listener.close()

        worker = threading.Thread(target=server, daemon=True)
        worker.start()
        client = TCPClientIQTransport()
        try:
            client.connect("127.0.0.1", port)
            frames = tuple(
                IQFrame(index, 2_000_000, 101_500_000, b"\x01\x02" * 4096, frame_id=index)
                for index in range(4)
            )
            responses = client.exchange_batch(frames)
            self.assertEqual([item.sequence_number for item in responses], [0, 1, 2, 3])
            self.assertEqual(client.stats.frames_sent, 4)
            self.assertEqual(client.stats.frames_received, 4)
        finally:
            client.close()
            worker.join(timeout=2.0)
        self.assertFalse(server_error)

    def test_tcp_client_keeps_continuous_stream_bounded_to_four_frames(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        server_error: list[Exception] = []
        observed_sequences: list[int] = []

        def receive_exact(connection: socket.socket, count: int) -> bytes:
            result = bytearray()
            while len(result) < count:
                block = connection.recv(count - len(result))
                if not block:
                    raise RuntimeError("test connection closed")
                result.extend(block)
            return bytes(result)

        def receive_frame(connection: socket.socket) -> IQFrame:
            header = receive_exact(connection, 48)
            payload_bytes = struct.unpack_from("<I", header, 36)[0]
            return IQFrameCodec.decode(header + receive_exact(connection, payload_bytes))

        def server() -> None:
            try:
                connection, _ = listener.accept()
                with connection:
                    pending = [receive_frame(connection) for _ in range(4)]
                    for index in range(12):
                        frame = pending.pop(0)
                        observed_sequences.append(frame.sequence_number)
                        connection.sendall(
                            IQResponseCodec.encode(IQResponse(frame.sequence_number, b"result"))
                        )
                        if index + 4 < 12:
                            pending.append(receive_frame(connection))
            except Exception as exc:
                server_error.append(exc)
            finally:
                listener.close()

        worker = threading.Thread(target=server, daemon=True)
        worker.start()
        client = TCPClientIQTransport()
        responses: list[int] = []
        try:
            client.connect("127.0.0.1", port)
            frames = (
                IQFrame(index, 2_000_000, 101_500_000, b"\x01\x02" * 4096, frame_id=index)
                for index in range(12)
            )
            completed = client.exchange_stream(
                frames, lambda response: responses.append(response.sequence_number)
            )
            self.assertEqual(completed, 12)
            self.assertEqual(responses, list(range(12)))
            self.assertEqual(client.stats.frames_sent, 12)
            self.assertEqual(client.stats.frames_received, 12)
        finally:
            client.close()
            worker.join(timeout=2.0)
        self.assertEqual(observed_sequences, list(range(12)))
        self.assertFalse(server_error)


if __name__ == "__main__":
    unittest.main()
