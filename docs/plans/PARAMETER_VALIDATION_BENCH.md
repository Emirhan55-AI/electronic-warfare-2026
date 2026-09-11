# Dört parametre doğrulaması

## OBW aralık kapsama denetimi — 11 Eylül 2026

Güncel 30 kayıt, ürün sonucuna dokunmayan iki tanıyla yeniden üretildi. Dört
ayrı 4096 dikdörtgen FFT'nin yakın aralık enerji oranı bu küçük kümede BPSK'yi
ayırdı, fakat aralık çok dar ve yalnız üç tohum/iki SNR içerdiği için eşik
seçilmedi. Dört ardışık karenin tek 16.384 örnekli Hann periodogramında her
kuyruk için `%0,5` üst belirsizlik sınırı kullanan aday, aralık dışı 6/6 BPSK
sonucunu tuttu. Aynı kapı 12 dB'deki CW/AM/NFM/FSK örneklerinin tamamında da
OBW vermedi; 24 dB'de bu ailelerin sonuçlarını korudu.

Bu sonuç adayın güvenli yönde davrandığını gösterir, ürün başarısı değildir.
Kilitli F5 değiştirilmedi. Yeni yöntem ancak önceden kilitli daha geniş bir
değerlendirme, komşu sinyal/renkli gürültü kontrolleri, Python↔C↔ARM eşdeğerliği,
bellek/süre ölçümü ve kontrollü RF sonrasında alınabilir. Kanıt:
`results/evidence/phase08/parameter-obw-containment-audit-20260911.json` ve ZIP.

## Dört parametrenin gerçek RF durumu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: yeni temiz AM koşusunda dar aralık SNR'si
13,36–15,32 dB iken sabit aday 10/10 Belirsiz kaldı. Yeni `rf_observation`
ürün dışı ön işlemesi uzun I/Q, FIR kanal süzme ve frekans kayması
hipotezlerini uygular; kesin sınıflandırıcı değildir. Kullanılabilir donanım
son beyana göre yalnız iki HackRF'dir; dBm kalibrasyonu diğer işleri durdurmaz.
Ürün/ARM/RTL ve önceki kabul durumları değişmedi.

Yeni ham veri üretilmeden üç eski gerçek kayıtta bant/gürültü tanısı ve
bir yeni temiz AM koşusu tamamlandı. Başarı paydası seçilerek daraltılmadı.
Doğrulayıcılar gerçek I/Q hash'lerini, güç ölçeğini ve alan bağımsızlığını
denetler. Kapsam, hatalı çıktı veya eksik RF'yi başarıya çevirmeyi içermez.

[Ayrıntılı durum, araştırma ve yeniden üretim](../reviews/PARAMETER_EXTRACTION_ASSESSMENT.md).


## QPSK ve kaynak dalga biçimi tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: 825 MHz QPSK beyanıyla 24/24 ve 32/32 dB'de
ikişer sonlu RX kaydı alındı. Dört kayıttaki 40 pencere kalite kapısını
geçti, 40/40 Belirsiz kaldı; model değiştirilmedi, ürün kabulü yapılmadı.
Mayhem upstream `31b25a445b166b13101ea4c6546f78b84dcc6499` incelemesinde
BPSK sabit 0–1, QPSK sabit dört sembollü döngüdür; Shape kullanılmaz.
BPSK ve kare mesajlı DSB'nin 256 faz adresindeki I/Q örnekleri aynıdır.
Bu örnekte yalnız menü etiketiyle farklı kesin Analog/Sayısal karar
beklenemez; Belirsiz tek başına algoritma hatasını kanıtlamaz. Bu bulgu
önceki başarısız RF kapsamını başarıya çevirmez. Rastgele verili sayısal
kaynak kabulü ayrıca açıktır. Ham RF çizgi aralıkları yaklaşık 2 kHz ton
hipoteziyle uyumludur; yüklü verici sürümü ve ayarı doğrulanmış değildir.
Güçlü yan çizgi taşıyıcı referansı sayılamaz. Güncel üretim F5 değişmedi;
ARM/FPGA ürün kabulü ve kalibre dBm açık kalır. Tanı komutu:
`python scripts/diagnose_siggen_reference.py --output <yeni-rapor.json>`.
Kanıt: `results/evidence/phase08/parameter-qpsk825-source-diagnostic-20260909.json`
ve ZIP (21 dosya hash doğrulaması); BPSK ham kayıtları önceki BPSK arşivindedir.

