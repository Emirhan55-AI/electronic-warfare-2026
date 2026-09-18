# Referans Modeller

## KTR-4.4 uyarlamalı yön planlayıcı — 16 Eylül 2026

`algorithms/p0/adaptive_df.py`, doğrulanmış `0°` başlangıcından saat yönündeki
ilk lob dışı sınıra, `0°`a dönüşten sonra ters sınıra, ardından 5° tepe
hassaslaştırmasına ve tek karşı-yön denetimine giden sınırlı ölçüm sırasını
üretir. `df.py` nihai sonucu en az sekiz farklı ölçülmüş açı, 3 dB tepe ve
ön/arka kapılarıyla verir; interpolasyon yapmaz.

## KTR-4.4 kilitli yön kanalı toplam gücü — 16 Eylül 2026

`P0PM-v4`, dört PL UQ28.30 güç karesinde kilitli sabit kanalın ortalama toplam
gücünü hesaplar. Sinyal ve alıcı gürültüsü birlikte tutulduğu için hedef tespit
eşiğinin altına indiğinde açı kaybolmaz; değer gürültü tabanına yaklaşır ve yayın
varlığı kanıtı sayılmaz. Python referans modeli ile ARM C sonucu aynı ölçek
sözleşmesini kullanır. Normal P0PM parametre yolu gürültü çıkarılmış güç ve kalite
kapılarını korur. Fiziksel kartta normal yol düz spektrumu reddederken P0PM-v4
aynı girdide sonlu toplam güç üretti; altı normal parametre sahnesi de geçti.
Geçici kart kurulumu yeniden başlatmada korunmaz; canlı RF/RMS kabulü açıktır.

## KTR-4.2 parametre iyileştirmesi — 16 Eylül 2026

Merkez frekansı ve ayrı taşıyıcı çizgisi ana sonuçlarda ayrıldı. Yetenek bildiren
kartta manuel ölçüm 16 özgün kareye (2 MS/s hızda 32,768 ms) uzatıldı; eski
kartta dört kare korunur. P0PM-v3, ARM grup kararlılığı denetimi ve kayıt/CRC
bağı eklendi; sayısal hesap için PC geri dönüşü yoktur. PL'nin kare başına
4096 FFT işlemi değişmedi. Yerel Analog/Sayısal modeli seçili kanal filtresiyle
aynı önişlemede yeniden eğitildi; sonuç deneysel tahmin olarak gösterilir.
Kaynak/test ve ARM derlemesi tamamlandı; karta yükleme ve yeni RF ölçümü
henüz yapılmadı. PHASE-08/ST-06 ve fiziksel KTR-4.2 kabulü açıktır. Yöntem,
kanıtlar, uyumluluk ve sınırlar: `docs/interfaces/PARAMETER_REFINEMENT_20260916.md`.

## KTR-4.3 dinleme kolaylıkları — 16 Eylül 2026

Bilinmeyen yayında aynı I/Q kaydını AM ve dar bant FM ile karşılaştırma,
sade kanal seçimleri, gizlenebilir ince ayar ve isteğe bağlı 200 Hz konuşma
filtresi eklendi. Yöntem seçimi otomatik tür tespiti sayılmaz. Canlı ses
hazırlığı son beş saniyeyi sabitleyip RX'i durdurur; kesintisiz ses akışı ve
sayısal kod çözümü yoktur. PL/ARM/RTL ve tespit kapıları değişmedi.
Kaynak/test doğrulaması yeni fiziksel kabul değildir; PHASE-08/ST-06 ve
KTR-4.3 açık kalır. Güncel ayrıntı `docs/interfaces/SIGNAL_MONITORING_LISTENING_STATUS.md`,
tekrarlanabilir ölçüm ve test kaydı `docs/reviews/LISTENING_ASSISTANCE_20260916.md` içindedir.

## Yalnız ED kaynak kapsamı — 13 Eylül 2026

ET dalga biçimi, görev ve iletim algoritmaları kaldırılmıştır. Bu dizin yalnız
ED tespit, parametre, dinleme, yön bulma ve bunları destekleyen FPGA/PS
algoritmalarını taşır. Aşağıdaki eski ET bölümleri tarihsel kayıttır.

## PÇ-02/PÇ-04 sayısal eşdeğerlik — 11 Eylül 2026

