# Parametre iyileştirme protokolü — 9 Eylül 2026

## Dört parametrenin gerçek RF durumu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: yeni temiz AM koşusunda dar aralık SNR'si
13,36–15,32 dB iken sabit aday 10/10 Belirsiz kaldı. Yeni `rf_observation`
ürün dışı ön işlemesi uzun I/Q, FIR kanal süzme ve frekans kayması
hipotezlerini uygular; kesin sınıflandırıcı değildir. Kullanılabilir donanım
son beyana göre yalnız iki HackRF'dir; dBm kalibrasyonu diğer işleri durdurmaz.
Ürün/ARM/RTL ve önceki kabul durumları değişmedi.

Yeni `rf_observation` mevcut v9/F5 baytlarından ayrıdır. Dört RF kaydı
artık geliştirme/tanı kapsamındadır; bunlar yeni yöntemin kör kabulü olarak
kullanılamaz. Henüz sınıf eşiği eğitilmedi veya ürün profili çıkarılmadı.
Ön işlemenin frekans hipotezi, taşıyıcı veya modülasyon doğrulaması değildir.

[Ayrıntılı durum, araştırma ve yeniden üretim](../reviews/PARAMETER_EXTRACTION_ASSESSMENT.md).


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


## v8/v9 bant kapsamı düzeltmesi

Kullanıcı vericinin kapalı olduğunu bildirdi; bu geliştirme kayıtlı I/Q
ve sayısal üreticiyle yürütüldü. v8 eşit kuyruklu OBW99 için her uçta ayrı
%0,5 sınırı ve Hann dördüncü moment varyans şişirmesini ekledi. Bağımsız
uzun kayıt üreticisinde geniş kuyruklu BPSK'nin 24 örneğinden ikisi yanlış
geçerli kaldı. v9 uzak gürültüyü sekiz ayrı bölgenin en düşük medyanıyla
muhafazakâr kestirir; sinyal kuyruğunun gürültü diye çıkarılmasını azaltır.
Bu yaklaşım renkli gürültüde daha fazla ret verebilir; kalibre güven aralığı
veya genel RF doğruluk iddiası değildir.

`validate_candidate_numeric.py` 262144 örnekli temiz referans ile ayrı
16384 örnekli gürültülü gözlemi karşılaştırır. 23000000 köklü geliştirme
koşusundan sonra yöntem değiştirilmeden 24000000 köklü 168 örnek sınandı:
altı desteklenen ailede 96/144 OBW sonucu üretildi ve 96/96 toleransı geçti;
12 dB zaman alanı SNR'li 48 örnekte OBW reddedildi. Tam emisyonu aralığı
aşan dikdörtgen BPSK 24/24 reddedildi. Aynı tohumun SNR varyantları bağımsız
dalga biçimi sayılmaz. Tolerans `max(2×488,28125 Hz, referansın %10'u)`.
Bu sınırlı deney genel OBW kabulü değildir.

800 örneklik eski sınıf kararları değişmedi; eski RF regresyonu AM 16/20,
FM 20/20 Analog. Geniş alıcı bozulma kümesinde OBW verme sayısı aile başına
33–57/100'e düştü; bu maliyet korunur, yalnız geçerli sonuçlar sunularak
başarıya çevrilmez. 28 birim/profil/kayıt testi geçti. Ürün ve ARM yolu
değişmedi. Sıradaki fiziksel kontrol aynı model ve yöntemle farklı frekans/
ton ayarında yapılır; model/eşik bu koşunun sonucuna göre ayarlanmaz.

Yeni `capture_parameter_candidate_rx.py` yalnız iki sonlu 0,5 saniye RX
kaydı alır; TX veya FPGA çalıştırmaz. Model özeti, ham I/Q, ayar, zaman,
kırpılma ve onar pencere sonucu saklanır. Ürün akışı kabulü değildir.

KTR-4.2 / KTR-4.2-F1. Kullanıcının parametre çıkarımını düzeltme talebi,
PÇ-02 sayısal yöntem geliştirmesi ve PÇ-03 sınıflandırma çalışması kapsamındadır.
Mevcut F5 ürün profili, özgün yöntem kilitleri ve geçmiş kanıtlar korunur.
Yeni `refined_candidate` ürün tarafından çağrılmaz; geliştirme adayıdır.

## Yöntem ve veri ayrımı

