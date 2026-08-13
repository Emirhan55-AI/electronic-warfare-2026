# PHASE-03/04 İşlem Profili Sözleşmesi

PHASE-03 tespit profili byte-byte tarihsel kanıttır. PHASE-04 Operasyon pipeline'ı, bütün kapılar geçerse `profiles/phase04/operation-default.json` dosyasındaki `validated` profilden kurulur. Profil ayrıca kanonik comparison kimliği ve SHA-256 değeriyle güncel katalog, implementation manifesti ve PHASE-03 profil digestlerine bağlanır. Controller içinde profilden bağımsız ikinci detector veya estimator zinciri bulunmaz. UI'daki profil özeti yürütülen neslin profilinden gelir.

## Şema

Profil şema sürümü, profil kimliği/sürümü, yaşam döngüsü, sabit sıralı bloklar ve bağlantılar içerir. Blok kimliği ile tür/sürüm çifti allowlist registry'de bulunmalı; port adları ve `iq.frame/v1`, `spectrum.power/v1`, `detection.cells/v1`, `detection.regions/v1`, `detection.events/v1`, `operation.view/v1` veri türleri uçtan uca eşleşmelidir. Parametreler şemaya göre doğrulanır. Mutlak yol, timestamp, makine bilgisi, arbitrary Python, dinamik kod veya plugin bulunmaz.

PHASE-04 yürütme sırası kayıtlı SigMF kaynak, PHASE-02 spektrum, seçilmiş detector, kaba gruplama, temporal M/N, `analysis.core-parameters/v1` ve `sink.operator-console/v2` bloklarıdır. Parametre bloğu `iq.frame/v1`, `spectrum.power/v1` ve `detection.events/v1` alıp `parameters.core/v1` üretir. Parametre bloğunda analysis-window, gürültü, bant, spektral merkez, taşıyıcı, güç/SNR ve sinyal alanı yöntem kimlikleri bulunur. Kaynak, profil, Pfa, merkez politikası veya DSP ayarı değişince pipeline nesli, temporal durum ve özellik geçmişi sıfırlanır; stale sonuç uygulanmaz.

Operasyon çözümleyicisi PHASE-04 profilini yalnız şu koşulların tamamında kabul eder: comparison v2 kimliği geçerlidir, exact comparison SHA profille eşleşir, güncel katalog/implementation/PHASE-03 digestleri iki belgede aynıdır, bütün aşamalar ile birleşik pipeline geçmiştir ve yöntem kimlikleri birebir aynıdır. Eksik, başarısız, bozuk veya stale bağda PHASE-04 profili diskte korunabilir fakat çalıştırılmaz; parametre katmanı kapatılır ve byte-sabit PHASE-03 profiline dönülür.

## Kurulum ve sahiplik

`select_phase03_profile.py --write`, sabit benchmark'ı çalıştırır; başarılı seçimden `detector-comparison.json` ve `operation-default.json` üretir. İkisi yoksa birlikte oluşturur. İkisi byte-byte aynıysa no-op'tur. Sonuç farklıysa sessizce yazmaz; yalnız normal kapanışta kullanılmayan açık `--reestablish` yeniden kurabilir. Başarısız benchmark profil üretmez ve eski profili yeni başarı kanıtı saymaz.

`verify_phase03.py --write` yalnız `golden-detection.json` ile `verification-summary.json`; `render_phase03_ui.py --write` yalnız `visual-summary.json` ve PHASE-03 PNG'lerini yazar. Bütün `--check` modları salt-okunurdur. Farklı makinede seçim sonucu değişirse profil sessizce değiştirilmez; fark raporlanır.

`select_phase04_profile.py`, iki analysis-window, üç gürültü ve dört bant yönteminden oluşan 24 tuple'ı; bant geçerse dokuz merkez–taşıyıcı çifti, sabit güç/SNR zinciri ve üç sınıflandırıcıyı tek yönlü sırada değerlendirir. `--evaluate` hiçbir dosya yazmaz. Selector `parameter-comparison.json` ile koşullu PHASE-04 profilinin sahibidir; normal `--write` yalnız byte-identical no-op'a izin verir, farklı sonuç için kontrollü `--reestablish` gerekir. Başarısız comparison `selected_methods=null` taşır ve stale profil için başarı kanıtı oluşturmaz. Downstream başarısızlığı upstream seçimini değiştirmez.

`verify_phase04.py --write` başarılı veya başarısız golden/summary dosyalarının sahibidir. Renderer yalnız geçerli bağlı profil ve tam başarıda PHASE-04 visual summary ile yedi PNG'nin sahibidir. Bütün `--check` modları salt-okunurdur.

PHASE-05'te gerçek dinleme blokları geldikçe ayrı Akış Tasarımı editörü geliştirilebilir. PHASE-06'da PC/PS/PL hedefleri ayrı doğrulanır; profil otomatik HDL üretmez. PHASE-08 canlı kaynak bloğunu, PHASE-13 doğrulanmış profil kilidini kapsar. ET/TX blokları güvenlik kapıları olmadan eklenmez.
