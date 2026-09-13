# Sayısal / Analog Sinyal Sınıflandırma

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

13 Eylül 2026 bakımında, hiçbir ürün giriş noktası veya doğrulama tarafından
kullanılmayan yinelenen `signal_channelizer_v1.py` aracı kaldırıldı. Sinyal
kanalizasyonu ve özellik çıkarımı `integration.py` ile
`feature_extractor_v1.py` üzerinden yürütülür.

Canlı RX kabulü, kaynak ve kanıt hash'leri eşleşen ayrı testlerle yapılır.
Sentetik eğitim sonucu fiziksel RF doğruluğu veya saha kabulü sayılmaz.
