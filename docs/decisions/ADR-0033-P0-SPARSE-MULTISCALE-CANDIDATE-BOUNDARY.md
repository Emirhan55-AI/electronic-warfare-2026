# ADR-0033 — P0 Seyrek Çok Ölçekli Aday Sınırı

- Durum: Mimari, bit-doğru referans, final candidate-reducer RTL ve Zynq-7020 50 MHz sentez/place/route kapısı tamamlandı; kart entegrasyonu ve fiziksel kabul beklemede
- Kapsam: P0 sürekli `PL → DMA → ARM` sinyal tespiti yolu
- Bağlı gereksinimler: KTR-4.1, KTR-4.2, KTR-6
- Ön koşullar: ADR-0028, ADR-0029, ADR-0030, ADR-0031, ADR-0032

## Sorun

ADR-0032 kısa yolu işlevsel eşdeğerlik sağlamış fakat hızlanma üretmemiştir.
Fiziksel 64+4.096 alt-aşama ölçümünde OS aday gruplama `0,635712 ms`, OS
gruplamayı da içeren çok ölçekli tespit `1,551391 ms`, ARM zinciri
`2,654336 ms` ve DMA `1,443685 ms` ölçülmüştür. Yalnız OS gruplamayı PL'ye
taşımak ARM ortalamasını kuramsal olarak `2,018624 ms` düzeyine indirir; bu,
`2,048 ms` kare bütçesine ortalamada yalnız `%1,455` marj bırakır ve ardışık
DMA ile gerçek-zamanı kapatmaz.

Çok ölçekli tespitin tamamı kaldırıldığında bile ölçülen sürelerden türetilen
ardışık DMA+ARM alt sınırı `2,546630 ms` olur. Bu nedenle yalnız mevcut
PHASE-06H aday gruplamayı bağlamak veya yalnız ARM içi kısa yol eklemek kabul
edilmez.

## Karar

Sürekli tespit karelerinde PL, son çok ölçekli aday kümesini üretir ve mevcut
PHASE-06I sürümlemeli seyrek paket sözleşmesini kullanır. Paket şu davranışları
kayıpsız korur:

- strict rank-24/32 OS-CFAR hücre kararı ve `maximum_gap_bins=1` gruplaması,
- 16×256 bölgesel çift-median, 32-bin bütünleşik enerji ve 41-bin asgari
  geniş bant kurtarma desteği,
- geniş bant adayının çakışan OS parçalarını bastırması,
- shifted artan aday sırası, ilk maksimum peak bağı ve boş-kare semantiği,
- peak gücü, gürültü, eşik, Pfa profili, frame kimliği, durum ve CRC alanları.

Sürekli tespit taşıması tam 4.096 güç hücresini PS'ye zorunlu göndermez.
Operatörün doğrulanmış bir olay için başlattığı parametre ölçümü ayrı, açıkça
seçilen ölçüm karesinde tam güç/IQ yolunu korur. Böylece KTR-4.2 ölçümleri
uydurulmuş veya eksik spektrumdan üretilmez.

DMA ve ARM yürütümü iki bounded buffer ile örtüştürülür. Tek kareli mevcut PL
çekirdeğinin giriş/çıkış backpressure sözleşmesi bozulmaz; gerçek ping-pong,
driver/ABI ve hizmet sıralaması ayrıca doğrulanmadan uygulanmış sayılmaz.

## Sayısal sözleşme

`algorithms/rtl/p0_candidate_reducer.py` doğal sıralı unsigned UQ28.30 gücü
bit-doğru P0 kararlarına dönüştürür. OS karar katsayısı mevcut Q32 değerini
korur. Paket metadata yuvarlamaları ve geniş bant karşılaştırması Q48 sabit
katsayılarla yapılır. Dondurulmuş 11 OS-CFAR karesi ile üç ek bölgesel/geniş
bant karesinde final aday sınırı, peak, güç, gürültü, eşik ve PHASE-06I packet
round-trip farkı sıfırdır.

## Uygulama kapıları

1. Yazılım referansı ve dondurulmuş vektör eşdeğerliği.
2. Median, bütünleşik enerji, aday birleştirme ve PHASE-06I çıkışı için
   synthesizable SystemVerilog; reset, malformed frame, overflow ve rastgele
   backpressure testleri.
