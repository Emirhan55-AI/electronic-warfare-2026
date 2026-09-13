# Elektronik Harp Operatör ve FPGA Sinyal İşleme Sistemi

13 Eylül 2026 ürün kapsamı: uygulama yalnız Elektronik Destek (ED) sistemiyle
devam eder. Elektronik Taarruz çalışma alanı, görev/TX kodu, yapılandırması ve
ET'ye özel testler kaldırılmıştır. Önceki tarihli ADR ve ölçüm dosyaları yalnız
geçmiş kayıt olarak korunur; güncel ürün yeteneği değildir.

13 Eylül otomatik canlı parametre ve kayıt bakımı: iki HackRF seri numarası
birincil/ikincil RX rolü olarak ayrı izlenir. Birincil canlı yol korunur;
ikincinin eşzamanlı işlenmesi fiziksel kanıt bulunmadan çalışıyor gösterilmez.
Destekleyen kart köprüsünde confirmed sinyaller tespit sürerken güç sırasıyla
dört-kare PL/ARM parametre gözlemine girer. Eski köprü yetenek sorgusunu
yanıtlamazsa tespit kesilmeden otomasyon kapanır. Sonuçlar SQLite kataloğunda
dBFS'e göre sıralı görünür ve CSV çıkarılabilir. dBm yalnız tam eşleşen,
süresi geçmemiş ölçülmüş alıcı profiliyle açılır; varsayılan profil boştur.
Yazılım/C/loopback testleri geçti, fakat bu değişiklik güncel kart imajı veya
iki HackRF fiziksel kabulü değildir.

Güncel kaynakla yapılan sınırlı 820 MHz tanısında yalnız birincil HackRF
göründü ve kartın kalıcı köprüsü yeni canlı parametre yeteneğini bildirmedi.
16/16 dB giriş kırpılmasında güvenli durdu; daha düşük kazanç koşularında
kalıcı confirmed hedef oluşmadı. 8.192 karelik koşu gerekli gerçek-zaman hızının
biraz altında kaldı. Başarı iddiası üretilmedi; tamamlanan koşulardaki sıfır
USB/taşıma hatası ve açık kabul sınırları
[tanı kaydındadır](results/evidence/phase08/automatic-inline-parameter-diagnostic-20260913.json).

13 Eylül parametre sonuç görünürlüğü: ölçüm tamamlandığında dört ana alanın
değeri ve geçerlilik durumu Parametre ekranında birlikte gösterilir. Teknik
doğrulama yeni sonuçta otomatik açılır; kaynağa göre kart veya kayıtlı I/Q kalite kapısı, gürültü referans
farkı, tespit anlamlılığı, merkez kararsızlığı ve zamansal OBW kenar değişimi
artık kayıt dosyasına gitmeden okunabilir. Arayüz bu alan geçerliliğinin
fiziksel doğruluk kabulü olmadığını açıkça belirtir. İlgili 94 regresyon geçti.

13 Eylül 820 MHz canlı ürün koşusu: bildirilen NFM ton yayını kaynak
arayüzünde tespit edildi, iki P0PM-v2 parametre tekrarı alındı ve beş saniyelik
NFM ses hazırlandı; oynat ve durdur işlemleri geçti. Dinleme tamponunu
gözlenmeyen eski olay kaydını eşzamanlı ikinci yayın sanarak sıfırlayan sorun
düzeltildi. Seçili kanal olay kimliği değişirken korunuyor ve operatörün
dinleme alanları canlı yenilemede ezilmiyor. İlgili 182 test geçti.
[Kanıt ve sınırlar](results/evidence/phase08/live-820mhz-e2e-product-20260913.json).
Bu önceden bildirilen tek açık koşudur; PHASE-08/ST-06, eşleştirilmiş negatif,
kör tekrar, gerçek konuşma ve genel Pd/Pfa kabulü açıktır.

12 Eylül geniş aralık düzeltmesi: canlı analiz taslağı artık geniş FPGA adayını
512 hücreye kesmez. P0PM-v2 kart yolu 8–3984 hücreyi destekler; sayısal hesap
PL/ARM'da kalır. Kart hizmeti ve ağ köprüsü doğrulanmış ZedBoard'un SD açılış
imajına yüklenmiş; kontrollü yeniden başlatmada doğru özetlerle otomatik
açılmıştır. Altı dar regresyon sahnesi ve gerçek kayıtlı geniş P0PM-v2 ölçümü
fiziksel PL/ARM yolunda geçmiştir. OBW kararsızlık kapısı ve genel RF doğruluğu açıktır.
[Durum ve sınırlar](docs/interfaces/P0_ARM_PARAMETER_RUNTIME_CONTRACT.md).

Canlı parametre akışı tek tıklamadır: `Aralığı Onayla ve Parametreleri Çıkar`.
Aday sınırı kareler arasında değişirse dört ardışık FPGA gözleminin birleşimi
kart sınırları içinde otomatik kullanılır; geçici eksik karede istek kaybolmaz
ve sahiplik denetimi alım durdurulmadan önce tamamlanır.

12 Eylül Analog/Sayısal entegrasyonu: `Parametreleri Çıkar` işlemi ilk üç
teknik parametreyi mevcut PL/ARM yolunda hesaplamayı sürdürür; aynı dört CI8
kare ayrıca PC'deki `digital_analog_detection` sınıflandırıcısına otomatik
verilir. Sonuç ana ölçüm kartında `Analog`, `Sayısal` veya güven yetersizse
`Belirsiz` olarak gösterilir. Modelin sentetik başarısı canlı RF kabulü
değildir; ürün bağlantısı `%90` güven kapısıyla deneysel ve fail-closed tutulur.
FPGA/ARM sınıflandırma kodu değişmedi.

13 Eylül yön ölçümü güncellemesi: hedef kanal bir kez seçilir. Tek ölçüm düğmesi
operatörün belirlediği başlangıç yönünü `0°` sayar; her başarılı ölçümden sonra
sıradaki hedefi otomatik olarak saat yönünde 15° ilerletir. Ürün ekranı yalnız
bağıl yön gösterir; serbest açı ve coğrafi kerteriz girişleri kaldırılmıştır.
Beş saniyede sonuç alınamazsa neden gösterilir ve açı ilerlemez. Kaynak
arayüzünü yeniden başlatmak gerekir; aşağıdaki 11 Eylül standalone paketi bu
düzeltmeyi içermez.
[Güncel akış ve kabul sınırı](docs/interfaces/SIGNAL_DIRECTION_FINDING_STATUS.md).

Genlik tabanlı yön bulma alan profili 15° adımlı 24 açı, 3 dB tepe ve ön/arka
kapıları, sabit hedef/alıcı bağı ve dairesel RMS hesabıyla uygulanmıştır.
Portable C/ARM çekirdeği Python referansıyla sıfır fark verdi; CRC korumalı
`P0DF-v1/P0FR-v1` yolu gerçek ZedBoard ARM'ında yedi sayısal sahneyi geçti.
Canlı ürün her açıda dört ardışık FPGA karesini kartın PL/ARM kanal gücü yolunda
ölçer ve 24 açı sonunda ARM sonucunu ister. Yön hizmeti kalıcı PetaLinux imajına
alınmış, yeniden başlatma ve yedi protokol sahnesi gerçek ZedBoard'da geçmiştir.
HackRF/yönlü anten ve bilinen bağıl açıyla fiziksel derece RMS kabulü açık olduğundan
henüz fiziksel yön doğruluğu iddia edilmez.
[Güncel yön bulma durumu](docs/interfaces/SIGNAL_DIRECTION_FINDING_STATUS.md).

Sinyal izleme/dinleme zinciri seçili gerçek I/Q kanalında AM veya NFM ses
üretir; beş saniyelik canlı tamponun sürekliliğini, 250 ms kanal gücü ve artık
merkez frekansı davranışını gösterir. Parametre ölçümünün merkez ve OBW sonucu
dinlemeye aktarılır, fakat canlı kaynakta yayın yeni FPGA oturumunda yeniden
doğrulanır. Sentetik/kayıtlı yazılım kapıları geçmiştir; gerçek amatör telsiz
sesi ve fiziksel ses kabulü henüz yapılmamıştır.
[Güncel izleme/dinleme durumu](docs/interfaces/SIGNAL_MONITORING_LISTENING_STATUS.md).
Korunmuş fiziksel HackRF NFM tekrar kaydında güncel zincir 1.700 Hz tonu
1.699,951 Hz olarak çıkarmıştır; yayın içeriği sentetik ton olduğu için bu sonuç
gerçek konuşma veya amatör telsiz kabulü değildir.
[Gerçek RF tekrar tanısı](results/evidence/phase05/real-nfm-replay-monitoring-20260911.json).
Güncel Windows standalone uygulaması
`dist/operator-console-20260911/BAZ.dist/baz_operator_console.exe` yolundadır;
QML ve zorunlu runtime varlıklarıyla başlangıç smoke testi geçmiştir.
[Paket doğrulama kaydı](results/evidence/phase05/listening-product-package-20260911.json).

Taşıyıcı frekansı, emisyon merkezi, OBW %99 ve kalibre edilmemiş kanal gücü
canlı ürün ölçümünde fiziksel FPGA güç çıkışı ile ZedBoard ARM'da hesaplanır;
PC yalnız dört seçili CI8 kareyi taşır, sonucu doğrular/kaydeder ve gösterir.
Altı fiziksel sayısal PL→ARM sahnesi ile 33 C referans sahnesi geçti. Kaynak,
FPGA, ARM hizmetleri ve cihaz ağacı PetaLinux 2025.2 açılış imajına alındı;
dört yeniden başlatmada FPGA ve hizmetler otomatik açıldı. Bu sonuç gerçek RF
doğruluğu veya dBm kalibrasyonu değildir.
[Kalıcı imaj kanıtı](results/evidence/phase08/parameter-persistent-image-20260911.json),
[parametre kart kanıtı](results/evidence/phase08/parameter-board-persistent-20260911.json).
OBW %99 sonucu onaylanan analiz aralığına koşulludur; aralık dışı uzun BPSK
kuyruklarını tutan 16.384 örnekli aday umut verici olsa da düşük SNR kapsamı ve
ARM eşdeğerliği doğrulanmadan ürüne alınmamıştır.
[OBW kapsama denetimi](results/evidence/phase08/parameter-obw-containment-audit-20260911.json).

CFAR normal/zayıf katsayıları ve FPGA FFT uzunluğu gerçek FPGA'ya kadar çalışma
sırasında değiştirilebilir ve karttan geri okunabilir. 4096/8192/16384 FPGA
FFT profilleri üçer bağımsız 4.096-kare koşuda sayısal hız kapısını geçti.
Fiziksel XFFT küçültme denemesinde DMA kilitlenmesi bulunduğundan aynı açılışta
yalnız daha büyük FFT'ye geçilir; küçültme güvenle reddedilir ve yeniden başlatma
4096 varsayılanını yükler. Pencere Hann olarak sabittir; HackRF RF doğruluğu ve
kontrollü Pd/Pfa kabulü tamamlanmadı.
[Güncel kapsam ve kanıt](docs/interfaces/DETECTION_RUNTIME_CONFIG_CONTRACT.md).
[SDRangel/GNU Radio karşılaştırması ve saha öncesi çalışma planı](docs/reviews/SIGNAL_DETECTION_COMPETITIVE_RESEARCH_20260911.md).

Tam tasarım Vivado 2025.2 ile 50 MHz'te yönlendirildi: WNS `+0,613 ns`, WHS
`+0,030 ns`, yönlendirme hatası sıfır; 24.251 LUT, 94,5 BRAM ve 61 DSP kullanır.
FPGA, DMA ABI v3, ARM hizmet ABI v4, Ethernet ve arayüz aynı etkin FFT değerini
kullanır. [Tekrarlı kart kanıtı](results/evidence/phase08/st06-runtime-fft-physical-repeated-20260911.json).

## Sinyal ayarları ve zayıf yol bakımı — 10 Eylül 2026

Tespit/görüntü ve bant taraması ayar panelleri eklendi. Destekleyen kartta tespit
FFT’si 4096/8192/16384 olarak FPGA'ya uygulanır; görüntü FFT’si ayrı kontroldür. DMA v2 zayıf aday
bilgisini ARM 24/32 yoluna bağlar. Güncel FPGA/hizmet birlikteliği sayısal
kart koşullarında doğrulandı; bu sonuç kontrollü RF Pd/Pfa kabulü değildir ve
ST-06 açık kalır.
[Ayarlar, kaynak dosyaları ve Vivado kılavuzu](docs/interfaces/DETECTION_TUNING_AND_SOURCE_GUIDE.md).

## Bant taramasından parametre çıkarımına geçiş — 10 Eylül 2026

