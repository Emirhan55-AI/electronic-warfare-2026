# Sinyal tespiti: güncel durum ve kabul sınırı

## Son ST-06 ürün güncellemesi — 5 Eylül 2026

Paketlenmiş hizmette CPU0 DMA sonrası güç çözme/doğrulamayı, CPU1 dar/geniş
aday ve olay işlerini yürütür. Kuyruk tamponlarının sahipliği değiştirilerek
ek kopya önlenir; hata geri alımında ortalama kayıtlı toplamdan türetilir.
Algoritma, medyan, eşikler ve RTL değişmedi. Üç zaman damgalı dijital ürün
koşusu 508,56 / 502,40 / 508,93 kare/s; 16.000 karelik karma tekrar ölçümü
529,30 kare/s verdi. Gerekli 488,28125 kare/s bu iş yüklerinde sağlandı.
Beş kısa testin ham yanıtları önceki paketle birebir eşleşti. Aktarım hatası
ve aday düşümü sıfırdı. Ek ARM kuyruk belleği 272 KiB'dir; FPGA artışı yoktur.
Kanıt: `results/evidence/phase08/st06-parallel-product-v1.json` ve ZIP.
Bu sonuç RF veya soğuk açılış kabulü değildir. SD değişmedi, hizmet geçici
yüklüdür. Hız payı sınırlıdır; saf periyodik ton/yoğun olay kapasitesi,
sürekli HackRF RX ve kör RF kapıları açıktır. ST-06 tamamlanmamıştır.
Aşağıdaki eski hız kayıtları kendi kaynak sürümlerinin tarihsel sonuçlarıdır.


## Sıradaki kabul ve yeniden başlama

CPU0 ve CPU1 kartın ARM çekirdekleridir; tespit bilgisayara taşınmadı.
PC hâlâ HackRF USB alımı, taşıma, görüntüleme ve kayıt görevlerini üstlenir.
Sonraki ölçüm gerçek HackRF → PC → kart → arayüz yolunda kesintisiz RX'tir:
kare/sıra kaybı, kuyruk doluluğu, gecikme ve durdur/başlat sürekliliği kaydedilir.
Test vericisi kapalı başlangıç, ortamın RF sessiz olduğunu kanıtlamaz.
Bunun ardından kontrollü kör RF doğruluğu ve soğuk açılış kabulü tamamlanır;
saf ton fazla adayları ve 64 olay kapasitesi ayrıca değerlendirilir.

Güncel yerel paket `build/p0/st06-parallel-product/` altındadır; klonlanan
depoda bu yerel çıktının veya eski kart oturumunun varlığı varsayılmaz.
Kaynak/ikili bağını `python scripts/verify_st06_parallel_product.py` denetler.
SD değiştirilmediği için yeniden başlatma sonrası çalışan imaj/hizmet yeniden
belirlenmelidir. En düşük ölçülen hız payı yaklaşık %2,89'dur; uzun süreli
uçtan uca performans garantisi değildir.

## Dal birleştirme ve kayıt kontrolü — 5 Eylül 2026

`master-yedek` üzerindeki `0cad6a0` ve `511e7f7` arayüz değişiklikleri
ST-06 çalışmasıyla birleştirildi. Açılış görseli ve bant taraması yerleşimi
korundu; yeni varlıklar depo dosya sözleşmesine eklendi. Bu birleştirme yeni
RF kabulü veya FPGA algoritması değişikliği içermez.

Birleşmiş kaynakta 120 hedefli regresyon geçti: depo sözleşmesi, ST-06
paralel ürün ve tarihsel kanıt kontrolleri, ARM hizmet/ürün yolu, operatör
ürün sınırı, Qt Quick, bant taraması ve canlı ED oturumu. PHASE-00 salt-okunur
kontrolündeki 10 kapı geçti. Tüm depo testlerinin çalıştırıldığı iddia edilmez.
Ham tarihsel kanıtların satır sonları hash bağını korumak için değiştirilmedi.

## Tarihsel deney kayıtları

Aşağıdaki “sonraki iş”, “güncel paket” ve “kapı açık” ifadeleri kayıtlarının
yazıldığı sürüme aittir; bugünkü çalışma sırası yukarıdadır. Geçmiş sonuçlar
ve ham kanıtlar karşılaştırılabilirlik için değiştirilmeden korunur.

## 5 Eylül 2026 — ARM döngü birleştirme denemesi

Giriş doğrulaması ve aritmetik sırası korunarak geniş bant kayan toplam ve
ortalama döngüleri ayrı kopyada birleştirildi. Üç dönüşümlü ölçümde dar tekrar
girdisi mevcut 1,169–1,191 ms / deneme 1,192–1,214 ms; geniş tekrar girdisi
mevcut 1,166–1,176 ms / deneme 1,189–1,209 ms verdi. İki girdide sonuç
özetleri aynıydı, fakat hız kazanılmadı. Deneme üretime alınmadı.
Kanıt: `results/evidence/phase08/st06-stream-fusion-v1.json` ve ZIP.
Parametre sıfırlamanın büyük tampon temizlemediği kodda doğrulandı.
Üretim kaynakları, hizmet ve SD değişmedi. Bu alt adım denemesi tam ürün
kabulü değildir. Sonraki ölçüm, yedekleme/kopyalama ve CPU0–CPU1 kuyruk
beklemesini güncel -O3 hizmet üzerinde ayrı zamanlamalıdır; veri doğrulama
ve geri alma garantileri performans uğruna kaldırılmaz.


## 5 Eylül 2026 — birleşik medyan denemesi

Sıralı dizileri doğrudan işleyen ve örnek değerlerin çeşitliliğine göre iki
**tam** bölümleme yönteminden birini seçen prototip denendi. Örnekleme medyanı
yaklaşıklamaz; hangi eşdeğer yöntemin kullanılacağını seçer. 960 referans
dizisi ve 1080 kayan pencere uyuşmazlık vermedi. Her varyant üç dönüşümlü
koşuda toplam 120.000 süre ölçümü verdi. Birleşik yöntemin 256 hücre sürekli
rastgele p99 süresi 33,11 → 27,81 µs, sıralı artan süresi 10,56 → 3,56 µs;
ancak tek tepeli girdi 7,21 → 8,78 µs oldu. Koşulsuz üstünlük yoktur.
Üretim kaynakları/hizmeti/SD değiştirilmedi; tam ürün hız iddiası yoktur.
Kanıt: `results/evidence/phase08/st06-median-hybrid-v1.json` ve ZIP.
Medyan seçeneklerini yalnız ortalama hızla seçmek uygun değildir. Sonraki
performans çalışması, tek bu mikro optimizasyona bağlanmadan ARM ürün yolunun
kopyalama ve işleme geçişlerini karşılaştırmalıdır. Hız kabulü açık kalır.


## 5 Eylül 2026 — medyan süre dağılımında gerileme

İki medyan uygulaması ARM CPU1 üzerinde 64/256 hücreli on giriş örüntüsünde
karşılaştırıldı. Her uygulamada 40.000 ölçüm ve 41.280 doğruluk kontrolü
uyuşmazlık vermedi. Ancak prototip her koşulda hızlı değildir: 256 hücreli
alternatif yüksek/düşük değerlerde p99, 6,61 µs'den 14,23 µs'ye çıktı;
rastgele sürekli değerlerde 33,37 µs'den 27,74 µs'ye indi. İki seviyeli ve
sabit dizilerdeki gerilemeler nedeniyle prototip üretime alınmadı.
Kanıt: `results/evidence/phase08/st06-median-tail-v1.json` ve ZIP.
Bunlar iki ardışık varyant koşusunun gözlenen süreleridir; işletim sistemi
kesmeleri ve ölçüm maliyeti dahildir, matematiksel en kötü süre sınırı değildir.
Üretim hizmeti/kaynakları/SD değişmedi. Kalan performans çalışmasında medyan
uygulamasını koşulsuz değiştirmek yerine girişe bağlı gerilemeyi önlemek ve
kalan maliyetleri ölçmek gerekir. Paket hizmeti için 488,28125 kare/s kapısı açıktır.


## 5 Eylül 2026 — medyan prototipinin tam hizmet deneyi

Medyan prototipi 960 referans dizisinde ve 120 akışın 1080 kayan penceresinde
uyuşmazlık vermedi. Ayrı, elle derlenen ARM hizmeti kartta üç dijital koşuda
470,81 / 471,51 / 476,20 kare/s verdi; 488,28125 kare/s sınırı yine geçilmedi.
Beş girdinin ham yanıtları mevcut paket hizmetiyle byte-tam eşleşti; DMA,
CRC, sıra hatası ve aday düşümü sıfırdı. Bu kayıt RF kabulü değildir.
Kanıt: `results/evidence/phase08/st06-median-experiment-v1.json` ve ZIP.
Deney sonunda paketlenmiş hizmet geri yüklendi ve özeti doğrulandı.
Üretim kaynakları ve SD değişmedi. Bu prototip paketlenmedi; patolojik
medyan süreleri ve tüm sahnelerde sürekli ürün hızı açık kalır.
Dolayısıyla güncel paket hizmeti için geçerli hız hâlâ 460–465 kare/s'dir.


## 5 Eylül 2026 — sonraki ARM tanı denemesi

Üretim kaynağı ve kart hizmeti değiştirilmeden geniş bant alt adımları
ölçüldü. Yerel tekrar üretim dosyaları ve ölçümler:
`build/p0/st06-wide-profile/diagnostic.json` (yerel çıktı; yeni ortamda
mevcut olduğu varsayılmaz). Destek aralığına göre erken çıkış prototipi
ölçülen girdilerde hız sağlamadığı için seçilmedi. İki yönlü medyan bölümleme
prototipi 51.200 dizide sıralama referansıyla aynı sonucu verdi. Üç dönüşümlü
koşuda izole ARM akış adımı dar girdide 1,1721–1,1821 ms'den
1,1283–1,1338 ms'ye; geniş girdide 1,1642–1,1688 ms'den
1,1200–1,1406 ms'ye indi. Bu iki tekrar girdisinde tüm sonuç özetleri eşleşti.
Bu yaklaşık %3–4 alt adım kazancıdır; tam ürün FPS'si veya RF kabulü değildir.
Medyan prototipi üretime alınmadı. Tam referans korpusu, uç durum süreleri,
paketleme ve ürün yolu ölçümü geçmeden mevcut kaynak değiştirilmez.
Geçerli ürün kanıtı hâlâ `st06-product-optimization-v1.json` kaydıdır.


## Son optimizasyon — 5 Eylül 2026

5 Eylül 2026 son ST-06 optimizasyonu: ARM güç çözme ve durum yedekleme
maliyeti azaltıldı; eşikler, sekiz karelik pencere ve RTL değişmedi. PetaLinux
paketinden çıkan hizmetle üç fiziksel dijital koşu 464,87 / 460,37 / 463,74
kare/s verdi. Önceki 286–290 kare/s kaydı tarihsel karşılaştırmadır;
488,28125 kare/s kabul sınırı hâlâ geçilemedi. Beş test girdisinin kart
yanıtları önceki sürümle byte-tam eşleşti. Bu, RF doğruluk kabulü değildir.
Kanıt: `results/evidence/phase08/st06-product-optimization-v1.json` ve ZIP.
SD açılış dosyaları değişmedi; güncel hizmet geçici yüklüdür. ST-06 sürer.

Alt adım tanısı güç çözme ve tam durum kopyalarının önemli maliyetini gösterdi.
Hizasız güvenli sözcük yükleme, UQ28.30 için eşdeğer iki uint32 dönüşümü ve
tek güncellemenin değiştirdiği durumun geri alınması uygulandı. Bağlam
sıfırlanırken tam yedek korunur; hata halinde geri alma testleri geçti.
Tanı klonlarının derleme ayarları ve süreleri ZIP içinde ayrı tutulur;
-O2 alt adım süreleri paketlenmiş -O3 hizmetin süreleri diye sunulmaz.
Güncel paket hizmet özeti: `3c175e1c644c653a04899feef67c57c21c72f5ba2479f319cf45192fa172900d`.
Güncel yerel çıktı: `build/p0/st06-product-optimized/`; image.ub derlendi,
ancak yeni BOOT.BIN paketi ve kalıcı soğuk açılış kabulü yoktur.
Sıradaki iş geniş bant/ARM maliyetinin kalan kısmını incelemek ve tüm
ürün yolunu tekrar ölçmektir. Saf tonun fazla adayları, yoğun girdide 64
olay kapasitesi, sürekli RX ve kontrollü kör RF kapıları açık kalır.

## Önceki sürümün fiziksel tanısı

### Optimizasyon öncesi — 5 Eylül 2026

