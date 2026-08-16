# Uygulama Yol Haritası

Fazlar sıralıdır; bir fazın çıkış kapısı doğrulanmadan ve kullanıcı onayı alınmadan sonraki faza geçilmez.

| Faz | Ad | Çıkış kapısı |
|---|---|---|
| PHASE-00 | Repository ve mühendislik temeli | Repository sözleşmesi, mimari/karar/güvenlik belgeleri, toolchain envanteri ve PHASE-00 doğrulaması başarıyla tamamlanır. |
| PHASE-01 | SigMF giriş sözleşmesi ve deterministik test verisi | Kanonik `ci8` ve çevrimdışı `ci16_le` sözleşmeleri ile sentetik golden fixture zorunlu doğrulamaları geçer; harici veri kontrolü mevcutsa geçer, yoksa kontrollü atlanır. |
| PHASE-02 | Referans spektrum DSP zinciri | Bounded çerçeveleme, Hann, 4096 FFT, güç/PSD ve üstel ortalama floating-point çıktıları deterministik vektörlerle doğrulanır; aynı gerçek sonuçları gösteren kalıcı Türkçe operatör uygulamasının ilk sürümü iki ekran ölçeğinde geçer. |
| PHASE-03 | Sinyal tespiti | Bölgesel, CA-CFAR ve OS-CFAR adayları sabit sahnelerde karşılaştırılır; bütün zorunlu kapıları geçen kanonik yöntem, allowlist bloklarından kurulan doğrulanmış profille kayıtlı/sentetik I/Q üzerinde kaba aday ve bounded temporal olay üretir. |
| PHASE-04 | Parametre çıkarımı | Operatörce onaylanan izole span içinde taşıyıcı çizgisi, emisyon merkezi, OBW99, kalibre edilmemiş göreli güç ve sınırlı Analog/Sayısal/Belirsiz alanları kendi binding ve OOS kapılarını geçer; yalnız geçen alanlar digest bağlı allowlist profiliyle etkinleşir. R1/R2/D1 ve E1 geçmeyen sonuçları yeniden üretilebilir mühendislik kanıtı olarak korunur; PHASE-04 tüm çekirdek alanlar doğrulanana kadar açık kalır. |
| PHASE-05 | Sinyal izleme ve analog dinleme | Kayıtlı/sentetik I/Q üzerinde operatör seçimli AM/NFM zinciri, bounded 48 kHz mono ses ve WAV çıktısı deterministik golden testlerle doğrulanır. |
| PHASE-06 | FPGA RTL DSP ve Zynq PS aday zinciri | Özel RTL dili SystemVerilog ve blok arayüzü AXI4-Stream olur. PHASE-06A–F giriş, Hann, gerçek AMD FFT, implementation ve exact lineer power zincirini; PHASE-06G PHASE-03 `regional` detectorü; PHASE-06H gruplamayı; PHASE-06I PL→PS packet sınırını; PHASE-06J portable PS temporal confirmation çekirdeğini kurmuştur. Görsel profilin otomatik HDL ürettiği iddia edilmez. |
| PHASE-07 | PC–ZedBoard veri aktarımı | Kayıtlı I/Q verisi PC'den Ethernet, ZedBoard PS, DDR/AXI DMA ve PL yoluyla bütünlük ve hız kanıtıyla aktarılır. |
| PHASE-08 | HackRF-1 canlı I/Q ve ED entegrasyonu | HackRF-1 canlı kaynak bloğu uçtan uca ED zincirine ulaşır ve kontrollü alma senaryolarında beklenen adayları üretir. |
| PHASE-09 | Genlik tabanlı yön bulma ve yaklaşık konum | Manuel açı/göreli güç ölçümlerinden yön ve iki bilinen ölçüm noktasından yaklaşık konum, bilinen hedeflerle hata raporu üretecek şekilde doğrulanır. |
| PHASE-10 | ET simülasyonu ve kapalı RF test altyapısı | İletimsiz dalga şekli simülasyonları doğrulanır; kablolu, zayıflatıcılı ve RF olarak kapalı test düzeni güvenlik kontrolünden geçmeden RF TX etkinleştirilmez. |
| PHASE-11 | Sürekli ve arabakışlı karıştırma | Sürekli ve arabakışlı dalga şekilleri önce simülasyonda, ardından yalnız onaylı kapalı RF düzeneğinde güç, spektrum ve görev çevrimi ölçümleriyle doğrulanır. |
| PHASE-12 | Analog telsiz ve GPS L1 aldatma | Analog telsiz ve GPS L1 senaryoları önce iletimsiz simülasyonda, ardından yalnız izinli kablolu/zayıflatıcılı kapalı düzende izole test alıcılarıyla doğrulanır. |
| PHASE-13 | Arayüz, sistem entegrasyonu ve yarışma demosu | Doğrulanmış profil kilidiyle Operasyon ekranında ED görev akışı ve yalnız izin verilen ET gösterimleri uçtan uca çalışır; demo provası, güvenlik kontrol listesi ve kanıt paketi tamamlanır. |

