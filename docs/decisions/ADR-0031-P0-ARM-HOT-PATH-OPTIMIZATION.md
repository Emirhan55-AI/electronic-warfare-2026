# ADR-0031 — P0 ARM Sıcak Yolunun Gecikme Düzeltmesi

- Durum: Uygulandı; gerçek-zaman kapısı açık
- Kapsam: P0 fiziksel PL→DMA→ARM yerel hizmet sıcak yolu
- Bağlı gereksinim: KTR-4.1

## Sorun

ADR-0030 fiziksel kabulünde PL OS-CFAR çıktısı 4.096/4.096 kelimede bit-doğru,
DMA ve hizmet koşusu 4.096/4.096 karede hatasızdır. Buna rağmen yerel hizmet
`95,62877 kare/s` ölçülmüş ve `488,28125 kare/s` kapısı geçilememiştir.
Düzeltilmiş profiler ortalama DMA süresini `1,456537 ms`, ARM zincirini
`6,714248 ms` ve birleşik süreyi `8,170784 ms` ölçmüştür. PL çıktı açma,
aday gruplama ve çok ölçekli tamamlamadan sonra ARM zincirinde henüz ayrı
araçlanmamış `4,672866 ms` kalmaktadır.

## Değişmez sözleşmeler

Bu düzeltme detector veya temporal yöntemi değiştirmez. Aşağıdaki davranışlar
byte ve semantik düzeyde korunur:

- 16 referans/yan, 4 koruma/yan, rank 24/32 ve Pfa `1e-4` OS-CFAR profili,
- strict `CUT > eşik`, tam pencere kenarları ve `max_gap_bins=1`,
- geniş bant kurtarma ve aday sıralama sonucu,
- önceki span ±2 bin pozitif örtüşme, küresel overlap/distance/event-id sırası,
- 2/3 doğrulama, iki ardışık kaçırmada sonlandırma ve bounded olay kapasitesi,
- PHASE-06I paketinin IEEE CRC32, little-endian ve reserved alan kontrolleri,
- yerel hizmet ABI v1/v2 mesaj boyları, alanları, CRC'leri ve yetki sınırı,
- ADR-0029'daki 64 ısınma + 4.096 ölçüm ve `488,28125 kare/s` fiziksel kapısı.

Sonuca göre örnekleme hızı, kare boyu, test girdisi, tespit eşiği veya kabul
paydası değiştirilemez.

## Karar

Çalışma üç kontrollü basamakta yürütülür:

1. PL paket açma, çok ölçekli aday üretimi, PHASE-06I paketleme, PHASE-06J
   eşleştirme ve yerel ABI kodlama/CRC maliyetleri ayrı monotonik ölçümlenir.
2. Aynı IEEE CRC32 sonucunu üreten sabit tablolı güncelleme ve PHASE-06J'nin
   mevcut küresel greedy seçimini koruyan track-başına en iyi eşleşme önbelleği
   uygulanır. Bir aday seçildiğinde yalnız o adayı önbelleğinde tutan track'ler
   yeniden taranır; böylece seçim sırası değişmeden tekrarlı tam matris taraması
   kaldırılır.
3. Bu iki düzeltme hedefi kapatmazsa, ürün içi `p0_ed_pipeline` PHASE-06J'ye
   doğrulanmış typed adayları doğrudan verebilir. PHASE-06I serileştirme ve strict
   packet decoder silinmez; dış taşıma ve regresyon doğrulama yolu olarak korunur.

DMA/PL ping-pong veya ek RTL ancak bu basamaklardan sonra hâlâ gerekli olduğu
ölçülürse ayrı mimari karar ve kullanıcı onayıyla ele alınır.

## Kabul kapıları

- Mevcut PHASE-06I/J golden dizilerinde semantik fark `0` olur.
- Paket yolu ile olası typed iç yol aynı kare sonuçlarını byte-tam üretir.
- ABI v1/v2 pozitif ve negatif protokol testlerinin tamamı geçer.
- Bozuk CRC, reserved alan, sıra atlaması, frame wrap, kapasite ve reset yolları
  fail-closed kalır.
- PetaLinux ARM paketi ve tam imaj sıfır başarısız görevle derlenir.
- Fiziksel kartta bilinen güç/karar kelimeleri golden ile sıfır fark verir.
- Fiziksel 64+4.096 koşusunda 4.096/4.096 tamamlanma, DMA `0x7`, sıfır hizmet,
  sıra ve aday düşürme hatası korunur.
- Gerçek-zaman başarı ölçütü değiştirilmeden en az `488,28125 kare/s` olur.

Host süreleri yalnız geliştirme karşılaştırmasıdır. Başarı yalnız fiziksel kart
ölçümüyle ilan edilir.

## Uygulama ve fiziksel sonuç

Üç kontrollü basamak da uygulanmıştır. IEEE CRC32 nibble tablosuyla
hızlandırılmış, PHASE-06J küresel greedy sonucu korunarak track-başına eşleşme
önbelleği eklenmiş ve ürün içi pipeline doğrulanmış typed aday yoluna alınmıştır.
Strict PHASE-06I paket decoder dış taşıma ve regresyon yolu olarak korunmuştur.
Paket ve typed yollar 33 karedeki 1.501 aday kaydında byte-tam aynı olay sonucunu
üretmiştir. PetaLinux derlemesindeki 5.679 görevin tamamı başarılıdır.

Fiziksel ZedBoard koşusunda FPGA manager `operating`, DMA `0x7` ve 4.096/4.096
tamamlanma korunmuştur; hizmet, sıra, DMA ve aday düşürme hataları sıfırdır. Kesin
aşama profili ARM ortalamasını `6,714248 ms` değerinden `2,612712 ms` değerine,
birleşik yolu `8,170784 ms` değerinden `4,075004 ms` değerine indirmiştir. Yerel
hizmet hızı `95,628767584 kare/s` değerinden `196,966411503 kare/s` değerine
çıkmıştır.

Buna rağmen kilitli `488,28125 kare/s` kapısı geçilmemiştir; gerçek-zaman marjı
`0,403387211` ve eksik hız çarpanı `2,479007696` olarak ölçülmüştür. ADR-0031
optimizasyonu işlevsel olarak kabul edilmiş, performans kapısı başarısız olarak
saklanmıştır. Sonraki adım DMA ile ARM işlemesini örtüştüren ping-pong akışı ve
aday üretim yükünün PL/PS dağılımını değerlendiren ayrı bir mimari karardır;
kullanıcı onayı olmadan başlatılmaz.

## İddia ve güvenlik sınırı

Bu karar RF dalga şekli, yayın, canlı HackRF, Ethernet, kalibrasyon veya saha
doğruluğu eklemez. `/dev/p0-dma` `root:root 0600`, ayrıcalık düşürme ve yerel
soket izinleri korunur. Herhangi bir hız kapısı geçmezse başarısız sonuç kanıt
olarak saklanır; yöntem veya eşik sessizce değiştirilmez.
