# Dört parametre doğrulaması

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
