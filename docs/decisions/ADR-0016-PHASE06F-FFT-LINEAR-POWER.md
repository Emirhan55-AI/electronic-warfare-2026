# ADR-0016 — PHASE-06F FFT Çıkışı Lineer Güç RTL

## Durum

Kabul edildi ve doğrulandı. Sayısal sözleşme RTL ve test sonuçları görülmeden önce dondurulmuş, uygulama daha sonra bütün işlevsel kapıları geçmiştir.

## Karar

PHASE-06E sonrasındaki en küçük kontrollü DSP adımı **PHASE-06F — FFT Çıkışı Lineer Güç RTL ve Sabit Nokta Sözleşmesi** olur. Faz, PHASE-06D dış FFT akışındaki her natural-order kompleks bin için yalnız

`P_int[k] = I_int[k]^2 + Q_int[k]^2`

işlemini uygular. PSD normalizasyonu, `fftshift`, dB dönüşümü, averaging ve PHASE-03 `regional` detector ayrı sonraki kontrollü adımlardır.

## Dondurulmuş aritmetik

PHASE-06D dış payload'ında I ve Q ayrı 32 bit sign-extended lane'lerde taşınır; gerçek sayısal değer her lane'in düşük 29 bitindeki signed `SQ14.15` alandır. Power RTL üstteki fiziksel padding bitlerini yeni bir 32 bit sayı biçimi olarak karesini almaz.

Signed 29 bit integer kod aralığı `[-2^28, 2^28-1]` olur. En büyük mutlak kod `-2^28` değerindedir:

- `(-2^28)^2 = 2^56`; tek kare için minimum unsigned genişlik 57 bittir,
- iki bileşen de minimum negatifken `I²+Q² = 2^57`; bu uç değeri temsil eden minimum unsigned toplam genişliği 58 bittir,
- gerçek değer yorumu `P_real=P_int/2^30` olur; sonuç `UQ28.30` biçimindedir,
- erişilebilir exact aralık `0..2^57` integer kodu, yani `0..2^27` gerçek değeridir.

58 bitten daha dar çıktı iki-minimum uç durumunu kaybeder. Saturation, rounding, truncation veya gizli ölçekleme uygulanmaz; 58 bit exact toplamda matematiksel overflow mümkün değildir.

## AXI ve latency kararı

Giriş payload'ı 64 bit FFT I/Q, `TLAST` ve 12 bit natural `XK_INDEX`; çıkış payload'ı 58 bit unsigned power, aynı `TLAST` ve aynı index olur. Aktarım yalnız `TVALID && TREADY` ile gerçekleşir. Reset synchronous active-low'dur. Stall sırasında output power/TLAST/index sabit kalır; frame ve sample sırası korunur.

Datapath üç elastic register aşaması kullanır: operand capture, iki paralel exact square ve exact sum/output. Hazır downstream altında giriş kabul kenarından output-valid gözlemine iki clock interval latency verir ve her clock bir örnek kabul edebilir. Multiplication inference-compatible synthesizable SystemVerilog olarak yazılır; belirli DSP48 sayısı bu işlevsel fazda zorlanmaz veya iddia edilmez.

## Golden katmanları

Üç referans ayrıdır:

1. PHASE-02 NumPy floating spectrum/power algoritmik referansı,
2. PHASE-06D AMD bit-accurate C-model/XSim ile doğrulanan gerçek FFT integer çıktısı,
3. PHASE-06F Python arbitrary-precision exact integer square-and-sum modeli.

PHASE-06F RTL, hem bağımsız extrema vektörleri hem de 11 frame/45.056 gerçek PHASE-06D FFT sonucu üzerinden üçüncü katmanla sıfır toleransla karşılaştırılır.

## Timing ve kapsam sınırı

PHASE-06E'nin `WNS=+0.037 ns` sonucu yalnız önceki FFT top'una aittir ve büyük timing marjı değildir. Power RTL eklendikten sonra 100 MHz timing yeniden doğrulanmış sayılmaz. Yeni genişletilmiş top için gerçek Vivado synthesis/implementation/timing ayrı bir sonraki implementation kapısında çalıştırılmalıdır.

PSD, Hann/FFT yeniden uygulaması, detector RTL, bitstream, ZedBoard, canlı HackRF, DMA/Ethernet, UI ve hardware bu fazın kapsamı dışındadır.

## Doğrulanan sonuç

Bağımsız Python modeli, 12 extrema/küçük değer vektörü ve 11 frame içindeki 45.056 gerçek PHASE-06D AMD FFT sonucu için exact power üretmiştir. Self-checking Icarus koşusu toplam 45.068 sonucu sıfır mismatch ile doğrulamış; iki-clock latency, reset flush, 11.520 input/output stall, output stability, TLAST, XK_INDEX, ardışık frame, no-drop ve no-duplication kapılarını geçmiştir. İki temiz compile/simulation koşusunun normalized sonucu byte-identical'dır.

Bu işlevsel doğrulama post-power synthesis, DSP48 kullanımı, 100 MHz timing, bitstream veya hardware sonucu değildir.
