# Sistem Temel Çizgisi

## Durum

Bu belge PHASE-00 sistem hedefini tanımlar. Burada açıklanan veri yolları ve işleme yetenekleri henüz doğrulanmamış hedeflerdir; çalışan bir DSP veya RF sistemi mevcut değildir.

## Fiziksel bileşenler ve görev ayrımı

| Bileşen | Planlanan görev |
|---|---|
| HackRF-1 + PortaPack H2 | ED/RX, kayıt ve canlı I/Q kaynağı |
| HackRF-2 + PortaPack H2 | Yalnız ileride kontrollü, izinli ET/TX ve aldatma test kaynağı |
| Laptop | HackRF USB erişimi, kayıt, veri aktarımı ve kullanıcı arayüzü |
| ZedBoard PS | Gigabit Ethernet, kontrol, DDR ve PL veri aktarımı |
| ZedBoard PL | Gerçek zamanlı FPGA DSP işlemleri |
| Antenler ve RF kabloları | Banda ve göreve uygun alma; ileride kontrollü test düzeneği |

Referans donanım; geniş bant omni antenleri, alt/orta bant teleskobik anteni, FOX 727 dual-band Yagi'yi, üst bant yönlü UWB antenleri ve GPS L1 aktif antenini içerir.

## Hedef veri ve geliştirme akışı

Hedef giriş veri yolu `SigMF veya HackRF-1 → PC → Gigabit Ethernet → ZedBoard PS → DDR/AXI DMA → ZedBoard PL` biçimindedir. Sparse sonuç dönüş yolu `ZedBoard PL → versioned candidate AXI packet → AXI DMA S2MM → PS DDR → ZedBoard PS temporal/control → PC display` olarak ayrılır; PC kritik algoritma motoru değildir. Geliştirme önce kayıtlı ve tekrarlanabilir SigMF verisiyle başlar; gerçek DMA/PetaLinux ve HackRF ancak ilgili acceptance fazlarında uygulanır.

ED işlevleri sinyal tespitinden başlayarak parametre çıkarımı, yön bulma, konum ve dinlemeye doğru sıralı geliştirilecektir. ET işlevleri ancak ED aşamaları doğrulandıktan ve güvenli, kontrollü, izinli RF test düzeni sağlandıktan sonra ele alınacaktır.

Yön bulma; yönlü antenin elle döndürülmesi ve her açı için göreli güç/PSD ölçümüyle planlanır. Açı ve ölçüm konumu kullanıcı tarafından elle girilecektir. Yaklaşık konum, bilinen iki ölçüm noktasından elde edilen LOB doğrularının birleştirilmesine dayanacaktır.

## KTR'ye göre mimari değişiklikler ve sınırlar

KTR 4.1 sinyal tespit zinciri korunur. Buna karşılık bladeRF, KrakenSDR, faz uyumlu çok kanallı alıcı, motorlu anten, PA, kuplör ve yüksek güçlü RF çıkış zinciri referans sistemde yoktur. Bu nedenle MUSIC veya faz karşılaştırmalı DF uygulanamaz; otomatik anten taraması ve yüksek güçlü ET yeteneği iddia edilemez. Tüm bunlar plan veya sınırlamadır, doğrulanmış yetenek değildir.