Bant taraması sonucu için canlı yeniden doğrulamalı Parametre geçişi eklendi.
Seçilen frekans sabit alımda yeniden görülüp dört ardışık ölçüm karesi hazır
olmadan parametre seçimi oluşmaz. Bu arayüz akışı düzeltmesi tespit veya
parametre RF kabul durumunu değiştirmez.

## Dört parametrenin gerçek RF durumu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: yeni temiz AM koşusunda dar aralık SNR'si
13,36–15,32 dB iken sabit aday 10/10 Belirsiz kaldı. Yeni `rf_observation`
ürün dışı ön işlemesi uzun I/Q, FIR kanal süzme ve frekans kayması
hipotezlerini uygular; kesin sınıflandırıcı değildir. Kullanılabilir donanım
son beyana göre yalnız iki HackRF'dir; dBm kalibrasyonu diğer işleri durdurmaz.
Ürün/ARM/RTL ve önceki kabul durumları değişmedi.

[Ayrıntılı durum, araştırma ve yeniden üretim](docs/reviews/PARAMETER_EXTRACTION_ASSESSMENT.md).


## Replay BPSK G8 tanı koşusu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı `03_BPSK.C16` için Play teyidi verdi.
RX 24/24 dB kaydında 20,35–26,20 saniye arasında 5,90 saniyelik hedef bant
etkinliği görüldü. Bu süre RF öncesi hazırlanan 6 saniyelik BPSK dosyasıyla
uyumludur. Kayıtta bir USB taşması bulunduğu için koşu kabul paydasına alınmadı.

Dondurulmuş PC adayı 1,32–4,70 dB SNR nedeniyle 10/10 `low_snr` Belirsiz
üretti. AM, NFM ve BPSK fiziksel kayıtlarının aynı kalite kapısında kalması,
sorunun tekrar sayısından çok adayın gerçek Replay veri alanı ve SNR tanımıyla
uyumsuz olduğunu gösterir. Aynı koşu körlemesine tekrarlanmaz; yöntem ayrı
geliştirme verisiyle düzeltilip yeni kör RF ile sınanmalıdır. Ürün, fiziksel
analog/sayısal kabul ve dBm kalibrasyonu açık. Kanıt:
`results/evidence/phase08/replay-bpskg8-diagnostic-20260909.json` ve ZIP.

## Replay NFM G8 fiziksel tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: `02_NFM.C16` için RX 24/24 dB kaydı tam boyutta,
sıfır USB taşması ve sıfır kırpılmayla alındı. Faz ayrıştırıcı 1702,88 Hz
tepe ölçtü; RF öncesi hazırlanan dosyanın mesaj tonu 1700 Hz'dir. Çizgi
etkinliği yalnız kaba zaman seçimi için kullanıldı ve 21,50–27,25 saniye
aralığını işaretledi. NFM taşıyıcı bastırması nedeniyle bu işaretler güç veya
bant ölçümü olarak yorumlanmadı.

Dondurulmuş PC adayı, önceki temiz CW merkezi ve RF öncesi manifest aralığıyla
incelenen on pencerede −2,33 ile +0,99 dB SNR buldu; 10/10 sonuç `low_snr`
nedeniyle Belirsiz kaldı. Fiziksel NFM içeriği gözlendi, fakat analog/sayısal
sınıflandırma kabulü geçmedi. Model ve eşik bu kayıtla değiştirilmedi. Ürün F5,
ARM/FPGA, dBm kalibrasyonu ve genel fiziksel kabul açık. Kanıt:
`results/evidence/phase08/replay-nfmg8-evaluation-20260909.json` ve ZIP.

## Replay AM G8 ve aralık tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı AM G8 hazırlığını bildirdi; RX 24/24 dB
kapalı ve açık kayıtları tam boyutta, sıfır taşma/kırpılmayla alındı. Açık
kayıtta 6,15 saniyelik tek etkin bölüm ve 1699,22 Hz zarf tonu, hazırlanan
6 saniye/1700 Hz AM dosyasıyla uyumludur. Ayrı Play yanıtı kayda ulaşmadı;
TX Gain 8 ekran fotoğrafıyla doğrulanmadı. Sabit nominal 98,1 kHz aralıkta
10/10 sonuç 1,72–3,89 dB SNR nedeniyle Belirsiz kaldı.

Koşu sonrası tanıda aralık gözlenen 824990308 Hz çevresine taşındı. 8,3–16,1
kHz aralıklarda on pencerenin kalite kapısı geçti ve SNR 7,80–13,93 dB oldu;
Analog skor 0,64–0,83 ile sabit 0,90 eşiğin altında kaldı, 10/10 Belirsiz.
Bu sonradan yapılan aralık taraması kabul paydasına alınmaz. Bulgular seviye
ve aralık sorununun yanında gerçek Replay AM için model genelleme açığı
olduğunu gösterir; model/eşik bu kayıtla değiştirilmedi.

Sonraki aileler aynı sabit modelle değerlendirilir; gelecekteki yöntem
geliştirmesi ayrı sayısal veriyle yapılır ve yeni kör RF gerekir. Ürün F5,
ARM/FPGA, dBm ve genel fiziksel kabul açık. Kanıt:
`results/evidence/phase08/replay-amg8-evaluation-20260909.json` ve ZIP.


## Replay AM 32/32 dB karşılaştırması — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: verici kapalı 10 saniye ve AM penceresi RX 32/32
dB'de tam boyutta, sıfır taşma ve sıfır kırpılmayla alındı. AM kaydında
1699,22 Hz zarf tonu hazırlanan 1700 Hz dosyayla uyumludur; Play basışına
ait ayrı operatör yanıtı kayda ulaşmadı. Sabit aday on pencerenin tamamında
−9,09 ile +0,70 dB SNR ve `low_snr` nedeniyle Belirsiz kaldı. RX kazancını
24/24'ten 32/32 dB'ye çıkarmak aday SNR'sini iyileştirmedi; alıcı kazancı
daha fazla yükseltilmez.

Model/eşik değiştirilmedi. En düşük TX kazançta taşmasız CW bağlantısı
görüldüğünden sonraki kontrollü aday, Amp kapalı ve TX Gain 8 ile AM tekrar;
RX yeniden 24/24 dB'dir. Bu güç kalibrasyonu değildir. Verici kimliği,
genel fiziksel kabul, dBm ve ürün/ARM/FPGA kapıları açık kalır. Kanıt:
`results/evidence/phase08/replay-am32-evaluation-20260909.json` ve ZIP.


## Replay AM 24/24 dB değerlendirmesi — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: operatör doğru `01_AM.C16` dosyasını seçip Play'e
bastığını bildirdi. 825,3 MHz, 8 MS/s, RX 24/24 dB kaydı tam boyutta;
USB taşması ve kırpılma sıfırdır. Ayrı zarf tanısı 1699,22 Hz tepe buldu;
hazırlanan 1700 Hz AM mesajıyla uyumludur. Sabit v6 model/v9 adayın on
penceresi 2,04–4,38 dB ölçüm SNR'sinde 10/10 `low_snr` nedeniyle Belirsiz
kaldı. Bu fiziksel AM sınıflandırma kapısını geçmez; eşik/model değiştirilmedi.

Tek yayın kaydının on penceresi bağımsız on RF koşusu değildir. Verici seri
kimliği açık, dBm ve mutlak frekans kalibrasyonu yoktur. Ürün F5, ARM ve FPGA
kullanılmadı. Önceki yanlış dosya olasılıklı kayıt AM paydasına alınmaz ve
özgün tanısıyla korunur. Sıradaki kontrollü adım daha yüksek RX kazancında
kırpılma ve sınıflandırma kontrolüdür. Kanıt:
`results/evidence/phase08/replay-am24-evaluation-20260909.json` ve ZIP.


## Replay CW taşmasız gözlem — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı USB portunu değiştirip alıcıyı HackRF
moduna aldı. Aynı seri 35138247, 825,3 MHz, 8 MS/s ve 24/24 dB'de
10 saniyelik kapalı ve 30 saniyelik CW penceresi tam boyutta, sıfır taşma
ve sıfır kırpılmayla alındı. Kullanıcı Play basıldığını bildirdi. CW
824989819 Hz çevresinde 43/598 tanı penceresinde görüldü; sonrasında
örneklenen seviye eşik altına indi. 50 ms adımlı görünür aralık yaklaşık
2,15 saniyedir; hassas RF süre kalibrasyonu veya acil Stop testi değildir.

Tek temiz kayıt kalıcı USB çözümü sayılmaz; araç hâlâ aynı yolda dört
başka cihaz bildiriyor. Eski taşmalar korunur. AM denemesi öncesi kaynak
seçimi ve alıcı kayıt eşlemesi gerekir. Model/ürün/RTL/ARM değişmedi;
fiziksel genel kabul, verici kimliği ve dBm kalibrasyonu açık kalır.
Kanıt: `results/evidence/phase08/replay-cw-clean-20260909.json` ve ZIP.


## Replay USB karşılaştırması — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: 8 MS/s, RX 24/24 dB, 825,3 MHz ayarında
verici kapalı beş saniyelik depo kaydı 1 taşma; yerel geçici klasörde
beş saniyelik kapalı kayıt 0 taşma verdi. Aynı yerel yoldaki 30 saniyelik
CW denemesi 3 taşma (en uzun 16876896 bayt) verdi. Üç kayıt tam boyutta
ve kırpılmasızdır; tam boyut süreklilik değildir. Kullanıcı Play basıldığını
bildirdi; 598 tanı penceresinde hedef artışı yok, kesin basış zamanı bilinmiyor.
Bu sonuç verici başarısızlığı veya kalibre RF yokluğu sayılmaz.

OneDrive dışına yazmak tek başına çözüm olmadı; kök neden kanıtlanmadı.
HackRF aracı aynı USB yolunda dört başka cihaz bildiriyor. Sonraki adım
alıcı USB bağlantısını doğrudan farklı bağlantı noktasında sınamak; yeni RF
denemesinden önce kapalı süreklilik kontrolüdür. Ürün/model/RTL/ARM değişmedi.
Kanıt: `results/evidence/phase08/replay-usb-comparison-20260909.json` ve ZIP.
Geçici klasörlerdeki ham kayıtlar da arşive alındı; önceki başarısızlıklar korunur.


## Replay CW gözlendi; USB sürekliliği başarısız — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: hazır bildirimi ardından alınan 24/24 dB kayıtta
824989697 Hz çevresinde 43/598 tanı penceresi eşik üstündedir; ardından
örneklenen seviye eşik altına iner. Ham dosya tam boyutta ve kırpılmasızdır,
ancak araç günlüğünde 3 USB taşması, en uzun 4527552 bayt vardır. Örnek
indislerinden görünen yaklaşık 2,15 saniye kesin RF süresi sayılamaz.
CW bağlantı gözlemi vardır; otomatik durdurma/süreklilik kabulü kapanmadı.
`capture.json complete` yalnız boyut/çıkış kodu kontrolüdür.

Önceki 24/24 penceresinde kullanıcı mesajı geç gördü; o negatif kayıt TX
başarısızlığı değildir. Fotoğrafta CW, 825 MHz, 500 kHz, G:0/A:0 ve Loop
kapalı görüldü. Model/ürün/RTL/ARM değişmedi; dBm ve mutlak frekans açık.
Sonraki koşu süreklilik tanısı çözülerek kısa eşzamanlı kayıttır.
Kanıt: `results/evidence/phase08/replay-cw-detected-20260909.json` ve ZIP.


## Replay CW ilk fiziksel tanı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: 825,3 MHz merkez, 8 MS/s, RX 16/16 dB'de
bir saniyelik kapalı kayıt ve iki 30 saniyelik alıcı penceresi alındı.
Operatör ilk 2 saniyelik CW dosyasının kendiliğinden durduğunu, ikinci
denemede Play'e bastığını bildirdi. İki kayıtta 825 MHz ±50 kHz çevresinde
kapalı q99 +6 dB tanı eşiği üstünde 0/598'er pencere bulundu. Bu, hiç RF
yayınlanmadığının kanıtı değildir; Play anı cihaz zamanıyla bilinmiyor.
Üç ham kayıt tam boyutta, yerleşmiş alımda kırpılma sıfırdır.

Alıcı seri sonu 35138247 ve v2.4.0 cihazdan okundu. Verici sürümü yalnız
“alıcıyla aynı” kullanıcı beyanıdır; seri ve gerçek Replay ekran ayarı
doğrulanmadı. CW/otomatik RF durdurma kabulü kapanmadı; sonraki adım ekran
ayarını doğrulamak, ardından gerekli eşleşmiş alıcı denemesidir. Sayısal
yayınlara geçilmedi; model/ürün/RTL/ARM değişmedi, dBm kalibrasyonu açık.
Kanıt: `results/evidence/phase08/replay-cw-initial-attempts-20260909.json`
ve ZIP; ham I/Q, günlük, komut ve tanı kaynakları korunur.


