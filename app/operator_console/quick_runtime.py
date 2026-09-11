"""Background workers and immutable presentation metadata for Qt Quick."""

from __future__ import annotations

import threading
import time
from typing import Callable

import numpy as np
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from algorithms.p0.coarse_detection import CoarseSpectrumDetector
from algorithms.spectrum import SpectrumConfig, SpectrumProcessor
from platforms.acquisition import AcquisitionError, decode_ci8

from .live_ed import LiveEDPreview, LiveEDSession


ERROR_TEXT = {
    "invalid_sigmf_contract": "SigMF sözleşmesi geçerli değil.",
    "source_open_failed": "Kayıt açılamadı.",
    "processing_failed": "İşleme tamamlanamadı.",
    "tools_unavailable": "Alıcı yazılımı bulunamadı.",
    "device_not_found": "Yapılandırılmış alıcı bulunamadı. USB bağlantısını denetleyin.",
    "device_serial_unassigned": "Alıcı seri kimliği yapılandırılmamış.",
    "configured_serial_not_found": "Yapılandırılmış alıcı bağlı cihazlar arasında bulunamadı.",
    "receiver_and_fpga_unavailable": "Alıcı ve FPGA bağlantısı kurulamadı. USB ve FPGA ağ bağlantılarını denetleyin.",
    "operation_timeout": "Donanım yanıt süresi aşıldı.",
    "operation_cancelled": "İşlem durduruldu.",
    "connection_failed": "FPGA hizmetine bağlanılamadı.",
    "dma_status": "FPGA DMA durumu doğrulanamadı.",
    "candidate_drop": "FPGA olay zincirinde aday düşürüldü.",
    "usb_overrun": "Alıcı USB akışında tampon taşması oluştu.",
    "iq_saturation": "Canlı I/Q akışında kırpılan örnek oluştu; alıcı kazançlarını azaltın.",
    "rx_level_low": "Alım seviyesi düşük. Otomatik kazanç ayarını açın veya alıcı kazancını artırın.",
    "rx_gain_unresolved": "Otomatik ayarda uygun seviye bulunamadı. Anten konumunu veya verici gücünü değiştirin; elle kazanç da seçebilirsiniz.",
    "stream_integrity": "Alıcı veri bütünlüğü doğrulanamadı.",
    "transport_integrity": "FPGA taşıma bütünlüğü doğrulanamadı.",
    "survey_reference_required": "TX açık karşılaştırma için aynı ayarlarda tamamlanmış TX kapalı referans gerekir.",
    "live_queue_timeout": "Canlı veri zinciri zamanında çıktı üretmedi. Taramayı yeniden başlatın.",
    "live_capture_timeout": "Alıcı bağlı, ancak canlı örnek akışı başlatılamadı. Taramayı yeniden başlatın; tekrar ederse USB veri yolunu denetleyin.",
    "live_channelizer_timeout": "Alıcı verisi alındı, ancak sinyal işleme zamanında çıktı üretmedi. Taramayı yeniden başlatın.",
    "insufficient_iq": "Dinleme için kaynakta yeterli kesintisiz I/Q örneği yok.",
    "insufficient_audio": "Seçili kanaldan kullanılabilir ses üretilemedi.",
    "invalid_channel_bandwidth": "Kanal bant genişliği kaynak sınırlarıyla uyumlu değil.",
    "nyquist_limit": "Seçili kanal kaynak Nyquist sınırını aşıyor.",
    "invalid_volume": "Ses düzeyi 0 ile 100 arasında olmalıdır.",
    "wav_write_failed": "WAV dosyası kaydedilemedi.",
}

ERROR_TITLE = {
    "tools_unavailable": "Alıcı yazılımı bulunamadı",
    "device_not_found": "Alıcı bağlı değil",
    "device_serial_unassigned": "Alıcı yapılandırması eksik",
    "configured_serial_not_found": "Yapılandırılmış alıcı bağlı değil",
    "receiver_and_fpga_unavailable": "Alıcı ve FPGA bağlı değil",
    "operation_timeout": "Donanım yanıt vermedi",
    "connection_failed": "FPGA bağlantısı kurulamadı",
    "dma_status": "FPGA veri yolu hazır değil",
    "usb_overrun": "USB veri akışı taştı",
    "iq_saturation": "Alımda kırpılma algılandı",
    "rx_level_low": "Alım seviyesi çok düşük",
    "rx_gain_unresolved": "Alıcı seviyesi ayarlanamadı",
    "stream_integrity": "Alıcı verisi doğrulanamadı",
    "transport_integrity": "FPGA verisi doğrulanamadı",
    "live_queue_timeout": "Canlı veri gecikti",
    "live_capture_timeout": "Canlı alım başlamadı",
    "live_channelizer_timeout": "Sinyal işleme gecikti",
}