## ET güvenlik kapıları

ET geliştirmesi önce iletimsiz simülasyon ve dalga şekli doğrulamasıyla başlar; ardından kablolu, zayıflatıcılı ve RF olarak kapalı test düzenine geçer. Güvenli test düzeneği kurulup doğrulanmadan RF TX etkinleştirilmez. Açık ortam RF testi yalnız yürürlükteki mevzuat, yarışma komitesi izni ve komitenin belirlediği zaman ile test düzeni altında yapılabilir.

KTR yarışma görevlerinin kaynağı olarak korunur; eski donanımın teknik performans hedefleri bağlayıcı değildir. Referans mimari 2× HackRF One, ZedBoard ve laptoptur.

## Kullanıcı onaylı P0 hızlı kontrol noktası

Yol haritası fazları yeniden sıralanmadan, kullanıcı onayıyla zorunlu yarışma
çekirdeği tek bir `P0 Mandatory EH Core` kontrol noktasında öne alınmıştır. P0;
KTR uyumlu OS-CFAR/parametre/manuel genlik DF host kanıtını, Zynq PS↔AXI
DMA↔Hann/FFT/güç Vivado mimarisini, görev odaklı operatör bağlarını ve yalnız
OFFLINE/LOOPBACK sürekli karıştırma ile analog FM/NFM aldatma taban bantlarını
tamamlar. PHASE-06A–J değiştirilmemiştir; konum, look-through ve GPS L1 P1'e
geçilmeden bekler.

Vivado 2025.2'de 50 MHz P0 tasarımı sentez, route, timing ve bitstream kapılarını
geçmiştir. PetaLinux/ARM, canlı ZedBoard DMA, canlı HackRF ve RF TX
çalıştırılmamıştır. Bu kontrol noktası sonraki faz için otomatik kullanıcı onayı
oluşturmaz.

### P0 Mandatory Closure Block A

Kullanıcının ayrı onayıyla P0 içindeki yalnız üç donanımdan bağımsız zorunlu açık
nokta kapatılır: exponential-noise Pfa denkleminden türetilen adlı OS-CFAR
mühendislik profili, kaba aday spanından ayrı gürültü-referanslı bant estimatorü
ve ortak acquisition sözleşmesi üzerinden çalışan `UNKNOWN`, `JUDGE_BAND`,
`JUDGE_FREQUENCY` hakem modları. Bu blok PHASE-06A–J RTL'yi, Vivado tasarımını,
HackRF/PetaLinux/ET/DF donanım kapsamını değiştirmez ve P1'e geçiş onayı değildir.

**P0 öncesindeki kayıtlı ana açık fazlar: PHASE-04 ve PHASE-06**

PHASE-05 kayıtlı/sentetik I/Q üzerinde operatör seçimli AM/NFM dinleme zincirini doğrulamıştır; bu sonuç PHASE-04 parametre doğrulamasının tamamlandığı anlamına gelmez. PHASE-06A–J tamamlanmış ve dondurulmuştur. PHASE-06J, PHASE-06I ABI v1 packet'ını strict tüketen bounded portable C11 PS temporal çekirdeğini host compile/link ve Python golden eşdeğerliğiyle doğrulamıştır. PetaLinux/ARM, gerçek DMA/driver/device tree, fiziksel birim dönüşümü, post-detector timing ve hardware sonucu değildir. Gerçek canlı HackRF dinleme, PHASE-07, PHASE-08 donanım kabulü ve TX başlatılmamıştır.

## PHASE-06 kontrollü alt-fazları

