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

PHASE-04-R2 comparison şeması v3'tür ve profil sürümü v3 içindeki
`analysis.core-parameters/v2` bloğuna bağlanır. R2 bağı; exact comparison SHA'nın
yanında method-lock SHA, güncel implementation manifesti, frozen katalog ve
PHASE-03 profil digestlerini zorunlu tutar. Locked analysis/noise/band yöntemleri,
geçen downstream yöntemleri ve comparison kayıtları birebir aynı değilse profil
yüklenmez. R2 bant geçmişi `6.528 byte`, birleşik parametre geçmişi `74.368 byte`
üst sınırındadır.

`select_phase04_r2_profile.py --evaluate`, tek frozen binding çalışmasının
canonical sonucunu yalnız repository dışındaki açık output yoluna yazar.
`--establish-from` benchmark'ı yeniden çalıştırmadan aynı payload'ı
`r2-parameter-comparison.json` olarak atomik kurar; validated profil yalnız bütün
aşamalar geçtiyse oluşur. `characterize_phase04_r2_oos.py` ayrı seed ailesinin
karakterizasyonunu repository dışında üretir ve bu veri selector kararına girmez.

R2 evidence sahipliği çakışmaz: selector yalnız R2 comparison ve koşullu profili;
R2 verifier family diagnostic, OOS, golden ve summary dosyalarını; renderer ise
yalnız tam başarıdaki mevcut yedi PHASE-04 görselini yönetir. R1 evidence dosyaları
R2 araçları tarafından yazılmaz. Başarısız R2 comparison yanında eski bir profil
bulunsa bile method-lock/comparison digest bağı geçmediğinde runtime onu
çalıştırmaz ve PHASE-03 `regional` profiline döner.

## PHASE-04-E1 alan bazlı capability profili

`phase04e1-operator-assisted-parameters` tam PHASE-04 profili değildir. Byte-sabit PHASE-03 `regional` zincirinin üzerine yalnız binding ve OOS kapılarını ayrı ayrı geçen `emission_center_frequency`, `carrier_line_frequency`, `occupied_bandwidth`, `uncalibrated_power_dbfs` ve `signal_domain` alanlarını ekler. Otomatik span ayrı convenience alanıdır; başarısızlığı manuel operatör span'ini tek başına kapatmaz.

Profil; `validated_fields`, sabit yöntem kimlikleri, method-lock SHA, exact comparison SHA, implementation manifest SHA, PHASE-03 profil SHA ve acceptance contract SHA taşır. Bu bağlardan biri bozuksa hiçbir E1 ölçüm bloğu yüklenmez, analiz sonuçları temizlenir ve uygulama saf PHASE-03 profiline döner. Doğrulanmamış alan UI'da sayı göstermez. En az bir alanın geçmesi `PHASE-04 tamamlandı` anlamına gelmez.

PHASE-05'te gerçek dinleme blokları geldikçe ayrı Akış Tasarımı editörü geliştirilebilir. PHASE-06'da PC/PS/PL hedefleri ayrı doğrulanır; profil otomatik HDL üretmez. PHASE-08 canlı kaynak bloğunu, PHASE-13 doğrulanmış profil kilidini kapsar. ET/TX blokları güvenlik kapıları olmadan eklenmez.
