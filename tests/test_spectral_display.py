"""Signal visibility, stable intensity, bounded history and GUI backpressure."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import threading
import time
from types import SimpleNamespace

import numpy as np
from PySide6.QtGui import QGuiApplication, QImage, QPainter

from algorithms.p0 import IQFrame
from app.operator_console.live_ed import LiveEDPreview
from app.operator_console.spectral_display import (
    HISTORY_ROWS, MAX_BINS, SpectralDisplay, WaterfallImage, peak_projection,
)
from app.operator_console.quick_view_model import _LatestWorkMailbox, _LiveMailbox, _LiveTask


def test_projection_keeps_single_bin_peaks_at_every_position_and_zoom():
    for start, end in ((0, 1), (.3, .37), (.99, 1)):
        for index in range(int(start * 4096), int(end * 4096), 7):
            data = np.full(4096, -100.)
            data[index] = -20
            _, projected = peak_projection(data, start, end, 37)
            assert projected.max() == -20


def test_scale_does_not_hide_peak_or_change_on_new_frames():
    display = SpectralDisplay()
    data = np.full(4096, -200.)
    data[2400] = -2
    display.append(data, timestamp=0, binding=(1, 100e6, 2e6))
    assert display.floorDb + display.spanDb > -2
    levels = display.floorDb, display.spanDb
    display.append(np.full(4096, -50.), timestamp=.1, binding=(1, 100e6, 2e6))
    assert (display.floorDb, display.spanDb) == levels


def test_history_wrap_is_bounded_and_tuning_clears_old_frequencies():
    display = SpectralDisplay()
    for index in range(HISTORY_ROWS + 17):
        display.append(np.full(4096, -index), timestamp=index / 30, binding=(1, 100e6, 2e6))
    assert display.count == HISTORY_ROWS
    assert display.rows.nbytes == HISTORY_ROWS * MAX_BINS * 4
    assert display.times[(display.head - display.count) % HISTORY_ROWS] == 17 / 30
    display.append(np.full(4096, -80), timestamp=0, binding=(1, 101e6, 2e6))
    assert display.count == 1
    assert display.times[(display.head - 1) % HISTORY_ROWS] == 0


def test_native_waterfall_pixels_update_and_keep_old_intensity():
    app = QGuiApplication.instance() or QGuiApplication([])
    display, item = SpectralDisplay(), WaterfallImage()
    item.setWidth(450)
    item.setHeight(256)
    item.source = display
    display.setLevels(-100, 80)
    display.append(np.full(4096, -90.), timestamp=0, binding=(1, 100e6, 2e6))
    display.setLevels(-100, 80)

    def draw():
        image = QImage(450, 256, QImage.Format.Format_RGB32)
        painter = QPainter(image)
        item.paint(painter)
        painter.end()
        return image

    before = draw()
    display.append(np.full(4096, -30.), timestamp=.032768, binding=(1, 100e6, 2e6))
    after = draw()
    assert before.pixelColor(200, 255) != after.pixelColor(200, 255)
    assert before.pixelColor(200, 255) == after.pixelColor(200, 253)
    item.viewStart = .2
    item.viewEnd = .4
    zoomed = draw()
    assert zoomed.pixelColor(200, 255) == after.pixelColor(200, 255)
    item.source = None
    app.processEvents()


def test_gui_mailbox_keeps_one_notification_and_latest_snapshot():
    mailbox = _LiveMailbox()
    notifications = sum(mailbox.publish(index) for index in range(10000))
    assert notifications == 1
    assert mailbox.take() == 9999
    assert mailbox.publish(10000)
    assert mailbox.take() == 10000


def test_preview_work_mailbox_never_backpressures_rx_and_discards_stale_work():
    mailbox = _LatestWorkMailbox()
    for index in range(10_000):
        assert mailbox.publish(index)
    mailbox.close()
    assert mailbox.take() == 9_999
    assert mailbox.take() is None
    assert not mailbox.publish(10_000)


def test_slow_preview_fft_does_not_block_the_receive_callback():
    callbacks_done = threading.Event()
    fft_started = threading.Event()
    release_fft = threading.Event()

    class Session:
        def set_preview_handler(self, handler):
            self.handler = handler

        def run(self, snapshot_handler):
            del snapshot_handler
            frame = IQFrame(0, 8_000_000, 100_000_000, bytes(32_768), frame_id=0)
            for sequence in range(100):
                self.handler(LiveEDPreview(sequence, frame, time.perf_counter(), frame))
            callbacks_done.set()
            return object()

        def cancel(self):
            raise AssertionError("Geçerli önizleme RX oturumunu iptal etmemeli.")

    class SlowProcessor:
        class Config:
            frame_length = 16_384

        config = Config()
        calls = 0

        def process(self, *args, **kwargs):
            del args, kwargs
            self.calls += 1
            fft_started.set()
            assert release_fft.wait(2)
            return object()

    task = _LiveTask(1, Session())
    processor = SlowProcessor()
    task.wide_processor = processor
    worker = threading.Thread(target=task.run)
    worker.start()
    assert callbacks_done.wait(.5)
    assert fft_started.wait(.5)
    assert worker.is_alive()
    release_fft.set()
    worker.join(2)
    assert not worker.is_alive()
    assert processor.calls <= 2


def test_wide_coarse_detection_runs_after_spectrum_publish_and_is_throttled():
    class Processor:
        config = SimpleNamespace(frame_length=16_384)

        def process(self, *args, **kwargs):
            del args, kwargs
            return SimpleNamespace(
                frame_length=16_384,
                display=SimpleNamespace(bin_power_fs2=np.ones(16_384)),
                center_frequency_hz=100_000_000,
                sample_rate_hz=8_000_000,
            )

    class Detector:
        calls = 0

        def process(self, *args, **kwargs):
            del args, kwargs
            self.calls += 1
            assert task.preview_mailbox._pending
            return object()

    task = _LiveTask(1, object())
    task.wide_processor = Processor()
    task.coarse_detector = Detector()
    frame = IQFrame(0, 8_000_000, 100_000_000, bytes(32_768), frame_id=0)

    task._process_preview(LiveEDPreview(17, frame, time.perf_counter(), frame))

    preview, spectrum, display_spectrum, processing_ms = task.preview_mailbox.take()
    sequence_number, coarse = task.coarse_mailbox.take()
    assert preview.sequence_number == sequence_number == 17
    assert coarse is not None
    assert spectrum.frame_length == display_spectrum.frame_length == 16_384
    assert processing_ms >= 0

    task._process_preview(LiveEDPreview(33, frame, time.perf_counter(), frame))
    assert task.coarse_detector.calls == 1
    assert task.coarse_mailbox.take() is None


def test_peak_hold_does_not_change_instantaneous_samples():
    display = SpectralDisplay()
    first = np.full(4096, -80.)
    first[2000] = -20
    display.append(first, timestamp=0, binding=(1, 100e6, 2e6))
    display.setPeakHold(True)
    display.append(np.full(4096, -80.), timestamp=.1, binding=(1, 100e6, 2e6))
    assert display.latest[2000] == -80
    assert display.peak[2000] == -20
    display.setPeakHold(False)
    assert display.peak[2000] == -80


def test_wide_receive_spectrum_accepts_all_16384_bins_without_losing_a_narrow_peak():
    display = SpectralDisplay()
    wide = np.full(MAX_BINS, -100.0)
    wide[12_345] = -10.0
    display.append(wide, timestamp=0, binding=(1, 103_150_000, 8_000_000))
    _, projected = peak_projection(display.latest, 0, 1, 900)
    assert display.latest.size == MAX_BINS
    assert projected.max() == -10.0
