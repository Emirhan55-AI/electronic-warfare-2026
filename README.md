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

PHASE-04; spektral merkez/gözlenmiş taşıyıcı, bant sınırları, göreli güç/bant içi SNR ve sınırlı `Analog / Sayısal / Belirsiz` ayrımı için sabit sahne ve yöntem karşılaştırması uygular. R1, R2 ve D1 başarısızlık kanıtları tarihsel olarak korunur. E1 çalışması confirmed olaya bağlı, operatörce açıkça onaylanan span içinde dört bounded frame kullanan alan-bazlı ölçüm altyapısını ve iki çalışma alanlı arayüzü kurmuştur; ancak binding ve OOS kapılarında hiçbir alan doğrulanmamıştır. Bu nedenle `phase04e1` profili yoktur, parametre sayıları gösterilmez ve çalışma zamanı yalnız doğrulanmış PHASE-03 `regional` tespit profiline döner. İşlem frame-local'dır; kesintisiz kanal alıcısı veya genel modülasyon tanıma değildir.

İşlevler yalnız kayıtlı veya sentetik I/Q üzerinde floating-point referans işlemedir. PHASE-08A kapsamında HackRF-1 RX için bounded, mock edilebilir host acquisition adaptörü hazırlanmıştır; gerçek cihaz, canlı I/Q ve RF performansı henüz çalıştırılmamış ve kanıtlanmamıştır. RF alma/verme yeteneği, dBm, FPGA/PL, ZedBoard aktarımı, dinleme/demodülasyon, yön/konum, karıştırma veya aldatma iddiası değildir. Arayüzde bu yeteneklere ait sahte durum bulunmaz.

## Dizinler

- `docs/`: Mimari, karar, gereksinim, yol haritası ve güvenlik belgeleri.
- `rtl/`: İleride geliştirilecek FPGA veri yolu; henüz RTL uygulaması içermez.
- `reference/`: SigMF/spektrum, detector/temporal olay ve PHASE-04 frame-local ile operatör destekli parametre modelleri; E1 alanları yalnız alan-bazlı profil bağı geçerse etkinleşir.
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
- `datasets/external/`: Repository dışında tutulan gerçek kayıtlar ve yerel kesitler için kullanım/Git politikası; gerçek ISM datası repository'ye eklenmez.
- `scripts/`: Faz doğrulayıcıları, fixture/kesit araçları, detector/parametre seçicileri ve gerçek UI renderer'ları.
- `tests/`: Repository, SigMF, DSP, detector/parametre istatistiği, işlem profili, bounded worker, Unicode, görsel durum ve performans testleri.
- `results/evidence/phase00/`: PHASE-00 makine tarafından okunabilir kanıtları.
- `results/evidence/phase01/`: Fixture manifesti ve PHASE-01 doğrulama kanıtları.
- `results/evidence/phase02/`: Golden spektrum, sabit sıralı doğrulama özeti ve görsel inceleme kanıtları.
- `results/evidence/phase03/`: Detector karşılaştırması, golden tespit, sabit doğrulama özeti ve yedi gerçek UI görüntüsü.
- `results/evidence/phase04/`: Başarılı veya başarısız parametre karşılaştırması ile golden/doğrulama özeti; yedi gerçek UI görüntüsü yalnız tam başarıda üretilir.
- `results/evidence/phase04e1/`: E1 golden ölçümleri, binding/OOS ham sonuçları, alan kararları, doğrulama özeti ve gerçek fallback arayüz görselleri.
- `results/evidence/phase08a/`: Gerçek donanım ve canlı RX çalıştırılmadan üretilen acquisition sözleşmesi, mock test ve dürüst UI kanıtları.

## Doğrulama

```text
python -B scripts/generate_phase01_fixture.py --check
python -B scripts/select_phase04_profile.py --evaluate
python -B scripts/select_phase04_profile.py --check
python -B scripts/verify_phase04.py --check
python -B -m unittest discover -s tests -v
```
