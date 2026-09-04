"""Bounded presentation of actual spectra, independent of detection decisions."""

from __future__ import annotations

import math
import time

import numpy as np
from PySide6.QtCore import QObject, Property, QRectF, Signal, Slot
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtQuick import QQuickPaintedItem
from pyqtgraph.functions import arrayToQPolygonF


HISTORY_ROWS = 128
MAX_BINS = 16_384


def peak_projection(values: np.ndarray, start: float, end: float, width: int):
    """Pool *all* visible bins; a narrow peak cannot fall between samples."""
    size = values.shape[-1]
    first = max(0, min(size - 1, math.floor(start * size)))
    stop = max(first + 1, min(size, math.ceil(end * size)))
    count = max(1, min(int(width), stop - first))
    edges = np.linspace(first, stop, count + 1, dtype=np.int64)
    projected = np.maximum.reduceat(values[..., first:stop], edges[:-1] - first, axis=-1)
    positions = (edges[:-1] + edges[1:] - 1) / (2 * size)
    return positions, projected


class SpectralDisplay(QObject):
    frameChanged = Signal()
    levelsChanged = Signal()
    resetOccurred = Signal()
    statisticsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = np.full((HISTORY_ROWS, MAX_BINS), -200, dtype=np.float32)
        self.times = np.zeros(HISTORY_ROWS)
        self.latest = np.empty(0, dtype=np.float32)
        self.peak = np.empty(0, dtype=np.float32)
        self.count = self.head = 0
        self.binding = None
        self._floor, self._span = -100.0, 60.0
        self._auto_pending = True
        self._last_statistics = time.perf_counter()
        self._updates = 0
        self._rate = 0.0
        self._held = False

    @Property(float, notify=levelsChanged)
    def floorDb(self):
        return self._floor

    @Property(float, notify=levelsChanged)
    def spanDb(self):
        return self._span

    @Property(str, notify=statisticsChanged)
    def historyText(self):
        if not self.count:
            return "Geçmiş bekleniyor"
        oldest = (self.head - self.count) % HISTORY_ROWS
        newest = (self.head - 1) % HISTORY_ROWS
        span = max(0, self.times[newest] - self.times[oldest])
        duration = f"{span * 1000:.1f} ms" if span < 1 else f"{span:.2f} s"
        return f"{duration} · {self.count} görüntü satırı"

    @Property(str, notify=statisticsChanged)
    def rateText(self):
        return f"Görüntü verisi {self._rate:.1f} Hz"

    @Property(bool, notify=levelsChanged)
    def peakHold(self):
        return self._held

    @Slot(bool)
    def setPeakHold(self, enabled):
        self._held = bool(enabled)
        self.peak = self.latest.copy()
        self.levelsChanged.emit()

    @Slot(float, float)
    def setLevels(self, floor, span):
        if not math.isfinite(floor) or not math.isfinite(span):
            return
        self._floor = max(-200.0, min(0.0, float(floor)))
        self._span = max(20.0, min(120.0, float(span)))
        self._auto_pending = False
        self.levelsChanged.emit()

    @Slot()
    def fitLevels(self):
        if self.latest.size and np.ptp(self.latest) > .01:
            # One-shot fit, never a per-frame remapping of past RF power.
            noise = float(np.percentile(self.latest, 20))
            upper = max(noise + 32, float(self.latest.max()) + 6)
            lower = max(noise - 8, upper - 90)
            self.setLevels(lower, upper - lower)

    def clear(self):
        self.count = self.head = 0
        self.latest = np.empty(0, dtype=np.float32)
        self.peak = self.latest.copy()
        self.binding = None
        self._auto_pending = True
        self._rate = 0.0
        self._updates = 0
        self._last_statistics = time.perf_counter()
        self.resetOccurred.emit()
        self.statisticsChanged.emit()

    def append(self, values, *, timestamp: float, binding: tuple):
        row = np.asarray(values, dtype=np.float32)
        if row.ndim != 1 or not 2 <= row.size <= MAX_BINS or not np.all(np.isfinite(row)):
            raise ValueError("Görünüm sonlu ve sınırlı bir güç spektrumu gerektirir.")
        if not math.isfinite(timestamp):
            raise ValueError("Görünüm zaman bilgisi geçersiz.")
        if self.binding != binding or self.latest.size != row.size:
            self.clear()
            self.binding = binding
        self.latest = row.copy()
        self.peak = np.maximum(self.peak, row) if self._held and self.peak.size else row.copy()
        slot = self.head % HISTORY_ROWS
        self.rows[slot, :row.size] = row
        self.times[slot] = timestamp
        self.head += 1
        self.count = min(HISTORY_ROWS, self.count + 1)
        if self._auto_pending:
            self.fitLevels()
        self.frameChanged.emit()
        self._updates += 1
        elapsed = time.perf_counter() - self._last_statistics
        if elapsed >= .5:
            self._rate = self._updates / elapsed
            self._updates = 0
            self._last_statistics = time.perf_counter()
            self.statisticsChanged.emit()


