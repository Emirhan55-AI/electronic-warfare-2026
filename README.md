# TEKNOFEST 2026 Elektronik Harp FPGA Projesi

Bu repository, TEKNOFEST 2026 Elektronik Harp Yarışması için FPGA merkezli bir Elektronik Harp prototipinin mühendislik temelidir. Planlanan görev sırası sinyal tespiti, parametre çıkarımı, genlik tabanlı yön bulma, yaklaşık konum belirleme, analog amatör telsiz izleme/dinleme ve kontrollü ET/aldatma deneyleridir.

## Referans sistem

Bağlayıcı donanım 2 adet HackRF One + PortaPack H2, bir ZedBoard Zynq-7000 (P/N 410-248), laptop, geniş bant omni antenler, alt/orta bant teleskobik anten, FOX 727 dual-band Yagi, üst bant yönlü UWB antenler, GPS L1 aktif anteni ve gerekli RF kablo/adaptörlerinden oluşur.

Hedef veri yolu şöyledir:

`SigMF veya HackRF-1 → PC → Gigabit Ethernet → ZedBoard PS → DDR/AXI DMA → ZedBoard PL`

HackRF-1 ED/RX ve canlı I/Q kaynağı, laptop USB erişimi/veri aktarımı/kayıt/kullanıcı arayüzü, ZedBoard PS ağ-kontrol-DDR aktarımı ve ZedBoard PL gerçek FPGA DSP işlemleri için planlanmıştır. HackRF-2 yalnızca ileride güvenli, kontrollü ve izinli ET/TX deneylerinde kullanılacaktır.

Korunan genel tespit yaklaşımı `I/Q → çerçeveleme → Hann → 4096 FFT → lineer güç → uyarlanabilir eşik → komşu hücre birleştirme → temporal olaylar` zinciridir. KTR yalnız yarışma görevleri ve bu genel sıralama için referanstır; sayısal performans parametreleri satın alınmış HackRF–ZedBoard–laptop sistemine göre belirlenir.

## Mevcut durum

Mevcut faz **PHASE-03 — Uyarlanabilir sinyal tespiti ve doğrulanmış işlem profili** aşamasıdır. PHASE-00 repository temelini kurmuştur; PHASE-01 `ci8`/`ci16_le` SigMF giriş sözleşmesini ve deterministik fixture'ı oluşturmuş, PHASE-02 kayıtlı SigMF için spektrum golden modelini ve Türkçe operatör uygulamasını getirmiştir. PHASE-03 bölgesel sağlam taban, CA-CFAR ve OS-CFAR yöntemlerini sabit sentetik sahnelerde tarafsız karşılaştırır; zorunlu kapıları geçen yöntemi seri hâle getirilebilir doğrulanmış profilden çalıştırır ve kaba adayları bounded temporal olaylara dönüştürür.

Tespit yalnız kayıtlı veya sentetik I/Q üzerinde floating-point referans işlemedir; canlı RF, HackRF gerçek zamanlı çalışma ve FPGA/PL tespiti iddiası değildir. Henüz sınıflandırma, parametre çıkarımı, RTL, ZedBoard veri aktarımı, RF alma/verme, yön/konum, demodülasyon, karıştırma veya aldatma uygulanmamıştır. Arayüzde bu yeteneklere ait sahte durum bulunmaz. Gösterilen `dBFS/bin` ve `dBFS/Hz` sonuçları kalibre edilmemiştir ve dBm değildir.

## Dizinler

- `docs/`: Mimari, karar, gereksinim, yol haritası ve güvenlik belgeleri.
- `rtl/`: İleride geliştirilecek FPGA veri yolu; henüz RTL uygulaması içermez.
- `reference/`: SigMF/spektrum modelleri ile PHASE-03 detector, gruplama, temporal olay ve işlem profili çalışma zamanı.
- `verification/`: Gelecekteki model ve RTL doğrulama varlıkları için ayrılmış alan.
- `host/`: Türkçe kalıcı operatör uygulamasının spektrum ve kayıtlı-I/Q tespit sürümü.
- `datasets/fixtures/phase03/`: Detector bağımsız, sayısal parametreleri sabit sentetik sahne kataloğu.
- `profiles/phase03/`: Benchmark sonucuyla kurulan doğrulanmış Operasyon işlem profili.
- `datasets/fixtures/phase01/`: Repository'de izlenen deterministik sentetik `ci8` golden fixture.
- `datasets/external/`: Repository dışında tutulan gerçek kayıtlar ve yerel kesitler için kullanım/Git politikası; gerçek ISM datası repository'ye eklenmez.
- `scripts/`: Faz doğrulayıcıları, fixture/kesit araçları, detector seçici ve gerçek UI renderer'ları.
- `tests/`: Repository, SigMF, DSP, detector istatistiği, işlem profili, bounded worker, Unicode, görsel durum ve performans testleri.
- `results/evidence/phase00/`: PHASE-00 makine tarafından okunabilir kanıtları.
- `results/evidence/phase01/`: Fixture manifesti ve PHASE-01 doğrulama kanıtları.
- `results/evidence/phase02/`: Golden spektrum, sabit sıralı doğrulama özeti ve görsel inceleme kanıtları.
- `results/evidence/phase03/`: Detector karşılaştırması, golden tespit, sabit doğrulama özeti ve yedi gerçek UI görüntüsü.

## Doğrulama

```text
python scripts/verify_phase00.py
python scripts/verify_phase01.py
python scripts/verify_phase02.py
python scripts/verify_phase03.py --check
```