- Dört ardışık 4096 örnek üzerinde 16384 örnek Hann spektrumu. Taşıyıcı
  yerine önce açıkça çizgi adayı bulunur; FM yan bandının taşıyıcı sayılması
  yasaktır. Uzun gözlem aynı I/Q içindedir; yeni donanım verisi değildir.
- İki taraflı gürültü referansı, kırpılma, düşük SNR ve aralık kenarı retleri.
  %0,5/%99,5 kümülatif kenar tanımı korunur; adayın üç gürültü düzeyli
  bastırması deneysel olduğu için ITU uygunluğu iddiası oluşturmaz.
- Özellikler gözlenen bant desteğine göre filtreleme/örnek azaltma sonrası
  zarf, faz farkı, moment ve korelasyonlardan çıkarılır. Ağaç modeli yalnız
  sayısal geliştirme verisiyle eğitilir. Sklearn geliştirme içindir; açık
  JSON ağacı yürütücüsü kod/pickle yüklemez. Model ürün paketine alınmaz.
- Sınıflar AM/NFM ve OOK/FSK/BPSK/QPSK/QAM; CW ayrı Belirsiz kontrolüdür.
  Sabit 0,9 ağaç oy eşiği kalibre doğruluk yüzdesi değildir. Bilinmeyen
  ailelerin güvenli reddi ayrı zorunlu kapıdır.

v1: 1100000 geliştirme, 2200000 kalibrasyon, 3300000 test kök tohumları.
Aile başına 10000 tohum ofseti kullanılır. Eğitim 120, kalibrasyon 40,
test 60 örnektir. Aynı üretici kullandığından test bağımsız tohum testidir;
bağımsız üretici veya saha genellemesi değildir. AM/NFM testinde 59/60'ar
doğru, birer Belirsiz; beş sayısal ailede 60/60'ar doğru, CW 60/60 Belirsiz.
Gerçek yüksek kazanç AM/FM regresyonunda 40/40 Belirsiz kaldı; v1 kabul edilmedi.

v2: alıcı düşük genliği, bağımsız DC/IQ dengesizliği ve 8 bit nicemleme
simülasyonu eklenir. 4400000/5500000/6600000 ayrık kök tohumları kullanılır;
aile başına 240/60/80 örnek. Model, test üretilmeden önce JSON olarak yazılıp
hash'lenir. Test sonrası eşik değiştirilmez. Başarısız sürüm raporu korunur.
Gerçek AM/FM kayıtları yalnız regresyondur: geliştirme boyunca incelendikleri
için sonraki kör fiziksel kabulün yerine geçemezler.

v2 sonucu: desteklenen ailelerde karar kapsamı %50–81,25; genel kapı
başarısız. Gerçek regresyonda AM 0/20, FM 16/20 Analog; diğerleri Belirsiz.
DC ofseti zayıf çizgi ve güç ölçümünü bozduğu için sayısal kabul de yapılmaz.

v3: nicemleme 8 MS/s'de, ardından 4:1 örnek azaltma; tohum kökleri
7700000/8800000/9900000, adetler 240/60/80. Gerçek regresyon AM 0/20,
FM 20/20 Analog; ürün kabulü yok.

v4: sabit alıcı DC'si örnek ortalamasıyla çıkarılır; LO merkezindeki baskın
çizgi belirsizdir. 12100000/13200000/14300000, adetler 240/60/80.
Testte modülasyonlu ailelerin doğru karar kapsamı %85–97,5, yanlış kesin
karar sıfır; CW 80/80 Belirsiz. 60 gürültü/chirp/iki-ton kontrolü Belirsiz;
JSON yürütücüsü test kararlarıyla eşleşti. Bu yalnız sınırlı sentetik sınıf
kapısıdır; tüm kapsam dışı ailelerin reddi değildir. Gerçek AM 1/20, FM
20/20 Analog. CW/AM geçerli çizgi hatasının %95 yüzdeliği yaklaşık 2 Hz;
bu kalibre fiziksel frekans değil sayısal üreteç karşılaştırmasıdır.

v5: AM %100 derinlik sınırı geliştirme örneklerinin dörtte birinde açıkça
temsil edildi. 15400000/16500000/17600000 kökleri, adetler 480/80/100.
Gerçek regresyonda AM 10/20, FM 20/20 Analog. v6 çizgiye göre özellik
merkezlemesi ve koherent ortalama özelliği ekler; kökler
18700000/19800000/20900000, adetler 480/80/100. İki sürümün testleri
birleştirilerek örnek sayısı veya başarı oranı artırılmaz.

