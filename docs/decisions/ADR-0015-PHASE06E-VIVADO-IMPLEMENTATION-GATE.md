# ADR-0015 — PHASE-06E Vivado Implementation Kapısı

## Durum

Kabul edildi ve doğrulandı. Kabul koşulları implementation sonuçları görülmeden önce dondurulmuş, gerçek Vivado akışı daha sonra bu koşulları geçmiştir.

## Karar

PHASE-06D sonrasındaki ilk kontrollü alt-faz **PHASE-06E — Vivado Sentez, Kaynak Kullanımı ve Zamanlama Doğrulaması** olur. Faz yalnız PHASE-06C/06D FFT wrapper, AXI boundary buffer, fiziksel AMD adapter ve gerçek generated FFT IP hiyerarşisini Vivado 2025.2 ile `xc7z020clg484-1` üzerinde sentezler, yerleştirir, route eder ve raporlar.

Sentezlenen mantıksal top `phase06e_fft_implementation_top` olur. Top; external boundary'de iki-entry registered-ready AXI input slice, `axis_fft_wrapper`, wrapper içindeki iki `axis_skid_buffer`, `amd_xfft_adapter` ve gerçek `phase06d_fft_4096` IP instance'ını içerir. Hann, FFT-output lineer güç/PSD, detector, PS/DMA/Ethernet, UI ve host yazılımı bu hiyerarşiye eklenmez.

## Clock ve I/O varsayımı

Tek primary clock `aclk` için proje timing hedefi **100 MHz**, period **10.000 ns** olarak sonuçlardan önce dondurulur. Bu seçim, generated XCI'nin AXI clock metadata'sındaki `FREQ_HZ=100000000` ve PHASE-06D davranışsal sınırındaki 10 ns clock ile uyumludur. XFFT generation içindeki `CONFIG.target_clock_frequency=250`, IP mimari/optimizasyon girdisidir; PHASE-06E proje timing kabul kriteri değildir ve 250 MHz donanım/Fmax iddiası oluşturmaz.

AXI ve status top portları aynı `aclk` domaininde synchronous kabul edilir. `aresetn` active-low ve `aclk` ile synchronous örneklenir; assert/deassert dış kaynak tarafından bu clock'a hizalanır. Pre-board logical-core ölçümünde bütün data/control giriş ve çıkışlarına `aclk` referanslı 0 ns input/output delay uygulanır. Bu değer bir PCB veya bağlı cihaz gecikmesi iddiası değil, top-port-to-register ve register-to-top-port yollarını timing analizine dahil eden dondurulmuş logical boundary varsayımıdır. Fiziksel package pinleri ve I/O standardı atanmaz.

## Timing kabulü

Timing PASS için koşulların tamamı zorunludur:

- setup WNS `>= 0.000 ns`, setup TNS `= 0.000 ns` ve setup failing endpoint sayısı `0`,
- hold WHS `>= 0.000 ns`, hold THS `= 0.000 ns` ve hold failing endpoint sayısı `0`,
- anlamlı unconstrained synchronous path/endpoint sayısı `0`,
- yalnız bir primary clock; beklenmeyen generated clock veya clock-domain interaction yok,
- CDC kapsamı yoktur; yeni bir clock domaini görülürse faz otomatik PASS sayılmaz.

Hedef sonuç görüldükten sonra düşürülemez. Timing başarısız olursa ilk sonuç korunur ve mühendislik iterasyonu açıkça kaydedilir.

## Synthesis, implementation ve kalite kabulü

Vivado project flow gerçek XCI'yi source olarak kullanır; `synth_1` başarıyla tamamlanır, ardından `opt_design`, `place_design` ve `route_design` içeren `impl_1` route aşamasına kadar tamamlanır. Route status tam routed olmalı, overutilization olmamalı ve blocking DRC/error bulunmamalıdır.

Bu pre-board top için pin LOC ve IOSTANDARD verilmediğinden yalnız `UCIO-1` ve `NSTD-1` critical warning kimlikleri önceden beklenen ve açıklama gerektiren sınıftadır. Bunlar kart/bitstream acceptance değildir. Başka critical warning, error, unrouted net veya route/timing failure blocking'dir. Normal warnings BENIGN veya NEEDS_EXPLANATION olarak kanıta bağlanır.

