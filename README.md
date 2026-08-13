# TEKNOFEST 2026 Elektronik Harp FPGA Projesi

Bu repository, TEKNOFEST 2026 Elektronik Harp Yarışması için FPGA merkezli bir Elektronik Harp prototipinin mühendislik temelidir. Planlanan görev sırası sinyal tespiti, parametre çıkarımı, genlik tabanlı yön bulma, yaklaşık konum belirleme, analog amatör telsiz izleme/dinleme ve kontrollü ET/aldatma deneyleridir.

## Referans sistem

Bağlayıcı donanım 2 adet HackRF One + PortaPack H2, bir ZedBoard Zynq-7000 (P/N 410-248), laptop, geniş bant omni antenler, alt/orta bant teleskobik anten, FOX 727 dual-band Yagi, üst bant yönlü UWB antenler, GPS L1 aktif anteni ve gerekli RF kablo/adaptörlerinden oluşur.

Hedef veri yolu şöyledir:

`SigMF veya HackRF-1 → PC → Gigabit Ethernet → ZedBoard PS → DDR/AXI DMA → ZedBoard PL`

HackRF-1 ED/RX ve canlı I/Q kaynağı, laptop USB erişimi/veri aktarımı/kayıt/kullanıcı arayüzü, ZedBoard PS ağ-kontrol-DDR aktarımı ve ZedBoard PL gerçek FPGA DSP işlemleri için planlanmıştır. HackRF-2 yalnızca ileride güvenli, kontrollü ve izinli ET/TX deneylerinde kullanılacaktır.

Korunan genel tespit yaklaşımı `I/Q → çerçeveleme → Hann → 4096 FFT → lineer güç → uyarlanabilir eşik → komşu hücre birleştirme → temporal olaylar` zinciridir. KTR yalnız yarışma görevleri ve bu genel sıralama için referanstır; sayısal performans parametreleri satın alınmış HackRF–ZedBoard–laptop sistemine göre belirlenir.

## Mevcut durum

Mevcut faz **PHASE-04 — Çekirdek teknik parametre çıkarımı** aşamasıdır. PHASE-00 repository temelini kurmuştur; PHASE-01 `ci8`/`ci16_le` SigMF giriş sözleşmesini ve deterministik fixture'ı oluşturmuş, PHASE-02 spektrum golden modelini ve Türkçe operatör uygulamasını getirmiş, PHASE-03 kayıtlı/sentetik I/Q için `regional` detector kullanan doğrulanmış tespit profilini oluşturmuştur.

PHASE-04; spektral merkez/gözlenmiş taşıyıcı, bant sınırları, göreli güç/bant içi SNR ve sınırlı `Analog / Sayısal / Belirsiz` ayrımı için sabit sahne ve yöntem karşılaştırması uygular. R1 kurtarma çalışması gerçek PHASE-03 `2-of-3` temporal olaylarını, tarafsız analysis-window adaylarını ve çok-bileşenli bant desteğini kullanır. Validated PHASE-04 profili yalnız bütün katalog kapıları ve comparison/digest bağı geçerse kurulur; başarısız comparison yanında eski bir profil bulunsa bile Operasyon zinciri onu yüklemez. İşlem frame-local'dır; kesintisiz kanal alıcısı veya genel modülasyon tanıma değildir.

İşlevler yalnız kayıtlı veya sentetik I/Q üzerinde floating-point referans işlemedir; RF alma/verme, canlı HackRF gerçek zamanlı çalışma, dBm, FPGA/PL, ZedBoard aktarımı, dinleme/demodülasyon, yön/konum, karıştırma veya aldatma iddiası değildir. Arayüzde bu yeteneklere ait sahte durum bulunmaz.

## Dizinler

- `docs/`: Mimari, karar, gereksinim, yol haritası ve güvenlik belgeleri.
- `rtl/`: İleride geliştirilecek FPGA veri yolu; henüz RTL uygulaması içermez.
- `reference/`: SigMF/spektrum, detector/temporal olay ve PHASE-04 frame-local parametre modelleri ile allowlist çalışma zamanı.
- `verification/`: Gelecekteki model ve RTL doğrulama varlıkları için ayrılmış alan.
- `host/`: Türkçe kalıcı operatör uygulamasının spektrum, tespit ve kalibre edilmemiş parametre sürümü.
- `datasets/fixtures/phase04/`: Geçerlilik matrisi, seed, yöntem sırası ve sabit başarı kapılarını içeren parametre sahne kataloğu.
- `profiles/phase04/`: Yalnız bütün zorunlu kapılar ile comparison/digest bağı geçerse oluşturulan validated parametre işlem profili.
- `datasets/fixtures/phase03/`: Detector bağımsız, sayısal parametreleri sabit sentetik sahne kataloğu.
- `profiles/phase03/`: Benchmark sonucuyla kurulan doğrulanmış Operasyon işlem profili.
- `datasets/fixtures/phase01/`: Repository'de izlenen deterministik sentetik `ci8` golden fixture.
- `datasets/external/`: Repository dışında tutulan gerçek kayıtlar ve yerel kesitler için kullanım/Git politikası; gerçek ISM datası repository'ye eklenmez.
- `scripts/`: Faz doğrulayıcıları, fixture/kesit araçları, detector/parametre seçicileri ve gerçek UI renderer'ları.
- `tests/`: Repository, SigMF, DSP, detector/parametre istatistiği, işlem profili, bounded worker, Unicode, görsel durum ve performans testleri.
- `results/evidence/phase00/`: PHASE-00 makine tarafından okunabilir kanıtları.
- `results/evidence/phase01/`: Fixture manifesti ve PHASE-01 doğrulama kanıtları.
- `results/evidence/phase02/`: Golden spektrum, sabit sıralı doğrulama özeti ve görsel inceleme kanıtları.
- `results/evidence/phase03/`: Detector karşılaştırması, golden tespit, sabit doğrulama özeti ve yedi gerçek UI görüntüsü.
- `results/evidence/phase04/`: Başarılı veya başarısız parametre karşılaştırması ile golden/doğrulama özeti; yedi gerçek UI görüntüsü yalnız tam başarıda üretilir.

## Doğrulama

```text
python -B scripts/generate_phase01_fixture.py --check
python -B scripts/select_phase04_profile.py --evaluate
python -B scripts/select_phase04_profile.py --check
python -B scripts/verify_phase04.py --check
python -B -m unittest discover -s tests -v
```
