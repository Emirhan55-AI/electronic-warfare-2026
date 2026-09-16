"""Background workers and immutable presentation metadata for Qt Quick."""

from __future__ import annotations

from dataclasses import replace
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
    "parameter_delivery_overflow": "Arayüz parametre kayıtlarını zamanında alamadı; alım durduruldu.",
    "invalid_sigmf_contract": "SigMF sözleşmesi geçerli değil.",
    "source_open_failed": "Kayıt açılamadı.",
    "processing_failed": "İşleme tamamlanamadı.",
    "tools_unavailable": "Alıcı algılanmadı",
    "device_not_found": "Alıcı algılanmadı",
    "device_serial_unassigned": "Alıcı algılanmadı",
    "configured_serial_not_found": "Alıcı algılanmadı",
    "portapack_control_not_found": "Alıcı HackRF USB modunda bulunamadı ve PortaPack USB denetim bağlantısına erişilemedi.",
    "portapack_control_ambiguous": "Birden fazla PortaPack USB denetim bağlantısı bulundu; güvenli seçim yapılamadı.",
    "portapack_serial_unavailable": "PortaPack USB denetim bileşeni kurulu değil; alıcı otomatik hazırlanamadı.",
    "portapack_mode_switch_failed": "PortaPack alıcıyı HackRF USB moduna geçiremedi.",
    "portapack_mode_timeout": "PortaPack komutu aldı ancak alıcı HackRF USB modu olarak yeniden bağlanmadı.",
    "receiver_connection_lost": "Alıcı HackRF USB modunda görünmüyor. Sistemi Denetle ile yeniden bağlanın.",
    "binary_pipe_failed": "Alıcı HackRF USB modunda görünmüyor. Sistemi Denetle ile yeniden bağlanın.",
    "receiver_and_fpga_unavailable": "FPGA ve Alıcı algılanamadı",
    "operation_timeout": "Donanım yanıt süresi aşıldı.",
    "operation_cancelled": "İşlem durduruldu.",
    "connection_failed": "FPGA algılanmadı",
    "dma_status": "FPGA DMA durumu doğrulanamadı.",
    "local_invalid_request": "FPGA etkin FFT ile gönderilen örnek boyutunu kabul etmedi. Karttan FFT ayarını yeniden okuyup alımı tekrar başlatın.",
    "local_dma_failure": "FPGA DMA işlemi tamamlanamadı. Karttan FFT ayarını yeniden okuyup alımı tekrar başlatın.",
    "local_pipeline_failure": "FPGA tespit işleme hattı sonucu tamamlayamadı. Alımı durdurup yeniden deneyin.",
    "local_internal_failure": "FPGA hizmetinde iç işlem hatası oluştu. Sistemi Denetle ile bağlantıları doğrulayın.",
    "local_service_failure": "FPGA hizmeti tanımsız bir hata döndürdü. Sistemi Denetle ile bağlantıları doğrulayın.",
    "candidate_drop": "FPGA tespit kapasitesi aşıldı; bazı adaylar güvenilir biçimde izlenemedi. Bu bağlantı hatası değildir. LNA/VGA kazançlarını azaltıp yeniden deneyin.",
    "usb_overrun": "Alıcı USB akışında tampon taşması oluştu.",
    "long_capture": "Alıcı ve görüntü işleme örnek boyları uyuşmadı. Alımı durdurup karttan FFT ayarını yeniden okuyun; tekrar ederse Sistemi Denetle ile bağlantıları doğrulayın.",
    "short_stream": "Alıcıdan beklenen veri tamamlanamadı. Bu, kablonun fiziksel olarak çıktığı anlamına gelmez; yüksek hızlı alım süreci erken sonlandı. Tekrar ederse HackRF’i doğrudan bir USB porta bağlayıp Sistemi Denetle ile yeniden deneyin.",
    "live_pipeline_short_stream": "Canlı alım işleme zinciri beklenen kare sayısını tamamlayamadı. Sistemi Denetle ile yeniden deneyin.",
    "fpga_short_stream": "FPGA beklenen yanıt sayısını tamamlayamadı. Sistemi Denetle ile bağlantıları yeniden denetleyin.",
    "iq_saturation": "Canlı I/Q akışında kırpılan örnek oluştu; alıcı kazançlarını azaltın.",
    "stream_integrity": "Alıcı veri bütünlüğü doğrulanamadı.",
    "transport_integrity": "FPGA taşıma bütünlüğü doğrulanamadı.",
    "survey_reference_required": "TX açık karşılaştırma için aynı ayarlarda tamamlanmış TX kapalı referans gerekir.",
    "live_queue_timeout": "Canlı veri zinciri zamanında çıktı üretmedi. Taramayı yeniden başlatın.",
    "live_capture_timeout": "Alıcı bağlı, ancak canlı örnek akışı başlatılamadı. Taramayı yeniden başlatın; tekrar ederse USB veri yolunu denetleyin.",
    "live_channelizer_timeout": "Alıcı verisi alındı, ancak sinyal işleme zamanında çıktı üretmedi. Taramayı yeniden başlatın.",
    "insufficient_iq": "Dinleme için kaynakta yeterli kesintisiz I/Q örneği yok.",
    "insufficient_audio": "Seçili kanaldan kullanılabilir ses üretilemedi.",
    "invalid_channel_bandwidth": "Analog ses için bant genişliğini 2–25 kHz arasında seçin.",
    "nyquist_limit": "Seçili kanal kaynak Nyquist sınırını aşıyor.",
    "invalid_volume": "Ses düzeyi 0 ile 100 arasında olmalıdır.",
    "wav_write_failed": "WAV dosyası kaydedilemedi.",
}

