# ADR-0012 — Sabit Nokta Hann ve FFT Arayüz Sınırı

- Durum: Accepted
- Kapsam: PHASE-06B

## Bağlam

PHASE-06A signed `ci8`, AXI4-Stream ve 4096 örnek frame temelini doğrulamıştır. PHASE-02 algoritmik referansı periyodik Hann ve kayan noktalı 4096 FFT kullanır; ancak bu referans PL iç sayı biçimini belirlemez. Gerçek FFT mimarisi ayrıca AMD/Xilinx FFT IP değerlendirmesi gerektirir. Hann bloğunun FFT kararından bağımsız, bit-doğru ve simüle edilebilir bir arayüz sınırı oluşturması gerekir.

## Nicel değerlendirme

Kanonik `w[n]=0,5-0,5cos(2πn/4096)` dizisi için UQ1.10, UQ1.12, UQ1.14, UQ1.15 ve UQ1.16 katsayı adayları; 4096 katsayının tamamı ve signed `ci8` aralığındaki 256 bileşen değeri üzerinde PHASE-02 float64 sonucu ile karşılaştırılmıştır.

UQ1.15 seçiminde katsayı maksimum hatası `1,5251686208472837e-05`, RMS katsayı hatası `8,693498779472143e-06`, SQ1.15 çıkış maksimum hatası `3,0386208056731867e-05 FS` ve RMS çıkış hatası `1,012389739870253e-05 FS` olur. Bütün 256 signed `ci8` bileşen değeri ve 4096 Hann indisi üzerinde `20log10(rms(PHASE-02 float64 çıkış)/rms(SQ1.15 hata))` olarak tanımlanan enumerated RMS signal-to-error oranı yaklaşık `90,8623 dB`'dir. Bu değer ölçülmüş SNR, SINAD, SQNR veya ENOB iddiası değildir. UQ1.16 aynı oranı yalnız yaklaşık `0,88 dB` iyileştirirken 17 bit katsayı depolaması gerektirir. UQ1.15, katsayıyı 16 bitte tutar, merkezde `1,0` değerini tam temsil eder ve 8×17 signed çarpımı Zynq-7000 DSP genişlikleri içinde bırakır. Bu bir kaynak-utilization sonucu değildir; yalnız word-length kararıdır.

## Karar

- Giriş bileşenleri signed 8 bit SQ1.7 olarak yorumlanır; `-128=-1,0`, `127=127/128` olur.
- Hann katsayıları unsigned 16 bit UQ1.15 olur ve `floor(w[n]×32768+0,5)` ile nicemlenir.
- Periyodik simetriyle `n=0..2048` aralığındaki 2049 katsayı repository'de dondurulur; ikinci yarı `4096-n` adresinden okunur.
- Unsigned katsayı signed çarpım için başına sıfır eklenerek 17 bite çıkarılır. Her bileşen çarpımı 25 bit signed kapta tutulur ve ikili noktası 22 kesir bitindedir.
- SQ1.15 çıkış için ürün yedi bit sağa ölçeklenir; en yakına yuvarlama ve tam yarıda sıfırdan uzağa bağlama uygulanır.
- Matematiksel aralık SQ1.15'i aşmadığı için saturation veya wrap uygulanmaz. Bir aralık aşımı model/doğrulama hatasıdır.
- Çıkış `tdata[15:0]=I`, `tdata[31:16]=Q` signed SQ1.15 olur.
- RTL vendor-bağımsız SystemVerilog ve AXI4-Stream olur. Katsayı belleği izlenen deterministik `.mem` dosyasından `$readmemh` ile başlatılır; kayan nokta veya `real` üretim datapath'inde bulunmaz.
- PHASE-06B gerçek FFT uygulamaz. AMD/Xilinx FFT IP, XCI, Vivado entegrasyonu, FFT ölçekleme, FFT sonrası güç ve PHASE-03 `regional` detector sonraki kontrollü PHASE-06 adımlarına bırakılır.

## Sonuçlar

PHASE-02 NumPy modeli algoritmik golden kaynak kalır; PHASE-06B integer Python modeli donanımın bit-doğru kaynağıdır. Icarus simülasyonu Hann RTL'sini doğrulayabilir fakat AMD FFT IP, sentez, implementation, timing, resource utilization veya ZedBoard sonucu göstermez. Otomatik HDL üretildiği iddia edilmez.
