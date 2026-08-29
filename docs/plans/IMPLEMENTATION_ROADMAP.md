# Uygulama Yol Haritası

Fazlar sıralıdır; bir fazın çıkış kapısı doğrulanmadan ve kullanıcı onayı alınmadan sonraki faza geçilmez.

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

### P0 ED sürekli throughput kabulü

Kullanıcının 2026-08-28 devam onayıyla ADR-0029, fiziksel sonuç görülmeden önce
2 MS/s profilinin sürekli işleme kapısını kilitlemiştir. Ürün hizmetinin aynı
yerel ABI yolunu kullanan `p0-ed-throughput-run`; bağlantı, PL Hann/FFT/güç,
DMA, ARM tespiti ve yanıt doğrulamayı birlikte ölçer. Kapı 64 ısınma ve 4096
ölçüm karesi, tüm yanıtlarda DMA `0x7`, sıfır istek/hizmet/sıra/DMA hatası,
sıfır aday düşürme ve en az `488,28125 kare/s` ister. Hostta sahte DMA ile araç,
yetki ve protokol sözleşmesi geçmiştir. PetaLinux 2025.2 imajı 6.090/6.090
görevle hatasız üretilmiştir. Fiziksel kartta optimize edilmiş servisle
4.096/4.096 kare, DMA `0x7`, sıfır hata ve sıfır aday düşürme geçmesine rağmen
hız 116,33994 kare/s olmuş, kilitli 488,28125 kare/s kapısı geçilememiştir.
İlk 50,67380 kare/s ölçümüne göre 2,295 kat iyileşme vardır. Sonuç
`results/evidence/p0/ed-throughput-physical-acceptance.json` içinde
başarısız kabul olarak korunmuştur. Aynı süreçteki profil DMA'yı 0,457 ms,
ARM zincirini 5,700 ms, OS-CFAR'ı 4,790 ms ölçmüş ve darboğazı PL/RTL'ye
taşıma kararını gerekçelendirmiştir. Bu kapı kapanmadan sürekli gerçek-zaman
başarısı ilan edilemez. Canlı HackRF,
USB/Ethernet aktarımı, kalibrasyon ve saha doğruluğu bu kabulün dışındadır.

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
çıktılarında sıfır fark vermiştir. Bu adım yeni imaj veya RTL üretmez; mevcut
PetaLinux kanıtı bu kaynakları kapsamadığı için fiziksel 64+4.096 profiler ve
`488,28125 kare/s` kapısı yeniden çalıştırılana kadar performans sonucu açık
kalır. **Host eşdeğerliği ve geçici ARM çalıştırması tamamlandı; yeni imaj ve
gerçek-zaman kabulü beklemede.**

Geçici çapraz derlenmiş ARM profilerı mevcut ZedBoard imajına kalıcı kurulum
yapmadan çalıştırılmış; 64+4.096 koşusu 4.096/4.096 ve sıfır hata ile bitmiştir.
ARM ortalaması `2,723289 ms`, birleşik yol `4,173240 ms` olduğundan ADR-0032
kısa yolu hız kapısını kapatmamış ve sonucu iyileştirme olarak ilan edilmemiştir.
Bu ölçüm yalnız çalışma uyumluluğudur; yeni PetaLinux imajı ve sürekli hız kapısı
ayrıca beklemektedir.

### P0 seyrek çok ölçekli aday sınırı

Kullanıcının devam onayıyla ADR-0033 başlatılmıştır. Fiziksel 64+4.096
ayrıştırma, OS gruplamanın `0,635712 ms` ve çok ölçekli tespitin toplam
`1,551391 ms` olduğunu göstermiştir. Yalnız mevcut PHASE-06H gruplamayı bağlamak
gerçek-zaman için yeterli değildir. Sürekli tespit karelerinde final OS+geniş
bant aday kümesi PHASE-06I seyrek paketiyle taşınacak; tam güç/IQ yalnız açık
parametre ölçüm yolunda korunacaktır. Q48 bit-doğru referans, dondurulmuş ve ek
14 karede final aday metadata'sı ile paket round-trip için sıfır fark vermiştir.
On altı bölgeyi paralel işleyen median RTL alt-aşaması beş kare/80 bölgede
sıfır fark ve en fazla `29.756` çevrimle geçmiştir. Buna bağlı 32-bin
bütünleşik enerji ve 41-bin geniş bant kurtarma RTL zinciri beş karede 22 aday
ve 24 AXI kaydında sıfır metadata farkı vermiş; median dahil son girişten son
çıkışa en fazla `44.755` çevrim ölçülmüştür. Seyrek OS motoru 5 kare/151 adayda,
final fusion ise 5 kare/61 final aday ve 62 AXI kaydında sıfır metadata farkıyla
geçmiştir. Uçtan uca son-girişten-son-çıkışa en yüksek `45.428`, bir örnek/çevrim
giriş dahil ardışık işlevsel üst sınır `49.524 / 102.400` çevrimdir. **Mimari,
referans ve final candidate-reducer RTL tamamlandı. Synthesis-only wrapper,
Zynq-7020 üzerinde sentez/place/route ve 50 MHz setup/hold kapısını
`WNS=+0,670 ns`, `WHS=+0,053 ns`, sıfır setup/hold endpoint ihlali ve sıfır
route hatasıyla geçti; kanıt `candidate-reducer-vivado.json` dosyasındadır.
Final reducer → PHASE-06I AXI64 packetizer üst bağlantısı, beş kare/61 aday/345
beat ve 30 backpressure kararlılık kontrolüyle bit-doğru geçti; kanıt
`candidate-reducer-packetizer.json` dosyasındadır. Pin atanmış board top'u,
DMA/driver/iki-buffer, PetaLinux ve fiziksel `488,28125 kare/s` kabulü hâlâ
beklemededir. CI8 girişten FFT/güce ve aynı aday packetizer sınırına uzanan
`p0_candidate_dsp_runtime_top` hiyerarşisi Icarus compile-only kapısından
geçmiştir. Ardından aynı hiyerarşi ZedBoard PS/AXI DMA blok tasarımına alınmış;
Vivado 2025.2 sentez, route ve 50 MHz kapısı `WNS=+0,423 ns`, `WHS=+0,021 ns`,
sıfır setup/hold endpoint ihlali, sıfır route hatası ve sıfır DRC error/critical
warning ile geçmiştir. Post-route kullanım 27.453 LUT, 27.154 register, 81,5
Block RAM tile ve 71 DSP'dir; bitstream ve gömülü bitstream'li XSA üretilmiştir.
Kanıt `vivado-50mhz.json` dosyasındadır. Yeni çıkış PHASE-06I değişken uzunluklu
64–54.144 byte aday paketidir; mevcut 32.768-byte güç-frame sürücüsüyle uyumlu
değildir. Sürücü/PetaLinux yeniden derleme, kart programlama, fiziksel
`488,28125 kare/s` kabulü ve canlı HackRF hâlâ beklemededir.**

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

