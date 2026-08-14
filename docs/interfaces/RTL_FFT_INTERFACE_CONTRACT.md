# PHASE-06C RTL FFT Wrapper Sözleşmesi

## Yetenek sınırı

PHASE-06C, PHASE-06B Hann çıkışı ile gelecekte üretilecek gerçek AMD/Xilinx 4096 FFT arasındaki sayısal ve AXI kontrol sınırını tanımlar. Vendor-independent wrapper uygulanır; Icarus transport stub'ı FFT hesaplamaz. Gerçek AMD FFT IP, XCI, vendor simülasyonu, lineer güç, PSD ve detector kapsam dışıdır.

## Algoritmik golden

PHASE-02 tanımı değişmez:

`X[k] = Σ(x[n] × exp(-j2πkn/4096))`, `n,k=0..4095`.

İleri transform ölçeklenmez. Giriş doğal zaman sırasıdır; dış wrapper çıkışı natural unshifted DFT sırası `k=0..4095` olur. Wrapper içinde `fftshift`, güç veya PSD yoktur.

## Dış giriş

| Alan | Sözleşme |
|---|---|
| Payload | 32 bit; `[15:0]=I`, `[31:16]=Q` |
| Bileşen | signed 16 bit SQ1.15 |
| Frame | 4096 kabul edilmiş kompleks örnek, `n=0..4095` |
| Transfer | Yalnız `s_axis_tvalid && s_axis_tready` |
| TLAST | Geçerli frame'de kabul edilen `n=4095` örneğiyle hizalı |
| Stall | `tvalid && !tready` boyunca payload/TLAST sabit |

PHASE-06A/B malformed-frame politikası upstream için authoritative kalır. Wrapper TLAST'i IP girişine taşır; erken/eksik/geç TLAST'i onarmaz ve geçerli frame olarak yeniden etiketlemez.

## Seçilen gelecek AMD IP varsayımı

| Parametre | Dondurulan değer |
|---|---|
| Product guide | AMD PG109 v9.1 / Vivado 2026.1; gerçek kurulu sürüm gelecekte bağlanacak |
| Channels | 1 |
| Transform length | Fixed 4096; runtime N kapalı |
| Direction | Sistem forward-only; beklenen mantıksal config `0x01` |
| Architecture | Pipelined Streaming I/O |
| AXI mode | Non-Realtime |
| Input width | 16 bit I + 16 bit Q |
| Phase factor width | 24 bit |
| Arithmetic | Unscaled full precision fixed-point |
| Rounding | Convergent |
| Output order | Natural `k=0..4095` |
| XK_INDEX | Etkin, 12 bit |
| BLK_EXP | Devre dışı / uygulanamaz |
| OVFLO | Devre dışı / unscaled full precision için uygulanamaz |
| Cyclic prefix | Kapalı |

PG109 v9.1 bu kabiliyetleri destekler; tablodaki seçimler gerçek AMD IP'nin üretildiği veya portlarının Vivado'da doğrulandığı iddiası değildir. Zynq-7000 aile desteği dokümanda vardır, ancak ZedBoard hedef parçası, seçilen parametre kombinasyonu, gerçek port genişlikleri ve vendor model uyumu gelecekteki Vivado entegrasyonunda doğrulanmalıdır.

## Config kanalı