## 9 Eylül 2026: AM karşılaştırması

Kullanıcı 735 MHz, AM %100, Sine 1 kHz, TX Gain 0 / Amp 0 ayarı
talimatından sonra AM açık bildirdi. Fotoğrafta önceki Gain 47 görülüyordu;
Gain 0 son talimat/yanıt bağıdır, cihazdan geri okunmuş ayar değildir.
Onaylı Faraday kabinindeki alıcıdan 0/0, 16/16 ve 24/24 dB kazançta,
735,3 ve 734,7 MHz merkezlerde altı adet 0,5 saniyelik ham kayıt alındı.
Tam örnek sayıları ve komutlar kayıtta; ilk 524288 kompleks örnekten
sonraki analiz bölümlerinde ray değerinde bileşen yoktur.

Dört yüksek kazanç kaydında zarf spektrumunda 998,91 Hz ton bulundu
(2,31 Hz hücre). 24/24 dB uzun spektrumunda güçlü orta çizgi
734990490,72 / 734990466,31 Hz, yan çizgiler yaklaşık ±1 kHz'dedir.
Bu desen bildirilen AM ile uyumludur. Ayarlanan 735 MHz'ten yaklaşık
9,5 kHz farkın hangi cihaz saatinden veya kaynak ayarından geldiği
kalibre referans olmadan belirlenmez; mutlak frekans doğruluğu değildir.

Gerçek I/Q'nun float 4:1 örnek azaltma ve sentetik olay bağlamıyla
F5 tanısında 40/40 kayıt yeniden üretildi, 40/40 sınıf Belirsiz kaldı.
16/16 dB'de 14 pencere SNR/kalite, kalan altı model uzaklığı nedeniyle
reddedildi. 24/24 dB'de 20/20 model uzaklığı sınırını aştı; yalnız kazanç
artışı sorunu çözmedi. Taşıyıcı toplam 8/40, 24/24 dB'de 2/20 geçerliydi.
24/24 dB OBW 18/20 geçerli, 3,93–4,31 kHz; iki Belirsiz pencere korunur.
Güç bu kazançta −51,13 ile −49,56 dBFS; dBm veya TX gücü değildir.

Bu, dört fiziksel kayıttan alınan 40 penceredir; 40 bağımsız RF koşusu
sayılmaz. F5 bant sonucu ideal 1 kHz AM'in iki yan çizgisinin açıklığıyla
aynı büyüklük değildir; FFT çözünürlük/kenar düzeltmesi ve gürültü etkisi
ayrıştırılmadan doğru kabul edilmez. Ürün sınıflandırıcısı ve taşıyıcı
seçimi için bağımsız geliştirme çalışması gerekir. Gerçek AM/FM kayıtları
eşik ayarlama verisine çevrilmez. FPGA ve canlı ürün yolu kullanılmadı.
Kanıt `results/evidence/phase08/parameter-rf-am735-20260909.json` ve ZIP;
ham kayıtlar, analiz kaynakları ve ölçüm arşivleri özetleriyle doğrulandı.

## 9 Eylül 2026: fiziksel 735 MHz FM tanısı

Kullanıcı iki HackRF'in onaylı Faraday kabininde olduğunu ve vericinin
sürekli açık kaldığını bildirdi. Fotoğraftaki kaynak ayarı FM/Sine,
735 MHz, 1 kHz ton, Gain 0 / Amp 0'dır. Etiketsiz 10 kHz ve 12 kHz
alanları doğrulanmış sapma veya OBW referansı sayılmadı.

Sekiz adet 0,5 saniyelik ham RX kaydı alındı (her biri 4 milyon kompleks
CI8 örneği, 8 MS/s). İlk kapalı/açık çifti 0/0 dB'de hedef artışı vermedi;
bu negatif gözlem korunur. Sonraki açık kayıtlar 8/8, 16/16, 24/24 dB ve
735,3 / 734,7 MHz alıcı merkezlerinde alındı. Alıcı seri sonu 35138247,
RF amplifikatörü ve anten beslemesi kapalıdır. Başlangıçtaki 524288 kompleks
örnek analiz dışında tutuldu; 16/16 ve 24/24 dB yerleşmiş bölümlerinde ray
değerine ulaşan bileşen yoktur. Araç günlükleri USB taşması bildirmedi.

