# P0 FPGA Runtime ve DMA Sınırı

## PL veri yolu

Kanonik top `p0_dsp_runtime_top` aşağıdaki doğrulanmış blokları yeniden kullanır:

`AXI4-Stream ci8 → PHASE-06B Hann → PHASE-06D AMD 4096 FFT → PHASE-06F exact lineer güç → AXI4-Stream UQ28.30`

Giriş her beat'te `{Q[7:0], I[7:0]}` ve `TKEEP=2'b11` taşır. Her frame tam 4096
karmaşık örnektir; son örnekte `TLAST=1` olur. Hann çıkışı bileşen başına signed
Q1.15, FFT çıkışı signed 29-bit Q14.15, güç çıkışı 58-bit unsigned UQ28.30'dur.
DMA çıkış beat'i 64 bittir; üst altı bit sıfırdır ve `TKEEP=8'hFF` olur.

`TVALID`, `TREADY` ve `TLAST` bütün bloklarda AXI kurallarına göre korunur. FFT'nin
natural `XK_INDEX` alanı güç bloğundan `m_axis_bin_index` tanı portuna taşınır;
DMA belleğinde beat sırası natural FFT bin kimliğidir. PS fiziksel frekans
dönüşümünde bu sırayı kullanır.

PS göreli toplam gücü raw FFT-power toplamını `N × Σw²` ile normalize ederek FS²
ölçeğine çevirir; periyodik Hann için `Σw²=3N/8` olur. dBFS bu lineer FS²
değerinin `10·log10` sonucudur. Kalibrasyon katsayısı olmadan dBm üretilmez.

## Çalışma zamanı ayrımı

P0 blok tasarımında AXI DMA MM2S DDR'dan ci8 frame'i PL'ye, S2MM ise 64-bit güç
beat'lerini DDR'a taşır. OS-CFAR, gruplama, temporal doğrulama ve fiziksel parametre
çıkarımı PS/ARM sahibidir. PHASE-06G/H/I doğrulanmış hızlandırıcıları korunur fakat
P0 DMA zincirinde yer almaz.

Native PetaLinux imajındaki `p0-os-cfar-run`, DMA'nın doğal FFT sıralı 4096 adet
little-endian UQ28.30 güç beat'ini okur, `fftshift` bin eşlemesini uygular ve kanonik
`P0_OS_CFAR_EXPONENTIAL_PFA_1E4` profiliyle ham aday JSON'u üretir. Fiziksel kartta
bilinen çerçevenin FPGA güç hash'i golden çıktıyla, ARM aday JSON'u ise host C
çıktısıyla byte-tam eşleşmiştir. Bu tek deterministik çerçevedeki 147 ham aday,
temporal doğrulanmış olay veya canlı RF detector doğruluğu olarak yorumlanmaz.

`p0-ed-runtime-run`, aynı güç çerçevesindeki OS-CFAR adaylarını dondurulmuş
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
`4096×16 bit = 8192 byte`, bir çıkış frame'i `4096×64 bit = 32768 byte` olur.
AXI DMA buffer-length alanı 16 bittir; `65535 byte` üst sınırı iki frame boyunu da
temsil eder. 14 bitlik tarihsel yapılandırmanın `16383 byte` üst sınırı tek S2MM
paketini temsil edemediğinden güncel kabul platformu değildir.

`p0_dma_client` çekirdek sürücüsü 8192 ve 32768 byte'lık DMA-coherent tamponların
sahibidir ve iki DMA adresinde de 8-byte hizalamayı zorunlu tutar. Her çalıştırmada
DMA resetlenir, S2MM kanalına hedef adres ile 32768-byte length yazılarak alıcı
önce hazırlanır, ardından MM2S kanalına kaynak adres ile 8192-byte length yazılır.
İki kanal ayrı kesmelerle IOC/error tamamlanması, 5 saniye timeout ve AXI DMA
`DMAIntErr`, `DMASlvErr`, `DMADecErr` ile SG hata bitleri açısından denetlenir.
Kullanıcı aracı yalnız tam 8192-byte giriş ve tam 32768-byte çıkış kabul eder.
`/dev/p0-dma` izinleri bilinçli olarak `0600` kalır. Ürün uygulaması aygıta
doğrudan erişmez; kalıcı entegrasyon ayrıcalıklı, dar bir kart servisi ve
yetkisiz operatör istemcisi sınırı kurmalıdır.

PetaLinux 2025.2 hedef derlemesi; ZedBoard PS önayarı, özel device-tree compatible
değeri, `/dev/p0-dma` sağlayan modül, `p0-dma-run`, salt-okuma varsayılanlı FCLK
koruma modülü/aracı ve HackRF/OpenSSH/udev bağımlılıklarıyla tamamlanmıştır. Yeni
FSBL, bitstream, U-Boot ve device tree içeren native `BOOT.BIN` fiziksel kartta
DONE, UART ve Linux giriş kapılarını geçmiş; DONE ve UART Linux giriş kapısı üç
ardışık soğuk açılışta 3/3 tekrarlanmıştır. Bu konfigürasyonda 8192-byte MM2S,
32768-byte S2MM, iki kanal IOC ve hata/timeout denetimleri geçmiştir. Sıfır çerçeve
tamamen sıfır çıkmış; bilinen 4096 örneklik çerçevenin 32768-byte güç çıktısı
yazılım referansıyla 10/10 byte-tam eşleşmiştir. Native açılışta FCLK0 50 MHz,
reset serbest ve 50 MHz doğrulama hata maskesi sıfırdır. Ayrı önceki fiziksel
oturumda 50 MHz geçişi, reset sırası ve yasal 100 MHz geri dönüşü doğrulanmıştır.

Kaynak ağacının `algorithms/fpga/` altında birleştirilmesinden sonra bütün Vivado
TCL kaynak yolları bu kanonik dizine taşınmış ve proje 2026-08-27 tarihinde temiz
durumdan yeniden üretilmiştir. Vivado 2025.2; blok tasarımı, sentez, route,
setup/hold zamanlaması, bitstream ve gömülü bitstream içeren XSA üretimini tekrar
geçmiştir. Bu çıktı yukarıdaki native boot ve DMA fiziksel kabulinde kullanılmıştır.

## Hata ve iddia sınırı

Eksik giriş `TKEEP` değeri sticky hata üretir. FFT olayları PHASE-06C sözleşmesinin
sticky durum bitlerinde korunur. Driver ve boot artifact'larının derlenmiş olması
tek başına kart kabulü değildir. Kaydedilmiş UART/runtime kanıtı yalnız yukarıdaki
boot, FCLK, DMA ve tek bilinen çerçeve kapsamını kabul eder; Ethernet, throughput,
canlı HackRF ve RF sonucu değildir.