ERROR_TITLE = {
    "tools_unavailable": "Alıcı algılanmadı",
    "device_not_found": "Alıcı algılanmadı",
    "device_serial_unassigned": "Alıcı algılanmadı",
    "configured_serial_not_found": "Alıcı algılanmadı",
    "portapack_control_not_found": "Alıcı algılanmadı",
    "portapack_control_ambiguous": "Alıcı algılanmadı",
    "portapack_serial_unavailable": "Alıcı algılanmadı",
    "portapack_mode_switch_failed": "Alıcı algılanmadı",
    "portapack_mode_timeout": "Alıcı algılanmadı",
    "receiver_connection_lost": "Alıcı bağlantısı koptu",
    "binary_pipe_failed": "Alıcı bağlantısı koptu",
    "receiver_and_fpga_unavailable": "FPGA ve Alıcı algılanamadı",
    "operation_timeout": "Donanım yanıt vermedi",
    "connection_failed": "FPGA algılanmadı",
    "dma_status": "FPGA veri yolu hazır değil",
    "local_invalid_request": "FFT ayarı kartla uyuşmuyor",
    "local_dma_failure": "FFT ayarı kartla uyuşmuyor",
    "local_pipeline_failure": "FPGA tespiti tamamlanamadı",
    "local_internal_failure": "FPGA hizmeti hata verdi",
    "local_service_failure": "FPGA hizmeti hata verdi",
    "candidate_drop": "FPGA tespit kapasitesi aşıldı",
    "usb_overrun": "USB veri akışı taştı",
    "long_capture": "Alıcı veri boyu uyuşmadı",
    "short_stream": "Alıcı verisi eksik kaldı",
    "live_pipeline_short_stream": "Canlı işleme erken durdu",
    "fpga_short_stream": "FPGA yanıtları eksik kaldı",
    "iq_saturation": "Alımda kırpılma algılandı",
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


class _CatalogTaskSignals(QObject):
    completed = Signal(object)
    failed = Signal(int, str)


class _CatalogTask(QRunnable):
    """Persist one bounded parameter delivery without blocking the GUI thread."""

    def __init__(self, outcome_count: int, operation: Callable[[], object]) -> None:
        super().__init__()
        self.outcome_count = outcome_count
        self.operation = operation
        self.signals = _CatalogTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.operation()
        except Exception as exc:
            self.signals.failed.emit(self.outcome_count, str(exc))
            return
        self.signals.completed.emit((self.outcome_count, result))


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


class _LiveSnapshotMailbox(_LiveMailbox):
    """Coalesce display frames while preserving pending parameter observations."""

    maximum_outcomes = 1024

    def publish(self, item):
        snapshot, received_at = item
        with self._lock:
            previous = self._latest[0] if self._latest is not None else None
            outcomes = (
                previous.automatic_parameter_outcomes if previous is not None else ()
            ) + snapshot.automatic_parameter_outcomes
            if len(outcomes) > self.maximum_outcomes:
                raise AcquisitionError(
                    "parameter_delivery_overflow",
                    "Arayüz parametre kayıtlarını zamanında alamadı; alım durduruldu.",
                )
            self._latest = (
                replace(snapshot, automatic_parameter_outcomes=outcomes), received_at
            )
            notify = not self._pending
            self._pending = True
            return notify


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
        self.mailbox = _LiveSnapshotMailbox()
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
        sample_count = processor.config.frame_length
        # The FPGA FFT controls the channelizer frame size. At 8192/16384 the
        # associated raw 8 MS/s preview is larger than the fixed 16384-sample
        # presentation/coarse-detection window. Use a real contiguous prefix;
        # do not reject a valid larger capture or relabel it as an RX fault.
        preview_payload = frame.payload[:sample_count * 2]
        spectrum = processor.process(
            decode_ci8(preview_payload, expected_complex_samples=sample_count),
            sample_rate_hz=frame.sample_rate_hz,
            center_frequency_hz=frame.center_frequency_hz,
        )
        display_spectrum = spectrum
        if frame.sample_rate_hz == 8_000_000 and self.display_processor is not self.wide_processor:
            count = self.display_processor.config.frame_length
            # Real contiguous samples from this frame; no padding or joining dropped previews.
            display_spectrum = self.display_processor.process(
                decode_ci8(preview_payload[:count * 2], expected_complex_samples=count),
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