16/16 dB'de iki merkezde spektral tepe yaklaşık 734,9865 MHz'te tekrarlandı;
FM yan bandı olabileceğinden taşıyıcı olarak etiketlenmedi. Dört yüksek
kazanç kaydının FM faz farkı spektrumunda 998,94 Hz ton görüldü (2,31 Hz
analiz hücresi). Bu tek bilinen FM kaynağıyla uyumluluk tanısıdır; genel
Analog/Sayısal doğruluğu veya kalibre frekans ölçümü değildir.

Gerçek ham I/Q, float 4:1 örnek azaltma ile mevcut F5'e verildi. Dedektör
yerine sentetik olay bağlamı kullanıldı; bu canlı ürün, PL veya ARM kabulü
değildir. Dört kayıttan onar örtüşmeyen pencere: 40/40 yeniden hesaplama
eşleşti, sınıf 40/40 Belirsiz, taşıyıcı 40/40 Gözlenmedi. Tüm sınıf
kararlarında model uzaklığı sınırı aşıldı. 24/24 dB'de en yakın prototip
20/20 two_fsk idi; ret kapısı bu etiketi ürün sonucu olarak yayımlamadı.
Bilinen FM'i Sayısal göstermemek için ret korunmalıdır; bu kayıtlarla
eşik gevşetilmez veya test verisi üzerinde model eğitilmez.

24/24 dB F5 OBW sonuçları 13,76–14,59 kHz, güç −40,69 ile −40,10 dBFS
arasındadır. Bağımsız uzun Hann spektrumu tanısı 16,52 / 18,99 kHz verdi;
gürültü çıkarma ve pozitif kırpma yanlılığı içerdiğinden kesin referans
değildir. OBW doğruluğu bu karşılaştırmayla kapanmaz. dBFS kazanca bağlıdır;
TX çıkış gücü veya RF giriş dBm değeri olarak yorumlanmaz.

Kanıt: `results/evidence/phase08/parameter-rf-fm735-20260909.json` ve ZIP.
Ham kayıtlar, komut/ayar/zaman günlükleri, analiz kaynakları ve 40 ölçüm
ZIP'i hash bağlıdır. Tekrarlı pencereler bağımsız 40 fiziksel koşu sayılmaz.
16/16 ve 24/24 dB eşleşmiş kapalı referansı yoktur. Kart portları erişilebilir
olsa da çalışan hizmet/imaj kimliği doğrulanmadı; FPGA kullanılmadı.
PÇ-02, PÇ-03 ve ST-06 kabulü açık, üretim algoritması değişmedi.

## 8 Eylül 2026: güncel tekrar ve karar kapısı tanısı

Parametre çıkarımı tamamlanmadı. Kullanıcının devam talimatıyla PÇ-02
tanılaması sürdürüldü; cihazların bağlı olmadığı bildirildi. Fiziksel
frekans/güç kalibrasyonu ve PÇ-03–05 kabulü açık kalır.

Güncel kaynakla 30 kayıt yeniden üretildi; 30/30 yeniden hesaplama eşleşti.
Aşağıdaki 7 Eylül tablosundaki sayısal sonuçlar tekrarlandı. Bu aynı
tohum/ayar kümesinin tekrarıdır; bağımsız yeni doğruluk paydası değildir.

`scripts/diagnose_parameter_bench.py` arşiv ve güncel kaynak bütünlüğünü
doğrulayıp mevcut F5 karar kapılarını raporlar; ürün yöntemini değiştirmez.
24 modülasyonlu örneğin tamamı model uzaklığı sınırını aşar; sınıf yine
24/24 Belirsizdir. SNR kapısı bu örneklerde geçer. CW'de reddedilen beş
örneğin beşi çizgi güç payı kapısında, dördü ayrıca belirginlik ve dört-kare
belirginliği kapısında kalır. Kapı sayıları örtüşür, toplanmaz.

CW tanısında çizgi adayı bilinen taşıyıcıdan yaklaşık −5,56 ile +5,15 kHz
sapabilir. Kaynakta `carrier_evidence_v4`, dar çizgiyi tüm aralıkta aramak
yerine kestirilen emisyon merkezi hücresini kullanır. Merkez kayması böylece
çizgi kontrolünü yanlış hücreye taşıyabilir. Sonraki geliştirme ayrı
tohum/ayar verisinde merkez yanlılığını ve çizgi seçimini incelemelidir;
en güçlü çizginin her ailede taşıyıcı olduğu varsayılmaz. Sınıflandırma
uzaklık sınırını gevşetmek bu sonuçlarla gerekçelendirilmiş değildir.

