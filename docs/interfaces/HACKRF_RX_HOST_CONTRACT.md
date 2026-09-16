# HackRF RX Host Acquisition Sözleşmesi

Canlı `rf_amplifier` seçimi tam boolean'dır, varsayılan kapalıdır. AMP
sabit izleme, tarama, aday doğrulama ve bunlardan başlatılan alımlarda aynı
oturum yapılandırmasına taşınır. Ayar alım dururken kaydedilir; yeni oturumda
`-a` komutuna çevrilir. Kayıttaki ayar oturum komutudur, bağımsız fiziksel
geri okuma iddiası değildir. AMP kontrolü LNA/VGA değerlerini kendiliğinden
değiştirmez; taramadaki mevcut kırpılma sonrası sınırlı kazanç tekrar politikası
bu eklemede değiştirilmemiştir.
Bias-T, özel analog filtre ve frekans kalibrasyonu bu eklemede açılmadı.

Hazır durum kalıcı bir USB varsayımı değildir. Etkin tam seri boşta periyodik
olarak yeniden keşfedilir; kaybolduğunda bütün RX başlatma kapıları kapanır ve
operatör yeniden `Sistemi Denetle` akışına yönlendirilir. Tanı komutunun kendi
başarısızlığı cihaz kaybı kanıtı sayılmaz; kesin kayıp sonraki denetimde aranır.

## Bileşen sınırı

`platforms/acquisition/` Qt ve DSP import etmez. Gerçek ve deterministik test backend'leri aynı `HackRFBackend` sözleşmesini uygular. Controller yalnız bu sözleşmeyi kullanır; UI ve controller `subprocess` çağırmaz. Gerçek backend `hackrf_info`, `hackrf_transfer` ve `hackrf_sweep` dışında executable kabul etmez.

PortaPack Mayhem denetim yolu ayrı bir RX hazırlık adımıdır. Yalnız USB-seri
`VID 0x1D50 / PID 0x6018` kimliğini taşıyan tam bir aygıt tekil bulunduğunda
115200 8N1 üzerinden `hackrf\r\n` gönderilir. Tam yazmadan sonra CDC çıkışı
temizlenir ve firmware'in satırı tüketmesi için port kapatılmadan önce 500 ms
beklenir. Bu adım FPGA hizmeti hazır değilse çalışmaz. Sonrasında `hackrf_info`
ile yapılandırılmış alıcı seri numarası
yeniden görülmeden RX hazır sayılmaz. Genel COM portuna, eksik kimliğe veya
birden çok eşleşmeye komut gönderilmez.

HackRF yeniden göründüğünde seçim keşif veya COM sırasına göre yapılmaz. Kayıtlı
`ED_RX_PRIMARY` görünürse seçilir; değilse kayıtlı `ED_RX_SECONDARY` aynı RX
ürün yolları için yedek olur. İki seri birlikte görünürse birincil seçilir.
Etkin seri her `hackrf_transfer -d` bağına, bant taramasına, aday doğrulamasına
ve seri-özel spur profiline taşınır. Yapılandırılmamış cihaz hazır yetkisi vermez.

Araç keşfi dosya sistemi üzerinden yapılır. Güvenli yardım sorguları açık `argv`, `shell=False`, iki saniyelik zaman aşımı ve 32.768 byte stdout/stderr sınırıyla çalışır. Cihaz keşfi ancak operatör denetim düğmesine bastığında ve gerekli araç doğrulandığında worker içinde yapılabilir. B0'daki `NO_DEVICE` hazırlık sonucu, PHASE-08 fiziksel turunda tek `ED_RX` HackRF keşfi ve bounded RX kabulüyle aşılmıştır.

Discovery sonuçları `TOOLCHAIN_UNAVAILABLE`, `NO_DEVICE`, `ONE_DEVICE`,
`MULTIPLE_DEVICES` ve `DEVICE_ERROR` olarak ayrıdır. Bir veya daha çok cihaz
bulunması capture yetkisi vermez; `ED_RX` config'indeki gerçek seriyle eşleşme
zorunludur.

Güncel fiziksel veri yolu `HackRF — USB → Windows host — Ethernet → ZedBoard
PS/DMA/PL — Ethernet → operatör arayüzü` biçimindedir. ZedBoard UART bağlantısı
I/Q veya aday paketi taşımaz; yalnız açılış, bakım ve ayrıcalıklı kart yönetim
konsoludur. HackRF'nin ZedBoard USB OTG portundan alınması uygulanmış bir özellik
değildir. Böyle bir değişiklik Zynq PS USB-host/device-tree, libhackrf, sürekli
alım servisi ve PS→PL DMA yolunun ayrı geliştirme ve fiziksel kabulünü gerektirir.
Mevcut KTR-4.1 kabulü tamamlanmadan bu alternatif mimariye geçilmez.