## PortaPack Replay kaynak hazırlığı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcının SD kartla bağımsız verici kullanma
talebi üzerine 825 MHz nominal merkezli, 500 kS/s C16/TXT paketi hazırlandı.
CW 2 saniye; AM/NFM/BPSK/QPSK/FSK altışar saniyedir. Sayısal aileler ayrı
sabit tohumlu rastgele veri taşır. Üretici sınıflandırıcıyı çağırmaz; model,
ürün F5, RTL ve ARM değişmedi. İlk paket CW referansında DC çıkarımı hatası
nedeniyle teslim edilmedi; v2 sonlu referans kontrolünü ve altı testi geçti.

Dosya bitleri ve süreleri doğrulandı; RF gönderilmedi, SD oynatma henüz
sınanmadı. Kullanıcı iki HackRF ile devamı seçti. Bildirilen yaklaşık
XDG2060/60 MHz üreteç ve osiloskop 825 MHz mutlak kalibrasyon kanıtı değildir;
dBm kapalı kalır. İlk adım verici kapalı alım, ardından tek 2 saniyelik CW
ve durdurma kontrolüdür. Ayarlar/sürüm/kimlik kaydedilmeden RF kabulü yapılmaz.
Talimat: `docs/plans/PARAMETER_REPLAY_LAB_GUIDE.md`.
Kanıt: `results/evidence/phase08/parameter-replay-preparation-20260909.json`
ve ZIP. Açık fiziksel sınıflandırma, kalibrasyon ve ürün kapıları korunur.


## Ayrı üreticiyle sınıflandırma kontrolü — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: sabit v6 model baytları ve v9 aday yöntemi,
eğitim üreticisinden ayrı `validate_candidate_numeric.py` dalga biçimleriyle
sınandı. 26000000 kök tohumda AM/NFM/FSK/BPSK/QPSK ailelerinin her birinde
24/24 doğru kesin karar; CW 24/24 Belirsiz. Toplam 144 SNR varyantı,
48 dalga biçimi tohumu vardır; 144 bağımsız yayın değildir. Protokol ve
model özeti sonuçtan önce kaydedildi; model/eşik değiştirilmedi.

Yeni `scripts/validate_candidate_classification.py` aile ve SNR bazında
doğru/yanlış/Belirsiz, karar kapsamı ve kesin karar doğruluğunu raporlar;
başarısız sayısal kapıda başarısız çıkış kodu verir. İlgili 11 test geçti.
Bu sınırlı sayısal sonuç fiziksel BPSK/QPSK kabulünü kapatmaz; OOK/QAM,
gerçek alıcı bozulmaları ve kapsam dışı aileler bu koşuda sınanmadı.
Ürün F5, RTL ve ARM değişmedi; aday ürün dışındadır. Doğrulanmış sayısal RF
kaynağıyla fiziksel kontrol, kalibrasyon ve ürün kabulü açık kalır.
Kanıt: `results/evidence/phase08/parameter-independent-classification-20260909.json`
ve ZIP; model, protokol, tam sonuçlar ve kaynaklar hash bağlıdır.


## Parametre çalışmasına devam — 9 Eylül 2026

Kullanıcının 5.1.2 kapsamındaki devam talebiyle KTR-4.2 / KTR-4.2-F1
adayının sayısal doğrulaması sürdürüldü. Yöntem değiştirilmeden 25000000
kök tohumlu 168 örnekte 96/144 desteklenen bant sonucu üretildi; 96/96
mevcut toleransı geçti. Desteklenen 48 düşük SNR örneğinde ve aralık dışı
24/24 dikdörtgen BPSK örneğinde OBW verilmedi. SNR varyantları bağımsız
yayın değildir. Sayısal güç mutlak hatası en çok 0,184 dB; bu dBm
kalibrasyonu değildir. İlgili aday/tanı testleri 10/10 geçti.

Ürün F5 ve aday yöntemi değişmedi; aday ürün dışındadır. Dört parametrenin
yarışma koşullarında birlikte doğruluğu henüz kanıtlanmadı. Sonraki açık iş,
ayarları doğrulanmış rastgele verili sayısal RF kaynağıyla sabit modelin
bağımsız kontrolü; frekans ve güç için kalibre referans karşılaştırmasıdır.
Ürün profili/ARM entegrasyonu ve fiziksel ürün kabulü ayrıca açıktır.
Bu devam kaydı sonraki fazı açmaz veya önceki başarısız RF sonuçlarını kapatmaz.
Kanıt: `results/evidence/phase08/parameter-numeric-continuation-20260909.json`
ve ZIP; çalıştırma komutu, kaynak özetleri ve tam sayısal sonuçlar korunur.


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

## 825 MHz BPSK fiziksel değerlendirme — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı BPSK yayınının açık olduğunu ve Shape
alanının ayarlanamadığını bildirdi. Pseudo Noise seçilmiş sayılmaz;
sembol hızı ve bit dizisi bilinmiyor. Önceki talimattaki 825 MHz/TX Gain 0/
Amp 0 cihazdan geri okunmuş ayar değildir. İki alıcı merkezinde 16/16,
24/24 ve 32/32 dB kazançlarla altı adet 0,5 saniyelik ham RX kaydı alındı.
16/16 ve 24/24 toplam 40 pencere düşük SNR kapısında kaldı; 32/32 dB'de
20 pencere kalite kapısını geçti fakat 20/20 sınıf Belirsiz kaldı.
Analiz edilen yerleşmiş bölümlerde kırpılma yok. Sayısal sınıflandırma
fiziksel kabulü başarısız; model/eşik değiştirilmedi. Farklı aralıklarla
sonradan yapılan tanılar bağımsız kabul koşusu sayılmaz. FPGA kullanılmadı.
Kanıt: `results/evidence/phase08/parameter-bpsk825-evaluation-20260909.json`
ve ZIP. Bu kullanıcı etiketli fiziksel kaynak kontrolüdür; üretici
uygulaması ve bağımsız modülasyon referansı ayrıca doğrulanmalıdır.


## Yeni 825 MHz AM değerlendirmesi — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: model/eşik değiştirilmeden 825 MHz, AM %100,
2 kHz sinüs kaynak ayarında iki merkez ve iki kazançta dört RF kaydı
alındı. 16/16 dB'de 20/20 düşük SNR reddi, 24/24 dB'de 10/20 Analog
ve 10/20 Belirsiz; yanlış Sayısal sıfır. Yeni koşul %80 karar kapsamını
geçmedi. İki yüksek kazanç kaydında zarf tonu 2000,14 Hz gözlendi.
Pencereler bağımsız RF koşuları sayılmaz; FPGA ve ürün yolu kullanılmadı.
Sınıflandırma genel kabulü açık; başarısız koşul model eğitimine eklenmedi.
Kanıt: `results/evidence/phase08/parameter-am825-evaluation-20260909.json`
ve ZIP. Sayısal aileler yalnız sentetik testlerde; fiziksel OOK/FSK/PSK/QAM,
farklı hızlar ve kapsam dışı yayın kabulü açık kalır.


## Bant kapsamı adayı v9 — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: aralık dışı enerji her uçta %0,5, Hann varyansı
ve ayrı gürültü bölgeleriyle denetlenir. Ayrı 168 sayısal örnekte 96
geçerli OBW toleransı geçti; 48 desteklenen düşük SNR örneğinde ret,
24/24 aralık dışı emisyon örneğinde ret vardır. Genel kabul değildir.
800 örneğin sınıf kararları değişmedi; eski RF AM 16/20, FM 20/20 Analog.
28 test geçti. Aday ürün dışındadır; ARM ve fiziksel ürün kabulü açık.
Kanıt: `results/evidence/phase08/parameter-band-containment-v9-20260909.json`
ve ZIP. Ayrıntı: `docs/plans/PARAMETER_REFINEMENT_PROTOCOL.md`.
Önceki v7/v8 hataları tarihsel sonuçlarıyla korunur.


## Parametre iyileştirme adayı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1 kapsamında ayrı bir sayısal aday geliştirildi:
uzun spektrum, gerçek çizgi araması, DC ayrıştırma, bant ölçekli özellikler
ve 8 bit alıcı bozulmalarıyla eğitilmiş sınıf modeli. Ürün F5 değişmedi.
Son ayrı tohum testinde 700 modülasyonlu örneğin 613'ü doğru kesin karar,
87'si Belirsiz, yanlış kesin karar sıfır; CW 100/100 Belirsiz. Aile
karar kapsamı %82–93. Önceden incelenmiş fiziksel regresyonda AM 16/20,
FM 20/20 Analog; bunlar kör fiziksel kabul değildir. Yeni aday bant
kontrolü geniş kuyruklu BPSK'de 1/6 hatalı kapsam sonucunu hâlâ kaçırır;
OBW kabulü başarısız, ürün entegrasyonu ve ARM taşıması yapılmadı.
27 ilgili test geçti. Parametre çıkarımı tamamlanmadı; aday ürün dışındadır.
Plan: `docs/plans/PARAMETER_REFINEMENT_PROTOCOL.md`. Kanıt:
`results/evidence/phase08/parameter-refinement-candidates-20260909.json`
ve ZIP; eski kaynak/kanıtlar korunur. Sıradaki iş bant kapsam belirsizliğini
ve bağımsız OBW doğrulamasını çözmek, ardından yeni ürün profilidir.


## 735 MHz AM fiziksel karşılaştırması — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: onaylı Faraday kabininde bildirilen AM %100,
1 kHz sinüs kaynağından altı ham RX kaydı alındı. İki alıcı merkezinde
999 Hz zarf tonu ve yaklaşık 1 kHz aralıklı taşıyıcı/yan çizgi deseni görüldü.
Çevrimdışı F5 tanısında 40/40 yeniden hesaplama eşleşti; sınıf 40/40
Belirsiz kaldı. 24/24 dB'de 20/20 model uzaklığı reddi, taşıyıcı 2/20
geçerli, OBW 18/20 geçerli sonucu vardı. Bunlar dört kaydın pencereleridir;
40 bağımsız RF koşusu veya doğruluk kabulü değildir. FPGA kullanılmadı.
Üretim yöntemi değişmedi; sınıflandırma, taşıyıcı ve OBW doğruluğu açık.
Kanıt: `results/evidence/phase08/parameter-rf-am735-20260909.json` ve ZIP.
Ayrıntı: `docs/plans/PARAMETER_VALIDATION_BENCH.md`.


## 735 MHz FM fiziksel parametre tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1 için kullanıcı onaylı Faraday kabininde sekiz ham
HackRF RX kaydı alındı. 16/16 ve 24/24 dB kazançta iki farklı alıcı
merkezinde yaklaşık 999 Hz FM tonu gözlendi. Gerçek I/Q üzerinde çevrimdışı
F5 tanısında 40/40 yeniden hesaplama eşleşti; sınıf 40/40 Belirsiz,
taşıyıcı 40/40 Gözlenmedi kaldı. Model uzaklığı retleri korundu.
Bu pencereler dört fiziksel kayıttandır; 40 bağımsız RF koşusu değildir.
OBW bağımsız hesap farkı, dBm kalibrasyonu ve kart/ürün kabulü açık kaldı.
FPGA kullanılmadı; üretim yöntemi ve eşikleri değiştirilmedi.
Kanıt: `results/evidence/phase08/parameter-rf-fm735-20260909.json` ve ZIP.
Ayrıntı: `docs/plans/PARAMETER_VALIDATION_BENCH.md`. Önceki ET önceliği
kaydı korunur; bu oturum kullanıcının parametre testlerine devam talebidir.


## PHASE-10 Tekli Görev — 8 Eylül 2026

Kullanıcının ET'ye geçiş onayıyla PÇ-02 ve PHASE-09 beklemeye alındı. Ürün ET
alanı yalnız seçilen tek frekans bandında süreli gürültü görevi sunar. İletimsiz
CI8/spektrum doğrulaması ve fiziksel profil kilitli HackRF süreç yolu uygulanmıştır.
Depodaki profil kapalı ve cihaz bağlı olmadığı için RF gönderimi yapılmamıştır;
PHASE-10 fiziksel kabulü açıktır ve PHASE-11 başlatılmamıştır. Ayrıntı:
`docs/interfaces/ET_SINGLE_TASK_CONTRACT.md`.

## Parametre kabul durumu ve PÇ-02 devamı — 8 Eylül 2026

