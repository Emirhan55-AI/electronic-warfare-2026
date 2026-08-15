# TEKNOFEST 2026 Elektronik Harp FPGA Projesi

Bu repository, TEKNOFEST 2026 Elektronik Harp Yarışması için FPGA merkezli bir Elektronik Harp prototipinin mühendislik temelidir. Planlanan görev sırası sinyal tespiti, parametre çıkarımı, genlik tabanlı yön bulma, yaklaşık konum belirleme, analog amatör telsiz izleme/dinleme ve kontrollü ET/aldatma deneyleridir.

## Referans sistem

Bağlayıcı donanım 2 adet HackRF One + PortaPack H2, bir ZedBoard Zynq-7000 (P/N 410-248), laptop, geniş bant omni antenler, alt/orta bant teleskobik anten, FOX 727 dual-band Yagi, üst bant yönlü UWB antenler, GPS L1 aktif anteni ve gerekli RF kablo/adaptörlerinden oluşur.

Hedef veri yolu şöyledir:

`SigMF veya HackRF-1 → PC → Gigabit Ethernet → ZedBoard PS → DDR/AXI DMA → ZedBoard PL`

HackRF-1 ED/RX ve canlı I/Q kaynağı, laptop USB erişimi/veri aktarımı/kayıt/kullanıcı arayüzü, ZedBoard PS ağ-kontrol-DDR aktarımı ve ZedBoard PL gerçek FPGA DSP işlemleri için planlanmıştır. HackRF-2 yalnızca ileride güvenli, kontrollü ve izinli ET/TX deneylerinde kullanılacaktır.

Korunan genel tespit yaklaşımı `I/Q → çerçeveleme → Hann → 4096 FFT → lineer güç → uyarlanabilir eşik → komşu hücre birleştirme → temporal olaylar` zinciridir. KTR yalnız yarışma görevleri ve bu genel sıralama için referanstır; sayısal performans parametreleri satın alınmış HackRF–ZedBoard–laptop sistemine göre belirlenir.

## Mevcut durum

PHASE-04 parametre doğrulaması açık kalırken **PHASE-06E — Vivado Sentez, Kaynak Kullanımı ve Zamanlama Doğrulaması** uygulanmıştır. PHASE-06A SystemVerilog `ci8`/AXI4-Stream frame temelini, PHASE-06B sabit nokta periyodik Hann ve SQ1.15 FFT-facing sınırını, **PHASE-06C — 4096 Nokta FFT Mimarisi, Ölçekleme Sözleşmesi ve AMD IP Wrapper Temeli** ise AMD FFT mimarisi ile vendor-independent wrapper sınırını tamamlayıp dondurmuştur. PHASE-06D, Vivado/XSim 2025.2 ile gerçek FFT IP v9.1 XCI'sini üretmiş ve 45.056 kompleks örnekte vendor C-model ile bit-eşit doğrulamıştır. PHASE-06E aynı gerçek wrapper/IP zincirini `xc7z020clg484-1` üzerinde 100 MHz hedefte sentezleyip route etmiş; setup/hold ve kaynak kullanımını gerçek Vivado raporlarıyla doğrulamıştır. Bitstream üretilmemiş ve kart/hardware çalıştırılmamıştır. PHASE-00 repository temelini kurmuştur; PHASE-01 deterministik giriş fixture'ını, PHASE-02 spektrum golden modelini ve Türkçe operatör uygulamasını, PHASE-03 ise kayıtlı/sentetik I/Q için doğrulanmış `regional` detector profilini oluşturmuştur.

PHASE-04; spektral merkez/gözlenmiş taşıyıcı, bant sınırları, göreli güç/bant içi SNR ve sınırlı `Analog / Sayısal / Belirsiz` ayrımı için sabit sahne ve yöntem karşılaştırması uygular. R1, R2 ve D1 başarısızlık kanıtları tarihsel olarak korunur. E1 çalışması confirmed olaya bağlı, operatörce açıkça onaylanan span içinde dört bounded frame kullanan alan-bazlı ölçüm altyapısını ve iki çalışma alanlı arayüzü kurmuştur; ancak binding ve OOS kapılarında hiçbir alan doğrulanmamıştır. Bu nedenle `phase04e1` profili yoktur, parametre sayıları gösterilmez ve çalışma zamanı yalnız doğrulanmış PHASE-03 `regional` tespit profiline döner. İşlem frame-local'dır; kesintisiz kanal alıcısı veya genel modülasyon tanıma değildir.