## Bounded süreç ve veri

- Aynı anda en fazla bir dış süreç bulunur.
- İptalde önce `terminate`, 250 ms içinde kapanmazsa `kill` uygulanır.
- Capture örnek sayısı 4.096–65.536 aralığında ve 4.096'nın katıdır; varsayılan 16.384'tür.
- Capture tam olarak `sample_count × 2 byte` olmalıdır. Tek kalan byte, kısa ve uzun çıktı typed hata üretir.
- Gerçek capture yalnız işletim sistemi geçici alanındaki bir dosyaya yazılır; başarı, hata, iptal ve kapanış sonunda dosya silinir.
- `ci8`, signed 8-bit interleaved I/Q'dur ve `128` ile normalize edilerek mevcut kompleks floating-point girişe çevrilir.
- Bounded frame kaynağı yalnız dört çerçevelik varsayılan capture'ı bellekte tutar. Host RX source tek producer thread, en çok 8 frame kuyruk, drop/error sayacı ve bounded stop/join kullanır; sınırsız kuyruk veya sürekli kayıt oluşturmaz.

## CLI seçenek zarfı

Gerçek RX ancak yerel `hackrf_transfer -h` çıktısında `-d`, `-r`, `-f`, `-s`, `-n`, `-a`, `-l` ve `-g` seçeneklerinin tamamı görülürse kurulabilir. `-d` atanmış ED_RX serisini zorunlu kılar. Backend RX-only argv üretir; TX seçenekleri kabul edilmez. Varsayılan RF amplifier kapalı, IF/LNA 16 dB ve Baseband/VGA 16 dB'dir; bunlar optimum, kalibre edilmiş veya dBm karşılığı değildir. Örnekleme zarfı 8, 10 ve 20 MS/s'tir.

Gerçek `hackrf_sweep` çıktı biçimi henüz donanımla doğrulanmadığından production sweep `not_exercised` döner. Bounded fixture parser'ı yalnız iki alanlı `frequency_hz,power_dbfs` test biçimini doğrular. Sweep coarse keşiftir; PHASE-03 detector sonucu değildir.

HackRF One zero-IF merkez çıkıntısı RF sinyali kabul edilmez. Ürün profili merkez
çevresindeki ±100 kHz'i adaylardan çıkarır ve istenen aralığı 500 kHz offset
tuning ile en çok 2,5 MHz'lik bitişik alt aralıklarda kapsar. Capture içinde
herhangi bir karede 2-of-3 ile doğrulanan son geçerli gözlem, capture'ın boş
kareyle bitmesi nedeniyle kaybedilmez; capture'lar arasında gizli durum tutulmaz.

## Worker ve kullanıcı arayüzü

Araç/cihaz keşfi, capture, `ci8` çözümleme, FFT ve detector worker tarafında çalışır. Mevcut `QThreadPool` üst sınırı `1`, pending niyet üst sınırı `1` ve generation/stale-result reddi korunur. Kaynak değişimi ve pencere kapanışı acquisition işlemini iptal eder, kaynak durumunu ve temporal zinciri sıfırlar.

Kaynak adları `SigMF Kaydı`, `HackRF Canlı RX` ve `Deterministik Test Kaynağı`dır. Test backend'i canlı veya bağlı cihaz olarak gösterilmez. Araç ya da cihaz yokken canlı kontroller pasiftir. PHASE-04 alanları `Henüz doğrulanmadı` kalır.

Canlı ürün oturumu `app/operator_console/live_ed.py` içinde orkestre edilir;
`platforms/acquisition/` bu nedenle Qt ve DSP'den bağımsız kalır. Canlı yol
yalnız gerçek backend ve seri bağlı `ED_RX` cihazını kabul eder. Operatör izleme
merkezini seçer; HackRF merkezi normalde 1,5 MHz aşağıdadır. Bu ayar cihazın
1 MHz alt sınırını aşacaksa merkez 1,5 MHz yukarı alınır. 8 MS/s giriş ve 193 tap kanal
seçici 2 MS/s × 4.096 CI8 FPGA karesi üretir. Görsel spektrum aynı alımın ham
8 MS/s × 16.384 örnekli karesinden host tarafında hesaplanır; FPGA sahiplik
alanı ve izleme merkezi geniş görünümde ayrıca işaretlenir. Tespit listesi yalnız ZedBoard ABI v3 yanıtındaki
etkin olaylardan oluşturulur; kart yanıtı yoksa host tespiti yedek sonuç olarak
gösterilmez. Frekans taraması sırasında parametre ve ses işlemleri başlatılmaz.