KTR-4.2 / KTR-4.2-F1 tamamlanmadı. Güncel kaynakla aynı 30 sentetik
örnek tekrarlandı ve 30/30 kayıt yeniden hesaplandı; bu doğruluk kabulü
değildir. CW taşıyıcısı 1/6, AM taşıyıcısı 2/6 geçerli; 24 modülasyonlu
örneğin tamamı model uzaklığı kapısında Belirsiz kaldı. Sayısal dBFS
hatası bu kümede en çok 0,189 dB; mutlak dBm kalibrasyonu açık.
Yeni karar kapısı tanısı ve ölçüm/profil kontrolleri 22/22 geçti.
Kanıt: `results/evidence/phase08/parameter-diagnostic-20260908-v1.json`
ve ZIP. Ayrıntı: `docs/plans/PARAMETER_VALIDATION_BENCH.md`.
Kullanıcı cihazların bağlı olmadığını bildirdi; fiziksel kabul yapılmadı.
PÇ-02 sürüyor; PÇ-03–05 ve ST-06 kapanmadı. Ürün yöntemi, eşikleri,
PC/PL/PS görev paylaşımı ve önceki kanıtlar korundu. Aşağıdaki tarihli
kayıtlar kendi sürümlerinin durumunu belirtir.


## ET ürününden hazır senaryoların çıkarılması — 8 Eylül 2026

Kullanıcının hazır/sentetik ET gösterimlerini kaldırma talimatıyla KTR-5.1–5.4
ürün kapsamı güncellendi. QML ET alanından hazır dalga biçimi çalıştırma,
önceden tanımlı hedef sahneleri, otomatik test sesi ve örnek GNSS konum/UTC/PRN
formu kaldırıldı. Görev seçimi yalnız uygulanmamış gönderim durumunu gösterir;
ölçüm, grafik, zaman çizelgesi veya tamamlanmış görev sonucu üretmez.
`quick_et_actions.py` artık model çalıştırma ya da GNSS doğrulama API'si sunmaz.
`algorithms/et` ürün import ve paket sınırının dışındadır; eski konsolun ET
mixin'i de paket dışında tutulur. HackRF gönderim yolu uygulanmamıştır.

Sayısal referans modelleri, doğrulama testleri ve özgün ET-A/B/C kanıtları
geçmiş çalışmanın yeniden üretimi için depoda korunur; güncel ürün yeteneği
sayılmaz. Aşağıdaki eski ET-C arayüz kabulü kayıtları tarihsel kapsamındadır.
ED kaynakları ve açık ST-06/parametre kabul kapıları bu ET düzenlemesiyle kapanmaz.
PHASE-10–12 donanım veya RF kabulü yapılmadı. Güncel ürün sınırı
`tests/test_operator_product_boundary.py` ve
`tests/test_app_f_quick_product.py` içindeki ET yokluk denetimiyle sınanır.


## PÇ-01 ölçüm arayüzü ve güncel gözlem bağı — 7 Eylül 2026

Kullanıcının devam talimatıyla dört zorunlu sonuç ana görünümde ayrıldı:
taşıyıcı frekansı, OBW %99, kalibrasyonsuz kanal gücü (dBFS) ve Analog/Sayısal.
Emisyon merkezi, bant kenarları, SNR, gözlem süresi, hesaplama bitiş UTC zamanı
ve kayıt yolu açılır ayrıntıdadır. Sonuç, alımın durduğu kayıtlı ölçüm olarak
etiketlenir. Taşıyıcı bulunmadığında merkez onun yerine gösterilmez.

Yeni canlı ölçüm, son işlenen kart yanıtına kadar süren dört ardışık gözlemi
ister; geçmiş/seçim önbelleği yeni ölçüm girdisi olamaz. Yeniden alım eski
sonucu ve aralık onayını temizler; operatör güncel tespiti yeniden seçer.
İptal, gecikmiş çalışan sonucu yayımlamaz. Geçersiz aralık girişi önceki
onayı kaldırır. Algoritma, eşik, RTL ve kart hizmeti değişmedi; F5 bilgisayarda.

Son doğrulama: 137/137 test geçti. Main.qml 2.137, görünüm modeli 1.996
satırla mevcut mimari sınırlar içindedir.

KTR-4.2 / KTR-4.2-F1 yazılım kabul kanıtı:
`results/evidence/phase08/parameter-workflow-v1.json` ve ZIP.
1280×720 ve 1920×1080 görünüm kontrolleri kayıtlı I/Q ile yapılır.
Önceki PÇ-00 kanıtı tarihsel baytlarıyla korunur; aşağıdaki 134/135 sonucu
önceki kaynak içindir. Yeni panel ayrımı Main.qml satır sınırı bulgusunu giderir.
ST-06, fiziksel RF doğruluğu, dBm kalibrasyonu ve ARM taşıması açıktır.
PÇ-02 sıradaki planlı çalışma adımıdır; bu değişiklikle uygulanmadı.

## PÇ-00 ölçüm kaydı uygulaması — 7 Eylül 2026

Kullanıcının uygulamaya devam talimatıyla KTR-4.2 / KTR-4.2-F1 için mevcut
F5 ölçümüne kaynak ve I/Q bağlı kayıt eklendi. Canlı ve SigMF ürün ölçümü,
dört normalize I/Q karesini ve alanların birim/yöntem/durum/neden bilgilerini
ayrı ZIP'e kaydeder; kayıt başarısızsa yeni sonuç yayımlamaz. Canlı karelerde
merkez, örnekleme, sıra ve kart yanıtı bağı ayrıca denetlenir. Profil/model
özetleri, oturum ayarları, kanal seçici ölçeği ve bilinen kaynak özetleri
saklanır. Donanım UTC zamanı, çalışan kart imajı ve kalibrasyon gözlenmemişse
bilinmiyor kalır; dBm veya RF doğruluk sonucu üretilmez.
[Kayıt ve yeniden üretim sözleşmesi](docs/interfaces/OPERATOR_ASSISTED_PARAMETER_CONTRACT.md) sınırları tanımlar.

F5E paket denetimi mevcut iki ek logoyu açık listesine aldı; eksik model ve
izinsiz ek dosya retleri korunur. Eski F5E/PHASE-08 kanıtları değiştirilmedi.
Parametre satırlarını oluşturma işlevi mevcut ölçüm modülüne taşındı; görünen
alanlar ve algoritma eşikleri değişmedi. Yeni kanıt
`results/evidence/phase08/parameter-record-v1.json` ve ZIP içindedir.
Bu yazılım kayıt/entegrasyon kabulüdür; yeni fiziksel kart veya RF deneyi
değildir. ST-06 ve dört parametrenin saha doğruluğu açıktır. PÇ-01 arayüz
sadeleştirmesi sonraki iştir; tercihli özellikler ve PHASE-09 açılmadı.

## Zorunlu parametreler için devam planı — 7 Eylül 2026

Kullanıcı yönlendirmesiyle taşıyıcı frekansı, bant genişliği, güç seviyesi ve
Analog/Sayısal ayrımı için [kontrollü devam planı](docs/plans/IMPLEMENTATION_ROADMAP.md)
hazırlandı. Mevcut canlı arayüz ölçümü bilgisayarda F5 yöntemini kullanır;
ARM'da merkez/OBW99/dBFS sayısal çekirdeği vardır. Taşıyıcı ve sınıflandırmanın
ARM'a taşınması, güncel RF doğruluğu ve dBm kalibrasyonu açıktır.
ST-06 tamamlanmadı; bu sınırlı kapsamda planlama başladı. Tercihli alanlar
ve sonraki yarışma görevleri açılmadı. Bu oturum üretim kodunu değiştirmedi.
Başlangıç doğrulamasındaki eski paket-listesi uyuşmazlığı ve ölçüm sınırları
planda kayıtlıdır; tarihsel başarılar yeni kaynağa aktarılmaz.

## Son arayüz düzenlemesi — 7 Eylül 2026

Sabit frekans ve bant taraması alanlarında sayılar ortalandı; etiketler, alan
yükseklikleri ve yazı boyutları eşitlendi. Bağlantı hazırken gereksiz bağlı
düğmesi ile yinelenen tespit metinleri kaldırıldı. Başlat/durdur eylemlerinden
yalnız geçerli olanı görünür. Sonuç listesi frekansı ve gerekli olduğunda kaba
aralığı gösterir; teknik ayrıntılar ipucundadır. Algoritma ve RTL değişmedi.
Yedi arayüz durumu ile kaynak hash'leri
`results/evidence/phase08/st06-ui-final-20260907.json` ve ZIP içinde saklandı.
İlgili sinyal tespiti, QML ve depo sözleşmesi paketi 130/130 geçti.

## İkinci kör turun hedef bildirimi — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: operatör ikinci tamamlanan turun hedefini
sonradan 873,4900 MHz olarak açıkladı. Sabitlenmiş normal tarama kaydı
873,490442 MHz (tepe 873,490039 MHz), 120 gözlem; bağımsız alıcı ayarı
873,490094 MHz, 40 gözlem ve otomatik ikinci kontrol 873,490192 MHz,
40 gözlem ile hedefi içerir. İki doğrulama FPGA yöntemindedir; durum
Tekrar görüldü. Kapalı referans veya önceden verilen hedef kullanılmadı.
Bildirim kanıtı `results/evidence/phase08/blind-second-target-873490-20260907.json`;
ham kaynak `blind-second-survey-20260907.json` ve ZIP. Frekans farkları
kalibre mutlak doğruluk iddiası değildir. Bu tek koşul tüm ortamlarda
Pd/Pfa veya otomatik yayıncı kimliği kabulü sayılmaz; ST-06 açık kalır.


## Tam bant ve otomatik ikinci kontrol — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: 700–1000 MHz normal tarama 500/500 pencereyi
239,06 s içinde tamamladı. İlk turda USB taşması, CRC, sıra ve kuyruk kaybı
sıfır. Otomatik ikinci kontrol 124 kayıt için 27,38 s sürdü: 113 tekrar
görüldü, 11 son kontrolde görülmedi, kontrol hatası bildirilmedi.
953 MHz hedefi 952,999935 MHz olarak bulundu; ikinci kontrolde
952,999914 MHz olarak tekrar görüldü. Toplam iki aşama yaklaşık 266,44 s.
11 görülmedi sonucu yanlış alarm veya yayın kapanışı olarak etiketlenmez.
Tekrarlı Pd/Pfa, kesintisiz takip veya ST-06 kabulü değildir.
Kanıt `results/evidence/phase08/full-survey-recheck-20260907.json` ve ZIP;
fiziksel kaynaklar arşivde korunur. Ölçüm sonrasında yalnız ikinci kontrol
sırasında ilk taramanın kalan süre tahminini gizleyen sunum düzeltmesi yapıldı;
4 kontrol testi geçti. Bu son metin düzeltmesinin RF tekrarı yapılmadı.
Tam bant ikinci kontrol çalışma/süre kapısı bu koşulda gözlendi; genel
ortam kabulü ve parametre fazına geçiş açık kalır.


## Otomatik ikinci kontrolün fiziksel doğrulaması — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: operatör önceki boş kısa turda vericinin kapalı
olduğunu düzeltti. 953 MHz açık bildirimi sonrası güncel kaynakla
952,6–953,8 MHz normal tarama iki pencereyi 1,1637 s içinde tamamladı.
952,999962 MHz bulundu; otomatik ikinci kontrol 0,2526 s içinde aynı
sinyali yeniden gördü ve arayüz satırı Tekrar görüldü oldu. Ek kontrolde
48/48 kart yanıtı, USB/CRC/sıra/kuyruk hatası ve kırpılma sıfırdır.
Kaynak hash'leri, ilk tur ve yan kontrol kaydının SHA-256 bağı doğrulandı.
Kanıt `results/evidence/phase08/survey-recheck-live-on-20260907.json` ve ZIP.

Bu hedefi bilinen iki pencerelik testtir; tam bantta yeniden kontrol süresi,
kesintisiz takip, yokluk kararının fiziksel açık/kapalı tekrarı ve genel
Pd/Pfa kabulü değildir. Önceki fiziksel yeniden kontrol bekliyor notu yalnız
bu dar kapsam için kapanır. ST-06 açık; parametre fazına geçilmedi.


## Otomatik ikinci kontrol ve frekans sıralaması — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, ST-06: normal tek tur sonuçları frekans sırasıyla
sunulur. Kontrol edilmemiş enerji bölgeleri listenin sonunda kalır. Normal
tur başarıyla tamamlanınca doğrulanmış ve birleştirilmiş sinyaller bir kez
otomatik yeniden kontrol edilir. Laboratuvar kapalı/açık turları bu ek kontrolü
başlatmaz. İkinci kontrol bitmeden görev tamamlandı bildirimi verilmez.
Tekrar görüldü / son kontrolde görülmedi / kontrol edilemedi ayrı durumlardır;
alım hatası veya iptal sinyal yokluğuna çevrilmez. Kontrol zamanı ipucundadır.
`.recheck.jsonl` yan kaydı özgün taramanın SHA-256 özetini ve her sonucu
saklar; ham tarama kanıtı değiştirilmez. Bu sınırlı bir ikinci turdur,
kesintisiz izleme veya yeni yayınların sürekli keşfi değildir.

