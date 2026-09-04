# Operatör Görev Akışları

- Sürüm: 1.8
- Güncelleme tarihi: 2026-09-01
- Kapsam: APP-F için ürün bilgi mimarisi

## Genel yerleşim

Ürün arayüzü beş kalıcı ED görev girişinden oluşur:

1. `Tespit`: kaynak, spektrum, spektrogram, tespit listesi ve seçili sinyal.
2. `Parametre`: seçili sinyalin analiz aralığı, ölçüm durumu ve sonuçları.
3. `Dinleme`: seçili doğrulanmış tespit, AM/NFM kanal ayarları, ses sonucu ve WAV.
4. `Yön Bulma`: anten açısı–güç ölçümü, bağıl geliş açısı ve kerteriz.
5. `Sistem`: bileşen sağlığı, performans ve son olaylar.

Üst görev çubuğundaki `BÂZ` logosu; `Tespit`, `Parametre`, `Dinleme`, `Yön Bulma`
ve `Sistem` girişlerini taşıyan ana görev menüsünü açıp kapatır. Menü başlangıçta
kapalıdır ve bu görünüm değişikliği çalışan görevlere komut göndermez. Açılan sol
görev şeridindeki `Tespit` dalga sembolü, ED/Tespit sabit-frekans yüzeyindeki
`Alıcı Ayarları` seçenek menüsünü açıp kapatır. Menü başlangıçta kapalıdır;
sembol başka bir görevde kullanılırsa ED/Tespit yüzeyine dönerek açılır. Bu
geçiş çalışan alım veya taramaya başlatma/durdurma komutu göndermez. Üst görev
çubuğunda bağlantı veya hata mesajı gösterilmez; ED/ET görev seçimi sağ kenarda
ve ayırıcı çizgisiz yer alır. `BÂZ` işareti koyu zeminde beyaz ön plan ve arka
hale katmanıyla sunulur.
Spektrum ve spektrogram başlıkları grafik alanında ortalanır; boş bağlantı uyarısı
tespit listesini doldurmaz. Sabit bant çalışma alanında dış marj kullanılmaz; alıcı
kontrolleri kendi sütununda ortalanır ve tespit ayırıcısı alanı tam yükseklikte
böler. Merkez frekansı ile örnekleme hızı yalnız geçerli alım verisi
varken görünür. Ana tespit yüzeyi yalnız sabit frekans taraması ile bant
taraması arasında geçiş verir. Olay konsolu ve geliştiriciye yönelik görünüm
kontrolleri ana operatör yüzeyinde yer almaz.

Parametre ölçümü ve analog dinleme seçili sinyal bağlamından açılır; kaynak ve
tespit kimliği her adımda korunur.

## Akış 1 — Kaynağı hazırlama

1. Uygulama alıcıyı otomatik denetlemeden `Alıcı bekleniyor` durumunda açılır.
2. Operatör `Alıcıyı Denetle` ile HackRF ve FPGA hizmet denetimini birlikte
   başlatır. `Hazır` için iki bağlantı da zorunludur. HackRF, FPGA veya ikisi
   birden kullanılamıyorsa uygun hata 10 saniye gösterilir; ardından bağlantı
   kurulmadıysa görünüm yeniden bekleme durumuna döner.
3. Başarılıysa alıcı `Hazır` olur; tarama başladıktan sonra merkez frekansı ve
   örnekleme hızı üst durum alanında görünür.
4. Başarısızsa hata yalnız `Alıcı Ayarları` alanında, kısa bir neden ve
   uygulanabilir kurtarma eylemiyle gösterilir; aynı hata başlıkta tekrarlanmaz.
   FPGA hizmet/taşıma erişim hatası birleşik `Hazır` yetkisini iptal eder ve
   taramadan önce yeniden `Alıcıyı Denetle` gerekir.

Bağlantı ve alım durumu, görevden bağımsız olarak yalnız operatörün işlem yaptığı
`Alıcı Ayarları` alanında gösterilir; üst görev çubuğunda durum rozeti bulunmaz.

