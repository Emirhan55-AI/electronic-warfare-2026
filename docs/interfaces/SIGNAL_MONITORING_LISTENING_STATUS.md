# Sinyal izleme ve dinleme: güncel durum

## 820 MHz canlı NFM ürün koşusu — 13 Eylül 2026

Kullanıcının kontrollü laboratuvarda açık olduğunu bildirdiği `820 MHz`,
`50 kHz` azami sapmalı ve `1 kHz` tonlu NFM yayını, kaynak arayüzü üzerinden
HackRF → kanal seçici → FPGA/ARM tespit → PC dinleme zincirinde işlendi.
RX `16/16 dB`, otomatik kazanç açık ve FPGA çıkışı `2 MS/s` idi. Canlı aday
seçim anında `819,9863 MHz`, FPGA + RX spektrumu uyumlu ve `35,3 dB` tepe/gürültü
olarak sunuldu; bu değer yayıncı kimliği değildir.

İlk denemede beş saniyelik tampon sık sık sıfırlanıyordu. Kök neden, ARM
yanıtındaki `active` yaşam döngüsü tablosunda tutulan fakat o karede gözlenmeyen
eski confirmed kayıtların eşzamanlı ikinci sinyal sayılmasıydı. Kanal kapısı
artık yalnız aynı karede gerçekten gözlenen birden fazla eşleşmeyi belirsizlik
olarak reddeder. Gözlenmeyen yaşam döngüsü kayıtları ve kısa olay-kimliği
boşlukları mevcut `%95`/en çok sekiz ardışık eksik kare kapısından geçer;
uzun kayıp yine tamponu sıfırlar. Operatör kanal frekansı olay kimliği
değişirken sabit tutulur. Ayrıca canlı öneriler operatörün yazdığı ofset veya
bant genişliğini her arayüz yenilemesinde ezmez.

Düzeltme sonrası `120 kHz`, `0 kHz` ofsetli NFM hazırlığı `5,001 s` canlı
girdiden `5,000 s`, `48 kHz` mono PCM16 ses üretti. `2.442` karenin `2.422`'si
gözlendi; en uzun boşluk üç kareydi ve süreklilik doğrulandı. Baskın ses
bileşeni `1,02301 kHz`, kanal gücü `−31,69…−28,58 dBFS`, artık merkez değişimi
`−667,8…+303,0 Hz` oldu. Oynat ve durdur işlemleri gerçek arayüzde geçti.

Aynı bildirilen yayında iki canlı parametre kaydı emisyon merkezini
`819,985633 / 819,962533 MHz`, OBW'yi `422,087 / 451,932 kHz`, kanal gücünü
`−31,340 / −28,193 dBFS` verdi. PC sınıflandırıcısı ikisini de yüksek güvenle
`Analog` gösterdi; kayıtların `accuracy_proven` ve sınıflandırma
`product_acceptance` bayrakları yine `false` kaldı. Parametre ile dinleme aynı
RF bağlamında kanıt paketine bağlandı, ancak doğrudan parametre-sonucu
`Dinleme İçin Yeniden Al` arayüz devri bu düzeltmeden sonra yeniden
tekrarlanmadı.

Kaynak bağı, iki kayıt SHA-256 özeti, ayrıntılı sonuçlar ve sınırlar
[`live-820mhz-e2e-product-20260913.json`](../../results/evidence/phase08/live-820mhz-e2e-product-20260913.json)
içindedir. İlgili 182 yazılım/QML testi geçti. Bu tek, dalga biçimi önceden
bildirilmiş açık koşudur; eşleştirilmiş kapalı/yanlış-kanal negatifi, kör tekrar,
gerçek konuşma anlaşılabilirliği, telsiz pre-emphasis profili, yayıncı kimliği
ve genel Pd/Pfa kabulü değildir. PHASE-08/ST-06 ile tam KTR-4.3 fiziksel kabulü
açık kalır.

## Şartname ve KTR eşlemesi

Şartnamenin `5.1.3 Sinyal İzleme/Dinleme` maddesi depoda `KTR-4.3` ile
izlenir. Zorunlu yarışma akışı `tespit → parametre çıkarımı → izleme/dinleme`
sırasındadır. Zorunlu dinleme hedefi analog amatör telsizdir. Sayısal amatör
telsizin dinlenmesi ilave puan kapsamındadır; analog kabul kapanmadan sayısal
protokol varsayılmaz.

## Gerçekten uygulanmış olanlar