PHASE-05, operatörün açıkça seçtiği AM veya NFM zinciriyle deterministik kayıtlı I/Q'dan bounded 48 kHz mono ses ve WAV üretir; otomatik modülasyon sınıflandırması yapmaz. PHASE-06C'nin Icarus transport stub'ı matematiksel FFT değildir; gerçek FFT sonucu PHASE-06D vendor C-model/XSim kanıtına dayanır. PHASE-06E yalnız synthesis/place-route/timing/resource sonucudur. FFT-output lineer güç, PSD, detector, bitstream veya kart üstü FPGA sonucu yoktur. PHASE-08A kapsamında HackRF-1 RX için bounded, mock edilebilir host acquisition adaptörü hazırlanmıştır; gerçek cihaz, canlı I/Q ve canlı analog dinleme henüz çalıştırılmamış ve kanıtlanmamıştır. RF yayın, dBm, ZedBoard aktarımı, yön/konum, karıştırma veya aldatma iddiası yoktur.

## Dizinler

- `docs/`: Mimari, karar, gereksinim, yol haritası ve güvenlik belgeleri.
- `rtl/phase06a/`: Vendor-bağımsız SystemVerilog AXI4-Stream giriş ve frame-istatistik kaynakları ile self-checking testbench; FFT/detector veya kart projesi içermez.
- `rtl/phase06b/`: Vendor-bağımsız sabit nokta Hann datapath'i ve sample-by-sample self-checking testbench; gerçek FFT veya detector içermez.
- `rtl/phase06c/`: Gelecekteki AMD FFT'nin abstract portlarına bağlanan vendor-independent AXI/config/event wrapper'ı ve yalnız test amaçlı non-FFT transport stub'ı.
- `rtl/phase06d/`: Vivado-generated gerçek AMD FFT v9.1 XCI'si, ince fiziksel-port adapter'ı ve gerçek IP kullanan XSim testbench'i.
- `rtl/phase06e/`: Gerçek wrapper/IP zinciri için synthesis top'u, 100 MHz logical-boundary XDC'si ve registered-ready AXI input slice testbench'i.
- `reference/`: SigMF/spektrum, detector/temporal olay, PHASE-04 parametre, Qt-bağımsız bounded AM/NFM monitoring ve PHASE-06A bit-doğru tam sayı RTL golden modelleri.
- `verification/`: Gelecekteki model ve RTL doğrulama varlıkları için ayrılmış alan.
- `host/`: Türkçe kalıcı operatör uygulamasının spektrum, tespit ve kalibre edilmemiş parametre sürümü.
- `host/acquisition/`: HackRF-1 için Qt/DSP bağımsız gerçek CLI ve deterministik test backend'leri, bounded `ci8` capture ve süreç güvenliği.
- `datasets/fixtures/phase04/`: Geçerlilik matrisi, seed, yöntem sırası ve sabit başarı kapılarını içeren parametre sahne kataloğu.
- `profiles/phase04/`: Yalnız bütün zorunlu kapılar ile comparison/digest bağı geçerse oluşturulan validated parametre işlem profili.
- `datasets/fixtures/phase04e1/`: E1 acceptance kapıları, operatör-span sahneleri ve sonuçlardan önce kilitlenen yöntem sözleşmesi.
- `profiles/phase04e1/`: En az bir E1 alanı binding ve OOS kapılarını geçerse oluşturulacak alan-bazlı profil; mevcut değerlendirmede oluşturulmamıştır.
- `datasets/fixtures/phase03/`: Detector bağımsız, sayısal parametreleri sabit sentetik sahne kataloğu.
- `profiles/phase03/`: Benchmark sonucuyla kurulan doğrulanmış Operasyon işlem profili.
- `datasets/fixtures/phase01/`: Repository'de izlenen deterministik sentetik `ci8` golden fixture.
- `datasets/fixtures/phase05/`: Gerçek RF olmayan deterministik AM, NFM ve noise-only SigMF dinleme fixture'ları.
- `datasets/fixtures/phase06a/`: PHASE-01'in dört frame'inden türetilen AXI giriş/golden sonuç vektörleri ve deterministik köşe durumu sözleşmesi.
- `datasets/fixtures/phase06b/`: Dondurulmuş Hann katsayı ROM'u, 10 frame giriş ve 40.960 örneklik bit-doğru FFT-facing golden çıkış.
- `datasets/fixtures/phase06c/`: On 4096-örnek frame için idealize FFT sayısal golden'ı ve ayrı non-FFT wrapper transport vektörleri.
- `datasets/fixtures/phase06d/`: PHASE-06C girişlerini byte-değişmez devralan, negatif frekans tone ekleyen 11 frame ve AMD bit-accurate C-model tam kompleks sonucu.
- `datasets/external/`: Repository dışında tutulan gerçek kayıtlar ve yerel kesitler için kullanım/Git politikası; gerçek ISM datası repository'ye eklenmez.
- `scripts/`: Faz doğrulayıcıları, fixture/kesit araçları, detector/parametre seçicileri ve gerçek UI renderer'ları.
- `tests/`: Repository, SigMF, DSP, detector/parametre istatistiği, işlem profili, bounded worker, Unicode, görsel durum ve performans testleri.
- `results/evidence/phase00/`: PHASE-00 makine tarafından okunabilir kanıtları.
- `results/evidence/phase01/`: Fixture manifesti ve PHASE-01 doğrulama kanıtları.
- `results/evidence/phase02/`: Golden spektrum, sabit sıralı doğrulama özeti ve görsel inceleme kanıtları.
- `results/evidence/phase03/`: Detector karşılaştırması, golden tespit, sabit doğrulama özeti ve yedi gerçek UI görüntüsü.
- `results/evidence/phase04/`: Başarılı veya başarısız parametre karşılaştırması ile golden/doğrulama özeti; yedi gerçek UI görüntüsü yalnız tam başarıda üretilir.
- `results/evidence/phase04e1/`: E1 golden ölçümleri, binding/OOS ham sonuçları, alan kararları, doğrulama özeti ve gerçek fallback arayüz görselleri.
- `results/evidence/phase05/`: Fixture hashleri, AM/NFM clean ve 20 dB golden ölçümleri, doğrulama özeti ve Dinleme UI kanıtları.
- `results/evidence/phase06a/`: Toolchain keşfi, sabit nokta sözleşmesi, golden/Python sonuçları ve varsa RTL simülasyon durumu; unavailable simülatör başarı iddiasına çevrilmez.
- `results/evidence/phase06b/`: Word-length çalışması, bit-doğru Python/RTL sonuçları, AXI/latency ve dürüst uygulanmamış-FFT sınırı.
- `results/evidence/phase06c/`: FFT mimari/sayısal kararları, wrapper Icarus sonucu ve gerçek AMD IP'nin uygulanmadığını açıkça ayıran kanıtlar.
- `results/evidence/phase06d/`: Planlama/toolchain kapısı ile gerçek IP generation, C-model, XSim bit-eşdeğerlik, latency ve event kanıtları; sentez veya donanım kanıtı değildir.
- `results/evidence/phase06e/`: Vivado 2025.2 synthesis, routed implementation, timing, kaynak, warning sınıflandırması ve AXI boundary testinin normalized kanıtları; raw proje veya hardware kanıtı değildir.
- `results/evidence/phase08a/`: Gerçek donanım ve canlı RX çalıştırılmadan üretilen acquisition sözleşmesi, mock test ve dürüst UI kanıtları.

## Doğrulama

```text
python -B scripts/generate_phase01_fixture.py --check
python -B scripts/select_phase04_profile.py --evaluate
python -B scripts/select_phase04_profile.py --check
python -B scripts/verify_phase04.py --check
python -B scripts/generate_phase05_fixtures.py --check
python -B scripts/verify_phase05.py --check
python -B scripts/generate_phase06b_vectors.py --check
python -B scripts/verify_phase06b.py --check
python -B scripts/generate_phase06c_vectors.py --check
python -B scripts/verify_phase06c.py --check
python -B scripts/verify_phase06d.py --check
python -B scripts/verify_phase06e.py --check
python -B -m unittest discover -s tests -v
```