ST-06 FPGA, ARM hizmeti ve ağ köprüsü mevcut Linux oturumuna geçici
yüklenmiştir. SD üzerindeki açılış imajı değişmemiştir. Kart erişimi
tamamlanmış ve SSH host anahtarı seri konsolundan bağımsız doğrulanmıştır.
Kanıt: `results/evidence/phase08/st06-product-board-diagnostic-v1.json` ve
aynı adlı ZIP içindeki I/Q girdileri, ham kart yanıtları ve metadata.

- 256 sıfır ve 256 bağımsız gürültü karesinde doğrulanmış olay yoktur.
  Gürültü koşulu yalnız 0,524288 saniyelik I/Q'dur; saha Pfa kabulü değildir.
- Gürültü içindeki dar ton 255/256 karede, geniş bant 249/256 karede
  doğrulanmıştır. Başlangıç birikimi bu sayılara dahildir. Sıfır girişe
  geçişte dar olay ikinci, geniş olay dördüncü sıfır karede kalmamıştır.
- Her koşulda DMA/CRC/sıra ve aday düşümü sıfırdır. Aynı girdilerin eski ve
  yeni ağ köprüsündeki yanıtları byte-tam eşleşmiştir.
- Ürün hız kapısı başarısızdır: 4096 ölçüm karesi için 287,27 ve 286,45
  kare/s; PC sonuç çözümlemesi ölçüm dışına alındığında 289,76 kare/s.
  Gereken hız 488,28125 kare/s'dir. ARM tespit iş parçacığı ölçüm aralığında
  CPU1'in 1469 toplam sayacına karşılık 1435 CPU sayacı tüketmiştir.
  Alt adım profili henüz yoktur; USB ve arayüz bu dijital deneyde yoktur.
- İlk saf periyodik ton denemesinde fazla aday, eski yoğun fixture'da 64
  olay kapasitesi taşması görülmüştür. Bunlar kapanmamıştır. Tek rastgele
  bloğu tekrar etmek bağımsız gürültü negatif testi sayılmaz.

Sıradaki iş ARM ürün yolunun alt adımlarını ölçmek, davranış eşdeğerliğini
koruyarak maliyeti azaltmak ve gerçek ürün hızını tekrar sınamaktır. Bu tanı
eşikleri değiştirmez; soğuk açılış, sürekli RX ve kontrollü kör RF kapılarını
kapatmaz. ST-06 tamamlanmamıştır. Aşağıdaki tarihli kayıtlar kendi sürümlerinin
kanıtıdır; bağımsız 551–578 kare/s DMA profili güncel ürün hızı değildir.

1 Eylül 2026. Kapsam yalnız şartnamenin kullanıcı tarafından paylaşılan
5.1.1 sinyal tespiti maddesi ve depodaki `KTR-4.1` / `KTR-4.1-OPS` izleridir.
Bu numaralar farklı belgelerin izleridir; şartname OS-CFAR'ın sayısal profilini
zorunlu kılıyor diye yorumlanmaz. Sonraki görev fazlarına geçiş yoktur.

## Sinyal tespiti kapanış planı — uygulama sürüyor

Kullanıcı planın ardından uygulama yetkisi vermiştir. Yalnız mevcut sinyal
tespiti kapsamındaki alım, görüntü ve tarama düzeltmeleri uygulanmaktadır.
İş paketlerinin tamamı bitmiş sayılmaz. RX/görüntü yazılımı, geniş bant tespit
RTL'i ve ADR-0040 zayıf-kararlı dar bant kaynak zinciri değiştirilmiştir.
ADR-0040'ın güncel PL→paket→PS değişikliği Icarus, portable C, Linux-host,
Vivado route/zamanlama/bitstream, PetaLinux P09 kalıcı soğuk açılış ve kart üstü
dijital işlev/hız kapılarından geçmiştir. Bir kontrollü canlı RF aç/kapat tanı
turu yapılmış, ancak tekrar sayılı kör saha Pd/Pfa ve kalibrasyon kabulü henüz
tamamlanmamıştır.
Aşağıdaki başlangıç bulguları düzeltme öncesini anlatır.
Operatörün harici verici durumu alıcı yazılımından doğrudan okunamaz. Ortam
kaydı bu nedenle otomatik olarak "yalnız gürültü" ya da gerçek değeri bilinen
bir negatif test sayılmaz; deney koşulu ayrıca operatör beyanı ve A/B sırasıyla
kaydedilir.
Kapsam mevcut PHASE-08 sinyal tespiti, onu sağlayan alım/FPGA yolu ve tespit
arayüzüdür; parametre çıkarımı, dinleme, yön bulma ve ET kapsam dışıdır.

1 Eylül 2026 sunum bakımında çalışan ürün davranışı değiştirilmeden Qt Quick
katmanı modüllere ayrılmıştır. `quick_view_model.py` yalnız ortak durum ve
sonuç birleştirmesini taşır; tarama, ölçüm, dinleme, yön bulma, ET eylemleri ve
arka plan işçileri ayrı modüllerdedir. Ortak QML kontrolleri, ET çalışma alanı
ve alıcı ayarları da ayrı bileşenlerdir. Eski Qt Widgets penceresi görev alanı
mixinlerine bölünmüş, fakat ürün giriş noktası olmaya devam etmemiştir.
Kaynak hashine bağlı önceki fiziksel UI/RX raporları bu modülerleştirme öncesine
ait tarihsel kanıttır. Otomatik davranış regresyonları geçse bile yeni fiziksel
koşu yapılmadan bu raporlar güncel kaynak kabulü sayılmaz; özellikle açık USB
shortfall kapısı kapanmış değildir.

1 Eylül 2026 sabit bant karar bakımında, tek LO'daki FPGA 2/3 sonucu artık
kesin yayın olarak sunulmaz; sarı `FPGA ADAYI`dır. Aday en az 8 FPGA
gözleminden sonra dört olası DC-güvenli fiziksel HackRF ayarından iki başarılı
ayar bulunana kadar 96'şar kare yeniden sınanır. İlk 16 kare yerleşme
korumasıdır ve kalan karelerin en az 24'ünde aynı mutlak RF tepesi (dar adayda
±50 kHz, geniş adayda destek örtüşmesi) görülürse yeşil `KARARLI RF ADAYI`
olur. FPGA alanının içinde veya dışında kalan doğrulanmış 8 MHz kaba RX adayı
da aynı FPGA sınamasını yalnız aday olarak başlatabilir. Geçici doğrulama
ayarlarından sonra ana görünüm daima operatörün seçtiği sabit merkeze döner. Bu işlem
alıcı ayarına bağlı DC/LO ve benzeri iç ürünleri reddetmek içindir; harici
vericinin kimliğini kanıtlamaz. Bunun için değişmeyen alıcı koşullarıyla TX
kapalı/açık A/B hâlâ zorunludur.

2 Eylül 2026 kontrollü 1 GHz tanısında iki ek yanlış-pozitif açığı
kapatılmıştır. İki-LO doğrulaması artık yalnız fiziksel HackRF merkezini değil,
FPGA çıkış merkezini de değiştirir; böylece çıkış/NCO koordinatına kilitli bir
ürün iki ayar sayılmaz. Yapılandırılmış ED_RX cihazında fiziksel olarak ölçülen
1 GHz dar spur için yalnız ±5 kHz adaylarda ek yan bant kapısı uygulanır:
taşıyıcının 2–25 kHz omuzlarında, 50–250 kHz yerel medyana göre 3 dB'yi aşan
en az sekiz 16.384-FFT hücresi gerekir. Bu cihaz profili bütün 1 GHz bandını
silmez ve diğer frekanslardaki dar adaylara uygulanmaz. TX kapalı ve alıcı
anteni sökülü koşulda dört ayarın tamamında yan bant hücre sayısı 0 olmuş ve
sonuç `not_reproduced` kalmıştır. Daha sonra pozitif diye etiketlenen koşunun
ardından kullanıcı vericinin aslında kapalı olduğunu bildirmiştir; bu nedenle
`receiver-spur-1ghz-characterization.json` içindeki 18/16 hücreli koşu pozitif
TX kabul kanıtı değildir ve kayıt `superseded_positive_state_uncontrolled`
olarak işaretlenmiştir. Kararlı karar artık canlı 8 MHz alıcı spektrumundaki
sekiz ölçümlük omuz kanıtıyla sürekli denetlenir; omuzlar kaybolduğunda eski
iki-ayar kararı `live_guard_failed` olur ve operatöre tespit diye sunulmaz.
TX kapalı, anten bağlı tekrarında dört ayar 0/0/0/0 hücreyle
`not_reproduced` kalmış; arayüz 27 saniye boyunca “Kararlı yayın aranıyor”
durumunda kalmıştır. Güncel negatif kanıt
`results/evidence/phase08/receiver-spur-1ghz-tx-off-live-guard.json`
dosyasındadır. Pozitif TX kabulü, saha Pd/Pfa kabulü ve 1 GHz dışındaki spur
profilleri hâlâ açıktır.

Aynı gün kullanılan `0000000000000000a32868dc36877e47` seri numaralı alıcıda
TX kapalı referansında 720, 760 ve 840 MHz'de dar iç ürünler ölçülmüştür. Bu üç
frekans dört farklı giriş/çıkış merkezinde yeniden görünmesine rağmen 2–25 kHz
omuz kapısını geçmemiştir: 720 MHz için her ayarda yalnız bir hücre, 760 ve
840 MHz için sıfır hücre bulunmuştur. Bu nedenle yalnız bu alıcı seri numarası
ve frekanslarda bilinen-spur kapısı uygulanır; bantların tamamı bastırılmaz.
Kanıt `results/evidence/phase08/receiver-spur-harmonics-36877e47.json`
dosyasındadır. Ölçüm, bağlı harici vericinin RF ürettiğini veya hedef yayının
frekansını kanıtlamaz.

2 Eylül 2026 tarihli 955,7 MHz tanısında tek-kare OS-CFAR ile zayıf kararlı
yayın arasındaki açıklık fiziksel olarak ölçülmüştür. Operatör frekansı
açıkladıktan sonra yapılan iki bağımsız HackRF ayarında tepe tam
955.700.000 Hz'de kalmış, ortalama P/N 8,04 ve 8,06 dB olmuştur. Aynı hücrenin
TX açık/kapalı farkı 7,73 ve 7,66 dB; 6 dB üstü kare oranı açıkta %88,1/%86,7,
kapalıda %6,3/%7,9 ölçülmüştür. Bu kayıt tanı ve kalibrasyon kanıtıdır; frekans
önceden açıklandığı için kör arama kabulü değildir.

Bu açıklık için FPGA'nın 9,33 dB tek-kare OS-CFAR profili değiştirilmemiştir.
Ham 8 MHz RX önizlemesinde en az 32 kare kullanan ayrı bir koherent olmayan
bütünleştirme yolu eklenmiştir. Bilinmeyen frekansta aday olabilmek için
ortalama P/N en az 6 dB, aynı hücrenin kare doluluğu en az %75 ve bağımsız
ikinci LO'da aynı mutlak RF frekansı şarttır. Sonuç `RX 2 AYARDA` olarak
etiketlenir; FPGA doğrulaması sayılmaz. Fiziksel dosya tekrarında açık iki LO
955.700.000 Hz'i %88,8/%86,9 dolulukla tek aday üretmiş, kapalı iki LO sıfır
aday üretmiştir. Canlı TX-kapalı 955,4–956,0 MHz denemesi de sıfır adayla
tamamlanmıştır. Frekansı açıklanmamış canlı geniş bant kabulü hâlâ açıktır.
Tanı kayıtları `build/acceptance/rx-survey/blind-800-1100-20260902/` altındadır.

Aynı kaba RX karesinde birden fazla doğrulanmış aday varsa en güçlü tek adayın
diğerlerini düşürmemesi için en fazla dört aday P/N sırasıyla sınırlı kuyrukta
tutulur ve iki-LO sınamasından sırayla geçirilir. Kuyruk operatör taramayı
durdurduğunda temizlenir. Uygulama girişinde tek örnek kilidi vardır; ikinci
BÂZ süreci alıcıyı paylaşmak üzere başlatılmaz.

4 Eylül 2026 sürekli sabit-bant akış bakımında otomatik ikinci-LO yeniden ayarı
ana alımı kesip görünümü baştan başlatıyor gibi gösterdiği için canlı akıştan
çıkarılmıştır. Aynı fiziksel I/Q karesinin FPGA olay yolu ile 8 MHz RX spektrum
yolunda zamansal ve frekansça uyuşması adayı sunmak için kullanılır; iki yol
bağımsız RF ölçümü olmadığı için sonuç sarı `FPGA ADAYI · FPGA + RX spektrumu
uyumlu` kalır. Yeşil `KARARLI RF ADAYI` ve kararlı sayaç yalnız iki farklı
fiziksel alıcı ayarında aynı mutlak RF frekansını geçen kayıt içindir. Bu ayrım
akışı sürekli tutar fakat harici verici doğrulaması iddia etmez.