# The detailed spectrum remains near 30 Hz. Wide coarse decisions need less
# temporal density; four display periods preserve sub-second confirmation while
# leaving USB capture and GUI painting with deterministic headroom.
LIVE_COARSE_INTERVAL_DSP_FRAMES = 64


def _reduce_display_max(values: np.ndarray, width: int) -> np.ndarray:
    """Preserve every display interval's maximum without a Python loop."""
    bounded_width = max(1, min(int(width), int(values.size)))
    edges = np.linspace(0, values.size, bounded_width + 1, dtype=np.int64)
    return np.maximum.reduceat(values, edges[:-1])


PIPELINE_COMPONENTS = (
    {
        "id": "source",
        "name": "I/Q Kaynağı",
        "runtime": "HOST",
        "implementation": "Python",
        "description": "Canlı alıcı verisini doğrular ve sınırlı RX akışını işleme zincirine bağlar.",
        "hostPath": "algorithms/spectrum/source.py",
        "rtlPath": "",
    },
    {
        "id": "preprocess",
        "name": "Ön İşleme",
        "runtime": "HOST",
        "implementation": "Python · SystemVerilog karşılığı",
        "description": "Kareleme ve periyodik Hann penceresini doğrulanmış spektrum sözleşmesiyle uygular.",
        "hostPath": "algorithms/spectrum/dsp.py",
        "rtlPath": "algorithms/fpga/phase06b/rtl/axis_hann_window.sv",
    },
    {
        "id": "fft_power",
        "name": "FFT ve Lineer Güç",
        "runtime": "HOST",
        "implementation": "Python · SystemVerilog karşılığı",
        "description": "4096 nokta FFT ve güç hesabını yürütür; PL uygulaması donanım kabulü değildir.",
        "hostPath": "algorithms/spectrum/dsp.py",
        "rtlPath": "algorithms/fpga/phase06f/rtl/axis_fft_linear_power.sv",
    },
    {
        "id": "regional",
        "name": "Bölgesel Eşik",
        "runtime": "HOST",
        "implementation": "Python · SystemVerilog karşılığı",
        "description": "Doğrulanmış Bölgesel Eşik profiliyle kaba spektral adayları üretir.",
        "hostPath": "algorithms/detection/pipeline.py",
        "rtlPath": "algorithms/fpga/phase06g/rtl/axis_regional_detector.sv",
    },
    {
        "id": "temporal",
        "name": "Zamansal Doğrulama",
        "runtime": "HOST",
        "implementation": "Python · taşınabilir C karşılığı",
        "description": "Adayları kareler arasında ilişkilendirir ve 2/3 gözlem kuralıyla tespiti doğrular.",
        "hostPath": "algorithms/detection/pipeline.py",
        "rtlPath": "platforms/embedded/phase06j/src/phase06j_temporal.c",
    },
    {
        "id": "parameters",
        "name": "Parametre Ölçümü",
        "runtime": "HOST",
        "implementation": "Python",
        "description": "Operatör onaylı analiz aralığında yalnız doğrulanmış parametre alanlarını ölçer.",
        "hostPath": "algorithms/parameters/f5_estimator.py",
        "rtlPath": "",
    },
    {
        "id": "monitoring",
        "name": "Analog Dinleme",
        "runtime": "HOST",
        "implementation": "Python",
        "description": "Operatör seçimli AM/NFM kanalını 48 kHz mono PCM16 ses zincirine dönüştürür.",
        "hostPath": "algorithms/monitoring/dsp.py",
        "rtlPath": "",
    },
)


