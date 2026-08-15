# PHASE-06D AMD FFT Fiziksel Bağlama Sözleşmesi

## Amaç ve sınır

Bu sözleşme, PHASE-06C `axis_fft_wrapper` soyut sınırının Vivado 2025.2 ile üretilen gerçek `xilinx.com:ip:xfft:9.1` Rev. 15 çekirdeğine PHASE-06D içinde nasıl bağlandığını tanımlar. Matematiksel ve dış AXI4-Stream sözleşmesi PHASE-06C'den devralınır. `amd_xfft_adapter` yalnız fiziksel byte padding'ini normalize eder, `XK_INDEX` alanını çıkarır ve altı vendor event sinyalini bağlar; yeni bir FFT algoritması içermez.

## Dondurulmuş generated yapılandırma

- Hedef part: `xc7z020clg484-1`.
- Tek kanal, sabit `N=4096`, runtime N kapalı.
- Fixed-point, 16 bit input bileşeni, 24 bit phase factor.
- Pipelined Streaming I/O, Non-Realtime throttle.
- Forward config: fiziksel 8 bit `s_axis_config_tdata=8'h01`.
- Unscaled full precision, convergent rounding seçeneği.
- Natural-order output, cyclic prefix kapalı, `XK_INDEX` açık, OVFLO kapalı.
- `aresetn` mevcut, `aclken` yok.

Bu listenin tek Tcl kaynağı `scripts/phase06d_ip_config.tcl` dosyasıdır. Kanonik XCI `scripts/generate_phase06d_ip.tcl` ile Vivado tarafından üretilir; elle yazılmaz veya sonradan düzenlenmez.

## Fiziksel portlar ve packing

Gerçek generated çekirdekte config TDATA 8 bit, input TDATA 32 bit, output TDATA 64 bit ve output TUSER 16 bittir. Giriş `TDATA[15:0]=I`, `TDATA[31:16]=Q` signed SQ1.15 düzenini doğrudan kullanır.

Unscaled `N=4096` çıkışında her sayısal bileşen signed 29 bit Q15'tir. Fiziksel I lane'i `[28:0]`, Q lane'i `[60:32]` alanındadır; `[31:29]` ve `[63:61]` bitleri ilgili sign bitinin uzatmasıdır. Adapter bu alanları açıkça signed 32 bit lane'lere normalize eder ve PHASE-06C dış 64 bit sözleşmesini korur.

TUSER içindeki mantıksal `XK_INDEX`, `[11:0]` alanındadır. `[15:12]` padding'i sıfırdır. Output TLAST yalnız natural index `4095` ile kabul edilir. TDATA, TUSER ve TLAST, output `TVALID=1` ve `TREADY=0` iken sabit kalır.

Generated yapılandırmada ayrı bir fiziksel status AXI kanalı dışarı çıkarılmamıştır. Buna rağmen altı event portunun tamamı generated component sınırında mevcuttur ve wrapper sticky bitlerine bağlanır.

## Reset, config ve frame davranışı

Generated interface `aresetn` portunu active-low olarak bildirir; FFT v9.1 reseti `aclk` ile synchronous örneklenir ve vendor kuralındaki en az iki çevrim yerine testbench'te beş tam çevrim düşük tutulur. Her reset sonrasında wrapper önce `8'h01` config handshake'ini tamamlar; harici input kabulü ancak bundan sonra açılır. Mid-frame reset yarım frame'i iptal eder, wrapper config/sticky durumunu temizler ve yeniden config sonrası yeni frame index sıfırdan başlar.

Doğru TLAST accepted sample `4095` üzerindedir. Erken TLAST `event_tlast_unexpected`, sample `4095` üzerinde TLAST eksikliği `event_tlast_missing` üretir. Geç TLAST testi, önce eksik TLAST olayını ve sonraki frame'in erken TLAST olayını ayrı pulse'lar olarak doğrular. TLAST vendor FFT'nin sayım tabanlı frame sınırını belirlemez; yanlış hizayı event olarak bildirir.

## Sayısal kabul ve doğrulama

Aynı 11 frame için AMD v9.1 bit-accurate C-model sonucu ile gerçek generated IP'nin XSim sonucu, 45.056 kompleks output sözcüğünün tamamında sıfır toleransla bit-eşit olmalıdır. PHASE-06C idealize modeli ve PHASE-02 NumPy FFT yalnız karakterizasyon/algoritmik yapı çapraz kontrolüdür.

İki temiz Vivado generation/elaboration/XSim koşusunun capture dosyası ve ölçüm alanları byte-identical olmalıdır. Testbench ardışık frame, deterministik output backpressure, payload kararlılığı, TLAST/index, fiziksel padding, event pulse'ları ve mid-frame reset sonrası temiz frame'i denetler.

## Kapsam dışı iddialar

Bu faz yalnız davranışsal vendor simülasyonudur. Synthesis, implementation, timing, Fmax, resource utilization ve donanım çalıştırması yapılmaz. FFT-output lineer güç/PSD ve PHASE-03 `regional` detector RTL uygulanmaz. Operatör UI ve PHASE-04-E1 capability davranışı değiştirilmez.
