"""Local binary byte pipe for tools whose Windows stdout is in text mode."""

import threading
import time
from uuid import uuid4


# At 8 MS/s CI8, 4 MiB holds about 262 ms of input.  The extra bounded headroom
# absorbs short Windows scheduler/render stalls before hackrf_transfer has to
# block, while the application continues to read in small fixed chunks.
RECEIVE_PIPE_BUFFER_BYTES = 4_194_304


class BinaryReceivePipe:
    def __init__(self):
        import pywintypes
        import win32event
        import win32file
        import win32pipe
        self._types, self._event, self._file = pywintypes, win32event, win32file
        self.path = rf"\\.\pipe\rf-receive-{uuid4().hex}"
        self._handle = win32pipe.CreateNamedPipe(
            self.path, win32pipe.PIPE_ACCESS_INBOUND | win32file.FILE_FLAG_OVERLAPPED,
            win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT
            | win32pipe.PIPE_REJECT_REMOTE_CLIENTS,
            1, RECEIVE_PIPE_BUFFER_BYTES, RECEIVE_PIPE_BUFFER_BYTES, 0, None,
        )
        self._lock = threading.Lock()
        self._closed = threading.Event()

    def _overlapped(self):
        operation = self._types.OVERLAPPED()
        operation.hEvent = self._event.CreateEvent(None, True, False, None)
        return operation

    def _cancel_io(self):
        import ctypes
        cancel = ctypes.WinDLL("kernel32", use_last_error=True).CancelIoEx
        cancel.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        cancel.restype = ctypes.c_int
        cancel(int(self._handle), None)

    def _finish_operation(self, operation, timeout, process=None):
        deadline = time.monotonic() + timeout
        while self._event.WaitForSingleObject(operation.hEvent, 50) == self._event.WAIT_TIMEOUT:
            if self._closed.is_set() or time.monotonic() >= deadline or (process is not None and process.poll() is not None):
                self._cancel_io()
                # Do not release a pending operation's read buffer before cancellation completes.
                try:
                    self._file.GetOverlappedResult(self._handle, operation, True)
                except self._types.error:
                    pass
                raise OSError("Binary receive pipe operation was cancelled or timed out")
        return self._file.GetOverlappedResult(self._handle, operation, False)

    def connect(self, process, timeout=3.0):
        import win32pipe
        with self._lock:
            operation = self._overlapped()
            try:
                try:
                    win32pipe.ConnectNamedPipe(self._handle, operation)
                except self._types.error as exc:
                    if exc.winerror == 535:
                        return
                    if exc.winerror != 997:
                        raise
                self._finish_operation(operation, timeout, process)
            except self._types.error as exc:
                raise OSError("Binary receive pipe connection failed") from exc
            finally:
                operation.hEvent.Close()

    def read(self, count):
        with self._lock:
            if self._closed.is_set():
                return b""
            operation = self._overlapped()
            buffer = self._file.AllocateReadBuffer(count)
            try:
                try:
                    self._file.ReadFile(self._handle, buffer, operation)
                    received = self._finish_operation(operation, 5.0)
                except self._types.error as exc:
                    if exc.winerror in {109, 232}:
                        return b""
                    raise
                return bytes(buffer[:received])
            finally:
                operation.hEvent.Close()

    def close(self):
        if self._closed.is_set():
            return
        self._closed.set()
        try:
            self._cancel_io()
        except self._types.error:
            pass
        with self._lock:
            self._handle.Close()
