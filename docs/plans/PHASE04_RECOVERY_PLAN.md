# PHASE-04 Parametre Çıkarımı Kurtarma Planı

## Amaç

PHASE-04'ü tarihsel başarısızlıkları silmeden veya yeniden etiketlemeden,
operatörce onaylanan izole analiz aralığında alan bazlı ve tekrar üretilebilir
kanıtla kapatmak. P0 referansı doğrudan doğrulanmış ürün profiline çevrilmez.

Bu çalışma algoritma ve doğrulama kapsamındadır. FPGA RTL, PetaLinux, canlı
HackRF kabulü, dBm kalibrasyonu, GNSS, konum ve TX kapsam dışıdır.

## Kontrollü alt fazlar

| Alt faz | Kapsam | Çıkış kapısı |
|---|---|---|
| PHASE-04-F1A | Sözleşme uzlaştırma ve tarihsel kanıt taşıma bağı | R1/R2/D1/E1 dosyaları byte-sabit kalır; relocation manifesti eski ve yeni kaynak kimliklerini doğrular; terim sözlüğü tek anlamlıdır. |
| PHASE-04-F1B | Geliştirme kataloğu ve yöntem kilidi | Geliştirme, binding ve OOS seed/katalogları ayrılır; kabul eşikleri sonuç görülmeden kilitlenir; ground truth runtime'a verilmez. |
| PHASE-04-F1C | Alan bazlı referans estimator | Merkez, taşıyıcı çizgisi, OBW99, güç/SNR ve sınırlı sinyal alanı bağımsız durum üretir; confirmed/owner/generation/span ve bounded bellek kapıları zorunludur. |
| PHASE-04-F1D | Tek seferlik binding ve kilitli OOS | Bütün çekirdek alanlar kilitli kapıları geçer veya sonuç başarısız olarak korunur; başarısız koşudan sonra aynı alt fazda eşik ayarı yapılmaz. |
| PHASE-04-F1E | Digest bağlı ürün entegrasyonu | Yalnız geçen alanlar profilden yüklenir; bağ bozulursa fail-closed olur; QML doğru terimleri ve alan durumlarını gösterir. |

## Kabul protokolü

E1'in sonuç görülmeden kilitlenmiş mühendislik eşikleri F1 için gevşetilmez.
Yeni yöntem, önce ayrı geliştirme kataloğunda geliştirilir. F1 binding ve OOS
kataloglarının seed'leri, trial sayıları, aileleri ve eşikleri yöntem kodundan
önce hash-kilitli olarak kaydedilir.

Zorunlu alanlar:

1. Yayın merkez frekansı
2. Gözlenmiş taşıyıcı çizgisi frekansı veya `not_observed/not_applicable`
3. OBW99 alt/üst kenarı ve bant genişliği
4. Kalibre edilmemiş kanal gücü ve SNR kestirimi
5. Sınırlı Analog/Sayısal/Belirsiz alanı

Otomatik span yalnız kolaylık yeteneğidir. Operatörün onayladığı geçerli spanın
ölçümünü global olarak kapatmaz ve PHASE-04 kapanışının çekirdek alanı değildir.

## Değişmez güvenlik ve doğruluk kuralları

- Operatör truth frekansı, beklenen bant, güç veya sınıf girmez.
- Yalnız `confirmed && observed_this_frame` olay ölçülebilir.
- Sonuç event/revision, frame dizisi, source, profile ve configuration nesline bağlıdır.
- Gürültü referansı eksik, komşu yayınla çakışan veya kalite eşiği altındaki alan sayı yayımlamaz.
- Güç dBFS'tir; dBm değildir. Kalibrasyon yoksa bu açıkça gösterilir.
- Analog/Sayısal genel modülasyon tanıma iddiası değildir; çelişkili kanıt `Belirsiz` olur.
- Runtime tam kayıt yüklemez; dört frame, bir worker ve bir pending intent sınırı korunur.
- R1/R2/D1/E1 kanıt dosyaları değiştirilmez.
- Binding/OOS başarısız olursa PHASE-04 açık kalır ve ürün doğrulanmış PHASE-03 profiline döner.

## Ürün entegrasyonu

QML kartları yalnız profil tarafından doğrulanan alanları sayısal gösterir.
Doğrulanmamış alan `Henüz doğrulanmadı`, yeterli kanıt bulunmayan alan ise kendi
durumuyla gösterilir. P0'daki güç ağırlıklı merkez artık `Taşıyıcı` adıyla
sunulmaz. Eski P0 kanıt dosyaları tarihsel kayıt olarak korunur; yeni ürün
sözleşmesi geriye dönük kanıtı yeniden adlandırmaz.

## Kapanış

PHASE-04 yalnız bütün çekirdek alanların binding ve OOS kapıları geçtiğinde,
profil/digest bağı, ürün fail-closed testleri, hedef regresyon ve tam repository
regresyonu birlikte geçtiğinde tamamlanır. Başarısız bir F1D koşusu fazı kapatmaz.

## Durum

- PHASE-04-F1A 2026-08-24 tarihinde tamamlandı. R1/R2/E1 tarihsel kanıtları
  SHA-256 korumalı relocation manifestine bağlandı; D1F'nin mevcut relocation
  kaydı korundu. R2 ve E1 salt-okunur bütünlük kontrolleri kaynak taşımasından
  sonra yeniden geçmektedir; algoritma sonuçları başarısız kalmıştır.
- P0 güç ağırlıklı frekans alanı model, ürün QML yüzeyi, tarihsel QWidget
  regresyon yüzeyi, doğrulama scriptleri ve KTR kayıtlarında `Yayın Merkez
  Frekansı` olarak düzeltildi. Ayrı taşıyıcı çizgisi yeteneği eklenmiş veya
  doğrulanmış sayılmadı.
- F1A çıkış regresyonu 454 passed, 1 kontrollü skip ve 0 failure sonucuyla
  422,55 saniyede tamamlandı. Skip yalnız yapılandırılmamış haricî gerçek veri
  setine aittir.
- PHASE-04-F1B başlamamıştır. Yöntem kodu değiştirilmeden önce geliştirme,
  binding ve OOS katalogları ile kabul kilidi hazırlanacaktır.