Aday grafikten kaybolduğunda canlı kılavuz hemen kaldırılır. Liste satırı
yalnız 128 FPGA karesi, yaklaşık 262 ms, `Kısa süreli izleniyor` durumunda
tutulur; yeni gözlem gelmezse `Son görüldü` geçmişine geçer. Bu sunum
histerezisi FPGA olay ömrünü veya OS-CFAR kararını uzatmaz.

1 Eylül 2026 canlı tespit sunumu bakımında, FPGA olay numaraları değişse bile
birbirine en fazla 75 kHz uzaklıktaki doğrulanmış tepeler tek operatör satırında
gruplanmıştır. Bu yalnız sunum/geçmiş birleştirmesidir; FPGA'nın OS-CFAR,
geniş bant kurtarma veya 2/3 zamansal kararını değiştirmez ve iki yakın fiziksel
vericinin kesinlikle tek verici olduğunu iddia etmez. Canlı sayaç artık geçmiş
satırlarını içermez; geçmiş ayrı başlık altında tutulur ve eski seçime ait
kılavuz grafikte çizilmez. En yüksek tepe/gürültü oranlı güncel FPGA olayı
baskın sonuç olarak gösterilir. Tek LO FPGA sonucu ve 8 MHz host kaba adayı
sarıdır. Yalnız iki bağımsız alıcı ayarında yeniden görülen mutlak RF adayı
yeşildir. Host adayı tek başına FPGA doğrulaması veya kesin yayın sonucu
sayılmaz.

Yakın verici denemelerinde alıcı iç ürünlerini ve kırpılma riskini azaltmak için
sabit bant ve bant taraması başlangıç kazançları LNA/VGA `16/16 dB` yapılmıştır.
Operatör ölçülen seviyeye göre kazancı yükseltebilir. Bu değişiklik 10 MHz'teki
gözlemin çevresel yayın mı, HackRF saat sızıntısı mı veya başka bir alıcı iç
ürünü mü olduğunu tek başına belirlemez; anten/dummy-load, kazanç ve iki LO'lu
kontrollü tekrar hâlâ gereklidir. Tek canlı TX kapalı/açık tanı turu saha
Pd/Pfa kabulü yerine geçmediğinden KTR-4.1 tamamlanmış sayılmaz.

1 Eylül 2026 kullanıcı kontrollü canlı tanı turunda 8 MS/s, LNA/VGA 32/32 dB
ve 898,5/901,5 MHz fiziksel LO ayarlarıyla 900,191406 MHz bileşeninin P/N değeri
TX açıkken 24,56/24,77 dB, TX kapalıyken 3,99/3,46 dB ölçülmüştür. Tepe gücü
iki ayarda 21,30 ve 21,81 dB düşmüştür. Tam 900,000 MHz bileşeni TX kapalıyken
iki LO'da da kalmıştır; bu nedenle operatörün açıp kapattığı bileşen değildir ve
tek merkez DC çizgisi olarak da açıklanamaz. Kanıt
`results/evidence/phase08/live-user-tx-on-off-900mhz.json` dosyasındadır.
Verici durumu operatör beyanıdır, mutlak güç kalibrasyonu yapılmamıştır ve tek
tur verici kimliği ya da saha tespit olasılığı kanıtı değildir.

### Yeniden kontrol edilen durum

- Fiziksel Ethernet bağlantısı **Up / 1 Gbps**, bilgisayar Ethernet adresi
  **192.168.7.1/24** ve yerel 192.168.7.0/24 rotası mevcut. Beklenen kart adresi
  **192.168.7.2** için komşu durumu **Incomplete**, MAC çözülememiş ve
  **47007/TCP** denemesi zaman aşımına uğramıştır. Kablonun bağlı olmasıyla
  kart IP'sinin ve hizmetinin erişilebilir olması ayrı kontrollerdir. Kartın
  kapalı olduğu veya kablonun bozuk olduğu sonucu çıkarılmamıştır.
- Bir HackRF One, **v2.4.0 / API 1.11**, aygıt sorgusunda bulunmuştur.
- `live_ed.py::handle_response` görüntü için seçilen kareyi kart yanıtından
  sonra yayımlar. Grafik çizimini hızlandırmak bu bağı tek başına kaldırmaz.
- `rx_survey.py::run` görüntü karelerini biriktirir; bütün pencere ve adayların
  yeniden doğrulanması bittikten sonra `window_complete` ile bildirir.
  `survey_controller.py` bu kareleri peş peşe gönderir. Bu, sabit banttaki
  yaklaşık 30 Hz hedefinden farklı, kesintili bir tarama görünümüdür.
- Her tarama penceresinde yeni alım oturumu, süreç/bağlantı ve filtre durumu
  kurulmaktadır. Geçiş maliyeti ve aday başına ek ziyaret tarama süresine eklenir.
- Mevcut 128 kare × 4096 / 2 MS/s ayarında pencere başına yalnız örnek süresi
  **262,144 ms**'dir. 600 kHz sorumluluk adımıyla 1 MHz–6 GHz için
  **9999 pencere / 2621,18 s ≈ 43,7 dakika**; 2400–2500 MHz için
  **167 pencere / 43,78 s**; 5725–5875 MHz için **250 pencere / 65,54 s** eder.
  Bunlar ölçülmüş tur süreleri değil, yalnız
  örnek süresi toplamlarıdır; süreç açma, ayar, tekrar ve doğrulama hariçtir.
- Bütün 2 MHz karar penceresini dolduran yayın karşı örneği açıktır. Pencere
  kenarı için 600 kHz sorumluluk adımlı örtüşen ayarlar ve geniş adaylarda
  mutlak destek örtüşmeli ikinci ayar uygulanmıştır; bu kısım henüz gerçek
  kart/RF ile kabul edilmemiştir. Sabit 50 kHz tarama gruplaması, iki yakın
  yayının birleştirilmesi ve geniş yayının parçalara ayrılması bakımından ayrıca
  test edilmelidir. Hız profili değişirse hücre sayısıyla
  tanımlı eşik/koruma/genişlik sabitleri körlemesine taşınamaz.
- Alımda tek uç-kod örneği oturumu durdurabilir; taramada hem doygunluk hem
  aday taşması kazanç azaltma denemesine gidebilir. Fiziksel doygunluk, örnek
  kalitesi ve olay kapasitesinin taşması farklı nedenlerdir. Kontrolleri
  gevşetmeden bu ayrımın ve operatöre verilen bilginin doğrulanması gerekir.

### Hedef mimari ve karar sınırı

FPGA arayüzü çizmez; tespit işlemlerini yürütür. Bilgisayar alımı yönetir,
görselleştirme için güç spektrumu üretir ve Qt arayüzünü çizer. HackRF/PortaPack
spektrumunun görünür olması, bizim otomatik kararlı yayın kararımızın kanıtı
değildir. İkisi ayrı başarı koşuludur.

Öneri, **tek HackRF alımını** iki sınırlı tüketiciye ayırmaktır: gerçek I/Q'dan
görsel spektrum ve doğrulanmış FPGA tespit yolu. İkinci bir HackRF alım süreci
açılmaz. Görünüm kart cevabını beklemeyebilir; bu durumda "RX görüntüsü" ve
"FPGA tespiti" durumları açıkça ayrılır. Kart kesilirse yeni FPGA tespiti
üretilmez; eski adaylar canlıymış gibi tutulmaz. Önizleme devamı mümkünse
sınırlı alım modu olarak görünür; sahte bir donanım kabulü oluşturmaz.

8 MS/s ham alımdan daha geniş bir önizleme üretme seçeneği ölçülür. Görünen
sayısal aralık bütünüyle temiz/kullanılabilir bant varsayılmaz; DC, geçiş
bantları ve geçerli FPGA penceresi ayrıca işaretlenir. **Geniş önizleme eklemek
FPGA'nın o genişliğin tamamını tespit ettiği anlamına gelmez.**

Tespit için kaba arama ve ayrıntılı doğrulama ayrılır. Tercih edilen yön,
ölçülmüş zaman/frekans kapsaması olan geniş bant FPGA arama profili ve mevcut
dar bant doğrulama profilidir. Bunun kaynak/hız bütçesi ST-04'te belirlenir.
Alternatif olarak çok pencereli arama değerlendirilebilir; fakat yeniden
ziyaret süresi uzun kaldığı halde buna eşdeğer başarı denmez. 8 MS/s'yi mevcut
4096 FFT ve aday yoluna yalnız bir sabit değiştirerek vermek kabul edilmez.
FFT boyunu küçültmek de tek başına toplam I/Q yükünü azaltma garantisi değildir.
Görünüm için bilgisayarda yapılan hesap, FPGA doğrulaması olarak etiketlenmez.

### Sıralı iş paketleri

| Sıra | Yapılacak iş | Tamamlanma kanıtı |
|---|---|---|
| ST-01 | Güncel kaynak/donanım kimliğini kaydet; Ethernet linki, ARP, kart IP'si, Linux açılışı, hizmet, FPGA ve DMA durumunu ayırarak teşhis et. Gerekirse mevcut UART erişiminden kart durumunu oku. | Doğru kart/hizmet kimliğiyle protokol el sıkışması ve kayıtlı I/Q için gerçek kart yanıtı. TX gerekmez. Ağ/boot ayarı ölçümden önce varsayımla değiştirilmez. |
| ST-02 | Güncel akışın uçtan uca sürelerini ölç; USB, filtre, kuyruk, Ethernet, FPGA/ARM ve ekran zamanlarını ayır. Bağımsız test ailelerini ve kabul zarfını algoritma ayarından önce dondur. | Kaynak hashli başlangıç ölçümü; örnek kapsamı, kare kayıpları, kuyruk üst sınırı, p50/p95/p99 gecikmeler, RAM/CPU ve taze görüntü hızı. Eski kaynak uyuşmazlığı korunur; yeni kanıt ayrı üretilir. |
| ST-03 | Alım/görünüm/tespit beklemelerini ayır; GUI iş parçacığından görsel FFT'yi çıkar; sınırlı tampon, frekans/oturum kimliği ve veri yaşı kullan. Pencere sonunu beklemeyen gerçek önizleme ekle. | Kart yavaş/kesik durumunda doğru etiketler; sahte aday yok; aynı I/Q iki tüketicide doğru frekans ve zamanla izlenir; görünüm tespiti yavaşlatmaz. |
| ST-04 | 2 MS/s'nin ayrıntılı doğrulamadaki yerini ve daha geniş arama profilini ölçerek seç. Aynı veride bant genişliği, frekans ayrıntısı, zaman kapsaması ve işlem maliyetini karşılaştır. | Python referansı, RTL kaynak/hız tahmini ve deney sonucu bulunan mimari karar. Hangi bandın hangi süreyle gözlendiği açık; yeni örnek hızı çalışıyor diye varsayılmaz. |
| ST-05 | Dar bant OS-CFAR'ı koruyarak geniş bant gürültü referansını düzelt; çok ölçekli bütünleşik güç ve emisyon sınırlarını karşılaştır. Bölgeyi dolduran yayın, yakın/uzak güçlü-zayıf yayın ve pencere kenarı için birleştirme/ayırma ile zamansal doğrulamayı ele al. | Bağımsız testlerde tespit/kaçırma/yanlış olay sonuçları ve önceki karşı örneklerin çözümü. Gürültü referansı geçersizken "yayın yok" denmez. Yalnız başarısız vektöre göre eşik düşürülmez. |
| ST-06 | Seçilen yöntemi Python, C/PS ve SystemVerilog/PL görev paylaşımıyla birlikte uygula; taşma, sabit nokta, tampon sınırı, akış bekletme, paket ve yaşam döngüsünü doğrula. | Bit-doğru eşdeğerlik, RTL benzetimi, sentez/yerleşim/zamanlama, gerçek kart sonucu ve güncel kaynaklarla işlem kapasitesi. Veri atılarak hız iddiası üretilmez. |
| ST-07 | Frekans taramasını kaba arama → aday doğrulama → yeniden ziyaret şeklinde düzenle. Sürekli alım/ayar değiştirme desteğini incele; her geçişte filtre yerleşmesi ve eski karelerin elenmesini koru. Yakın frekansları, pencere kenarlarını ve taramanın adaylarla meşgul edilmesini test et. Tespit ekranını operatör akışına göre tamamla. | Bandı tarama ve yeniden ziyaret süreleri, aday doğrulama gecikmesi ve gerçek gözlem kapsamı. Tarihsel panorama canlı sabit bant waterfall'u gibi gösterilmez; başarısız pencere kapsam dışı kalır. |
| ST-08 | Önce kayıtlı I/Q ve pasif ortamla bütünlük/akıcılık, sonra kontrollü bilinen yayınlarla doğruluk, en son frekansı tespit yazılımına verilmeyen yayınla uçtan uca kabul yap. | Tekrarlı kabul paketi, geçerli çalışma zarfı, yanlış olay/dakika, kaçırma, ilk tespit gecikmesi ve arayüz kaydı. Açık kalan test varken tespit aşaması kapatılmaz. |