**P0 öncesindeki kayıtlı ana açık fazlar: PHASE-04 ve PHASE-06**

PHASE-05 kayıtlı/sentetik I/Q üzerinde operatör seçimli AM/NFM dinleme zincirini doğrulamıştır; bu sonuç PHASE-04 parametre doğrulamasının tamamlandığı anlamına gelmez. PHASE-06A–J tamamlanmış ve dondurulmuştur. PHASE-06J, PHASE-06I ABI v1 packet'ını strict tüketen bounded portable C11 PS temporal çekirdeğini host compile/link ve Python golden eşdeğerliğiyle doğrulamıştır. PetaLinux/ARM, gerçek DMA/driver/device tree, fiziksel birim dönüşümü, post-detector timing ve hardware sonucu değildir. Gerçek canlı HackRF dinleme, PHASE-07, PHASE-08 donanım kabulü ve TX başlatılmamıştır.

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
- **PHASE-06I — PL→PS Aday Paket Transportu ve Sürümlemeli ABI:** PHASE-06H candidate stream'ini 64-bit AXI4-Stream üzerinde 32-byte header, 40-byte candidate record ve 32-byte trailer içeren little-endian ABI v1 packet'ına dönüştürür. `uint32` frame ID, count, status, exact integer metadata ve IEEE payload CRC32 ile maksimum 54.144-byte frame sınırı dondurulmuştur. Python encode/decode ve Icarus packetizer 13 packet/8.964 beat'te byte-exact doğrulanmıştır. Hedef boundary interrupt-driven AXI DMA S2MM ve iki bounded DDR buffer'dır; DMA IP/driver/device tree instantiate edilmemiştir. PetaLinux/ARM toolchain hazır olmadığından C ABI/decoder kaynakları hazırlanmış fakat compile/ARM execution ve temporal 2-of-3 uygulanmamıştır. **Tamamlandı ve donduruldu.**
- **PHASE-06J — Zynq PS Temporal Aday Doğrulama ve Frame Association:** Committed PHASE-06I ABI v1 packet'ını little-endian byte decoder ile strict doğrular ve authoritative PHASE-03 `DetectionPipeline._update_tracks` 2-of-3 state machine'ini bounded portable C11 PS çekirdeğine taşır. Previous span ±2 bin positive-overlap association, global deterministic tie order, iki ardışık miss expiry, 64 active/128 ended ring sınırı, empty/reset ve uint32 frame-wrap davranışı 10 sequence/33 frame/1.501 candidate record üzerinde Python golden ile sıfır semantic mismatch vermiştir. Geliştirme host'unda gerçek C compile/link geçmiştir. Yeni PL RTL yoktur; PetaLinux/ARM cross-build, gerçek DMA/driver/device tree, ZedBoard execution, fiziksel Hz/dB/precise bandwidth, throughput iyileştirmesi ve live RF kapsam dışıdır. **Tamamlandı ve donduruldu.**

PHASE-06J sonrasındaki gerçek DMA/PetaLinux integration, ARM/ZedBoard execution, fiziksel birim dönüşümü/PHASE-04 parametre ölçümü ve detector-throughput iyileştirmesi ayrı bir sonraki kontrollü planlama kararına tabidir. PHASE-06J bunları, post-detector timing'i veya hardware çalışmasını mevcut saymaz.

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

PHASE-04 ana açık faz olarak kalırken, kullanıcı onayıyla PHASE-08'in yalnız donanımdan bağımsız host hazırlığı `PHASE-08A — HackRF Canlı RX Host Altyapısının Donanımsız Ön Hazırlığı` adıyla erken yürütülür. PHASE-08'in asıl kapsamı değişmez. PHASE-08A yalnız acquisition adaptörü, deterministik mock backend, bounded süreç güvenliği ve dürüst UI durumlarını kapsar. Gerçek cihaz keşfi, gerçek sweep, canlı I/Q, RF performansı ve donanım evidence'ı PHASE-08 donanım kabul turuna aittir. Bu istisna PHASE-06–07'nin başladığı, atlandığı veya tamamlandığı anlamına gelmez.