3. Zynq-7020 sentez/place/route ve 50 MHz setup/hold; kare başına en fazla
   `102.400` çevrim. Temiz sentez/route koşusunda `WNS=+0,670 ns`,
   `WHS=+0,053 ns`, setup/hold failing endpoint `0` ve route hatası `0`
   ölçülmüştür. Bu kapı synthesis-only wrapper içindir; board pin/IO standardı
   tanımı içermez.
4. Sürümlemeli DMA/driver ve iki-buffer hizmet entegrasyonu.
5. Yeni PetaLinux imajı, fiziksel bit-doğru aday kabulü ve değişmeyen
   64+4.096 / `488,28125 kare/s` kapısı.
6. Parametre ölçüm modunda dört gözlem, tam güç/IQ bağı ve mevcut altı alanın
   sayısal eşdeğerliği.

## İlk RTL sonucu

On altı 256-bin bölgeyi aynı radix geçişinde işleyen paralel çift-median motoru
synthesizable SystemVerilog olarak eklenmiştir. Beş deterministik kare ve 80
bölgesel sonuçta bit farkı sıfır, en yüksek son-kabulden-sonuç gecikmesi `29.756`
çevrimdir; 50 MHz kapasite karşılığı `0,59512 ms` olur. Malformed frame sticky
hata yolu ayrıca geçmiştir. Bu değer yalnız median alt-aşamasıdır; bütünleşik
enerji, final aday fusion, sentez/place/route ve kart ölçümü değildir.

Median motoruna bağlı geniş bant kurtarma çekirdeği 32-bin kayan toplamı Q48
eşikle karşılaştırır, bir boş hücreyi köprüler, en az 41-bin desteği korur ve
shifted sıradaki ilk maksimumu peak olarak seçer. Beş karede 22 semantik aday
ve 24 AXI kaydının sınır, peak, güç, gürültü, eşik ve paket metadata'sı bit-doğru
referansla aynıdır. Rastgele çıkış backpressure altında veri sabitliği, malformed
frame ve fiziksel güç aralığı dışındaki girdinin fail-closed boş paket davranışı
geçmiştir. Median dahil son girişten son çıkışa en yüksek gecikme `44.755`
çevrimdir; 50 MHz yalnız kapasite karşılığı `0,89510 ms` olur.

OS karar motorunun seyrek çıkışı aynı rank-24/32 strict Q32 kararını korur;
bir-bin boşluk köprüsü ve peak hücresindeki OS gürültü/eşik metadata'sıyla 5
karede 151 aday ve 154 AXI kaydında sıfır fark vermiştir. Sıralı fusion taraması
geniş bantla çakışan tüm OS parçalarını bastırıp kalan iki akışı shifted sırada
birleştirir. Uçtan uca reducer aynı 5 karede 61 final aday ve boş kare dahil 62
AXI kaydında sıfır metadata farkı vermiştir. En yüksek son-girişten-son-çıkışa
gecikme `45.428`, bir örnek/çevrim giriş kabulüyle ardışık işlevsel üst sınır
`49.524 / 102.400` çevrimdir. Kanonik en yüksek 1.352 OS adayı taşmasız
çıkmış; birleşik RAM sınırını aşan bozuk akış sticky overflow ve boş paketle
fail-closed olmuştur. Bu yalnız RTL simülasyon kapasitesidir.

## İddia sınırı

Bit-doğru final candidate-reducer RTL simülasyonu ile Zynq-7020 sentez,
yerleştirme, yönlendirme ve 50 MHz setup/hold kapısı tamamlanmıştır. Kanıt,
`results/evidence/p0/candidate-reducer-vivado.json` içinde kaynak ve rapor
özetleriyle dondurulmuştur. PHASE-06I packetizer üst bağlantısı, DMA/driver,
iki-buffer hizmeti, pin atanmış board top'u, bitstream üretimi, fiziksel FPGA
yürütümü ve gerçek-zaman başarısı hâlâ doğrulanmamıştır. Canlı HackRF, dBm
kalibrasyonu, yön bulma ve RF yayın kapsamı değişmez.