class SpectralItem(QQuickPaintedItem):
    sourceChanged = Signal()
    viewChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = None
        self._start, self._end = 0.0, 1.0
        self.setAntialiasing(False)
        self.widthChanged.connect(self.invalidate)
        self.heightChanged.connect(self.update)
        self.visibleChanged.connect(self.invalidate)

    @Property(QObject, notify=sourceChanged)
    def source(self):
        return self._source

    @source.setter
    def source(self, source):
        if self._source is source:
            return
        if self._source is not None:
            self._source.frameChanged.disconnect(self.new_frame)
            self._source.levelsChanged.disconnect(self.invalidate)
            self._source.resetOccurred.disconnect(self.invalidate)
        self._source = source
        if source is not None:
            source.frameChanged.connect(self.new_frame)
            source.levelsChanged.connect(self.invalidate)
            source.resetOccurred.connect(self.invalidate)
        self.invalidate()
        self.sourceChanged.emit()

    @Property(float, notify=viewChanged)
    def viewStart(self):
        return self._start

    @viewStart.setter
    def viewStart(self, value):
        self._start = max(0.0, min(.999, float(value)))
        self.invalidate()
        self.viewChanged.emit()

    @Property(float, notify=viewChanged)
    def viewEnd(self):
        return self._end

    @viewEnd.setter
    def viewEnd(self, value):
        self._end = max(.001, min(1.0, float(value)))
        self.invalidate()
        self.viewChanged.emit()

    @Slot()
    def new_frame(self):
        if self.isVisible():
            self.update()

    @Slot()
    def invalidate(self):
        self.update()