### Sıralı frekans taraması ve Windows ikili taşıma

`rx_survey.py`, mevcut kart yolunu değiştirmeden 1–6.000 MHz aralığını
9.999 bitişik, en fazla 600 kHz sorumluluk hücresine böler. Hücre merkezli
2 MHz alıcı ayarları örtüşür; böylece merkezi kendi hücresinde olan en fazla
1 MHz destek, en az bir ayarda kanal seçicinin doğrulanmış ±800 kHz geçiş bandı
içinde kalır. Bu geometrik sınır algılama olasılığı veya RF doğruluğu iddiası
değildir. Son üst sınır dahil, diğer üst sınırlar hariçtir. Her pencere taze
kanal seçici/TCP oturumuyla 128 kare
işler; ilk sekiz kare gözlem biriktirmeye alınmaz. Yalnız gerçek yanıtta
confirmed+observed olaylar kaydedilir; sonuç frekansı adayın tepe hücresidir,
dar aday doğrulaması tepe frekansıyla, 257 hücre ve üzeri geniş aday doğrulaması
mutlak destek aralığı örtüşmesiyle yapılır. Listelenen frekans destek merkezidir;
hassas taşıyıcı veya OBW kestirimi değildir. Tam kare sayısı ve bütünlük geçmeden
pencere kapsama eklenmez. Kırpılmış pencere hatalıdır; boş sayılmaz.
Bağlantı/veri/depolama hatası taramayı durdurur. Kapsama, kart yanıtlı alımı
ifade eder; her yayının bulunduğu veya antenin o bantta yeterli olduğu iddiası
değildir. Tur gözlemleri tarihsel olup sürekli aktif yayıncı listesi değildir.

Windows'ta sürekli RX `-r -` yerine yerel, ikili adlandırılmış kanal kullanır.
Bu, stdout metin modunun LF→CRLF dönüşümünü önler; gelen baytlardan CR silinmez.
Diğer platformlarda ikili stdout yolu korunur. Tam bayt sayısı ve EOF birlikte
doğrulanır; süreç çıkışı beklenmeden fazla veri denetlenerek boru doluluğunda
kilitlenme önlenir. İptal ve zaman aşımı bekleyen kanal I/O'sunu da sonlandırır.
Windows bağımlılığı `pywin32==311` olup yalnız bu platformda kurulur.

Her tur benzersiz, üzerine yazılmayan JSONL kaydına yapılandırma, kaynak SHA-256,
pencere kapsamı, gerçek sonuç sayaçları ve gözlem metadatasını yazar. Bu kayıt
bütün ham I/Q'yu saklamaz; tek başına dalga biçimi yeniden oynatma veya RF
doğruluğu kanıtı değildir. Önceki fiziksel kabul kaynak özetleri korunur;
aşağıdaki tarihsel sonuçlar yeni taşıma sürümünün yeniden kabulü yerine geçmez.

Kırpılmış giriş/çıkış karesi karta gönderilmez. Oturum sonunda USB veya taşıma
bütünlüğü başarısızsa gösterilen spektrum ve tespitler temizlenir; oturum hata
durumunda kalır. Geç gelen görünüm bildirimi eski sonuçları geri getiremez.
Görünüm işleme hatası da başarılı tamamlanmaya veya operatör iptaline çevrilmez.
Yeni oturum hata durumunu sıfırlayıp kendi verisiyle başlar.

## Fiziksel kabul ve kalanlar

2026-08-30 sıralı RX ön denemesinde ürün ekranından 151 pencere ve 19.328
kare 54,18 saniyede hatasız tamamlanmış; operatör iptali yarım pencereyi
kapsama eklememiştir. Yerel kayıt
`build/acceptance/rx-survey/6e779824045b4fef946a57dc53f4192d.jsonl` içindedir.
Son ayar-görünümü düzeltmesinden sonra güncel kaynak özetleriyle yeniden yapılan
1–5,2 MHz ve 5.995,8–6.000 MHz ön denemeleri toplam altı pencere/768 karede
geçmiştir (`preflight-low-v4.jsonl`, `preflight-high-v3.jsonl`). Her pencerede
4.194.304 ham bayt tamdır; USB taşması ve taşıma sıra hatası sıfırdır.
Bu kısa örneklerden tam tur için yaklaşık 25–26 dakika tahmin edilir; tam
tur süresi ölçümü veya bilinmeyen vericiyi bulma başarısı değildir. Anten
duyarlılığı ve kontrollü RF kabulü açık kalır. Aşağıdaki kayıtlar önceki sürümlere aittir.