- Seçili doğrulanmış olay için AM zarf demodülasyonu ve NFM ardışık faz farkı
  demodülasyonu gerçek kompleks I/Q örneklerini işler. Üretilen ses 48 kHz,
  mono PCM16'dır; oynatılabilir ve WAV olarak dışa aktarılabilir.
- DDC, 129 tap anti-alias ve kanal FIR'ı, durum korumalı örnek azaltma, 65 tap
  ses filtresi, DC giderimi ve sınırlı normalizasyon çalışır. Beş ile yirmi
  saniye arasındaki kesintisiz kayıtlar blok sınırlarında NCO, FIR, decimator
  ve NFM ayrıştırıcı durumunu korur.
- NFM sesine birinci derece `750 µs` de-emphasis uygulanır; bu, 6 dB/oktav
  telsiz konuşma karakteristiğinin yazılım karşılığıdır. NFM ses bandı 12,5 kHz
  kanalda 2,55 kHz, daha geniş kanalda 3 kHz ile sınırlandırılır. Gerçek telsiz
  profilinin bu varsayımla eşleşmesi fiziksel kabulte kaydedilecektir.
- Canlı ürün yolu, HackRF'ten alınmış, karta gönderilmiş ve kart yanıtıyla
  eşleşmiş `2 MS/s` CI8 karelerin son `5,001216` saniyesini kullanır. Tampon
  `2.442` kare ve yaklaşık `19,1 MiB` ile sınırlıdır. Bir sıra boşluğu tamponu
  sıfırlar. Seçili RF kanalı pencere boyunca ARM'da `confirmed` kanıt ister;
  olay kimliği değişebilir. Aynı karede kanala uyan birden fazla gözlenen olay
  belirsizliktir. Yaşam döngüsü tablosunda tutulan fakat o karede gözlenmeyen
  kayıtlar ikinci yayın sayılmaz. Karelerin en
  az `%95`'inde yeniden gözlenmesi ve ardışık gözlenmeme boşluğunun en çok `8`
  kare (`16,384 ms`) olması gerekir. Böylece tek karelik CFAR salınımı sesi
  bütünüyle düşürmez; sekiz kareyi aşan kanal kaybı kapıyı kapatır. Arayüz
  gözlenen kare sayısını ve en uzun boşluğu bildirir.
- Kanal gücü ve artık merkez frekansı 250 ms pencerelerle izlenir. Güç
  `10 log10(mean(|x|²)) dBFS`; artık frekans
  `angle(sum(x[n]·conj(x[n−1]))) Fs/(2π)` ile hesaplanır. Arayüz güç aralığını,
  frekans değişimini, gözlem noktası sayısını ve canlı tespit sürekliliğini
  gösterir.
- Parametre ölçümünden gelen emisyon merkezi ve OBW %99 dinleme aşamasına
  devredilir. Önerilen kanal genişliği OBW'nin `1,2` katıdır ve desteklenen
  `2–200 kHz` sınırına alınır. Canlı kaynakta eski olay kimliği taşınmaz; aynı
  frekanstaki yayın yeni FPGA oturumunda yeniden doğrulandıktan sonra seçilir.

Bu işlemler boş veya sabit arayüz değeri üretmez. DSP gerçek I/Q dizisini
işler. Buna karşı bugünkü olumlu doğruluk kanıtı sentetik ve kayıtlı I/Q
üzerindedir. Canlı bir amatör telsiz konuşmasının hoparlörden anlaşılır biçimde
duyulduğuna dair fiziksel kabul kanıtı henüz yoktur.

## İşlem yeri

| İş | Çalıştığı yer |
|---|---|
| Canlı I/Q alma ve 8→2 MS/s kanal seçimi | PC / HackRF host yolu |
| Hann, FFT, güç ve sinyal tespiti | FPGA PL |
| Tespit yaşam döngüsü ve teknik parametreler | ZedBoard ARM |
| Beş saniyelik I/Q tamponu, AM/NFM demodülasyonu, ses ve WAV | PC |

Dinlemenin PC'de olması sahte veri anlamına gelmez. FPGA geri I/Q üretmediği
için PC, karta göndermiş olduğu özgün I/Q'yu yalnız kart yanıtı doğrulandıktan
sonra kullanır. Ses çıkışı zaten PC'dedir; bu yerleşim ek kart→PC ses protokolü
ve ARM yükü getirmez. Yarışma belgesi dinleme algoritmasının FPGA'da olmasını
zorunlu kılmıyorsa mevcut sahiplik daha düşük entegrasyon riski taşır. ARM'a
taşımak mümkündür, fakat önce ARM süre/bellek ölçümü ve sürümlü ses taşıma
sözleşmesi gerekir.

## Kanıt durumu