Wrapper'ın soyut config sınırı `fft_s_axis_config_tdata[7:0]=8'h01` üretir. PG109 mantıksal paketinde tek kanal channel 0 `FWD_INV` alanı bit 0'dadır; `1` forward demektir. Bu nedenle `0x01`, **beklenen mantıksal config payload** olarak doğrudur. Gerçek üretilmiş AMD `s_axis_config_tdata` bus genişliği ve bütün padding/port haritası **henüz doğrulanmamıştır**; Vivado Information/Port Structure çıktısıyla bağlanmalıdır.

Reset bırakıldıktan sonra wrapper `TVALID=1` tutar; soyut IP `TREADY=1` verdiği kenarda config kabul edilir. Config kabul edilmeden dış input `TREADY=0` olur ve ilk input transferi en erken sonraki saat kenarında gerçekleşebilir; bu PG109'un idle core için config handshake'inin ilk data transferinden en az bir saat önce tamamlanması kuralını karşılar. Config her resetten sonra bir kez gönderilir, frame sırasında veya frame'ler arasında runtime reconfiguration yapılmaz. Eksik config giriş akışını kapalı tutar; illegal payload üretim wrapper'ında mümkün değildir. Gerçek core `aresetn` portu kullanılırsa PG109 en az iki aktif reset çevrimi ister; mevcut testbench üç çevrim uygular, fakat gerçek generated reset port varlığı/bağlantısı Vivado'da doğrulanacaktır.

## Sayısal çıkış

Unscaled transform, ikili noktayı 15 kesir bitinde korur. Matematiksel 4096-terimli DFT toplamı `log2(4096)=12` bit büyüme getirir. PG109'un unscaled kuralındaki ek `+1`, kompleks rotasyonun `1+j` gibi büyüklüğü 1'i aşan ara değerini bir kez karşılar. Bu nedenle vendor genişlik artışı 13 bit, sonuç genişliği `16+12+1=29` bittir; “teorik DFT toplam büyümesi 12 bit” ile “vendor fiziksel genişlik artışı 13 bit” birbirine karıştırılmaz.

Repository `SQm.n` gösteriminde `m`, sign biti dahil ikili noktanın solundaki toplam bit sayısıdır. Dolayısıyla sonuç signed 29 bit `SQ14.15` ve sayısal aralık `[-8192, 8192-2^-15]` olur. “29-bit Q15” kısa ifadesi yalnız 15 kesir bitini belirtir. Dış AXI arayüzünde:

- `m_axis_tdata[31:0]`: 29 bit I'nin 32 bite sign-extension değeri; `[31:29]` bitleri `[28]` sign bitine eşittir,
- `m_axis_tdata[63:32]`: 29 bit Q'nun 32 bite sign-extension değeri; lane `[31:29]` bitleri lane `[28]` sign bitine eşittir,
- toplam payload: 64 bit.

PHASE-06C ideal sayısal modeli NumPy unscaled FFT sonucunu Q15 gridine convergent round eder. Bu dış hedef ve hata karakterizasyonudur; AMD C-model bit-doğru çıktısı değildir. Gerçek IP farkı sonraki entegrasyonda ölçülmeden vendor equivalence iddia edilemez.

PG109'daki convergent rounding seçeneği yasaldır, fakat guide kompleks multiplier ve diğer iç word-length reduction noktalarının tümünde aynı rounding kuralının kullanılmadığını açıklar. Bu nedenle “convergent” konfigürasyon seçimi, PHASE-06C NumPy `rint` sonucuyla bit-doğru AMD eşdeğerliği anlamına gelmez.

`m_axis_tuser_index[11:0]`, natural sırada `k=0..4095` mantıksal değerini taşır. PG109, `XK_INDEX` alanını `log2(maximum point size)=12` bit tanımlar ve TUSER alanının sonraki byte sınırına zero-pad edilmesini ister; dolayısıyla gerçek generated TUSER fiziksel genişliği mantıksal 12 bit ile karıştırılmaz ve Vivado'da doğrulanır. Wrapper soyut sınırda yalnız 12 anlamlı biti taşır. Dış `TLAST`, gerçek IP'nin son natural output bini `k=4095` için ürettiği TLAST'tir. Wrapper IP TLAST'ini yeniden üretmez; gelecekteki vendor testleri index/TLAST ilişkisini doğrulamalıdır.

Wrapper ayrı frame numarası üretmez. Frame ordinal'i kabul edilmiş TLAST dizisiyle örtük olarak korunur; XK_INDEX her yeni geçerli output frame'de sıfırdan başlamalıdır. Testbench ardışık frame'lerde bütün indeksleri ve TLAST sınırlarını denetler.

## Backpressure ve buffer sınırı

Wrapper, PHASE-06A `axis_skid_buffer` bloğunu hem IP girişinde hem IP çıkışında kullanır. Dış ve IP transferleri kendi `TVALID && TREADY` el sıkışmalarında gerçekleşir. Stall boyunca payload, TLAST ve XK_INDEX sabit kalır. Wrapper combinational ready/valid döngüsü kurmaz. Config tamamlanınca, hazır abstract IP altında çevrim başına bir örnek geçirilebilir.

Transport stub'ın gecikmesi gerçek FFT latency değildir. Mevcut testbench immediate-response stub ile dış kabul kenarından dış output-valid gözlemine iki çevrimlik wrapper-boundary gecikmesini ölçer. Gerçek IP latency ve tam frame latency gelecekte XSim ile ayrıca ölçülmelidir.

## Status/event politikası

Sticky bit sırası `[5:0]` şöyledir:

1. `[0] event_frame_started`
2. `[1] event_tlast_unexpected`
3. `[2] event_tlast_missing`
4. `[3] event_status_channel_halt`
5. `[4] event_data_in_channel_halt`
6. `[5] event_data_out_channel_halt`

Bitler ilgili event görüldüğünde, eşzamanlı olsalar da aynı çevrimde set olur ve yalnız resetle temizlenir. Unexpected/missing TLAST ve halt olayları entegrasyon hatasıdır; sticky bit tek başına frame'i düşürmez veya geçerli saymaz. Seçilen unscaled modda `event_fft_overflow` portu beklenmez ve bitmap'e dahil değildir. Sistem-level recovery gerçek IP entegrasyon fazında bağlanacaktır. Testbench'teki `6'h3f`, altı stub event girişinin yönlendirilmiş olarak aynı anda bir çevrim sürülmesinden doğar; gerçek AMD event davranışı kanıtı değildir.

