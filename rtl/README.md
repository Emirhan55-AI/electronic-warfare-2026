# RTL

`phase06a/`, vendor-bağımsız SystemVerilog ile `ci8` AXI4-Stream giriş buffer'ı, 4096 örnek frame sözleşmesi, kompleks güç ve frame istatistikleri temelini içerir. Aynı dizindeki self-checking testbench deterministik PHASE-01 vektörlerini ve protokol köşe durumlarını kullanır.

Bu temel FFT, Hann, detector, DMA, Ethernet, canlı HackRF veya kart üstü ZedBoard sonucu değildir. Mevcut makinede SystemVerilog simülatörü bulunmadığında RTL yalnız hazırlanmış kabul edilir; sentezlenmiş, simüle edilmiş veya FPGA'da doğrulanmış sayılmaz.