LIVE_PIPELINE_DETAILS = {
    "source": {
        "description": "Alımı 8 MS/s hızında alır; kanal seçici 2 MS/s CI8 karelerini Ethernet üzerinden karta gönderir.",
        "hostPath": "app/operator_console/live_ed.py",
    },
    "preprocess": {
        "runtime": "FPGA",
        "implementation": "SystemVerilog",
        "description": "Bilgisayarda karelenen CI8 örneklerine PL üzerinde sabit noktalı periyodik Hann penceresi uygular.",
    },
    "fft_power": {
        "runtime": "FPGA",
        "implementation": "AMD FFT IP · SystemVerilog",
        "description": "PL üzerinde 4096 nokta FFT ve lineer güç hesabını yürütür. Ekran spektrumu aynı I/Q karesinden bilgisayarda ayrıca hesaplanır.",
    },
    "regional": {
        "name": "OS-CFAR ve Aday Gruplama",
        "runtime": "FPGA",
        "implementation": "SystemVerilog",
        "description": "PL, OS-CFAR hücre kararlarını üretir. ARM CPU1 dar adayları gruplar ve sekiz karelik geniş bant enerjisini değerlendirir.",
        "hostPath": "platforms/embedded/p0/src/p0_ed_pipeline.c",
        "rtlPath": "algorithms/fpga/p0/rtl/axis_p0_os_cfar.sv",
    },
    "temporal": {
        "runtime": "ZYNQ PS",
        "implementation": "Taşınabilir C",
        "description": "ARM CPU0 DMA güç çıktısını doğrular ve çözer; CPU1 adaylara 2/3 gözlem kuralını uygular. Hizmet olayları ABI v3 yanıtıyla bilgisayara iletir.",
        "rtlPath": "platforms/embedded/p0/src/p0_ed_pipeline.c",
    },
}


class _TaskSignals(QObject):
    completed = Signal(int, str, object, float)
    failed = Signal(int, str, str)


class _Task(QRunnable):
    """Run one bounded operation outside the GUI thread."""

    def __init__(self, generation: int, kind: str, operation: Callable[[], object]) -> None:
        super().__init__()
        self.generation = generation
        self.kind = kind
        self.operation = operation
        self.signals = _TaskSignals()

    @Slot()
    def run(self) -> None:
        started = time.perf_counter()
        try:
            result = self.operation()
        except Exception as exc:
            code = str(getattr(exc, "code", f"{self.kind}_failed"))
            self.signals.failed.emit(self.generation, code, type(exc).__name__)
            return
        self.signals.completed.emit(
            self.generation,
            self.kind,
            result,
            time.perf_counter() - started,
        )


class _LiveTaskSignals(QObject):
    snapshot = Signal(int, object)
    preview = Signal(int, object)
    coarse = Signal(int, object)
    coarseFailed = Signal(int, str)
    completed = Signal(int, object, float)
    failed = Signal(int, str, str)


class _LiveMailbox:
    """At most one queued GUI notification; supersede display snapshots only."""

    def __init__(self):
        self._lock = threading.Lock()
        self._latest = None
        self._pending = False

    def publish(self, snapshot):
        with self._lock:
            self._latest = snapshot
            notify = not self._pending
            self._pending = True
            return notify

    def take(self):
        with self._lock:
            snapshot, self._latest = self._latest, None
            self._pending = False
            return snapshot


class _LatestWorkMailbox:
    """Non-blocking latest-only input for expendable display work."""

    def __init__(self):
        self._condition = threading.Condition()
        self._latest = None
        self._closed = False

    def publish(self, item) -> bool:
        with self._condition:
            if self._closed:
                return False
            self._latest = item
            self._condition.notify()
            return True

    def take(self):
        with self._condition:
            self._condition.wait_for(lambda: self._latest is not None or self._closed)
            if self._latest is None:
                return None
            item, self._latest = self._latest, None
            return item

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()


