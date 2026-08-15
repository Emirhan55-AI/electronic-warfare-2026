# ADR-0014 — PHASE-06D Vendor Doğrulama ve Toolchain Kapısı

- Durum: Accepted
- Kapsam: PHASE-06D planlama ve toolchain kapısı
- Faz: PHASE-06D — Gerçek AMD FFT IP Entegrasyonu ve Vendor Doğrulaması

## Amaç ve tarihsel sınır

PHASE-06D, PHASE-06C'nin matematiksel FFT yapmayan transport stub sınırını gerçek Vivado-generated AMD/Xilinx FFT LogiCORE ile değiştirir ve generated çekirdeği vendor destekli C-model/XSim akışıyla doğrular. PHASE-06A/B/C tamamlanmış ve dondurulmuştur; tarihsel fixture, RTL ve kanıtları değiştirilmez.

Bu ADR yalnız faz kimliğini, kapsamı, araç kapısını ve sonuçlar görülmeden önce kabul politikasını dondurur. Gerçek IP üretilmemiş, XCI oluşturulmamış, PHASE-06D vektörleri AMD C-model veya XSim'de çalıştırılmamış ve wrapper/core entegrasyonu uygulanmamıştır.

## Kapsam

PHASE-06D şunları kapsar:

- gerçek AMD FFT IP generation ve gerçek generated XCI,
- generated HDL/simulation products manifesti ve XCI hash'i,
- generated port/config/TDATA/TUSER/TLAST/event/reset denetimi,
- PHASE-06C wrapper ile gerçek core arasındaki gerekli en ince adapter/binding,
- AMD bit-accurate C-model ve XSim ile tam kompleks çıktı doğrulaması,
- gerçek core ile wrapper+core gecikmesi,
- ardışık frame, sustained transfer, waitstate ve backpressure davranışı,
- doğru, erken, eksik ve anlamlıysa geç input TLAST ile gerçek event zamanlaması,
- deterministik ve katmanları ayrılmış vendor kanıtı.

Synthesis, implementation, place/route, timing, resource utilization, ZedBoard, canlı HackRF, FFT-output `I²+Q²`, PSD, PHASE-03 `regional` detector RTL, DMA, Ethernet, GNSS, ET/TX, UI ve PHASE-04-E1 capability değişikliği kapsam dışıdır.

## Devralınan dış sözleşme

PHASE-06B davranışı değişmez. Gerçek FFT girişi `tdata[15:0]=I`, `tdata[31:16]=Q` yerleşiminde iki signed SQ1.15 bileşen taşıyan 32 bit AXI4-Stream'dir. Transform fixed `N=4096`, forward ve natural time `n=0..4095` girişlidir. Aktarım yalnız `TVALID && TREADY` ile olur; geçerli input TLAST kabul edilen `n=4095` örneğine hizalanır ve stall boyunca TDATA/TLAST sabit kalır.

Amaçlanan dış sonuç her bileşen için signed 29 bit, 15 kesir bitli `SQ14.15`'tir. I ve Q 32 bit lane'lere sign-extend edilerek `[31:0]=I`, `[63:32]=Q` düzeninde 64 bit wrapper payload'ı oluşturur. Çıkış natural unshifted `k=0..4095` olur; wrapper içinde `fftshift` bulunmaz. Mantıksal XK_INDEX 12 bittir. Bu dış sözleşme ancak generated AMD fiziksel portları doğrulandıktan sonra gerçek-IP sonucu sayılır.

## Gerçek araç zinciri ve sürüm kararı

Toolchain kapısı şu yerel bileşenleri doğrudan çalıştırarak veya Vivado Tcl kataloğundan sorgulayarak doğrulamıştır:

- Vivado `2025.2` 64-bit, SW build `6299465`, IP build `6300035`,
- `xvlog`, `xelab` ve `xsim` `2025.2`,
- IP VLNV `xilinx.com:ip:xfft:9.1`,
- Zynq-7000 device verisi; `xc7z020clg484-1` part girdisi katalogda mevcuttur,
- Windows AMD FFT v9.1 bit-accurate C-model paketi ve beraberindeki GMP/MPFR/vendor DLL/import library/header dosyaları,
- Visual Studio Build Tools 2022 C/C++ ortamıyla vendor örnek C-model derleme ve çalıştırma sonucu başarılıdır.

