# RTL

`phase06a/`, vendor-bağımsız SystemVerilog ile `ci8` AXI4-Stream giriş buffer'ı, 4096 örnek frame sözleşmesi, kompleks güç ve frame istatistikleri temelini içerir. Aynı dizindeki self-checking testbench deterministik PHASE-01 vektörlerini ve protokol köşe durumlarını kullanır.

Bu temel FFT, Hann, detector, DMA, Ethernet, canlı HackRF veya kart üstü ZedBoard sonucu değildir. Mevcut makinede SystemVerilog simülatörü bulunmadığında RTL yalnız hazırlanmış kabul edilir; sentezlenmiş, simüle edilmiş veya FPGA'da doğrulanmış sayılmaz.

`phase06b/`, PHASE-06A `axis_skid_buffer` altyapısını kullanarak signed `ci8` örnekleri dondurulmuş UQ1.15 periyodik Hann katsayılarıyla çarpar ve bileşen başına SQ1.15 olan 32 bit AXI4-Stream çıkış üretir. Çekirdek hazır downstream altında çevrim başına bir örnek ve bir çevrim kabulden-valid gecikmesi hedefler; gerçek sonuç yalnız self-checking RTL simülasyonuyla raporlanır.

PHASE-06B gerçek 4096 FFT, AMD/Xilinx IP, FFT sonrası güç veya `regional` detector değildir. Katsayı belleği deterministik izlenen `.mem` verisidir; otomatik HDL üretimi değildir. Sentez, implementation, timing, resource utilization ve ZedBoard çalışması ayrıca doğrulanmadan mevcut sayılmaz.