- **PHASE-06A — SystemVerilog RTL temeli ve bit-doğru golden eşdeğerlik:** `ci8`, AXI4-Stream, 4096 örnek frame ve frame-istatistik temelini kurmuştur.
- **PHASE-06B — Sabit Nokta Hann Pencereleme ve FFT Arayüz Temeli:** PHASE-02 periyodik Hann tanımını dondurulmuş UQ1.15 katsayılarla signed `ci8` girişe uygular, bileşen başına SQ1.15 olan 32 bit AXI4-Stream çıkış üretir ve bir çevrimlik çekirdek gecikmesini bit-doğru Python modeli ile gerçek RTL simülasyonunda doğrular. Gerçek 4096 nokta FFT, AMD/Xilinx FFT IP, FFT sonrası güç ve `regional` detector bu alt-fazda uygulanmaz.
- **PHASE-06C — 4096 Nokta FFT Mimarisi, Ölçekleme Sözleşmesi ve AMD IP Wrapper Temeli:** AMD FFT LogiCORE mimarisini, fixed forward `N=4096`, natural order ve unscaled full-precision Q15 çıkış sözleşmesini dondurur. Vendor-independent SystemVerilog wrapper/config/event sınırı matematiksel FFT yapmayan transport stub ile Icarus'ta doğrulanır. Gerçek AMD IP generation, vendor FFT simulation, synthesis ve hardware uygulanmaz.
- **PHASE-06D — Gerçek AMD FFT IP Entegrasyonu ve Vendor Doğrulaması:** Gerçek AMD/Xilinx FFT LogiCORE, Vivado tarafından üretilen XCI ve simulation products ile PHASE-06C wrapper sınırına bağlanır. Generated config/TDATA/TUSER/TLAST/event/reset portları, AMD bit-accurate C-model ile tam kompleks çıktı ve XSim wrapper/core davranışı doğrulanır; gerçek core ve wrapper+core gecikmeleri ile sürekli frame/backpressure davranışı ölçülür. Vivado/XSim 2025.2 ve `xilinx.com:ip:xfft:9.1` Rev. 15 ile XCI üretilmiş; 11 frame/45.056 kompleks sonuç C-model ve gerçek-IP XSim arasında sıfır toleransla bit-eşit, iki temiz koşuda deterministik doğrulanmıştır. Sentez, implementation, timing, resource utilization, ZedBoard, lineer güç, PSD ve `regional` detector kapsam dışıdır ve çalıştırılmamıştır.
- **PHASE-06E — Vivado Sentez, Kaynak Kullanımı ve Zamanlama Doğrulaması:** PHASE-06C/06D wrapper, AXI skid buffer, fiziksel adapter ve gerçek generated AMD FFT IP'yi içeren en küçük anlamlı top, Vivado 2025.2 ile `xc7z020clg484-1` üzerinde synthesis ve route'a kadar implementation akışından geçirilmiştir. Sonuçlardan önce dondurulan 100 MHz/10.000 ns hedef `WNS=+0.037 ns`, `TNS=0`, `WHS=+0.050 ns`, `THS=0` ve sıfır failing endpoint ile geçmiştir; 10.093 routable netin tamamı route edilmiştir. Post-route kullanım 3.844 LUT, 1.129 LUTRAM, 7.278 register, 14,5 Block RAM tile, 30 DSP48 ve bir BUFG'dir. XFFT generation içindeki 250 MHz target property proje timing hedefi veya Fmax iddiası değildir. Bitstream, kart, hardware ve power analysis kapsam dışıdır ve çalıştırılmamıştır.
- **PHASE-06F — FFT Çıkışı Lineer Güç RTL ve Sabit Nokta Sözleşmesi:** PHASE-06D'nin signed 29 bit `SQ14.15` I/Q bileşenlerinden exact `I²+Q²` hesaplayan, 58 bit unsigned `UQ28.30` AXI4-Stream çıkışını TLAST ve natural XK_INDEX ile koruyan pipelined SystemVerilog bloğu bit-doğru Python modeli ve Icarus ile 45.068 sonuçta sıfır mismatch ile doğrulanmıştır. PSD normalization, detector, post-power synthesis/timing ve hardware bu işlevsel alt-fazda uygulanmamıştır.
- **PHASE-06G — PHASE-03 Bölgesel Detector RTL ve Sabit Nokta Sözleşmesi:** PHASE-06F natural-order `UQ28.30` power frame'ini shifted-index bölgelerine eşler; 16×256 bölgede exact even medianı iki-rank radix selection ile bulur, üç doğrulanmış Pfa ve center politikasını frame başında kilitler, noise/threshold ve strict detection metadata'sını üretir. Bağımsız integer model ile Icarus RTL 20 frame/81.920 hücrede bütün alanlarda bit-exact; float PHASE-03 ile non-boundary kararlarda sıfır mismatch'tir. Gerçek FFT+power+detector top synthesis-only resource fizibilitesi `xc7z020clg484-1` kapasitesini aşmamıştır. Tek frame buffer nedeniyle processing/replay boyunca input durur; continuous frame desteği yoktur. Post-detector implementation, 100 MHz timing, cell grouping, temporal confirmation, parameter extraction ve hardware uygulanmamıştır.
- **PHASE-06H — Tespit Hücresi Gruplama ve Aday Metadata RTL:** PHASE-03 `DetectionPipeline._group` kaynak sözleşmesindeki shifted detected hücreleri `max_gap_bins=1` ile kaba adaylara birleştirir; her aday için inclusive start/end bin, first-max tie policy ile peak bin, exact peak power, peak bölgesinin noise/threshold metadata'sı ve `end-start+1` coarse span üretir. Natural sıradaki detector stream'i iki 676×94 candidate RAM ile shifted sıraya getirir; kesin üst sınır 1352 aday/frame'dir. Empty frame sentinel, malformed frame, reset, backpressure ve TLAST davranışı 13 frame/1.773 AXI record üzerinde Python golden ile Icarus RTL arasında bit-exact doğrulanmıştır. Standalone targeted Vivado synthesis 879 LUT, 251 FF, 6 BRAM tile ve 0 DSP kullanmıştır. Bu çıktı hassas bandwidth değildir; Hz/dB, temporal 2-of-3, PHASE-04 ölçümleri, post-route timing, bitstream ve hardware bu alt-fazın dışındadır. **Tamamlandı ve donduruldu.**
- **PHASE-06I — PL→PS Aday Paket Transportu ve Sürümlemeli ABI:** PHASE-06H candidate stream'ini 64-bit AXI4-Stream üzerinde 32-byte header, 40-byte candidate record ve 32-byte trailer içeren little-endian ABI v1 packet'ına dönüştürür. `uint32` frame ID, count, status, exact integer metadata ve IEEE payload CRC32 ile maksimum 54.144-byte frame sınırı dondurulmuştur. Python encode/decode ve Icarus packetizer 13 packet/8.964 beat'te byte-exact doğrulanmıştır. Hedef boundary interrupt-driven AXI DMA S2MM ve iki bounded DDR buffer'dır; DMA IP/driver/device tree instantiate edilmemiştir. PetaLinux/ARM toolchain hazır olmadığından C ABI/decoder kaynakları hazırlanmış fakat compile/ARM execution ve temporal 2-of-3 uygulanmamıştır. **Tamamlandı ve donduruldu.**
- **PHASE-06J — Zynq PS Temporal Aday Doğrulama ve Frame Association:** Committed PHASE-06I ABI v1 packet'ını little-endian byte decoder ile strict doğrular ve authoritative PHASE-03 `DetectionPipeline._update_tracks` 2-of-3 state machine'ini bounded portable C11 PS çekirdeğine taşır. Previous span ±2 bin positive-overlap association, global deterministic tie order, iki ardışık miss expiry, 64 active/128 ended ring sınırı, empty/reset ve uint32 frame-wrap davranışı 10 sequence/33 frame/1.501 candidate record üzerinde Python golden ile sıfır semantic mismatch vermiştir. Geliştirme host'unda gerçek C compile/link geçmiştir. Yeni PL RTL yoktur; PetaLinux/ARM cross-build, gerçek DMA/driver/device tree, ZedBoard execution, fiziksel Hz/dB/precise bandwidth, throughput iyileştirmesi ve live RF kapsam dışıdır. **Tamamlandı ve donduruldu.**

PHASE-06J sonrasındaki gerçek DMA/PetaLinux integration, ARM/ZedBoard execution, fiziksel birim dönüşümü/PHASE-04 parametre ölçümü ve detector-throughput iyileştirmesi ayrı bir sonraki kontrollü planlama kararına tabidir. PHASE-06J bunları, post-detector timing'i veya hardware çalışmasını mevcut saymaz.

## Erken hazırlık istisnası: PHASE-08A

PHASE-04 ana açık faz olarak kalırken, kullanıcı onayıyla PHASE-08'in yalnız donanımdan bağımsız host hazırlığı `PHASE-08A — HackRF Canlı RX Host Altyapısının Donanımsız Ön Hazırlığı` adıyla erken yürütülür. PHASE-08'in asıl kapsamı değişmez. PHASE-08A yalnız acquisition adaptörü, deterministik mock backend, bounded süreç güvenliği ve dürüst UI durumlarını kapsar. Gerçek cihaz keşfi, gerçek sweep, canlı I/Q, RF performansı ve donanım evidence'ı PHASE-08 donanım kabul turuna aittir. Bu istisna PHASE-06–07'nin başladığı, atlandığı veya tamamlandığı anlamına gelmez.
