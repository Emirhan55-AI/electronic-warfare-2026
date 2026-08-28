# ADR-0028 — P0 Çok Ölçekli Tespit ve Geniş Bant Kurtarma

- Durum: Kabul edildi
- Kapsam: P0/ED kapanış düzeltmesi
- Bağlı gereksinim: KTR-4.1

## Sorun

P0'daki 16 referans ve 4 koruma hücreli OS-CFAR, dar ve yerel emisyonlar için
yetkili tespit yoludur. Bununla birlikte emisyon desteği bütün yerel referans
penceresini doldurduğunda referans hücreleri de sinyal gücü içerir. Eşik sinyalle
birlikte yükselir; geniş bant emisyon seyrek uç hücrelere parçalanabilir ve 2/3
zamansal doğrulama için kararlı bir olay sahibi oluşmayabilir.

Bu düzeltme parametre çıkarımını veya OS-CFAR'ın sayısal profilini değiştirmez.
Amaç, OS-CFAR'ın doğal ölçek sınırını ayrı ve sınırlı bir geniş bant öneri yoluyla
kapatmaktır.

## Karar

P0 tespiti iki tamamlayıcı ölçek kullanır:

1. `P0_OS_CFAR_EXPONENTIAL_PFA_1E4` değişmeden çalışır. Dar ve yerel adayların
   sahibi bu yoldur.
2. Bölgesel sağlam taban aynı shifted 4096-bin güç karesi üzerinde 16 adet
   256-bin bölgede çalışır. Her bölgenin bin başına gürültü kestirimi
   `median / ln(2)` olur.
3. Geniş bant yolu, her değerlendirilen merkez bin için `[bin-15, bin+16]`
   inclusive 32-bin alt-bant ortalama gücünü hesaplar. Strict karar
   `mean_power > 2,5 × regional_noise` olur. `2,5` katsayısı OS-CFAR'ın
   `Pfa=1e-4` iddiasını paylaşmaz; aşağıdaki popülasyon kapılarıyla sınırlanan
   ayrı bir ürün sabitidir.
4. Alt-bant tespit merkezleri mevcut `maximum_gap_bins=1` kuralıyla gruplanır.
   32-bin pencerenin dar bir emisyonu yapay olarak genişletmemesi için grup,
   `support_start = group_start + 15` ve `support_end = group_end - 16`
   sınırlarıyla muhafazakâr ham desteğe aşındırılır. Yalnız bu desteğin inclusive
   span'i en az 41 bin ise geniş bant kurtarma adayı oluşur.
   `41 = 2 × (16 reference + 4 guard) + 1`, yani OS-CFAR'ın tam yerel pencere
   genişliğidir; bu sınır değerlendirme sonucundan türetilmez.
5. Kurtarma adayıyla çakışan OS-CFAR parçaları tek geniş bant adayının altında
   bastırılır. Çakışmayan OS-CFAR adayları korunur. Son liste başlangıç, bitiş ve
   tepe binine göre deterministik sıralanır.
6. Aday kapasitesi 1352, etkin olay kapasitesi 64, zamansal 2/3 doğrulama,
   PHASE-06I ABI v1 ve parametre ölçüm sözleşmesi değişmez.

Bu karar, ham hücre eşiğini koşulsuz `min(OS, regional)` ile düşürmez. Böyle bir
OR birleşimi geniş bant dışındaki yanlış adayları artırabildiği için kabul edilmez.

## Fiziksel kapı sonrası düzeltme kaydı

İlk kilitli yöntem 28 Ağustos 2026'da ZedBoard üzerinde çalıştırıldı. İmaj,
FPGA-manager, DMA, hizmet süreci ve ARM ikili özetleri doğrulandığı halde
`wideband-noise-like` dizisinin 10 fiziksel karesinde doğrulanmış geniş bant olay
oluşmadı. Ham aday sayıları `0, 0, 0, 1, 1, 2, 1, 0, 2, 1`; bunların tümü dar
OS-CFAR parçalarıydı. İndirilen PL güç karelerinde gerçek bant desteği
`2455..2576` iken bölgesel tek-bin kararı kararlı destek üretmedi.

