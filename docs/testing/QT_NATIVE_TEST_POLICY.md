# Qt Yerel Test Yaşam Döngüsü Politikası

PySide6 ve pyqtgraph kullanan operatör entegrasyon testleri, Python cyclic GC ile yerel Qt nesne yıkımının başka bir `QThreadPool` worker'ı çalışırken çakışmaması için modül başına ayrı Python süreçlerinde yürütülür. Saf Python testleri ana unittest sürecinde kalır.

İzolasyon bir başarı toleransı değildir. Alt süreç assertion hatası, zaman aşımı veya yerel çökme ile sonlanırsa üst test de başarısız olur; alt sürecin tam çıkış kodu, stdout, stderr ve faulthandler çıktısı hata raporuna eklenir.

Qt fixture kapatılırken yeni iş kabulü durdurulur, timer üreticileri kesilir, controller backend ve worker'ları kapatıp `QThreadPool.waitForDone()` ile bekler, ardından pencere/timer QObject grafiği `deleteLater()` ve `DeferredDelete` işleme ile worker bulunmayan durumda yok edilir. Python GC ancak bu sınırdan sonra nesneleri toplayabilir.

| Bileşen | Sahip | Başlatma | Durdurma / çıkış | Bekleme ve sinyal | QObject/GC sınırı |
| --- | --- | --- | --- | --- | --- |
| `OperatorController` | `MainWindow` QObject parent'ı | uygulama kurulumu | `_closing`, timer stop, backend close/cancel | `thread_pool.waitForDone()` | pencere DeferredDelete zinciri |
| `FrameTask`, `MeasurementTask`, `SourceOpenTask`, `ListeningTask`, `WavExportTask` | çalışma süresince `QThreadPool` | `thread_pool.start()` | bounded `run()` dönüşü | controller kapanışı pool'u bekler; receiver yok edilince Qt bağlantıyı keser | QRunnable auto-delete, worker çıkışından sonra |
| `AcquisitionTask` | çalışma süresince `QThreadPool` | `thread_pool.start()` | closing event ve backend cancellation, sonra `run()` dönüşü | controller backend'i kapatır ve pool'u bekler | worker çıkışından sonra |
| controller playback timer'ı | `OperatorController` | playback başlangıcı | `controller.close()` içinde stop | ana Qt thread'i | controller parent zinciri |
| test heartbeat timer'ı | test fixture | ilgili test başlangıcı | stop ve explicit signal disconnect | worker drain sonrasında | explicit `deleteLater()` + DeferredDelete |
| `MainWindow`/pyqtgraph grafiği | test fixture | `build_application()` | controller tamamen kapandıktan sonra `close()` | queued worker sonucu kalmadan | explicit `deleteLater()` + DeferredDelete, sonra GC |
| `QApplication` | izole test süreci | modül child başlangıcı | child süreç sonu | modül testleri seri | başka Qt modülüyle paylaşılmaz |

Minimal sıra/GC reproducer'ı:

```powershell
python -B scripts/verify_qt_lifecycle.py --iterations 20
```

Bu reproducer, measurement worker fixture'ını capture/fixture worker testinden önce çalıştırır ve ikinci worker aktifken GC basıncı uygular. Her alt süreç çökmesi doğrulama başarısızlığıdır.
