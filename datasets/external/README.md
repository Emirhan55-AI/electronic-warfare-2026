# Harici Veri

Bu dizin gerçek RF kayıtlarının Git dışında kalan yerel çalışma alanını tanımlar. `datasets/external/local/` altındaki metadata, binary kesit ve yerel manifestler izlenmez.

Harici entegrasyon için `PHASE01_EXTERNAL_METADATA` ve `PHASE01_EXTERNAL_DATA` birlikte tanımlanır. İkisi de yoksa test kontrollü biçimde atlanır; yalnız biri varsa yapılandırma hatasıdır. Mutlak yollar tracked dosyalara veya evidence JSON'larına yazılmaz.

İncelenen `ism_band_24` kaydının lisans metni yalnız `CC BY-SA` olduğundan kesin sürüm ve özgün kaynak doğrulanmamıştır. Durum `license_status: unverified` olarak kalır; gerçek binary veya kesit Git'e eklenmez.
