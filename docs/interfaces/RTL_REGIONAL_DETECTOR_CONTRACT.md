# PHASE-06G Bölgesel Detector RTL Sözleşmesi

## Algoritmik kaynak

Bağlayıcı algoritma `reference/detection/cfar.py` içindeki PHASE-03 `regional` yöntemidir. Bir frame 4096 natural-order PHASE-06F power hücresidir. Her natural index için `shifted_index = natural_index XOR 12'h800` uygulanır; 16 shifted bölgenin her biri 256 ardışık hücre içerir.

Bir bölgenin sıralanmış değerleri `x[0]..x[255]` ise NumPy ile aynı even-length median

`median = (x[127] + x[128]) / 2`

olur. RTL yarım LSB bilgisini kaybetmemek için exact 59 bit `median_twice=x[127]+x[128]` taşır. Floating PHASE-03 tanımı `noise=median/ln(2)`, `threshold=noise*(-ln(Pfa))` ve strict `power > threshold` kararıdır.

Shifted `0..19` ve `4076..4095` hücreleri değerlendirilmez. `evaluate_center=false` ise shifted 2048 de değerlendirilmez. Dışlanan hücrelerde `evaluated=0`, `detected=0`, noise ve threshold sıfırdır; median metadata'sı bölgeye ait exact değer olarak korunur.

## Sabit nokta

Giriş `power[57:0]`, unsigned `UQ28.30` ve erişilebilir `0..2^57` integer aralığındadır. Katsayılar 24 kesir bitli unsigned tam sayılardır:

| Katsayı | Biçim | Integer |
|---|---:|---:|
| `1/ln(2)` | UQ2.24 / 26 bit | 24.204.406 |
| `-ln(1e-3)` | UQ4.24 / 28 bit | 115.892.902 |
| `-ln(1e-4)` | UQ4.24 / 28 bit | 154.523.870 |
| `-ln(1e-5)` | UQ4.24 / 28 bit | 193.154.837 |
| `(-ln(1e-3))/ln(2)` | UQ5.24 / 29 bit | 167.198.116 |
| `(-ln(1e-4))/ln(2)` | UQ5.24 / 29 bit | 222.930.821 |
| `(-ln(1e-5))/ln(2)` | UQ5.24 / 29 bit | 278.663.526 |

Noise ayrı katsayıyla, detector threshold ise iki aşamalı quantization hatasını önlemek için matematiksel olarak eşdeğer tek birleşik katsayıyla hesaplanır:

`noise_int = round_half_up(median_twice * C_NOISE / 2^25)`

`threshold_int = round_half_up(median_twice * C_COMBINED[pfa] / 2^25)`

Unsigned round-to-nearest uygulanır; exact yarım yukarı yuvarlanır. Truncation ve saturation yoktur. 59×26 noise ve 59×29 threshold çarpımları exact ara genişlikte değerlendirilir. Noise 58 bit, threshold 62 bittir; dondurulmuş erişilebilir giriş aralığında overflow yoktur.

## Pfa ve center yapılandırması

PHASE-03 profilinin doğrulanmış zarfı Pfa `1e-3`, `1e-4`, `1e-5` ve iki `evaluate_center` değeridir. `cfg_pfa_select=0/1/2` sırasıyla bu Pfa değerlerini seçer; `3` geçersizdir. Config yalnız frame'in natural index 0 transferinde örneklenir ve frame boyunca değişmez. Default profil `cfg_pfa_select=1`, `cfg_evaluate_center=1` değeridir.

## AXI4-Stream ve çıkış

Giriş `TVALID/TREADY`, 58 bit power `TDATA`, `TLAST` ve 12 bit natural index taşır. Çıkış yalnız `TVALID && TREADY` ile transfer edilir ve stall boyunca bütün payload/TLAST/metadata sabit kalır:

- original power: 58 bit UQ28.30,
- natural index: 12 bit,
- shifted index: 12 bit,
- `median_twice`: 59 bit,
- regional noise: 58 bit UQ28.30,
- regional threshold: 62 bit UQ32.30,
- evaluated ve detected: birer bit,
- latched Pfa selector: 2 bit,
- latched center policy: 1 bit,
- `TLAST`: natural index 4095 çıktısında bir.

## Tamponlama, latency ve throughput

Tek 4096×58 dual-port frame RAM kullanılır. Tam frame doğrulandıktan sonra 16 bölgenin iki orta rank'ı exact ikili-radix seçimle bulunur; sonra frame natural sırada replay edilir. Bir radix biti için 256 değer iki-state synchronous RAM taramasıyla okunur. İlk gerçek Icarus ölçümünde son input transferinden ilk output-valid transferine 476.131 clock interval görülmüştür.

Collect sırasında bir sample/clock kabul edilebilir. Processing ve replay boyunca yeni input kabul edilmez; ping-pong tampon yoktur. Bu nedenle continuous frame stream sürdürülemez ve frame'ler arasında bounded, deterministik boşluk gerekir. Backpressure replay süresini uzatır fakat sonuçları değiştirmez.

## Reset ve bozuk frame

Active-low synchronous reset partial frame'i, processing state'ini ve pending output'u flush eder. Geçerli frame için index `0..4095`, yalnız index 4095'te TLAST zorunludur. Early TLAST, missing TLAST, late/unexpected index/TLAST veya geçersiz Pfa frame'i discard eder ve sticky frame error kurar. Early TLAST görüldüğünde ya da bilinen 4096 hücre sınırında yeniden frame başına dönülür; başka kayıplarda bir sonraki TLAST'a kadar input tüketilip discard edilerek resync olunur. Bozuk frame output üretmez.

## Kapsam sınırı

Bu blok cell grouping, temporal 2/3, hassas bandwidth/center frequency, PSD, dBFS, direction finding veya localization uygulamaz. PHASE-06G Vivado koşusu synthesis-only resource feasibility'dir; post-detector route veya 100 MHz timing closure değildir.