102 hedefli test ve 25 arayüz testi geçti. İptal, hatanın yokluktan ayrılması,
kayıt korunması ve görev tamamlanma sırası sınandı. 952,6–953,8 MHz fiziksel
denemede 2/2 pencere tamamlandı fakat sinyal bulunmadı; otomatik ikinci kontrol
çalışmadı. Vericinin güncel durumu soruldu; fiziksel yeniden kontrol kabulü
bekliyor. Kanıt `results/evidence/phase08/survey-recheck-20260907.json` ve ZIP.
Ek kontrol süresi genel tur süresine eklenir; tarama ve kontrol ayrı kaydedilir.
ST-06 açık; parametre fazı başlamadı.


## 953 MHz hedef eşleştirmesi ve kısa tekrar — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: operatör tamamlanan 700–1000 MHz turunun
hedefini sonradan 953 MHz olarak açıkladı. Değiştirilmemiş kayıtta
952,999989 MHz, ilk ölçümde 63 ve ikinci ayarda 23 gözlemle FPGA doğrulaması
vardır; arayüzün saklanan sıralamasında 76. satırdadır. Kapalı referans
kullanılmadan hedef listelenmiştir; otomatik hedef seçimi kanıtlanmamıştır.
Yeni dar-sinyal eşleştirmesiyle 952,6–953,8 MHz kısa fiziksel tarama
2/2 pencereyi 1,0834 s içinde tamamladı: 952,999964 MHz, ikinci ayarda
952,999955 MHz, 91/26 gözlem. Tamamlanan pencerelerde USB taşması,
CRC, sıra ve kuyruk kaybı sıfır. Bu hedefi bilinen dar aralık tekrarıdır;
300 MHz kör tarama süresi veya genel Pd/Pfa kabulü değildir.
Kanıt: `results/evidence/phase08/target953-confirmation-20260907.json`
ve ZIP; iki fiziksel kaynağın hash'leri ayrı korunur. Önceki hedef frekansı
bekleniyor notu bu bildirimle çözülmüştür. ST-06 açık kalır.


## Dar sinyal doğrulama eşleştirmesi — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, ST-06: dar ilk gözlem geniş ikinci-ayarlama
olayının içine düştüğünde yalnız aralık örtüşmesiyle kabul edilebiliyordu.
Dar ilk gözlem için ikinci olayın genişliğinden bağımsız olarak tepe
frekansı mevcut 50 kHz toleransında eşleşmelidir. Geniş ilk gözlemin
aralık tabanlı doğrulaması korunur. Yeni dar/geniş yanlış eşleşme testi ve
mevcut geniş bant tepe değişimi testi dahil 60 hedefli test geçti.
Bu değişiklik hedef frekansı öğrenilmeden yapıldı; frekansa özel kural yoktur.
Kanıt `results/evidence/phase08/survey-narrow-verification-20260907.json`
ve ZIP. Eski kayıttaki özetlerin incelemesi yeni RF sonucu değildir;
tek tek doğrulama kareleri bu kayıtta bulunmadığından başarı sayısı
sonradan değiştirilmedi. Güncel kaynak fiziksel doğrulaması bekleniyor.
ST-06 ve parametre fazına geçiş kapısı açık kalır.


## Güncel kaynakla tek tur fiziksel ölçüm — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: 700–1000 MHz, azami 24/24 dB, harici
verici açık operatör beyanıyla normal tarama 249,10 s sürdü. Kapalı referans
yüklenmedi. 500/500 pencere tamamlandı; tamamlanan pencerelerde USB taşması,
CRC, sıra ve kuyruk kaybı sıfır. 10 kazanç tekrarı, 126 ham gözlem kaydedildi.
Önceki açık turun 257,16 s süresinden yaklaşık %3,13 kısa; değişen RF yükü
ve tekrar sayıları nedeniyle nedensel hız kazancı kanıtlanmadı.
Önceki 826 MHz çevresinde ±50 kHz doğrulanmış gözlem yok; bu turun hedef
frekansı henüz açıklanmadı. Hedef başarısı veya ST-06 kabulü çıkarılmaz.
Arayüz sonuç satırları kaydedildi; pencere görüntüsü kaydedilemedi.
Kaynak hash eşleşmeleri ve ham kayıtlar:
`results/evidence/phase08/survey-optimized-live-20260907.json` ve ZIP.
Önceki mikro ölçümün fiziksel toplam süre kapısı bu gözlemle güncellendi;
tekrarlı hız kabulü ve RF hedef doğruluğu açık kalır.


## Tarama hesaplama maliyeti ve sade görünüm — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: tarama ve ikinci ayar doğrulamasında ilk kareden
sonra yalnız doğrusal FFT gücü hesaplanır; kullanılmayan genlik, logaritmik
PSD ve frekans ekseni dizileri tekrar üretilmez. Referans işlem sırası,
Hann penceresi, kare sayısı, gözlem süresi ve eşikler korunur. Ayrı hız modu yoktur.
`tests/test_detection_power.py` sıfır, DC, ton ve rastgele CI8 girdilerinde
4096/16384 boyutları ve DC çıkarımı seçeneklerinde birebir güç eşitliğini sınar.
Yerel mikro ölçüm medyanı tam yol 1,3607 ms, güç yolu 0,6442 ms;
bu toplam tarama süresi veya fiziksel RF doğruluğu kabulü değildir.

Görünümde tekrarlanan tespit yazıları, yeni etiketi, teknik pencere sayacı
ve renk açıklamaları kaldırıldı. Frekans, varsa kaba aralık ve yalnız
belirsiz bulguda doğrulama durumu gösterilir. Ayrıntılar ipucunda korunur.
Tamamlanan turda son pencere aralığı ana başlık gibi gösterilmez.
Yeni kaynakla fiziksel süre karşılaştırması açık; ST-06 tamamlanmadı.
Kanıt: `results/evidence/phase08/survey-power-20260907.json` ve ZIP.


## Tek tur tarama sunumu — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, PHASE-08 / ST-06 kapsamında bant taraması
kartlarında frekans, tespit durumu ve mevcutsa kaba frekans aralığı gösterilir.
Teknik kanıtlar ipucunda korunur. Yalnız enerji bölgeleri doğrulama bekliyor
olarak ayrılır; geçmiş tarama sonucu kesintisiz canlı yayın sayılmaz.
Dar çizgiler yalnız komşu pencerelerde, aynı kanıt sınıfında ve iki ayardaki
tepe frekansları ayrı ayrı iki FFT hücresi içinde uyuşursa birleştirilir.
Sabit eşleştirme merkezi zincirleme frekans kaymasını önler; geniş emisyonlar
ve aynı penceredeki ayrı çizgiler birleştirilmez. Ham kayıtlar değişmez.

Kanıt: `results/evidence/phase08/survey-single-presentation-20260907.json`
ve ZIP. Önceki 6679a49 kaynağıyla 700–1000 MHz kapalı/açık turları
500/500 pencere tamamladı (282,56 / 257,16 s). Açık tur sonrasında operatör
826 MHz bildirdi. Yeni sunumun yalnız açık kayıt tekrarı kapalı referans
kullanmadan 130 gözlemi 122 satıra birleştirdi; 826 MHz tekrarı da birleşti.
Bu RF algoritmasının yeni fiziksel tekrarı, yayıncı sayısı, otomatik hedef
seçimi veya Pd/Pfa kabulü değildir. Kaynaklar kanıtta ayrı tutulur.

Hedefli 99 yazılım ve 25 arayüz testi geçti. İlk alım oturumları 193,05 s, kabul edilen
130 ek doğrulama 25,92 s tuttu; süreler toplam turun bütün aşamalarını
ayrı ayrı açıklamaz. Alım hızlandırması, sürekli yeniden ziyaret ve ortamdan
bağımsız hedef seçimi henüz uygulanmadı. Eşikler, RTL ve alım süreleri
korundu. ST-06 açık; parametre fazına geçilmedi.


## Gün sonu aktarımı — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: bilinen 853 MHz CW ve 24/24 dB ile önceki fiziksel
sürümün kısa açık/kapalı ayrımı olumludur. Son otomatik kazanç ve arayüz sürümü
henüz fiziksel olarak denenmedi. Sinyal tespitinin temel yolu çalışıyor;
ST-06 tamamlandı veya her ortamda kararlı denemez. Parametre fazı başlamadı.
RF tanı kayıtları, başarısız girişimler ve yeniden üretim araçları artık
`results/evidence/phase08/rf-diagnostics-20260906.zip` içinde korunur; yanındaki
JSON her dosyanın SHA-256 özetini içerir. Arşiv köke açıldığında belgelerdeki
özgün build yolları geri gelir. Var olan dosyalar hash karşılaştırılmadan
üzerine yazılmaz. Eski ölçümler kendi kaynak özetleriyle korunur.
Sonraki oturum: önce kart/servis/çalışan imaj kimliği yeniden kontrol edilir;
yeni sürümle kısa kapalı → açık → kapalı ölçüm, otomatik kazanç yönü/döngü/iptal
ve frekans durumlarının doğruluğu sınanır. Anten konumu ve TX kazancı sabitlenir;
koşullar sonra tek tek değiştirilir. Sonuçlar uygun olursa kalan kör RF,
soğuk açılış ve güncel kaynak kabul kapıları değerlendirilerek faz kararı verilir.
Sırf önceki masaüstü geçişleri nedeniyle uzun GUI koşuları baştan tekrarlanmaz.
Sayısal ölçekleme deneyinin kazancı umut vericidir; canlı güç telafisi ve
fiziksel doğrulaması yapılmadan üretim ölçeği 1'den değiştirilmez. Otomatik
kazanç ilk seviye ayarı ve kırpılma sonrası sınırlı yeniden denemedir; kesintisiz
AGC veya kalibre güç ölçümü değildir. Optimizasyon için ölçülebilir yol vardır;
tamamlanma kararı yeni kanıta dayanacaktır.

## Sinyal tespiti kullanım ve seviye düzenlemesi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, PHASE-08 / ST-06: sabit izleme arayüzünde
isteğe bağlı otomatik kazanç (başlangıçta seçili), MHz girişi ve sade sinyal
durumları uygulandı. Başlangıç görünümü değerlendirilen ±700 kHz'e odaklanır;
kullanıcı genişletirse kapsam işareti korunur. Frekans ve alınıyor/artık alınmıyor
ana bilgidir; teknik sayılar ipucunda kalır. RF kimliği veya çift ayar doğrulaması
bu sade sunumdan çıkarılmaz.
Otomatik mod ilk 16 kareyi seviye hesabından dışlar, sonraki 32 karenin CI8
çıkışında %95'ten fazla sıfır bileşeni varsa kazançları 8 dB artırarak yeni oturum
açar. Kırpılmada 8 dB azaltır. En çok 8 girişim, tekrar ziyaret yasağı ve operatör
iptali vardır. Kırpılmış kare karta gönderilmez; denemeler ayrı oturumlardır ve
kayıpsız kesintisiz alım diye sayılmaz. %95 ölçütü mühendislik sezgisidir; genel
hassasiyet, Pfa/Pd hedefi veya RF yokluk kararı değildir. Başlangıç kırpılması
henüz sürekli kırpılmadan ayrılmıyor. Sürekli düşük-seviye takibi yapılmıyor.
Kanal seçiciye yalnız açıkça seçilen deneyler için 1–16 genlik ölçeği ve çıktı
ölçeği bilgisi eklendi; üretim varsayılanı 1. Kaydedilmiş aynı 16/16 dB açık ham
veride kayan noktalı merkez eşik aşımı ölçek 1'de 14/496, ölçek 8'de 474/496;
kapalıda ikisinde de 0/496. Beş ölçek ve açık/kapalı çiftin tümünde 512/512
Python/yerel çıktı eşleşti; kırpılma sıfır. Bu donanım FFT tekrarı değildir.
Yerel yeniden üretim: `build/acceptance/st06-gui-20260906/analyze_channelizer_scaling.py`;
özet ve SHA-256: `build/acceptance/st06-gui-20260906/channelizer-scaling-diagnosis-01.json`.
Canlı ölçekleme entegrasyonu güç/ölçek izlenebilirliği ve fiziksel doğrulama
bekler; henüz etkin değildir. RTL/CFAR katsayısı değişmedi. Yazılım testleri
kazanç yönü, döngü sınırı, iptal, MHz dönüşümü, kapsam odağı ve referans eşleşmesini
denetler. Yeni sürüm FPGA/HackRF üzerinde bu değişikliklerden sonra denenmedi;
eski fiziksel kanıt bu kaynağa taşınmaz. ST-06 ve sonraki faz kabulü açık kalır.