Kaynak kabulü sabit bir keyfi yüzde tavanı kullanmaz. Post-synthesis ve post-route LUT, LUTRAM, FF, BRAM36/BRAM18, DSP ve BUFG kullanımı gerçek Vivado raporundan alınır; absolute değer ve `xc7z020clg484-1` kapasite yüzdesi kaydedilir. Kullanım device kapasitesini aşamaz ve doğru target part ile raporlanmalıdır. FFT IP katkısı hierarchical raporda ayrıştırılır.

Bitstream generation, pin planning, board constraints, güç analizi, hardware programming ve hardware throughput bu fazın kapsamı dışındadır.

## Kanıt ve determinism

Kanonik Tcl, XDC, top RTL, normalized JSON kanıtı ve verifier/testler repository'de tutulur. `.Xil`, project runs, DCP, generated HDL, journals, logs ve route database transient kalır. Source/XCI/XDC/Tcl hashleri, tool/version, target part ve sabit run kimliği kaydedilir. Fiziksel placement/route dosyalarının byte-identical olması istenmez; normalized metrik/evidence şeması aynı girdiler için deterministik olmalıdır.

## Kapsam sınırı

PHASE-06E, gerçek synthesis/implementation/timing/resource kanıtı üretir fakat ZedBoard veya başka hardware çalıştırması değildir. Lineer güç, PSD, PHASE-03 `regional` detector RTL, HackRF, DMA/Ethernet ve UI sonraki ayrı planlama adımlarıdır.

## Timing iterasyon kaydı

İlk default implementation, dondurulmuş 100 MHz hedefte pin atanmamış logical top'un `configuration_done → s_axis_tready` dış yolunda setup timing'i `WNS=-0.572731 ns` ile kaçırmıştır. Performance strategy aynı yolu `-0.444 ns` düzeyine iyileştirmiş, post-route physical optimization ek kazanç üretmemiştir. Clock veya I/O kabul varsayımı değiştirilmemiştir. External AXI davranışını koruyan iki-entry registered-ready input slice top boundary'ye eklenmiş; input kabulü reset/config tamamlanana kadar kapalı tutulmuş ve `TREADY` IOB register'dan sürülmüştür. Bu iterasyon ana ihlali kaldırmış; direct output skid-buffer register'ından `m_axis_tdata` pinlerine giden beş OBUF yolu en kötü `-0.020185 ns` kalmıştır. Mevcut output register'ları RTL latency değişmeden IOB'a paketleyen XDC placement directive'i eklenmiştir. Dördüncü routed koşu 100 MHz hedefte `WNS=+0.037 ns`, `TNS=0.000 ns`, `WHS=+0.050 ns`, `THS=0.000 ns` ve sıfır failing endpoint ile geçmiştir. İlk başarısız sonuçlar ve nedenleri nihai evidence'da korunur.

## Doğrulanan sonuç

Vivado 2025.2 ile `xc7z020clg484-1` üzerinde synthesis ve route tamamlanmıştır. Toplam 10.093 routable netin tamamı route edilmiş, routing error görülmemiş, check-timing kategorilerinin tamamı sıfır ve tek `phase06e_aclk` domaini temiz bulunmuştur. Post-route kullanım 3.844 Slice LUT, 1.129 LUTRAM, 7.278 register, 14,5 Block RAM tile, 30 DSP48 ve bir BUFG'dir.

Pin/IOSTANDARD içermeyen bu logical pre-board top'ta önceden izin verilen `UCIO-1` ve `NSTD-1` critical warning'leri korunur. `ZPS7-1`, PS içermeyen minimal PL top nedeniyle; `XDCH-2`, dondurulmuş 0 ns min/max logical I/O varsayımı nedeniyle açıklanmıştır. Bitstream üretilmemiş, kart veya başka hardware çalıştırılmamış, power analysis yapılmamıştır.