F5'in taşıyıcı çizgisi dahil ilk üç teknik parametre yolu C11'e taşındı. 33
sentetik sahnede Python ile alan durumları ve değerleri eşleşti. Taşıyıcı
artifakt kapısının 3968 noktalı DFT'si ARM'da Bluestein/8192 ile aynı uzunlukta
hesaplanır; tepe çalışma belleği 327.680 bayt, kalıcı ölçüm belleği 56.064
bayttır. Sınıflandırma taşınmadı. Gerçek PL→ARM altı sahne ayrıca kartta geçti;
bu testler RF doğruluk kabulü değildir.

## CFAR katsayı girişi — 10 Eylül 2026

Tamsayı model ve RTL isteğe bağlı normal/zayıf Q32 katsayılarını destekler.
Genel üst modülde `RUNTIME_CONFIG=0` korunur; güncel yapılandırılabilir kart
varyantı bunu `1` yapar. Yeni test dört çerçevede
16.384 kelime, geçersiz ayar, kare yalıtımı ve reset davranışını denetler.
Güncel bitstream/kart kanıtı ayrı hash bağlı pakettedir; önceki bitstream
kanıtı güncel kaynak için geçerli sayılmaz.
[Kontrol sözleşmesi](../docs/interfaces/DETECTION_RUNTIME_CONFIG_CONTRACT.md).

## ST-06 zayıf güç metaverisi — 10 Eylül 2026

`rtl/p0_os_cfar.py` ve `fpga/p0/rtl/axis_p0_os_cfar.sv` DMA v2 zayıf
kararını birlikte üretir. Normal eşik değişmedi; zayıf eşik Q32
`17098572778` ile aynı sıra istatistiği üzerinden hesaplanır. ARM bağlantısı
yalnız zayıf adayları 24/32 yoluna gönderir. Yeni RTL simülasyonu donmuş v1
kanıtını değiştirmeden 45.056 kelimede eşleşti; fiziksel kabul ayrıdır.
[Kaynak kılavuzu](../docs/interfaces/DETECTION_TUNING_AND_SOURCE_GUIDE.md).

## Dört parametrenin gerçek RF durumu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: yeni temiz AM koşusunda dar aralık SNR'si
13,36–15,32 dB iken sabit aday 10/10 Belirsiz kaldı. Yeni `rf_observation`
ürün dışı ön işlemesi uzun I/Q, FIR kanal süzme ve frekans kayması
hipotezlerini uygular; kesin sınıflandırıcı değildir. Kullanılabilir donanım
son beyana göre yalnız iki HackRF'dir; dBm kalibrasyonu diğer işleri durdurmaz.
Ürün/ARM/RTL ve önceki kabul durumları değişmedi.

[Ayrıntılı durum, araştırma ve yeniden üretim](../docs/reviews/PARAMETER_EXTRACTION_ASSESSMENT.md).


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


## PHASE-10 Tekli Görev taban bandı — 8 Eylül 2026

`algorithms/transmission/single_band_noise.py`, seçilen tek RF aralığı için
8 MS/s deterministik, bant sınırlı kompleks gürültü döşemesi ve tam süreli CI8
görev dosyası üretir. Modül SDR açmaz veya RF gönderimi başlatmaz. Fiziksel süreç
sınırı `platforms/transmission` altındadır ve varsayılan güvenlik profili kapalıdır.

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


## PÇ-01 sınırı — 7 Eylül 2026

KTR-4.2 / KTR-4.2-F1 arayüz ve güncel gözlem bağı uygulanmıştır.
Kestirimci, RTL ve kart hizmeti değişmedi; F5 ölçümü bilgisayarda kalır.
Yazılım kanıtı `results/evidence/phase08/parameter-workflow-v1.json` ve ZIP;
RF doğruluğu, dBm kalibrasyonu ve ARM taşıması bu kabulün dışındadır.

## PÇ-00 yeniden üretilebilir ölçüm bağı — 7 Eylül 2026

KTR-4.2 için uygulama katmanı F5'e verilen dört normalize I/Q karesini,
profil/model/kaynak özetlerini ve ham alan durumlarını saklar. Aynı kaynakla
`scripts/verify_parameter_record.py` alanları yeniden hesaplar; uyumsuz
kaynak, değişmiş I/Q veya sonuç reddedilir. F5/RTL/ARM algoritması, eşikleri
ve kilitli profilleri değiştirilmedi. Bu kayıt eşdeğerliğidir, bağımsız RF
doğruluğu değildir. Yeni kanıt `results/evidence/phase08/parameter-record-v1.json`
ve ZIP içindedir; PÇ-02 fiziksel doğruluk ve kalibrasyon kapıları açıktır.

## Zorunlu parametrelerin mevcut yöntemi — 7 Eylül 2026

