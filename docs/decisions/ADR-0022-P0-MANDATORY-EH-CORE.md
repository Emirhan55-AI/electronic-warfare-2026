# ADR-0022 — P0 Zorunlu EH Çekirdeği ve Gerçek Donanım Uyarlaması

- Durum: Kabul edildi
- Kapsam: Tek P0 kontrol noktası
- Önceki doğrulanmış sınır: PHASE-06A–06J dondurulmuştur

## Bağlam

KTR'de yer alan eski `bladeRF`, `KrakenSDR`, Raspberry Pi, çok kanallı faz
uyumlu alıcı ve motorlu yön bulma düzeni satın alınmış donanımı temsil etmez.
P0 yarışma kabulü için bağlayıcı donanım iki HackRF One + PortaPack H2, bir
ZedBoard Zynq-7000 P/N 410-248, iki bilgisayar ve envanterdeki pasif antenler ile
RF bağlantı elemanlarıdır.

PHASE-04 parametre kabulü açık, PHASE-06A–J doğrulanmış ve dondurulmuş, PetaLinux
ile ARM çalışma ortamı ise hazır değildir. Bu durum PetaLinux gerektirmeyen
algoritma, operatör, iletimsiz ET ve Vivado donanım mimarisi çalışmalarını
engellemez.

## Karar

P0, yol haritasındaki sonraki işlevlerin yalnız zorunlu yarışma çekirdeğini tek
kontrollü istisna olarak öne alır. P1'e ve isteğe bağlı puan işlevlerine geçilmez.
Önceki fazların dosyaları veya kanıtları yeniden yazılmaz.

Çalışma zamanı sahipliği şöyledir:

- PL: Hann, 4096 nokta AMD FFT ve exact lineer güç.
- PS/ARM: KTR uyumlu OS-CFAR, aday işleme, temporal doğrulama, zorunlu
  parametreler ve genlik tabanlı yön bulma.
- Bilgisayar-1: HackRF-1 RX, Ethernet taşıması, operatör uygulaması ve
  geliştirme sırasında host referans/oracle yürütümü.
- Bilgisayar-2: HackRF-2 için yalnız iletimsiz/loopback P0 ET kontrolü.

P0'nun yetkili tespit kararı KTR uyumlu PS OS-CFAR çekirdeğidir. PHASE-06G
`regional` detector, doğrulanmış kaba FPGA hızlandırıcısı olarak korunur; sürekli
canlı akış hızı kanıtlanana kadar yetkili P0 kararı sayılmaz.

PC→ZedBoard yolu `HackRF-1 → USB → Bilgisayar-1 → Ethernet → ZedBoard PS → DDR
→ AXI DMA → PL` olur. ZedBoard'ın HackRF USB host olması P0 bağımlılığı değildir.

ET varsayılan olarak iletimsizdir. `OFFLINE` ve `LOOPBACK` yazılım kabul
modlarıdır. `CABLED_LAB` ayrıca fiziksel güvenlik sözleşmesi gerektirir;
`HARDWARE_TX_LOCKED` gönderim yapamaz. Açık alan otomatik TX uygulanmaz.

## Kanıt seviyeleri

Her sonuç şu seviyelerden yalnız gerçekten sağlananlarla etiketlenir:

1. Host üzerinde algoritma doğrulandı.
2. RTL doğrulandı.
3. Vivado sentezlendi.
4. Vivado route edildi ve zamanlama kapandı.
5. Bitstream üretildi.
6. ZedBoard üzerinde çalıştırıldı.
7. Canlı HackRF ile çalıştırıldı.

Bu seviyeler birbirinin yerine kullanılamaz. Kalibrasyon katsayısı olmadan dBm
gösterilmez ve arayüzde `KALİBRASYON BEKLİYOR` yazılır.

## Ertelenen kapsam

P0; konum, MUSIC/faz DF, TDOA, motorlu DF, dijital radyo çözme/tanıma, yayılım
tekniği sınıflandırma, AI/ML, GNSS, look-through, sweep karıştırma ve açık alan RF
TX içermez.
