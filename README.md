# TEKNOFEST 2026 Elektronik Harp FPGA Projesi

Bu repository, TEKNOFEST 2026 Elektronik Harp Yarışması için FPGA merkezli bir Elektronik Harp prototipinin mühendislik temelidir. Planlanan görev sırası sinyal tespiti, parametre çıkarımı, genlik tabanlı yön bulma, yaklaşık konum belirleme, analog amatör telsiz izleme/dinleme ve kontrollü ET/aldatma deneyleridir.

## Referans sistem

Bağlayıcı donanım 2 adet HackRF One + PortaPack H2, bir ZedBoard Zynq-7000 (P/N 410-248), laptop, geniş bant omni antenler, alt/orta bant teleskobik anten, FOX 727 dual-band Yagi, üst bant yönlü UWB antenler, GPS L1 aktif anteni ve gerekli RF kablo/adaptörlerinden oluşur.

Hedef veri yolu şöyledir:

`SigMF veya HackRF-1 → PC → Gigabit Ethernet → ZedBoard PS → DDR/AXI DMA → ZedBoard PL`

HackRF-1 ED/RX ve canlı I/Q kaynağı, laptop USB erişimi/veri aktarımı/kayıt/kullanıcı arayüzü, ZedBoard PS ağ-kontrol-DDR aktarımı ve ZedBoard PL gerçek FPGA DSP işlemleri için planlanmıştır. HackRF-2 yalnızca ileride güvenli, kontrollü ve izinli ET/TX deneylerinde kullanılacaktır.

Korunan genel tespit yaklaşımı `I/Q → çerçeveleme → Hann → 4096 FFT → PSD → üstel ortalama → OS-CFAR → komşu hücre birleştirme → aday sinyaller` zinciridir. KTR yalnız yarışma görevleri ve bu genel sıralama için referanstır; sayısal performans parametreleri satın alınmış HackRF–ZedBoard–laptop sistemine göre belirlenir.

## Mevcut durum

Mevcut faz **PHASE-01 — SigMF giriş sözleşmesi ve deterministik test verisi** aşamasıdır. PHASE-00 repository temelini kurmuştur. PHASE-01 yalnız `ci8`/`ci16_le` metadata ve binary yerleşim sözleşmesini, deterministik golden fixture'ı ve güvenli harici veri incelemesini uygular. Henüz DSP, FFT, RTL, RF alma/verme, yön bulma, konum belirleme, demodülasyon, karıştırma veya aldatma işlevi uygulanmamıştır.

## Dizinler

- `docs/`: Mimari, karar, gereksinim, yol haritası ve güvenlik belgeleri.
- `rtl/`: İleride geliştirilecek FPGA veri yolu; henüz RTL uygulaması içermez.
- `reference/`: PHASE-01 SigMF sözleşme çözümleyicisi; DSP referans modelleri henüz uygulanmamıştır.
- `verification/`: Gelecekteki model ve RTL doğrulama varlıkları için ayrılmış alan.
- `host/`: İleride geliştirilecek PC/ZedBoard ana sistem yazılımı.
- `datasets/fixtures/phase01/`: Repository'de izlenen deterministik sentetik `ci8` golden fixture.
- `datasets/external/`: Repository dışında tutulan gerçek kayıtlar ve yerel kesitler için kullanım/Git politikası; gerçek ISM datası repository'ye eklenmez.
- `scripts/`: PHASE-00 araçları ile PHASE-01 fixture üreticisi, harici kesit aracı ve verifier.
- `tests/`: Repository, SigMF sözleşmesi, fixture ve opsiyonel harici dataset testleri.
- `results/evidence/phase00/`: PHASE-00 makine tarafından okunabilir kanıtları.
- `results/evidence/phase01/`: Fixture manifesti ve PHASE-01 doğrulama kanıtları.

## Doğrulama

```text
python scripts/verify_phase00.py
python scripts/verify_phase01.py
```
