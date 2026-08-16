# TEKNOFEST 2026 Elektronik Harp FPGA Projesi

Bu repository, TEKNOFEST 2026 Elektronik Harp Yarışması için FPGA merkezli bir Elektronik Harp prototipinin mühendislik temelidir. Planlanan görev sırası sinyal tespiti, parametre çıkarımı, genlik tabanlı yön bulma, yaklaşık konum belirleme, analog amatör telsiz izleme/dinleme ve kontrollü ET/aldatma deneyleridir.

## Referans sistem

Bağlayıcı donanım 2 adet HackRF One + PortaPack H2, bir ZedBoard Zynq-7000 (P/N 410-248), iki bilgisayar, 2 adet Quectel YE0003AA geniş bant omni anten, Diamond SRH-789 teleskobik anten, FOX-727 çift bant Yagi, 800 MHz–6 GHz UWB yönlü anten, 2,4–10,5 GHz yönlü TEM anten ve mevcut RF kablo/adaptör/zayıflatıcılarından oluşur. Anten kullanımı HackRF'ın desteklediği RF aralığıyla sınırlıdır; listede olmayan GNSS veya eski KTR BOM donanımı mevcut kabul edilmez.

Hedef veri yolu şöyledir:

`SigMF veya HackRF-1 → PC → Gigabit Ethernet → ZedBoard PS → DDR/AXI DMA → ZedBoard PL`

HackRF-1 ED/RX ve canlı I/Q kaynağı, laptop USB erişimi/veri aktarımı/kayıt/kullanıcı arayüzü, ZedBoard PS ağ-kontrol-DDR aktarımı ve ZedBoard PL gerçek FPGA DSP işlemleri için planlanmıştır. HackRF-2 yalnızca ileride güvenli, kontrollü ve izinli ET/TX deneylerinde kullanılacaktır.

Korunan genel tespit yaklaşımı `I/Q → çerçeveleme → Hann → 4096 FFT → lineer güç → uyarlanabilir eşik → komşu hücre birleştirme → temporal olaylar` zinciridir. KTR yalnız yarışma görevleri ve bu genel sıralama için referanstır; sayısal performans parametreleri satın alınmış HackRF–ZedBoard–laptop sistemine göre belirlenir.

## Mevcut durum

PHASE-04 parametre doğrulaması açık kalırken kullanıcı onaylı **P0 Mandatory EH Core — ED Algorithms, FPGA Runtime and Operator Integration** hızlı kontrol noktası uygulanmıştır. P0; açık parametreli KTR uyumlu OS-CFAR, 2-of-3 doğrulama, taşıyıcı/bant/göreli dBFS/SNR, açıklanabilir Analog/Sayısal/Belirsiz ayrımı, manuel genlik DF, CRC'li PC→ZedBoard IQ sözleşmesi, Türkçe operatör arayüzü ve iletimsiz/loopback ET taban bant motorlarını kapsar. Portable C OS-CFAR host'ta derlenip Python ile 32.768 hücrede sıfır mismatch vermiş; 7 ED, 7 DF, tekli/çoklu/barrage ve FM/NFM loopback fixture kapıları geçmiştir. Bu P0 referansı nihai çalışma zamanı sahibi olarak PS/ARM'ı korur; ARM execution değildir.

Kanonik Vivado 2025.2 tasarımı Zynq PS, AXI DMA, DDR HP yolu, MM2S→Hann→4096 AMD FFT→lineer güç→S2MM, saat/reset ve iki DMA interruptını gerçek blok tasarımında bağlar. İlk 100 MHz denemesi WNS −6,541 ns ile dürüstçe başarısız kaydedilmiş ve bitstream üretmemiştir. HackRF'ın 20 MS/s sınırını 2,5 kat aşan 50 MHz çalışma hedefi WNS +0,258 ns, TNS 0, WHS +0,025 ns ve sıfır route hatasıyla kapanmış; bitstream üretilmiştir. Bu sonuç Vivado sentez/route kanıtıdır; PetaLinux, driver, canlı DMA veya kartta yürütüm değildir.

PHASE-00 repository temelini kurmuştur; PHASE-01–06J tarihsel kanıtları korunur. PHASE-04 R1/R2/D1/E1 başarısızlık kanıtları ve `phase04e1` profilinin yokluğu değiştirilmemiştir; P0 ayrı, açık sözleşmeli zorunlu çekirdektir. PHASE-05 kayıtlı AM/NFM dinleme sonucu korunur. PetaLinux hazır değildir, ARM ve ZedBoard DMA çalıştırılmamıştır. PHASE-08A/P0 RX soyutlaması hazırdır; HackRF araçları bulunmadığından `BLOCKED_TOOLCHAIN` durumundadır ve gerçek cihaz, canlı I/Q ve canlı analog dinleme henüz çalıştırılmamış ve kanıtlanmamıştır. RF yayın yapılmamış, gerçek TX backend'i eklenmemiş, dBm veya RF etki iddiası üretilmemiştir.

Korunan alt-faz adı: **PHASE-06C — 4096 Nokta FFT Mimarisi, Ölçekleme Sözleşmesi ve AMD IP Wrapper Temeli**.

## Dizinler

