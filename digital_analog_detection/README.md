# Sayısal / Analog Sinyal Sınıflandırma

## KTR-4.2 parametre iyileştirmesi — 16 Eylül 2026

Merkez frekansı ve ayrı taşıyıcı çizgisi ana sonuçlarda ayrıldı. Yetenek bildiren
kartta manuel ölçüm 16 özgün kareye (2 MS/s hızda 32,768 ms) uzatıldı; eski
kartta dört kare korunur. P0PM-v3, ARM grup kararlılığı denetimi ve kayıt/CRC
bağı eklendi; sayısal hesap için PC geri dönüşü yoktur. PL'nin kare başına
4096 FFT işlemi değişmedi. Yerel Analog/Sayısal modeli seçili kanal filtresiyle
aynı önişlemede yeniden eğitildi; sonuç deneysel tahmin olarak gösterilir.
Kaynak/test ve ARM derlemesi tamamlandı; karta yükleme ve yeni RF ölçümü
henüz yapılmadı. PHASE-08/ST-06 ve fiziksel KTR-4.2 kabulü açıktır. Yöntem,
kanıtlar, uyumluluk ve sınırlar: `docs/interfaces/PARAMETER_REFINEMENT_20260916.md`.

Bu dizin yalnız ED alım zincirinde kullanılan sayısal/analog sınıflandırma
bileşenlerini içerir. RF yayın, TX cihaz kontrolü, dalga biçimi üretimi veya ET
görevi içermez.

## İşlem zinciri

```text
Ham RX I/Q
  → sinyal var/yok denetimi
  → taşıyıcı ofseti ve kanal seçimi
  → bant genişliği kestirimi
  → normalizasyon
  → modülasyondan bağımsız özellikler
  → Analog / Sayısal sınıflandırma
```

## Dosyalar

| Dosya | Açıklama |
|---|---|
| `feature_extractor_v1.py` | Kanalize I/Q üzerinden sınıflandırma özellikleri çıkarımı |
| `classifier_model.py` | NumPy tabanlı sınıflandırıcı çalışma zamanı |
| `integration.py` | Parametre ölçüm zinciriyle ED sınıflandırma bağı |
| `train_classifier.py` | Çevrimdışı, sentetik eğitim ve değerlendirme aracı |
| `hackrf_inspector.grc` | HackRF RX akışını ZMQ üzerinden yayımlayan alıcı akışı |
| `hackrf_rx_interference_monitor.grc` | Yalnız RX çalışan; spektrum, spektrogram ve I/Q zaman alanını birlikte gösteren bağımsız bozulma/girişim gözlem akışı |

13 Eylül 2026 bakımında, hiçbir ürün giriş noktası veya doğrulama tarafından
kullanılmayan yinelenen `signal_channelizer_v1.py` aracı kaldırıldı. Sinyal
kanalizasyonu ve özellik çıkarımı `integration.py` ile
`feature_extractor_v1.py` üzerinden yürütülür.

Canlı RX kabulü, kaynak ve kanıt hash'leri eşleşen ayrı testlerle yapılır.
Sentetik eğitim sonucu fiziksel RF doğruluğu veya saha kabulü sayılmaz.
