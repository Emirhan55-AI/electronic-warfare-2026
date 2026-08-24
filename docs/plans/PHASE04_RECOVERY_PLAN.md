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
| PHASE-04-F1B | Değerlendirme protokolü kilidi | Geliştirme kataloğu yayımlanır; binding ve OOS seed'leri commitment ile kapatılır; kabul eşikleri yöntem geliştirilmeden önce kilitlenir; ground truth runtime'a verilmez. |
| PHASE-04-F1C | Alan bazlı referans estimator ve yöntem kilidi | Yalnız geliştirme kataloğunda emisyon merkezi, gözlenen taşıyıcı frekansı, OBW99, güç/SNR ve sınırlı modülasyon kategorisi bağımsız durum üretir; confirmed/owner/generation/span ve bounded bellek kapıları zorunludur; evaluation reveal öncesi yöntem digest'i kilitlenir. |
| PHASE-04-F1D | Tek seferlik binding ve kilitli OOS | Bütün çekirdek alanlar kilitli kapıları geçer veya sonuç başarısız olarak korunur; başarısız koşudan sonra aynı alt fazda eşik ayarı yapılmaz. |
| PHASE-04-F1E | Digest bağlı ürün entegrasyonu | Yalnız geçen alanlar profilden yüklenir; bağ bozulursa fail-closed olur; QML doğru terimleri ve alan durumlarını gösterir. |

## Kabul protokolü

E1'in sonuç görülmeden kilitlenmiş mühendislik eşikleri F1 için gevşetilmez.
Yeni yöntem, önce ayrı geliştirme kataloğunda geliştirilir. F1 binding ve OOS
kataloglarının seed'leri, trial sayıları, aileleri ve eşikleri yöntem kodundan
önce hash-kilitli olarak kaydedilir.

Zorunlu alanlar:

1. Emisyon merkez frekansı
2. Gözlenen taşıyıcı frekansı veya `not_observed/not_applicable`
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
  regresyon yüzeyi, doğrulama scriptleri ve KTR kayıtlarında `Emisyon Merkez
  Frekansı` olarak düzeltildi. Ayrı taşıyıcı frekansı yeteneği eklenmiş veya
  doğrulanmış sayılmadı.
- F1A çıkış regresyonu 454 passed, 1 kontrollü skip ve 0 failure sonucuyla
  422,55 saniyede tamamlandı. Skip yalnız yapılandırılmamış haricî gerçek veri
  setine aittir.
- PHASE-04-F1B 2026-08-24 tarihinde tamamlandı. Altı zorunlu alanın kabul
  eşikleri yöntem geliştirilmeden önce donduruldu; 64 trial/aile geliştirme
  kataloğu ayrıldı. Binding ve OOS seed preimage'ları repository dışında kapalı
  tutuluyor; repository yalnız SHA-256 commitment değerlerini taşıyor. Protokol
  kilidi `6ce085432fc8f74f29442b66ab37e72ce934bcbb9b83dfad241e4fac218f342b`
  digest'iyle altı zorunlu kontrolü geçti.
- PHASE-04-F1C 2026-08-24 tarihinde tamamlandı. Alan bazlı estimator yalnız
  64 trial/aile açık geliştirme kataloğunda geliştirildi. Emisyon merkezi,
  taşıyıcı çizgisi, OBW99, span dayanıklılığı, kalibre edilmemiş kanal gücü,
  SNR ve sınırlı modülasyon kategorisi geliştirme kapılarının tamamını geçti;
  bu sonuç binding, OOS, canlı RF veya ürün kabulü değildir.
- Confirmed olay, owner/revision, source/pipeline/configuration nesli, dört frame,
  izole span ve komşu aday kapıları fail-closed uygulanmaktadır. Estimator sonucu
  ile sabit istatistiksel modelin toplam sayısal kalıcı yükü 46.116 byte olarak
  65.536 byte sınırının altında kilitlendi.
- Yöntem ve uygulama girdileri binding/OOS seed reveal öncesinde
  `d42ba38cda80c901f57288a23d253e787b9f88aabd607dbd01e4dbd4fdab9e2b`
  method-lock digest'ine bağlandı. Seed'ler açılmadı.
- PHASE-04-F1D 2026-08-24 tarihinde tek sefer çalıştırıldı. Değerlendirme
  çalıştırıcısı `186a23a8744d357a92afa96e5752545b8b4001d2a08c92d237aea5bd13f915b1`
  kimliğiyle seed reveal öncesinde kilitlendi ve kilit `b9a4587` commit'iyle uzak
  depoya gönderildi. Seed commitment'ları doğrulandı; binding ve ardından OOS
  popülasyonu yeniden koşuya izin vermeyen başlangıç kaydıyla değerlendirildi.
- F1D sonucu başarısızdır. Binding popülasyonunda yalnız span dayanıklılığı
  geçti. OOS popülasyonunda emisyon merkezi, gözlenen taşıyıcı frekansı, span
  dayanıklılığı, kalibre edilmemiş kanal gücü ve SNR geçti; OBW99 ile sinyal
  alanı geçmedi. Binding'deki gürültü negatif kontrolünde güç ve SNR için dört
  yanlış sayısal sonuç görüldü; ortak fail-closed kapısı yerel kapıları geçen beş
  sayısal alanın tamamını başarısız yaptı. Binding'deki bağımsız alan başarısızlığı
  6 dB global ve aile tabanlı sinyal alanı kapılarıdır. OOS'ta OBW aile geçerlilik
  sayısı ile sinyal alanı doğru/yanlış karar sayıları kilitli sınırların dışında
  kaldı.
- Kanıt bütünlüğü doğrulaması geçti, ancak değerlendirme kararı başarısızdır.
  Eşikler ve kilitli yöntem değiştirilmedi; yeniden koşu yapılmayacak. Ürün
  profili oluşturulmadı, PHASE-04 açık kaldı ve F1E başlatılmadı.
- F1D sonrasında PHASE-04-F2 ayrı iyileştirme turu açıldı. F2A salt-okunur
  analizinde F1 kararlarının tamamı yeniden üretildi; taşıyıcı abstention kapısı
  ile binding/OOS negatif kontrol kare sayılarının kilitli skorlayıcıda
  değerlendirilmediği doğrulandı. Ayrıntılar `PHASE04_F2_RECOVERY_PLAN.md` ve
  `PHASE04_F2A_FAILURE_ANALYSIS.md` içindedir.
- PHASE-04-F2B tamamlandı. Altı yeni açık geliştirme seed'i, 288 trial/aile ve
  384 negatif kontrol ölçümü ayrıldı. Binding için 40, OOS için 24 benzersiz
  çalıştırılabilir kapı; alan bazlı negatif kontrol ve iki popülasyonda düşük SNR
  taşıyıcı abstention zorunlu hale getirildi. Yeni binding/OOS seed preimage'ları
  repository dışında tutuluyor; commitment ve protokol
  `ca22f1189a5e5dbf0b0cd6e3af1a8518f80048733b15f011610091889d671614`
  kimliğiyle v3 yöntem geliştirmesi öncesinde kilitlendi. F2C başlamamıştır.
