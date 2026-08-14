# ADR-0009 — HackRF RX Host Ön Hazırlığı

- Durum: Accepted
- Kapsam: PHASE-08A

## Karar

PHASE-04 ana açık faz olarak kalırken, üniversitedeki donanım kabul süresini azaltmak amacıyla PHASE-08'in yalnız donanımdan bağımsız host acquisition hazırlığı erken yapılacaktır. Bu sıra istisnası PHASE-05, PHASE-06 veya PHASE-07'nin başladığı, atlandığı ya da tamamlandığı anlamına gelmez. PHASE-08'in gerçek donanım kabul kapsamı değişmez.

HackRF-1 RX girişi Qt ve DSP'den bağımsız, dependency injection kullanan bir acquisition sözleşmesiyle hazırlanır. Gerçek CLI backend yalnız allowlist argümanları, bounded çıktı, zaman aşımı, iptal ve geçici dosya temizliğiyle çalışabilir. Yardım çıktısı gerekli seçenekleri doğrulamadan RX komutu kurulmaz. `hackrf_transfer` stdout akışı varsayılmaz; gerçek backend yalnız kesin boyutlu geçici `ci8` capture dosyası kullanır. Deterministik test backend'i aynı sözleşmeyi uygular fakat hiçbir zaman bağlı cihaz veya canlı RF olarak sunulmaz.

Capture biçimi signed, interleaved `ci8` ve `[I0,Q0,I1,Q1,...]` düzenidir. Varsayılan bounded capture 16.384 karmaşık örnekten, yani dört adet 4096 örnekli çerçeveden oluşur. Capture mevcut PHASE-02 spektrum ve PHASE-03 `regional` detector/temporal olay zincirine kaynak adaptörü olarak bağlanır; DSP veya detector yeniden yazılmaz.

## Güvenlik ve iddia sınırı

Bu karar yalnız HackRF-1 RX hazırlığıdır. HackRF-2, TX, firmware, karıştırma, aldatma, FPGA/RTL ve PHASE-04 estimator geliştirmesi kapsam dışıdır. Gerçek cihaz keşfi, gerçek sweep formatı, canlı I/Q, RF performansı ve donanım evidence'ı üniversitedeki PHASE-08 donanım kabul turuna bırakılmıştır. Donanımsız evidence `hardware_status=not_exercised` ve `live_rx_status=not_exercised` taşır.
