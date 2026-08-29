# ADR-0033 — P0 Seyrek Çok Ölçekli Aday Sınırı

- Durum: Mimari, bit-doğru referans ve paralel median RTL alt-aşaması tamamlandı; final reducer ve fiziksel kabul beklemede
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
   `102.400` çevrim.
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

## İddia sınırı

Bu karar, referans model ve median RTL simülasyonu tam candidate reducer,
sentez, fiziksel FPGA yürütümü veya gerçek-zaman başarısı değildir. Canlı
HackRF, dBm kalibrasyonu, yön bulma ve RF yayın kapsamı değişmez.