## Ekran incelemesi ve MHz girişi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında sabit izleme merkez girişi MHz oldu;
ondalık nokta/virgül kabul edilir, iç arayüze tam Hz aktarılır. QML testi birim
dönüşümünü, hatalı değerleri ve gerçek ayarların forma geri yansımasını denetler.
Kullanıcının 933 MHz görsellerinde yaklaşık 929,8 MHz geniş tepe, görünür
932,3–933,7 MHz tespit alanının dışındadır; bu tepenin kaynağı kanıtlanmadı.
Ham 8 MHz görüntünün tamamı aynı anda tespit kapsamı sayılmaz. 931,5 MHz ve
1198,5 MHz merkez çizgileri DC iziyle uyumludur; görüntü tek başına kimlik kanıtı
veya Pd/Pfa hesabı değildir. Tek uç-değer I/Q bileşeni oturumu durdurur; yerel
kanal seçici böyle giriş karesini sıfırladığından yalnız durdurma koşulunu kaldırmak
geçerli çözüm değildir. Kırpılma oranı/başlangıç ayrımı ve kullanıcıya daha açık
kazanç tanısı halen açıktır. MHz değişikliği DSP veya RF kabulünü değiştirmez;
önceki fiziksel sonuçlar yeni arayüz kaynağının fiziksel testi sayılmaz.

## 853 MHz eşleştirilmiş kart sonucu — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında RX LNA/VGA 24/24 dB ile aynı anten
konumunda kısa, kullanıcı beyanlı açık/kapalı kart koşuları tamamlandı. Açıkta
853 MHz olayı ilk kareden son kareye 4.883/4.883 kez gözlendi; örneklenmiş 327
yanıtın ilk tentative yanıtından sonraki 326'sı aynı hedefi confirmed ve observed
olarak taşıdı. Kapalı koşunun 327 örnek yanıtında hedef çevresinde confirmed olay
yoktu. Her iki koşuda USB/CRC/sıra/kuyruk hatası ve kırpılma sıfırdı. Bu bilinen
CW için kısa olumlu ayrım kanıtıdır; kör/tekrarlı RF doğruluğu veya ST-06 kapanışı
değildir. Yerel özet `build/acceptance/st06-gui-20260906/rf853-24db-board-comparison-01.json`.

## 853 MHz 24/24 dB gerçek kart gözlemi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: kullanıcı beyanlı açık vericiyle üç kazanç kaydı alındı.
Her ayarda 512 ardışık ham kare, sıfır USB taşması/kırpılma ve 512/512 yerel /
Python kanal seçici eşleşmesi var. İlk 16 kare dışlanınca 16/16 dB açık kaydında
ham USB merkez hücresi kayan noktalı eşik hesabını 474/496, kanal seçici çıkışı
14/496 kez aştı. 24/24 dB çıkışında 496/496, kapalıda 1/496; medyan açık eşik
marjı +11,06 dB. 32/32 dB kapalı merkezde de 76/496 aşım görüldüğünden daha yüksek
kazanç otomatik olarak tercih edilmedi. Bu hesaplar FPGA bit-tam tekrarı değildir.
Ardından 24/24 dB ile gerçek RX → kart → GUI koşusu 4.883 kareyi sıfır USB/CRC/
sıra/kuyruk hatası ve kırpılmayla bitirdi. İlk örnek tentative; kalan 326 örnek
yanıtta aynı 853 MHz olay kimliği confirmed ve observed idi. Son kart yanıtında
first_frame_id=0, last_seen_frame_id=4882, seen_count=4883: kart sayacı bu kısa
koşunun tüm karelerinde hedef gözlemi bildiriyor. GUI kısa koşu kontrolleri geçti.
Bu sonuç bilinen CW için kısa olumlu gözlemdir; genel Pd/Pfa, uzun süreli hız payı
ve ST-06 kabulü değildir. 24/24 dB eşleştirilmiş kapalı kart koşusu bekleniyor.
Üretim eşikleri değiştirilmedi; kazanç yalnız tanı koşusuna uygulandı.
Yerel raporlar: `build/acceptance/st06-gui-20260906/rf853-gain-comparison-01.json`
ve `build/acceptance/st06-gui-20260906/rf853-on-24db-target-01.json`.

## 853 MHz kapalı kazanç karşılaştırması — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında kullanıcı vericinin kapalı olduğunu bildirdi.
RX LNA/VGA 16/16, 24/24 ve 32/32 dB ayarlarının her birinde 512 ardışık ham
kare (yaklaşık 1,05 saniye) kaydedildi. Üç koşuda USB taşması ve giriş/çıkış
kırpılması sıfır; aynı ham verinin yerel ve Python kanal seçici çıktıları her
koşuda 512/512 bayt-tam eşleşti. Kanal seçici çıkışında sıfır olmayan bileşen
oranı sırasıyla %1,726 / %4,390 / %52,880 oldu. Bu artış kapalı ortamın sayısal
seviyesidir; hedef sinyal iyileşmesi, Pd/Pfa veya FPGA kabulü değildir.
Ham ve türetilmiş I/Q birlikte `build/acceptance/st06-gui-20260906/rf853-gain-off-01/`
içinde; kaynak/girdi özetleri `summary.json` içindedir. Yeniden üretim aracı
`build/acceptance/st06-gui-20260906/rf853_gain_capture.py` (yeni çıktı dizini gerektirir).
Bu tanıda kart gönderimi yapılmadı; üretim yapılandırması ve eşikler değişmedi.
Eşleştirilmiş verici açık kazanç karşılaştırması bekleniyor. ST-06 açık kalır.

## 853 MHz eşik incelemesi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, ST-06 kapsamında mevcut yakın anten kayıtları
çevrimdışı incelendi; üretim eşikleri ve kazançlar değiştirilmedi. Periyodik Hann,
kayan noktalı FFT ve kaynakla aynı OS-CFAR penceresi/rank/katsayısıyla açık kaydın
327 örnek karesinde merkez hücre güçlü eşiği 14 kez, kapalıda sıfır kez aştı.
Açık kayıtta medyan güçlü eşik marjı −4,49 dB; zayıf eşik aşımı güçlüler dahil
119/327 idi. Bu sayılar donanımın bit-tam tekrar sonucu veya Pd değildir.
Normal doğrulama 3 karede 2 gözlem, zayıf yol 32 karede 24 gözlem gerektirir;
15 kare aralıklı kayıtla bu ardışık pencereler yeniden kurulamaz.
Gerçek yanıtların iki merkez confirmed olayında saklanan eşik marjı +0,388 ve
+0,180 dB idi; ilki o karede gözlenmemiş geçmiş olaydır. İkinciyle aynı I/Q
karesinin kayan noktalı marjı +0,158 dB çıktı; tek karşılaştırma genel bit-tam
uyum kanıtı değildir. Açık I/Q bileşenlerinin %98,208'i sıfır, kalanları ±1'dir.
Bu düşük sayısal seviye ve eşik altı dağılım seyrek tespitle uyumludur; kaybın
RF girişinde mi kanal seçimi/yeniden nicemlemede mi oluştuğu bu çiftle ayrılmaz.
Periyodik Hann açık/kapalı merkez güç farkı +7,150 dB; bu değer SNR değildir.
Yerel yeniden üretim: `python build/acceptance/st06-gui-20260906/analyze_rf853_threshold.py`.
Girdi ve kaynak SHA-256 kayıtlı rapor: `build/acceptance/st06-gui-20260906/rf853-threshold-diagnosis-01.json`.
Sonraki tanı kısa, sabit konumlu RX kazanç karşılaştırması ve eşzamanlı ham USB /
kart girdisi kaydıdır; uzun GUI testi gerekmez. ST-06 kabulü açık kalır.

## 853 MHz yakın anten açık/kapalı tanısı — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: kullanıcı beyanlı 853 MHz CW, TX gain 0,
RX LNA/VGA 16/16 dB ile aynı yakın anten konumunda ayrı açık/kapalı 10 saniyelik
koşuların her biri 4.883 kareyi sıfır USB/CRC/sıra/kuyruk hatası ve kırpılmayla
bitirdi. 327 örneklenmiş I/Q karesinin ortalama merkez-hücre gücü açıkta kapalıya
göre 7,15 dB arttı. Örneklenmiş FPGA yanıtlarında tam 853 MHz hücresinde iki
confirmed gözlem (biri o karede observed değil), kapalıda hedef çevresinde sıfır
confirmed gözlem vardı. Bu seyrek bulgu kararlı tespit veya Pd/Pfa kabulü değildir.
Yakın anten mesafesi sayısal kaydedilmedi; kapatma/expiry gecikmesi ayrı oturumlar
nedeniyle ölçülmedi. Yerel ham paket `build/acceptance/st06-gui-20260906/rf853-near-comparison-01.zip`.
Önceki uzak açık/kapalı merkez farkı 0,46 dB idi; koşullar karıştırılmaz. Kanal
seçici 0/0 dB kapalı ham kaydında Python referansıyla 128/128 byte-tam eşleşti;
çok düşük girişin çıkışta sıfıra yuvarlanması tespit yokluğunu tek başına
algoritmaya atfetmeyi engeller. ST-06 ve kontrollü tekrarlı RF kabulü açık kalır.


## 853 MHz kapalı referansı — 6 Eylül 2026

Kullanıcı alıcıyı geçici olarak `…36877e47` ile değiştirdi; ED_RX yapılandırması
bu cihaza bağlandı. KTR-4.1 / KTR-4.1-OPS-B0 kapsamında 853 MHz, LNA/VGA 0/0 dB
ve verici kapalı operatör beyanıyla yaklaşık 30 saniyede 14.648 kare işlendi;
USB/CRC/sıra/kuyruk hatası, kırpılma, ham aday ve etkin olay sayısı sıfırdı.
İlk alım giriş kırpılmasıyla durdu; sonraki aynı ayarlı koşu geçti. Başlangıç
kırpılmasının nedeni kanıtlanmadı. Yerel ham kayıt ve örneklenmiş I/Q paketi:
`build/acceptance/st06-gui-20260906/rf853-off-bundle.zip` (yeni klonda bulunması
varsayılmaz). Bu kısa negatif gözlem ortam sessizliği veya Pd/Pfa kabulü değildir;
verici açık eşleştirilmiş ölçüm henüz yapılmadı. ST-06 açık kalır.


## GUI ve oturum yaşam döngüsü gözlemi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, PHASE-08 / ST-06 kapsamında yeni ham kayıtlar
`results/evidence/phase08/gui-rx-lifecycle-v1.json` ve ZIP içinde saklanır.
900 MHz ayarında tek 15 dakikalık koşu 439.453 kareyi sıfır USB/CRC/sıra/kuyruk
hatasıyla tamamladı. Operatörün doğruladığı son-saniye masaüstü geçişinde
3,53 saniyelik çizim aralığı oluştu; kesintisiz GUI kabulü değildir.
Önceki kısa GUI koşusundaki bir USB taşması ve 104,65 MHz giriş kırpılması
başarısız kayıt olarak korunur. İki dakikalık görünür kısa koşu geçti.

Aynı uygulamada 30 saniye sonra durdurma yaklaşık 124 ms sürdü; yeni oturum
nesli, kare ve RX/FPGA zaman bilgileri sıfırlandı. Yeniden başlatılan 90 saniyelik
koşu 43.945 kareyi sıfır USB/taşıma hatası ve kırpılmayla tamamladı.
Ancak p95 RX→görüntü yaşı 153,47 ms ile 150 ms hedefini aşmıştır; örneklenmiş
kuyruk değerleri 118/512 ve 64/64'tür, kesin tepe değildir. Etkin olay olmadığı
için eski olay kimliklerinin karışmaması fiziksel olarak sınanmış sayılmaz.
Operatör masaüstünden döndüğünü bildirdi, fakat Qt gizlenme geçişi kaydetmedi;
pencereye dönüş gecikmesi ölçülmüş gibi sunulmaz. İlk iptal edilen oturumun
son USB istatistiği yoktur. Pencere kapatılarak kesilen denemeler ayrı korunur.