Seri numarası `0000000000000000a32868dc35138247` olan cihazda WinUSB erişimi,
beş bounded dört-frame capture, gerçek offset tuning ve host tespiti geçmiştir.
Toplam 81.920 kompleks örnekte byte uzunlukları tam, doyan bileşen sayısı
sıfırdır. Fiziksel kanıt `results/evidence/p0/hackrf-rx-physical-acceptance.json`
dosyasındadır. Sürekli 8→2 MS/s USB/Ethernet/ZedBoard/FPGA yolu PHASE-07 fiziksel
kabulünde beş kez geçmiştir. PHASE-08 ürün penceresinden başlatılan beş ardışık
4.096-kare oturumu 104,65 MHz, LNA/VGA 0/0 dB koşulunda eksiksiz ve hatasız
tamamlanmıştır. Önceki 16/16 dB giriş kırpılması oturumu sonuç üretmeden
durdurmuştur. Kanıt `results/evidence/phase08/product-live-acceptance.json`
içindedir. USB okuma, 512 karelik sınırlı ham-I/Q kuyruğuyla kanal seçimi ve
FPGA taşımasından ayrılmıştır. Bu FPGA-bağlı kaynak sürümü sekiz tam koşuda
32.768 kareyi sıfır
USB/taşıma hatasıyla tamamlamış; 750. karede fiziksel iptal ve ardından tam
yeniden başlatma geçmiştir. Kanıt
`results/evidence/phase08/detection-ui-decoupling.json` içindedir. Kesintisiz
dayanıklılık kabulü 15 dakika boyunca 439.453/439.453 kareyi ve
14.399.995.904 ham baytı sıfır USB/CRC/sıra/kuyruk hatası ve sıfır
kırpılmayla tamamlamıştır. Ham RX kuyruğu en fazla 28/512 kullanılmıştır.
Hash-bağlı kanıt `results/evidence/phase08/live-rx-endurance.json`
içindedir. Sonraki güncel RX/görüntü sürümünde görsel FFT kanal seçici
çağrısından ayrılmış; RX-only 15 dakika / 439.454 kare sıfır USB taşması,
28/512 ham ve 7/64 kanal kuyruğu tepesi, 30,51 taze görüntü/s ve 21,82 ms p95 veri yaşıyla
geçmiştir. Hash-bağlı kanıt
`results/evidence/phase08/live-rx-display-8msps-v1.zip` içindedir; FPGA yanıtı
ve tespit doğruluğu iddiası taşımaz. Oturum açılışını ve kuyruk boşaltmayı
içeren hızlar FPGA
azami kapasitesi değildir; kontrollü RF doğruluğu ayrı kabul kapısıdır.
dBm kalibrasyonu, kontrollü RF doğruluğu, canlı parametre doğruluğu, canlı ses
ve saha başarısı bu sınırlı kabulün dışındadır.

ADR-0039 bu tarihsel kabulden sonra kanal seçiciyi aynı sayısal sözleşmeyle
C++17 AVX2/FMA3 çekirdeğine alır. Fiziksel HackRF yolu derlenmiş çekirdek yoksa
fail-closed durur. Beş tuning ofsetinde 80 kare NumPy referansına karşı sıfır
CI8 LSB farkıyla geçmiş; p95 kanal seçici süresi `0,524815 ms` ölçülmüştür.
Canlı görünüm 15 DSP karesinde bir, nominal 32,55 Hz beslenir. Güncel 60 saniye
koşusunda 32,15 taze görüntü/s, 40,04 ms p95 çizim aralığı ve 20,72 ms p95 veri
yaşı geçmiştir; üç USB shortfall nedeniyle genel sonuç başarısızdır. Uygulamasız
8 MS/s aktarım da bir shortfall ürettiğinden farklı fiziksel port/kablo tekrarı
ve ardından uzun kaynak-bağlı kabul zorunludur. Kayıtlar
`native-channelizer-v3.json` ve `live-rx-display-8msps-v2.json` dosyalarındadır.
