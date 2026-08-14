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
| PHASE-06 | FPGA RTL DSP zinciri | Özel RTL dili SystemVerilog ve blok arayüzü AXI4-Stream olur. PHASE-06A vendor-bağımsız `ci8` giriş, frame sözleşmesi ve frame-istatistik temelini bit-doğru model/testbench ile hazırlar; bu adım FFT veya detector uygulamaz ve simülatör yoksa çalıştırılmış sayılmaz. Sonraki adımlarda AMD/Xilinx FFT IP değerlendirilir ve ilk RTL tespit bloğu PHASE-03 `regional` detectorü olur; her PL bloğunun sabit nokta, gecikme, kaynak ve RTL sonucu ayrıca doğrulanır. Görsel profilin otomatik HDL ürettiği iddia edilmez. |
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

**Mevcut ana açık fazlar: PHASE-04 ve PHASE-06**

PHASE-05 kayıtlı/sentetik I/Q üzerinde operatör seçimli AM/NFM dinleme zincirini doğrulamıştır; bu sonuç PHASE-04 parametre doğrulamasının tamamlandığı anlamına gelmez. PHASE-06A yalnız RTL temelini hazırlar. Gerçek canlı HackRF dinleme, PHASE-06 FFT/detector zinciri, PHASE-07, PHASE-08 donanım kabulü ve TX başlatılmamıştır.

## Erken hazırlık istisnası: PHASE-08A

PHASE-04 ana açık faz olarak kalırken, kullanıcı onayıyla PHASE-08'in yalnız donanımdan bağımsız host hazırlığı `PHASE-08A — HackRF Canlı RX Host Altyapısının Donanımsız Ön Hazırlığı` adıyla erken yürütülür. PHASE-08'in asıl kapsamı değişmez. PHASE-08A yalnız acquisition adaptörü, deterministik mock backend, bounded süreç güvenliği ve dürüst UI durumlarını kapsar. Gerçek cihaz keşfi, gerçek sweep, canlı I/Q, RF performansı ve donanım evidence'ı PHASE-08 donanım kabul turuna aittir. Bu istisna PHASE-06–07'nin başladığı, atlandığı veya tamamlandığı anlamına gelmez.