ST-04'ün mimari seçimi ST-05/06'yı belirler; bunlar doğrulanmadan ST-07'nin yeni
geniş arama modu ürün özelliği sayılmaz. Araştırma sonuçları mevcut tasarımın
kapasitesini aşarsa gerekçesi görünür olur; başarı ölçütleri sonradan küçültülmez.
ST-01–ST-03 uygulanmış; ST-07'de 600 kHz sorumluluk adımlı örtüşen ayarlar,
geniş adayın mutlak destek aralığıyla ikinci ayarda doğrulanması ve arayüzde kaba
aralık gösterimi yazılım testinden geçmiştir. Ölçülmüş tam tur süresi, kart/RF
kenar kabulü, bütün pencereyi dolduran yayın ve genel RF doğruluğu açık kalır.

Sabit banttaki 2/3 zamansal sonuç artık `sinyal tespit edildi` diye sunulmaz;
`FPGA adayı` olarak sarı gösterilir. Ham 8 MHz RX merkezi gerçek LO frekansıyla
ayrı yazılır ve bu merkezdeki DC/LO çizgisinin tek başına yayın olmadığı
belirtilir. Tarama satırı ancak aynı mutlak RF özelliği ikinci fiziksel LO
ayarında da görülürse `2 AYARDA` olur. Harici test vericisiyle ilişki için ürün
aynı aralık/kazanç/süreyle `TX kapalı referans` ve `TX açık karşılaştırma`
turlarını ayrı kaydeder. TX açık turda referansta bulunmayan veya aynı gerçek
kazançta iki LO'da ortalama tepe gücü en az 6 dB artan aday sarı
`A/B: YENİ ADAY/GÜÇLENDİ` olarak ayrılır. Tek karelik tepe veya yalnız P/N
artışı yeterli değildir. Bu etiket laboratuvar karşılaştırmasında değişen bir
özelliği gösterir; harici verici kimliği veya saha Pd/Pfa kabulü değildir.
Karşılaştırma tam kapsam, aynı alıcı ve yazılım kaynak hash'leri, taşmasız ve
doyumsuz alım, eksiksiz FPGA cevapları ister. Farklı gerçek kazançlar belirsiz
kalır. Eski, harici TX durumu belirtilmeyen kayıtlar A/B referansı sayılamaz.

Tam pencereyi dolduran yayınların araştırılması için ayrıca koruma kareleri
sonrasındaki kanal seçici çıkışının toplam I/Q gücü kaydedilir. Aynı ayarda
2 MHz kanal gücü en az 6 dB artarsa `A/B: KANAL GÜCÜ` tanı satırı gösterilir.
Bu host hesabıdır; FPGA geniş bant tespiti, ikinci LO kontrolü, yayın sınırı
veya verici sayısı değildir. 6 dB deneysel ayırma eşiğidir, kalibre edilmiş
yanlış alarm olasılığı değildir. Fiziksel kapalı/açık tekrarı hâlâ gereklidir.

ST-04'ün host kaba arama kolu ADR-0038 ile uygulanmıştır. 8 MHz/16.384 hücre
görüntü gücü dörderli enerji toplamıyla 4.096 hücreye indirilir; vektörize
OS-CFAR sonucu kanonik aday alanlarıyla eşdeğerdir ve mevcut geniş bant yolu
korunur. Arayüz kesikli `kaba RX adayı` ile düz sarı zamansal `FPGA adayı`nı
ayırır; ikisi de tek başına harici verici kanıtı değildir.
100 kHz–4 MHz sentetik aileleri 32/32 geçmiştir. 6 MHz 31/32 olduğu için kabul
zarfında değildir; 8 MHz tam doluluk açık kalır. Otomatik kaba aday→FPGA yeniden
ayar bağı ve fiziksel RF kabulü tamamlanmadan ST-05, ST-07 ve PHASE-08 kapanmaz.

4 Eylül 2026'da ST-04 için eşikleri değiştirmeyen ilk kaynak bağlı arama profili
ölçümü yapılmıştır. 20 MHz–6 GHz aralığında mevcut 600 kHz sorumluluklu,
pencere başına 128 karelik 2 MHz FPGA/ARM taramasının yalnız ham örnek toplama
alt sınırı 9.967 pencere ve 2.612,789248 saniyedir. Aynı aralık için mevcut
DC-güvenli 8 MS/s kaba plan, pencere başına üç gözlem varsayımıyla 2.392 pencere
ve 14,696448 saniye ham örnek alt sınırı üretmiştir. Bağlı HackRF ile RF amp ve
anten portu gücü kapalı, LNA/VGA 16/16 dB iken resmî `hackrf_sweep`, 1 MHz güç
hücreli tek pasif turda aralığı 1.196 satır ve 5.980 hücreyle boşluksuz
kapsamış; süreç duvar süresi 0,798792 saniye ölçülmüştür. Kanıt
`results/evidence/phase08/st04-search-profile-baseline-v1.json` ve aynı hashle
bağlı `.csv` kaydıdır. Bu tek tur host kaba arama ölçümüdür; FPGA doğrulaması,
kısa yayın yakalama olasılığı, tekrarlı tarama zamanı veya RF doğruluk/Pd/Pfa
kabulü değildir. Aynı I/Q üzerinde tekrarlı profil karşılaştırması ve kontrollü
yayın matrisi henüz bulunmadığı için bu ilk ölçüm tek başına ST-04'ü kapatmamıştır.

Aynı gün tekrarlı çözünürlük/zaman ölçümü 1 MHz, 100 kHz ve 25 kHz istenen
hücre genişliklerinde yapılmıştır. Her profil üç bağımsız `hackrf_sweep`
sürecinde üçer tur, toplam 27 tam RX-only sweep içermektedir. Turların tamamı
20 MHz–6 GHz aralığını boşluksuz kapatmış; başlangıç ve bitişte USB shortfall
sayacı sıfır kalmıştır. Tur başına süreç medyanı 1 MHz'de 0,768583 saniye,
100 kHz'de 0,764985 saniye ve 25 kHz'de 0,794019 saniyedir. Ölçülen %3,80
zaman yayılımına karşılık tur başına ham CSV medyanı yaklaşık 129 kB'dan
2,00 MB'a çıkar; en ince profilin çıktı yükü en kaba profilin 15,57 katıdır.
Gerçek araç hücreleri 1 MHz, 98,03922 kHz ve 24,87562 kHz'dir. Bu ölçüm yalnız
host tarama zamanı, kapsama ve çıktı maliyetini kanıtlar; küçük süre farkına
göre profil seçilmemiştir. Kanıt
`results/evidence/phase08/st04-sweep-resolution-v1.json` ve hash bağlı `.zip`
arşividir. Aynı I/Q karşılaştırması ile kontrollü kör yayın Pd/Pfa kapısı
bulunmadan bu çözünürlük ölçümü tek başına FPGA tespiti veya ST-04 kapanışı
sayılmaz.

ST-04 aynı-I/Q karşılaştırmasında iki LO'ya ait 955,7 MHz açık ve kapalı
fiziksel CI8 kayıtlarının aynı 0,507904 saniyelik bölümü kullanılmıştır. Hedef
frekans aday üretimine verilmemiş, yalnız sonuç değerlendirmesinde
kullanılmıştır. 4.096 ve 8.192 FFT hedefi kaçırmıştır. Mevcut 16.384 FFT,
955.700.000 Hz hedefi iki LO'da geri kazanmış ve kapalı iki LO arasında ortak
aday üretmemiştir. 32.768 FFT hedefi geri kazanırken kapalı kayıtta bir; 65.536
FFT ise üç ortak aday üretmiştir. En ince profil ayrıca Python referansında
yaklaşık 0,85–0,90 gerçek zaman oranına çıkmıştır. Bu veri, mevcut 16.384
değerinin tek bu kayıtta doğru denge olduğunu gösterir; profil ürün için
seçilmiş veya tüm banda genellenmiş değildir. Kaynak ve fiziksel giriş hashleri
`results/evidence/phase08/st04-same-iq-resolution-v1.json` içindedir.

ADR-0041, bu ölçümlerden kontrollü kör RF deneyi için üç aşamalı aday
mimarisi çıkarır: hostta 20 MS/s ve 25 kHz istenen hücreyle tam bant
`hackrf_sweep`; aday çevresinde hostta 8 MS/s, 16.384 FFT ve iki LO; son
kararda mevcut FPGA/ARM 2 MS/s, 4.096 FFT zinciri. Mevcut RTL'nin yaklaşık
991,375 kare/s işlevsel kapasitesi, 2 MS/s için gereken 488,281 kare/s hızını
karşılar. Aynı 4.096-hücre zinciri doğrudan 8 MS/s'de gereken 1.953,125
kare/s hızın yalnız %50,76'sına ulaşır; tam route tasarımı 48.040/53.200 LUT
(%90,30) kullanır. Bu hesap yalnız mevcut RTL'nin doğrudan 8 MS/s tekrar
kullanımını eler. Mimari kontrollü kör deney için kilitlenmiş, ürün için
seçilmemiştir. Kaynak bağlı kayıt
`results/evidence/phase08/st04-hierarchical-detection-architecture-v1.json`
dosyasındadır. Bu kanıt ST-04 mimari seçimini tamamlar; ST-05–ST-08 algoritma,
uygulama ve kör RF kabul kapıları açık kalır.

Kullanıcının 4 Eylül 2026 onayıyla ST-05 geniş bant Python referansı
seçilmiştir. Dar bant OS-CFAR ve katsayısı korunur. Yeni referans sekiz karede
32/64/128/256 hücreli enerji ölçeklerini, iki bağımsız 64 hücreli flank
referansını, 3 dB flank uyumunu ve en az `%75` zaman doluluğunu birlikte ister.
Pencere kenarında bağımsız referans yoksa `retune_required` olur. Tam pencereyi
dolduran gürültü benzeri yayın tek ayardan alıcı gürültüsüne karşı tanımlanabilir
olmadığı için sistem mutlak `yayın yok` iddiası üretmez.

Önceden dondurulmuş sentetik holdout 960/960 dizide bütün kapıları geçmiştir:
256 geniş yayın, 128 güçlü-zayıf ayrım, 64 yakın yayın birleştirme, 192 gürültü,
128 kenar, 64 geçici, 64 kalıcı ve 64 tam-pencere tanımlanabilirlik dizisi.
Bu, canlı RF veya ürün kabulü değil ST-06'ya girdi olan Python referansıdır.
Karar `docs/decisions/ADR-0042-PHASE08-ST05-WIDEBAND-REFERENCE.md`, kaynak bağlı
kanıt `results/evidence/phase08/st05-wideband-holdout-v2.json` içindedir. V2,
aynı adayın iki gerçek desteğe sayılmasını engelleyen bire bir eşleme düzeltmesini
içerir; sahne ve eşikler v1 ile aynıdır.
**ST-05 tamamlanmıştır; ST-06–ST-08 açık kalır.**

ST-06'nın güncel ürün bölümü PL/PS olarak ikiye ayrılmıştır. FPGA; Hann,
4.096 nokta FFT, UQ28.30 güç ve OS-CFAR hücre kararını üretir. ARM; tam 32 KiB
güç karesinden sekiz karelik geniş bant kararını, dar/geniş örtüşme bastırmasını
ve temporal olay yaşam döngüsünü üretir. Bu görev paylaşımıyla routed LUT
kullanımı `%90,30`dan `%36,82`ye düşmüş ve 50 MHz zamanlama geçmiştir. Dört
yuvalı CPU0/CPU1 boru hattı kartta beş tekrarda 2 MS/s alt sınırını geçmiş;
güncel ARM kaynakları aynı XSA ile PetaLinux ürün imajına alınmıştır. Paket
5.679/5.679, tam imaj 6.090/6.090 görevde hatasızdır ve imaj içindeki hizmet
ikilisinin hash'i hazırlanan ikiliyle aynıdır. Kanıt
`results/evidence/phase08/st06-product-integration-v1.json` içindedir. Aynı
ürün imajının kartta soğuk açılışı, fiziksel hizmet yaşam döngüsü ve kontrollü
kör RF doğruluğu açık olduğundan ST-06 henüz tamamlanmamıştır.

