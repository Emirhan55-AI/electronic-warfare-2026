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

PetaLinux 2025.2 hedef derlemesi; özel device-tree compatible değeri,
`/dev/p0-dma` sağlayan modül, `p0-dma-run` aracı, otomatik modül yükleme kaydı ve
HackRF/OpenSSH/udev bağımlılıklarıyla tamamlanmıştır. Bu, boot edilebilir yazılım
hazırlığıdır. Deprecated `petalinux-package --boot` ile ayrıca paketlenen ilk
`BOOT.BIN` fiziksel A/B testinde UART-sessiz başarısız olmuş, aynı kartta eski imaj
yeniden boot etmiştir. PetaLinux-native `xilinx-bootbin` hedefiyle üretilen recovery
imajı statik Bootgen denetiminden geçmiştir fakat henüz kartta çalıştırılmamıştır.
Fiziksel `S2MM_LENGTH=32768`, DMA IOC ve sayısal golden henüz çalıştırılmamıştır.

## Hata ve iddia sınırı

Eksik giriş `TKEEP` değeri sticky hata üretir. FFT olayları PHASE-06C sözleşmesinin
sticky durum bitlerinde korunur. Driver ve boot artifact'larının derlenmiş olması
kart çalışması, fiziksel DMA completion, FPGA golden veya canlı HackRF sonucu
değildir; bunlar yalnız gerçek UART ve runtime çıktısıyla kabul edilebilir.
