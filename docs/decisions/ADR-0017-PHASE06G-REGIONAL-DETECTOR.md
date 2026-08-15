# ADR-0017 — PHASE-06G PHASE-03 Bölgesel Detector RTL ve Sabit Nokta Sözleşmesi

## Durum

Kabul edildi ve doğrulandı. Matematik, median, fixed-point ve eşdeğerlik kapıları RTL sonucu görülmeden önce dondurulmuştur.

## Karar

PHASE-06F sonrasındaki kontrollü adım **PHASE-06G — PHASE-03 Bölgesel Detector RTL ve Sabit Nokta Sözleşmesi** olur. PHASE-03 `regional` detector doğal sıralı exact power akışına SystemVerilog ile uygulanır. Shifted bölge eşlemesi index XOR ile yapılır; FFT veya power verisi yeniden sıralanarak ikinci bir frame kopyası oluşturulmaz.

## Median mimari karşılaştırması

| Aday | Exact | Depolama/latency | Karar |
|---|---|---|---|
| Tam sorting network | Evet | Çok yüksek comparator ve routing baskısı | Reddedildi |
| RAM içinde sequential sort | Evet | Yoğun read/write; basit bounded çözümde karesel worst case | Reddedildi |
| Histogram/binning | Hayır | Küçük fakat PHASE-03 medianını değiştirir | Reddedildi |
| Partial sort/selection | Evet | Daha karmaşık variable control veya geniş comparator ağı | Reddedildi |
| İki-rank ikili-radix selection | Evet | Tek read-only scan datapath'i, bounded 58×256 tarama/bölge | Seçildi |

Seçilen mimari rank 127 ve 128 için bağımsız prefix/rank state'ini aynı RAM okumalarıyla ilerletir. 58 bitin her biri için bütün 256 bölge değeri taranır. Sonuç input değerlerinden biridir; approximate median, truncation veya data-dependent loop bound yoktur.

## Tamponlama kararı

Frame doğruluğunu output öncesinde kesinleştirmek ve malformed frame'de partial detector output üretmemek için 4096×58 tek frame RAM kullanılır. Tampon fill sırasında bir hücre/clock kabul edilir. Median processing ve output replay sırasında input durdurulur. Ping-pong eklenmemiştir; sürekli frame kapasitesi iddia edilmez. Daha yüksek frame rate gerekirse aynı sözleşmeyi koruyan ping-pong ve paralel region engine ayrı kapasite fazıdır.

## Sayısal karar

PHASE-03 medianı iki orta değerin arithmetic mean'idir. `median_twice` exact tutulur. Pfa profile/runtime parametresidir ve doğrulanmış üç-değer envelope iki bit selector ile frame başında örneklenir; arbitrary runtime floating katsayı yoktur.

12, 16, 20, 24, 28 ve 32 fractional-bit katsayı adayları karşılaştırılmıştır. Seçim politikası, birleşik threshold katsayısında `3e-9` altında relative error, noise katsayısında `2e-8` altında relative error, dondurulmuş non-boundary vektörlerde sıfır karar farkı ve RTL ile bit-exact eşdeğerlik sağlayan en küçük adaydır. Bu kapıları ilk geçen aday 24 fractional bittir.

Threshold için iki katsayılı ardışık quantization yerine `(-ln(Pfa))/ln(2)` birleşik katsayısı kullanılır. Noise metadata ayrı `1/ln(2)` katsayısıyla üretilir. Her ikisi exact genişlikli unsigned multiplication ve round-to-nearest/ties-up ile hesaplanır. Equality kararı strict olduğundan `power==threshold` tespit değildir.

## Golden katmanları

Üç bağımsız katman korunur:

1. `reference/detection/cfar.py` PHASE-03 NumPy float64 algoritması,
2. `reference/rtl/regional_detector.py` PHASE-06G integer/bit-true modeli,
3. `rtl/phase06g/rtl/axis_regional_detector.sv` synthesizable RTL.

Bit-true model↔RTL bütün alanlarda sıfır toleranslıdır. Float↔fixed non-boundary detector kararlarında tolerans yoktur. Exact fixed threshold ile eşit ve ±1 integer LSB boundary vektörleri ayrı raporlanır; sonuçtan sonra tolerans üretilmez.

## Resource ve timing sınırı

Targeted Vivado 2025.2 synthesis, `xc7z020clg484-1` üzerinde gerçek PHASE-06E FFT wrapper/IP + PHASE-06F power + PHASE-06G detector top'u için çalıştırılır. Detector-only sayı tüm zincirin fizibilitesi gibi sunulmaz. Synthesis resource sonucu route/timing closure veya hardware sonucu değildir.

PHASE-06E'nin `WNS=+0.037 ns` sonucu detector eklenmiş top'a aktarılmaz. Post-detector 100 MHz timing, implementation, bitstream ve ZedBoard çalışması yapılmadıkça **NOT VERIFIED** kalır.

## Kapsam dışı

Cell grouping, temporal 2/3, parameter extraction, direction finding, localization, PSD/dBFS, PetaLinux/ARM, UI, live HackRF, bitstream ve hardware PHASE-06G kapsamında değildir.
