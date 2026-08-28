# P0 FPGA Akış Hızı Gerçekliği

## Hann → FFT → lineer güç

P0 çalışma saati 50 MHz'dir. Üç blok da kararlı durumda bir karmaşık
örnek/çevrim AXI akışını kabul edecek biçimde tasarlanmıştır. Bu nedenle PL
aritmetik üst sınırı:

- Saat: 50.000.000 çevrim/s
- Kararlı durum çevrim/frame: 4096
- En yüksek frame/s: 12.207,03125
- En yüksek karmaşık örnek/s: 50.000.000

PHASE-06D davranışsal kanıtında FFT wrapper ilk girişten ilk çıkış transferine
8348 çevrim gecikmiştir. Bu başlangıç gecikmesidir; sürekli akışta frame başına
4096 çevrim kapasitesinin yerine kullanılmaz.

HackRF'ın P0 için izin verilen en yüksek 20 MS/s akışı PL aritmetik üst sınırının
%40'ıdır; salt PL aritmetik kapasitesi 2,5 kat pay sağlar. Buna rağmen PC
Ethernet, PS DDR ve iki yönlü DMA bant genişliği kartta
ölçülmediğinden uçtan uca 20 MS/s iddiası yoktur.

İlk 100 MHz uygulama denemesi route edilmiş, fakat WNS −6,541 ns ve TNS
−507,301 ns ile setup timing'i geçememiştir. Bu denemede bitstream üretilmemiştir.
50 MHz seçimi bu sonucu saklamak veya timing'i olduğundan iyi göstermek için
değil, 20 MS/s gereksinimini hâlâ aşan gerçek çalışma hedefini tanımlamak içindir.
Vivado 2025.2 post-route sonucu WNS +0,258 ns, TNS 0, WHS +0,025 ns, THS 0 ve
sıfır failing endpoint ile timing'i kapatmıştır. Bu PL aritmetik kapasite kanıtı,
kart üzerinde Ethernet/DDR/DMA akış hızı ölçümü değildir.

## PHASE-06G detector borcu

PHASE-06G tek frame buffer kullanır; input toplama sonrasında processing ve replay
süresince `TREADY` düşer. Kanıtlanan mimari sayıları 4096 giriş çevrimi, son
girişten ilk çıkışa 476.131 saat aralığı ve 4096 çıkış çevrimidir. Yaklaşık
484.322 çevrim/frame üzerinden 50 MHz'de teorik üst sınır yaklaşık 103,24 frame/s
veya 422.859 karmaşık örnek/s'dir. Post-detector 50 MHz timing doğrulanmadığı için bu
yalnız mimari üst sınırdır, canlı detector hızı değildir. P0 yetkili tespit kararı
bu nedenle PS OS-CFAR'dır.

## Fiziksel sürekli-hız ölçümü

ADR-0029 ile önceden kilitlenen 2 MS/s profilinde (64 ısınma ve 4096 ölçüm
karesi) ZedBoard üzerindeki aynı `PL → DMA → ARM` hizmet yolu 4096/4096 kareyi
ve her yanıtta DMA `0x7` durumunu tamamladı; ancak yeniden ölçülen toplam hız
50,67380 kare/s (p50 18,910 ms/kare) oldu. Gereken alt sınır 488,28125
kare/s olduğundan kapı yaklaşık 9,63577 kat eksik kaldı. Bu sonuç DMA veya
protokol hatası değil, hizmet yolunun kare başına işlem süresinin baskın
olduğunu gösteren başarısız bir sürekli-hız kabulüdür; kanıt
`results/evidence/p0/ed-throughput-physical-acceptance.json` dosyasındadır.

Bu ölçümden sonra kabul profilini gevşetmek veya sonucu gerçek-zamanlı ilan
etmek yerine DMA ioctl/aktarımı, PL çekirdek beklemesi ve ARM aday/temporal
işlemesi ayrı zamanlanmalıdır. Aynı kartta yalnız DMA ioctl/aktarımı 100 tekrar
karakterizasyonunda 0,666 s toplam (yaklaşık 6,66 ms/kare) ölçülmüştür; bu
ölçüm kabul hızının kendisi değildir, ancak 2,048 ms/kare bütçesinin DMA
katmanında bile aşıldığını gösterir. Yeni RTL/PS boruhattı veya paralel tamponlama
kararı ancak bu ayrıştırılmış ölçümden sonra verilecek ve ayrı fiziksel kabul
ile kapatılacaktır.
