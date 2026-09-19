# Sinyal izleme ve dinleme: güncel durum

## Seçili kanal sahipliği düzeltmesi — 19 Eylül 2026

Canlı dinleme kapısındaki `50 kHz` olay izleme toleransı artık seçili frekansı
gerçekte kapsamayan yakın bir FPGA adayını aynı kanalın ikinci sahibi saymaz.
Seçili frekansı ölçülen alt/üst sınırları içinde taşıyan tek gözlenen ve
doğrulanmış olay varsa beş saniyelik kanal doğrulaması ilerler; seçili frekansı
aynı anda kapsayan iki olay veya yalnız tolerans alanında kalan iki ayrı aday
yine belirsiz kabul edilerek fail-closed durur. Böylece dolu I/Q tamponunda
yakın komşu aday yüzünden AM/FM karşılaştırma düğmesinin gereksiz yere kapalı
kalması giderildi. FPGA tespiti, eşikler, RTL/ARM ve `%95`/sekiz-kare süreklilik
kapıları değişmedi. Kaynak regresyonu fiziksel RF kabulü değildir; KTR-4.3 ve
PHASE-08/ST-06 kabul kapıları açık kalır.

## Kesintisiz analog dinleme ve görünür kanal izlemesi — 18 Eylül 2026

KTR-4.3 canlı analog yolunda beş saniye artık dinleme süresi sınırı değildir.
İlk `5,001216 s` ardışık I/Q, seçilen kanalın FPGA/ARM tarafından doğrulanması,
en az `%95` gözlem ve en çok sekiz ardışık eksik kare kapısı için başlangıç
tamponudur. Bu kapı geçildikten sonra aynı HackRF → FPGA/ARM RX oturumu
durdurulmadan, yalnız yeni ve sıra numarası ardışık kareler yaklaşık `0,25 s`
parçalar halinde PC'deki durum koruyan AM/NFM çözücüye verilir. Operatör
`Durdur` diyene, RX oturumu bitene veya süreklilik kapısı kapanana kadar canlı
dinleme sürer. I/Q penceresi beş saniye, dışa aktarılabilen PCM16/WAV geçmişi
son yirmi saniye ile sınırlıdır; sınırsız bellek kuyruğu yoktur.

Canlı çözücü NCO fazını, RF/ses FIR geçmişini, örnek azaltma ve yeniden örnekleme
fazını, NFM önceki örneğini, 30 Hz DC kesiciyi, seçili 200 Hz konuşma filtresini,
de-emphasis ve yavaş AGC durumunu parçalar arasında korur. Tüketici geride
kalırsa, sıra boşluğu oluşursa veya seçili kanalın doğrulanması kaybolursa ses
parçaları sessizce birleştirilmez; akış fail-closed durur. Sonuç kartında kanal
frekansı, süreklilik, anlık güç ve frekans değişimi; ayrı grafikte ise 250 ms
çözünürlüklü zamansal güç/frekans izi görünür.

Yayın türü bilinmiyorsa operatör AM ve FM'i tek tek ayrı kayıtlarla denemek
zorunda değildir: `AM / FM Karşılaştırmasını Hazırla`, aynı doğrulanmış I/Q
penceresinden iki sonucu tek işlemde üretir. Bu yol otomatik modülasyon tanıma
değildir ve karşılaştırma için sabit beş saniyelik kayıt kullanır. Operatörün
seçtiği AM veya NFM ile kesintisiz akış başlatmak yeni canlı kanal doğrulaması
gerektirir.

Analog sinyalleşmede yalnız standart DTMF çifti, süre/dominans/twist kapılarıyla
tutucu biçimde çözümlenir. CTCSS/DCS, 5-ton, AFSK/AX.25, konuşma karıştırıcıları,
şifreleme veya bilinmeyen analog veri için genel çözücü yoktur; arayüz bunu
`diğer kodlar incelenmedi` diye açıkça belirtir. Bu, amatör telsiz konuşma
içeriğini ya da şifreyi çözme iddiası değildir.

Durum koruyan NFM yolunun altı saniyelik girdiyi tek parça ve 0,5 saniyelik
parçalarla bit düzeyinde aynı PCM16 üretmesi, DTMF `5#` kabulü ve tek 1 kHz tonun
reddi, yalnız yeni canlı karelerin verilmesi ve geride kalan tüketicide açık sıra
boşluğu regresyonlarla doğrulandı. Gerçek hoparlör gecikmesi, uzun süreli gerçek
telsiz konuşma anlaşılabilirliği, vericiye özgü pre/de-emphasis eşleşmesi ve
kontrollü RF kabulü yeniden ölçülmedi. Bu nedenle kaynak yeteneği uygulanmıştır;
KTR-4.3 fiziksel kabulü ve PHASE-08/ST-06 açık kalır, yeni faz açılmamıştır.
Yöntem ve tekrarlanabilir komutlar
`docs/reviews/CONTINUOUS_ANALOG_LISTENING_20260918.md` içindedir.

## Bilinmeyen yayınla dinleme — 16 Eylül 2026

Mevcut KTR-4.3 yolu için `Bilmiyorum · AM/FM karşılaştır` seçimi eklendi.
Aynı sınırlı I/Q penceresinden AM ve dar bant FM sonuçları hazırlanır; kullanıcı
sonuçlar arasında geçer. Bu bir modülasyon sınıflandırıcısı değildir. Sonuçtaki
`Çözümleme` alanı uygulanan yöntemi gösterir, ölçülmüş yayın türünü göstermez.
Kanal genişliği anlaşılır seçeneklerle, frekans düzeltmesi ve de-emphasis
`İnce ayar` altında sunulur. Ölçülen OBW 25 kHz'i aşıyorsa dar bant yolun tüm
sinyali kapsamadığı belirtilir; sınırlandırılmış öneri OBW diye etiketlenmez.