class _LiveTask(QRunnable):
    """Run one bounded physical HackRF-to-FPGA session outside the GUI thread."""

    def __init__(self, generation: int, session: LiveEDSession) -> None:
        super().__init__()
        self.generation = generation
        self.session = session
        self.signals = _LiveTaskSignals()
        self.mailbox = _LiveMailbox()
        self.preview_mailbox = _LiveMailbox()
        self.coarse_mailbox = _LiveMailbox()
        self.preview_input = _LatestWorkMailbox()
        self.preview_errors: list[Exception] = []
        self._coarse_disabled = False
        self._last_coarse_queued_sequence = -LIVE_COARSE_INTERVAL_DSP_FRAMES
        self.processor = SpectrumProcessor()
        self.wide_processor = SpectrumProcessor(SpectrumConfig(frame_length=16_384))
        self.display_processor = self.wide_processor
        self.coarse_detector = CoarseSpectrumDetector()
        self.independent_preview = hasattr(session, "set_preview_handler")
        if self.independent_preview:
            session.set_preview_handler(self._queue_preview)

    def _queue_preview(self, preview) -> None:
        # The RX/channelizer thread must never wait for an FFT or GUI paint.
        self.preview_input.publish(preview)

    def _process_preview(self, preview) -> None:
        started = time.perf_counter()
        frame = preview.display_frame or preview.output_frame
        processor = self.wide_processor if frame.sample_rate_hz == 8_000_000 else self.processor
        spectrum = processor.process(
            decode_ci8(frame.payload, expected_complex_samples=processor.config.frame_length),
            sample_rate_hz=frame.sample_rate_hz,
            center_frequency_hz=frame.center_frequency_hz,
        )
        display_spectrum = spectrum
        if frame.sample_rate_hz == 8_000_000 and self.display_processor is not self.wide_processor:
            count = self.display_processor.config.frame_length
            # Real contiguous samples from this frame; no padding or joining dropped previews.
            display_spectrum = self.display_processor.process(
                decode_ci8(frame.payload[:count * 2], expected_complex_samples=count),
                sample_rate_hz=frame.sample_rate_hz,
                center_frequency_hz=frame.center_frequency_hz,
            )
        prepared = (preview, spectrum, display_spectrum, (time.perf_counter() - started) * 1000)
        if self.preview_mailbox.publish(prepared):
            self.signals.preview.emit(self.generation, self.preview_mailbox)
        if (
            not self._coarse_disabled
            and frame.sample_rate_hz == 8_000_000
            and getattr(spectrum, "frame_length", 0) == 16_384
            and preview.sequence_number - self._last_coarse_queued_sequence
            >= LIVE_COARSE_INTERVAL_DSP_FRAMES
        ):
            self._last_coarse_queued_sequence = preview.sequence_number
            try:
                coarse = self.coarse_detector.process(
                    spectrum.display.bin_power_fs2,
                    center_frequency_hz=spectrum.center_frequency_hz,
                    sample_rate_hz=spectrum.sample_rate_hz,
                    sequence_number=preview.sequence_number,
                )
            except Exception as exc:
                self._coarse_disabled = True
                self.signals.coarseFailed.emit(self.generation, type(exc).__name__)
            else:
                if self.coarse_mailbox.publish((preview.sequence_number, coarse)):
                    self.signals.coarse.emit(self.generation, self.coarse_mailbox)

    def _process_previews(self) -> None:
        try:
            while (preview := self.preview_input.take()) is not None:
                self._process_preview(preview)
        except Exception as exc:
            self.preview_errors.append(exc)
            self.preview_input.close()
            self.session.cancel()

    def _publish(self, snapshot):
        if not self.independent_preview:
            self._queue_preview(
                LiveEDPreview(snapshot.sequence_number, snapshot.output_frame, time.perf_counter())
            )
        if self.mailbox.publish((snapshot, time.perf_counter())):
            self.signals.snapshot.emit(self.generation, self.mailbox)

    @Slot()
    def run(self) -> None:
        started = time.perf_counter()
        preview_worker = threading.Thread(
            target=self._process_previews,
            name="live-spectrum-preview",
            daemon=True,
        )
        preview_worker.start()
        result = None
        session_error: Exception | None = None
        try:
            result = self.session.run(self._publish)
        except Exception as exc:
            session_error = exc
        finally:
            self.preview_input.close()
            preview_worker.join(timeout=5.0)
        if preview_worker.is_alive():
            session_error = AcquisitionError(
                "processing_failed",
                "Canlı spektrum önizleme işçisi süresinde kapanmadı.",
            )
        error = self.preview_errors[0] if self.preview_errors else session_error
        if error is not None:
            code = str(getattr(error, "code", "live_session_failed"))
            self.signals.failed.emit(self.generation, code, type(error).__name__)
            return
        assert result is not None
        self.signals.completed.emit(self.generation, result, time.perf_counter() - started)