Önceki sürümlerin kaynakları, model JSON'ları ve raporları ayrı dizinlerde
saklanır. Başarısızlıklar yeni yöntem kabulüne çevrilmez. Geliştirme
üreticisi aynıdır; bağımsız tohum ve alıcı bozulma dağılımı tek başına
bağımsız algoritma/üretici doğrulaması anlamına gelmez.

v6 sonucu: 800 test örneğinde AM 86/100, NFM 89/100, OOK 89/100,
FSK 82/100, BPSK 89/100, QPSK 85/100, QAM 93/100 doğru kesin karar;
kalan modülasyonlu örnekler Belirsiz, yanlış kesin karar sıfır. CW
100/100 Belirsiz. JSON yürütücüsü eğitim kitaplığıyla aynı test kararlarını
verdi; 60 sınırlı negatif kontrolün tamamı Belirsiz. Gerçek eski kayıt
regresyonu AM 16/20, FM 20/20 Analog; dört AM Belirsiz. Önceden incelenen
iki fiziksel kayıt/aile genel kabul paydası değildir.

Bağımsız mevcut 30 örneklik başlangıç üreticisinde AM/NFM 12/12 Analog,
FSK 6/6 Sayısal; CW 6/6 Belirsiz. BPSK'nin uzun kuyrukları seçilen
aralığa sığmadığı halde aday OBW ürettiği için sayısal bant kapısı başarısızdır.
CW/AM/NFM bu kümedeki bant farkları yaklaşık +337/+195/−174 Hz düzeyine
inse de bu iyileşme BPSK başarısızlığını kapatmaz.

v7 model eğitmez; v6 modelini aynı baytlarla kullanır. Aralık dışındaki
toplam enerjiye gürültü belirsizliği ekleyerek %1 sınırı aşılırsa yalnız
`obw99_hz` alanını boş bırakır; `bandwidth_reason` nedenini taşır. Diğer
alanlar bağımsız kalır. Bu muhafazakâr denetim dışarıdaki enerjinin aynı
yayıcıya ait olduğunu iddia etmez. Başlangıç BPSK kümesinde 5/6 ret,
1/6 kaçan kapsam sonucu kaldı: bant kabulü hâlâ başarısızdır. Aralık
kanıtı yetersizken ürüne geçiş yapılmaz. Daha uzun gözlem ve ayrı temiz
emisyon referansı ile tam kuyruk belirsizliği giderilmelidir.

26 temel/regresyon testi, alan bağımsız dış-emisyon kontrolü eklendikten
sonra 27/27 geçti. Bunlar algoritma doğruluğunun tüm kapsamını kanıtlamaz.

## Ürüne geçiş kapıları

1. Desteklenen her ailede en az %80 karar kapsamı ve verilen kararlarda
   en az %90 doğruluk; Belirsiz ve yanlışlar tüm paydalarıyla saklanır.
2. Gürültü, CW, chirp, çoklu yayın, aralık dışı, sıra kesintisi ve kırpılma
   olumsuz kontrolleri. Dijital periyodik dizinin analogla aynı I/Q'yu
   oluşturabildiği durumlar genel kesin sınıflandırma iddiasını engeller.
3. Taşıyıcı uygulanabilirliği ile çizgi adayını ayır; CW/AM frekans hatası,
   bant sınırlı sayısal OBW ve temiz I/Q güç referansı ayrı ölçülür. Önceki
   yol haritası hata hedefleri korunur; yalnız geçerli sonuçlar seçilmez.
4. Yeni yöntem/profil/kayıt sürümü ve kaynak hash bağı, canlı olay sahipliği,
   iptal, eski kayıt tekrar üretimi, paket kontrolü. Eski F5 hashleri güncellenmez.
5. Python/host C/ARM eşdeğerliği, süre ve bellek; çalışan hizmet/imaj kimliği
   ile fiziksel ürün kabulü. Bu aday için RTL/ARM uygulaması henüz yoktur.
6. Yeni kör RF örnekleri ve referans cihazla kalibrasyon. dBm kalibrasyon
   olmadan açılmaz. Tüm kapılar geçmeden parametre çıkarımı tamamlandı denmez.

Kaynaklar: [ITU-R SM.443-4](https://www.itu.int/rec/R-REC-SM.443-4-200702-I/en),
[moment tabanlı sınıflandırma araştırması](https://pubs.gnuradio.org/index.php/grcon/article/download/7/6/).
Bu kaynaklar seçilen adayın performansını kanıtlamaz.
