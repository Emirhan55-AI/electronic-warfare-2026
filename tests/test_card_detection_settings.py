import os
import time
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtGui import QGuiApplication
from algorithms.p0.detection_config import DetectionProfile, DetectionConfigError
from app.operator_console.quick_view_model import OperatorViewModel


def test_read_apply_restore_and_busy_guards():
    app = QGuiApplication.instance() or QGuiApplication([])
    view = OperatorViewModel()
    actual = DetectionProfile(0,36851433755,17098572778)
    calls=[]
    def exchange(host, port, *, profile=None):
        nonlocal actual
        calls.append(profile)
        if profile is not None:
            assert profile.generation == actual.generation
            actual=DetectionProfile(actual.generation+1,profile.alpha_q32,
                                    profile.weak_alpha_q32,profile.fft_size,
                                    profile.runtime_fft_supported)
        return actual
    def wait():
        deadline=time.monotonic()+3
        while view.busy and time.monotonic()<deadline:
            app.processEvents(); time.sleep(.005)
        assert not view.busy
    try:
        assert not view.cardDetectionProfile['ready']
        assert not view.applyCardDetectionProfile('2','1')
        with patch('app.operator_console.quick_view_model.exchange_profile', side_effect=exchange):
            view.refreshCardDetectionProfile()
            assert view.busy
            assert not view.applyCardDetectionProfile('2','1')
            wait()
            assert view.cardDetectionProfile['ready']
            assert not view.cardDetectionProfile['runtimeFftSupported']
            assert not view.applyCardDetectionProfileWithFFT(8192, '2', '1')
            for invalid in [('nan','1'),('2','Infinity'),('2','3'),('16','1'),('2','4')]:
                assert not view.applyCardDetectionProfile(*invalid)
            assert len(calls)==1
            assert view.applyCardDetectionProfile('2,5','1,25')
            wait()
            assert actual==DetectionProfile(1,int(2.5*(1<<32)),int(1.25*(1<<32)))
            assert view.restoreCardDetectionProfile()
            wait()
            assert actual==DetectionProfile(2,36851433755,17098572778)
        with patch('app.operator_console.quick_view_model.exchange_profile',side_effect=DetectionConfigError('Uyumsuz imaj')):
            view.refreshCardDetectionProfile();wait()
            assert not view.cardDetectionProfile['ready']
            assert view.cardDetectionProfile['message']=='Uyumsuz imaj'
        before=dict(view.cardDetectionProfile)
        view._on_detection_profile_completed(view._generation-1,'detection_config',{'profile':actual},0)
        assert view.cardDetectionProfile==before
    finally:
        view.shutdown()


def test_runtime_fft_profile_is_exposed_and_applied_atomically():
    app = QGuiApplication.instance() or QGuiApplication([])
    view = OperatorViewModel()
    actual = DetectionProfile(4, 36_851_433_755, 17_098_572_778, 4096, True)

    def exchange(host, port, *, profile=None):
        nonlocal actual
        if profile is not None:
            actual = DetectionProfile(
                actual.generation + 1, profile.alpha_q32, profile.weak_alpha_q32,
                profile.fft_size, True)
        return actual

    def wait():
        deadline = time.monotonic() + 3
        while view.busy and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.005)
        assert not view.busy

    try:
        with patch('app.operator_console.quick_view_model.exchange_profile', side_effect=exchange):
            view.refreshCardDetectionProfile()
            wait()
            assert view.cardDetectionProfile['runtimeFftSupported']
            assert view.cardDetectionProfile['fftSize'] == 4096
            assert view.applyCardDetectionProfileWithFFT(16384, '2,5', '1,25')
            wait()
            assert view.cardDetectionProfile['fftSize'] == 16384
            assert actual == DetectionProfile(
                5, int(2.5 * (1 << 32)), int(1.25 * (1 << 32)), 16384, True)
            assert not view.restoreCardDetectionProfile()
            assert view.cardDetectionProfile['fftSize'] == 16384
            assert view.cardDetectionProfile['message'] == (
                "4096 varsayılanına dönmek için kartı yeniden başlatın; "
                "tam güç kesmeli cold-start gerekmez."
            )
    finally:
        view.shutdown()


def test_stale_larger_fft_cache_is_reconciled_after_card_restart():
    app = QGuiApplication.instance() or QGuiApplication([])
    view = OperatorViewModel()
    card = DetectionProfile(1, 36_851_433_755, 17_098_572_778, 4096, True)
    calls = []

    def exchange(host, port, *, profile=None):
        nonlocal card
        calls.append(profile)
        if profile is not None:
            assert profile.generation == card.generation
            assert profile.fft_size == 4096
            card = DetectionProfile(
                card.generation + 1,
                profile.alpha_q32,
                profile.weak_alpha_q32,
                profile.fft_size,
                card.runtime_fft_supported,
            )
        return card

    def wait():
        deadline = time.monotonic() + 3
        while view.busy and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.005)
        assert not view.busy

    try:
        # The open application still remembers 8192, but the restarted card has
        # already returned to its 4096 default.
        view._card_detection_profile = DetectionProfile(
            9, 36_851_433_755, 17_098_572_778, 8192, True)
        with patch('app.operator_console.quick_view_model.exchange_profile', side_effect=exchange):
            assert view.applyCardDetectionProfileWithFFT(4096, '8,58', '3,98')
            wait()

        assert calls[0] is None
        assert calls[1] is not None
        assert view.cardDetectionProfile['fftSize'] == 4096
        assert view.cardDetectionProfile['message'] == (
            "Etkin katsayılar FPGA’dan okundu. Yeni alım bu profille başlayacak.")
    finally:
        view.shutdown()