HackRF'ı ZedBoard USB OTG host portuna doğrudan bağlamak ST-04'te aday mimari
olarak tutulur. Bu bağlantı PC→Ethernet kopyasını kaldırabilir fakat HackRF'ın
anlık RF bant genişliğini artırmaz. 8 MS/s CI8 akış yaklaşık 16 MB/s, 20 MS/s
yaklaşık 40 MB/s ham USB yüküdür. ZedBoard USB 2.0 host, PetaLinux `libusb` /
`libhackrf`, kararlı 5 V besleme ve PS DDR→PL aktarım yolunun ayrı fiziksel
kabulünü gerektirir. Doğrudan OTG, mevcut host ve geniş kaba arama profilleriyle
ölçülmeden seçilmiş mimari sayılmaz.

### Uygulama ve ölçüm kaydı

- UART COM6/115200 üzerinden kartın Linux giriş ekranı görülmüş, sonrasında ağ
  köprüsü etkinleştirilip SysV çalışma seviyelerine kaydedilmiştir.
  `192.168.7.2:47007` TCP hizmeti erişilebilirdir ve 136-kare fiziksel FPGA
  duman testi sıfır taşıma hatasıyla geçmiştir. Yeniden açılış sonrası hizmet
  erişimi ayrıca denetlenmiştir. Karttaki P09 bitstream'i ADR-0040'ın geniş bant
  ve zayıf-kararlı aday yolunu içerir; bilinen dijital çerçeveyle kart kabulü
  geçmiştir. Kör canlı RF doğruluğu bu dijital kabulden ayrı ve açıktır.
  Ethernet durumu USB shortfall nedeni değildir.
- `LiveEDPreview`, kart yanıtı taşımayan ayrı bir I/Q görüntü kaydıdır. Kanal
  seçici bütün kareleri işler; önizleme callback'i yalnız son ham görüntü işini
  bırakır ve hemen döner. Ayrı
  spektrum işçisi 16.384 noktalı görsel FFT'yi hesaplar. Hazır sonuçta GUI
  bildirimi de yalnız son görüntüyü tutar. Gerçek tespit yalnız doğrulanmış
  `LiveEDResponse` üzerinden gelir. Her I/Q karesi kanal seçicide işlenir;
  görüntü için yaklaşık 32,55 Hz sağlayan 15-kare aralığı kullanılır.
- Sınırlı 512-kare alım ve 64-kare kanal kuyrukları, son 4096 süre örneği,
  kuyruk üst sınırı ve USB istatistiği kaydedilir. GUI bildirimi yalnız son
  görüntüyü tutar; tespit/USB kaybı başarıya çevrilmez. Veri yaşı bilgisayarın
  I/Q bloğunu aldığı andan itibaren ölçülür; anten gecikmesi değildir.
- "Yalnız RX Önizleme" kart bağlantısı olmadan alıcı grafiğini sınar; başlıkta
  FPGA tespitinin kapalı olduğu yazılır ve aday/olay üretilmez. Normal canlı
  ED oturumunda FPGA yanıtı ve DMA doğrulaması zorunlu kalır.
- Pahalı kenar yumuşatmalı geniş çizgi yerine tek fiziksel piksel çizgi,
  NumPy–Qt toplu nokta aktarımı ve görünmeyen grafiği çizmeme uygulanmıştır.
  FFT/güç işlemi GUI dışında kalır; genel durum alanları 4 Hz, gerçek görüntü
  yaklaşık 32,55 Hz güncellenir. Grafik için tepe koruyan izdüşüm tespit
  algoritmasının örneklerini azaltmaz. Bu çizim seçimi
  [PyQtGraph performans açıklamasıyla](https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/plotdataitem.html)
  uyumludur; asıl kabul gerçek alım ölçümüdür.
- Başlangıç canlı GUI denemelerinde USB kaybı ve saniye düzeyinde gecikme
  bulundu. Ekransız aynı alımda kayıp yoktu. Ayrı kanal seçici süreci deneyi
  sorunu çözmedi ve ürün kodunda tutulmadı. Başarısız ölçümler
  `build/acceptance/detection-closure` altında korunur. Bir eşzamanlı
  `grabWindow()` denemesi çizim kilitlenmesi oluşturduğundan zaman ölçümünde
  ekran yakalama kullanılmaz; grafik doğrulaması ayrı yapılır.
- Çizim düzeltmesi sonrası 6.144-kare gerçek RX ölçümünde sıfır USB taşması,
  30,53 taze görüntü/s ve yaklaşık 21 ms p95 sunum yaşı görüldü. Tekrarlanabilir
  `scripts/measure_live_rx_display.py` ile 32.768 kare / yaklaşık 67 saniye
  ölçümünde de sıfır taşma, 30,52 Hz, 36,62 ms p95 güncelleme aralığı ve
  21,71 ms p95 veri yaşı elde edildi. Bunlar FPGA/Pd/Pfa kabulü değildir.
- Görsel önizleme artık aynı HackRF alımının ham **8 MS/s × 16.384** örneğini
  gösterir; FPGA'ya giden kanal seçilmiş **2 MS/s × 4.096** kare değişmez.
  Frekans ekseni gerçek ham alım merkezine bağlıdır. FPGA'nın doğrulanmış
  ±700 kHz sahiplik alanı gölgeli bant, izleme merkezi ayrı çizgi olarak
  gösterilir; 8 MHz görünüm FPGA tespit kapsamı diye etiketlenmez.
- Windows ikili alım borusu 4 MiB ile sınırlanmıştır; 8 MS/s CI8 akışta
  yaklaşık 262 ms zamanlama payıdır. `hackrf_transfer` Windows'ta normalin
  üzerinde süreç önceliğiyle çalışır. Ekran FFT'sinin kanal seçici çağrısında
  yapıldığı sonraki 15 dakikalık olumsuz koşu 1.223 USB taşması ve 287,84 ms
  p95 görüntü yaşıyla doğru biçimde başarısız olmuştur; kayıt silinmez.
  Önizleme FFT'si ayrı işçiye alındıktan sonraki bir tekrar, bütün kareleri
  işlemesine karşın HackRF aracında tek 36.640 baytlık USB taşması verdiği için
  fail-closed kalmıştır. Windows ikili borusu 4 MiB'ye çıkarılıp RX süreci
  normalin üzerinde önceliğe alındıktan sonra güncel kaynakla 15 dakika /
  439.454 kare fiziksel RX-only kabulü geçmiştir: sıfır USB taşması, ham kuyruk
  tepesi 28/512, kanal kuyruğu tepesi 7/64, 30,51 taze görüntü/s, 36,24 ms p95
  çizim aralığı, 21,82 ms p95 ve 71,00 ms azami alımdan sunuma yaşı. Kanal
  seçici önizleme çağrısının p95 süresi 0,023 ms'dir. Hash bağlı kaynak ve ölçüm
  `results/evidence/phase08/live-rx-display-8msps-v1.zip` içindedir. Bu kayıt
  FPGA/Pd/Pfa veya kontrollü RF doğruluğu kabulü değildir.
- ADR-0039 ile aynı 193 tap/4:1 kanal seçici C++17 AVX2/FMA3 çekirdeğine
  alınmıştır. Beş tuning ofsetinde 80 ardışık kare NumPy referansına karşı
  sıfır CI8 LSB farkıyla geçmiş; 2.000 çağrıda p95 `0,524815 ms` ölçülmüştür.
  Fiziksel HackRF yolu derlenmiş çekirdek yoksa yavaş referansa sessizce düşmez.
  Kaynak/DLL bağlı kayıt `native-channelizer-v3.json` dosyasındadır.
- Statik grid/etiket Canvas katmanları RF karesinden ayrılıp görünüm 15 karede
  bire çekildikten sonra güncel 60 saniyelik koşu 32,15 taze görüntü/s,
  40,04 ms p95 çizim aralığı ve 20,72 ms p95 veri yaşıyla görünüm kapılarını
  geçti. Aynı koşuda üç USB shortfall bulunduğu için genel sonuç fail-closed
  başarısızdır; `live-rx-display-8msps-v2.json` bu açık kapıyı korur.
- Uygulamasız `hackrf_transfer → NUL` kontrolünde de bir adet 832 bayt
  shortfall oluşmuştur. Bağlı cihaz USB 2.0 High-Speed'dır, dört başka aygıtla
  aynı bus üzerindedir ve üretici doğrulama uyarısı verir. Farklı fiziksel port
  ve bilinen iyi veri kablosuyla A/B yapılmadan güncel kaynak için sıfır-taşma
  kabulü iddia edilmez. USB seçmeli askıya alma deneyi fayda sağlamamış ve güç
  ayarı eski değerine döndürülmüştür.
- Tarama görüntüsü pencere tamamlanmasını ve adayların ikinci ayarını
  beklemeden, koruma karelerinden sonra yayımlanır. FFT arka plandadır;
  en fazla 64 bildirimli kuyruk yalnız ara önizlemeleri birleştirir.
  Frekans geçişi, yeniden deneme ve başarısız pencere grafiği temizler.
  Pencere kapsamı yalnız bütün alım, kart ve ikinci doğrulama tamamlanınca
  kayda geçer. Tamamlanınca eski satırlar peş peşe yeniden çizilmez.
- `candidate_drop` artık doygunluk gibi kazanç azaltılarak gizlenmez;
  kapasite kaybında tarama durur ve pencere başarılı sayılmaz. Gerçek
  `iq_saturation` için mevcut sınırlı düşük kazanç denemesi korunur.
- 1–1,5 GHz fiziksel taramanın tamamlanan 499. penceresinde
  `1.299.995.941,9 Hz` dar adayı ilk ayarda 73, ikinci LO ayarında 26 kare
  gözlenmiştir. İkinci ölçüm `1.299.995.960,8 Hz` olup merkez farkı yaklaşık
  19 Hz'dir; iki alımda P/N sırasıyla 9,85 ve 13,00 dB, USB taşması ve I/Q
  kırpılması sıfırdır. Kayıt
  `build/acceptance/rx-survey/3997b5e3b6554d919beccae99fdec1f7.jsonl`
  içindedir. Sonraki tamamlanmış 1,28–1,33 GHz turunda aynı 1,3 GHz çizgisi
  görülmemiştir; bu nedenle iki tur tek başına kullanıcı vericisine atıf
  oluşturmaz. O turdaki çok sayıdaki yaklaşık 4 MHz aralıklı çizgi de yalnız
  iki-LO kontrolüyle harici yayın sayılamaz. Kontrollü TX kapalı/açık turu
  ST-08 kapanışının açık fiziksel girdisidir.
- 31 Ağustos gece tekrarında
  `build/acceptance/rx-survey/9563e724b4424dc2a951ce8b8d344f0d.jsonl`
  1,28–1,33 GHz aralığını 38,397 saniyede 84/84 pencereyle tamamlamıştır.
  10.752 birincil kare ve kabul edilen adaylara ait 480 ikinci-LO karesinde
  USB taşması, doyum veya taşıma hatası yoktur; yeniden deneme gerekmemiştir.
  1,3 GHz çevresindeki üç ayarda toplam kanal gücü yaklaşık -19,2 dBFS iken
  çevrede yaklaşık -32 dBFS ölçülmüştür. Buna rağmen FPGA tarama listesinde
  1,3 GHz adayı yoktur; yalnız aday listesiyle yayın yokluğu söylenemez.
- Aynı anda ayrı, sınırlı I/Q kayıtları alınmıştır:
  `build/acceptance/rx-survey/diagnostic-08d7f4d1bbe342fdb98c5deefba2b902/`.
  1.300 MHz çıkış merkezi, 1.298,5 ve 1.302,5 MHz fiziksel LO ile ayrı ayrı
  120 kullanılabilir kare kaydedilmiştir. İkisinde de ortalama spektrumun
  en güçlü hücresi 1.299,985352 MHz yakınıdır. Kanal güçleri -19,069 ve
  -19,331 dBFS; ayrı 1.310 MHz kaydında -31,602 dBFS'tir.
  `capture.json` gerçek alım sonuçlarını ve CI8 SHA-256 bağlarını taşır;
  `rf-power-diagnostic.png` bu verileri gösterir. Harici TX durumu beyan
  edilmediğinden bu kayıtlar kullanıcı vericisinin kimliğini doğrulamaz.