- `docs/`: Mimari, karar, gereksinim, yol haritası ve güvenlik belgeleri.
- `rtl/phase06a/`: Vendor-bağımsız SystemVerilog AXI4-Stream giriş ve frame-istatistik kaynakları ile self-checking testbench; FFT/detector veya kart projesi içermez.
- `rtl/phase06b/`: Vendor-bağımsız sabit nokta Hann datapath'i ve sample-by-sample self-checking testbench; gerçek FFT veya detector içermez.
- `rtl/phase06c/`: Gelecekteki AMD FFT'nin abstract portlarına bağlanan vendor-independent AXI/config/event wrapper'ı ve yalnız test amaçlı non-FFT transport stub'ı.
- `rtl/phase06d/`: Vivado-generated gerçek AMD FFT v9.1 XCI'si, ince fiziksel-port adapter'ı ve gerçek IP kullanan XSim testbench'i.
- `rtl/phase06e/`: Gerçek wrapper/IP zinciri için synthesis top'u, 100 MHz logical-boundary XDC'si ve registered-ready AXI input slice testbench'i.
- `rtl/phase06f/`: Signed 29 bit FFT I/Q alanlarından 58 bit unsigned exact lineer power üreten pipelined AXI4-Stream RTL ve self-checking Icarus testbench'i.
- `rtl/phase06g/`: Exact 256-cell median, fixed-point regional noise/threshold ve detector metadata'sı üreten frame-buffered AXI4-Stream RTL, self-checking Icarus testbench'i ve synthesis-only integration top'u.
- `rtl/phase06h/`: PHASE-06G detected hücrelerini shifted sırada coarse adaylara birleştiren, bounded candidate RAM kullanan AXI4-Stream RTL, self-checking Icarus testbench'i ve standalone synthesis-only top'u.
- `rtl/phase06i/`: PHASE-06H adaylarını sürümlemeli little-endian DMA-facing 64-bit AXI4-Stream packet'larına dönüştüren vendor-independent packetizer ve self-checking testbench.
- `rtl/p0/`: PHASE-06B/D/F bloklarını yeniden kullanan kanonik AXI4-Stream Hann→FFT→güç runtime top'u ve Vivado modül-reference sarmalayıcısı.
- `ps/phase06i/`: Candidate transport ABI v1 C layout'u ve ilk shape decoder kaynağı.
- `ps/phase06j/`: ABI v1'i byte-wise strict doğrulayan, bounded PHASE-03 2-of-3 association state machine'ini uygulayan ve host'ta gerçek compile/link edilmiş portable C11 PS çekirdeği; ARM/ZedBoard üzerinde çalıştırılmamıştır.
- `ps/p0/`: Açık konfigürasyonlu OS-CFAR ve aday gruplama için portable C11 PS hedef çekirdeği; host'ta doğrulanmış, ARM'de çalıştırılmamıştır.
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
- `datasets/fixtures/phase06f/`: Power extrema vektörleri ve PHASE-06D gerçek FFT sonuçlarından exact integer power golden'ı; PSD normalization içermez.
- `datasets/fixtures/phase06g/`: On beş sentetik detector frame'i ve beş frozen PHASE-06F gerçek-power frame'inden türetilen bit-exact detector giriş/çıkış vektörleri.
- `datasets/fixtures/phase06h/`: On iki sentetik grouping frame'i ile bir frozen PHASE-06G gerçek-detector frame'inin bit-exact candidate giriş/çıkış vektörleri.
- `datasets/fixtures/phase06i/`: Frozen PHASE-06H candidate stream'inden üretilen ABI packet binary'si ve 64-bit AXI golden beat'leri.
- `datasets/fixtures/phase06j/`: Temporal 1/3, 2/3, 3/3, movement, ambiguity, expiry, reset, uint32 wrap ve 1352-candidate sınırı için PHASE-06I ABI packet sequence'leri ve authoritative Python golden olayları.
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
- `results/evidence/phase06f/`: Exact genişlik kanıtı, bağımsız Python sonucu, gerçek FFT entegrasyonu, Icarus AXI/latency ve determinism kanıtları; post-power timing veya hardware kanıtı değildir.
- `results/evidence/phase06g/`: PHASE-03 matematik/median sözleşmesi, katsayı ve mimari çalışması, bit-exact Python/Icarus sonucu, gerçek-power entegrasyonu ve targeted synthesis-only resource fizibilitesi; post-detector timing veya hardware kanıtı değildir.
- `results/evidence/phase06h/`: Authoritative grouping sözleşmesi, bit-exact Python/Icarus candidate sonucu, determinism, throughput ve standalone targeted synthesis-only resource fizibilitesi; implementation, timing veya hardware kanıtı değildir.
- `results/evidence/phase06i/`: Transport seçimi, ABI, Python decode, byte-exact Icarus packetizer, toolchain ve dürüst deferred PS/temporal sınırı; DMA/PetaLinux/hardware kanıtı değildir.
- `results/evidence/phase06j/`: Portable C11 host build/link, strict ABI decoder, Python↔C temporal semantic eşdeğerliği, bounded bellek/karmaşıklık ve dürüst blocked PetaLinux/ARM/hardware sınırı.
- `results/evidence/phase08a/`: Gerçek donanım ve canlı RX çalıştırılmadan üretilen acquisition sözleşmesi, mock test ve dürüst UI kanıtları.
- `results/evidence/p0/`: ED/DF/ET golden sonuçları, başarısız 100 MHz denemesi ve geçen 50 MHz Vivado/bitstream kanıtı.

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
python -B scripts/generate_phase06f_vectors.py --check
python -B scripts/verify_phase06f.py --check
python -B scripts/generate_phase06g_vectors.py --check
python -B scripts/verify_phase06g.py --check
python -B scripts/generate_phase06h_vectors.py --check
python -B scripts/verify_phase06h.py --check
python -B scripts/generate_phase06i_vectors.py --check
python -B scripts/verify_phase06i.py --check
python -B scripts/generate_phase06j_vectors.py --check
python -B scripts/verify_phase06j.py --check
python -B scripts/verify_p0_algorithms.py --check
python -B scripts/verify_p0_df.py
python -B scripts/verify_p0_et.py
python -B scripts/verify_p0_os_cfar.py
python -B scripts/verify_ui_performance.py --check
python -B -m unittest discover -s tests -v
```
