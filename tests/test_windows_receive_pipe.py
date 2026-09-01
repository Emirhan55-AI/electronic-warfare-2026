import os
import subprocess
import sys
import threading
import time

import pytest

from platforms.acquisition.windows_pipe import BinaryReceivePipe, RECEIVE_PIPE_BUFFER_BYTES


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows binary pipe contract")


def test_receive_pipe_reserves_bounded_scheduler_headroom_for_8_msps_ci8():
    import win32pipe

    pipe = BinaryReceivePipe()
    try:
        _, output_buffer_bytes, input_buffer_bytes, max_instances = win32pipe.GetNamedPipeInfo(pipe._handle)
        assert input_buffer_bytes == RECEIVE_PIPE_BUFFER_BYTES
        assert output_buffer_bytes == RECEIVE_PIPE_BUFFER_BYTES
        assert max_instances == 1
        assert RECEIVE_PIPE_BUFFER_BYTES == 4_194_304
        assert RECEIVE_PIPE_BUFFER_BYTES / (8_000_000 * 2) >= .25
    finally:
        pipe.close()


def test_binary_receive_preserves_every_byte_including_cr_lf_and_text_eof():
    pipe = BinaryReceivePipe()
    expected = bytes(range(256)) * 2048
    process = subprocess.Popen([sys.executable, "-c",
        "import sys; f=open(sys.argv[1],'wb'); f.write(bytes(range(256))*2048); f.close()", pipe.path],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        pipe.connect(process)
        chunks = []
        while chunk := pipe.read(32768):
            chunks.append(chunk)
        assert b"".join(chunks) == expected
        assert process.wait(timeout=3) == 0
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=3)
        pipe.close()
        pipe.close()


def test_receive_pipe_connection_has_bounded_wait_without_a_writer():
    class MissingWriter:
        def poll(self):
            return None
    pipe = BinaryReceivePipe()
    try:
        with pytest.raises(OSError):
            pipe.connect(MissingWriter(), timeout=.1)
    finally:
        pipe.close()


def test_close_cancels_pending_connection_from_another_thread():
    class MissingWriter:
        def poll(self):
            return None
    pipe = BinaryReceivePipe()
    outcomes = []
    def connect():
        try:
            pipe.connect(MissingWriter(), timeout=3)
        except OSError:
            outcomes.append("cancelled")
    thread = threading.Thread(target=connect)
    thread.start()
    time.sleep(.05)
    pipe.close()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert outcomes == ["cancelled"]