- Saklanan aynı CI8, RF alımı yapılmadan mevcut karta tekrar gönderilmiştir.
  `fpga-baseline.json` içinde hedefin merkezi ±50 kHz'ini kapsayan kararlı
  desteğin sayısı iki 1.300 MHz kaydında da 0/120'dir. Aynı kayıtların
  periyodik Hann ve güncel yazılım referansı tekrarında (`replay.json`)
  ADR-0037 iki taraflı kurtarması 120/120 + 120/120 karede bu desteği üretir;
  1.310 MHz karşılaştırma kaydında 0/120 üretir. Bu kontrollü yöntem
  karşılaştırması, canlı vericinin açılıp kapanmasından bağımsız tekrar edilebilir.
  Yazılım sonucu yeni RTL'nin karta yüklenmiş veya fiziksel kabulünün geçmiş
  olduğu anlamına gelmez. Yeni imaj ayrı `build/p0/flanked-20260831` dizininde
  hazırlanır; eski çalışan bitstream ve kanıtları korunur.

Güncel kod eski FPGA fiziksel raporlarının kaynak özetlerinden farklıdır. Bu
kontroller gevşetilmez; güncel 15 dakikalık RX/görüntü kanıtı eski FPGA
bitstream kabulünün yerine geçmez. Alım/görüntü kabulü ve geniş bant karar
deneyleri ayrı kaydedilir.

### Algoritma uygulaması ve açık deneyler

OS-CFAR'ın referans hücrelerinin ve bölgesel medianın sinyalle dolması aynı
sorunun iki görünümüdür. İncelenecek çözümler: farklı genişlikte enerji
pencereleri, güvenilir boş bölgeleri ayırarak gürültü kestirimi, frekans/kazanç
bağımlı kalibrasyon ve güvenilirliği izlenen zaman referansı. Bir yayını uzun
süre gözlemleyip onu otomatik olarak gürültü tabanına katma hatası engellenir.
Gerçekten boş bir referans bulunamıyorsa belirsizlik raporlanır; tüm pencereyi
dolduran gürültü benzeri yayını yalnız yerel normalleştirmeyle koşulsuz ayırma
garantisi verilmez.

ADR-0037 ile 257 bin ve üzeri destekler için mevcut on altı bölgesel medianın
dördüncü küçüğünü kaba referans yapan, adayın iki yanında birer bağımsız tam
bölge ve `2,5` median oranı isteyen ek yol uygulanmıştır. Mevcut 41–256 bin
bölgesel yol ve rank-24/32 OS-CFAR korunur. 512/1024/2048 bin sentetik CI8/Hann
pozitiflerinde 64/64; düz, 12 dB eğimli ve 12 dB basamaklı negatiflerde 0/64
geniş aday sonucu alınmıştır. 10 kat güç oranındaki konum çalışmasında
384–2048 bin için 672/672, 5 katta 636/672 kare `%80` kapsama ulaşmıştır.
Bu sonuçlar saha Pd/Pfa değeri değildir.

Yazılım referansı, sabit noktalı model ve SystemVerilog zinciri birlikte
güncellenmiştir. Sekiz vektörde 512/2048-bin pozitifler ve 12 dB basamak
negatifi dahil metadata farkı sıfırdır; geniş bant alt-aşaması 44.886 çevrim,
nihai azaltıcı 45.557 çevrimdir. Paket sınırı 63 aday ve 379 AXI64 beat ile
geçmiştir. Ardından Vivado 2025.2 ile tam ZedBoard tasarımı sentez, yerleştirme,
yönlendirme ve 50 MHz zamanlama kapılarını geçmiştir: setup WNS `+0,046 ns`,
hold WHS `+0,015 ns`, sıfır failing endpoint, sıfır route ve DRC hatası.
Bitstream, FPGA Manager ikilisi ve bitstream içeren XSA üretilmiştir. Bu yerel
yapı sonucu kart yükleme ve fiziksel RF kabulünün yerine geçmez; kartta çalışan
eski imaj yeni algoritmayı içeriyormuş gibi gösterilmez.

Geliştirme ve kör doğrulama kayıtları/seeds ayrı tutulur. Testler yalnız ton
ve ideal plato içermez: farklı işgal genişlikleri, gürültü benzeri/modüle
yayınlar, iki yakın yayın, güçlü yanında zayıf yayın, renkli gürültü, DC/ayna,
doygunluk, frekans kayması, aralıklı yayın, sınırdan taşan ve bütün pencereyi
dolduran yayınlar bulunur. SNR'nin hangi bantta tanımlandığı, yayın süresi,
kazanç ve frekans konumu kayıt altına alınır. Geniş bant tespitinin kaba sınırı
raporlanır; bu iş paketi parametre çıkarımı fazını açmaz.

Geniş bandın yalnız bir kenarında birkaç OS-CFAR hücresi bulmak, yayının
bütününü doğru tespit etmekle eş tutulmaz. Tam ve kısmi gözlem ayrı ölçülür.
2/3 doğrulama ve olay kapanışı, yeni kare süresi ve tarama ziyaretleriyle
uyumlu olacak şekilde gerçek zaman biriminde değerlendirilir. Tespit edilmiş
emisyon, otomatik olarak "drone" veya "tehdit" diye sınıflandırılmaz.

### Arayüz kapsamı

- Ana alanda geniş ve okunur spektrum/waterfall; sabit renk ölçeği, güç skalası,
  imleç frekansı, ölçeği uydurma, tepe tutma ve gerektiğinde ortalama görünümü.
  Ortalama güç dB değerleri doğrudan toplanarak hesaplanmaz.
- 30 Hz çizim aralığı içindeki kısa yükselmeleri atlamamak için o aralığın
  tepe/ortalama özetleri değerlendirilir. Taze veriyi tekrar çizmek yeni
  gözlem sayılmaz; kapsanmayan aralıklar saklanmaz.
- Waterfall süre seçimi, gerçek örnek zamanı, boşluk gösterimi ve sınırlı
  bellek. Farklı frekans, kazanç, kaynak veya geçersiz kalite dönemleri tek
  homojen geçmişmiş gibi birleştirilmez.
- Üstte merkez frekansı, **görünen bant / FPGA'nın taradığı bant**, örnek hızı
  **MS/s**, alıcı kazancı, RX/FPGA durumu ve veri yaşı. Kalibrasyon yokken dBm
  veya ölçülmüş mutlak doğruluk gösterilmez.
- Tespit listesinde frekans/kaba aralık, doğrulanma durumu, ilk/son görülme ve
  göreli seviye; olay kimliği ve ayrıntılı iç sayaçlar ikincil tanı panelinde.
- Sabit bant waterfall'u ile geniş arama panoraması ayrılır. Panoramada her
  parçanın ölçüm zamanı, geçerli kapsamı ve yeniden ziyaret durumu vardır.
- Yakınlaştırma, frekans seçimi, durdurma/başlatma ve kayıt alma net olur.
  Bağlantı yok, tespit yok ve hiç gözlenmedi durumları farklı görünür.
- 1280×720, daha geniş ekran ve %150 ölçekle gerçek etkileşim kontrolü;
  ölçek/kazanç/frekans değişimlerinde geçmiş ve tespit kimlikleri karışmaz.

### Önerilen kabul hedefleri

Aşağıdaki sayılar şartnameden alınmış değerler veya kazanılmış başarılar
değildir; ST-02'de deney zarfıyla birlikte sabitlenecek mühendislik hedefleridir.

| Alan | Başlangıç hedefi / raporlama kuralı |
|---|---|
| Sabit bant canlı görünüm | 15 dakika boyunca yaklaşık 30 **taze veri** güncellemesi/s; p95 güncelleme aralığı ≤50 ms ve alımdan gösterime p95 yaş ≤150 ms hedefi. Aynı kareyi yeniden çizerek FPS artırma yok. |
| Akış bütünlüğü | Sıfır USB/CRC/sıra hatası ve sıfır tespit adayı düşümü hedefi. Hata olduğunda geçersiz aralık ve sebep açık; başarılı kabul yok. Kuyruk ve RAM zamanla büyümez. |
| İşlem payı | Gerçek zaman eşiğinin üzerinde en az %20 kapasite payı hedefi; aynı profilin hızlandırılmış kayıtlı I/Q yüküyle ölçülür. Canlı alımı hızlı gösterme anlamına gelmez. |
| Tespit doğruluğu | Önceden tanımlanmış bant genişliği/SNR/süre/konum zarfında ≥%95 tespit ve bilinen negatiflerde ≤1 yanlış doğrulanmış olay/dakika başlangıç hedefi. Her senaryo ayrı, tekrar sayısı ve güven aralığıyla raporlanır; yalnız toplu ortalama yetmez. |
| Tarama | Her arama aralığı için ilk ziyaret, tam tur, yeniden ziyaret ve doğrulama süreleri ayrı ölçülür. Hedef yayın süresinden uzun yeniden ziyaret aralığı varsa aralıklı yayın kabulü geçmez. Kesin saniye hedefi ST-02/04'te arama bandı ve yayın süresiyle dondurulur. |
| Frekans | FFT hücresi aralığı, kalibrasyon hatası ve ölçülen frekans hatası ayrı raporlanır; 488 Hz garanti etiketi kullanılmaz. |
| Yayın kapalı denemesi | Kullanıcının vericisinin kapalı olması bütün RF ortamının boş olduğunu kanıtlamaz. Yanlış alarm ölçümü için gerçek değeri bilinen kayıt veya kontrollü negatif düzen gerekir. |

Algoritma kabulünde yüksek SNR'li kolay örneklerin düşük SNR veya geniş bant
kaçırmalarını ortalamada gizlemesine izin verilmez. Mevcut karşı örnekler
saklanır; farklı veri üretim ailesinden bağımsız örnekler eklenir. Yeni kaynak
sürümü için yeni fiziksel kabul üretilir; eski kanıttaki hash değiştirilmez.

### Karşılaştırma ve bilimsel dayanak

Mayhem kaynaklarında spektrum üretimi, FIFO üzerinden aktarım ve waterfall
renk/ekran kaydırma işleri ayrılmıştır. Bu düzen görüntüleme yaklaşımı için
incelenir; kullanıcıdaki PortaPack'in seçili modu, örnek hızı veya FPS'si
ölçülmeden aynı olduğu varsayılmaz. Eşit I/Q veya kayıtlı ayarlar olmadan
görüntü karşılaştırmasından hassasiyet üstünlüğü çıkarılmaz.

