# PHASE-06F FFT Lineer Güç RTL Sözleşmesi

## Sayısal giriş

Giriş, PHASE-06D tarafından doğrulanan 64 bit external FFT AXI4-Stream payload'ıdır:

- `s_axis_tdata[28:0]`: signed 29 bit I, `SQ14.15`,
- `s_axis_tdata[31:29]`: I sign-extension padding,
- `s_axis_tdata[60:32]`: signed 29 bit Q, `SQ14.15`,
- `s_axis_tdata[63:61]`: Q sign-extension padding.

RTL yalnız `[28:0]` ve `[60:32]` alanlarını signed değer olarak çıkarır. 32 bit fiziksel lane padding'i aritmetik genişliği değiştirmez.

## Exact power çıkışı

Her kabul edilen bin için:

`m_axis_tdata = unsigned(I_int × I_int + Q_int × Q_int)`

uygulanır. Signed kod aralığı `-268435456..268435455` olur. Her kare 57 bit unsigned, toplam 58 bit unsigned'dır. Çıkış `UQ28.30` biçiminde ve 30 kesir bitlidir. Erişilebilir integer aralığı `0..144115188075855872` (`0..2^57`) olur. Çıkış portu `logic [57:0]` olur.

Hesap exact'tır: saturation, clipping, rounding, truncation, block exponent, frame normalization veya veri-bağımlı scaling yoktur.

## AXI4-Stream

- Input: 64 bit `TDATA`, `TVALID/TREADY`, `TLAST`, 12 bit `XK_INDEX`.
- Output: 58 bit unsigned `TDATA`, `TVALID/TREADY`, korunmuş `TLAST`, korunmuş 12 bit `XK_INDEX`.
- Bir örnek yalnız `TVALID && TREADY` ile kabul edilir veya çıkarılır.
- Output stall sırasında `TDATA/TLAST/XK_INDEX` byte ve bit düzeyinde sabit kalır.
- Reset bütün pipeline valid state'ini temizler; reset sırasında output valid değildir.
- Ardışık frame'ler bubble zorunluluğu olmadan kabul edilir.

## Pipeline

Üç elastic register aşaması operand, square ve sum/output state'ini taşır. Hazır downstream altında input acceptance edge ile output-valid observation arasında iki clock interval vardır. Pipeline dolduktan sonra one-sample-per-cycle kabul ve çıktı kapasitesi vardır. Backpressure latency'ye transfer bekleme süresi ekleyebilir fakat sıra, TLAST ve index değiştirmez.

## Doğrulama

Self-checking Icarus testi aşağıdakileri zorunlu olarak doğrular:

- integer sonuçta sıfır mismatch,
- pozitif/negatif extrema ve `2^57` worst-case toplam,
- gerçek PHASE-06D AMD FFT çıktılarına tam uyum,
- reset, backpressure, stall stability, ardışık frame, no-drop/no-duplication,
- TLAST ve `XK_INDEX` korunumu,
- iki-clock unstalled pipeline latency,
- iki temiz koşuda deterministik capture ve normalized evidence.

## Kapsam dışı

Bu çıktı PSD değildir. `N`, sample rate, Hann coherent gain/window power/ENBW bölmesi, `fftshift`, dBFS, dBFS/Hz, averaging ve kalibrasyon uygulanmaz. Post-power synthesis/timing, bitstream, hardware ve detector ayrı fazlardır.
