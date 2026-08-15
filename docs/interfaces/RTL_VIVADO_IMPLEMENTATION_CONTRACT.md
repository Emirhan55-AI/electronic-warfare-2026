# PHASE-06E Vivado Implementation Sözleşmesi

## Top ve kaynak kümesi

Kanonik top `phase06e_fft_implementation_top` olur. Kaynak kümesi yalnız şunlardan oluşur:

- `rtl/phase06c/rtl/phase06c_pkg.sv`,
- `rtl/phase06a/rtl/axis_skid_buffer.sv`,
- `rtl/phase06c/rtl/axis_fft_wrapper.sv`,
- `rtl/phase06d/rtl/amd_xfft_adapter.sv`,
- `rtl/phase06d/ip/phase06d_fft_4096/phase06d_fft_4096.xci`,
- `rtl/phase06e/rtl/phase06e_fft_implementation_top.sv`,
- `rtl/phase06e/constraints/phase06e_fft_100mhz.xdc`.

Hiyerarşi dış AXI4-Stream input/output portlarını, external iki-entry registered-ready input slice'ı, wrapper içindeki 33 ve 77 bit skid buffer'ları, config/sticky-event mantığını, fiziksel adapter'ı ve gerçek AMD FFT IP'yi içerir. Registered-ready slice reset/config tamamlanmadan input kabul etmez ve AXI payload/TLAST sırasını korur. Vendor IP tek başına sentezlenip proje kaynağı olarak raporlanamaz.

## Clock, reset ve interface

Tek domain `aclk` için `create_clock -period 10.000` uygulanır. Bütün external AXI payload/valid/last/ready/index/status portları aynı clock ile synchronous'tur ve 0 ns logical input/output delay ile timing kapsamındadır. `aresetn` synchronous active-low reset girişidir. External AXI4-Stream sayısal/protokol sözleşmesi PHASE-06C/06D'den byte ve bit düzeyinde değişmeden devralınır.

XFFT `CONFIG.target_clock_frequency=250` değeri IP generation seçimidir. XDC'deki 100 MHz proje kabul hedefini değiştirmez. Bu faz Fmax araması yapmaz.

## Flow ve raporlar

`scripts/run_phase06e_vivado.tcl`, Vivado 2025.2 project flow ile gerçek XCI ürünlerini üretir; synthesis'i ve implementation'ı route aşamasına kadar çalıştırır. En az şu gerçek raporlar transient run alanında üretilir:

- synthesis ve post-route hierarchical utilization,
- synthesis ve post-route timing summary,
- clocks, clock interaction ve check-timing,
- route status,
- DRC ve methodology.

`scripts/verify_phase06e.py` bu raporları normalized JSON evidence'a dönüştürür ve ADR-0015 kabul koşullarını uygular. Raw run path, timestamp, hostname ve makineye özgü mutlak yol kanonik evidence'a yazılmaz.

## PASS koşulları

- `synth_1` ve route tamamlanmış `impl_1` başarılı,
- 100 MHz hedefte setup WNS `>=0`, TNS `0`, failing endpoint `0`,
- hold WHS `>=0`, THS `0`, failing endpoint `0`,
- anlamlı unconstrained path `0`, tek primary clock ve yeni CDC yok,
- tam routed design, blocking DRC/error/critical warning yok,
- `UCIO-1`/`NSTD-1` varsa yalnız pre-board pinlerin bilinçli atanmadığı gerekçesiyle NEEDS_EXPLANATION,
- gerçek post-synthesis/post-route resource kullanımı device kapasitesi içinde,
- source/XCI/XDC/Tcl hash manifesti ve normalized evidence internally consistent.

## İddia sınırı

Başarılı PHASE-06E sonucu yalnız Vivado synthesis, place/route, timing ve resource doğrulamasıdır. Bitstream üretilmez; ZedBoard, hardware, live HackRF, lineer güç/PSD, detector ve end-to-end throughput çalıştırılmaz.

## Kapanış sonucu

Kanonik `implementation4` akışı 100 MHz/10.000 ns hedefte route'a kadar tamamlanmış; setup `WNS=+0.037 ns`, `TNS=0.000 ns`, hold `WHS=+0.050 ns`, `THS=0.000 ns` ve her iki sınıfta failing endpoint sayısı sıfır olmuştur. 10.093 routable netin tamamı route edilmiş ve routing error sayısı sıfırdır. Normalized sonuçlar `results/evidence/phase06e/` altında tutulur; raw Vivado proje/run ürünleri repository kanıtı değildir.