Çalışan hizmet özeti seri konsoldan doğrulandı; bitstream/imaj özeti okunamadı.
Vericinin kapalı olması operatör beyanıdır. RF doğruluğu, soğuk açılış,
tekrarlı dayanıklılık ve ST-06 kapanışı açık kalır. Sıradaki hedef uzun testleri
körlemesine tekrarlamak değil, yeniden başlatmadaki gecikmeyi kısa ölçümlerle
ayrıştırmak ve olay içeren yaşam döngüsünü sınamaktır. Eski kanıtlar değiştirilmedi.


## Güncel kanıt sınırı — 6 Eylül 2026

PHASE-08 / ST-06 ve KTR-4.1 / KTR-4.1-OPS-B0 kabulü açıktır.
5 Eylül tarihli 439.453 karelik tek arayüzsüz RX koşusunda USB taşması ve
CRC/sıra/kuyruk hatası görülmedi. Ölçülen 488,2153 kare/s, nominal
488,28125 kare/s üzerinde bir hız payı kanıtlamaz. Önceki kaynakla yapılan
iki uzun koşu USB taşmasıyla başarısızdı. GUI sürekliliği, RF tespit doğruluğu
ve kalıcı sorunsuz çalışma bu koşuyla doğrulanmadı; soğuk açılış kabulü de açıktır.

Tarihsel `native-channelizer-v3` ve `st06-parallel-product-v1` kanıtları
özgün kaynak hash'leri ve arşivleriyle korunur. Yeni RX koşusu kendi kaydıdır;
eski fiziksel sonuçlar değiştirilmiş PC kaynağına aktarılmaz.
İnceleme: `results/evidence/phase08/rx-evidence-recovery-v1.json` ve ZIP.
Doğrulama: `python scripts/verify_phase08_evidence_recovery.py`.
Bu işlem yeni donanım ölçümü içermez. Güncel ayrıntılar sinyal tespiti durum
belgesindedir; aşağıdaki tarihli kayıtlar kendi sürümlerinin sonuçlarıdır.

## Son ST-06 ürün güncellemesi — 5 Eylül 2026

Paketlenmiş hizmette CPU0 DMA sonrası güç çözme/doğrulamayı, CPU1 dar/geniş
aday ve olay işlerini yürütür. Kuyruk tamponlarının sahipliği değiştirilerek
ek kopya önlenir; hata geri alımında ortalama kayıtlı toplamdan türetilir.
Algoritma, medyan, eşikler ve RTL değişmedi. Üç zaman damgalı dijital ürün
koşusu 508,56 / 502,40 / 508,93 kare/s; 16.000 karelik karma tekrar ölçümü
529,30 kare/s verdi. Gerekli 488,28125 kare/s bu iş yüklerinde sağlandı.
Beş kısa testin ham yanıtları önceki paketle birebir eşleşti. Aktarım hatası
ve aday düşümü sıfırdı. Ek ARM kuyruk belleği 272 KiB'dir; FPGA artışı yoktur.
Kanıt: `results/evidence/phase08/st06-parallel-product-v1.json` ve ZIP.
Bu sonuç RF veya soğuk açılış kabulü değildir. SD değişmedi, hizmet geçici
yüklüdür. Hız payı sınırlıdır; saf periyodik ton/yoğun olay kapasitesi,
sürekli HackRF RX ve kör RF kapıları açıktır. ST-06 tamamlanmamıştır.
Aşağıdaki eski hız kayıtları kendi kaynak sürümlerinin tarihsel sonuçlarıdır.


5 Eylül 2026 son ST-06 optimizasyonu: ARM güç çözme ve durum yedekleme
maliyeti azaltıldı; eşikler, sekiz karelik pencere ve RTL değişmedi. PetaLinux
paketinden çıkan hizmetle üç fiziksel dijital koşu 464,87 / 460,37 / 463,74
kare/s verdi. Önceki 286–290 kare/s kaydı tarihsel karşılaştırmadır;
488,28125 kare/s kabul sınırı hâlâ geçilemedi. Beş test girdisinin kart
yanıtları önceki sürümle byte-tam eşleşti. Bu, RF doğruluk kabulü değildir.
Kanıt: `results/evidence/phase08/st06-product-optimization-v1.json` ve ZIP.
SD açılış dosyaları değişmedi; güncel hizmet geçici yüklüdür. ST-06 sürer.

Önceki kayıtlar ve mimari açıklamalar:

Bu proje; RF I/Q verisinin alınması, spektral analizi, sinyal tespiti, operatör
onaylı parametre ölçümü ve FPGA üzerinde gerçek zamanlı işlenmesi için geliştirilen
bir mühendislik sistemidir. Referans platform HackRF One, ZedBoard Zynq-7000 ve
Türkçe Qt Quick operatör uygulamasından oluşur.

Proje yalnız ölçülmüş veya tekrarlanabilir testle doğrulanmış sonuçları yetenek
olarak kabul eder. Canlı donanım, RF doğruluğu ya da performans kanıtı bulunmayan
işlevler uygulamada çalışıyormuş gibi gösterilmez.

## Sistem mimarisi

```text
SigMF / HackRF RX
       │
       ▼
Operatör bilgisayarı ── kontrol ve kayıt ──► ZedBoard PS / DDR
       │                                         │
       │                                         ▼
       ◄──────────── sonuçlar ───── ZedBoard PS: güç çözme → geniş bant → 2/3
                                                  ▲
                                               AXI DMA
                                                  ▲
                                     ZedBoard PL: Hann → 4096 FFT → Güç
                                                  → OS-CFAR hücre kararı
                                                  → 4096 işaretli güç kelimesi
```

Bu çizim ST-06 ürün imajının görev paylaşımıdır. PL→PS sınırı her karede
32 KiB işaretli güçtür; aday gruplama, sekiz karelik geniş bant kararı ve
temporal olaylar ARM'da işlenir. PC alım, 8→2 MS/s kanal seçimi, görünüm ve
kayıttan sorumludur. Host referansları sayısal eşdeğerliği denetler.

## Güncel aşama — 5 Eylül 2026

Çalışma PHASE-08 / ST-06 sinyal tespitindedir. ST-05 Python referansı seçilmiş,
C eşdeğerliği ve güç nicemleme kontrolleri geçmiştir. ARM geniş bant çekirdeği
kayan nokta kullanır. Güncel FPGA tasarımı 50 MHz zamanlamayı geçmiş; LUT
kullanımı 19.587/53.200 (`%36,82`), BRAM `%16,79`, DSP `%21,36` olmuştur.
Bu sonuç [Vivado kaydına](results/evidence/phase08/st06-power-vivado-v1.json) aittir.

Bağımsız kart DMA/ARM profili beş adet 2.000-kare tekrarda 551,22–577,68
kare/s ölçmüştür; 2 MS/s için gereken hız 488,28125 kare/s'dir. Ölçüm ürün
ağ hizmetinin veya canlı RF'nin kabulü değildir;
[profilin kapsamı](results/evidence/phase08/st06-pipelined-dma-profile-v1.json)
korunur. Güncel bitstream ve ARM hizmeti PetaLinux ürün imajında paketlenmiştir;
[ürün entegrasyon kanıtı](results/evidence/phase08/st06-product-integration-v1.json)
paket 5.679/5.679 ve tam imaj 6.090/6.090 derleme görevini doğrular.

5 Eylül kart tanısında FPGA/hizmet/ağ köprüsü geçici yüklenmiştir. Bağımsız
256 gürültü karesinde doğrulanmış olay yoktur; dar ton 255/256, geniş bant
249/256 karede doğrulanmış ve sıfır giriş kuyruğunda olaylar sonlanmıştır.
Bu kısa dijital deney RF doğruluğu kabulü değildir. Ürün yolu 286–290 kare/s
ile gerekli 488,28125 kare/s hızını **geçememiştir**; ARM tespit iş parçacığı
darboğazdır. [Ham verili tanı kaydı](results/evidence/phase08/st06-product-board-diagnostic-v1.json)
başarısız hız kapısını da korur. SD açılış dosyaları değişmemiştir.
Soğuk açılış, ürün hızı ve kontrollü kör RF doğruluğu açık kalır.
ST-06 ve PHASE-08 tamamlanmamıştır.
Sonraki çalışma bu kabul kapılarıdır. Güncel durumun ayrıntıları
[sinyal tespiti durum belgesinde](docs/interfaces/SIGNAL_DETECTION_STATUS.md),
faz sırası [yol haritasında](docs/plans/IMPLEMENTATION_ROADMAP.md) tutulur.

## Mevcut yetenekler

Bu bölümdeki tarihli ölçümler ilgili eski kaynak sürümlerine aittir. ST-06
ürününün güncel kabul durumu yukarıdadır; aşağıdaki aday-paket PL mimarisi ve
kaynak kullanım sayıları tarihsel tasarımları anlatır.

31 Ağustos sinyal tespiti bakımında spektrum ve waterfall çizimi Qt görüntü
tamponuna taşınmıştır: 128 satır, dar tepe koruma, sabit güç/renk ölçeği ve
15 DSP karesinde bir canlı görünüm hedefi bulunur. Tarama görünümü, bütünlüğü
geçen pencerenin gerçek karelerinden geçmiş gösterir. Yeni görünümün canlı
kabulü eski fiziksel kayıtlardan devralınmaz. Geniş bant kurtarmanın bölgesel
gürültü tabanı kirlenmesi sınırı ve güncel SystemVerilog/ARM sahipliği
[durum belgesinde](docs/interfaces/SIGNAL_DETECTION_STATUS.md) açıklanmıştır.

8 MS/s, 16.384 noktalı canlı görünüm gücü için ayrıca hostta kaba aday yolu
bulunur. Dörder hücrenin enerjisi toplanarak mevcut 4.096-hücre OS-CFAR ve
geniş bant referansına verilir; sarı kaba RX alanı, yeşil FPGA doğrulamasından
ayrıdır. Bağımsız sentetik kabulte 100 kHz–4 MHz aileleri 32/32 geçmiş, 6 MHz
31/32 ile yalnız karakterize edilmiş, bütün 8 MHz doluluğu çözülememiştir.
Bu sonuç RF veya FPGA kabulü değildir; ayrıntı ADR-0038 ve
`results/evidence/phase08/coarse-rx-detection-v1.json` içindedir.

Güncel çalışma, frekansı bilinmeyen yayının **yalnız alımla aranmasına** odaklanır.
HackRF görünümündeki `Frekans Taraması`, 1–6.000 MHz aralığını 9.999 bitişik
600 kHz sorumluluk hücresinde, örtüşen 2 MHz alıcı ayarlarıyla sırayla işler;
bütün aralık aynı anda dinlenmez. Her pencere 128 gerçek
I/Q karesinin kartta işlenmesi ve alım bütünlüğünün geçmesiyle kapsama eklenir.
Başarısız ve ziyaret edilmemiş bantlar boş bant sayılmaz. Gözlemler tur boyunca
korunur; tarama durdurulduktan sonra seçilen frekans sabit bantta izlenebilir.
Bu geometri 1 MHz desteği en az bir ayarın doğrulanmış kanal seçici geçiş bandı
içinde tutar; RF algılama olasılığı garantisi değildir. Kısa yayınlar kaçabilir
ve tek antenin bütün aralıkta duyarlı olduğu varsayılmaz.

**Kanıt sürümü sınırı:** Aşağıdaki eski fiziksel kabul kayıtları, içlerinde
belirtilen kaynak sürümlerine aittir. Yeni tarama ve Windows ikili I/Q taşıma
değişiklikleri bu kayıtların güncel kaynak kabulü olduğu anlamına gelmez;
kaynak özeti denetimleri korunur. Yeni çalıştırmalar, yapılandırma/kaynak özetleri
ve gerçek kart sonuçlarıyla `build/acceptance/rx-survey/` altında ayrı JSONL
kayıtları oluşturur. Kısa alıcı denemeleri tam bant doğruluğu, gizli vericiyi
bulma başarısı veya saha kabulü değildir.

