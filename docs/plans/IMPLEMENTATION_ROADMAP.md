# Uygulama Yol Haritası

## Yalnız ED kapsamına geçiş — 13 Eylül 2026

Kullanıcı kararıyla ET arayüzü, görev/TX kaynakları, yapılandırması,
doğrulayıcıları ve özel testleri kaldırıldı. PHASE-10–12 etkin geliştirme
planından çıkarıldı; PHASE-13 yalnız ED bütünleştirme ve demo kapsamındadır.
KTR-5.1–5.4 kimlikleri izlenebilirlik için korunur fakat uygulanmıyor ve ürün
kapsamı dışındadır. Tarihli eski ET kayıtları güncel yetenek değildir. Açık ED
kabul kapıları ve kullanıcı onayı olmadan sonraki faza geçmeme kuralı korunur.

## PHASE-08 / KTR-4.1–4.3 paralel alım ve otomatik kayıt bakımı — 13 Eylül 2026

Kullanıcı mevcut açık kabul işleri içinde iki HackRF'nin seri numarasına bağlı
alıcı rolleri, tespit sürerken otomatik parametre çıkarımı, dBFS sıralı kalıcı
kayıt ve fail-closed kalibrasyon kapısını onayladı. `ED_RX_PRIMARY` güncel canlı
tespit yolunun sahibidir; `ED_RX_SECONDARY` ayrı seriyle tanınır fakat eşzamanlı
ikinci fiziksel akış henüz uygulanmış/doğrulanmış gösterilmez.

PC↔kart P0IQ v2 sözleşmesi, yalnız 4096 örneklik ve en çok 512 hücrelik canlı
parametre isteği için 80 baytlık CRC korumalı başlıkla genişletildi. Ayrı P0CQ
yetenek sorgusu eski kart imajını bozmadan destek denetler. Destek varsa en güçlü
confirmed olaydan başlayarak tek ARM bağlamında dört ardışık kare işlenir; tespit
her karede devam eder. Geniş, FFT kenarındaki veya komşu referanslı olay sayı
uydurulmadan ret nedeniyle kaydedilir.

Sonuçlar sınırlı SQLite kataloğunda saklanır, geçerli dBFS'e göre sıralanır ve
CSV çıkarılabilir. dBm yalnız seri, örnekleme hızı, kazançlar, genlik ölçeği,
frekans aralığı ve geçerlilik süresi tam eşleşen ölçülmüş profil varsa üretilir;
başlangıç kalibrasyon dosyası bilinçli olarak boştur. C taşıma ve Linux köprü
loopback testleri geçti. Güncel fiziksel tanıda yalnız birincil HackRF görünür,
kalıcı kart köprüsü ise yeni canlı parametre yeteneğini bildirmedi; bu nedenle
gerçek iki HackRF ve güncellenmiş kart imajı kabul kapıları açıktır. 820 MHz
kazanç tanısı da kalıcı confirmed olay üretmedi ve 8.192 karelik koşu nominal
gerçek-zaman hızının biraz altında kaldı; ikisi de başarıya çevrilmedi. Sonraki
faz açılmamıştır.

## PHASE-09 saat yönünde bağıl ölçüm arayüzü — 13 Eylül 2026

Kullanıcının mevcut PHASE-09 içindeki açık yönlendirmesiyle ürün akışı tek
ölçüm düğmesine indirildi. İlk başarılı ölçüm operatörün fiziksel olarak
belirlediği `0°` yönüdür; sonraki başarılı ölçümler saat yönünde 15° artarak
`345°` değerine kadar ilerler. Serbest açı, kuzey ve coğrafi kerteriz alanları
ürün ekranından kaldırıldı; sonuç yalnız bağıl tepe yönüdür. Zaman veya dönüş
hızından açı çıkarılmaz ve başarısız/iptal edilmiş ölçüm adımı ilerletmez.

Bu bakım mevcut 24 açı, 3 dB tepe/ön-arka ve ARM karar profilini değiştirmez.
Enkoder/IMU tabanlı sürekli dönüş ayrı bir donanım ve kabul işidir. Fiziksel
HackRF/yönlü anten derece RMS kapısı açık kalır; sonraki faza geçiş onayı
oluşturulmaz.

## PHASE-08 / KTR-4.2 parametre sonuç görünürlüğü — 13 Eylül 2026

Mevcut faz içinde parametre alanı durumları ve kart kalite tanıları sonuç
ekranına bağlandı. Yeni sonuç teknik doğrulamayı otomatik açar; kullanıcı
değerleri, geçerlilikleri ve Türkçe ret nedenlerini kayıt paketini açmadan
görür. 94 ilgili regresyon geçti. Bu yalnız ürün görünürlüğü düzeltmesidir;
parametre fiziksel doğruluk kabulünü kapatmaz ve sonraki faza geçiş onayı
oluşturmaz.

## PHASE-08 / KTR-4.3 820 MHz sınırlı canlı ürün koşusu — 13 Eylül 2026

Kullanıcının mevcut faz içinde istediği canlı tespit → parametre → dinleme
deneyi, kontrollü laboratuvarda bildirilen `820 MHz` NFM ton yayınıyla yapıldı.
İki P0PM-v2 parametre tekrarı geçerli merkez/OBW/güç sonuçları verdi. Dinleme
zinciri `5,001 s` gerçek canlı I/Q'dan `5,000 s` NFM ses üretti; baskın bileşen
`1,02301 kHz` oldu ve oynat/durdur geçti.

Dinleme tamponunu sıfırlayan yaşam döngüsü/eski olay belirsizliği düzeltildi;
seçili kanal olay kimliğinden ayrıldı ve operatörün dinleme alanları canlı
yenilemede korunuyor. Dosya kaynağı sınırı ve Canvas yazı tipi uyarısı da
düzeltildi. İlgili 182 test geçti. Kanıt
`results/evidence/phase08/live-820mhz-e2e-product-20260913.json` içindedir.
Bu yalnız önceden bildirilen tek açık koşudur; eşleştirilmiş kapalı/yanlış kanal,
kör tekrar, gerçek konuşma ve genel Pd/Pfa yapılmadı. PHASE-08/ST-06 ve tam
KTR-4.3 kabulü açık kalır; sonraki faza geçiş onayı oluşturmaz.

## PÇ-02/PÇ-04 geniş aralık düzeltmesi — 12 Eylül 2026

Kullanıcı sayısal parametrelerin FPGA/ARM'da kalmasını ve kart desteğinin
geliştirilmesini açıkça onayladı. P0PM-v2 8–3984 hücre desteği, tam aday
taslağı ve ret nedenleri uygulandı; host F5 profili değiştirilmedi. Portable
49 eşdeğerlik kontrolü geçti; hizmet/ağ köprüsü ARM için derlenip kimliği seri
konsolla doğrulanan karta yüklendi. Altı dar regresyon ve bir değişmemiş gerçek
kayıtlı geniş P0PM-v2 kart ölçümü geçti. Tek kayıt genel geniş bant veya RF
doğruluk kabulü değildir. Bu düzeltme sonraki faza geçiş onayı oluşturmaz.

## PÇ-03 otomatik PC sınıflandırma bağlantısı — 12 Eylül 2026

Kullanıcı analog/sayısal ayrımını FPGA/ARM yerine kolay çalışan otomatik PC
işlevi olarak `Parametreleri Çıkar` akışına bağlamayı açıkça istedi. Mevcut dört
karelik ürün girdisi, operatör analiz aralığı ve kart SNR kapısı kullanılarak
`digital_analog_detection` modeli sınırlı işçiye alındı. `%90` güven altında
`Belirsiz` verilir; sonuç ve yöntem bağı ölçüm arşivinde yeniden üretilebilir.
Bu geliştirme PÇ-03 ürün bağlantısını açar, fakat bağımsız canlı RF doğruluk
kabulünü kapatmaz ve sonraki faza geçiş onayı oluşturmaz.

## PHASE-09 kanal ölçümü düzeltmesi — 12 Eylül 2026

Kullanıcının onayıyla yön bulma ölçüm akışı tek kanal seçimi ve açı başına
istekten sonra yeni dört kare toplama biçimine geçirildi. Beş saniye sınırı,
iptal ve açıklamalı retler eklendi. Olay numarası değişikliği kanal seçimini
düşürmez; tek aday ve alıcı bağlamı koşulları korunur. Yeni faz açılmadı;
fiziksel RF/RMS kabulü açıktır.
[Ayrıntı ve doğrulama](../interfaces/SIGNAL_DIRECTION_FINDING_STATUS.md).

## 5.1.4 genlik tabanlı yön bulma başlangıcı — 11 Eylül 2026

Kullanıcı KTR §5.1.4 için genlik tabanlı yöntemi seçerek PHASE-09 çalışmasını
açıkça başlattı. KrakenSDR'nin faz uyumlu beş kanallı MUSIC/Root-MUSIC mimarisi
tek HackRF ve elle döndürülen yönlü antene taşınmadı; hedef kanal seçimi, kalite
kapısı, kaynak/ayar kaydı ve kerteriz sunumu ilkeleri incelendi.

Ürün yön ölçümü geniş bant FFT ortalamasından seçili confirmed hedefin dört
ardışık gerçek karesini PL Hann → 4096 FFT → güç ve ARM kanal ölçüm yolunda
birleştiren akışa geçirildi. Alan profili 15° adımlı 24 açılı tam tur,
3 dB tepe belirginliği, 3 dB ön/arka ayrımı, sabit hedef/alıcı bağı ve aynı
karenin yeniden kullanılmaması kapılarını uygular. Ham maksimum ölçülmüş açı
olarak korunur. 360 bağımsız sayısal doğrultuda 15° ızgara RMS değeri
4,377975° olmuş; bu fiziksel saha doğruluğu değildir.

Portable C/ARM eşdeğerliği sıfır farkla, CRC korumalı kart hizmet/ağ bağı ise
gerçek ZedBoard üzerinde yedi sayısal sahneyle geçti. PetaLinux 5.679/5.679
görevle derlendi; kalıcı SD imajı yazıldı ve yeniden başlatılan 47007 hizmetinde
aynı yedi durum geçti. Saha öncesi PHASE-09 yazılım/imaj işi tamamlandı. Sıradaki
PHASE-09 işi uygun yönlü anten ve HackRF ile bilinen yönlü fiziksel RMS kabulüdür.
Güncel durum
[`SIGNAL_DIRECTION_FINDING_STATUS.md`](../interfaces/SIGNAL_DIRECTION_FINDING_STATUS.md),
araştırma ve deney planı
[`AMPLITUDE_DIRECTION_FINDING_RESEARCH_20260911.md`](../reviews/AMPLITUDE_DIRECTION_FINDING_RESEARCH_20260911.md)
içindedir. Açık 5.1.3 ve önceki RF kabul kapıları kapanmış sayılmaz.

## 5.1.3 sinyal izleme/dinleme devamı — 11 Eylül 2026

Kullanıcı zorunlu analog ve isteğe bağlı sayısal amatör telsiz kapsamındaki
5.1.3 çalışmasını açıkça başlattı. Bu iş depodaki KTR-4.3 / PHASE-05
yeteneğinin canlı ürün devamıdır. Parametre ölçümünden dinlemeye merkez/OBW
aktarımı, yeni oturumda FPGA ile yeniden doğrulama ve 250 ms güç/frekans
izleme uygulanmıştır. Beş saniyelik kapı olayın ARM'da confirmed kalmasını,
en az %95 kare gözlemini ve en çok 8 kare ardışık boşluğu ister. Sentetik kayma
ile blok değişmezlik kapısı geçmiştir. Korunmuş fiziksel HackRF NFM tekrarında
1.700 Hz sentetik ton 1.699,951 Hz olarak çıkarılmıştır; bu gerçek konuşma veya
canlı ürün kabulü değildir.
Gerçek HackRF + analog telsiz sesi, telsiz profilinin de-emphasis ayarı ve
fiziksel ürün akışı açık kabul kapılarıdır. Sayısal protokol isteğe bağlıdır ve
analog kabul kapanmadan varsayılmayacaktır.
[Güncel durum ve kabul planı](../interfaces/SIGNAL_MONITORING_LISTENING_STATUS.md).

## Sayısal parametrelerin karta taşınması — 11 Eylül 2026

Kullanıcı taşıyıcı frekansı, bant genişliği ve güç için PÇ-02 sayısal çalışması
ile PÇ-04 kart entegrasyonunu açıkça istedi; analog/sayısal ayrımı sonraya
bıraktı. Bu kapsam PÇ-03 kabulünü gerektirmeden sayısal ARM taşımasına izin
verir. ST-06 RF kabulü ve sınıflandırma kabulü açık kalır. Aşağıdaki eski
"yeni faz açılmaz" kayıtları kendi tarihlerinin kapsamını anlatır.

Öncelik: F5 sayısal referansıyla taşıyıcı dahil C eşdeğerliği, gerçek PL güç
girdisinin korunması, sürümlü kart sonucu ve ürün arayüzü bağlantısıdır.
dBm yalnız ölçülmüş, alıcı bağlamı eşleşen kalibrasyonla geçerli olur.
Kaynak değişikliği önceki ikiliye ait fiziksel kabulü devralmaz.

ST-06 kapsamında kullanıcının gerçek FPGA/ARM ayarlanabilirliği talebinin
CFAR ve FFT bölümü tamamlandı. Geçici kart imajında normal/zayıf CFAR ile
4096/8192/16384 FPGA FFT seçimi, etkin değer geri okuması ve üç tekrarlı
sayısal gerçek zaman kapısı geçti. Pencere türü Hann olarak sabittir; kalıcı
SD imajı, HackRF RF doğruluğu ve soğuk açılış tamamlanmadı; yeni faz açılmaz.
[Devam kapsamı](../interfaces/DETECTION_RUNTIME_CONFIG_CONTRACT.md).

Dinamik 4096/8192/16384 XFFT için çerçeve sözleşmesi, uzunluğa bağlı Hann ROM'u,
FFT/güç/CFAR, DMA, ARM/ağ, arayüz geri okuma, tam Vivado yerleştirme ve kart
sayısal testleri tamamlandı. Sıradaki ST-06 işleri güncel imajla HackRF+GUI
dayanıklılığı, kontrollü RF Pd/Pfa ve kalıcı imaj soğuk açılışıdır. Pencere türü
seçimi ancak ayrı RTL katsayıları, referans eşdeğerliği ve CFAR kalibrasyonuyla
ele alınır.

## ST-06 saha öncesi bakım — 10 Eylül 2026

Kullanıcının sinyal tespiti ayarları ve entegrasyon düzeltmesi isteğiyle,
görüntü/tarama kontrolleri ve DMA v2 → ARM 24/32 zayıf yol bağlantısı eklendi.
Çalışma mevcut ST-06 kapsamındadır. RTL/ref eşitliği ve yazılım regresyonlarına
ek olarak yeni imaj/hizmetin fiziksel sayısal kontrolü ve tekrarlı hızı geçti.
RF ve soğuk açılış kapıları açıktır.
[Ayrıntı ve kaynaklar](../interfaces/DETECTION_TUNING_AND_SOURCE_GUIDE.md).

## PÇ-01 arayüz akışı bakımı — 10 Eylül 2026

Bant taramasından Parametre görünümüne seçim aktarımı PÇ-01 kapsamında
tamamlandı. Geçmiş tarama frekansı sabit alımda yeniden doğrulanmadan ölçüm
seçimi yapılmaz; dört güncel kare hazır olduğunda görünüm otomatik açılır.
Bu bakım PÇ-02/03 yöntemini, faz sırasını veya açık fiziksel kabul kapılarını
değiştirmez.

## Dört parametrenin gerçek RF durumu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: yeni temiz AM koşusunda dar aralık SNR'si
13,36–15,32 dB iken sabit aday 10/10 Belirsiz kaldı. Yeni `rf_observation`
ürün dışı ön işlemesi uzun I/Q, FIR kanal süzme ve frekans kayması
hipotezlerini uygular; kesin sınıflandırıcı değildir. Kullanılabilir donanım
son beyana göre yalnız iki HackRF'dir; dBm kalibrasyonu diğer işleri durdurmaz.
Ürün/ARM/RTL ve önceki kabul durumları değişmedi.

Mevcut PÇ-02/03 kapsamında, yeni sentetik başarı turu yerine arşivlenmiş
gerçek RF tanısı ve tek temiz AM bağlantı kontrolü yapıldı. Sınıflandırma
modeli/eşiği değiştirilmedi. Ön işlemede alan bağımsızlığı ve frekans kayması
ele alındı; dört parametrenin ortak kabulü ve PÇ-04 ARM taşıması tamamlanmadı.
BPSK'de yeni pencere yayınla eşleşmedi; aynı süre baskılı akış tekrarlanmaz.

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


## PHASE-10 Tekli Görev geçişi — 8 Eylül 2026

