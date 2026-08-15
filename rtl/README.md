# RTL

`phase06a/`, vendor-bağımsız SystemVerilog ile `ci8` AXI4-Stream giriş buffer'ı, 4096 örnek frame sözleşmesi, kompleks güç ve frame istatistikleri temelini içerir. Aynı dizindeki self-checking testbench deterministik PHASE-01 vektörlerini ve protokol köşe durumlarını kullanır.

Bu temel FFT, Hann, detector, DMA, Ethernet, canlı HackRF veya kart üstü ZedBoard sonucu değildir. Mevcut makinede SystemVerilog simülatörü bulunmadığında RTL yalnız hazırlanmış kabul edilir; sentezlenmiş, simüle edilmiş veya FPGA'da doğrulanmış sayılmaz.

`phase06b/`, PHASE-06A `axis_skid_buffer` altyapısını kullanarak signed `ci8` örnekleri dondurulmuş UQ1.15 periyodik Hann katsayılarıyla çarpar ve bileşen başına SQ1.15 olan 32 bit AXI4-Stream çıkış üretir. Çekirdek hazır downstream altında çevrim başına bir örnek ve bir çevrim kabulden-valid gecikmesi hedefler; gerçek sonuç yalnız self-checking RTL simülasyonuyla raporlanır.

PHASE-06B gerçek 4096 FFT, AMD/Xilinx IP, FFT sonrası güç veya `regional` detector değildir. Katsayı belleği deterministik izlenen `.mem` verisidir; otomatik HDL üretimi değildir. Sentez, implementation, timing, resource utilization ve ZedBoard çalışması ayrıca doğrulanmadan mevcut sayılmaz.

`phase06c/`, fixed 4096 forward/natural-order/unscaled full-precision AMD FFT mimari varsayımını çevreleyen vendor-independent AXI/config/event wrapper'ını içerir. Üretim wrapper'ı gerçek IP'yi instantiate etmez. Testbench'teki `fft_ip_transport_stub` yalnız sample sırası ve kontrol plumbing'i için sign-extension cevabı verir; FFT hesaplamaz.

PHASE-06C Icarus sonucu yalnız wrapper simulation'dır. Gerçek AMD FFT IP generation, XCI, C-model/XSim, vendor latency, lineer güç, detector, synthesis, implementation, timing, resource utilization ve ZedBoard çalışması ayrıca doğrulanmadan mevcut sayılmaz.

`phase06d/`, PHASE-06C dış sözleşmesini Vivado 2025.2 ile üretilmiş gerçek `xilinx.com:ip:xfft:9.1` Rev. 15 XCI'sine bağlar. `amd_xfft_adapter` yalnız 29-bit signed output lane padding'ini normalize eder, 16-bit fiziksel TUSER içinden 12-bit `XK_INDEX` alanını çıkarır ve altı vendor event portunu bağlar. Testbench gerçek generated IP'yi kullanır; PHASE-06C transport stub'ı bu simülasyona katılmaz.

AMD bit-accurate C-model ve XSim, PHASE-06C'nin on frame'i ile ek negatif-frekans exact-bin tone'un toplam 45.056 kompleks sonucunda sıfır toleransla bit-eşittir. İki temiz Vivado/XSim koşusu capture ve ölçümlerde deterministiktir. Doğru/erken/eksik/geç TLAST, ardışık frame, backpressure kararlılığı, fiziksel padding ve mid-frame reset doğrulanmıştır. Bu davranışsal vendor sonucu sentez, implementation, timing, resource utilization, ZedBoard, lineer güç, PSD veya `regional` detector sonucu değildir.
