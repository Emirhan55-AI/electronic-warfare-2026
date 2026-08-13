# TEKNOFEST 2026 Elektronik Harp FPGA Projesi

Bu repository, TEKNOFEST 2026 Elektronik Harp Yarışması için FPGA merkezli bir Elektronik Harp prototipinin mühendislik temelidir. Planlanan görev sırası sinyal tespiti, parametre çıkarımı, genlik tabanlı yön bulma, yaklaşık konum belirleme, analog amatör telsiz izleme/dinleme ve kontrollü ET/aldatma deneyleridir.

## Referans sistem

Bağlayıcı donanım 2 adet HackRF One + PortaPack H2, bir ZedBoard Zynq-7000 (P/N 410-248), laptop, geniş bant omni antenler, alt/orta bant teleskobik anten, FOX 727 dual-band Yagi, üst bant yönlü UWB antenler, GPS L1 aktif anteni ve gerekli RF kablo/adaptörlerinden oluşur.

Hedef veri yolu şöyledir:

`SigMF veya HackRF-1 → PC → Gigabit Ethernet → ZedBoard PS → DDR/AXI DMA → ZedBoard PL`

HackRF-1 ED/RX ve canlı I/Q kaynağı, laptop USB erişimi/veri aktarımı/kayıt/kullanıcı arayüzü, ZedBoard PS ağ-kontrol-DDR aktarımı ve ZedBoard PL gerçek FPGA DSP işlemleri için planlanmıştır. HackRF-2 yalnızca ileride güvenli, kontrollü ve izinli ET/TX deneylerinde kullanılacaktır.

Korunan genel tespit yaklaşımı `I/Q → çerçeveleme → Hann → 4096 FFT → PSD → üstel ortalama → OS-CFAR → komşu hücre birleştirme → aday sinyaller` zinciridir. KTR yalnız yarışma görevleri ve bu genel sıralama için referanstır; sayısal performans parametreleri satın alınmış HackRF–ZedBoard–laptop sistemine göre belirlenir.

## Mevcut durum

Mevcut faz **PHASE-02 — Referans spektrum DSP zinciri ve kalıcı operatör uygulamasının ilk sürümü** aşamasıdır. PHASE-00 repository temelini kurmuştur; PHASE-01 `ci8`/`ci16_le` SigMF giriş sözleşmesini ve deterministik fixture'ı oluşturmuştur. PHASE-02 yalnız kayıtlı SigMF çerçevelerini bounded biçimde okuyan Hann/FFT/güç/PSD golden modelini ve bu gerçek sonuçları gösteren Türkçe Windows operatör uygulamasını uygular.

Henüz sinyal tespiti, CFAR, sınıflandırma, parametre çıkarımı, RTL, canlı HackRF, ZedBoard veri aktarımı, RF alma/verme, yön/konum, demodülasyon, karıştırma veya aldatma işlevi uygulanmamıştır. Arayüzde bu yeteneklere ait sahte durum bulunmaz. Gösterilen `dBFS/bin` ve `dBFS/Hz` sonuçları kalibre edilmemiştir ve dBm değildir.

## Dizinler

- `docs/`: Mimari, karar, gereksinim, yol haritası ve güvenlik belgeleri.
- `rtl/`: İleride geliştirilecek FPGA veri yolu; henüz RTL uygulaması içermez.
- `reference/`: PHASE-01 SigMF sözleşmesi ve PHASE-02 floating-point spektrum golden modeli.
- `verification/`: Gelecekteki model ve RTL doğrulama varlıkları için ayrılmış alan.
- `host/`: Türkçe kalıcı operatör uygulamasının PHASE-02 SigMF spektrum sürümü.
- `datasets/fixtures/phase01/`: Repository'de izlenen deterministik sentetik `ci8` golden fixture.
- `datasets/external/`: Repository dışında tutulan gerçek kayıtlar ve yerel kesitler için kullanım/Git politikası; gerçek ISM datası repository'ye eklenmez.
- `scripts/`: Faz doğrulayıcıları, fixture/kesit araçları ve PHASE-02 gerçek UI renderer'ı.
- `tests/`: Repository, SigMF, golden DSP, bounded okuma, operatör uygulaması, Unicode, görsel durum ve performans testleri.
- `results/evidence/phase00/`: PHASE-00 makine tarafından okunabilir kanıtları.
- `results/evidence/phase01/`: Fixture manifesti ve PHASE-01 doğrulama kanıtları.
- `results/evidence/phase02/`: Golden spektrum, sabit sıralı doğrulama özeti ve görsel inceleme kanıtları.

## Doğrulama

```text
python scripts/verify_phase00.py
python scripts/verify_phase01.py
python scripts/verify_phase02.py
```