ADR-0013'ün PG109 v9.1 / Vivado 2026.1 değeri mimari çalışma sırasında kullanılan planlama baseline'ıdır. Gerçek yerel araç `2025.2` ve FFT IP `9.1` Rev. 15'tir. Bu fark PHASE-06C tarihini değiştirmez. PHASE-06D, gerçek generated ürün ve port raporlarını 2025.2 ile üretir; ADR-0013'teki bütün AMD'ye özgü fiziksel varsayımları yeniden doğrulama hedefi yapar. Daha sonra 2026.1 veya başka sürüme geçilirse XCI yeniden üretilir, IP revision/VLNV ve port/config farkları yeni addendum ile kaydedilir ve vendor doğrulaması tekrarlanır.

Araçlar varsayılan PATH üzerinde değildir. Tekrarlanabilir komutlar `C:\AMDDesignTools\2025.2\Vivado\settings64.bat` ile kurulan ortamdan veya aynı kurulumun `Vivado\bin` araçlarının açık yollarıyla çalıştırılır.

## Generated-IP doğrulama hedefleri

Generated ürün şu amaçlanan seçimleri ya doğrular ya da kontrollü PHASE-06D değişikliği doğurur: tek kanal, fixed 4096, runtime N kapalı, forward-only, Pipelined Streaming I/O, Non-Realtime, natural output, unscaled full precision, convergent rounding seçeneği, 24 bit phase factor, cyclic prefix kapalı, XK_INDEX açık, BLK_EXP kapalı ve unscaled mimaride OVFLO kapalı.

Gerçek generated port denetimi en az şunları kaydeder:

- kesin hedef part ve IP VLNV/revision,
- `s_axis_config_tdata` fiziksel genişliği, FWD_INV bit konumu ve padding,
- mantıksal `0x01` değerinin gerçek forward config karşılığı,
- config handshake ve reset sonrası ilk input sırası,
- input/output TDATA fiziksel genişlik ve packing'i,
- `m_axis_data_tuser` genişliği, XK_INDEX konumu/padding'i ve stall kararlılığı,
- output TLAST ile `k=4095` hizası,
- altı gerçek AMD event portunun pulse zamanlaması ve sticky wrapper sonucu,
- reset sırasında ve mid-frame reset sonrasındaki gerçek core davranışı.

Generated packing farklıysa yalnız width adaptation, TUSER extraction, config packing, event wiring ve vendor-instance binding içeren en ince PHASE-06D adapter değişikliği yapılabilir. PHASE-06B datapath'i veya PHASE-06C dış sayısal sözleşmesi sessizce değiştirilemez. Bir varsayım geçersizse eski varsayım, gerçek vendor kanıtı, yeni sözleşme, uyumluluk etkisi ve supersession ilişkisi ayrı addendum ile kaydedilir.

## Sonuçlar görülmeden kilitlenen sayısal kabul politikası

Dört referans katmanı ayrı tutulur:

1. PHASE-02 NumPy floating unscaled forward FFT algoritmik golden'dır.
2. PHASE-06C modeli idealize convergent-rounded 29-bit Q15 dış mimari modelidir.
3. Gerçek AMD FFT v9.1 bit-accurate C-model vendor sayısal referansıdır.
4. Gerçek generated AMD FFT'nin XSim çıktısı doğrulanan RTL sonucudur.

Karşılaştırma A — AMD C-model/XSim: Yerel AMD dağıtımındaki header ve API modeli açıkça bit-accurate olarak tanımlar. Aynı input integer kodları ve aynı generated konfigürasyon için her kabul edilen output bininin I/Q integer kodları C-model ile XSim arasında bit-eşit olmalıdır. Tolerans sıfırdır. İlk fark bin/index/bileşen ve iki integer kodla raporlanır. TUSER, TLAST ve event sinyalleri sayısal C-model kapsamına katılmaz; generated RTL protokol kontrolleriyle ayrıca doğrulanır.

Karşılaştırma B — AMD C-model/PHASE-06C mimari model: Bit-eşitlik beklenmez, çünkü AMD iç word-length reduction davranışı ideal NumPy `rint` modeli değildir. Tam kompleks çıktı için maksimum mutlak bileşen hatası ve RMS bileşen hatası input-LSB biriminde raporlanır. PHASE-06C'nin `16 input-LSB / 0,25 input-LSB RMS` proxy baseline'ı kabul kapısı olarak kullanılmaz. Bu katmanın kapanış kapıları doğru N, yön, unscaled binary point, natural order, output range/sign-extension ve vektörün matematiksel yapısal beklentileridir; yeni bir sayısal tolerans sonuç görüldükten sonra eklenemez.

