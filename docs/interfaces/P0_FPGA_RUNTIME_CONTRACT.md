# P0 FPGA Runtime ve DMA Sınırı

> Güncellik notu — 31 Ağustos 2026: Aşağıdaki yeni aday-paket imajı için
> "henüz kart kabulü yok" cümleleri entegrasyon öncesi tarihseldir. Sonraki
> fiziksel paket, soğuk açılış ve 2 MS/s hizmet kabulü geçmiştir; kanıt ve
> kontrolü açık kalan RF kapsamı [güncel durum belgesindedir](SIGNAL_DETECTION_STATUS.md).
> ADR-0037 ile eklenen 257-bin üzeri iki taraflı geniş bant yolu henüz yeni
> bitstream ve kart kabulünden geçmemiştir; aşağıdaki fiziksel sonuçlar önceki
> imaja aittir.

## PL veri yolu

Kanonik top `p0_candidate_dsp_runtime_top` aşağıdaki doğrulanmış blokları yeniden
kullanır:

`AXI4-Stream ci8 → PHASE-06B Hann → PHASE-06D AMD 4096 FFT → PHASE-06F exact lineer güç → ADR-0033 final aday indirgeme → PHASE-06I AXI64 paket`

Giriş her beat'te `{Q[7:0], I[7:0]}` ve `TKEEP=2'b11` taşır. Her frame tam 4096
karmaşık örnektir; son örnekte `TLAST=1` olur. Hann çıkışı bileşen başına signed
Q1.15, FFT çıkışı signed 29-bit Q14.15, güç çıkışı 58-bit unsigned UQ28.30'dur.
Güç çıkışı 58-bit unsigned UQ28.30 olarak aday indirgeme zincirine girer. DMA
çıkışı artık ham güç beat'i değil, `PL_PS_CANDIDATE_TRANSPORT_ABI.md` ile
dondurulmuş 64-bit PHASE-06I paketidir. Paket 32-byte header, aday başına 40-byte
record ve 32-byte trailer taşır; 0–1.352 aday için toplam uzunluk 64–54.144
byte'dır. Son beat'te `TLAST`, son geçerli byte'larda `TKEEP` kullanılır.

`TVALID`, `TREADY` ve `TLAST` bütün bloklarda AXI kurallarına göre korunur. FFT'nin
natural `XK_INDEX` alanı güç bloğundan aday indirgeme zincirine taşınır. Paket
record'larındaki shifted start/end/peak bin alanları ABI'nin tanımladığı frekans
eşlemesini korur.

Paket gürültü, eşik ve tepe gücünü exact integer metadata olarak taşır. Fiziksel
Hz/dBFS/OBW99 dönüşümü ve parametre ölçümü PS tarafında kalır. Periyodik Hann için
`Σw²=3N/8` normalizasyonu korunur; kalibrasyon katsayısı olmadan dBm üretilmez.
Parametre isteği açıkça verildiğinde ARM, aynı CI8 karesinden referans PSD'yi yeniden
hesaplar; bu yardımcı yol FPGA'nın bit-tam aday/güç akışının yerine yeni bir donanım
doğruluğu iddiası değildir.

## Çalışma zamanı ayrımı

`p0_candidate_dsp_runtime_top`, Icarus compile-only kapısından sonra kanonik
ZedBoard PS/AXI DMA blok tasarımına alınmıştır. Vivado 2025.2 sentez, route ve
50 MHz kapısı `WNS=+0,423 ns`, `WHS=+0,021 ns`, sıfır setup/hold endpoint
ihlali, sıfır route hatası ve sıfır DRC error/critical warning ile geçmiştir.
Post-route kullanım 27.453 LUT, 27.154 register, 81,5 Block RAM tile ve 71
DSP'dir. Bitstream ve gömülü bitstream içeren XSA üretilmiştir. Bu sonuç kart
programlama, DMA yazılım uyumluluğu veya fiziksel hız kabulü değildir.

P0 blok tasarımında AXI DMA MM2S DDR'dan ci8 frame'i PL'ye, S2MM ise 64-bit aday
paketini DDR'a taşır. OS-CFAR hücre kararı, gruplama, geniş bant kurtarma ve
PHASE-06I paketleme PL sahibidir; strict paket doğrulama, temporal doğrulama ve
fiziksel parametre çıkarımı PS/ARM sahibidir.

Aşağıdaki fiziksel kanıtlar tarihsel `p0_dsp_runtime_top` güç→ARM yoluna ve
bilinen deterministik çerçevelere aittir. Yeni aday-paket bitstream'i için kart
kabulü sayılmaz.

Tarihsel güç-frame imajındaki `p0-os-cfar-run`, DMA'nın doğal FFT sıralı 4096 adet
little-endian UQ28.30 güç beat'ini okur, `fftshift` bin eşlemesini uygular ve kanonik
`P0_OS_CFAR_EXPONENTIAL_PFA_1E4` profiliyle ham aday JSON'u üretir. Fiziksel kartta
bilinen çerçevenin FPGA güç hash'i golden çıktıyla, ARM aday JSON'u ise host C
çıktısıyla byte-tam eşleşmiştir. Bu tek deterministik çerçevedeki 147 ham aday,
temporal doğrulanmış olay veya canlı RF detector doğruluğu olarak yorumlanmaz.

Tarihsel güç-frame imajındaki `p0-ed-runtime-run`, aynı güç çerçevesindeki OS-CFAR adaylarını dondurulmuş
PHASE-06I ABI v1 header/record/trailer ve IEEE CRC32 sınırına paketler; ardından
PHASE-06J portable C çekirdeğini kalıcı durumla çalıştırır. Tepe gücü FPGA'nın
UQ28.30 değerinden bit-tam korunur. OS-CFAR sıra istatistiği gürültüsü integer
referans hücrelerinden yeniden ve exact seçilir; eşik en yakın UQ32.30 tam
sayıya yuvarlanır. Kanonik Pfa `1e-4`, ABI `pfa_select=1` olarak taşınır.
Fiziksel kartta üç ayrı ve golden ile byte-tam FPGA güç çerçevesi ilk karede
geçici, ikinci karede 2/3 doğrulanmış olay üretmiş; iki boş kare sonunda olaylar
sonlanmıştır. 81.076 byte ARM sonuç JSON'u host C çıktısıyla byte-tam eşleşmiştir.
Araç güncel rootfs içindeki `/usr/bin/p0-ed-runtime-run` yoluna kurulmuş; yeni
`image.ub` SD karta yazıldıktan sonraki soğuk açılışta FPGA manager, DMA aygıtı,
üç byte-tam güç çerçevesi ve host/ARM olay eşdeğerliği yeniden geçmiştir.

Direct-mode DMA sözleşmesi SG kapalı ve DRE kapalı olarak kalır. Bir giriş frame'i
`4096×16 bit = 8192 byte`, bir çıkış paketi `64 + 40×candidate_count` byte olur;
üst sınır 54.144 byte'dır. AXI DMA buffer-length alanı 16 bittir ve 65.535-byte
üst sınırı paketi temsil eder. Sürücü 54.144-byte DMA-coherent tampon ayırır,
S2MM'yi bu kapasiteyle önce kollar ve IOC sonrasında S2MM_LENGTH register'ından
gerçekte yazılan paket uzunluğunu okur. 64–54.144 aralığı dışındaki veya 8-byte
hizalı olmayan uzunluklar fail-closed reddedilir.

`p0_dma_client` çekirdek sürücüsü iki DMA adresinde de 8-byte hizalamayı zorunlu
tutar. Her çalıştırmada DMA resetlenir, S2MM kanalına hedef adres ve 54.144-byte
kapasite yazılarak alıcı önce hazırlanır, ardından MM2S kanalına kaynak adres ile
8192-byte length yazılır. İki kanal ayrı kesmelerle IOC/error tamamlanması,
5 saniye timeout ve AXI DMA `DMAIntErr`, `DMASlvErr`, `DMADecErr` ile SG hata
bitleri açısından denetlenir. Kullanıcı runtime'ı kapasiteyi alır, status'taki
actual `output_bytes` değerini kontrol eder ve yalnız o kadar paketi okur.
`/dev/p0-dma` izinleri bilinçli olarak `0600` kalır. Ürün uygulaması aygıta
doğrudan erişmez. `P0_ED_LOCAL_SERVICE_ABI.md` ile tanımlanan yerel kart hizmeti
aygıtı açtıktan sonra `p0ed` hesabına yetki düşürür; tam 8192-byte I/Q isteğini
CRC ve sürüm kapılarından geçirir, DMA→PHASE-06I paket doğrulama→PHASE-06J
ABI v1→2/3 sonucunu alan alan little-endian serileştirir. Bu paragraftaki
PetaLinux 2025.2 ARM paket, rootfs ve `image.ub` sonuçları tarihsel güç-frame
imajına aittir; yeni aday-paket ABI'si için yeniden üretilmelidir. Tarihsel
rootfs içinde `p0ed` hesabı,
SysV başlatma bağlantıları ve ARM EABI5 servis/istemci doğrulanmıştır. O tarihsel imajın
fiziksel soğuk açılışında hizmet otomatik başlamış; DMA aygıtı `root:root 0600`,
hizmet süreci ek grubu olmayan `p0ed` ve soket `p0ed:petalinux 0660` olarak
ölçülmüştür. DMA aygıtını doğrudan okuyamayan `petalinux` kullanıcısı, soket
üzerinden beş karelik FPGA→OS-CFAR→2/3 dizisini çalıştırmış ve bütün olay alanları
host referansıyla eşleşmiştir. SysV yeniden başlatma sonrasında yeni süreç ve
soketle ek bir fiziksel istek de geçmiştir.

Tarihsel PetaLinux 2025.2 hedef derlemesi; ZedBoard PS önayarı, özel device-tree compatible
değeri, `/dev/p0-dma` sağlayan modül, `p0-dma-run`, salt-okuma varsayılanlı FCLK
koruma modülü/aracı ve HackRF/OpenSSH/udev bağımlılıklarıyla tamamlanmıştır. O
imaja ait FSBL, bitstream, U-Boot ve device tree içeren native `BOOT.BIN` fiziksel kartta
DONE, UART ve Linux giriş kapılarını geçmiş; DONE ve UART Linux giriş kapısı üç
ardışık soğuk açılışta 3/3 tekrarlanmıştır. Bu konfigürasyonda 8192-byte MM2S,
32768-byte S2MM, iki kanal IOC ve hata/timeout denetimleri geçmiştir. Sıfır çerçeve
tamamen sıfır çıkmış; bilinen 4096 örneklik çerçevenin 32768-byte güç çıktısı
yazılım referansıyla 10/10 byte-tam eşleşmiştir. Native açılışta FCLK0 50 MHz,
reset serbest ve 50 MHz doğrulama hata maskesi sıfırdır. Ayrı önceki fiziksel
oturumda 50 MHz geçişi, reset sırası ve yasal 100 MHz geri dönüşü doğrulanmıştır.

Kaynak ağacının `algorithms/fpga/` altında birleştirilmesinden sonra önceki
güç-frame platformu 2026-08-27 tarihinde temiz durumdan üretilmiş ve yukarıdaki
native boot/DMA kabulinde kullanılmıştır. 2026-08-29 tarihinde üretilen yeni
aday-paket bitstream/XSA ise farklı artefakttır; `vivado-50mhz.json` ile
hash-kilitlidir ve henüz yeni PetaLinux imajı ya da fiziksel kart kabulü yoktur.

## Hata ve iddia sınırı

Eksik giriş `TKEEP` değeri sticky hata üretir. FFT olayları PHASE-06C sözleşmesinin
sticky durum bitlerinde korunur. Driver ve boot artifact'larının derlenmiş olması
tek başına kart kabulü değildir. Kaydedilmiş UART/runtime kanıtı yalnız yukarıdaki
boot, FCLK, DMA ve tek bilinen çerçeve kapsamını kabul eder; Ethernet, throughput,
canlı HackRF ve RF sonucu değildir.