```powershell
python scripts/validate_parameter_bench.py --output build/acceptance/parameter-bench-20260908-v1
python scripts/diagnose_parameter_bench.py build/acceptance/parameter-bench-20260908-v1 --output build/acceptance/parameter-bench-20260908-v1/diagnostics.json
python -m pytest tests/test_parameter_bench_diagnostics.py tests/test_measurement_record.py tests/test_phase04f5_product_profile.py tests/test_phase04f5_method_lock.py -q
```

Çıktı adları mevcutsa yeni ad kullanılmalıdır. 22/22 test geçti. Yeni tanı
testleri özgün kaydın korunmasını, ürün karar eşleşmesini ve bozuk arşiv
özetinin reddini sınar. Kanıt `results/evidence/phase08/parameter-diagnostic-20260908-v1.json`
ve ZIP içindedir; 35 girdinin özetleri ve ZIP bütünlüğü denetlendi.
Üretim eşikleri, profil, RTL, ARM hizmeti ve önceki kanıtlar değişmedi.

## 7 Eylül 2026: bağımsız sayısal başlangıç

Kapsam KTR-4.2 / KTR-4.2-F1, PÇ-02 tanılama ve mevcut sınıflandırmanın
başlangıç değerlendirmesidir. Tercihli özellikler ve ARM taşıması açılmadı.
Üretim eşikleri değiştirilmedi; bu örnekler üzerinde eşik ayarlanmayacak.

Çalıştırma (çıktı dizini yeni olmalıdır):

```powershell
python scripts/validate_parameter_bench.py --output build/acceptance/parameter-bench-20260907-v1
```

30 sentetik örnek: CW, AM (3 kHz ses, %60 derinlik), NFM (2 kHz ses,
5 kHz sapma), dikdörtgen BPSK (20 ksym/s), sürekli fazlı ikili FSK
(20 ksym/s, ±10 kHz), her ailede üç tohum ve 12/24 dB zaman alanı SNR.
Gerçek donanım kullanılmaz; olay bağı sentetiktir. Aynı ürün kayıt/kestirim
yolu çalışır, dedektör devre dışıdır. Böylece ölçüm matematiği ile tespit
sürekliliği ayrı incelenir. Her örnek tam I/Q, sonuç, kaynak özetleri ve
yeniden hesaplama kontrolüyle ayrı ZIP'tedir. 30/30 yeniden hesaplama eşleşti.

Referans taşıyıcı üretecin denkleminden, güç temiz I/Q ortalama karesinden,
OBW ise bağımsız 262144 örnekli Hann periodogramının %0,5/%99,5 noktalarından
gelir. OBW referansı yaklaşık 7,63 Hz çözünürlüklü sonlu kayıt kestirimidir;
ideal CW için sıfır genişlik iddiası değildir. Ürün 4096 FFT ve 8,192 ms
gözlem kullanır. Üretim sınıflandırıcısı referans üretiminde kullanılmaz.

| Aile | Adet | Taşıyıcı geçerli | Güç en büyük mutlak hata | OBW geçerli | OBW en büyük mutlak hata | Sınıf |
|---|---:|---:|---:|---:|---:|---|
| CW | 6 | 1 | 0,029 dB | 6 | 2,545 kHz | 6 Belirsiz |
| AM | 6 | 2 | 0,044 dB | 6 | 1,596 kHz | 6 Belirsiz |
| NFM | 6 | 2* | 0,019 dB | 6 | 1,987 kHz | 6 Belirsiz |
| BPSK | 6 | 0 | 0,189 dB | 3 | 325,644 kHz** | 6 Belirsiz |
| FSK | 6 | 0 | 0,024 dB | 6 | 6,322 kHz | 6 Belirsiz |

* NFM çizgisi taşıyıcı doğruluk paydasına alınmadı; yan bant ile taşıyıcının
aynı şey olduğu varsayılmaz. CW'de geçerli tek sonucun hatası 7,25 Hz;
AM'deki iki geçerli sonucun en büyük hatası 366,21 Hz. Yalnız geçerli
sonuçların küçük hatasını tüm örneklerin başarısı olarak sunmayın.

** Dikdörtgen BPSK'nin uzun spektral kuyrukları seçilen yaklaşık 225 kHz
aralığın dışına uzanır. Tablodaki karşılaştırma tam emisyon ile sınırlı
ürün aralığının farkını da içerir. Bu örnek kapsam dışı kontrolüdür;
dar aralıkta geçerli sayının tam emisyon OBW'si sayılması kabul edilemez.