Karşılaştırma C — AMD sonucu/PHASE-02 NumPy: NumPy sonucu signed Q15 input kodlarının float64 unscaled DFT'si olarak korunur. Tam kompleks output üzerinde hata metrikleri raporlanır; bit-eşitlik beklenmez. Pass/fail kapıları doğru forward işareti, natural bin yerleşimi, unscaled büyüklük ilişkisi, sıfır/impulse/DC/tone yapıları ve sonlu/aralık içi sonuçlardır. Ayrı bir algoritmik hata toleransı ancak sonuçlar görülmeden önce yeni, kaynaklı bir karar ile eklenebilir.

PHASE-06D işlevsel sayısal kabulünün zorunlu kapısı Karşılaştırma A'nın tam bit-eşitliğidir. B ve C, yanlış yön/order/scale/config seçimini yakalayan bağımsız mimari ve algoritmik çapraz kontrollerdir.

## Vektör ve protokol planı

PHASE-06C'nin `zero`, `impulse`, `positive_dc`, `negative_dc`, `single_tone`, `two_tone`, `multiple_tones`, `alternating_extrema`, `complex_extrema` ve `representative_hann` fixture'ları byte-değişmez girdi olarak yeniden kullanılır. PHASE-06D kendi alanında deterministic negatif-frekans exact-bin tone ekler ve natural unshifted `N-k` yerleşimini doğrular. Uygun vektörlerde yalnız peak değil 4096 binin bütün kompleks çıktısı karşılaştırılır.

Gerçek core ve wrapper+core gecikmeleri ayrı ölçülür. İlk kabul edilen inputtan ilk output-valid'e ve yararlı olduğunda input-frame sonundan output-frame sonuna çevrim sayıları raporlanır. Backpressure kaynaklı transfer beklemesi core computational latency ile birleştirilmez. Ardışık frame, sustained accepted input rate, input/output waitstate, stall kararlılığı, sample kaybı/tekrarı ve output TLAST/index ilişkisi doğrulanır; simülasyon sonucu Fmax veya kart throughput iddiasına çevrilmez.

## Artifact ve kapanış politikası

IP yalnız Vivado-supported generation akışıyla oluşturulur; XCI elle yazılmaz. Kesin target part, IP VLNV/revision, config parametreleri, generation komutu/project flow, XCI SHA-256 ve generated-product manifesti kanıta bağlanır. `.Xil`, `xsim.dir`, log, journal, waveform ve büyük transient cache/build ürünleri repository dışında veya ignore edilen build alanında tutulur; yalnız açıkça gerekli kanonik IP/generation girdileri izlenir.

PHASE-06D yalnız gerçek generated IP, C-model ve XSim doğrulamalarının tamamı deterministik kanıtla geçtiğinde kapanabilir. Synthesis/resource/timing ayrı sonraki kontrollü fazdır; lineer güç, PSD ve regional detector ondan sonraki ayrı planlama adımlarıdır.

## Kapı sonucu ve uygulama kaydı

Planlama anında gerekli vendor araçları, IP/device kataloğu ve C-model runtime doğrulanmış ve PHASE-06D uygulaması `READY_FOR_IMPLEMENTATION` durumuna getirilmiştir. Bu tarihsel toolchain kapısı `toolchain-gate.json` içinde sonuç görmeden önceki haliyle korunur ve tek başına gerçek IP'nin üretildiği veya FFT'nin çalıştırıldığı anlamına gelmez.

Sonraki PHASE-06D uygulamasında aynı dondurulmuş seçimlerle Vivado 2025.2 tarafından `xilinx.com:ip:xfft:9.1` Rev. 15 XCI üretilmiş, gerçek generated çekirdek PHASE-06C wrapper'a ince adapter ile bağlanmış ve AMD bit-accurate C-model/XSim tam kompleks sonuçları sıfır toleransla doğrulanmıştır. Fiziksel port/padding, AXI backpressure, TLAST olayları, reset ve latency sonuçları ayrı PHASE-06D kanıtlarında tutulur. Bu uygulama kaydı synthesis, implementation, timing, kaynak veya donanım sonucu oluşturmaz.