Kök neden, gürültü benzeri geniş bant enerjisinin çok sayıda FFT binine
dağılması ve tek-bin `Pfa=1e-4` kararının toplam alt-bant enerjisini sınamamasıydı.
Bu nedenle yukarıdaki 32-bin bütünleşik enerji kararı, kullanıcı onayıyla ve yeni
sonuçlar çalıştırılmadan önce bu ADR'ye eklenmiştir. Önceki başarısız kayıt
silinmez; yeni yöntemin kabul kanıtından ayrı tutulur.

## Uygulama sınırı

İlk ürün uygulaması ZedBoard PS/ARM üzerindeki portable C çalışma zamanıdır.
Floating-point Python modeli referanstır. Mevcut PHASE-06G SystemVerilog bloğu
değiştirilmez ve kanonik bitstream'e alındığı iddia edilmez. İleride bölgesel yol
PL'ye taşınırsa aynı kararların bit-doğru eşdeğerliği, throughput, sentez, route,
zamanlama, bitstream ve fiziksel kart kanıtı ayrıca gerekir.

## Önceden kilitlenen kabul kapıları

Aşağıdaki kapılar sonuç görülmeden önce kilitlenmiştir:

- PHASE-03 `wideband-noise-like` popülasyonunda 256 kare; karelerin en az
  `%90`'ında coverage `>=0,60`, IoU `>=0,50` ve overreach `<=0,25`.
- Mevcut dar bant, iki sinyal, merkez/kenar ve 2/3 temporal kapılarında gerileme
  yok.
- IID üstel gürültüde mevcut P0'nun 1.038.336 CUT ve iki taraflı `%99` Wilson
  yanlış alarm kapısı korunur.
- PHASE-03 homojen, eğimli ve basamaklı gürültü popülasyonlarında geniş bant
  kurtarma yolunun ek 41-bin adayı sıfır olur.
- Python ve portable C; OS-CFAR hücreleri, kurtarma seçimi, birleşik adayların
  start/end/peak alanları ve zamansal sonuçlarda eşdeğer olur.
- Aday, bellek ve ABI sınırları değişmez; non-finite, negatif ve kapasite hata
  yolları fail-closed kalır.
- Fiziksel kabulte 10 karelik aynı geniş bant dizisi içinde en az dört ardışık
  kare boyunca tek `confirmed + observed_this_frame` olay sahibi bulunur.
  `2455..2576` referans desteğine göre coverage `>=0,60`, IoU `>=0,50` ve
  overreach `<=0,25` kapıları korunur.
- 10 karelik fiziksel yalnız-gürültü dizisi ek 41-bin kurtarma adayı,
  doğrulanmış olay veya geçerli parametre sonucu üretmez.

Bir kapı geçmezse eşik veya sahne sonuca göre değiştirilmez. Bundan sonraki yeni
aday yöntemi, yeni ön kayıt ve ayrı kullanıcı onayı olmadan denenmez.

## Literatür bağı

ITU-R SM.2256, geniş bant emisyonlarda FFT çözünürlüğü, dinamik eşik ve komşu
frekans örneklerinin birlikte değerlendirilmesini ele alır. ITU-R SM.443, işgal
edilen bant genişliğinin FFT tabanlı sayısal izlerden ölçülebileceğini tanımlar.
Geniş bant spektrum algılama literatüründeki enerji algılayıcıları da tek-bin
tepe kararı yerine alt-bant enerjisini ve gürültü belirsizliğini açıkça ele alır.
Bu kaynaklar tek başına uygulamanın `32` ve `2,5` sabitlerini belirlemez;
sabitler yukarıdaki önceden kayıtlı mühendislik ve kabul sözleşmesidir.

- ITU-R SM.2256-1: https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-SM.2256-1-2016-PDF-E.pdf
- ITU-R SM.443-4: https://www.itu.int/dms_pubrec/itu-r/rec/sm/r-rec-sm.443-4-200702-i!!pdf-e.pdf
- Bogale, Vandendorpe ve Le, *Wideband Sensing and Optimization for Cognitive
  Radio Networks with Noise Variance Uncertainty*: https://arxiv.org/abs/1409.3246

## Sonuç

KTR'nin OS-CFAR yolu korunur; OS-CFAR'ın kendi referans penceresinden geniş
emisyonlar için ayrı, izlenebilir ve yanlış alarmı sınırlanmış bir öneri ölçeği
eklenir. Parametre çıkarımı ancak birleşik adayın normal 2/3 ve dört gözlem
kapılarını geçmesinden sonra çalışır.