Çıkış koşulu: kaynak gerçek ve erişilebilir durumdadır. Yerine başka veri
konulmaz; son başarılı kaynağın değerleri yeni kaynakmış gibi korunmaz.

## Akış 2 — Sinyal tespiti

### Frekansı bilinmeyen yayın

Operatör sabit frekans görünümündeki `Bant Taraması` bağlantısıyla arama
ekranına geçer; 1–6.000 MHz içindeki aralığı ve LNA/VGA değerlerini seçip
`Taramayı Başlat` eylemini kullanır. Kapsam ve süre solda, geçmiş frekans
gözlemleri kendi kaydırma alanında sağda güncellenir. Gözlem seçimi yeni
sonuçlarda değişmez. Hatalı bantlar sarı, henüz alınmayan bantlar gri kalır.
Mavi yalnız alım/kart bütünlüğünün geçtiğini gösterir; RF doğruluk işareti değildir.

Laboratuvarda belirli bir harici vericinin gerçekten bulunduğunu sınamak için
operatör aynı aralık ve kazançlarla önce `1 · TX’İ KAPAT → REFERANS`, ardından
vericiyi açıp `2 · TX’İ AÇ → KARŞILAŞTIR` kullanır. Her turdaki aday önce ikinci
LO ayarında yeniden görülmelidir. TX açık turda referansta bulunmayan veya aynı
kazançta iki LO'da ortalama tepe gücü en az 6 dB artan satır sarı
`A/B: YENİ ADAY/GÜÇLENDİ`; iki turda da bulunan satır gri `REFERANSTA VAR` olur.
Eksik kapsam, taşma veya farklı alıcı/yazılım kaydı karşılaştırmayı kapatır;
gerçek kazançları farklı pencereler `A/B: BELİRSİZ` kalır. Bu farklar tek başına
vericinin kimliğini kanıtlamaz. Uygulama harici vericiyi açıp kapatmaz;
düğme metni operatörün fiziksel deney koşulunu kayda geçirir.

FPGA adayı çıkmasa da aynı ayarlarda 2 MHz kanalın toplam I/Q gücü en az 6 dB
artarsa ayrı `A/B: KANAL GÜCÜ` satırı gösterilir. Bu host tanı ölçümüdür;
ikinci LO doğrulaması, yayın bant genişliği veya verici sayısı değildir.
6 dB eşiği deneysel karşılaştırma kuralıdır; kalibre edilmiş yanlış alarm
olasılığı değildir. TX kapalı/açık tekrarı ve değişmeyen alıcı/anten düzeni gerekir.

Tarama başka bantlara geçtiğinden waterfall geçmişi aynı frekanstaymış gibi
birleştirilmez. Sol grafik son tamamlanan gerçek pencereyi gösterir. `Durdur`
tamamlanan kapsamı ve gözlemleri korur. Seçili gözlem, `Seçili Frekansı İzle`
ile sabit bant ekranına taşınır; burada ortak yakınlaştırmalı spektrum ve
spektrogram kullanılır. Gözlem frekansı tepe hücresidir; yayıncı kimliği veya
hassas taşıyıcı ölçümü değildir. Kısa yayınlar tarama sırasında kaçabilir.

### Sabit frekansta tespit

```text
[Veri Kaynağı] → [Ön İşleme] → [FFT / Güç] → [Bölgesel Eşik] → [Zamansal Doğrulama]
```

1. Operatör izleme merkez frekansını ve gerekirse LNA/VGA değerlerini girer.
2. `Taramayı Başlat` canlı alımı ve FPGA tespitini birlikte başlatır;
   `Taramayı Durdur` oturumu güvenli biçimde sonlandırır.