Analog/sayısal uygulanabilir örnek sayısı 24; doğru karar 0/24, yanlış
karar 0/24, Belirsiz 24/24. CW'nin altı Belirsiz sonucu bu paydadan ayrıdır.
Bu küçük başlangıç kümesi genel doğruluk kabulü değildir. Tam rapor yerel
`build/acceptance/parameter-bench-20260907-v1/report.json` dosyasındadır.

## Fiziksel doğrulama düzeni

| Parametre | Bilinen referans | Ölçüm ve kayıt | Kabul yaklaşımı |
|---|---|---|---|
| Taşıyıcı | Önce denklemden CW; RF'de frekans referanslı üreteç veya ölçer | Hz hatası, ppm, sonuç verebilme oranı; birden fazla frekans ve SNR | Vericide girilen frekansın mutlak doğruluğu ayrıca bilinmeli; iki serbest saat hatası ayrıştırılamaz. |
| OBW99 | Bağımsız uzun temiz I/Q, RF'de spektrum analizörünün OBW99 ölçümü | Bant kenarları ve toplam genişlik hatası; AM/NFM/FSK, komşu ve kenar kontrolü | CW çözünürlük tabanını gösterir; tek başına modülasyonlu bant doğrulamaz. RF ve yazılım aynı toplam emisyonu kapsamalı. |
| Güç | Sayısalda ortalama kare; RF'de alıcı SMA girişinde bilinen dBm | Aynı seri/frekans/kazanç/örnekleme/ölçek için referans ve okunan değer | Kalibrasyon noktaları ile bağımsız kontrol noktaları ayrı; doyum/gürültü tabanı dışında hata ve belirsizlik raporlanır. |
| Analog/Sayısal | Kaynağı bilinen AM/NFM ve OOK/FSK/PSK/QAM | Aile bazlı doğru/yanlış/Belirsiz; farklı içerik, SNR ve hız | CW ayrı belirsiz kontrol; test verisiyle model/eşik ayarı yapılmaz. |

RF öncesi kablo/zayıflatıcı kaybı ve ölçüm referans düzlemi kaydedilir.
HackRF alıcı giriş sınırı -5 dBm'dir; doğrudan iki RF portu bağlanmaz,
bilinen zayıflatma ve kaynağın en yüksek çıkışı hesaba katılır.
Kalibrasyon: C = referans_dBm − ölçülen_dBFS; aynı geçerlilik alanında
P_dBm = P_dBFS + C. Tek C farklı cihaz, frekans, kazanç veya sayısal ölçeğe
taşınmaz. Kalibrasyon dışındaki değerler dBm olarak sunulmaz.

Her koşul için en az 10 bağımsız kayıt planlanır; iptal, kırpılma, kayıp
tespit ve Belirsiz sonuçlar paydadan çıkarılmaz. Deneme sırası ve verici
ayarları önceden yazılır. Referans cihazın belirsizliği öğrenildikten sonra
RF kabul toleransları ölçümden önce sabitlenir; sonuca göre genişletilmez.
Yalnız iki kalibrasyonsuz HackRF varsa sayısal doğrulama, göreli güç ve
tekrarlanabilirlik yapılabilir; mutlak RF dBm kabulü açık kalır.

## Uygulama sırası

1. Canlı tespit listesindeki seçim değişimini ve dört güncel gözlem bağını
   birlikte düzelt; eski kaydı güncel kabul ederek engeli aşma.
2. CW/AM taşıyıcı abstention nedenlerini ve geniş manuel aralığın sınıf
   özelliklerine etkisini ayrı geliştirme verisinde incele.
3. Bant sınırlı sayısal örnekler, güç basamakları, gürültü, komşu, aralık
   kenarı ve kırpılma kontrolleri ekle. Tam emisyonun aralık dışına taşması
   bağımsız kapsam kontrolü olarak kalsın.
4. Referans cihazla frekans/güç kalibrasyonu ve bağımsız kontrol ölçümleri.
5. Dondurulmuş yöntemle yeni tohum/ayar ailesinde kör son değerlendirme.

Kaynaklar: [HackRF kazanç kontrolleri](https://hackrf.readthedocs.io/en/latest/setting_gain.html),
[HackRF giriş sınırı](https://hackrf.readthedocs.io/en/stable/hackrf_one.html),
[ITU-R SM.443-4 bant ölçümü](https://www.itu.int/rec/R-REC-SM.443-4-200702-I/en).
