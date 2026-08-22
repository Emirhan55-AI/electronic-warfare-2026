# Doğrulama

Bu dizin doğrulama sahipliğini ve katman bağımlılığı kapılarını tanımlar.
Tarihsel KTR ve faz kanıtlarının yolları değişmesin diye `tests/`, `scripts/`,
`datasets/fixtures/` ve `results/evidence/` kökte korunur; bu alanların tamamı
doğrulama katmanına aittir. `architecture-boundaries.json`, ürün kaynaklarının
izin verilen bağımlılık yönlerini ve eski dizin adlarının kaldırıldığını tanımlar.

Kökteki `tests/` dizini repository ve PHASE-01 SigMF regresyonlarına ek olarak PHASE-02 golden DSP, bounded frame okuma, operatör uygulaması, Türkçe/Unicode, görsel durum ve kayıt inceleme performansı testlerini içerir.

`scripts/verify_phase02.py` sabit sıralı PHASE-02 kanıtlarını üretir. `scripts/render_phase02_ui.py` gerçek Qt uygulamasının boş, yüklü, uyarı ve hata durumlarını `%100` ile fiziksel `1920×1080 @ %150` senaryolarında render eder. PNG dosyaları görsel inceleme kanıtıdır; byte-for-byte platform kapısı değildir.

Harici dataset yolu tanımlı değilse tek-çerçeve doğrulaması kontrollü olarak atlanır. RTL testbench bu fazın kapsamı dışındadır.
