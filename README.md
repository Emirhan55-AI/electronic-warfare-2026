# TEKNOFEST 2026 Elektronik Harp FPGA Projesi

Bu repository, TEKNOFEST 2026 Elektronik Harp Yarışması için FPGA merkezli bir Elektronik Harp prototipinin mühendislik temelidir. Planlanan görev sırası sinyal tespiti, parametre çıkarımı, genlik tabanlı yön bulma, yaklaşık konum belirleme, analog amatör telsiz izleme/dinleme ve kontrollü ET/aldatma deneyleridir.

## Referans sistem

Bağlayıcı donanım 2 adet HackRF One + PortaPack H2, bir ZedBoard Zynq-7000 (P/N 410-248), laptop, geniş bant omni antenler, alt/orta bant teleskobik anten, FOX 727 dual-band Yagi, üst bant yönlü UWB antenler, GPS L1 aktif anteni ve gerekli RF kablo/adaptörlerinden oluşur.

Hedef veri yolu şöyledir:

`SigMF veya HackRF-1 → PC → Gigabit Ethernet → ZedBoard PS → DDR/AXI DMA → ZedBoard PL`

HackRF-1 ED/RX ve canlı I/Q kaynağı, laptop USB erişimi/veri aktarımı/kayıt/kullanıcı arayüzü, ZedBoard PS ağ-kontrol-DDR aktarımı ve ZedBoard PL gerçek FPGA DSP işlemleri için planlanmıştır. HackRF-2 yalnızca ileride güvenli, kontrollü ve izinli ET/TX deneylerinde kullanılacaktır.

Korunan tespit yaklaşımı `I/Q → çerçeveleme → Hann → 4096 FFT → PSD → üstel ortalama → OS-CFAR → komşu hücre birleştirme → aday sinyaller` zinciridir. Bu zincir hedef mimaridir; henüz uygulanmış değildir.

## Mevcut durum

Mevcut faz yalnızca **PHASE-00 — Repository ve mühendislik temeli** aşamasıdır. Henüz DSP, RTL, RF alma/verme, yön bulma, konum belirleme, demodülasyon, karıştırma veya aldatma işlevi uygulanmamıştır.

## Dizinler

- `docs/`: Mimari, karar, gereksinim, yol haritası ve güvenlik belgeleri.
- `rtl/`: İleride geliştirilecek FPGA veri yolu; PHASE-00'da kaynak kod içermez.
- `reference/`: İleride geliştirilecek yazılım referans modelleri.
- `verification/`: İleride eklenecek donanım ve model doğrulama varlıkları.
- `host/`: İleride geliştirilecek PC/ZedBoard ana sistem yazılımı.
- `datasets/`: İleride tanımlanacak kayıtlı test verileri ve veri sözleşmeleri.
- `scripts/`: PHASE-00 ortam envanteri ve repository doğrulama araçları.
- `tests/`: Repository sözleşmesi testleri.
- `results/evidence/phase00/`: PHASE-00 makine tarafından okunabilir kanıtları.

## Doğrulama

```text
python scripts/verify_phase00.py
```