## TLAST katmanları

1. PHASE-06B, geçerli upstream frame için `TLAST`'i kabul edilen `n=4095` örneğinde üretir ve malformed-frame politikasının sahibidir.
2. PG109'a göre gerçek AMD core giriş `TLAST`'ini frame uzunluğunu belirlemek için kullanmaz; sabit N sayacıyla karşılaştırıp yalnız unexpected/missing event üretir. Erken/geç/eksik giriş `TLAST`'inin gerçek event zamanlaması gelecekte vendor modelinde doğrulanacaktır.
3. PHASE-06C dış çıkış `TLAST`'i abstract IP çıkışından buffer ile taşır. Gerçek AMD core bu çıkış `TLAST`'ini kendi son output örneğinde üretir. Transport stub yalnız kontrol yolu testi için giriş TLAST'ini deterministik olarak taşır; bu davranış gerçek AMD malformed-frame davranışı olarak yorumlanamaz.

## Üç bağımsız doğrulama katmanı

1. PHASE-02 NumPy float64: algoritmik unscaled forward FFT golden.
2. PHASE-06C Python: seçilen Q15 input, 29-bit unscaled output, ordering ve aday scaling çalışması.
3. SystemVerilog wrapper + transport stub: yalnız AXI/config/reset/TLAST/index/event plumbing.

Stub sign-extended input örneğini deterministik cevap olarak döndürür; FFT değildir ve matematiksel golden yerine kullanılamaz.

## Açık kapsam dışı

Gerçek AMD IP generation/simulation, custom FFT RTL, FFT-output `I²+Q²`, power width, PSD, regional detector, synthesis, implementation, timing, resource utilization, ZedBoard, DMA, Ethernet, canlı HackRF, UI ve PHASE-04-E1 capability değişikliği kapsam dışıdır.