Kullanıcı PÇ-02 ve PHASE-09 çalışmalarını beklemeye alıp ET çalışmasına geçişi
açıkça onayladı. Bu kullanıcı onaylı öncelik istisnasıyla PHASE-10 yalnız KTR-5.1
Tekli Görev kapsamında açıldı; açık ED maddeleri tamamlanmış sayılmaz. Tek hedef
bant için deterministik bant sınırlı CI8, iletimsiz spektrum/OBW doğrulaması,
Türkçe operatör akışı ve fail-closed HackRF süreç sınırı uygulanmıştır.

Depodaki ET_TX güvenlik profili kapalı, seri kimliği ve izin listesi boştur.
HackRF bağlı olmadığı ve kablolu/zayıflatıcılı veya RF ekranlı düzen ölçülmediği
için fiziksel TX çalıştırılmamış, PHASE-10 çıkış kapısı kapanmamış ve PHASE-11
başlatılmamıştır. Sözleşme `docs/interfaces/ET_SINGLE_TASK_CONTRACT.md`, karar
ADR-0041 ve yazılım kanıtı `results/evidence/phase10/single-et-software-v1.json`
içindedir.

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


## Dört parametre bağımsız tanılama — 7 Eylül 2026

KTR-4.2 / KTR-4.2-F1 kapsamında PÇ-02 sayısal başlangıç çalıştırıldı:
`scripts/validate_parameter_bench.py` ile beş ailede 30 bağımsız sentetik
I/Q kaydı üretildi; ürün F5 ölçümü ve 30/30 yeniden hesaplama eşleşti.
Bu doğruluk kabulü değildir: 24 modülasyonlu örneğin tamamında sınıf Belirsiz;
CW taşıyıcı alanı 1/6 sonuç verdi. Geniş kuyruklu BPSK tam emisyonu ölçüm
aralığını aşıyor. Güç hatası bu sentetik örneklerde en çok 0,189 dB;
dBm kalibrasyonu ve canlı ölçüm sürekliliği açık. İlgili 82 yazılım testi geçti.
Yöntem/eşik/RTL değişmedi; eski kanıtlar korunur. Ayrıntılı referans, paydalar,
sınırlamalar ve fiziksel deney düzeni `docs/plans/PARAMETER_VALIDATION_BENCH.md`
içindedir. Yerel rapor: `build/acceptance/parameter-bench-20260907-v1/report.json`.

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

Son doğrulama: 135 kontrolün 134'ü geçti. Tek başarısızlık değiştirilmemiş
`Main.qml` dosyasının mevcut 2.255 satırıyla 2.200 satır mimari sınırını
aşmasıdır; HEAD ve güncel metin aynıdır, sınır gevşetilmedi. PÇ-00 paket,
kayıt/yeniden üretim, olumsuz giriş ve canlı/SigMF ürün bağları geçti.
Paket genel test sonucu bu açık bulgu nedeniyle başarısız olarak saklandı.
PÇ-00 işlevleri uygulanmıştır; bu kayıt bütünlüğü başarısı sayısal/RF
doğruluğa dönüştürülmez. Sonraki çalışma PÇ-01'dir.

Kullanıcının uygulamaya devam talimatıyla KTR-4.2 / KTR-4.2-F1 için mevcut
F5 ölçümüne kaynak ve I/Q bağlı kayıt eklendi. Canlı ve SigMF ürün ölçümü,
dört normalize I/Q karesini ve alanların birim/yöntem/durum/neden bilgilerini
ayrı ZIP'e kaydeder; kayıt başarısızsa yeni sonuç yayımlamaz. Canlı karelerde
merkez, örnekleme, sıra ve kart yanıtı bağı ayrıca denetlenir. Profil/model
özetleri, oturum ayarları, kanal seçici ölçeği ve bilinen kaynak özetleri
saklanır. Donanım UTC zamanı, çalışan kart imajı ve kalibrasyon gözlenmemişse
bilinmiyor kalır; dBm veya RF doğruluk sonucu üretilmez.
[Kayıt ve yeniden üretim sözleşmesi](../interfaces/OPERATOR_ASSISTED_PARAMETER_CONTRACT.md) sınırları tanımlar.

F5E paket denetimi mevcut iki ek logoyu açık listesine aldı; eksik model ve
izinsiz ek dosya retleri korunur. Eski F5E/PHASE-08 kanıtları değiştirilmedi.
Parametre satırlarını oluşturma işlevi mevcut ölçüm modülüne taşındı; görünen
alanlar ve algoritma eşikleri değişmedi. Yeni kanıt
`results/evidence/phase08/parameter-record-v1.json` ve ZIP içindedir.
Bu yazılım kayıt/entegrasyon kabulüdür; yeni fiziksel kart veya RF deneyi
değildir. ST-06 ve dört parametrenin saha doğruluğu açıktır. PÇ-01 arayüz
sadeleştirmesi sonraki iştir; tercihli özellikler ve PHASE-09 açılmadı.

## Dört zorunlu parametre için kontrollü devam planı — 7 Eylül 2026

Kullanıcı, sinyal tespiti kabulü henüz açıkken parametre çıkarımına sınırlı
geçişi ve önce dört zorunlu alanın planlanmasını açıkça istedi. Bu yönlendirme,
aşağıdaki tarihli kayıtlardaki yalnız tespitle sınırlı çalışma talimatını bu
kapsamda günceller. PHASE-08 / ST-06 tamamlanmış sayılmaz. Çalışma mevcut
PHASE-04-F5 yeteneğinin PHASE-08 canlı entegrasyonuna devamdır; PHASE-09 açılmaz.
Modülasyon/protokol/çoklama/EKKT ve diğer tercihli özellikler sonraki kapsamdır.
Bu oturum envanter, başlangıç doğrulaması ve planlamadır; aşağıdaki uygulama
işlerinin tamamlandığı veya karta yeni yazılım yüklendiği anlamına gelmez.

### Gereksinim ve mevcut durum

Kullanıcının paylaştığı yarışma metni §5.1.2, depodaki kalıcı `KTR-4.2` ve
`KTR-4.2-F1` kimliklerine bağlanır. Eski kimlikler korunur. Paylaşılan kesitte
sayısal hata toleransı, güç birimi ve taşıyıcısız yayın için değerlendirme
yöntemi belirtilmediğinden aşağıdaki hedefler yarışmanın resmî eşikleri değildir.

| Zorunlu alan | Mevcut kaynakta olan | Açık iş |
|---|---|---|
| Taşıyıcı frekansı | F5 bilgisayar yöntemi dar çizgi kanıtıyla ayrı taşıyıcı alanı üretir; ARM yalnız emisyon merkezini hesaplar. | Çizgi olmayan/bastırılmış taşıyıcılı yayında merkezin taşıyıcı diye sunulmaması; desteklenen ailelerde taşıyıcı kestirimi, frekans kalibrasyonu ve ARM taşıması. |
| Bant genişliği | F5 ve ARM C çekirdeğinde alt/üst kenar ve OBW99 kestirimi vardır. Tespitin kaba aralığı ayrı kavramdır. | Güncel 2 MS/s canlı yolda fiziksel bant doğruluğu, komşu sinyal/kenar etkisi, gözlem süresi ve daha geniş ölçüm kapsamı. |
| Güç seviyesi | F5 ve ARM onaylı aralıkta gürültü çıkarılmış kanal gücünü dBFS olarak hesaplar. | Kazanç, sayısal ölçek ve filtre etkisinin izlenmesi; RF girişine göre dBm kalibrasyonu ve hata bütçesi. |
| Analog/Sayısal ayrımı | F5 bilgisayar yöntemi zaman/istatistik özellikleri ve aile prototipleriyle Analog/Sayısal/Belirsiz sonucu üretir. | Bağımsız gerçek yayınlarla doğrulama, kapsam dışı ve kararsız örneklerde karar vermeme; ardından aynı yöntemin ARM C uygulaması. |

Kaynaklar: `app/operator_console/quick_measurement_actions.py`,
`quick_view_model.py` içindeki `_f5_parameter_rows`,
`algorithms/parameters/f5_estimator.py`, `f4_estimator.py`, `f4_domain.py`,
`platforms/embedded/p0/src/p0_parameter_runtime.c` ve `p0_ed_service.c`.
`algorithms/p0/parameters.py` içindeki ayrı P0 referansı güncel QML F5 yolu
değildir; onun %98 geri dönüş bant yöntemi F5 OBW99 yerine geçirilmez.

### Gerçek veri yolu ve hedef görev paylaşımı

Bugün canlı QML ölçümü, karta gönderilmiş ve aynı olay için kart yanıtı
doğrulanmış dört I/Q karesini bilgisayarda sabitler. Alımı durdurur; bilgisayar
bu I/Q'dan spektrumu yeniden hesaplayıp F5 ölçümünü ayrı iş parçacığında yapar.
Bu, parametrelerin PL'de hesaplandığı anlamına gelmez. Kart hizmetinde parametre
isteği desteği vardır; mevcut QML ölçüm eylemi bu desteği kullanmaz.

Hedef görev paylaşımı:

| Bileşen | Görev |
|---|---|
| FPGA / PL | Mevcut Hann → 4096 FFT → UQ28.30 güç → OS-CFAR zinciri; sayısal ölçüme spektral güç sağlar. İlk uygulama adımı yeni RTL gerektirmez. |
| Kartın ARM / PS işlemcisi | Onaylı olaya bağlı merkez/taşıyıcı, OBW99, kanal gücü ve Analog/Sayısal kararı; zaman alanı için karta ulaşan I/Q kullanılır. Mevcut sayısal C çekirdeği temel alınır. |
| Bilgisayar | HackRF USB alımı, kanal seçimi, taşıma, operatör arayüzü, kayıt ve kalibrasyon profilinin yönetimi. Python F5, geçiş süresince ölçüm yolu ve sonrasında bağımsız karşılaştırma referansıdır. |

ARM, ZedBoard üzerindeki işlemcidir. Mevcut CPU0 DMA/güç çözme ve CPU1 tespit
iş paylaşımı iki çekirdeği zaten kullanır. Yeni ölçümün boş bir çekirdekte
ücretsiz çalışacağı varsayılmaz. Önce tek seçili sinyal için sınırlı ölçüm işi
uygulanır; eşzamanlı sürekli tespit ancak ölçülen gecikme/kuyruk bütçesiyle açılır.
PL'ye yeni hızlandırıcı taşıması ancak ARM profili gerekli olduğunu gösterirse
ayrı RTL, bit-tam referans, benzetim ve fiziksel zamanlama kabulüyle ele alınır.

### Uygulama sırası ve kabul kapıları

| Sıra | Yapılacak iş | Çıkış kapısı |
|---|---|---|
| PÇ-00 | Güncel ölçüm profilini ve paket doğrulamasını eşleştir; ölçüm sözleşmesine birim, yöntem, alan durumu, olay/oturum, zaman, I/Q ve kaynak hash'i, örnekleme, kazanç/ölçek/kalibrasyon kimliği ekle. | Mevcut F5 profil bütünlüğü korunur; paket kapısı geçer; alanlar ayrı geçerli/belirsiz/ölçülemedi durumuyla kaydedilir. Eski RF kanıtı yeni kaynak kabulü yapılmaz. |
| PÇ-01 | Tarama sonucu → yeniden alım → aynı sinyalin yeniden doğrulanması → önerilen izole aralığın onayı → tek ölçüm akışını sadeleştir; dört zorunlu sonucu öne al. | Eski tarama satırı, kayıp olay veya kazanç değişimi yeni ölçüm gibi kullanılamaz. İptal, hata, tekrar ölçüm ve seçili hedef değişimi sınanır; 1280×720 ve 1920×1080 görünümü doğrulanır. |
| PÇ-02 | Mevcut F5 ile taşıyıcı/merkez, OBW99 ve dBFS doğruluğunu bağımsız bilinen I/Q ve kontrollü RX kayıtlarında ölç; frekans/güç kalibrasyonunu kur. | CW, AM, NFM ve en az bir sayısal aile; farklı frekans/kazanç/SNR; komşu sinyal, kırpılma, aralık kenarı ve yalnız gürültü kontrolleri. dBm yalnız kalibrasyon geçerlilik alanında açılır. |
| PÇ-03 | Analog/Sayısal yöntemini AM/NFM ile OOK/FSK/PSK/QAM gibi bağımsız aile/ayar örneklerinde değerlendir; gerekli geliştirmeyi ayrı veriyle yap. | Aile bazlı karışıklık matrisi, doğru karar oranı, karar verilebilen örnek oranı ve Belirsiz oranı birlikte raporlanır. Test örnekleriyle eşik ayarlanmaz; CW otomatik Analog sayılmaz. |
| PÇ-04 | Karttaki sayısal ölçüm isteğini ürün akışına bağla; eksik taşıyıcı ve sınıflandırma yöntemlerini ARM'a taşı. | Aynı I/Q ve gerçek PL güç kareleriyle Python ↔ host C ↔ ARM karşılaştırması; sayısal toleranslar önceden sabit; alan durum/nedenleri ve sınıflar eşleşir. Süre, ek bellek, sıra/kuyruk kaybı ve iptal ölçülür. |
| PÇ-05 | Dört alanı birlikte, kaynağı operatöre önceden açıklanmayan kontrollü RX senaryolarında değerlendir. | Başarısız ve Belirsiz denemeler dahil tüm paydalar, kaynak/hizmet/imaj hash'leri, gerçek alıcı ayarları ve referans ölçümler saklanır. Parametre kabulü ve ST-06 kabulü ayrı kararlardır. |

Bu sıra dört zorunlu alanı kapsar. Tercihli modülasyon etiketlerini arayüze
eklemek veya başka yarışma görevine geçmek bu planın çıkışı değildir.

### Ölçüm tanımları ve ilk sınırlar

- Taşıyıcı ile emisyon merkezi ayrı kalır. Taşıyıcı çizgisi gözlenmiyorsa
  `Gözlenmedi` gösterilir; merkez ancak kendi adı ve yöntemiyle verilir.
  Bastırılmış taşıyıcı için yeni kestirim ayrı yöntem/kanıt ister; en güçlü FFT
  hücresinin RF taşıyıcı olduğu varsayılmaz.
