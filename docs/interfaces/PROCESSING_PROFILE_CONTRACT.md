# PHASE-03 İşlem Profili Sözleşmesi

Operasyon pipeline'ı `profiles/phase03/operation-default.json` dosyasındaki `validated` profilden kurulur. Controller içinde profilden bağımsız ikinci detector zinciri bulunmaz. UI'daki profil özeti yürütülen neslin profilinden gelir.

## Şema

Profil şema sürümü, profil kimliği/sürümü, yaşam döngüsü, sabit sıralı bloklar ve bağlantılar içerir. Blok kimliği ile tür/sürüm çifti allowlist registry'de bulunmalı; port adları ve `iq.frame/v1`, `spectrum.power/v1`, `detection.cells/v1`, `detection.regions/v1`, `detection.events/v1`, `operation.view/v1` veri türleri uçtan uca eşleşmelidir. Parametreler şemaya göre doğrulanır. Mutlak yol, timestamp, makine bilgisi, arbitrary Python, dinamik kod veya plugin bulunmaz.

Yürütme sırası kayıtlı SigMF kaynak, PHASE-02 spektrum, seçilmiş detector, kaba gruplama, temporal M/N ve Operasyon sink bloklarıdır. Kaynak, profil, Pfa, merkez politikası veya DSP ayarı değişince pipeline nesli ve temporal durum sıfırlanır; stale worker sonuçları uygulanmaz. `experimental` profil Operasyon varsayılanı olamaz.

## Kurulum ve sahiplik

`select_phase03_profile.py --write`, sabit benchmark'ı çalıştırır; başarılı seçimden `detector-comparison.json` ve `operation-default.json` üretir. İkisi yoksa birlikte oluşturur. İkisi byte-byte aynıysa no-op'tur. Sonuç farklıysa sessizce yazmaz; yalnız normal kapanışta kullanılmayan açık `--reestablish` yeniden kurabilir. Başarısız benchmark profil üretmez ve eski profili yeni başarı kanıtı saymaz.

`verify_phase03.py --write` yalnız `golden-detection.json` ile `verification-summary.json`; `render_phase03_ui.py --write` yalnız `visual-summary.json` ve PHASE-03 PNG'lerini yazar. Bütün `--check` modları salt-okunurdur. Farklı makinede seçim sonucu değişirse profil sessizce değiştirilmez; fark raporlanır.

PHASE-04/05'te gerçek bloklar geldikçe ayrı Akış Tasarımı editörü geliştirilebilir. PHASE-06'da PC/PS/PL hedefleri ayrı doğrulanır; profil otomatik HDL üretmez. PHASE-08 canlı kaynak bloğunu, PHASE-13 doğrulanmış profil kilidini kapsar. ET/TX blokları bu genel alana güvenlik kapıları olmadan eklenmez.
