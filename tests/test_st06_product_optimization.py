"""ST-06 aktarım biçimi ve sayısal eşdeğerlik regresyonları."""
import _ctypes
import ctypes
import os
from pathlib import Path
import tempfile

import numpy as np

from scripts.verify_p0_os_cfar_pl_runtime import _compile
from scripts.verify_st06_product_optimization import verify


def test_historical_product_optimization_evidence_and_open_speed_gate():
    assert verify(historical=True)["status"] == "partial_product_throughput_failed"


def test_unaligned_uq30_decode_remains_bit_exact_across_full_power_range():
    with tempfile.TemporaryDirectory() as directory:
        library_path, _ = _compile(Path(directory))
        library = ctypes.CDLL(str(library_path))
        try:
            decode = library.p0_pl_os_cfar_decode
            decode.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                               ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
            rng = np.random.default_rng(6100699)
            bins = np.arange(4096) ^ 2048
            for repeat in range(128):
                powers = rng.integers(0, 1 << 58, 4096, dtype=np.uint64)
                powers[:8] = [0, 1, (1 << 32) - 1, 1 << 32, (1 << 53) - 1,
                              1 << 53, (1 << 58) - 2, (1 << 58) - 1]
                words = powers.copy()
                if repeat % 2:
                    words |= np.uint64(0xA000000000000000)
                    words[(bins >= 20) & (bins < 4076)] |= np.uint64(1 << 58)
                raw = ctypes.create_string_buffer(b"\0" + words.astype("<u8").tobytes())
                shifted = np.empty(4096, dtype=np.uint64)
                floating = np.empty(4096, dtype=np.float64)
                detections = np.empty(4096, dtype=np.uint8)
                marked = ctypes.c_int()
                assert decode(ctypes.addressof(raw) + 1, 32768, shifted.ctypes.data,
                              floating.ctypes.data, detections.ctypes.data,
                              ctypes.byref(marked)) == 0
                expected = np.roll(powers, 2048)
                assert np.array_equal(shifted, expected)
                assert np.array_equal(floating.view(np.uint64),
                                      (expected.astype(np.float64) / (1 << 30)).view(np.uint64))
                assert marked.value == repeat % 2
                assert not detections.any()
                # Reject mixed format and invalid evaluation at either end.
                if repeat < 4:
                    words[0 if repeat % 2 else -1] ^= np.uint64(1 << 60)
                    invalid = ctypes.create_string_buffer(words.astype("<u8").tobytes())
                    assert decode(invalid, 32768, shifted.ctypes.data, floating.ctypes.data,
                                  detections.ctypes.data, ctypes.byref(marked)) != 0
        finally:
            if os.name == "nt":
                _ctypes.FreeLibrary(library._handle)
            else:
                _ctypes.dlclose(library._handle)