- Hedef bant tanımı OBW99'dur. ITU-R SM.443-4 doğrudan yöntemi toplam gücün
  iki yanında %0,5 bırakır. Mevcut F5'in %0,75 kuyruk ve 0,375 hücre kenar
  düzeltmesi kendi deneysel OBW99 kestirimidir; doğrudan standart algoritması
  veya saha uyumluluk belgesi diye adlandırılmaz. Bağımsız referansla hata
  ölçülür. [Birincil kaynak: ITU-R SM.443-4](https://www.itu.int/rec/R-REC-SM.443/en).
- Canlı 2 MS/s ve 4096 FFT için hücre aralığı 488,28125 Hz'dir. Mevcut 8–512
  hücre analiz sınırı yaklaşık 3,906–250 kHz aralık demektir; ölçülen sinyal
  bant genişliğinin doğruluk aralığı değildir. İki tarafta gürültü referansı
  gerekir. 8 MHz önizleme bu ölçüm sınırını genişletmez. 250 kHz üzerindeki
  emisyonlar için ayrı profil/geniş aralık desteği ve yeniden kabul gerekir.
- Dört kare 2 MS/s'de 8,192 ms I/Q süresidir. Bu ilk sınırlı ölçüm penceresi,
  yavaş analog değişimi veya aralıklı sayısal yayını temsil etmeyebilir.
  PÇ-02/03'te örneğin 50/100/250 ms gözlem adayları süre/bellek/doğruluk
  karşılaştırmasına alınır; bunlar henüz uygulanmış süre seçenekleri değildir.
- Güç hedefi alıcının RF girişindeki kanal gücüdür; uzaktaki vericinin çıkış
  gücü değildir. dBFS ön sonuç olarak kalır. dBm dönüşümü referans düzlemi,
  frekans, LNA/VGA/RF kazancı, örnekleme, kanal filtresi ve sayısal ölçeğe bağlı
  kalibrasyon gerektirir. Sadece LNA/VGA değerini dBFS'den çıkarmak yeterli
  kalibrasyon sayılmaz. Ölçüm boyunca kazanç sabitlenir; değişirse birikim
  sıfırlanır. Kalibrasyon dışı ayar, kırpılma veya bilinmeyen ölçek dBm'yi kapatır.
- Analog/Sayısal alanı için güç spektrumu tek başına giriş değildir; mevcut
  yöntem I/Q zaman özelliklerini de kullanır. Aile prototipleri ve bütün
  ön işleme ARM'a birlikte taşınır. Belirsiz sonucu korunur; model uzaklığı
  veya karar marjı kalibre bir doğruluk yüzdesi gibi sunulmaz.

İlk mühendislik hedef önerisi: desteklenen taşıyıcılı örneklerde frekans
hatasının %95 yüzdeliği en fazla bir FFT hücresi, OBW99 hatasının %95 yüzdeliği
en fazla `max(2 hücre, referans bandın %10'u)`; kalibre bölgede güç hatasının
%95 yüzdeliği en fazla 3 dB. Frekans için saat/ppm ve referans cihaz belirsizliği
ayrıca raporlanır; hücre aralığı mutlak doğruluk değildir. Analog/Sayısal için
desteklenen her ailede en az %80 karar kapsamı ve verilen kararlarda en az %90
doğruluk başlangıç hedefidir. Bunlar henüz karşılanmış değildir. Deney öncesi
örnek sayısı, bağımsız tekrar, SNR/ayar matrisi, güven aralığı ve kapsam dışı
yanlış karar sınırı bir kabul protokolünde sabitlenir; sonuca göre değiştirilmez.

### Arayüz kararı

Mevcut spektrum + sağ ölçüm paneli korunabilecek bir temeldir. Bugünkü panel
dokuz satırı aynı ağırlıkta gösterir; ölçüm yokken de aralık denetimleri ve
teknik açıklamalar görünür. Dört zorunlu alanın önceliği yeterince belirgin
değildir. PÇ-01 hedefi:

1. Seçili sinyal ve tek bir sonraki eylem: `Sinyali Seç`, `Aralığı Onayla`,
   ardından `Ölçümü Başlat`. Var olan tarama sonucunu izlemeye alma işlevi
   yeniden kullanılır; güncel ölçüm için yeni olay ve dört gözlem şartı korunur.
2. Ana sonuçlar: `Taşıyıcı frekansı`, `Bant genişliği (%99)`,
   `Güç seviyesi` (dBFS/dBm açık birimle), `Sinyal türü`.
3. `Ayrıntılar`: emisyon merkezi, alt/üst sınır, SNR, ölçüm zamanı/süresi,
   kalibrasyon durumu ve alanın neden ölçülemediği. Teknik kaynak/işlemci
   bilgileri kayıt ve tanıda kalır.
4. Tarama geçmişi güncel alım sayılmaz. Sonuç zamanını koru; yeni oturum,
   kazanç veya hedef değişiminde eski değeri canlıymış gibi taşıma. İlk sürüm
   ölçümün alımı durdurduğunu açıkça söyler. Sürekli ölçüm ayrı kabul ister.

### Bu oturumdaki başlangıç doğrulaması

Üretim kodu değiştirilmeden yapılan inceleme:

- `verify_p0_parameter_runtime.py`: MSVC C11 durum makinesi geçti; AM ve
  geniş bant sahnesinde altı sayısal alan Python ile sıfır fark verdi;
  yalnız gürültüde ret korundu. Kalıcı yük 56.064 bayt. Bu host C testidir,
  yeni fiziksel ARM/RF kabulü değildir; test örnekleme hızı 8 MS/s'dir.
- F5 ürün profili + tarihsel canlı parametre arşivi + güncel QML paketi:
  32 geçti, 1 başarısız. Başarısız kontrol `release-assets`: F5E doğrulayıcısı
  paket listesinin eski altı dosyayla birebir eşitliğini isterken mevcut paket
  iki ek logo (`baz-logo-intro.png`, `baz-logo-glow.png`) taşır. Profil üretimi,
  çalışma zamanı yeteneği, değişmiş profilin reddi ve QML bağı geçti. Başarısız
  kontrol kaldırılmaz; PÇ-00'da güncel paket sözleşmesiyle uyumlu hale getirilir.
- Boş ve kayıtlı tek-ton sonuç durumları 1280×720 / 1920×1080 olarak üretildi.
  İncelenen küçük sonuç ekranında dokuz alan sığıyor fakat yazı yoğunluğu
  fazla. Kayıtlı CW örneğinde `Belirsiz` sınıfı ve 281,48 dB SNR gösterildi;
  bu fiziksel SNR değildir. PÇ-02'de sıfıra yakın gürültü tabanı ve bant
  çözünürlük sınırının sunumu ayrıca denetlenir.
- Yerel çıktılar `build/acceptance/parameter-planning-20260907/` içindedir:
  `arm-host-verification.json`, `f5-integration-baseline.json`, `tests.xml`,
  `ui-inspection.json` ve dört PNG. Bunlar donanım ölçümü değildir. Tarihsel
  `live-parameter-functional.json` kaydındaki `accuracy_proven: false` korunur;
  eski kaynak hash'leri güncel kaynağa taşınmaz. Tarihsel canlı parametre
  kaydındaki dokuz kaynak hash'inin yedisi bugün farklıdır. İnceleme çıktıları
  ve kaynak hash'leri yerel `planning-inspection.json` içinde ayrıca bağlıdır.
- Plan ve bağlantılı durum belgeleri güncellendikten sonra depo sözleşmesi
  20/20 geçti. Değişiklikler belge eklemeleriyle sınırlıdır; eski ölçümler,
  kilitli profiller ve başarısız kanıtlar korunmuştur.
## ET Faraday laboratuvar yetkilendirmesi — 8 Eylül 2026

Kullanıcı, bundan sonraki fiziksel ET-TX çalışmalarının hazır korumaları bulunan
Faraday kabini içinde yapılacağını bildirmiş ve kontrollü `CABLED_LAB` kapsamını
onaylamıştır. Bu modun politika kilidi kaldırılmıştır; genel/açık alan
`HARDWARE_TX_LOCKED` yolu kapalı kalır. Seri bağlı cihaz, doğrulanmış HackRF
araçları, sınırlı süre/kazanç, acil durdurma ve ölçüm kaydı gerçek TX için hâlâ
zorunludur. Ortam kararı sırasında TX arka ucu ve bağlı cihaz yoktu; RF yayını
yapılmamıştır. Birleşik güncel kaynakta sonradan eklenen güvenlik kapılı Tekli
Görev arka ucu vardır ancak depo profili kapalıdır. Karar ADR-0043, bağlayıcı sınırlar
`docs/safety/RF_TEST_BOUNDARIES.md` içindedir.

Bu onay PHASE-10/11 güvenlik hazırlığıdır; PHASE-08'i kapatmaz veya PHASE-09'u
tamamlamaz. Sonraki kullanıcı onayıyla PHASE-10 yalnız Tekli Görev kapsamında
açılmıştır. Fiziksel uygulama ve kabul, cihaz görünür olduğunda ayrıca yürütülür.

## ET yerel sinyal üreteci bakımı — 8 Eylül 2026

Kullanıcının ET sinyal üreteci entegrasyon talebiyle, PortaPack firmware
çalışma zamanı alınmadan bağımsız C++17 `int8` I/Q üreteci ve Python bağı
eklenmiştir. Kapsam yalnız deterministik `OFFLINE/LOOPBACK` tampon üretimidir;
bu bileşen HackRF-2, aygıt erişimi, RF ayarı veya TX çağrısı içermez. Daha sonra
eklenen PHASE-10 Tekli Görev arka ucundan ayrı kalır ve ürün paketine girmez.
Kabul sınırı ve kullanım `docs/interfaces/ET_SIGNAL_GENERATOR_CONTRACT.md`
içinde tutulur.

## Son arayüz düzenlemesi — 7 Eylül 2026

PHASE-08 / ST-06 arayüzünde sabit frekans ve bant taraması alanlarının sayı,
etiket, düğme ve sonuç hizaları birleştirildi. Bağlı durum düğmesi ile yinelenen
tespit metinleri kaldırıldı; bağlantı yokken denetleme, çalışma sırasında
durdurma eylemi görünür. Algoritma, RTL ve eşikler değişmedi. Bu çalışma
parametre çıkarımı fazını açmaz; kullanıcı talimatı beklenir.
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

5 Eylül 2026 ST-06 fiziksel tanı güncellemesi: geçici FPGA/ARM hizmeti/ağ
köprüsü yüklenmiş ve dijital dar/geniş olay yaşam döngüsü gözlenmiştir.
Ürün hızı 286–290 kare/s ile gerekli 488,28125 kare/s kapısını geçememiştir.
ARM ürün yolu alt adım profili ve eşdeğer optimizasyon sıradaki iştir.
SD soğuk açılışı, sürekli RX ve kör RF kapıları açıktır; sonraki faza geçilmez.
Kanıt: `results/evidence/phase08/st06-product-board-diagnostic-v1.json`.

Fazlar sıralıdır; bir fazın çıkış kapısı doğrulanmadan ve kullanıcı onayı alınmadan sonraki faza geçilmez.

31 Ağustos 2026 kullanıcı yönlendirmesiyle mevcut sinyal tespiti ve onun
spektrum/spektrogram arayüzü üzerinde bakım yapılır; sonraki görevler açılmaz.
Görüntüleme düzeltmeleri, bilimsel dayanak incelemesi ve geniş bant sınır tanısı
[güncel durum belgesinde](../interfaces/SIGNAL_DETECTION_STATUS.md) izlenir.
Bu bakımın tamamlanan ilk turu yeni detector katsayısı, RTL/bitstream veya RF TX değişikliği içermemiştir;
kontrollü bilinmeyen yayın kabulü geçmeden aşama tamamlandı sayılmaz.
Kullanıcının sonraki "önce plan" yönlendirmesi için aynı durum belgesindeki
**Sinyal tespiti kapanış planı — uygulama sürüyor** bölümü ST-01–ST-08 işlerini,
arayüz/algoritma/FPGA sınırlarını ve önerilen kabul hedeflerini tanımlar.
Bu, yeni bir fazın açılması veya planlanan algoritmanın uygulanmış olması
anlamına gelmez. Kullanıcının devam yetkisiyle RX/görüntü ayrımı, canlı çizim
darboğazı ve tarama önizlemesi uygulanmıştır; kart oturumu ve genel geniş bant
tespit kabulü açık olduğundan sinyal tespiti aşaması kapatılmamıştır.

| Faz | Ad | Çıkış kapısı |
|---|---|---|
| PHASE-00 | Repository ve mühendislik temeli | Repository sözleşmesi, mimari/karar/güvenlik belgeleri, toolchain envanteri ve PHASE-00 doğrulaması başarıyla tamamlanır. |
| PHASE-01 | SigMF giriş sözleşmesi ve deterministik test verisi | Kanonik `ci8` ve çevrimdışı `ci16_le` sözleşmeleri ile sentetik golden fixture zorunlu doğrulamaları geçer; harici veri kontrolü mevcutsa geçer, yoksa kontrollü atlanır. |
| PHASE-02 | Referans spektrum DSP zinciri | Bounded çerçeveleme, Hann, 4096 FFT, güç/PSD ve üstel ortalama floating-point çıktıları deterministik vektörlerle doğrulanır; aynı gerçek sonuçları gösteren kalıcı Türkçe operatör uygulamasının ilk sürümü iki ekran ölçeğinde geçer. |
| PHASE-03 | Sinyal tespiti | Bölgesel, CA-CFAR ve OS-CFAR adayları sabit sahnelerde karşılaştırılır; bütün zorunlu kapıları geçen kanonik yöntem, allowlist bloklarından kurulan doğrulanmış profille kayıtlı/sentetik I/Q üzerinde kaba aday ve bounded temporal olay üretir. |
| PHASE-04 | Parametre çıkarımı | Operatörce onaylanan izole span içinde taşıyıcı çizgisi, emisyon merkezi, OBW99, kalibre edilmemiş göreli güç ve sınırlı Analog/Sayısal/Belirsiz alanları kendi binding ve OOS kapılarını geçer; yalnız geçen alanlar digest bağlı allowlist profiliyle etkinleşir. R1/R2/D1 ve E1 geçmeyen sonuçları yeniden üretilebilir mühendislik kanıtı olarak korunur; PHASE-04 tüm çekirdek alanlar doğrulanana kadar açık kalır. |
| PHASE-05 | Sinyal izleme ve analog dinleme | Kayıtlı/sentetik I/Q üzerinde operatör seçimli AM/NFM zinciri, bounded 48 kHz mono ses ve WAV çıktısı deterministik golden testlerle doğrulanır. |
| PHASE-06 | FPGA RTL DSP ve Zynq PS aday zinciri | Özel RTL dili SystemVerilog ve blok arayüzü AXI4-Stream olur. PHASE-06A–F giriş, Hann, gerçek AMD FFT, implementation ve exact lineer power zincirini; PHASE-06G PHASE-03 `regional` detectorü; PHASE-06H gruplamayı; PHASE-06I PL→PS packet sınırını; PHASE-06J portable PS temporal confirmation çekirdeğini kurmuştur. Görsel profilin otomatik HDL ürettiği iddia edilmez. |
| PHASE-07 | PC–ZedBoard veri aktarımı | Kayıtlı I/Q verisi PC'den Ethernet, ZedBoard PS, DDR/AXI DMA ve PL yoluyla bütünlük ve hız kanıtıyla aktarılır. |
| PHASE-08 | HackRF-1 canlı I/Q ve ED entegrasyonu | HackRF-1 canlı kaynak bloğu uçtan uca ED zincirine ulaşır ve kontrollü alma senaryolarında beklenen adayları üretir. |
| PHASE-09 | Genlik tabanlı yön bulma ve yaklaşık konum | Manuel açı/göreli güç ölçümlerinden yön ve iki bilinen ölçüm noktasından yaklaşık konum, bilinen hedeflerle hata raporu üretecek şekilde doğrulanır. |
| PHASE-10 | Kapsamdan çıkarıldı | ADR-0044 uyarınca ET simülasyonu, görev kodu ve TX altyapısı geliştirilmez. |
| PHASE-11 | Kapsamdan çıkarıldı | ADR-0044 uyarınca sürekli ve arabakışlı karıştırma geliştirilmez. |
| PHASE-12 | Kapsamdan çıkarıldı | ADR-0044 uyarınca aldatma işlevleri geliştirilmez. |
| PHASE-13 | ED arayüzü, sistem entegrasyonu ve yarışma demosu | Doğrulanmış profil kilidiyle ED görev akışı uçtan uca çalışır; demo provası ve kanıt paketi tamamlanır. |

## Kapsam dışı fazlar

PHASE-10–12 sıralama ve gereksinim geçmişini korumak için tabloda tutulur; etkin
geliştirme fazları değildir. Ürün ET/TX kodu, arayüzü, yapılandırması veya test
akışı içermez. Tarihsel laboratuvar kararları güncel yetenek sağlamaz.

KTR yarışma görevlerinin kaynağı olarak korunur; eski donanımın teknik performans hedefleri bağlayıcı değildir. Referans mimari 2× HackRF One, ZedBoard ve laptoptur.

## Kullanıcı onaylı P0 hızlı kontrol noktası

Yol haritası fazları yeniden sıralanmadan, kullanıcı onayıyla zorunlu yarışma
çekirdeği tek bir `P0 Mandatory EH Core` kontrol noktasında öne alınmıştır. P0;
KTR uyumlu OS-CFAR/parametre/manuel genlik DF host kanıtını, Zynq PS↔AXI
DMA↔Hann/FFT/güç Vivado mimarisini, görev odaklı operatör bağlarını ve yalnız
OFFLINE/LOOPBACK sürekli karıştırma ile analog FM/NFM aldatma taban bantlarını
tamamlar. PHASE-06A–J değiştirilmemiştir; konum, look-through ve GPS L1 P1'e
geçilmeden bekler.

Vivado 2025.2'de 50 MHz P0 tasarımı, 32768-byte S2MM paketi için zorunlu 16-bit
DMA length alanıyla sentez, route, timing, bitstream ve XSA kapılarını geçmiştir.
FPGA kaynak ağacının `algorithms/fpga/` altına taşınmasından sonra eski TCL yolları
düzeltilmiş; aynı kapılar 2026-08-27 tarihinde temiz projeden yeniden geçmiştir.
ZedBoard `avnet-tria:zedboard:part0:1.5` önayarı kanonik Vivado üretimine
bağlanmış; PetaLinux 2025.2 device tree, coherent-buffer DMA/FCLK modülleri,
rootfs ve native boot artifact üretimi tamamlanmıştır. Yeni FSBL, bitstream,
U-Boot ve device tree içeren native `BOOT.BIN` fiziksel kartta DONE, UART, Linux,
`/dev/p0-dma` ve FPGA manager `operating` kapılarını geçmiştir. Soğuk açılışta
DONE ve UART Linux giriş kapısı 3/3 tekrarlanmıştır. FCLK0 doğrudan
50 MHz/reset serbest durumda ve doğrulama hata maskesi sıfır ölçülmüştür. Sıfır
çerçeve ile 4096 örneklik bilinen çerçevenin 32 KiB FPGA çıktısı doğrulanmış;
bilinen çerçeve 10/10 byte-tam eşleşmiş ve iki DMA kesme sayacı 0'dan 11'e
çıkmıştır. FPGA güç çıktısı kart üzerindeki ARMv7 OS-CFAR aracına bağlanmış; bilinen
çerçevede üretilen aday JSON'u host C çıktısıyla byte-tam eşleşmiştir. Ham 147 aday
bu deterministik çerçevenin doğruluk veya confirmed-event sonucu sayılmaz. Önceki
native paketleme açığı kapanmıştır. Üç ayrı byte-tam FPGA güç çerçevesi, PHASE-06I
ABI paket köprüsü üzerinden karttaki PHASE-06J 2/3 çekirdeğinde çalıştırılmış;
ikinci karede doğrulama ve iki boş kare sonunda sonlandırma geçmiş, 81.076 byte
ARM olay çıktısı host C ile byte-tam eşleşmiştir. Yeni araç rootfs içindeki
`/usr/bin/p0-ed-runtime-run` yoluna kurulmuş; SD güncellemesi sonrasındaki soğuk
açılışta aynı DMA ve temporal kabul yeniden geçmiştir. Ethernet taşıma,
throughput, geniş detector vektörleri, parametre ARM bağı, canlı HackRF ve RF TX
açık kalır. Yerel
kart hizmeti ABI v1 kaynakları; root-only DMA sahipliği, açılış sonrası `p0ed`
yetki düşürme, 8224-byte CRC korumalı istek ve bounded 8772-byte yanıtla host C11
kapılarını geçmiştir. PetaLinux 2025.2 hedefinde 5679/5679 görev, paket QA, rootfs,
ARM EABI5 servis/istemci ve SysV runlevel bağları geçmiş; yeni `image.ub` üretilmiştir.
Bu imajla fiziksel kartta otomatik hizmet başlangıcı, `root:root 0600` DMA sınırı,
ek grubu olmayan `p0ed` süreci ve `p0ed:petalinux 0660` soketi doğrulanmıştır.
DMA aygıtına doğrudan erişemeyen `petalinux` kullanıcısı beş karelik fiziksel
FPGA→OS-CFAR→2/3 dizisini çalıştırmış; DMA tamamlanma bayrakları ve bütün olay
alanları host referansıyla eşleşmiştir. Hizmetin SysV yeniden başlatma ve yeniden
istek kabulü de geçmiştir. Bu kontrol noktası sonraki faz için otomatik
kullanıcı onayı oluşturmaz.

### P0 ED geniş bant düzeltmesi

Kullanıcının 2026-08-28 onayıyla, yeni bir yol haritası fazı açılmadan mevcut P0
ED kapanışındaki geniş bant olay sahipliği düzeltilmektedir. ADR-0028 sonuçlardan
önce yöntemi ve kapıları kilitlemiştir: OS-CFAR yerel tespit sahibi olarak kalır;
32-bin bütünleşik enerji desteği aşındırıldıktan sonra yalnız tam 41-bin OS
penceresinden geniş destekler kurtarma adayı olur. Host referansı 256/256 geniş
bant kareyi, 128/128 dört-kare tek olay dizisini,
7.168 gürültü ve 4.992 yerel sinyal karesinde sıfır ek geniş aday kapısını ve
64/64 Python/C aday eşdeğerliğini geçmiştir. İlk tek-bin bölgesel imaj fiziksel
geniş bant kapısında olay üretememiş ve bu başarısızlık ADR-0028'e kaydedilmiştir.
Bütünleşik enerji sürümü PetaLinux'ta 5.679/5.679 görevle derlenmiş ve fiziksel
PL→DMA→ARM yolunda kabul edilmiştir. 10/10 geniş bant karesi kurtarma adayı
üretmiş; tek olay kare 1–9 boyunca doğrulanmış ve gözlenmiş, en kötü coverage ve
IoU `0,6475409836`, overreach `0` olmuştur. 10 yalnız-gürültü karesinde geniş
aday/doğrulanmış olay ve dört parametre isteğinde geçerli alan oluşmamıştır.
Canlı RF, kalibre doğruluk ve sürekli throughput bu kabul kapsamı dışındadır.

ADR-0038 ile 8 MS/s ham görünümden host kaba aday yolu eklenmiştir. 16.384 FFT
gücü dörderli enerji toplamıyla kanonik 4.096 hücrelik profile bağlanır; sarı
host önerisi zamansal FPGA adayından ayrıdır. Bağımsız sentetik kabul zarfı
100 kHz–4 MHz'te 32/32, üç renkli-gürültü negatifinde 0/32'dir. 6 MHz 31/32
olduğundan garanti edilmez; 8 MHz tam doluluk açıktır. Bu ST-04'ün host koludur;
otomatik FPGA yeniden ayarı, güncel bitstream/kart ve kontrollü RF kapıları
tamamlanmadan PHASE-08 veya sinyal tespiti kapanmış sayılmaz.

ADR-0039 ile ADR-0036'nın sayısal davranışı değiştirilmeden 8→2 MS/s host kanal
seçici C++17 AVX2/FMA3 çekirdeğine alınmıştır. Beş tuning ofsetinde 80 kare
NumPy referansına karşı sıfır CI8 LSB farkıyla geçmiş; bağımsız p95 süre
`0,524815 ms` olmuştur. Statik QML overlay çizimleri RF karesinden ayrılmış ve
15-kare görünüm ritmiyle son fiziksel koşuda 32,15 taze görüntü/s,
40,04 ms p95 çizim aralığı, 20,72 ms p95 veri yaşı elde edilmiştir. Ancak aynı
koşu üç USB shortfall nedeniyle başarısızdır; doğrudan uygulamasız 8 MS/s aktarım
da bir shortfall üretmiştir. Kaynak/DLL bağlı `live-rx-display-8msps-v2.json`
başarısızlığı korur. Farklı fiziksel USB portu/kablo A/B ve ardından iki kısa,
bir 15 dakikalık sıfır-shortfall tekrar geçmeden güncel fiziksel kapı kapanmaz.

### P0 ED sürekli throughput kabulü

Kullanıcının 2026-08-28 devam onayıyla ADR-0029, fiziksel sonuç görülmeden önce
2 MS/s profilinin sürekli işleme kapısını kilitlemiştir. Ürün hizmetinin aynı
yerel ABI yolunu kullanan `p0-ed-throughput-run`; bağlantı, PL Hann/FFT/güç,
DMA, ARM tespiti ve yanıt doğrulamayı birlikte ölçer. Kapı 64 ısınma ve 4096
ölçüm karesi, tüm yanıtlarda DMA `0x7`, sıfır istek/hizmet/sıra/DMA hatası,
sıfır aday düşürme ve en az `488,28125 kare/s` ister. Hostta sahte DMA ile araç,
yetki ve protokol sözleşmesi geçmiştir. PetaLinux 2025.2 imajı 6.090/6.090
görevle hatasız üretilmiştir. Aday-paket PL yolu, kompakt yerel ABI v3,
slicing-by-4 CRC ve iki ARM çekirdeğinin görev odaklı yerleşimi sonrasında
fiziksel kartta geçilmiştir. Güncel kaynaklarla PetaLinux paketi 5.679/5.679,
tam imaj 6.090/6.090 görevle yeniden derlenmiştir. SHA-256 değeri
`da735531487a652cd98a30679f15d1d5706037e705d016ae81c886a9479dcd18`
olan imaj SD karttan soğuk açılmış; FPGA `operating`, kurulu ikili hash
eşitliği ve bit-doğru 54-aday yaşam döngüsü doğrulanmıştır. Dört derinlikli
sınırlı yerel istek kuyruğuyla beş bağımsız koşunun tamamı geçmiş; toplam
20.480/20.480 karede tüm hata sayaçları sıfır, en düşük/ortalama/en yüksek hız
`508,759225230 / 509,458386609 / 509,884071480 kare/s` ve en düşük gerçek-zaman
marjı `1,041938893` olmuştur. Sonuç
`results/evidence/p0/ed-throughput-physical-acceptance.json` içinde korunur.
Canlı HackRF, USB/Ethernet aktarımı, kalibrasyon ve saha doğruluğu bu kabulün
dışındadır.

### P0 ED OS-CFAR PL throughput düzeltmesi

Kullanıcının 2026-08-28 onayıyla ADR-0030 kapsamında kanonik OS-CFAR hücre
kararı PL'ye taşınmıştır. Profil değişmemiştir: 16 referans/yan, 4 koruma/yan,
yükselen rank 24/32, Pfa `1e-4`, Q32 alpha `36.851.433.755` ve strict `>`.
SystemVerilog çekirdeği Python tam-sayı modeliyle 11 kare/45.056 adet 64-bit DMA
kelimesinde bit-doğru geçmiştir. İlk tam karenin simülasyon süresi 50 MHz'te
48.910 çevrimdir; 2 MS/s için kilitli 102.400 çevrim RTL kapasite bütçesini
geçer. Vivado 2025.2 ile `xc7z020clg484-1` üzerinde tam
FFT→güç→OS-CFAR zinciri yerleştirilip yönlendirilmiş; 50 MHz'te setup marjı
`+2,400 ns`, hold marjı `+0,050 ns`, route hata ağı `0` olmuştur. Son kullanım
17.387/53.200 LUT, 13.769/106.400 register, 21/140 BRAM tile ve 45/220 DSP'dir.
Standalone üstte board pinleri bulunmadığı için DRC'deki yalnız `NSTD-1` ve
`UCIO-1` uyarıları gerçek block design'ın I/O katmanına bırakılmıştır. Bu
post-route kapasite kanıtıdır; fiziksel throughput sonucu değildir.

Aynı zincir Avnet ZedBoard `1.5` kart tanımıyla PS7, DDR, AXI DMA, saat, reset
ve kesme yollarını içeren tam block design içinde de temiz kurulmuştur. Tam
tasarım 50 MHz'te `+0,372 ns` setup, `+0,018 ns` hold, sıfır başarısız uç ve
sıfır route hatasıyla geçmiştir; bitstream ile bitstream içeren XSA üretilmiştir.
Kullanım 19.587/53.200 LUT, 17.183/106.400 register, 23,5/140 BRAM tile ve
47/220 DSP'dir. Bitstream ön koşulu DRC sonucu sıfır hata ve sıfır kritik
uyarıdır. Bu üretim kanıtı kart üzerinde çalıştırma veya fiziksel hız kabulü
değildir.

PS yolu bütün karede `0xA` biçim işaretini ve değerlendirme maskesini fail-closed
doğrular. PL kararlarıyla aday gruplama ve yalnız aday tepesinde OS gürültü/eşik
hesabı yapar; geniş bant kurtarma, 2/3 zamansal doğrulama ve parametre çıkarımı
PS'de kalır. Yeni ve eski PS yolları dondurulmuş üç gerçek FFT karesi dahil 11
karede birleşik aday ve geniş bant sonucunda sıfır fark vermiş, PL işaretli sahte
DMA ile ayrıcalıksız Linux hizmet kabulü geçmiştir. Çekirdek kanonik Vivado
üst zincirine bağlanmış; tam block design sentez/route/timing/bitstream/XSA
kapıları geçmiştir. Güncel XSA ve ADR-0030 ARM kaynaklarıyla PetaLinux paketi
5.679/5.679, tam imaj 6.090/6.090 görevle derlenmiş; kök dosya sistemi, `image.ub`
ve yeni bitstream'i içeren `BOOT.BIN` üretilmiştir. Fiziksel kartta DONE, Linux,
FPGA `operating`, DMA, yerel hizmet ve tam 4.096 kelimelik bit-doğru PL çıktısı
geçmiştir. Beş karelik 2/3 olay dizisi de sıfır hata ve sıfır aday düşürmeyle
tamamlanmıştır. Buna karşılık kilitli 64+4.096 sürekli hizmet koşusu
`95,62877 kare/s` ölçülmüş ve gerekli `488,28125 kare/s` kapısı geçilememiştir.
Düzeltilmiş fiziksel profil DMA'yı `1,456537 ms`, ARM zincirini `6,714248 ms`,
birleşik yolu `8,170784 ms` ölçmüştür. ADR-0030 sayısal/işlevsel sonucu kabul,
gerçek-zaman sonucu başarısızdır; sonraki mimari hız düzeltmesi ayrı karar ve
kullanıcı onayı gerektirir.
Önceki fiziksel kanıtlar `56f5f333df4551517fa170ef3dff1da9367913b5`
kaynağına aittir ve güncel ADR-0030 kaynaklarını kabul etmez.

### P0 ARM sıcak yol gecikme düzeltmesi

Kullanıcının 2026-08-28 devam onayıyla ADR-0031 uygulanmıştır. IEEE CRC32 nibble
tablosu, semantik sırayı koruyan temporal eşleşme önbelleği ve strict packet
yolunu regresyon için koruyan typed iç aday yolu tamamlanmıştır. Paket/typed
karşılaştırması 33 kare ve 1.501 aday kaydında sıfır fark vermiş, PetaLinux
5.679/5.679 görevle derlenmiştir. Fiziksel kartta kesin 64+4.096 profiler
4.096/4.096 kareyi sıfır DMA/pipeline/flag/drop/probe hatasıyla tamamlamış; ARM
ortalaması `6,714248 ms` değerinden `2,612712 ms` değerine inmiştir. Yerel hizmet
`196,966411503 kare/s` ile önceki sonucun 2,0597 katına çıkmış ancak kilitli
`488,28125 kare/s` kapısını geçememiştir. ADR-0031 tamamlandı; gerçek-zaman kapısı
açıktır. DMA/ARM ping-pong veya yeni RTL ayrı karar ve kullanıcı onayı gerektirir.
**Tamamlandı; performans kapısı başarısız.**

### P0 doğrulanmış aday yolu kısaltması

Kullanıcının 2026-08-29 devam onayıyla ADR-0032'nin ilk uygulama adımı
tamamlanmıştır. PL decoder tarafından biçim ve aralık açısından doğrulanmış
güç/karar hücreleri için ikinci kez yapılan genel giriş taraması ürün yolundan
çıkarılmış; strict dış OS-CFAR ve çok ölçekli API'leri korunmuştur. Host C
karşılaştırması strict/trusted yollarında karar, aday, gürültü, eşik ve kurtarma
çıktılarında sıfır fark vermiştir. İlk geçici ARM ölçümü hız kazanımı
göstermemiştir; sonraki aday-paket imajı kaynakları kalıcı olarak içermiş,
PetaLinux paket/tam-imaj ve fiziksel kart kapılarından geçmiştir. **Host
eşdeğerliği, kalıcı imaj ve fiziksel aday-paket kabulü tamamlandı.**

Geçici çapraz derlenmiş ARM profilerı mevcut ZedBoard imajına kalıcı kurulum
yapmadan çalıştırılmış; 64+4.096 koşusu 4.096/4.096 ve sıfır hata ile bitmiştir.
ARM ortalaması `2,723289 ms`, birleşik yol `4,173240 ms` olduğundan ADR-0032
kısa yolu hız kapısını kapatmamış ve sonucu iyileştirme olarak ilan edilmemiştir.
Bu ölçüm tarihsel ara sonuçtur; güncel sürekli hız kabulü ADR-0034 ve
`ed-throughput-physical-acceptance.json` içinde ayrıca kayıtlıdır.

### P0 seyrek çok ölçekli aday sınırı

Kullanıcının devam onayıyla ADR-0033 başlatılmıştır. Fiziksel 64+4.096
ayrıştırma, OS gruplamanın `0,635712 ms` ve çok ölçekli tespitin toplam
`1,551391 ms` olduğunu göstermiştir. Yalnız mevcut PHASE-06H gruplamayı bağlamak
gerçek-zaman için yeterli değildir. Sürekli tespit karelerinde final OS+geniş
bant aday kümesi PHASE-06I seyrek paketiyle taşınacak; tam güç/IQ yalnız açık
parametre ölçüm yolunda korunacaktır. Q48 bit-doğru referans, dondurulmuş ve ek
14 karede final aday metadata'sı ile paket round-trip için sıfır fark vermiştir.
On altı bölgeyi paralel işleyen median RTL alt-aşaması beş kare/80 bölgede
sıfır fark ve en fazla `29.756` çevrimle geçmiştir. Buna bağlı bütünleşik enerji
ve iki taraflı geniş bant kurtarma RTL zinciri sekiz karede 24 aday ve 27 AXI
kaydında sıfır metadata farkı vermiş; median dahil son girişten son çıkışa en
fazla `44.886` çevrim ölçülmüştür. Seyrek OS motoru sekiz kare/151 adayda,
final fusion ise sekiz kare/63 final aday ve 65 AXI kaydında sıfır metadata
farkıyla geçmiştir. Uçtan uca son-girişten-son-çıkışa en yüksek `45.557`, bir
örnek/çevrim giriş dahil ardışık işlevsel üst sınır `49.653 / 102.400`
çevrimdir. **Mimari, referans ve final candidate-reducer RTL tamamlandı.
ADR-0037 öncesi synthesis-only wrapper,
Zynq-7020 üzerinde sentez/place/route ve 50 MHz setup/hold kapısını
`WNS=+0,670 ns`, `WHS=+0,053 ns`, sıfır setup/hold endpoint ihlali ve sıfır
route hatasıyla geçti; kanıt `candidate-reducer-vivado.json` dosyasındadır.
Final reducer → PHASE-06I AXI64 packetizer üst bağlantısı, sekiz kare/63 aday/379
beat ve 37 backpressure kararlılık kontrolüyle bit-doğru geçti; güncel kanıt
`candidate-reducer-packetizer-v2.json` dosyasındadır. CI8 girişten FFT/güce ve aynı
aday packetizer sınırına uzanan
`p0_candidate_dsp_runtime_top` hiyerarşisi Icarus compile-only kapısından
geçmiştir. Ardından aynı hiyerarşi ZedBoard PS/AXI DMA blok tasarımına alınmış;
Vivado 2025.2 sentez, route ve 50 MHz kapısı `WNS=+0,423 ns`, `WHS=+0,021 ns`,
sıfır setup/hold endpoint ihlali, sıfır route hatası ve sıfır DRC error/critical
warning ile geçmiştir. Bu Vivado/bitstream kanıtı ADR-0037 öncesi kaynaklara
bağlı tarihsel kayıttır; güncel geniş bant RTL için yeniden çalıştırılmamıştır.
Post-route kullanım 27.453 LUT, 27.154 register, 81,5
Block RAM tile ve 71 DSP'dir; bitstream ve gömülü bitstream'li XSA üretilmiştir.
Kanıt `vivado-50mhz.json` dosyasındadır. Yeni çıkış PHASE-06I değişken uzunluklu
64–54.144 byte aday paketidir. ABI v2 DMA sürücüsü, PetaLinux paketi, kart
programlama, bit-doğru fiziksel aday paketi ve ADR-0034'teki
`488,28125 kare/s` kabulü tamamlanmıştır. Canlı HackRF ve kalibre RF kabulü
hâlâ beklemededir.**

### P0 sınırlı yerel istek boruhattı

Kullanıcının devam onayıyla ADR-0034 uygulanmıştır. Kalıcı ABI v3 imajındaki
tek-istek/tek-yanıt ek tekrarlanabilirlik kontrolü 4/5 geçmiş; başarısız koşu
4.096/4.096 doğru kareye rağmen `487,986461398 kare/s` ile sınırın `%0,0604`
altında kalmıştır. Yöntem veya kabul paydası değiştirilmemiş; aynı sıralı
`SOCK_SEQPACKET` ABI üzerinde dört derinlikli sınırlı istek kuyruğu eklenmiştir.
Hizmet FPGA/DMA/ARM karelerini yine tek tek işler ve her yanıt kare kimliği,
hizmet durumu, DMA `0x7` ve düşen aday sayısıyla doğrulanır.

Güncel kaynaklar PetaLinux paketinde 5.679/5.679, tam imajda 6.090/6.090 görevle
derlenmiştir. SHA-256 değeri
`da735531487a652cd98a30679f15d1d5706037e705d016ae81c886a9479dcd18`
olan imaj SD karttan soğuk açılmıştır. Bilinen kare ve 2-of-3 yaşam döngüsü
host referansıyla alan alan aynıdır. Beş bağımsız 64+4.096 koşuda toplam
20.480/20.480 kare ve sıfır hata elde edilmiş; en düşük/ortalama/en yüksek hız
`508,759225230 / 509,458386609 / 509,884071480 kare/s`, en düşük gerçek-zaman
payı `1,041938893` olmuştur. **Kalıcı fiziksel 2 MS/s yerel hizmet kapısı
tekrarlanabilir biçimde tamamlandı. Canlı HackRF, RF kalibrasyonu ve geniş saha
doğruluğu açık kalır.**

### P0 Mandatory Closure Block A

Kullanıcının ayrı onayıyla P0 içindeki yalnız üç donanımdan bağımsız zorunlu açık
nokta kapatılır: exponential-noise Pfa denkleminden türetilen adlı OS-CFAR
mühendislik profili, kaba aday spanından ayrı gürültü-referanslı bant estimatorü
ve ortak acquisition sözleşmesi üzerinden çalışan `UNKNOWN`, `JUDGE_BAND`,
`JUDGE_FREQUENCY` hakem modları. Bu blok PHASE-06A–J RTL'yi, Vivado tasarımını,
HackRF/PetaLinux/ET/DF donanım kapsamını değiştirmez ve P1'e geçiş onayı değildir.

### P0 Block B0 — HackRF Host Toolchain ve Live-RX Hazırlığı

Fiziksel HackRF geçici olarak mevcut değilken yalnız Computer-1 RX host hazırlığı
yapılır. Upstream HackRF host araçları, `libhackrf`, ayrıntılı discovery durumları,
atanmamış ED_RX seri config'i, RX-only bounded argv/queue, üç hakem modu tuning
planları ve dürüst disconnected UI doğrulanır. `B0 READY`; canlı HackRF, Block B,
hardware RX, FPGA/ZedBoard veya TX PASS anlamına gelmez.

### P0 Block B / PHASE-08 — HackRF Fiziksel RX ve Host Tespiti

Kullanıcının 2026-08-29 onayıyla tek HackRF One, seri numarasıyla `ED_RX`
rolüne bağlanmıştır. İlk merkez-tuned ölçümde zero-IF DC çıkıntısının aday gibi
doğrulandığı görülmüş ve sonuç kabul edilmemiştir. ADR-0035 ile ±100 kHz DC
dışlama, 500 kHz offset tuning ve boşluksuz DC-güvenli alt aralık planı
uygulanmıştır. Beş bağımsız 104,4–104,9 MHz canlı RX koşusunun tamamında en az
bir `LIVE_HACKRF` aday 2-of-3 ile doğrulanmıştır. Toplam 81.920 kompleks örnek
tam byte uzunluğunda, doyan bileşen sayısı sıfırdır. **HackRF fiziksel bounded
RX ve host tespit kapısı tamamlandı. Sürekli USB akışı, 8→2 MS/s örnek oranı
dönüşümü, PC→ZedBoard taşıması, FPGA canlı tespiti ve ürün UI kabulü açıktır.**

### PHASE-07A — Kanal Seçici ve Ağ Köprüsü Donanımsız Kabulü

Kullanıcının devam onayıyla, Ethernet kablosu gerektirmeyen PHASE-07 alt kapısı
tamamlanmıştır. HackRF'nin `8 MS/s × 16.384` girişi stateful NCO, 193 tap
anti-alias FIR ve 4:1 polyphase örnek azaltmayla FPGA'nın tam
`2 MS/s × 4.096 ci8` çerçevesine dönüştürülmüştür. Sürüm 2 `P0IQ/P0RS`
protokolü metadata ve payload için ayrı CRC, ardışık sıra ve dört derinlikli
bounded pipeline kullanır. Taşınabilir C decoder MSVC'de; tam IPv4 bind/peer
allowlist kullanan Linux TCP→`AF_UNIX/SOCK_SEQPACKET` köprüsü GCC/WSL2
loopback'te geçmiştir. Üç tekrarlı 1.024-kare host hız kapısında en düşük sonuç
`488,28125 kare/s` gereksinimini aşmış; drop, sıra hatası ve doyum sıfır kalmıştır.
Kanıt `results/evidence/p0/phase07-host-loopback.json` dosyasındadır.

PHASE-05 kayıtlı/sentetik I/Q kapsamındaki operatör seçimli AM/NFM dinleme
zinciri tamamlanmıştır. Gerçek canlı HackRF dinleme ve ses saha kabulü ayrı
donanım kapısıdır; bu sonuç PHASE-04'ün fiziksel parametre doğrulamasının
tamamlandığı anlamına gelmez.

Doğrudan 1 Gbps Ethernet alt kapısı fiziksel ZedBoard üzerinde tamamlanmıştır.
Köprü sürekli dört istekli akış, CPU0 bağı ve kopyasız yerel istek ile çalışır.
Bilinen CI8 yaşam döngüsü 54 aday için alan bazında eşleşmiş; beş bağımsız
64+4.096-kare koşusunda 20.480/20.480 ölçüm karesi sıfır sıra hatası ve sıfır
aday düşümüyle bitmiştir. En düşük/ortalama/en yüksek hız
`505,184524010 / 506,606589485 / 508,009093258 kare/s`, gereken alt sınır
`488,28125 kare/s` ve en düşük gerçek zaman marjı `1,034617905` olmuştur. Kanıt
`results/evidence/p0/phase07-ethernet-physical-acceptance.json` dosyasındadır.

SHA-256 değeri `5d749d4c2a8a86f2bbcc3be9a700ea32efc8104196b237700740886003e2e61d`
olan PetaLinux imajı soğuk açılıştan sonra FPGA `operating` durumuyla başlamış;
kalıcı ağ köprüsü değişken ağ arayüzünü `auto` seçerek aynı kabulü geçmiştir.
Önceki kabul imajında köprü güvenli varsayılan olarak kapalıdır ve kontrollü kabul oturumunda açıkça
etkinleştirilmiştir. Tek süreçli HackRF stdout RX, stateful kanal seçici ve ağ
taşıması üç aşamalı sınırlı boru hattında birleştirilmiştir. Beş bağımsız canlı
64+4.096-kare koşusunda 20.480/20.480 ölçüm karesi, sıfır USB overrun, sıfır sıra
hatası ve toplam 32.927 FPGA adayıyla tamamlanmıştır. En düşük canlı hız
`488,746900919 kare/s`, gerekli sınır `488,28125 kare/s`; 64-kare kuyruğun tepe
kullanımı 8 olmuştur. Kanıt
`results/evidence/p0/phase07-live-hackrf-fpga-acceptance.json` dosyasındadır.
ADR-0040 işletim imajında aynı tam bind/tek eş sınırı korunarak köprü kart
hizmetiyle birlikte otomatik başlatılır ve başarısız başlangıç hizmeti kapatır.
P09 imajının PetaLinux derlemesi ve kart soğuk açılış kabulü geçmiştir. Beş
koşuda 20.480 ölçüm karesi, minimum 525,83 kare/s ve sıfır sıra/aday düşürme
hatası `adr0040-physical-acceptance.json` içinde kayıtlıdır.
**PHASE-07 tamamlandı. PHASE-08 henüz tamamlanmadı.** Ürün bağı ve fiziksel
kapanış aşağıdaki ayrı kabul adımıyla yürütülür.

### PHASE-08 — Canlı ED ürün oturumu

#### Güncel kapsam — frekansı bilinmeyen yayını arama

Kullanıcı onayıyla yalnız sinyal tespiti ve ilgili arayüz ele alınır; parametre,
dinleme ve ET geliştirmesi bu adımın dışındadır. Kullanıcının paylaştığı 2026
şartnamesinin 5.1.1 maddesi için 1 MHz–6 GHz arası 9.999 bitişik, en fazla
600 kHz sahiplik aralığına bölünür. Örtüşen 2 MHz alıcı ayarları, 1 MHz desteği
en az bir ayarın doğrulanmış kanal seçici geçiş bandında tutar. Dar adaylar tepe
frekansıyla, 257 hücre ve üzeri geniş adaylar mutlak destek örtüşmesiyle bağımsız
yeniden ayarda doğrulanır. Her aralıkta 2 MS/s çıkışta 128 kare
işlenir; ilk sekiz kare gözlem biriktirmeye alınmaz. Pencere ancak bütün
karelerin kart yanıtı ve alım bütünlüğü geçerse doğrulanır. İptal, kırpılma,
bağlantı hatası ve ziyaret edilmemiş bantlar ayrı tutulur. Geçmiş frekans
gözlemleri sabit listede kalır ve durdurma sonrası sabit bant izlemeye aktarılır.

Windows `hackrf_transfer` standart çıktısının metin modunda LF baytını CRLF'ye
çevirebildiği gerçek alımda saptanmıştır. Sürekli RX bu platformda ikili yerel
adlandırılmış kanala alınır; bayt silerek veri düzeltmesi yapılmaz. Taşıma
testleri tüm 256 bayt değerini, kapanışı ve iptali denetler. Eski kaynak bağlı
fiziksel kabul arşivleri değiştirilmez ve yeni kaynak için geçmiş sayılır.
Yeni test kayıtları `build/acceptance/rx-survey/` altında ayrı tutulur.
Tam bant kör RF deneyi, anten kapsamı, yanlış alarm ve kaçırma oranı henüz
kanıtlanmış değildir. PHASE-08 açık kalır; PHASE-09 başlatılmaz.

31 Ağustos uygulama ilerlemesi: aynı HackRF akışından ham 8 MS/s × 16.384
görsel FFT ile 2 MS/s × 4.096 FPGA yolu ayrılmıştır. Görsel FFT'nin kanal
seçici çağrısından ayrı son-kare işçisine taşındığı güncel kaynakla 15 dakika /
439.454-kare RX-only ürün koşusu sıfır USB taşması, 30,51 taze görüntü/s,
36,24 ms p95 çizim aralığı ve 21,82 ms p95 veri yaşıyla geçmiştir. Kanıt
`results/evidence/phase08/live-rx-display-8msps-v1.json` dosyasındadır.
ADR-0037'nin 257-bin üzeri iki taraflı geniş bant yolu yazılım referansı,
sabit nokta model ve SystemVerilog'da uygulanmıştır. 512/2048 bin pozitifler ve
12 dB basamak negatif dahil birleşik RTL/paket zinciri sıfır metadata farkıyla
geçmiştir. Pencere kenarı için 600 kHz adımlı örtüşen tarama ve geniş adayda
mutlak destek örtüşmeli ikinci ayar host testinde geçmiştir. Güncel tam Vivado
sentez/route/zamanlama/bitstream kapısı 1 Eylül'de geçmiştir; kart yükleme,
bütün pencereyi dolduran yayın ve kontrollü RF doğruluğu açık kalır.

4 Eylül'de kullanıcı onayıyla ST-04 arama profili karşılaştırması başlatılmıştır.
İlk RX-only fiziksel baseline'da 20 MHz–6 GHz aralığı, 1 MHz `hackrf_sweep`
hücreleriyle tek turda 0,798792 saniyede ve boşluksuz ölçülmüştür. Aynı aralığın
mevcut 2 MHz ayrıntılı ürün taraması yalnız ham örnek toplamada 2.612,789248
saniye; üç gözlemli mevcut 8 MS/s kaba plan ise 14,696448 saniye alt sınırı
üretir. Bu değerler farklı karar yetkilerine sahiptir: `hackrf_sweep` ve 8 MS/s
yol yalnız kaba host adayı, 2 MHz yol FPGA/ARM ayrıntılı kararıdır. İlk tur
Pd/Pfa, kısa yayın veya FPGA kabulü değildir. Kanıt
`results/evidence/phase08/st04-search-profile-baseline-v1.json` dosyasındadır.
Ardından 1 MHz, 100 kHz ve 25 kHz istenen güç hücresi genişliklerinin her biri
üç bağımsız süreçte üçer tam bant turuyla ölçülmüştür. 27/27 tur 20 MHz–6 GHz
aralığını boşluksuz kapatmış ve ölçüm sonundaki USB shortfall sayacı sıfır
kalmıştır. Süreç medyanları tur başına sırasıyla 0,768583 / 0,764985 / 0,794019
saniyedir ve üçü arasındaki yayılım %3,80'dir; ham CSV medyanı ise yaklaşık
129 kB / 568 kB / 2,00 MB olmuştur. `hackrf_sweep` gerçek hücre genişliklerini
sırasıyla 1 MHz / 98,03922 kHz / 24,87562 kHz olarak üretmiştir. Bu zaman
yakınlığı bir RF tespit profili seçmez; ince çözünürlüğün yaklaşık 15,57 kat
çıktı yükü aynı kayıt ve kontrollü kör yayın sonuçlarıyla birlikte
değerlendirilecektir. Kaynak bağlı rapor ve ham arşiv
`results/evidence/phase08/st04-sweep-resolution-v1.json` ile `.zip`
dosyalarındadır.
Kayıtlı aynı-I/Q karşılaştırması, 955,7 MHz açık/kapalı fiziksel kaydın aynı
0,507904 saniyelik öneklerini iki LO'da 4.096, 8.192, 16.384, 32.768 ve 65.536
FFT uzunluklarıyla işlemiştir. Aday üretimi truth frekansını kullanmamıştır;
truth yalnız sonradan eşleştirme için kullanılmıştır. 4.096 ve 8.192 hedefi
iki LO'da geri kazanamamış, 16.384 hedefi iki LO'da geri kazanıp kapalı kayıtta
ortak aday üretmemiştir. 32.768 ve 65.536 hedefi geri kazanırken kapalı kayıtta
sırasıyla bir ve üç iki-LO ortak aday üretmiştir. Bu tek açıklanmış frekans
kaydında 16.384 temiz tek sonuçtur; farklı bant/yayın/seviye ve kör holdout
olmadan ürün seçimi değildir. Kanıt
`results/evidence/phase08/st04-same-iq-resolution-v1.json` dosyasındadır.
ADR-0041 kontrollü kör deney için hiyerarşik mimariyi kilitler: 20 MS/s / 25
kHz `hackrf_sweep` host tam bant adayı, 8 MS/s / 16.384 FFT iki-LO host RX
kanıtı ve mevcut 2 MS/s / 4.096 FFT FPGA/ARM ayrıntılı kararı. Mevcut RTL'nin
991,375 kare/s işlevsel kapasitesi 2 MS/s gereksiniminin 2,03 katıdır; aynı
4.096-hücre zincirin doğrudan 8 MS/s kullanımı için gereken 1.953,125 kare/s
değerinin yalnız %50,76'sını karşılar. Tam tasarım LUT kullanımının %90,30
olması da kanıtsız geniş FPGA ekini riskli kılar. Mimari yalnız kontrollü kör
deney için seçilmiştir; kaynak bağlı karar
`results/evidence/phase08/st04-hierarchical-detection-architecture-v1.json`
dosyasındadır. Python referansı, ölçülmüş çözünürlük/zaman, aynı-I/Q sonucu ve
RTL kaynak/hız sınırı birlikte bulunduğundan **ST-04 mimari seçimi
tamamlanmıştır**. Kontrollü kör RF doğruluğu ST-08'e kadar açık kalır.
ST-04 tamamlandığından sıradaki teknik iş ST-05'tir; kullanıcı faz onayı olmadan
başlatılmaz. ST-07 ürün taraması ST-05/06 doğrulaması tamamlanmadan başlatılmaz.
ZedBoard USB OTG doğrudan alım olasılığı bant genişliği kazanımı olarak
varsayılmaz; yalnız PC→Ethernet taşımasını kaldırabilecek alternatif topoloji
olarak ayrıca ölçülecektir.

Kullanıcının 4 Eylül 2026 onayıyla ST-05 başlatılmış ve önceden dondurulan 960
dizilik sentetik holdout ilk çalıştırmada geçmiştir. Dar bant OS-CFAR korunmuş;
geniş bant için sekiz kareli, 32/64/128/256 hücreli enerji, iki bağımsız flank,
sınır ve `%75` zaman doluluğu bulunan Python referansı seçilmiştir. Kenarda
referans yoksa yeniden ayar istenir; tek pencere tam doluyken mutlak `yayın yok`
denmez. ADR-0042 ve `st05-wideband-holdout-v2.json` bu seçimi kaynaklara bağlar.
V2 yalnız aday-gerçek eşlemesini bire bir yaparak doğrulayıcıyı sıkılaştırır;
sahneler ve eşikler değiştirilmemiştir.
**ST-05 tamamlanmıştır.** Ürün algoritması değiştirilmemiştir; C/PS, RTL/PL,
sabit nokta, kaynak/zamanlama ve kart eşdeğerliği ST-06'dır ve ayrıca kullanıcı
faz onayı gerektirir.

Kullanıcının ST-06 onayıyla 5 Eylül 2026 ürün görev paylaşımı kaynak sınırına
göre yeniden kurulmuştur. PL; periyodik Hann, 4.096 nokta FFT, exact UQ28.30
güç ve temel OS-CFAR hücre kararını üretir. PS/ARM; 32 KiB işaretli güç
karesini çözer, sekiz karelik çok ölçekli geniş bant kararını, dar/geniş
örtüşme bastırmasını ve tek temporal olay yaşam döngüsünü yürütür. Bu ayrım
ürün algoritmasının eşiklerini değiştirmemiştir. Zynq-7020 post-route
kullanımında LUT 48.040'tan 19.587'ye (`%90,30` → `%36,82`), BRAM 73'ten
23,5 tile'a ve DSP 77'den 47'ye düşmüş; 50 MHz setup WNS `+0,372 ns`, hold
WHS `+0,018 ns` ve failing endpoint sayısı sıfır olmuştur.

Fiziksel kartta sınırlı dört yuvalı CPU0 DMA/CPU1 detector profili beş adet
2.000-kare koşuda `551,2206–577,6820 kare/s` ölçmüş; 2 MS/s için gereken
`488,28125 kare/s` alt sınırına karşı en düşük marj `1,1289`, en yüksek toplam
çift çekirdek kullanımı `%58,20` olmuştur. Güncel kaynaklar ve aynı routed XSA
PetaLinux 2025.2 ile paket ve tam imaj düzeyinde sırasıyla 5.679/5.679 ve
6.090/6.090 görevde tekrar geçmiştir. Oluşan `image.ub` içindeki gerçek
`p0-ed-service` SHA-256 değeri hazırlanan ARM ikilisiyle eşleşir; güncel
bitstream de Vivado kanıtıyla eşleşir. Kaynak bağlı bütünlük kaydı
`results/evidence/phase08/st06-product-integration-v1.json` dosyasındadır.
Bu kayıt derleme ve paketleme kapısını kapatır; aynı imajın kartta soğuk açılışı,
fiziksel ürün hizmeti yaşam döngüsü ve frekansı saklı kontrollü RF Pd/Pfa
kabulü henüz yapılmadığından ST-06 tamamlanmış sayılmaz.

Kullanıcının 2026-08-30 onayıyla doğrulanmış canlı alım yolu ürün uygulamasına
bağlanmıştır. Operatörün seçtiği izleme merkez frekansı için HackRF 1,5 MHz
DC-güvenli ofsetle 8 MS/s alır; stateful kanal seçici çıkışı tam 2 MS/s × 4.096
CI8 kare olarak dört derinlikli Ethernet yoluyla ZedBoard hizmetine gönderilir.
Spektrum ve spektrogram aynı gerçek çıkış karesinin host gösterim yolundan,
tespit kimliği/durumu/frekans hücreleri ve tepe-gürültü oranı ise yalnız ABI v3
FPGA/ARM yanıtından üretilir. Kart yanıtı yokken sonuç üretilmez.

Ürün oturumu tek süreçli ve sınırlıdır; 4.096 kare, 64 kare kuyruk, 16 karede
bir görünüm güncellemesi, açık iptal, USB overrun, I/Q kırpılması, DMA durumu,
aday düşümü ve taşıma sıra/bütünlük kontrolleri kullanır. Birim ve QML ürün
regresyonları; tamamlanma, iptal ve kart yokken fail-closed durumu geçmiştir.
Bağlı gerçek HackRF ürün arayüzünden doğru seriyle bulunmuş; ZedBoard hizmetine
erişilemeyen durumda bağlantı hatası, sıfır spektrum ve sıfır tespit gösterilmiştir.
Kırpılmış giriş/çıkış karesi gönderilmeden reddedilir. Başarısız oturumun
sonuçları temizlenir; geç gelen görünüm güncellemesi sonucu geri getiremez.
Görünüm işleme hatası normal iptal veya başarılı tamamlanma olarak sunulmaz;
yeniden deneme ayrı oturumla doğrulanır.
2026-08-30 fiziksel ürün gözleminde kart erişimi sağlanmış; arayüzden başlatılan
beş ardışık 4.096-kare oturumu toplam 20.480 kareyi sıfır USB taşması, taşıma
CRC/sıra hatası ve kırpılmayla tamamlamıştır. İzleme merkezi 104,65 MHz,
LNA/VGA 0/0 dB'dir. Önceki 16/16 dB denemesi giriş kırpılması nedeniyle ilk
görünümden önce reddedilmiştir; olumsuz kayıt korunmuştur. Ham gözlemler ve
gerçek ekran görüntüleri `results/evidence/phase08/product-live-acceptance.zip`,
yeniden hesaplanan özet `product-live-acceptance.json` içindedir.
Sistem görünümünün canlı kaynak/RTL bağlantıları sonradan gerçek OS-CFAR,
geniş bant aday paketleme ve ARM hizmetiyle eşleştirilmiş; bu düzeltme veri
işleme yolunu değiştirmemiştir. Açık pencere önceki yüklenmiş sürümü gösterir.

**Sınırlı canlı ürün alımı fiziksel olarak geçti; PHASE-08 henüz tamamlanmadı.**
Ortam sinyalleri kontrollü referans RF doğruluğu kanıtı değildir. Fiziksel
durdurma ve sonrasında yeniden başlatma ile 15 dakikalık kesintisiz ürün
veri yolu kabulü geçmiştir. Canlı parametre ürün bağı dört ardışık gerçek FPGA
karesiyle işlevsel olarak geçmiştir; kontrollü referans RF doğruluğu, canlı ses
fiziksel kabulü ve saha kalibrasyonu açık kalır. Sonraki ana faz açılmamıştır.

31 Ağustos fiziksel arama gözleminde 1–1,5 GHz turu, ilk LO'da 73 ve bağımsız
ikinci LO'da 26 kare süren `1.299.995.942 Hz` adayı üretmiştir; iki ayarın
ortalama frekans farkı yaklaşık 19 Hz, her iki alımda USB taşması ve kırpılma
sıfırdır. Ardından tamamlanan 1,28–1,33 GHz turunda bu aday yoktur. Bu farklılık
verici durumunu alıcıdan okuyamadığımız için kontrollü pozitif/negatif kabul
sayılmaz. Sabit bant arayüzündeki 2/3 sonucu bu nedenle `FPGA adayı` olarak
yeniden adlandırılmış; ham RX LO/DC merkezi açıkça işaretlenmiştir. Tarama
arayüzüne aynı ayarlı TX kapalı referans → TX açık karşılaştırma sırası ve ham
JSONL kayıtlarından yeniden üretilebilen fark sınıflandırması eklenmiştir.
Karşılaştırma aynı alıcı/yazılım, tam pencere kapsamı, temiz USB/FPGA aktarımı
ve aynı gerçek kazancı zorunlu tutar. İki LO'da ortalama tepe gücü farkı ile
host 2 MHz toplam kanal gücü farkı ayrı tanı sonuçlarıdır; ikisi de tek turda
verici kimliği veya saha tespit olasılığı kabulü değildir.
Kontrollü fiziksel A/B tamamlanmadan ST-08 ve PHASE-08 kapanmaz.

1 Eylül'deki iki tam 1490–1600 MHz turu, 1587,5 MHz merkezli pencereyi iki
koşuda da en güçlü bölge olarak bulmuştur. İki fiziksel LO ile kaydedilen ham
I/Q, 1.586.923.828,125 Hz tepesini 0 Hz farkla yeniden üretmiş; yazılım
çok ölçekli detector bu tepeyi 120/120 ve 119/120 karede kapsarken kartta
yüklü eski bitstream 0/120 ve 0/120 karede kapsamıştır. Tarama sunumuna tek
turda yerel medyanı en az 6 dB aşan ve en az iki komşu pencerede süren enerji
bölgelerini öne çıkaran tamamlayıcı sıralama eklenmiştir; gerçek kayıtta yalnız
1585,3–1588,5 MHz bölgesi +9,04 dB ile sıralanmıştır. Bu tek-LO enerji adayıdır,
FPGA OS-CFAR'ın veya kontrollü A/B'nin yerine geçmez. Güncel geniş bant RTL
SystemVerilog eşdeğerliğini ve tam 50 MHz Vivado kapısını geçmiştir. FPGA
Manager imajı karta yüklenmiş ve aynı kayıtlı fiziksel I/Q iki LO ayarında
eski imajın 0/120 ve 0/120 sonucunu 119/120 ve 118/120'ye çıkarmıştır. CRC,
sıra ve kuyruk hatası sıfırdır. Kontrollü canlı TX kapalı/açık kabulü hâlâ
açıktır; sonraki faz açılmamıştır.

Kullanıcının harici yayını yeniden ayarlamasından sonraki bağımsız tur 184/184
pencereyi 95,65 saniyede ve sıfır pencere hatasıyla tamamlamıştır. Eski
1586,9 MHz çevresi yer değiştirmediği için harici verici olarak sınıflandırılmamış;
1595,3 MHz penceresindeki artış +4,10 dB ile kilitli +6 dB A/B eşiğinin altında
kalmıştır. Bu bölgenin iki fiziksel LO'daki tam PSD desen korelasyonu 0,916 ve
mevcut kart/host tepe kapsamı 120/120'dir; yalnız kararlı RF adayıdır. İlk uzun
yollu Vivado koşusu Windows yol sınırında, sonraki implementation çalışanı ise
yerleştirme sırasında dışarıdan kesilmiştir. Tamamlanan temiz devam koşusu 50 MHz
tasarımı setup WNS `+0,046 ns`, hold WHS `+0,015 ns`, sıfır failing endpoint,
sıfır route ve DRC hatasıyla geçirmiş; bitstream, FPGA Manager ikilisi ve XSA
üretmiştir. Güncel imajın kayıtlı fiziksel I/Q kart tekrarı
`results/evidence/phase08/fpga-p2-wideband-physical-replay.json` ile geçmiştir;
canlı kontrollü RF doğruluğu açık kalır.

3 Eylül ADR-0040 donanım kapanışında 6 dB zayıf aday sınıfı, PHASE-06I paket
bayrağı ve ARM 24/32 doğrulaması içeren tam Zynq-7020 tasarımı Vivado 2025.2 ile
50 MHz'te route edilmiştir. Setup WNS `+0,199 ns`, hold WHS `+0,010 ns`, failing
endpoint, route hatası ve DRC hatası sıfırdır; bitstream ve XSA üretilmiştir.
Slice LUT kullanımı 48.040/53.200 (`%90,30`) olduğundan kaynak payı izlenir.
Tam PetaLinux imajı aynı XSA ile 6090/6090 görevde derlenmiş, `image.ub` ve yeni
bitstream'i içeren `BOOT.BIN` ayrı hazırlama dizinine alınmıştır. Yeni imajın kartta
soğuk açılışı, fiziksel DMA/ARM 24/32 yürütümü ve frekansı açıklanmamış kontrollü
canlı RF kabulü hâlâ açıktır; PHASE-08 tamamlanmış sayılmaz.

Yarışma tespit yüzeyi sabit frekans ve bant taraması olarak sadeleştirilmiştir.
Canlı alıcı için otomatik açılış denetimi sonraki bağlantı bakımında kaldırılmış;
ürün `Bekliyor` durumunda açılır ve denetim operatörün `Alıcıyı Denetle` eylemiyle
başlar. Bu eylem HackRF keşfi ile FPGA hizmet erişimini paralel denetler ve yalnız
ikisi de erişilebilirse `Hazır` olur. Tekil veya birleşik bağlantı hatası 10 saniye
sonra yeniden bekleme durumuna döner.
Ana eylemler `Taramayı Başlat` ve `Durdur` olarak ortaklaştırılmıştır. SigMF kaynak seçimi, olay konsolu,
yakınlaştırma/geçmiş, taban/aralık ve tepe-tut düğmeleri operatör yüzeyinden
kaldırılmış; frekans ile LNA/VGA denetimleri korunmuştur. Kayıtlı I/Q arka ucu
yalnız tekrarlanabilir test için tutulur. İlgili ürün/QML koşusu 98/98 geçmiştir.

2026-09-01 sabit bant bakımında ürün kimliği logo ile `BÂZ` olarak
sadeleştirilmiş; alt durum çubuğu, tekrarlı bağlantı/hata durumları, grafik yenileme
metinleri ve ham aday açma denetimi kaldırılmıştır. Hata tek yerde operatör nedeni
ve kurtarma eylemiyle gösterilir. Spektrum örneği yokken FPGA izleme penceresi ve
merkez kılavuzu çizilmez. Bu bakım tespit eşiklerini ve FPGA/ARM karar zincirini
değiştirmez; ilgili regresyon paketi 98/98 geçmiştir.

Sonraki seçenek menüsü bakımında ana görev şeridi ve `Alıcı Ayarları` başlangıçta
kapalı hale getirilmiştir. `BÂZ` logosu ana görev şeridini; açılan şeritteki
`Tespit` sembolü ise alıcı seçeneklerini açıp kapatır. Başka bir
görevden yapılan sembol seçimi ED/Tespit sabit-frekans yüzeyine döner; alım,
tarama, FPGA/ARM karar zinciri ve donanım denetimi durumu değiştirilmez.

Hazır-durum bakımında canlı FPGA hizmet/taşıma erişim hatası önceki birleşik
`Hazır` yetkisini düşürür ve yeni denetim olmadan tarama başlatılamaz. ED/Tespit
yüzeyindeki tekrarlı üst sağ rozet kaldırılmış; Parametre, Dinleme, Yön Bulma ve
Sistem görevlerinde korunmuştur. DSP/RTL/ARM işleyişi değiştirilmez.

Aynı bakımın fiziksel hata incelemesinde alıcı probe'u ve 8 MS/s kısa I/Q alımı
başarılıyken 32/32 dB kazançta oluşan I/Q kırpılmasının beş saniye sonra genel
`live_queue_timeout` hatasıyla maskelendiği bulunmuştur. Canlı oturum artık giriş
ve kanal seçici beklemelerini ayrı hata kodlarıyla bildirir; ilk kırpılan kare
doğrudan `iq_saturation` üretir. Tekil tanı koşusunda 32/32 ve 16/16 dB kırpılma
vermiş, 8/8 ve 0/0 dB ayarları 64/64 FPGA yanıtını sıfır USB taşmasıyla
tamamlamıştır. Bu kısa tanı saha kazanç profili veya RF doğruluk kabulü değildir.

Sabit bant tespit yüzeyi sonraki bakımda iç içe kart görünümünden düz, ayırıcılarla
kurulan tek çalışma yüzeyine geçirilmiştir. `İZLEME` merkez çizgisi kaldırılmış,
FPGA'nın geçerli karar penceresi `TESPİT ALANI` olarak adlandırılmıştır. Yalnız
2/3 koşulunu geçen frekanslar sağ listede oturum boyunca tutulur; örtüşen frekans
destekleri yeni FPGA olay kimliği alsa da tek satırda güncellenir. Güncel satır
`Algılanıyor`, geçmiş satır `Son görüldü` olur. Bu frekans geçmişi detector
durumunu uzatmaz ve dış yayın kimliği kanıtı değildir. Regresyon 100/100 geçmiştir.

Canlı ürün gözleminde olay kimliklerinin operatör tarafından toplam sinyal sayısı
gibi okunabildiği ve hızlı liste üyeliğinin seçimi takip etmeyi zorlaştırdığı
görülmüştür. Sunum katmanı bu nedenle frekans-öncelikli ve anahtarlı Qt liste
modeline geçirilmiştir. Doğrulanmamış ham adaylar operatör yüzeyinde gösterilmez;
`Algılanıyor` yalnız 2/3 zamansal koşulunu ifade eder. Ölçüme uygun son dört ardışık
FPGA karesi görünür olay için otomatik korunur; operatörün listeyi dondurması
gerekmez. Frekans geçmişi `Son görüldü` olarak korunur. Seçili frekans
spektrum/spektrogram üzerinde ortak kılavuzdur. Bu bakım FPGA/ARM tespit
eşiklerini, olay ilişkilendirme ve iki-miss sona erme kurallarını değiştirmez.

İlk iki yeni fiziksel UI koşusunda 16-karede bir çizimle USB taşması oluşmuş ve
ürün sonuçları doğru biçimde reddetmiştir. Aynı RX→FPGA yolu GUI olmadan 4.096
kareyi sıfır taşmayla tamamlamıştır. Ürün görünümü her 50 DSP karesinde bir
(`9,77 Hz`) güncellenecek biçimde sınırlandıktan sonra önce beş gerçek UI
oturumu geçmiş, sonraki koşu USB taşmasıyla fail-closed durmuştur. Kök neden
incelemesinde USB okuma ile kanal seçimi/FPGA taşımasının aynı üretici işinde
ardışık yürüdüğü görülmüştür. RX okuma, 512 giriş karesiyle sınırlı yaklaşık
16 MiB ham-I/Q kuyruğuna ayrılmıştır. Bu FPGA-bağlı sürüm sekiz tam fiziksel ürün
koşusunda 32.768/32.768 kareyi sıfır USB/CRC/sıra hatası ve kırpılmayla
tamamlamıştır. İki koşu eşzamanlı host yükü altında geçmiş; kalibre edilmemiş bu
yük genel performans ölçütü sayılmamıştır. Ham kuyruk tepe değerleri 31–111/512
aralığındadır. Operatör iptali 750. karede `operation_cancelled` olarak geçmiş,
sonraki yeniden başlatma 4.096/4.096 kareyi tamamlamıştır. Ayrı kesintisiz
dayanıklılık kabulü 15 dakika boyunca 439.453/439.453 kareyi,
14.399.995.904 ham baytı ve aynı sayıda FPGA yanıtını sıfır
USB/CRC/sıra/kuyruk hatası ve sıfır kırpılmayla tamamlamıştır. Ham RX
kuyruğu bu kaynak bağlı tekrar koşusunda en fazla 170/512 kullanılmıştır.
Sonraki güncel RX/görüntü sürümünün ayrı önizleme işçisiyle yaptığı RX-only
15 dakikalık koşuda ham kuyruk tepesi 28/512, kanal kuyruğu 7/64 ve USB taşması
sıfırdır; FPGA kabulü
değildir. Önce/sonra UI kayıtları
`results/evidence/phase08/detection-ui-decoupling.json`, dayanıklılık kaydı
`results/evidence/phase08/live-rx-endurance-v2.json` dosyasındadır. Canlı parametre
ürün bağı `results/evidence/phase08/live-parameter-functional.json` kaydında dört
ardışık confirmed+observed FPGA karesi ve dokuz ürün alanıyla işlevsel olarak
geçmiştir. Kontrollü RF doğruluğu, canlı ses ve saha kalibrasyonu açık kalır.

Canlı dinleme ürün yolu, host kanal seçicisinin karta gönderdiği ve yanıtı
doğrulanmış ardışık 2 MS/s I/Q karelerinden 5,001216 saniyelik ve yaklaşık
19,1 MiB'lık sınırlı tamponla uygulanmıştır; FPGA I/Q geri döndürmez. Tampon
sıra boşluğunda temizlenir; dinleme yalnız aynı olay bütün pencere boyunca ARM'da
confirmed kalır, karelerin en az %95'inde gözlenir ve ardışık gözlenmeme boşluğu
en çok 8 kare olursa etkinleşir. Operatör AM/NFM kanalını istediğinde immutable
pencere sabitlenir, canlı oturum güvenli biçimde durdurulur ve demodülasyon GUI
iş parçacığı dışında yürütülür. Bu yazılım bağı birim/QML ürün testlerinde
geçmiştir; kontrollü AM/NFM RF kaynağıyla fiziksel ses doğruluğu ve ses aygıtı
kabulü henüz yapılmamıştır. Korunmuş fiziksel HackRF NFM tekrar kaydında güncel
zincir 1.700 Hz sentetik tonu 1.699,951 Hz olarak çıkarmış ve sıfır kırpılma
üretmiştir; gerçek konuşma ve canlı FPGA olay bağı içermediğinden bu tanı kabul
kapısını kapatmaz. Ayrıca ED gezinmesi `Sinyal Tespiti` ve `Parametre
Çıkarımı` için ayrı görev girişlerine ayrılmış, seçili olay ve ortak spektrum
bağlamı iki ekran arasında korunmuştur.

Kullanıcının 2026-08-26 onayıyla `ET-A — Offline ET Ortak Matematiksel Kabul`
bakım paketi uygulanmıştır. Önceden izinli P0 offline kaynaklarında KTR-5.1–5.4
ortak doğrulayıcıya bağlanmış; iki kuyruklu OBW99, tepkili görev denetleyicisinin
sıfır çıkış örneği sınırı ve GPS L1 C/A metadata/PRN/UTC sözleşmesi
düzeltilmiştir. ET-A PHASE-10–12'yi başlatmaz; RF TX, ephemeris, GNSS dalga
şekli, gerçek ses girişi ve kapalı RF düzeni kapsam dışıdır.

Kullanıcının aynı tarihte verdiği ayrı onayla `ET-B — Arabakışlı Offline
Zamanlama` bakım paketi uygulanmıştır. Denetleyici; ölçüm yapılan `DİNLE`, bir
tam pencere süren `GECİKME`, maskeli `GÖREV` ve çıkışı kapalı `KORUMA`
pencerelerini birbirini dışlayacak biçimde ayırır. Offline kompleks görev
tamponu, örnek-seviyesi kapı maskesi, görev çevrimi ve pencere sayıları bağımsız
kabul testine bağlanmıştır. Bu bakım paketi PHASE-10 veya PHASE-11'in RF
kapılarını tamamlamaz; gerçek zamanlı çalıştırma, SDR erişimi ve RF TX yoktur.

Kullanıcının devam onayıyla `ET-C — Ürün Arayüzü Bağı` bakım paketi
uygulanmıştır. Ana Qt Quick/QML uygulamasına ED/ET alan seçimi ve dört doğrulanmış
çevrimdışı ET görev görünümü eklenmiş; `algorithms/et` yayın paketine bilinçli
olarak alınmıştır. Mock kaynak, eski laboratuvar arayüzü, doğrulama verileri ve RF
TX yolu ürün sınırının dışında kalır. ET-C, 1180×680, 1280×720 ve 1440×900
render/binding kapılarıyla doğrulanır; PHASE-10–12 donanım ve RF kabulünü
başlatmaz veya tamamlamaz.

ET-C arayüz bakımında operatöre görünür iç mod adları ve tekrarlı TX uyarıları
tek `YAYIN — DEVRE DIŞI` durumuna indirilmiş; görev sekmeleri, ölçüm hiyerarşisi
ve azaltılabilir mikro geçişler güncellenmiştir. Bu bakım yalnız sunum ve kullanım
kalitesini değiştirir; ET matematiğini veya PHASE-10–12 kapsamını ilerletmez.

Kullanıcının devam onayıyla APP-F ED operatör hiyerarşisi bakımı uygulanmıştır.
Spektrum kaynak panelindeki tekrarlı üst durum bilgileri kaldırılmış, seçili sinyal
ve tespit listesi sıkılaştırılmış, Sistem görünümünde operatör özeti ile geliştirici
ayrıntısı ayrılmıştır. İşleme zinciri ve salt okunur operasyon günlüğü korunur.
Bakım commit'i `6ef650d` üzerinde 27/27 görsel kapı, 49/49 odaklı ürün testi ve
`550 passed, 1 skipped, 0 failed` tam depo regresyonuyla doğrulanmıştır. Bu bakım
algoritma fazını ilerletmez ve fiziksel donanım kabulü anlamına gelmez.

İkinci APP-F ED bakımında Dinleme ölçüm özeti, Yön Bulma kerteriz hiyerarşisi ve
ortak Olay Konsolu sadeleştirilmiştir. Kare işleme başlangıcındaki tekrarlı genel
QML durum bildirimi kaldırılarak tamamlanan kare başına tek güncelleme korunmuş,
görünmeyen Spektrum yüzeyinin gereksiz tespit çizimi engellenmiştir. Bakım commit'i
`c5b6f59` üzerinde 27/27 görsel kapı, 39/39 odaklı ürün testi ve `550 passed,
1 skipped, 0 failed` tam depo regresyonuyla doğrulanmıştır. Bu bakım matematiksel
algoritmaları veya faz durumunu değiştirmez; fiziksel donanım kabulü değildir.

APP-F ortak kabuk kapanış bakımında kaynak seçilmemiş, tespit seçilmemiş ve
geçersiz SigMF durumları görev odaklı hale getirilmiş; navigasyon kısayol ipuçları
ve animasyon erişilebilirlik adı düzenlenmiştir. Boş kaynak ekranı ayrı kanonik
kanıt ve `empty_source_surface` kapısıyla doğrulayıcıya eklenmiştir. Bakım commit'i
`89a2d5e` üzerinde 28/28 görsel kapı, 35/35 odaklı ürün/depo sözleşmesi testi ve
`550 passed, 1 skipped, 0 failed` tam regresyonla kabul edilmiştir. Faz durumu ve
algoritma sonuçları değişmemiştir.

## PHASE-06 kontrollü alt-fazları

- **PHASE-06A — SystemVerilog RTL temeli ve bit-doğru golden eşdeğerlik:** `ci8`, AXI4-Stream, 4096 örnek frame ve frame-istatistik temelini kurmuştur.
- **PHASE-06B — Sabit Nokta Hann Pencereleme ve FFT Arayüz Temeli:** PHASE-02 periyodik Hann tanımını dondurulmuş UQ1.15 katsayılarla signed `ci8` girişe uygular, bileşen başına SQ1.15 olan 32 bit AXI4-Stream çıkış üretir ve bir çevrimlik çekirdek gecikmesini bit-doğru Python modeli ile gerçek RTL simülasyonunda doğrular. Gerçek 4096 nokta FFT, AMD/Xilinx FFT IP, FFT sonrası güç ve `regional` detector bu alt-fazda uygulanmaz.
- **PHASE-06C — 4096 Nokta FFT Mimarisi, Ölçekleme Sözleşmesi ve AMD IP Wrapper Temeli:** AMD FFT LogiCORE mimarisini, fixed forward `N=4096`, natural order ve unscaled full-precision Q15 çıkış sözleşmesini dondurur. Vendor-independent SystemVerilog wrapper/config/event sınırı matematiksel FFT yapmayan transport stub ile Icarus'ta doğrulanır. Gerçek AMD IP generation, vendor FFT simulation, synthesis ve hardware uygulanmaz.
- **PHASE-06D — Gerçek AMD FFT IP Entegrasyonu ve Vendor Doğrulaması:** Gerçek AMD/Xilinx FFT LogiCORE, Vivado tarafından üretilen XCI ve simulation products ile PHASE-06C wrapper sınırına bağlanır. Generated config/TDATA/TUSER/TLAST/event/reset portları, AMD bit-accurate C-model ile tam kompleks çıktı ve XSim wrapper/core davranışı doğrulanır; gerçek core ve wrapper+core gecikmeleri ile sürekli frame/backpressure davranışı ölçülür. Vivado/XSim 2025.2 ve `xilinx.com:ip:xfft:9.1` Rev. 15 ile XCI üretilmiş; 11 frame/45.056 kompleks sonuç C-model ve gerçek-IP XSim arasında sıfır toleransla bit-eşit, iki temiz koşuda deterministik doğrulanmıştır. Sentez, implementation, timing, resource utilization, ZedBoard, lineer güç, PSD ve `regional` detector kapsam dışıdır ve çalıştırılmamıştır.
- **PHASE-06E — Vivado Sentez, Kaynak Kullanımı ve Zamanlama Doğrulaması:** PHASE-06C/06D wrapper, AXI skid buffer, fiziksel adapter ve gerçek generated AMD FFT IP'yi içeren en küçük anlamlı top, Vivado 2025.2 ile `xc7z020clg484-1` üzerinde synthesis ve route'a kadar implementation akışından geçirilmiştir. Sonuçlardan önce dondurulan 100 MHz/10.000 ns hedef `WNS=+0.037 ns`, `TNS=0`, `WHS=+0.050 ns`, `THS=0` ve sıfır failing endpoint ile geçmiştir; 10.093 routable netin tamamı route edilmiştir. Post-route kullanım 3.844 LUT, 1.129 LUTRAM, 7.278 register, 14,5 Block RAM tile, 30 DSP48 ve bir BUFG'dir. XFFT generation içindeki 250 MHz target property proje timing hedefi veya Fmax iddiası değildir. Bitstream, kart, hardware ve power analysis kapsam dışıdır ve çalıştırılmamıştır.
- **PHASE-06F — FFT Çıkışı Lineer Güç RTL ve Sabit Nokta Sözleşmesi:** PHASE-06D'nin signed 29 bit `SQ14.15` I/Q bileşenlerinden exact `I²+Q²` hesaplayan, 58 bit unsigned `UQ28.30` AXI4-Stream çıkışını TLAST ve natural XK_INDEX ile koruyan pipelined SystemVerilog bloğu bit-doğru Python modeli ve Icarus ile 45.068 sonuçta sıfır mismatch ile doğrulanmıştır. PSD normalization, detector, post-power synthesis/timing ve hardware bu işlevsel alt-fazda uygulanmamıştır.
- **PHASE-06G — PHASE-03 Bölgesel Detector RTL ve Sabit Nokta Sözleşmesi:** PHASE-06F natural-order `UQ28.30` power frame'ini shifted-index bölgelerine eşler; 16×256 bölgede exact even medianı iki-rank radix selection ile bulur, üç doğrulanmış Pfa ve center politikasını frame başında kilitler, noise/threshold ve strict detection metadata'sını üretir. Bağımsız integer model ile Icarus RTL 20 frame/81.920 hücrede bütün alanlarda bit-exact; float PHASE-03 ile non-boundary kararlarda sıfır mismatch'tir. Gerçek FFT+power+detector top synthesis-only resource fizibilitesi `xc7z020clg484-1` kapasitesini aşmamıştır. Tek frame buffer nedeniyle processing/replay boyunca input durur; continuous frame desteği yoktur. Post-detector implementation, 100 MHz timing, cell grouping, temporal confirmation, parameter extraction ve hardware uygulanmamıştır.
- **PHASE-06H — Tespit Hücresi Gruplama ve Aday Metadata RTL:** PHASE-03 `DetectionPipeline._group` kaynak sözleşmesindeki shifted detected hücreleri `max_gap_bins=1` ile kaba adaylara birleştirir; her aday için inclusive start/end bin, first-max tie policy ile peak bin, exact peak power, peak bölgesinin noise/threshold metadata'sı ve `end-start+1` coarse span üretir. Natural sıradaki detector stream'i iki 676×94 candidate RAM ile shifted sıraya getirir; kesin üst sınır 1352 aday/frame'dir. Empty frame sentinel, malformed frame, reset, backpressure ve TLAST davranışı 13 frame/1.773 AXI record üzerinde Python golden ile Icarus RTL arasında bit-exact doğrulanmıştır. Standalone targeted Vivado synthesis 879 LUT, 251 FF, 6 BRAM tile ve 0 DSP kullanmıştır. Bu çıktı hassas bandwidth değildir; Hz/dB, temporal 2-of-3, PHASE-04 ölçümleri, post-route timing, bitstream ve hardware bu alt-fazın dışındadır. **Tamamlandı ve donduruldu.**
- **PHASE-06I — PL→PS Aday Paket Transportu ve Sürümlemeli ABI:** PHASE-06H candidate stream'ini 64-bit AXI4-Stream üzerinde 32-byte header, 40-byte candidate record ve 32-byte trailer içeren little-endian ABI v1 packet'ına dönüştürür. `uint32` frame ID, count, status, exact integer metadata ve IEEE payload CRC32 ile maksimum 54.144-byte frame sınırı dondurulmuştur. Python encode/decode ve Icarus packetizer 13 packet/8.964 beat'te byte-exact doğrulanmıştır. Hedef boundary interrupt-driven AXI DMA S2MM ve iki bounded DDR buffer'dır. **Tamamlandı ve donduruldu.**
- **PHASE-06J — Zynq PS Temporal Aday Doğrulama ve Frame Association:** Committed PHASE-06I ABI v1 packet'ını little-endian byte decoder ile strict doğrular ve authoritative PHASE-03 `DetectionPipeline._update_tracks` 2-of-3 state machine'ini bounded portable C11 PS çekirdeğine taşır. Previous span ±2 bin positive-overlap association, global deterministic tie order, iki ardışık miss expiry, 64 active/128 ended ring sınırı, empty/reset ve uint32 frame-wrap davranışı 10 sequence/33 frame/1.501 candidate record üzerinde Python golden ile sıfır semantic mismatch vermiştir. Geliştirme host'unda gerçek C compile/link geçmiştir. Yeni PL RTL yoktur; PetaLinux/ARM cross-build, ZedBoard execution, fiziksel Hz/dB/precise bandwidth, throughput iyileştirmesi ve live RF kapsam dışıdır. **Tamamlandı ve donduruldu.**

PHASE-06J sonrasında aday paketinin Linux DMA sürücüsü, runtime ve ED yerel hizmet
entegrasyonu kaynak düzeyinde tamamlanmış ve WSL2 host kabulünden geçmiştir.
İlk aday-paket imajı kartta Linux ve sıfır-girdi DMA taşıma kapılarını geçmiş,
ancak pozitif bilinen-ton deneyi sıfır aday üretmiştir. Sentez günlüğündeki
`$readmem` hatası Hann katsayı ROM'unun out-of-context çalışmada yüklenmediğini ve
mantığın budandığını göstermiştir. Katsayı kaynağı Vivado'nun kopyaladığı dosya
adıyla bağlanmış ve aynı hata için zorunlu sentez kapısı eklenmiştir. Düzeltilmiş
tasarım 50 MHz'te `WNS=+0,157 ns`, `TNS=0`, `WHS=+0,007 ns`, `THS=0` ve sıfır
yönlendirme hatasıyla bitstream/XSA üretmiştir. Bu XSA, ABI v2 DMA kernel modülü,
runtime ve ED hizmeti PetaLinux 2025.2 projesinde 6.090/6.090 görevle yeniden
derlenmiştir. Bootgen paketi ve SD açılış dosyaları SHA-256 ile doğrulanmış,
düzeltilmiş imaj fiziksel ZedBoard'da açılmıştır. FPGA manager `operating`,
DMA aygıtı ve kernel modülü hazır durumdadır. Dondurulmuş 8.192-byte bilinen-ton
CI8 karesinde DMA hatasız tamamlanmış; 2.224-byte aday paketinin 54 nihai adayı
ve bütün aday alanları bit-doğru referansla eşdeğer bulunmuştur. Üç pozitif ve
iki sıfır karelik servis dizisi 2-of-3 confirmation ile iki-miss expiry kuralını
54 olayda alan-alan geçmiştir. 4.096/4.096 kare işlevsel hatasız tamamlansa da
uçtan uca hizmet hızı `353,663076221/488,28125 kare/s` ve gerçek-zaman marjı
`0,724301980` olduğundan sürekli 2 MS/s kapısı açıktır. Aşama profili
PL+DMA için ortalama `1,261138 ms`, paket doğrulama+temporal için `0,664621 ms`
ve birleşik çekirdek yol için `1,925759 ms` ölçmüştür; bir sonraki düzeltme
servis/IPC maliyetini ve ardışık DMA–ARM çalışmasını hedeflemelidir. Fiziksel
birim dönüşümü/PHASE-04 parametre ölçümü, canlı RF ve kalibrasyon ayrı
kapılardır.

## PHASE-04 kontrollü kurtarma alt-fazı

APP-F sonrasında ilk açık ana kapı olan PHASE-04, kullanıcı onayıyla
`PHASE-04-F1 — Alan Bazlı Parametre Doğrulama ve Ürün Bağı` planına alınmıştır.
F1A–F1E sırası; sözleşme/relocation bağı, sonuçtan önce kilitlenen bağımsız
doğrulama, estimator, tek seferlik binding/OOS ve yalnız geçen alanların digest
bağlı ürün entegrasyonudur. Ayrıntılı kapsam ve kapanış kapıları
`docs/plans/PHASE04_RECOVERY_PLAN.md` içindedir. R1/R2/D1/E1 başarısızlık
kanıtları byte-sabit korunur; P0 host kabulü PHASE-04 başarısı sayılmaz.

F1A, F1B, F1C ve tek seferlik F1D tamamlanmıştır. Yöntem ile değerlendirme
çalıştırıcısı seed reveal öncesinde ayrı digest'lerle kilitlenmiş, commitment'lar
doğrulanmış ve binding ardından OOS yalnız bir kez çalıştırılmıştır. F1D sonucu
başarısızdır: binding'de yalnız span dayanıklılığı; OOS'ta emisyon merkezi,
taşıyıcı çizgisi, span dayanıklılığı, kalibre edilmemiş kanal gücü ve SNR
kapıları geçmiştir. OBW99 ile sinyal alanı OOS'ta, diğer zorunlu alanlar ise
binding'de kalmıştır. Bütün alanların iki popülasyonu birlikte geçme şartı
sağlanmadığından ürün profili üretilmemiş, F1E başlatılmamış ve PHASE-04 açık
kalmıştır. Aynı F1D popülasyonlarıyla eşik ayarı veya yeniden koşu yapılmaz.

F1 başarısızlığından sonra `PHASE-04-F2 — Kontrollü İyileştirme` turu açılmıştır.
F2A salt-okunur kapı analizini tamamlamış; F1 kararlarını yeniden üretmiş,
alanlar arası negatif kontrol kaskadını ve üç protokol/skor kapsama açığını
belgelemiştir. F2B de tamamlanmış; 40 binding ve 24 OOS kontrolünün tamamı
çalıştırılabilir scorer sözleşmesine bağlanmış, altı yeni açık geliştirme seed'i
ayrılmış ve görülmemiş binding/OOS seed commitment'ları v3 yöntem geliştirmesi
öncesinde kilitlenmiştir. F2C de tamamlanmıştır: ayrı v3 kestirimci açık
katalogdaki 40/40 binding kontrolünü geçmiş; gürültü reddi, taşıyıcı, OBW ve
sinyal alanı geliştirme kanıtları yöntem kaynaklarıyla birlikte seed reveal
öncesinde kilitlenmiştir. Açılmış F1 popülasyonları kullanılmamış, F2
binding/OOS seed'leri F2D çalıştırıcı kilidi commit/push sonrasında açılmıştır.
Tek seferlik F2D'de binding 40/40 kontrolü geçmiş, OOS'ta ise taşıyıcı geçerli
aile sayısı ile sinyal alanı yanlış kesin karar sayısı olmak üzere 2/24 kontrol
başarısız olmuştur. Sonuç değiştirilmeden korunur ve aynı popülasyonlarla yeniden
koşulmaz. Bütün alanlar iki popülasyonu birlikte geçmediğinden F2E başlatılmamış,
ürün profili üretilmemiş ve PHASE-04 açık kalmıştır. Yeni iyileştirme turu ancak
ayrı plan, yeni popülasyon commitment'ları ve kullanıcı onayıyla açılabilir.

Kullanıcı onayıyla `PHASE-04-F3 — OOK Dayanıklılığı` turunun F3A salt-okunur
kök neden analizi ve F3B ön-yöntem protokol kilidi tamamlanmıştır. F2D kararları
yeniden üretilmiş; aggregate geliştirme oranlarının OOK taşıyıcı seed-alt sınırı
ile 6 dB sinyal alanı yanlış karar sayımı için yeterli güvenlik payı sağlamadığı
doğrulanmıştır. F2'nin 40 binding ve 24 OOS kontrolü gevşetilmeden byte-bağlı
korunmuş; sekiz yeni açık seed ayrılmış, 14 ek seed-bazlı geliştirme kapısı
çalıştırılabilir sözleşmeye alınmış ve yeni binding/OOS preimage'ları v4
kaynaklarından önce commitment ile kapatılmıştır. Kullanıcı onayıyla tamamlanan
F3C'de ayrı v4 kestirimci sekiz açık seed üzerinde geliştirilmiş; korunan 40
temel ve 14 ek risk kontrolünün tamamı geçmiştir. Yöntem ve geliştirme kanıtı,
yeni binding/OOS seed'leri açılmadan önce `method-lock-v4.json` ile
kilitlenmiştir. Kullanıcı onayıyla F3D çalıştırıcısı commit/push öncesinde
kilitlenmiş, yeni seed'ler commitment doğrulamasıyla açılmış ve popülasyonlar
birer kez çalıştırılmıştır. Binding 40/40 geçerken OOS 23/24 geçmiş; NFM 6 dB
sinyal alanı doğru karar sayısı 48 alt sınırına karşı 44 kaldığı için F3D
başarısız olmuştur. OOK ihlalleri giderilmiş olsa da bütün zorunlu alanlar iki
popülasyonda birlikte geçmemiştir. Aynı popülasyonlar yeniden çalıştırılamaz,
F3E başlatılamaz ve ürün profili oluşturulamaz.

Kullanıcı onayıyla `PHASE-04-F4 — NFM Düşük SNR Dayanıklılığı` turunun F4A
salt-okunur kök neden analizi ve F4B ön-yöntem protokol kilidi tamamlanmıştır.
F4A, F3D'yi yeniden çalıştırmadan NFM 6 dB seed genellemesi, aşırı abstention ve
NFM'e özgü seed kapısı eksikliğini doğrulamıştır. F4B'de önceki popülasyonlardan
bağımsız sekiz açık seed ayrılmış; yeni binding/OOS preimage'ları commitment ile
kapatılmış; korunan F2 kapıları ve F3 risklerine dört NFM seed/risk kapısı ile üç
zorunlu tanı çıktısı eklenmiştir. F4C ayrı yöntem geliştirmesidir ve kullanıcı
onayıyla tamamlanmıştır. v5, mevcut sınırlı özellik/prototip yapısını koruyup
NFM'e en yakın örnekler için leave-one-seed-out çapraz doğrulamalı aile marjı
kullanır; tespit ve taşıyıcı güvenlik payları da aynı açık popülasyonda korunan
kapılarla doğrulanmıştır. Geliştirmede 40 temel, 14 miras ve dört NFM risk kontrolü
geçmiş; yöntem ve kanıtlar gizli seed açılmadan önce `method-lock-v5.json` ile
kilitlenmiştir. Kullanıcı onayıyla tamamlanan F4D'de değerlendirme çalıştırıcısı
commit/push öncesinde kilitlenmiş, taahhüt edilmiş yeni seed'ler doğrulanarak
açılmış ve binding ardından OOS yalnız bir kez çalıştırılmıştır. Binding 40/40
kontrolü geçerken OOS 23/24 geçmiştir. OOS OBW aile alt sınırı 62/64 iken AM,
OOK ve BPSK aileleri 61/64 geçerli ölçümde kalmış; diğer OBW doğruluk, kenar,
clipping ve span kontrolleri geçmiştir. Kanıt bütünlüğü 7/7 doğrulanmıştır.
Bütün zorunlu alanlar iki popülasyonda birlikte geçmediğinden F4D başarısızdır;
aynı popülasyonlar yeniden çalıştırılamaz, F4E başlatılamaz, ürün profili
oluşturulamaz ve PHASE-04 açık kalır. Yeni iyileştirme turu ayrı plan, bağımsız
popülasyon commitment'ları ve kullanıcı onayı gerektirir.

Kullanıcı onayıyla `PHASE-04-F5 — OBW Zamansal Dayanıklılık` turunun F5A
salt-okunur kök neden analizi tamamlanmıştır. F4D kararları yeniden üretilmiş;
OBW yönteminin v3-v5 boyunca değişmediği, kalan retlerin clipping veya genel
ölçüm kalitesinden değil zamansal kenar kararsızlığından geldiği ve geliştirme
aile kapısının %90 iken OOS kapısının %96,875 olduğu doğrulanmıştır. F3/F4 ek
kapılarında seed bazlı OBW geçerlilik payı yoktur. Kullanıcı onayıyla tamamlanan
F5B'de sekiz yeni açık seed F1-F4 popülasyonlarından ayrılmış, yeni binding/OOS
preimage'ları commitment ile kapatılmıştır. Korunan 18 geliştirme kontrolüne
yedi OBW güvenlik kontrolü ve altı zorunlu tanı eklenmiş; aile başına 379/384,
seed başına 47/48 geçerli OBW şartı yöntemden önce kilitlenmiştir. F5E yalnız bütün kapılar geçerse host ürün profilini
etkinleştirir ve FPGA entegrasyonu anlamına gelmez.

Kullanıcı onayıyla başlatılan F5C'nin ilk açık geliştirme taramasında 3,0-5,0
bin arasındaki beş bounded temporal-recovery adayı aynı 3.072 ölçümde
karşılaştırılmış, hiçbiri 25 kilitli geliştirme kontrolünün tamamını geçmemiştir.
En geniş aday aile minimumunda 377/384 ve seed minimumunda 46/48 kalmış; NFM üst
kenar q95 hatası da 2 bin sınırını aşmıştır. Basit eşik genişletmesi yöntem olarak
seçilmemiş ve negatif aday kanıtı korunmuştur. Ardından gürültü-çıkarılmış dört
kare ortalamasında %0,75 kuyruk, 0,375 bin simetrik kenar yanlılığı düzeltmesi ve
7 bin temporal ret sınırı seçilmiştir. Sekiz açık ailede minimum 383/384, seed
minimumunda 47/48 geçerli OBW; en kötü göreli q95 %14 ve alt/üst kenar q95
1,87/1,92 bin elde edilmiştir. Birleşik geliştirme 40 temel, 14 F3, dört F4 ve
yedi F5 kontrolünün tamamını geçmiştir; altı gürültü yanlış-geçerli sayısı
sıfırdır. v6 yöntem ve tek-seferlik çalıştırıcı seed reveal öncesinde ayrı
kilitlerle dondurulmuştur. Kullanıcı onayıyla F5D'de clean/synced runner commit'i
sonrasında commitment'lar doğrulanmış, binding ve OOS seed'leri açılmış ve iki
popülasyon yalnız birer kez çalıştırılmıştır. Binding 40/40, OOS 24/24 ve yedi
alanın tamamı birlikte geçmiştir. OOS OBW aile minimumu 64/64, göreli q95 hata
%9,06, alt/üst kenar q95 1,43/1,58 bin ve clipping sıfırdır. Kanıt bütünlüğü
7/7 geçmiştir. Kullanıcı onayıyla F5E'de altı ölçüm alanı ve span dayanıklılığı
F5D kanıtlarına digest bağlı `phase04f5-operator-assisted-parameters-v6` host
ürün profiline alınmıştır. Qt Quick ürün akışı F5 kestirimcisini yalnız bu profil
doğrulanırsa açar; dört ardışık gözlem ve operatörce onaylanmış izole analiz
aralığını zorunlu tutar. Profil veya çalışma zamanı kaynağı değişirse parametre
ölçümü fail-closed kapanır. PHASE-04 host parametre ürün entegrasyonu tamamlanmıştır;
FPGA, canlı RF, dBm kalibrasyonu ve saha kabulü bu sonuç kapsamında değildir.

## Erken hazırlık istisnası: PHASE-08A

PHASE-04 ana açık faz olarak kalırken, kullanıcı onayıyla PHASE-08'in yalnız donanımdan bağımsız host hazırlığı `PHASE-08A — HackRF Canlı RX Host Altyapısının Donanımsız Ön Hazırlığı` adıyla erken yürütülmüştür. PHASE-08'in asıl kapsamı değişmez. PHASE-08A yalnız acquisition adaptörü, deterministik test kaynağı, sınırlı süreç güvenliği ve dürüst UI durumlarını kapsar. Gerçek cihaz keşfi, gerçek sweep, canlı I/Q, RF performansı ve donanım kanıtı PHASE-08 donanım kabul turuna aittir. Bu tarihsel istisna PHASE-07 veya PHASE-08'in tamamlandığı anlamına gelmez ve sonraki ana fazlar için otomatik onay oluşturmaz.