3. Spektrum ve spektrogram merkez çalışma alanında güncellenir.
4. Canlı FPGA/ARM sonucu veya geniş RX spektrumundaki kararlı kaba sonuç önce
   sarı aday olarak gösterilir. En az 8 FPGA gözleminden sonra ya da kararlı
   kaba aday oluştuğunda alıcı otomatik olarak iki farklı fiziksel LO ayarında
   kısa tekrar yapar. Aynı mutlak RF bileşeni iki ayarda da görülürse sonuç
   yeşil `KARARLI RF ADAYI` olur. Karttaki 2/3 olay zinciri iki ayarda da sonucu
   üretmişse yöntem FPGA, aksi halde 8 MHz alıcı spektrumundaki iki-LO tekrar
   sayımıdır ve satırda `RX çift ayar` yazılır. Bu, harici
   vericinin kimliği değildir; kontrollü TX kapalı/açık karşılaştırması ayrı
   kabul adımıdır. Aynı
   frekansta yeniden oluşan FPGA olayları frekans destekleri örtüşüyorsa tek satırda
   birleştirilir. Canlı kılavuz gözlem kesildiğinde hemen kalkar; satır yaklaşık
   262 ms `Kısa süreli izleniyor` durumunda kaldıktan sonra yeni gözlem yoksa
   `Son görüldü` olur. Ham aday ve FPGA olay numarası operatör yüzeyine
   taşınmaz. Bu sunum sinyal türünü veya fiziksel yayıncı kimliğini doğrulamaz.
5. Sağdaki `Sinyal Tespiti` alanı seçili tespitin kimliğini, frekansını,
   tepe/gürültü oranını ve durumunu sabit tutar. `Parametre Çıkarımı` ayrı görev
   girişidir; tespit seçimi ekranı kendiliğinden ölçüme geçirmez.
6. Operatör bir doğrulanmış tespit seçtiğinde kaba aday ve önerilen analiz aralığı
   gerçek FFT hücrelerine bağlı olarak spektrum üzerinde işaretlenir.
7. Spektrum ve spektrogram ortak frekans penceresini kullanır. Görünür
   yakınlaştırma/geçmiş, seviye, taban ve tepe-tut düğmeleri bulunmaz; güç ve
   renk ölçeği ilk anlamlı karede otomatik ayarlanır.
8. Ortak frekans imleci iki görünümde aynı frekansı işaretler. Operatör,
   `Shift+sürükle` ile seçili tepeyi içeren 8–512 FFT hücrelik analiz aralığı
   taslağı oluşturabilir; taslak ayrıca açıkça onaylanmadan ölçüm başlamaz.

Ürün grafikleri yaklaşık 9,77 Hz'de (50 DSP karesinde bir) yenilenir; RX ve FPGA
2 MS/s veri yolundaki bütün kareleri işlemeye devam eder. Canlı listedeki satır
üyeliği yaklaşık 5 Hz örnek-zamanıyla yenilenir; frekans geçmişinin Qt satırları
her yanıtta yeniden kurulmaz. Ölçüme uygun son dört ardışık FPGA karesi güncel
olay için arka planda otomatik korunur. Yeni gözlemi olmayan satır gri
`Son görüldü` olur. Bu yalnız arayüzde tutulan oturum bilgisidir ve detector yaşam
süresini uzatmaz.

FPGA'nın ±700 kHz geçerli alanı dışında kalan 8 MHz kaba aday iki LO sınamasına
alınır. Geçici sınama ayarlarından sonra görünüm operatörün girdiği sabit merkez
frekansına döner. Aynı kaba karedeki en fazla dört güçlü aday P/N sırasıyla
saklanır ve tek tek sınanır; aynı aday kuyrukta tekrar edilmez.

