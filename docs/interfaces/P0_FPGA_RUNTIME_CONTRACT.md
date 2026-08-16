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

## Hata ve iddia sınırı

Eksik giriş `TKEEP` değeri sticky hata üretir. FFT olayları PHASE-06C sözleşmesinin
sticky durum bitlerinde korunur. DMA completion yalnız interrupt/driver tarafından
ileride doğrulanabilir; blok tasarımının varlığı PetaLinux, driver, kart çalışması
veya canlı HackRF sonucu değildir.