| Alan | Durum |
|---|---|
| SigMF kayıt açma, sözleşme denetimi ve gerçek I/Q işleme | Doğrulandı |
| HackRF araç/cihaz denetimi ve RX alımı | Seri numarasına bağlı fiziksel HackRF-1 ile 8 MS/s RX, DC-güvenli offset tuning ve host tespiti önceki kaynaklarda geçti. Güncel ADR-0039 sürümünde görünüm 32,15 Hz hedefini geçmiştir; ancak hem ürün hem doğrudan aktarım shortfall ürettiğinden farklı USB port/kablo tekrarı ve uzun kabul açıktır |
| PC kanal seçici ve ZedBoard ağ taşıması | 8→2 MS/s, 193 tap anti-alias kanal seçici C++17 AVX2/FMA3 yolunda NumPy referansına 80 karede bayt-tam eşdeğerdir; p95 süre 0,525 ms'dir. Tam CI8/4096 çerçeve ve çift CRC'li dört derinlikli TCP→yerel hizmet yolu önceki fiziksel kaynak sürümünde doğrulanmıştır. Güncel kartta TCP 47007 açıktır; son ADR-0037 bitstream kabulü açıktır |
| Hann, çalışma zamanında 4096/8192/16384 FFT, dBFS spektrum ve spektrogram | FPGA'da üç boyut için tekrarlı fiziksel sayısal hız ve bütünlük doğrulaması geçti; canlı HackRF dayanıklılık tekrarı açıktır |
| Uyarlanabilir hücre tespiti, bütünleşik geniş bant enerjisi, aday gruplama ve 2/3 zamansal doğrulama | Host referansı ve fiziksel PL→DMA→ARM zincirinde doğrulandı. Kalıcı kart imajıyla yapılan beş sürekli 2 MS/s kabul koşusunda toplam 20.480/20.480 kare sıfır hatayla işlendi; en düşük hız 508,76 kare/s oldu |
| Emisyon merkezi, gözlenen taşıyıcı, OBW99, göreli güç ve SNR ölçümü | Canlı ürün ölçümü seçili dört CI8 kareyi gerçek PL Hann→4096 FFT→güç yolundan geçirir; ARM bütün sayısal alanları çıkarır ve taşıyıcı gözlenemediğinde sonuç üretmekten kaçınır. Altı sentetik sahne kartta geçti. Sinyal türü ertelendi; RF doğruluğu ve dBm kalibrasyonu açıktır |
| Manuel açı–güç ölçümüne dayalı bağıl geliş açısı ve kerteriz | Seçili confirmed kanal gücü, 15°/24-açı saha profili, ham maksimum ve fail-closed kalite kapıları host modelinde sayısal olarak doğrulandı; ARM hizmet bağı ve fiziksel derece RMS kabulü açık |
| ZedBoard PL CI8→Hann→FFT→güç→aday paketi zinciri | SystemVerilog ve AMD FFT IP ile kanonik P0 blok tasarımına alındı; Vivado sentez, route, 50 MHz setup/hold, bitstream ve XSA kapıları geçti |
| FPGA tespit, gruplama ve aday paketleme blokları | Bit-doğru alt blok doğrulamalarına ek olarak tam kart tasarımında 27.453 LUT, 81,5 BRAM tile ve 71 DSP ile route edildi; setup WNS +0,423 ns, hold WHS +0,021 ns |
| ZedBoard üzerinde DMA ve tespit zinciri | Değişken 64–54.144 bayt aday paketi, S2MM gerçek uzunluk sürücüsü ve yerel Linux hizmeti kalıcı PetaLinux imajında doğrulandı. Soğuk açılış, bit-doğru 54 aday yaşam döngüsü ve tekrarlı 2 MS/s hız kapıları geçti |
| AM/NFM izleme zinciri | Kayıtlı I/Q ve QML ürün akışında doğrulandı; canlı HackRF/ses saha kabulü bekliyor |
| Ürün kapsamı | Yalnız RX tabanlı ED işlevleri bulunur; ET arayüzü, görev/TX kodu ve yapılandırması kaldırılmıştır |

Parametre sonuçları kalibrasyonsuz `dBFS` ölçeğindedir; `dBm` ölçümü değildir.
Faz uyumlu çok kanallı DoA, menzil veya otomatik hedef konumu üretilmez.

## Operatör uygulaması

Uygulama yalnız ED görevlerini sunar: veri kaynağı, bağlı spektrum/spektrogram
görünümü, tespitler, üç adımlı sinyal ölçümü, AM/NFM dinleme, manuel yön bulma,
sistem sağlığı ve salt okunur olay konsolu aynı ürün kabuğundadır. Çalışma
zamanı yalnız gerçek SigMF/HackRF RX kaynaklarını içerir; mock kaynaklar,
gösterim verileri ve eski laboratuvar arayüzleri ürün paketine girmez.

`HackRF Canlı RX` görünümü izleme merkezini, LNA/VGA kazançlarını ve sınırlı
canlı ED oturumunu yönetir. Gösterilen geniş spektrum aynı alımın ham 8 MS/s
I/Q karesine, ayrıntılı tespitler ise 2 MS/s kanal seçilmiş kareye verilen
ZedBoard FPGA/ARM yanıtına bağlıdır. Sarı kaba RX adayı host önerisidir; yeşil
durum FPGA doğrulamasıdır. Kart bağlantısı yoksa uygulama FPGA sonucu üretmez.

Fiziksel ürün arayüzünden başlatılan beş ardışık 4.096-kare oturumu toplam
20.480 kareyi sıfır USB taşması, taşıma CRC/sıra hatası ve I/Q kırpılmasıyla
tamamlamıştır. Bu kabul 104,65 MHz izleme merkezi ve LNA/VGA 0/0 dB koşulundadır;
ortam RF sinyallerinden tespit doğruluğu yüzdesi çıkarılmaz. İlk 16/16 dB
denemesinde kırpılma oluşmuş ve oturum sonuç üretmeden reddedilmiştir.
[Ölçüm kaydı](results/evidence/phase08/product-live-acceptance.json) başarısız
denemeyi de korur. Oturum açılışını içeren hızlar FPGA azami kapasitesi veya
C/C++ karşısında hızlanma iddiası değildir. Fiziksel durdurma ve yeniden
başlatma geçmiştir. Canlı parametre ürün bağı dört ardışık gerçek FPGA karesiyle
işlevsel olarak geçmiştir; kontrollü RF doğruluğu, canlı ses ve saha kalibrasyonu
ayrı kapılardır.

Kayıtların bütünlüğü `python scripts/verify_phase08_product.py` ile denetlenir.
Yeni fiziksel gözlem için `python scripts/capture_phase08_product.py --output
build/acceptance/new-product-run` ürün penceresini açar; cihaz denetimi ve oturum
başlatma operatör tarafından yapılır. Araç yalnız gerçek alımı gözlemler;
örnek veri veya kart yanıtı üretmez.

8 MS/s canlı ürün yolu derlenmiş kanal seçici gerektirir. Windows Release
çekirdeği şu komutlarla hazırlanır; DLL oluşmazsa fiziksel ürün yavaş Python
yoluna sessizce düşmez:

```powershell
cmake -S algorithms\p0\native -B build\native\p0_channelizer -G "Visual Studio 17 2022" -A x64
cmake --build build\native\p0_channelizer --config Release
python scripts\verify_phase08_native_channelizer.py
```

Canlı tespit listesi varsayılan olarak doğrulanmış gözlemleri gösterir;
`Adayları göster` henüz doğrulanmamış olayları açar. Ölçüm için gereken son dört
ardışık FPGA karesi görünür tespitlerle birlikte otomatik korunur; operatörün
listeyi dondurması gerekmez. Seçili olay kaybolduğunda `Son gözlem`, oturum bittiğinde
`Son oturum` gösterilir; aynı frekanstaki yeni olay otomatik olarak eski
seçime bağlanmaz. Spektrum ve spektrogram seçili frekansı ortak kılavuzla
gösterir. Önceki kabulde görüntüleme yaklaşık 10 Hz'dir. Yeni görünüm 15 karede
bir, nominal 32,55 Hz güncelleme hedefler; FPGA bütün I/Q karelerini işler.
Güncel arayüz ölçüsü geçmiştir, fakat USB shortfall nedeniyle uzun fiziksel
kabul açıktır.
[Canlı seçim görünümü](results/evidence/phase08/detection-selection-aligned.png)
frekans kılavuzunun spektrum ve spektrogramdaki ortak konumunu gösterir.
UI yük karşılaştırmasının olumlu ve olumsuz ham kayıtları ile sınırları
[`detection-ui-decoupling.json`](results/evidence/phase08/detection-ui-decoupling.json)
özetindedir; `python scripts/verify_phase08_detection_ui.py` arşivi yeniden
hesaplayarak doğrular. USB okuma, 512 karelik sınırlı ham-I/Q kuyruğuyla kanal
seçimi ve FPGA taşımasından ayrılmıştır. Önceki kaynak sürümü sekiz tam fiziksel ürün
koşusunda 32.768/32.768 kareyi sıfır USB taşmasıyla tamamlamış; operatör iptali
750. karede ve ardından yeniden başlatma ayrı ayrı geçmiştir. En yüksek kuyruk
kullanımı 111/512'dir. Ayrı kesintisiz dayanıklılık kabulü 15 dakika boyunca
439.453/439.453 kareyi ve 14.399.995.904 ham baytı sıfır USB/CRC/sıra/kuyruk
hatası ve sıfır kırpılmayla tamamlamıştır; ham kuyruk tepe kullanımı
170/512'dir. Hash-bağlı özet
[`live-rx-endurance-v2.json`](results/evidence/phase08/live-rx-endurance-v2.json)
içindedir ve `python scripts/verify_phase08_endurance.py` ile yeniden
doğrulanır. Bu kayıtlar ADR-0039 kaynak sürümüne devredilmez; güncel
`live-rx-display-8msps-v2.json` üç USB shortfall nedeniyle başarısızdır. Ortam
sinyalleri kontrollü RF doğruluğu kanıtı değildir.

Dört ardışık confirmed+observed FPGA karesine bağlı canlı parametre ürün akışı
gerçek HackRF oturumunda dokuz sonuç alanını üretmiştir. Hash-bağlı işlevsel kanıt
[`live-parameter-functional.json`](results/evidence/phase08/live-parameter-functional.json)
içindedir ve `python scripts/verify_phase08_live_parameter.py` ile yeniden
doğrulanır. Bu kayıt ürün bağını kanıtlar; ortam sinyalinden frekans, bant
genişliği, güç veya sınıflandırma doğruluğu yüzdesi çıkarmaz.

### Kurulum

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements\phase02.txt
```

### Çalıştırma

```powershell
python -m app.operator_console
```

Klavye kısayolları:

- `Ctrl+O`: SigMF kaydı açar.
- `Boşluk`: Spektrum alanında taramayı başlatır veya duraklatır.
- `Ctrl+1`, `Ctrl+2`, `Ctrl+3`, `Ctrl+4`, `Ctrl+5`: ED çalışma alanları arasında geçer ve
  klavye odağını seçilen alana taşır.
- `Ctrl+B`: Spektrum alanında veri kaynağı panelini açar veya kapatır.
- `Alt+Sol`, `Alt+Sağ`: frekans görünümü geçmişinde geri veya ileri gider.
- `Ctrl+0`: spektrum ve spektrogramı tam banda döndürür.
- `Esc`: açık olay konsolunu kapatır.

## Doğrulama

Tam yazılım regresyonu:

```powershell
python -m pytest tests
```

Operatör arayüzü 1280×720, 1366×768, 1920×1080 ve %150 ölçek koşullarında
aşağıdaki doğrulayıcıyla yeniden üretilebilir:

```powershell
python -B scripts\verify_app_f_release_ui.py
```

Sistem çalışma alanı etkin işlem zincirini ve host/FPGA kabul sınırını açıkça
ayırır. Filtrelenebilir olay günlüğü çalışma durumunu salt okunur olarak izler;
ürün görünümü komut çalıştıran bir terminal içermez.

Ayrıntılı gereksinim durumu ve yöntem sınırları
[`docs/requirements/KTR_TRACEABILITY.md`](docs/requirements/KTR_TRACEABILITY.md),
sistem hedefi ise
[`docs/architecture/SYSTEM_BASELINE.md`](docs/architecture/SYSTEM_BASELINE.md)
altında tutulur.

## Depo düzeni

- `app/`: Qt Quick operatör uygulaması ve sunum katmanı.
- `app/operator_console/quick_*_actions.py`: tarama, ölçüm, dinleme ve yön bulma
  kullanıcı eylemlerini ayıran sunum denetleyicileri.
- `app/operator_console/qml/`: ana kabuk, görev çalışma alanları ve ortak görsel
  bileşenler; QML dosyaları tek bir dev ekran tanımı olarak tutulmaz.
- `algorithms/`: host referans DSP, tespit, parametre, izleme ve FPGA RTL kaynakları.
- `platforms/`: HackRF alım katmanı ile Zynq PS/embedded bileşenleri.
- `profiles/`: doğrulama kapılarını geçmiş çalışma profilleri.
- `tests/` ve `verification/`: otomatik regresyonlar ve bağımsız doğrulama araçları.
- `docs/`: mimari, gereksinim izlenebilirliği ve teknik kararlar.

## RF güvenliği

Depoda RF yayın yolu veya TX çalışma zamanı yoktur. Güncel ürün yalnız alım
tabanlı ED işlemleri yapar. Tarihsel güvenlik kararları geçmiş kayıt olarak
korunur; güncel üründe yayın yeteneği bulunduğu anlamına gelmez.