Spektrum verisi gelmeden FPGA tespit alanı veya aday kılavuzu çizilmez; böylece boş
görünüm gerçek RF enerjisi izlenimi vermez. Eski `İZLEME` merkez çizgisi ve
grafik içindeki `TESPİT ALANI` yazısı kaldırılır; geçerli FPGA penceresi yalnız
ince turkuaz sınırla belirtilir. Tek LO FPGA kılavuzu sarı, iki ayarda kararlı
aday kılavuzu yeşil, host kaba RX adayı ise ince gri kesikli kılavuzdur. Eski
seçim grafikte kılavuz üretmez; geçmiş yalnız sağ listede `Son görüldü` olarak
kalır. Kılavuz waterfall
geçmişinin o frekansta sürekli sinyal içerdiğini iddia etmez. Birbirine en fazla
75 kHz uzaklıktaki güncel FPGA tepeleri yalnız sunumda tek satıra gruplanır;
ham FPGA olayları ve FPGA/ARM tespit eşikleri ile
2/3–iki-miss kuralları değişmez. Kayıtlı I/Q tekrar oynatma yalnız
tekrarlanabilir doğrulama altyapısında tutulur; yarışma operatör yüzeyinde
kaynak seçeneği değildir.

Çıkış koşulu: seçimin kaynak kimliği, çerçeve ve tespit kimliği birbirine bağlıdır.
Canlı HackRF görünümünde spektrum aynı gerçek I/Q karesinden gelir. FPGA/ARM
olayları ayrı kalır; iki-LO RX doğrulaması yalnız aynı mutlak RF özelliğini iki
fiziksel alıcı ayarında tekrar bulduğunu bildirir ve FPGA olayı gibi sunulmaz.
Kart bağlantısı yoksa ürün oturumu başlamaz ve sonuç alanları boş kalır.

## Akış 3 — Parametre ölçümü

1. Seçili doğrulanmış tespitin sabit bağlamından `Parametre` görevi açılır.
2. Sistem deterministik `Tespit aralığı`nı gösterir; operatör isterse sınırları
   düzeltir.
3. Ölçüm yalnız `Ölçümü Başlat` eylemiyle çalışır.
4. Sonuçta emisyon merkez frekansı, gözlenen taşıyıcı frekansı, OBW %99, alt/üst
   OBW frekansı, kanal gücü, SNR ve sinyal türü kalite
   durumuyla birlikte gösterilir.
5. Kalite kapısı geçmezse sayı yerine neden gösterilir.

## Akış 4 — Analog dinleme

1. Operatör Spektrum alanında doğrulanmış bir tespit seçer.
2. `Dinleme` alanı tespit kimliğini, frekansını ve kaynak I/Q süresini kaydırılan
   ayarlardan bağımsız sabit bir kanal kartında tutar.
3. AM veya NFM, kanal ofseti, bant genişliği ve ses seviyesi açıkça belirlenir.
4. Sabit `Kanal Sesini Hazırla` eylemi, kaynaktaki I/Q'yu GUI iş parçacığı dışında
   işler.
5. SigMF kaynağında en az beş saniyelik uygun kayıt kesintisiz sonuç; daha kısa
   kayıt yalnız açıkça etiketli kısa önizleme üretir. Canlı FPGA yolunda tam beş
   saniyelik ardışık I/Q tamponu ve aynı tespitin bu süre boyunca doğrulanmış
   gözlemi zorunludur; sıra boşluğu tamponu sıfırlar.
6. Sonuç 48 kHz mono PCM16 olarak oynatılabilir veya WAV dışa aktarılabilir.
   Salt-okunur zaman çizelgesi hazırlanan PCM süresini ve ses çıkışının gerçekten
   işlediği oynatma konumunu gösterir; fiziksel ses çıkışı yoksa WAV kullanılabilirliği
   bundan ayrı bildirilir.

Canlı kanalı hazırlama komutu I/Q penceresini sabitler, RX oturumunu güvenli
biçimde durdurur ve demodülasyonu arka planda yürütür. Kontrollü AM/NFM kaynağı
ve fiziksel ses aygıtı saha kabulü tamamlanmadan bu akış canlı RF dinleme
başarısı olarak sunulmaz.

## Akış 5 — Yön bulma

1. Sabit kaynak kartı kaynak kimliğini, merkez frekansını, etkin kareyi ve
   kalibrasyonsuz geniş bant kare gücünü gösterir.
2. Operatör anten dönüş açısını ve antenin 0° yön referansını belirler. İlk kayıt
   bu referansı ölçüm oturumu için sabitler; değiştirmek için ölçümler temizlenir.
