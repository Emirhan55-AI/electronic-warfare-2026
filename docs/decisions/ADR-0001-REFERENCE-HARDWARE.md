# ADR-0001: Referans Donanım

- Durum: **Accepted**
- Karar tarihi: 2026-08-12

## Bağlam

Proje, satın alınmış donanımla gerçekçi ve izlenebilir bir FPGA merkezli prototip geliştirmelidir. Mimari, mevcut olmayan eski KTR donanımına veya ölçülmemiş performans varsayımlarına dayanmamalıdır.

## Karar

Referans sistem 2× HackRF One + PortaPack H2, 1× ZedBoard Zynq-7000 (P/N 410-248), bir laptop ve satın alınmış anten/RF bağlantı takımından oluşacaktır. Anten takımı geniş bant omni, alt/orta bant teleskobik, FOX 727 dual-band Yagi, üst bant yönlü UWB ve GPS L1 aktif antenlerini kapsar.

Hedef veri yolu `SigMF veya HackRF-1 → PC → Gigabit Ethernet → ZedBoard PS → DDR/AXI DMA → ZedBoard PL` olacaktır. Laptop, HackRF USB erişimi ile ZedBoard arasında köprü görevi görecektir.

## Gerekçe

Bu seçim satın alınmış donanımı temel alır; çevrimdışı, tekrarlanabilir veriyle başlayıp canlı alıma ilerlemeye izin verir ve hesaplama yoğun DSP'nin ZedBoard PL üzerinde geliştirilmesi hedefini korur. İkinci HackRF, yalnız ileride güvenli ve izinli testlerde ayrı bir kontrollü kaynak sağlar.

## Sonuçlar ve sınırlamalar

- İki HackRF ortak saatli, faz uyumlu çok kanallı alıcı oluşturmaz. Bu nedenle MUSIC veya kanallar arası faz karşılaştırmasına dayalı DF uygulanamaz.
- Yön bulma, yönlü antenin manuel döndürülmesi ve açı başına göreli güç/PSD ölçümüyle sınırlandırılır.
- Motorlu anten sistemi bulunmadığından otomatik mekanik tarama iddia edilemez.
- PA, kuplör ve yüksek güçlü çıkış zinciri bulunmadığından yüksek güçlü ET yeteneği iddia edilemez.
- HackRF-2 kullanımı güvenli test düzeni ve açık faz onayı sağlanana kadar ertelenir.
- PC köprülü veri yolu hedef mimaridir ve PHASE-00'da uygulanmış veya doğrulanmış değildir.