Kullanıcı dört zorunlu alanın geliştirme planlamasını açtı. QML ürün yolu
`parameters/F5ParameterEstimator` kullanır; ayrı `p0/parameters.py` referansı
ile karıştırılmaz. F5 taşıyıcı çizgisi, OBW99, göreli kanal gücü ve sınırlı
Analog/Sayısal/Belirsiz alanlarını içerir. ARM C sayısal karşılaştırması bu
oturumda AM/geniş bantta sıfır farkla geçti; bu host testi yeni RF kanıtı
değildir. OBW99 yöntem sınırı, kalibrasyon, sınıflandırma ve ARM taşıma sırası
[yol haritasındadır](../docs/plans/IMPLEMENTATION_ROADMAP.md). Yöntem, eşik ve
kilitli profiller değiştirilmedi; ST-06 ve parametre RF kabulü açıktır.

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

Güncel PHASE-08/ST-06 sinyal tespiti için `p0/st05_wideband.py` geniş bant
referansıdır; C eşdeğeri ZedBoard ARM'de çalışır. Hann/FFT/güç/OS-CFAR hücre
kararı PL'dedir. Dijital kart tanısı ürün hızını henüz geçememiştir.
[Güncel durum](../docs/interfaces/SIGNAL_DETECTION_STATUS.md) kaynak/kanıt
sınırını tanımlar. Aşağıdaki faz açıklamaları ilgili tarihsel sürümlerin
özetidir; örneğin E1'in başarısızlığı daha sonraki F5 host profilinin sonucu
olarak okunmaz. Parametre/DF/ET bu ST-06 çalışmasının kapsamı değildir.

- `sigmf/`, PHASE-01 metadata ve binary yerleşim sözleşmesini yalnız Python standart kütüphanesiyle doğrular. Örnek değerlerini dönüştürmez ve DSP uygulamaz.
- `spectrum/`, PHASE-02 bounded SigMF çerçeve kaynağını ve Qt'den bağımsız floating-point Hann/FFT/güç/PSD golden modelini içerir.
- `detection/`, PHASE-03 bölgesel/CA/OS detectorlerini, kaba bölge gruplamasını, bounded temporal olay belleğini ve katalog tabanlı sentetik sahneleri içerir.
- `pipeline/`, allowlist bloklarından doğrulanmış işlem profilini kurar; PHASE-04 ve E1 alan-bazlı comparison/digest bağlarını doğrular ve geçersiz bağda PHASE-03 Operasyon zincirine döner.
- `parameters/`, PHASE-04 geçerlilik modeli ve başarısızlık deneylerinin yanında E1 confirmed-olay span önerisini, dört bounded frame ölçümünü, taşıyıcı çizgisi/emisyon merkezi/OBW99/dBFS/sınırlı alan kurallarını ve `34.084 byte` kalıcı payload sınırını içerir. E1 profili yalnız doğrulanan alanları kurabilir; mevcut karşılaştırmada doğrulanan alan yoktur.
- `monitoring/`, operatör seçimli AM/NFM için bounded DDC, FIR kanal süzme, frame-sürekli NFM faz farkı, 48 kHz mono ses, PCM16/WAV ve deterministik fixture/evaluation sözleşmesini içerir. Kesintisiz yolda 250 ms pencereli dBFS kanal gücü ile DDC sonrası artık merkez frekansı dizileri de üretilir. Korunmuş fiziksel HackRF NFM tekrar kaydında 1.700 Hz referans ton 1.699,951 Hz olarak çıkarılmıştır; içerik sentetik RF tekrarıdır, gerçek konuşma kabulü değildir.
- `rtl/`, PHASE-06A `ci8` AXI4-Stream frame-istatistik bloğunun yalnız tam sayı kullanan bit-doğru Python golden modelini ve deterministik HDL vektör üretimini içerir.
- `rtl/hann_window.py` ve `rtl/hann_vectors.py`, PHASE-02 float64 periyodik Hann dizisinden dondurulmuş UQ1.15 katsayı üretir; donanım sonucunu integer çarpım, açık yuvarlama ve SQ1.15 çıkışla bit-doğru modeller.
- `rtl/fft_model.py` ve `rtl/fft_vectors.py`, PHASE-06C için PHASE-02 unscaled forward FFT'yi SQ1.15 giriş/29-bit Q15 çıkış sınırında idealize eder, scaling adaylarını nicel karşılaştırır ve wrapper transport stub vektörünü matematiksel FFT golden'ından ayrı tutar.