- [Mayhem SpectrumCollector — incelenen kaynak sürümü](https://github.com/portapack-mayhem/mayhem-firmware/blob/ca9ca93fa29c745d6550c6ad41c58479e5a8963a/firmware/baseband/spectrum_collector.cpp)
- [Mayhem spektrum/waterfall görünümü](https://github.com/portapack-mayhem/mayhem-firmware/blob/ca9ca93fa29c745d6550c6ad41c58479e5a8963a/firmware/application/ui/ui_spectrum.cpp)
- [ITU-R SM.2256-1, 2016: ölçüm eşiği, zamanlama, yeniden ziyaret ve farklı kanal genişlikleri](https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-SM.2256-1-2016-PDF-E.pdf)

Kaynaklar yöntem ve deney tasarımını destekler. Bu plandaki 30 Hz, %20, %95 ve
1 olay/dakika hedefleri bu yayınlardan çıkarılmış standart değerler değildir.
Yeni katsayılar kaynak atfıyla birlikte bağımsız deney ve donanım eşdeğerliği
gerektirir; başka bir uygulamanın güzel görüntüsü otomatik tespit kabulü olmaz.

## Gerçek yürütüm sahipleri

| İş | Güncel sahibi | Kaynak / kanıt |
|---|---|---|
| 8 MS/s RX, frekans kaydırma, 193 tap filtre, 4:1 örnek azaltma | HackRF + bilgisayar | `algorithms/p0/channelizer.py` |
| Hann, FFT bağlantısı, güç | SystemVerilog + AMD FFT IP, ZedBoard PL | `algorithms/fpga/p0/rtl/p0_candidate_dsp_runtime_top.sv` |
| OS-CFAR, bölgesel median, bütünleşik enerji, gruplama, birleştirme, paket | SystemVerilog, ZedBoard PL | `p0_candidate_reducer_packetizer_top.sv` ve alt blokları |
| Paket/CRC denetimi, 2/3 doğrulama ve iki kaçırmada sonlandırma | C, ZedBoard PS/ARM | `platforms/embedded/p0/src/p0_ed_pipeline.c` |
| Çok kareli zayıf dar bant aday | SystemVerilog PL zayıf kapı + C/ARM kare başına en güçlü sekiz aday kabulü ve 24/32 doğrulama | `p0_weak_nomination_top.sv`; `axis_candidate_packetizer.sv`; `p0_ed_pipeline.c`; RTL/C/P09 soğuk açılış ve dijital kart kabulü geçti. İki LO kontrolü alıcı iç ürünü ayırmak için bilgisayarda yürüyen ayrı bir RF kontrolüdür. |
| Spektrum ve waterfall çizimi | Python/Qt Quick, bilgisayar | `app/operator_console/spectral_display.py`; kart yanıtı bağlı gerçek I/Q |

FFT matematiğinin tamamı elle SystemVerilog olarak yazılmamıştır; AMD FFT IP,
SystemVerilog bağdaştırıcıyla kullanılır. Python modelleri referans ve test içindir.
FPGA/ARM olay listesi karttan gelir. Karta kalıcı olarak yüklenen P09 imajı
ADR-0040 zayıf yolunu içerir. Python/NumPy modeli artık yalnız referans ve
tekrarlanabilir doğrulama sahibidir. İki LO kontrolü FPGA olayı değildir; HackRF
ayarına bağlı iç ürünleri gerçek RF yayınından ayırmaya yardım eden bilgisayar
tarafı alıcı kontrolüdür.

2 Eylül 2026 ADR-0040 hedef modeli, mevcut rank-24/32 PL gürültü kestirimine
karşı 6 dB zayıf aday çıkışı ve ARM'da tepe ±2 hücre destekli 24/32 doğrulama
olarak somutlaştırılmıştır. Python hedef modeli ile portable C çekirdeği aynı
vektörde alan alan eşleşmiştir. Ayrı SystemVerilog karar-hücresi benzetiminde
5× gürültü hücresi yalnız zayıf aday, 10× hücre hem zayıf hem normal aday
olmuştur. 64'er adet beyaz, eğimli ve dalgalı 32-kare gürültü penceresinde
doğrulanmış yanlış aday çıkmamış; beş farklı FFT konumundaki enjeksiyon aynı
hücrede doğrulanmıştır. Zayıf bit güncel kaynakta sınıflı gruplama, paket ve ARM
hizmetine bağlanmıştır. Tam RTL paket testi 8 kare/113 aday/629 beat ve 63
backpressure kontrolünde, portable C boru testi 24/32/reset/sona-erme
yaşam döngüsünde geçmiştir. Güncel kaynaklardan PetaLinux 2025.2 ARM imajı
5679/5679 görevle üretilmiştir; Vivado route/zamanlama/bitstream ve P09 kalıcı
soğuk açılış kapıları geçmiştir. Karttaki işlev dizisi 104 adaydan 50 etkin
olaya, ardından iki boş karede 50 sona ermeye sıfır düşümle ulaşmıştır. Beş
bağımsız koşudaki 20.480 ölçüm karesinde sıra hatası görülmemiş; en düşük hız
525,8263 kare/s ile gereken 488,28125 kare/s sınırını geçmiştir. Bu, bilinen
dijital çerçeveyle FPGA/ARM işlev ve hız kabulüdür; kör canlı RF Pd/Pfa,
frekans/genlik kalibrasyonu ve saha başarımı henüz açık kapıdır. Güncel model kanıtı
`results/evidence/phase08/persistent-weak-model-v1.json` dosyasındadır.
Kayıtlı I/Q yolu yalnız tekrarlanabilir doğrulama altyapısında tutulur; yarışma
operatör arayüzünde kaynak seçeneği değildir ve canlı P0 OS-CFAR yoluyla aynı
başarı iddiasını üretmez.

## Tarihsel belgelerdeki eksiklik

ADR-0028 geniş bant yolunun önce ARM üzerinde kurulduğu aşamayı; ADR-0033'ün
ilk kapanış metni ise kart entegrasyonundan önceki aşamayı anlatır. Bu kayıtların
"henüz PL'de/kartta değil" ifadeleri güncel durum değildir. Eski kanıtlar silinmez.
29 Ağustos tarihli `candidate-packet-physical-acceptance.json` ve
`ed-service-v3-cold-boot-acceptance.json` ADR-0037 öncesi aday paketini fiziksel kartta,
54 adayın alan eşdeğerliğini ve 2/3 yaşam döngüsünü doğrular. Beş koşuda
20.480 kare, en düşük 508,759 kare/s ile kayıtlı 2 MS/s yük kapısı geçmiştir.

`results/evidence/phase08/live-rx-endurance-v2.json`, kendi FPGA-bağlı kaynak
sürümünde 15 dakika / 439.453 kare canlı RX bütünlüğünü belgeler. Güncel
RX/görüntü sürümü için 30 Hz geniş görünüm ve 15 dakika bütünlük ayrıca
`live-rx-display-8msps-v1.json` ile geçmiştir. Bu sonuç güncel ADR-0039 kaynak
sürümüne devredilmez; güncel `live-rx-display-8msps-v2.json` USB shortfall
nedeniyle başarısızdır. Bilinmeyen verici doğruluğu veya güncel FPGA işlevi bu
RX-only kayıtlardan devralınmaz. Belge güncelliği eksikti;
bu, önceki donanımın hiç yapılmadığı anlamına gelmiyordu.

## Örnek hızının anlamı

8→2 MS/s, geçen fiziksel zamanı dört kat uzatmaz. Her saniyenin filtrelenmiş
2 milyon örneği işlenir. 4096 örneklik kare 2,048 ms'dir; saniyede 488,28125
kare gerekir. 8 MS/s'yi aynı FFT boyuyla karta vermek dört kat kare yükü ister;
mevcut fiziksel uçtan uca kanıt bunu karşılamaz. Bedel, daralan anlık banttır:
2 MHz sayısal pencerenin ürünce kullanılan güvenli kısmı merkez ±700 kHz'dir.
Tüm 2,4 GHz veya 5,8 GHz bandı aynı anda görünmez.
4096 örnek toplama süresi 8 MS/s'deki 0,512 ms yerine 2,048 ms olur; gözlem
penceresi uzar. Ayrıca aynı geniş arama bandı için daha çok merkez frekansı
ziyareti gerekebilir. Bu yüzden gerçek zamanlı işleme kapasitesi, tek kare
süresi, bütün bandı tarama süresi ve arayüz FPS'si ayrı değerlendirilir.

HackRF belgeleri cihazı 8 MS/s altında doğrudan örneklemek yerine 8 MS/s alıp
keskin alçak geçiren filtreyle 4:1 azaltmayı önerir. Bizdeki yaklaşım bununla
uyumludur. Bu öneri, bütün yayın türleri için 2 MHz görünüm yeterlidir demez.
[HackRF örnekleme ve filtreleme açıklaması](https://hackrf.readthedocs.io/en/stable/sampling_rate.html)

## FFT hücresi, çözünürlük ve doğruluk

`2.000.000 / 4096 = 488,28125 Hz`, frekans ızgarasının adımıdır. Bir cetvelin
çizgi aralığı gibi düşünülmelidir. Pencere ana lobu, SNR, hücreler arasına düşen
ton ve alıcı saat hatası ayrıca etkiler. Örnek olarak 1 ppm frekans hatası
2,4 GHz'de 2400 Hz, 5,8 GHz'de 5800 Hz eder; bunlar cihazda ölçülmüş hata değil,
ppm dönüşümü örneğidir. Periyodik Hann'ın eşdeğer gürültü bant genişliği 1,5
hücredir; burada yaklaşık 732 Hz eder. Bu da iki tonu ayırma veya mutlak frekans
doğruluğuyla eş anlamlı değildir.
[Keysight pencere özellikleri](https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/gui/content/meassetup_resbw_windowtypes.htm)

Hann→FFT→güç, standart bir spektral ön uçtur. Sızıntıyı azaltır; tek başına
sinyal varlığı, yayın kararlılığı veya saat kalibrasyonu sağlamaz. Güç ölçeği
dBFS'dir; dBm değildir.
[Analog Devices: pencereleme](https://www.analog.com/en/resources/technical-articles/coherent-sampling-vs-window-sampling.html)

## OS-CFAR ve yanlış alarm

OS-CFAR bilimsel dayanağı olan bir uyarlamalı eşik yöntemidir. Rohling'in
çalışması sıralı referans örneği kullanımını ve çoklu hedef/arka plan geçişlerinde
CA-CFAR'a göre avantajlarını inceler; tüm yayınlara koşulsuz başarı garantisi
vermez. Projenin 16+16 referans, 4+4 koruma, sıra 24 ve alpha 8,580143 profili
kendi model varsayımları ve deney zarfıyla sınırlıdır.
[Rohling, 1983, özgün makale](https://ece.iisc.ac.in/~cmurthy/E1_244/Slides/Rohling.pdf)

`Pfa=10^-4`, sinyal yokken bir hücrenin bir değerlendirmede eşiği aşmasının
tasarım olasılığıdır; bütün ekranın veya saniyenin yanlış alarm oranı değildir.
4056 değerlendirilen hücrede beklenen ham aşım sayısı yaklaşık 0,4056/karedir;
488,28 kare/s için yaklaşık 198 ham hücre aşımı/s eder. Beklenen değer toplamı
bağımsızlık gerektirmez; kare bazlı "en az bir alarm" olasılığı ve zamansal
sonuçlar ise bağımlılıklar bilinmeden bu sayıdan çıkarılamaz. Gruplama ve 2/3,
bu ham aşımlardan ayrı olay katmanıdır. Hann korelasyonu, alıcı süzgeci,
girişim, renkli gürültü ve doygunluk gerçek oranı değiştirebilir.

## Geniş bant kurtarmanın açık sınırı

32 hücre enerjisini bölgesel `median/ln(2)` tabanına karşı sınamak, tek hücre
OS-CFAR parçalanmasını belirli sahnelerde gidermiştir. ITU'nun farklı kanal
genişliklerini farklı ölçeklerde değerlendirmesi bu yaklaşımın genel yönünü
destekler; bizim 32, 2,5 ve 41 sabitlerimizi standart belirlemez.
[ITU-R SM.2256-1, çok ölçekli kanal değerlendirmesi](https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-SM.2256-1-2016-PDF-E.pdf)

İlk `scripts/characterize_detection_limits.py` tanısı, eski bölgesel yolda 512,
2048 ve 4096 hücre desteklerinin kaçtığını göstermiştir. ADR-0037 iki taraflı
tam-bölge referansıyla 512/1024/2048 hücre ailelerini sentetik CI8/Hann ve
SystemVerilog eşdeğerlik kapılarında düzeltmiştir. Bütün 4096 hücreyi dolduran,
gürültü benzeri güç artışında aynı karede bağımsız yerel referans bulunmadığı
için bu durum hâlâ çözülmüş sayılmaz.

Tarama sorumluluk aralığı 1,4 MHz'den 600 kHz'e indirilmiştir. Böylece merkezi
kendi sorumluluk hücresinde olan 1 MHz destek, en az bir 2 MHz ayarda ±800 kHz
kanal seçici geçiş bandının içinde kalır ve detector karesinde iki dış bölgeye
yer bulunur. Dar adaylar ikinci ayarda tepe frekansıyla; 257 hücre ve üzeri
adaylar mutlak alt/üst destek aralığının en az yarı örtüşmesiyle eşleştirilir.
Tepe hücresini iki ayar arasında 800 kHz'den fazla oynatan 1 MHz sentetik aday
bu yolla doğrulanmıştır. Bu, geometrik ve yazılım düzeyi bir kapıdır; kanal
süzgecinin gerçek yayın şekli üzerindeki etkisini, Pd/Pfa'yı veya saha başarısını
kanıtlamaz. Bütün pencere işgali için frekans/kazanç bağlı RX tabanı ya da daha
geniş kaba referans ayrıca değerlendirilmelidir.
Kaynak bağlı rapor `results/evidence/phase08/survey-overlap-v1.json` içindedir.

ADR-0038, zaten hesaplanan 8 MHz görünüm FFT'sinden ayrı bir host kaba aday
üretir. Dört komşu güç hücresi toplanır; bu işlem enerjiyi korur ve 4.096
hücrelik kanonik tespit profilini yeniden kullanır. Bağımsız deneyde düz/eğimli/
basamaklı negatiflerde aday 0/32; 100 kHz, 500 kHz, 1 MHz, 2 MHz ve 4 MHz
pozitiflerinde `%80` kapsama 32/32'dir. Detector çağrısı p95 `5,86 ms` ölçülmüş,
ancak FFT/USB/Qt bu süreye dahil edilmemiştir. 6 MHz 31/32, 8 MHz 0/32 sonucu
özellikle korunur. Bu katman Python/NumPy host işidir; SystemVerilog 2 MHz FPGA
doğrulamasının yerine geçmez. Kanıt
`results/evidence/phase08/coarse-rx-detection-v1.json` dosyasındadır.

## Görünüm düzeltmesi

48 satırlı JavaScript hücre çizimi yerine 128×16.384 float32 ring tampon ve Qt
görüntü çizimi kullanılır. Her piksele düşen tüm frekans hücrelerinin maksimumu
alınır; seyrek örneklemeyle dar tepe atlanmaz. İnceleme sırasında 16.384 hücre
korunur. Renk/güç ölçeği ilk anlamlı karede bir kez otomatik ayarlanır. Görünür
yakınlaştırma/geçmiş, taban, aralık ve tepe-tut düğmeleri operatör yüzeyinden
kaldırılmıştır; bu değişiklik alıcı kazancını veya detector eşiğini değiştirmez.
Frekans/örnekleme/oturum değişince geçmiş sıfırlanır. Zaman etiketleri
gerçek kare indisinden hesaplanır; atlanan görüntü kareleri yeniden üretilmez.

Canlı görünüm 15 DSP karesinde bir örneklenir (nominal 32,55 Hz). Tek bekleyen
GUI bildirimi en son görünümü tutar; tüm I/Q, FPGA ve temporal işlemleri devam
eder. Görüntü Hz'si, çizilen FPS ve FPGA kare/s farklı ölçülerdir. Tarama ekranı
yalnız bütünlüğü geçen pencerenin en fazla 32 seçilmiş gerçek karesini gösterir;
farklı frekanslardan sahte bir zaman geçmişi oluşturulmaz.

Qt, sık güncellenen büyük Canvas/JavaScript çizimlerinin maliyetine dikkat çeker.
Yeni yol NumPy ve Qt görüntü tamponu kullanır; GPU'da DSP çalıştığı iddia edilmez.
[Qt Canvas açıklaması](https://doc.qt.io/qt-6/qml-qtquick-canvas.html)

## Bu değişikliğin doğrulaması

`results/evidence/phase08/detection-display-rendering.json`, aynı sonlu kayıtlı
I/Q karesini tekrar çizdiren yerel ölçümün beşer koşusunu ve kaynak hashlerini
korur. Eski çizimde ortanca 24,65, yeni çizimde 30,00 görüntü güncellemesi/s
ölçülmüştür. Bu, canlı HackRF + FPGA yükü altında FPS veya RF doğruluk kabulü
değildir. Eski çalışma ağacının bütün kaynakları ayrıca arşivlenmediğinden
temiz iki checkout arasında yeniden kurulabilir bir performans kabulü sayılmaz;
yeni çizimin ölçümü `scripts/measure_detection_display.py` ile tekrarlanabilir.

Kayıtlı I/Q görünümü 1280×720 boyutunda ve %150 ölçekle ayrıca incelenmiştir.
Tepeyi kaybetmeyen projeksiyon, 4096 hücre geçmişi, sabit güç/renk karşılığı,
yakınlaştırma ve yeniden boyutlandırmanın geçmiş üretmemesi, sınırlı bildirim
kuyruğu ve tarama penceresi bütünlüğü yazılım testleriyle denetlenmiştir.
Kapsamlı seçili koşuda 118 test geçmiştir; iki tarihsel dayanıklılık testi,
bu değişiklikten önce değiştirilmiş `app/operator_console/live_ed.py` ve
`platforms/acquisition/continuous.py` dosyalarının arşiv hashleriyle uyuşmaması
nedeniyle geçmemiştir. Kaynak denetimi gevşetilmemiştir; yeni sürümde fiziksel
dayanıklılık yeniden kabul edilmelidir.
Son metin yerleşimi düzeltmesinden sonra görünüm, canlı alım görünüm modeli,
tarama ve depo sözleşmesi için seçilen 78 testin tamamı yeniden geçmiştir.
Bu koşu önceki testlerle örtüşür; sayılar bağımsız testler gibi toplanmaz.

Bu oturumda bağlı HackRF bulunmuş ve ZedBoard hizmetinin `192.168.7.2:47007`
TCP bağlantısı doğrulanmıştır. Kart yanıtlı kısa duman testi geçmiştir; ancak
karttaki bitstream ADR-0037'nin güncel geniş bant RTL'sini içermez. ADR-0039
kaynağında RX-only görünüm hedefleri geçerken USB shortfall kapısı geçmemiştir.
Kart yanıtlı geniş bant tarama, bilinmeyen verici ve kontrollü RF kabulü
yapılmamıştır. Bütün pencere karşı örneği açıktır.

1 Eylül 2026'da tamamlanan iki bağımsız 1490–1600 MHz turu aynı en güçlü
2 MHz pencereyi 1587,5 MHz merkezde bulmuştur. Son tur 184/184 pencereyi
98,42 saniyede, sıfır USB/FPGA aktarım hatasıyla tamamlamış; bu pencerenin
kanal gücü taramanın medyanından yaklaşık 8,1 dB yüksek çıkmıştır. Ayrı ham-I/Q
tanısında 1585 ve 1590 MHz fiziksel LO ayarları aynı 1.586.923.828,125 Hz
ortalama PSD tepesini üretmiş; iki tepe arasındaki fark 0 Hz ve iki hedef
pencerenin ortalama kanal gücü 1577,5 MHz karşılaştırma penceresinden 9,41 dB
yüksek olmuştur. Yazılım çok ölçekli aday yolu bu tepeyi 120/120 ve 119/120
karede kapsarken kartta yüklü önceki bitstream 0/120 ve 0/120 karede kapsamıştır.
Bu sonuç gerçek RF enerjisinin ve o tarihte yüklü kart imajı eksiğinin tanısıdır; harici
verici kimliği veya kontrollü TX açık/kapalı kabulü değildir. Ham kanıt
`build/acceptance/rx-survey/diagnostic-1587p5-20260901/analysis.json` içindedir.

Tek turda eski kart imajının ürettiği 73 küçük iki-LO adayını operatöre tek
öncelikmiş gibi göstermemek için tamamlanmış taramaya tamamlayıcı bir yerel
kanal-gücü sıralaması eklenmiştir. Her pencere için merkez çevresindeki
±10 komşu pencerenin medyanı alınır; adayın kendi ±2 komşusu referanstan
çıkarılır. Yalnız yerel tabanı en az 6 dB aşan en az iki bitişik 600 kHz
sorumluluk penceresi bir enerji bölgesi olur. Bu yol dar ve düşük toplam güçlü
yayınlar için FPGA OS-CFAR'ın yerine geçmez; tek LO kanal gücüdür ve dış verici
kanıtı değildir. Mevcut fiziksel kayıtta yalnız 1585,3–1588,5 MHz bölgesini,
1587,5 MHz tepe penceresi ve +9,04 dB yerel farkla öne çıkarmıştır. Birim ve
sunum testleri, tarama ve görünüm modeliyle birlikte seçilen koşuda 68/68
geçmiştir.

Vericinin kullanıcı tarafından yeniden ayarlanmasından sonra alınan üçüncü tam
1490–1600 MHz turu 184/184 pencereyi 95,65 saniyede ve sıfır başarısız pencereyle
tamamlamıştır. 1586,3–1587,5 MHz enerji yükselmesi aynı yerde kalmış; bu nedenle
test vericisine bağlanmamıştır. Önceki tura göre en büyük artış 1510,7 MHz'de
+4,66 dB, 1595,3 MHz'de +4,10 dB olmuş; ikisi de kilitli +6 dB A/B sınırını
aşmamıştır. 1595,3 MHz çevresindeki ayrı 120+120 karelik iki-LO kaydının
doğrulanmış ±800 kHz geçiş bandındaki PSD desen korelasyonu 0,916'dır; hem host
detector hem karttaki mevcut imaj ortak tepeyi 120/120 ve 120/120 karede
kapsamıştır. Bu, kararlı bir RF yapısıdır; verici kimliği değildir. Kanıtlar
`build/acceptance/rx-survey/live-1490-1600-after-retune-20260901.jsonl` ve
`build/acceptance/rx-survey/diagnostic-1595p3-20260901/analysis.json`
dosyalarındadır.

Güncel geniş bant RTL için `fpga-p2` tam yapısı Vivado 2025.2 ile geçmiştir.
50 MHz post-route sonuçları setup WNS `+0,046 ns`, hold WHS `+0,015 ns`, sıfır
failing endpoint, 54.801/54.801 tam yönlendirilmiş ağ ve sıfır DRC hatasıdır.
Üretilen FPGA Manager ikilisinin SHA-256 değeri
`46466f74cd1b045fa1844124274cf19dc7e654420418f4737a0f3137909a0db2`'dir.
İmaj FPGA Manager ile karta yüklenmiş; durum `operating`, Ethernet hizmeti
`192.168.7.2:47007` erişilebilir ve bilinen-ton yaşam döngüsü geçmiştir. Eski
imajın hedef tepeyi kapsadığı kare sayısı iki bağımsız LO kaydında 0/120 ve
0/120 iken güncel imaj 119/120 ve 118/120 üretmiştir. Üç oturumda CRC, sıra ve
kuyruk hatası sıfırdır. Hash-bağlı kanıt
`results/evidence/phase08/fpga-p2-wideband-physical-replay.json` dosyasındadır.
Bu çalışma kayıtlı fiziksel HackRF I/Q'sunu Ethernet→PS/DMA→PL yolunda doğrular;
harici verici kimliği, canlı Pd/Pfa veya kontrollü TX kapalı/açık kabulü değildir.
Yükleme FPGA Manager ile çalışma zamanında yapılmıştır; SD kartın kalıcı
`BOOT.BIN` imajı bu kanıt kapsamında değiştirilmediğinden kart yeniden açılırsa
güncel imaj tekrar yüklenmelidir.

Operatör tespit yüzeyi ayrıca sadeleştirilmiştir. Açılışta canlı alıcı otomatik
denetlenir; ana eylemler sabit frekansta ve bantta `Taramayı Başlat`/`Durdur`
akışıdır. SigMF seçimi, olay konsolu, yakınlaştırma/geçmiş, seviye ve tepe-tut
düğmeleri görünür yüzeyden kaldırılmış; alıcı LNA/VGA ve frekans denetimi
korunmuştur. İlgili canlı görünüm, tarama ve QML ürün sınırı koşusunda 98/98
test geçmiştir.

900 MHz sabit bant kontrollü tanısında kullanıcı tarafından bildirilen TX açık
ve kapalı kayıtlar aynı 32/32 kazanç ve iki LO ayarında karşılaştırılmıştır.
Yayınla birlikte değişen ortak bileşen 900,183–900,191 MHz'de bulunmuş; TX açık
eksi kapalı farkı iki LO'da dar bantta 24,47 ve 25,14 dB olmuştur. 900,4385 ve
900,6499 MHz çizgileri en fazla 1,17 dB değiştiğinden bu yayına bağlanmamıştır.
İlk sabit bant doğrulayıcısı adayı çıkış spektrumunun DC merkezine taşıdığı ve
yalnız karttaki 2/3 olayı saydığı için gerçek yayını reddediyordu. Güncel
doğrulayıcı hedefi çıkış merkezinden 300 kHz uzakta tutar; aynı canlı FPGA
oturumunun 8 MHz alıcı spektrumunda iki bağımsız LO tekrarını da sayar. Fiziksel
tekrarda aday iki LO'da 79/79 kare, 900,184702 ve 900,185197 MHz ortalama tepe,
22,48 ve 22,34 dB P/N ile geçmiştir. Kartın zamansal olay sayısı bu dalga
biçiminde 0/0 kaldığından arayüz yöntem alanını `RX çift ayar` olarak gösterir;
bu sonuç FPGA zamansal doğrulaması veya verici kimliği diye sunulmaz. Hash-bağlı
kanıt `results/evidence/phase08/live-user-tx-on-off-900mhz.json` dosyasındadır.

## Kontrollü fiziksel kabul sırası

1. Alıcı/kart bağlantısı ve geçerli kart yanıtı; bozuk paket/kırpılmada sonuç yok.
2. Bilinen frekansta, ayrı kaydedilen yayın kapalı ve açık koşulları. Giriş
   bandı, dalga biçimi, süre, göreli seviye, kazanç ve saat referansı kayıtlı olur.
3. Aynı verinin görünümü ile FPGA adaylarının karşılaştırılması: görünür olup
   aday olmayan yayının kaydı da korunur. Gösterilen tepe ile taşıyıcı aynı
   varsayılmaz; frekans hatası yayın biçimine uygun referansla hesaplanır.
4. Kaynak frekansı tespit yazılımına verilmeden, önceden belirlenmiş bantta
   arama. Gerçek değer ayrı hakem kaydında tutulur. Yayın süresi tarama turu,
   ziyaret süresi ve yeniden doğrulama süresiyle birlikte raporlanır.
5. Dar, geniş, aralıklı yayın ve kenar konumları; bağımsız tekrarlar. Başarı
   oranı, kaçırmalar, yanlış olay/dakika ve ilk tespit gecikmesi birlikte ölçülür.

İzinli/kontrollü RX test düzeni kullanılır; bu çalışma TX ayarı yapmaz.
Bu aşama geçmeden sinyal izleme, yön bulma veya ET geliştirmesine geçilmez.
