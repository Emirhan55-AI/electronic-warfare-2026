# Uygulama Yol Haritası

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
| PHASE-10 | ET simülasyonu ve kapalı RF test altyapısı | İletimsiz dalga şekli simülasyonları doğrulanır; kablolu, zayıflatıcılı ve RF olarak kapalı test düzeni güvenlik kontrolünden geçmeden RF TX etkinleştirilmez. |
| PHASE-11 | Sürekli ve arabakışlı karıştırma | Sürekli ve arabakışlı dalga şekilleri önce simülasyonda, ardından yalnız onaylı kapalı RF düzeneğinde güç, spektrum ve görev çevrimi ölçümleriyle doğrulanır. |
| PHASE-12 | Analog telsiz ve GPS L1 aldatma | Analog telsiz ve GPS L1 senaryoları önce iletimsiz simülasyonda, ardından yalnız izinli kablolu/zayıflatıcılı kapalı düzende izole test alıcılarıyla doğrulanır. |
| PHASE-13 | Arayüz, sistem entegrasyonu ve yarışma demosu | Doğrulanmış profil kilidiyle Operasyon ekranında ED görev akışı ve yalnız izin verilen ET gösterimleri uçtan uca çalışır; demo provası, güvenlik kontrol listesi ve kanıt paketi tamamlanır. |

## ET güvenlik kapıları

ET geliştirmesi önce iletimsiz simülasyon ve dalga şekli doğrulamasıyla başlar; ardından kablolu, zayıflatıcılı ve RF olarak kapalı test düzenine geçer. Güvenli test düzeneği kurulup doğrulanmadan RF TX etkinleştirilmez. Açık ortam RF testi yalnız yürürlükteki mevzuat, yarışma komitesi izni ve komitenin belirlediği zaman ile test düzeni altında yapılabilir.

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
Köprü güvenli varsayılan olarak kapalıdır ve bu kontrollü kabul oturumunda açıkça
etkinleştirilmiştir. Tek süreçli HackRF stdout RX, stateful kanal seçici ve ağ
taşıması üç aşamalı sınırlı boru hattında birleştirilmiştir. Beş bağımsız canlı
64+4.096-kare koşusunda 20.480/20.480 ölçüm karesi, sıfır USB overrun, sıfır sıra
hatası ve toplam 32.927 FPGA adayıyla tamamlanmıştır. En düşük canlı hız
`488,746900919 kare/s`, gerekli sınır `488,28125 kare/s`; 64-kare kuyruğun tepe
kullanımı 8 olmuştur. Kanıt
`results/evidence/p0/phase07-live-hackrf-fpga-acceptance.json` dosyasındadır.
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

Yarışma tespit yüzeyi sabit frekans ve bant taraması olarak sadeleştirilmiştir.
Canlı alıcı açılışta otomatik denetlenir; ana eylemler `Taramayı Başlat` ve
`Durdur` olarak ortaklaştırılmıştır. SigMF kaynak seçimi, olay konsolu,
yakınlaştırma/geçmiş, taban/aralık ve tepe-tut düğmeleri operatör yüzeyinden
kaldırılmış; frekans ile LNA/VGA denetimleri korunmuştur. Kayıtlı I/Q arka ucu
yalnız tekrarlanabilir test için tutulur. İlgili ürün/QML koşusu 98/98 geçmiştir.

2026-09-01 sabit bant bakımında ürün kimliği logo ile `BÂZ` olarak
sadeleştirilmiş; alt durum çubuğu, tekrarlı bağlantı/hata durumları, grafik yenileme
metinleri ve ham aday açma denetimi kaldırılmıştır. Hata tek yerde operatör nedeni
ve kurtarma eylemiyle gösterilir. Spektrum örneği yokken FPGA izleme penceresi ve
merkez kılavuzu çizilmez. Bu bakım tespit eşiklerini ve FPGA/ARM karar zincirini
değiştirmez; ilgili regresyon paketi 98/98 geçmiştir.

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
sıra boşluğunda temizlenir; dinleme yalnız aynı olay her karede
confirmed+observed ise etkinleşir. Operatör AM/NFM kanalını istediğinde immutable
pencere sabitlenir, canlı oturum güvenli biçimde durdurulur ve demodülasyon GUI
iş parçacığı dışında yürütülür. Bu yazılım bağı birim/QML ürün testlerinde
geçmiştir; kontrollü AM/NFM RF kaynağıyla fiziksel ses doğruluğu ve ses aygıtı
kabulü henüz yapılmamıştır. Ayrıca ED gezinmesi `Sinyal Tespiti` ve `Parametre
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