İsteğe bağlı konuşma filtresi, normalizasyondan önce 200 Hz kesimli 1025 tap
FIR yüksek geçiren süzgeç uygular. Mevcut 2,55/3 kHz üst ses sınırı korunur.
Filtre konuşma bandı içindeki gürültüyü veya bilinmeyen sayısal protokolü
çözmez. AM/FM karşılaştırması ek DSP işi yapar; hız artışı iddiası yoktur.

Canlı yol son 5,001216 saniyeyi sabitleyip alımı durdurarak ses üretir;
kesintisiz hoparlör akışı değildir. Güç/frekans grafikleri bu kayıt penceresini
izler. Genel AM/FM tanıma, WFM, sayısal protokol/kodek çözümü ve gerçek telsiz
konuşmasıyla yeni fiziksel kabul yoktur. PHASE-08/ST-06 ve KTR-4.3 kabulü açık
kalır; yeni faz açılmadı. Yöntem, testler ve sınırlar
`docs/reviews/LISTENING_ASSISTANCE_20260916.md` içinde kayıtlıdır.

## Analog ses profili ve sade izleme görünümü — 16 Eylül 2026

Dinleme zinciri gerçek I/Q üzerinde AM zarfı veya NFM faz farkını çözerek
48 kHz mono PCM16/WAV üretir. Kullanıcının duyduğu fakat boğuk bulduğu canlı
ses, işlevin çalıştığını gösterir; konuşma anlaşılabilirliği için fiziksel kabul
kanıtı değildir. İncelemede NFM kanalına parametre ölçümündeki 200 kHz'e kadar
çıkan OBW önerisinin taşındığı ve eşleşen verici profili kanıtlanmadan 750 µs
de-emphasis uygulandığı görüldü.

Analog konuşma dinlemesi artık 2–25 kHz kanal sınırında çalışır; parametre
önerisi 6–25 kHz'e alınır. NFM varsayılanı `Net ses` profilidir ve de-emphasis
uygulamaz. `Telsiz düzeltmesi · 750 µs` yalnız vericinin pre-emphasis profili
biliniyorsa operatörce seçilir. Demodüle konuşma, 48 kHz'e çevrilmeden önce
257 tap alçak geçiren süzgeçle bant sınırlandırılır; böylece örnek azaltmada
yüksek frekanslı ayrıştırıcı gürültüsünün ses bandına katlanması bastırılır.

Arayüzde yayın türü, frekans düzeltmesi, alım bant genişliği, ses profili ve
ses seviyesi kalır. Sonuç özeti yayın türü, frekans, bant, ses profili, alım
seviyesi ve frekans sapmasıyla sınırlıdır. Ses dalga biçimi ile beş saniyelik
seviye/frekans kararlılığı grafiği korunur; teknik süreklilik sayaçları arayüzde
gösterilmez fakat canlı kabul kapısında uygulanmaya devam eder.

Bu değişiklik sentetik AM/NFM, 20 dB SNR, blok sürekliliği, de-emphasis ve
yüksek frekans alias reddi regresyonlarıyla doğrulanır. Yeni kaynakla gerçek
telsiz konuşması tekrarlanmadığından KTR-4.3 fiziksel kabulü açık kalır.

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
- DDC, 129 tap anti-alias ve kanal FIR'ı, 257 tap örnekleme öncesi konuşma
  filtresi, durum korumalı örnek azaltma, 65 tap çıkış ses filtresi, DC giderimi
  ve sınırlı normalizasyon çalışır. Beş ile yirmi
  saniye arasındaki kesintisiz kayıtlar blok sınırlarında NCO, FIR, decimator
  ve NFM ayrıştırıcı durumunu korur.
- NFM varsayılanı de-emphasis uygulamayan `Net ses` profilidir. Birinci derece
  `750 µs` düzeltme yalnız operatörün seçtiği isteğe bağlı telsiz profilidir.
  NFM ses bandı 12,5 kHz kanalda 2,55 kHz, daha geniş kanalda 3 kHz ile
  sınırlandırılır. Gerçek telsiz profilinin bu seçimle eşleşmesi fiziksel
  kabulde kaydedilecektir.
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
  süreklilik kapısını arka planda uygular.
- Dinleme kartındaki süre yalnız ardışık I/Q veri birikimini gösterir. FPGA
  hedef kanalı kısa süre kaybettiğinde süre başa dönmez; beş saniye dolduktan
  sonra `hedef sinyal kesiliyor` durumu ayrı gösterilir. Böylece alıcı veri
  kesintisi ile sinyal doğrulama kararsızlığı birbirine karıştırılmaz.
- Kanal gücü ve artık merkez frekansı 250 ms pencerelerle izlenir. Güç
  `10 log10(mean(|x|²)) dBFS`; artık frekans
  `angle(sum(x[n]·conj(x[n−1]))) Fs/(2π)` ile hesaplanır. Arayüz güç aralığını,
  frekans değişimini sade sonuç alanında ve kararlılık grafiğinde gösterir.
- Parametre ölçümünden gelen emisyon merkezi ve OBW %99 dinleme aşamasına
  devredilir. Önerilen kanal genişliği OBW'nin `1,2` katıdır ve analog konuşma
  için `6–25 kHz` öneri sınırına alınır; DSP sözleşmesi `2–25 kHz` kabul eder.
  Canlı kaynakta eski olay kimliği taşınmaz; aynı
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