- Temiz AM/NFM, 20 dB sentetik SNR, noise-only negatif kontrol, PCM/WAV
  bütünlüğü ve blok bölme değişmezliği doğrulanmıştır.
- Bilinen `−200…+200 Hz` doğrusal kayma verilen beş saniyelik AM sahnesinde
  20 adet 250 ms gözlem üretilmiş; ilk ve son pencere hataları `2 Hz` sınırının
  altında kalmıştır. Tek blok ile 4096 örnekli bloklar aynı PCM ve gözlem
  dizilerini üretmiştir.
- Tekrarlanabilir kanıt:
  `results/evidence/phase05/monitoring-observation-v1.json`. Canlı veri boyutu
  host gözlemi `results/evidence/phase05/monitoring-live-scale-host-20260911.json`
  içindedir.
- 820 MHz canlı tespit, iki parametre tekrarı ve NFM hazırlama/oynatma sonucu
  `results/evidence/phase08/live-820mhz-e2e-product-20260913.json` içindedir.
  Kaynak bağına karşı 182 yazılım/QML testi geçmiştir; bu tek açık koşu fiziksel
  kabul paydası değildir.
- Korunmuş fiziksel HackRF NFM tekrar kaydının `5,001216` saniyesi güncel yerel
  8→2 MS/s kanal seçici ve dinleme DSP'sinden geçirilmiştir. Çıkışta `1.700 Hz`
  referansa karşı `1.699,951172 Hz` baskın ses (`0,048828 Hz` hata), 20 kanal
  gözlemi ve sıfır kırpılma elde edilmiştir. Kanıt
  `results/evidence/phase05/real-nfm-replay-monitoring-20260911.json` içindedir.
  Bu kayıt gerçek RF taşıma içerir; içeriği gerçek konuşma değil, RF üzerinden
  tekrar oynatılmış sentetik NFM tonudur ve fiziksel ürün kabulü sayılmaz.
- Çalıştırma:
  `python scripts/verify_phase05_monitoring_observation.py --check` ve
  `python scripts/benchmark_phase05_live_scale.py --check`;
  gerçek kayıt tanısı için
  `python scripts/evaluate_phase05_real_nfm_recording.py --check`; regresyon için
  `python -m pytest tests/test_phase05_monitoring.py tests/test_live_ed_view_model.py -q`.
- Güncel Windows standalone ürün paketi
  `dist/operator-console-20260911/BAZ.dist/baz_operator_console.exe` olarak
  üretilmiştir. Başlangıç smoke testi çıkış kodu `0` vermiş; parametre ve tespit
  QML panelleri, iki işlem profili, HackRF alıcı/spur yapılandırmaları ve yerel
  kanal seçici DLL paket içinde doğrulanmıştır. Tekrarlanabilir yerel denetim
  `python scripts/verify_phase05_product_package.py --check`, kayıt ise
  `results/evidence/phase05/listening-product-package-20260911.json` içindedir.
  Bu yalnız paket bütünlüğü ve başlangıç kanıtıdır; donanım kabulü değildir.

## Açık kabul kapıları

1. HackRF ve gerçek analog amatör telsizle sessiz/açık/sessiz kayıt; doğru
   frekans, doğru AM/NFM seçimi, anlaşılır ses, sıra kaybı, kırpılma ve yanlış
   kanal negatifleri ölçülecek.
2. Kullanılacak telsiz modelinin kanal aralığı, sapması ve pre-emphasis
   karakteristiği kaydedilecek. NFM de-emphasis profili bu bilgiye göre
   sabitlenecek; bilinmeyen bir zaman sabiti varsayılan başarı gibi sunulmayacak.
3. Parametre sonucu ile dinleme sonucunu tek kanıt paketinde bağlayan canlı
   ürün koşusu yapılacak. Bugünkü arayüz geçişi birim/QML testinde geçmiştir;
   fiziksel akış değildir.
4. Sayısal dinleme ancak telsizin gerçek protokolü belirlendikten sonra ayrı
   kapsamda ele alınacak. DMR, dPMR, C4FM gibi yollar birbirinin yerine
   kullanılamaz; şifreli içerik çözülmüş gibi gösterilmez.

Zorunlu analog iş teknik olarak yapılabilir durumdadır ve ana DSP zinciri
hazırdır. Kalan ana risk algoritmanın varlığı değil, gerçek telsiz profiline
uygun ses karakteristiği ve fiziksel RF kabulüdür. Sayısal dinleme ayrı ve daha
zor bir protokol/kodek işidir; zorunlu analog kapanışını geciktirmemelidir.