3. Her saha ölçümü anten açısı, dBFS kare gücü, frekans, zaman, anten azimutu ve
   kaynak kimliğiyle kaydedilir. Kaynak değiştiğinde eski oturum otomatik temizlenir.
4. En az üç farklı açı yoksa veya güç maksimumu yeterince ayrışmıyorsa sonuç
   üretilmez ve eksik koşul gösterilir.
5. Geçerli sonuç önce antenin 0° eksenine göre `Bağıl Geliş Yönü` olarak sunulur.
6. Anten 0° yönü gerçek kuzeye bağlanmışsa `Gerçek Kerteriz` ayrıca gösterilir.
7. Faz uyumlu çok kanallı DoA, hedef konumu veya menzil sonucu üretilmez.

`Radyo kerterizi` terminolojisi ITU-R yön bulma kullanımını; bağıl ve gerçek yön
ayrımı ise açının anten eksenine mi gerçek kuzeye mi bağlı olduğunu izler. Tek
istasyon kerterizi bir konum kestirimi değildir.

## Akış 6 — Sistem denetimi ve kurtarma

Sistem görünümü düzenlenebilir veya dekoratif bir DSP blok grafiği sunmaz.
Kaynak, ön işleme, FFT/güç, tespit ve operatör görevleri soldaki sıralı işlem
zincirinde `Kullanılmıyor`, `Bekliyor`, `Hazır`, `Çalışıyor` veya `Hata` olarak
gösterilir. Seçili bileşenin gerçekten çalışan katmanı, doğrulanmış kaynak
karşılığı ve donanım kabul sınırı sağdaki denetçide açıklanır. Sistem olayları
sıra numarası, zaman, seviye, bileşen ve kısa nedenle Sistem görünümünde
filtrelenebilir salt-okunur günlükte tutulur. Bu alan komut çalıştırmaz; ana
tespit ekranında ikinci bir olay konsolu bulunmaz.

Canlı HackRF kaynağında alım/kanal seçimi bilgisayarda; Hann, FFT/güç,
OS-CFAR ve geniş bant aday paketleme FPGA'da; zamansal doğrulama Zynq PS'de
gösterilir. Kart yanıtı bilgisi bu oturumun gerçek verisine bağlıdır; yalnız
kaynak seçmek donanımın çalıştığı anlamına gelmez. Geliştirici görünümündeki
çift tıklama etkin katmana ait host veya RTL/PS kaynak konumunu açar.

## Geçiş ve hareket kuralları

- Durum değişimleri 120–180 ms arası opacity/position geçişi kullanabilir.
- Spektrum, spektrogram, alarm ve ölçüm sayıları dekoratif animasyon kullanmaz.
- Hareket, görev bağlamının değiştiğini veya bir panelin açılıp kapandığını
  anlatmalıdır; sürekli parlayan öğe kullanılmaz.
- Tespit listesinin yüksekliği içerik sayısından bağımsızdır; confirmed adaylar
  olay kimliğiyle kararlı sıralanır ve seçim fare basışında alınır.
- Tespit seçimi sabit kalırken sinyal ölçümü ve analog kanal ayarları kendi
  panellerinde bağımsız kaydırılır; dinleme hazırlama eylemi ile oynatma
  kontrolleri görünür kalır. Bütün çalışma alanını hareket ettiren ortak sayfa
  kaydırması kullanılmaz.
- Kerteriz ibresi yalnız yeni geçerli ölçüme geçerken hareket eder; seçili adayın
  spektrum vurgusu kısa bir odak geçişi kullanır.
- Yön Bulma kaynak bağlamı, kayıt eylemi ve sonuç geçmişi sabit kalır; yalnız
  ölçüm ayarları kendi panelinde kaydırılır.
- Veri güncellemesi hedefi 10 Hz'dir; hareketli geçişlerin hedefi 60 Hz olsa da
  hedef donanım ölçümü yapılmadan performans iddiası kurulmaz.