class SpectrumTrace(SpectralItem):
    """Native polyline; the QML layer retains axes, markers and mouse controls."""

    def paint(self, painter):
        painter.fillRect(self.boundingRect(), QColor("#1F1F1F"))
        source = self._source
        if source is None or not source.latest.size or self._end <= self._start:
            return
        area = QRectF(0, 8, max(1, self.width() - 8), max(1, self.height() - 26))
        painter.setClipRect(area)
        # A cosmetic one-pixel pen uses Qt's fast raster path even at high DPI.
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        for values, color in ((source.peak, "#CE9178"), (source.latest, "#569CD6")):
            if values is source.peak and not source.peakHold:
                continue
            positions, levels = peak_projection(values, self._start, self._end, int(area.width()))
            xs = area.left() + (positions - self._start) * area.width() / (self._end - self._start)
            ys = area.bottom() - np.clip((levels - source.floorDb) / source.spanDb, 0, 1) * area.height()
            points = arrayToQPolygonF(xs, ys)
            pen = QPen(QColor(color), 1.0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawPolyline(points)


class WaterfallImage(SpectralItem):
    """One vectorized row update, two wrapped image blits, no JS cell loop."""

    rowsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        anchors = np.asarray([[4, 10, 15], [12, 31, 83], [25, 87, 151],
                              [26, 167, 183], [115, 219, 153], [251, 219, 97], [255, 251, 221]])
        table = np.column_stack([np.interp(np.linspace(0, 6, 256), np.arange(7), anchors[:, c])
                                 for c in range(3)]).astype(np.uint32)
        self._palette = (0xff000000 | table[:, 0] << 16 | table[:, 1] << 8 | table[:, 2]).tolist()
        self._pixels = np.zeros((HISTORY_ROWS, 1), dtype=np.uint8)
        self._image = QImage()
        self._dirty = True
        self._visible_rows = HISTORY_ROWS

    @Property(int, notify=rowsChanged)
    def visibleRows(self):
        return self._visible_rows

    @visibleRows.setter
    def visibleRows(self, value):
        self._visible_rows = max(1, min(HISTORY_ROWS, int(value)))
        self.update()
        self.rowsChanged.emit()

    def invalidate(self):
        self._dirty = True
        self.update()

    def new_frame(self):
        if not self.isVisible():
            self._dirty = True
            return
        source = self._source
        if source is not None and source.latest.size and not self._dirty and self._end > self._start:
            _, values = peak_projection(source.latest, self._start, self._end, self._pixels.shape[1])
            if values.size == self._pixels.shape[1]:
                self._pixels[(source.head - 1) % HISTORY_ROWS] = self._color_indices(values)
            else:
                self._dirty = True
        self.update()

    def _color_indices(self, values):
        source = self._source
        return np.rint(np.clip((values - source.floorDb) / source.spanDb, 0, 1) * 255).astype(np.uint8)

    def paint(self, painter):
        painter.fillRect(self.boundingRect(), QColor("#1F1F1F"))
        source = self._source
        if source is None or not source.count or self._end <= self._start:
            return
        area = QRectF(0, 0, max(1, self.width() - 8), self.height())
        if self._dirty:
            _, values = peak_projection(source.rows[:, :source.latest.size], self._start,
                                        self._end, int(area.width()))
            self._pixels = np.ascontiguousarray(self._color_indices(values))
            self._image = QImage(self._pixels.data, self._pixels.shape[1], HISTORY_ROWS,
                                 self._pixels.strides[0], QImage.Format.Format_Indexed8)
            self._image.setColorTable(self._palette)
            self._dirty = False
        # Newest observations at the bottom. Unfilled history remains blank.
        count = min(source.count, self._visible_rows)
        oldest = (source.head - count) % HISTORY_ROWS
        first_count = min(count, HISTORY_ROWS - oldest)
        row_height = area.height() / self._visible_rows
        top = area.bottom() - count * row_height
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(QRectF(area.left(), top, area.width(), first_count * row_height),
                          self._image, QRectF(0, oldest, self._image.width(), first_count))
        rest = count - first_count
        if rest:
            painter.drawImage(QRectF(area.left(), top + first_count * row_height, area.width(), rest * row_height),
                              self._image, QRectF(0, 0, self._image.width(), rest))
        # Actual sample-clock ages, not an invented FPS-derived time axis.
        painter.setPen(QColor("#9D9D9D"))
        font = QFont("Consolas")
        font.setPixelSize(9)
        painter.setFont(font)
        newest_time = source.times[(source.head - 1) % HISTORY_ROWS]
        for offset in sorted({0, count // 2, count - 1}):
            slot = (source.head - 1 - offset) % HISTORY_ROWS
            age = max(0, newest_time - source.times[slot])
            y = max(12, min(self.height() - 3, self.height() - (offset + .5) * row_height))
            label = f"−{age * 1000:.0f}ms" if age < 1 else f"−{age:.1f}s"
            painter.drawText(QRectF(0, y - 10, 38, 14), label)