PHASE-06C Python modeli seçilen dış FFT sayısal sözleşmesini karakterize eder fakat AMD C-model değildir. Gerçek vendor FFT sonucu PHASE-06D'nin ayrı AMD C-model/XSim katmanında doğrulanır; FFT sonrası güç ve detector PL biçimi uygulanmamıştır. PHASE-04 sonuçları yalnız katalogdaki sentetik ailelerde ve kayıtlı I/Q çalışma yolunda doğrulanabilir; genel gerçek dünya sınıflandırması, kalibre edilmiş RF gücü veya canlı RF işlevi değildir.

`algorithms/fpga/phase06d_vectors.py`, PHASE-06C'nin on giriş frame'ini byte-değişmez devralır ve natural-order negatif frekans denetimi için exact-bin tone ekler. `rtl/amd_xfft_cmodel_driver.cpp`, yerel AMD FFT v9.1 bit-accurate C-model API'sini dondurulmuş fixed-point yapılandırmayla çalıştırır ve signed 29-bit Q15 sonucu 64-bit dış lane düzeninde yazar.

PHASE-06D sayısal doğrulaması dört kaynağı ayrı tutar: PHASE-02 NumPy floating golden, PHASE-06C idealize 29-bit Q15 mimari model, gerçek AMD bit-accurate C-model ve generated AMD FFT'nin XSim çıktısı. Zorunlu kabul C-model ile XSim'in tam kompleks integer çıktılarda bit-eşitliğidir; NumPy ve PHASE-06C farkları yalnız ayrı karakterizasyon ve algoritmik yapı çapraz kontrolüdür. FFT-output güç, PSD ve detector referansı bu fazda eklenmemiştir.

`rtl/fft_power.py` ve `rtl/power_vectors.py`, PHASE-06F için PHASE-06D'nin gerçek signed 29 bit FFT integer alanlarından exact `I²+Q²` hesaplar. Model Python arbitrary-precision integer aritmetiği kullanır; 58 bit `UQ28.30` sonuçta rounding, truncation veya saturation yoktur. PHASE-02 floating güç/PSD modeli ve PHASE-06D FFT vendor referansı ayrı katmanlar olarak korunur. PHASE-06F PSD normalization veya detector algoritması uygulamaz.

`rtl/regional_detector.py` ve `rtl/detector_vectors.py`, PHASE-06G için PHASE-03 `regional` matematiğini bağımsız integer/bit-true katmanda uygular. Natural↔shifted mapping, exact doubled even median, üç doğrulanmış Pfa için UQ*.24 noise/threshold, mask ve strict decision alanları üretilir. On beş sentetik ile beş frozen PHASE-06F real-power frame'i kullanılır. Floating `algorithms/detection/cfar.py`, bit-true model ve SystemVerilog birbirinden ayrı doğrulama katmanlarıdır; grouping/temporal/PHASE-04 parametre çıkarımı bu modelde yoktur.

`rtl/candidate_grouping.py` ve `rtl/candidate_vectors.py`, PHASE-06H için authoritative `DetectionPipeline._group` davranışını PHASE-06G integer hücre metadata'sına uygular. Shifted detected index farkı en fazla iki olduğunda aynı kaba aday oluşturulur; start/end ilk/son detected bindir, eşit peak'te ilk/düşük shifted bin kazanır ve peak-region noise/threshold korunur. On iki sentetik köşe frame'i ile bir frozen gerçek PHASE-06G frame'i kullanılır. Coarse span `end-start+1` olup precise bandwidth, Hz/dB, temporal association veya PHASE-04 parametre çıkarımı değildir.

`ps/candidate_transport.py` ve `ps/transport_vectors.py`, PHASE-06I little-endian ABI v1 packet'ını bağımsız Python encode/decode katmanında tanımlar. Header/record/trailer boyutları, frame ID, empty frame, count, status, reserved alanları, exact integer metadata ve payload CRC32 strict doğrulanır. Bu model DMA veya PS temporal runtime değildir.

`ps/temporal_confirmation.py` ve `ps/temporal_vectors.py`, PHASE-06J için yeni temporal kural icat etmeden PHASE-03 `DetectionPipeline._update_tracks` state machine'ini PHASE-06I packet candidate'larına uygular. Python katmanı C11 PS çekirdeğinin golden oracle'ıdır; uint32 wrap ardışık kabul edilir, diğer frame gap'leri reset üretir. Fiziksel Hz/dB dönüşümü veya gerçek DMA/PetaLinux davranışı içermez.
