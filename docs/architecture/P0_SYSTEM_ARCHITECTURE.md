# P0 Gerçek Sistem Mimarisi

## Windows EXE paketi — 18 Eylül 2026

Masaüstü kısayolu artık kullanıcıya özel uygulama dizinindeki Windows x64 EXE kurulumu açar. Python/Qt ve sayısal çalışma zamanı paketin içindedir; proje kaynak klasörüne veya sistem Python kurulumu bağımlılığı yoktur. Qt, Windows sistem ICU arayüzünü kullanır; uyumsuz üçüncü taraf ICU pakete alınmaz. HackRF araçları/USB sürücüsü ve kart hizmeti donanım bağlantısı için ayrı gerekliliklerdir. PC/PL/PS hesap ve görev paylaşımı ile operatör başlatma kapıları değişmedi. Sözleşme: `docs/interfaces/WINDOWS_PRODUCT_PACKAGE.md`.

## Windows masaüstü başlatma yolu — 18 Eylül 2026

Yerel `BÂZ.lnk`, mevcut ürün bağımlılıklarının kurulu olduğu Python kurulumunun `pythonw.exe` dosyasıyla `-m app.operator_console` çalıştırır; çalışma dizini proje köküdür. Bu PC sunum katmanının açılış yoludur. PL/PS görev paylaşımı, RX akışı ve operatör başlatma kapıları değişmez.

## P0PM-v5 taşıyıcı frekansı kökeni — 18 Eylül 2026

PL'nin Hann → 4096 FFT → UQ28.30 güç yolu korunur. P0PM-v5'in 16 özgün
CI8 karesinden ARM, geçerli bant/SNR bağında ikinci/dördüncü kuvvet frekansını
ve dört zaman grubu uzlaşmasını hesaplar. Ek 65536 noktalı FFT ARM yazılımıdır,
PL özelliği olarak gösterilmez. PC yalnız CRC/kimlik/köken yanıtını çözer ve
koşullu kestirimi ayrı kaydeder; kart hatasında sayısal geri dönüş yoktur.
Doğrudan çizgi, koşullu kestirim, emisyon merkezi ve deneysel PC sinyal türü
ayrı alanlardır. Yöntem, bellek, güncel ikili hash'leri ve açık fiziksel kapılar
`docs/interfaces/CARRIER_RECOVERY_20260918.md` içindedir.

## P0DF-v1 kaynak kimliği ve sonuç sunumu — 18 Eylül 2026

Canlı RX oturum kuşağı ile gerçek kare sıra numarası PC kanıt kaydında korunur.
P0DF-v1 tel alanı 32 bit olduğundan PC, en fazla 96 ölçümlük yön oturumu için
ölçüm sırası ve ilk kaynak kareyi çakışmasız tarama-yerel bir belirtece çevirir;
ARM aynı-kare ve sabit alıcı bağı kapılarını bu belirteçle uygular. Sınır dışı
kimlik gönderilmez. Son P0DF işlemi bağlantı/yanıt hatası verirse PC ölçümleri
korur ve yalnız aynı ARM karar isteğini yeniden gönderebilir.

PC görünümü ham maksimumu yalnız `ölçüm adayı` olarak sunabilir. Nihai bağıl yön
yetkisi ZedBoard ARM'ın `LOB HAZIR` yanıtında kalır. 0° fiziksel anten başlangıç
eksenidir; sensör/pusula bağı olmadan coğrafi kerterize çevrilmez. Derece RMS
tek taramanın ızgara metriğinden değil, bilinen gerçek yönlü çoklu fiziksel
koşulardan hesaplanır.

## Uyarlamalı yön taraması görev paylaşımı — 16 Eylül 2026

PC'deki `AdaptiveDirectionSweep`, `0°` doğrulamasından sonra önce saat yönündeki,
sonra operatörün `0°`a dönüşüyle ters yöndeki lob dışı sınırı planlar ve tepe
çevresinde 5° noktalar ister. PL mevcut Hann→4096 FFT→UQ28.30 güç zincirini
değiştirmez. ARM P0PM-v4 kilitli kanal toplam gücünü üretir ve tarama
tamamlandığında `P0_AMPLITUDE_DF_ADAPTIVE_V2` kapılarıyla P0DF kararını verir.
Lob dışı gözlem, hedef kimliği iddiası değil; aynı alıcı/kanal bağındaki eşik-altı
güç ve gözlem maskesidir.

## KTR-4.2 parametre iyileştirmesi — 16 Eylül 2026

Merkez frekansı ve ayrı taşıyıcı çizgisi ana sonuçlarda ayrıldı. Yetenek bildiren
kartta manuel ölçüm 16 özgün kareye (2 MS/s hızda 32,768 ms) uzatıldı; eski
kartta dört kare korunur. P0PM-v3, ARM grup kararlılığı denetimi ve kayıt/CRC
bağı eklendi; sayısal hesap için PC geri dönüşü yoktur. PL'nin kare başına
4096 FFT işlemi değişmedi. Yerel Analog/Sayısal modeli seçili kanal filtresiyle
aynı önişlemede yeniden eğitildi; sonuç deneysel tahmin olarak gösterilir.
Kaynak/test ve ARM derlemesi tamamlandı; karta yükleme ve yeni RF ölçümü
henüz yapılmadı. PHASE-08/ST-06 ve fiziksel KTR-4.2 kabulü açıktır. Yöntem,
kanıtlar, uyumluluk ve sınırlar: `docs/interfaces/PARAMETER_REFINEMENT_20260916.md`.

## KTR-4.3 dinleme kolaylıkları — 16 Eylül 2026

Bilinmeyen yayında aynı I/Q kaydını AM ve dar bant FM ile karşılaştırma,
sade kanal seçimleri, gizlenebilir ince ayar ve isteğe bağlı 200 Hz konuşma
filtresi eklendi. Yöntem seçimi otomatik tür tespiti sayılmaz. Canlı ses
hazırlığı son beş saniyeyi sabitleyip RX'i durdurur; kesintisiz ses akışı ve
sayısal kod çözümü yoktur. PL/ARM/RTL ve tespit kapıları değişmedi.
Kaynak/test doğrulaması yeni fiziksel kabul değildir; PHASE-08/ST-06 ve
KTR-4.3 açık kalır. Güncel ayrıntı `docs/interfaces/SIGNAL_MONITORING_LISTENING_STATUS.md`,
tekrarlanabilir ölçüm ve test kaydı `docs/reviews/LISTENING_ASSISTANCE_20260916.md` içindedir.

## Kalibrasyonsuz güç tahmini — 16 Eylül 2026

PC sunum katmanı, karttan gelen geçerli dBFS kanal gücünü canlı alıcının
frekans/LNA/VGA/RF AMP ve kanal seçici ölçek bağlamıyla yaklaşık SMA giriş
dBm değerine dönüştürür. Alan `estimated` ve geniş belirsizlik taşır; PL/ARM
ölçümü, kalıcı kalibrasyon sicili ve `channel_power_dbm` alanı değişmez.
Kalibre profil yokken gerçek dBm üretmeme sınırı korunur.

## Durdurulan tam bant turu — 16 Eylül 2026

Kullanıcı isteğiyle 1–6000 MHz turu 1963/2400 pencerede durduruldu; tamamlanan
kapsam 1–4908,5 MHz, liste 161 geçmiş gözlemdir. 60 kayıt 40 MHz katlarına
±10 kHz yakındır; bu ortak kaynak şüphesidir, kesin parazit/verici sayısı
sınıflaması değildir. İki kare sayacı ve sekiz geniş/dar eşleşme incelemesi
açıktır. İki kazanç ve bir USB taşma tekrarı vardır; başarısız kalan pencere
sayısı sıfırdır. Son tekrar kontrolü yapılmadı. Özgün kayıt, hash ve ayrıntılar
`output/rx-wideband-20260916/RAPOR.md` içindedir. KTR-4.1 / KTR-4.1-OPS-B0,
PHASE-08/ST-06 fiziksel kabulü açık kalır; yeni faz açılmadı.

## Tam bant taraması ve liste gözlemi — 16 Eylül 2026

1 MHz–6 GHz gözleminde PC tarama biriktiricisinin aynı karedeki ayrı
grupları bir geçmiş kayda tekrar sayabildiği görüldü. Bu, kart kare sayısının
artması değildir; `observed_frames` süreklilik yorumunu etkileyen açık host
sayaç hatasıdır. PL/PS algoritması bu incelemede değiştirilmedi. Ayrıntı
`output/rx-wideband-20260916/RAPOR.md` içindedir.

PHASE-08/ST-06 açık; bu kayıt yeni fiziksel kabul oluşturmaz.

## Tespit sunumu sınırı — 16 Eylül 2026

Tarama ekseni görüntülenen spektrumun merkez/hız metadatasını kullanır.
Tespit, ek alıcı ayarıyla doğrulama ve geçmiş kayıt durumları sunumda ayrıdır.
Aday sınırlarının ortalaması işgal bant genişliği ölçümü değildir. Bu değişiklik
QML/görünüm modelindedir; PL, ARM aday/temporal hesabı, CFAR ve RF kazançları
korunur. Fiziksel kabul durumu SIGNAL_DETECTION_STATUS.md içinde tutulur.

## Alıcı ayarlarının uçtan uca bağlanması — 15 Eylül 2026

RF AMP, alım oturumu yapılandırmasının parçasıdır; sabit izleme ve tarama
doğrulamalarında korunur, açık/kapalı durumları aynı güç kalibrasyonu sayılmaz.
Alım sürerken değiştirilmez. CFAR kontrolü mevcut kart protokolünü ve geri
okumayı kullanır; RTL/eşik matematiği değişmedi. NFM ses düzeltmesi PC dinleme
dalındadır ve tespit/parametre I/Q'sunu değiştirmez. LNA/VGA ana ekranda kalır;
örnekleme profilleri ve analog filtre politikası değişmedi.

## Tarama hızının değerlendirilmesi — 15 Eylül 2026

Fiziksel alıcı örnekleme ayarı ile sistemin işlediği örnek sayısı ayrıdır.
Sabit izleme 8 MS/s alır, filtrelenmiş 2 MS/s alt bandı işler. Ürün bant
taraması 10 MS/s alır ve örnek azaltmadan sonlu pencereler işler. Üst bilgide
yalnız alıcı ayarı gösterilir; bu sürekli işleme hızı iddiası değildir.

Güncel tarama planı 2,5 MHz sorumluluk adımıyla 1 MHz–6 GHz için 2400 pencere
üretir. Varsayılan 128 kare, 4096 FFT ve 10 MS/s ile pencere başına ana RF
gözlemi 52,4288 ms'dir. Geçmiş 800–840 MHz QML kaydının 16 penceresinde ana
aşama 5,608 s, ek doğrulama 1,608 s, ana RF gözlemi 0,839 s olmuştur.
8 saniyelik kısa turu 2400 pencereye doğrusal ölçeklemek yaklaşık 20 dakika
verir; bu yalnız tahmindir. Aday yoğunluğu, kazanç/taşıma tekrarları ve bağımsız
yeniden ayarlamalar tam bant süresini değiştirebilir; 45 dakika kök nedeni
tam tur kaydı olmadan kesinleşmez.

PL Hann/FFT/güç/OS-CFAR hesabı yapar. ARM CPU0 DMA ve çözme, CPU1 aday ve
temporal işleme yürütür; dört öğelik iş kuyruğu zaten vardır. 5 Eylül farklı
ikiliyle yapılan kart içi tanı DMA+PL için ortalama 1,518 ms, ARM çözme+tespit
için 1,757 ms bildirmiştir (`st06-pipelined-dma-profile-v1.json`). Bunlar örtüşen
aşamalardır, süreleri tek bir sıralı gecikme gibi toplanmaz ve güncel ikiliye
aktarılmaz. 14 Eylül 10 MS/s burst tüketimi yaklaşık 500 kare/s iken gereken
2441,40625 kare/s'dir. Mevcut mimarinin PC-only eşdeğerinden daha hızlı olduğu
ölçülmüş değildir; PL tasarım saatinden uçtan uca hız çıkarılamaz.

İncelenecek iyileştirmeler, henüz uygulanmış yetenek değildir:

1. Aynı kayıt/algoritma/FFT/eşik/gözlem süresi ile PC ve kart sürelerini ölçmek;
   güncel kartta DMA/çözme/aday/temporal ve pencere kurulum sürelerini ayırmak.
2. Her pencerede alıcı süreç/oturum açıp kapama maliyetini kalıcı alım ve kontrollü
   yeniden ayarlamayla azaltmak; frekans geçişinde eski örnekleri ayırmak.
3. Kare başına DMA/servis maliyetini toplu aktarım ve örtüşen tamponlarla azaltmak;
   ARM'ın tüm güç hücrelerini tekrar işlediği pahalı aşamaları ölçüp uygun kısmını
   PL'ye taşımak. Daha büyük kuyruk tek başına sürekli kapasite artırmaz.
4. Geniş bant FFT'nin iki kullanılabilir yanını kapsayan tarama planını sınamak;
   merkez/kenar kör bölgeleri ve tam sinyal desteği korunmadan adımı büyütmemek.
5. Hızlı keşif ile ayrıntılı doğrulamayı ayırmak; kısa/darbeli/zayıf sinyallerde
   kaçırma ve yanlış alarm ölçmek. Önceki kaba-sweep denemesi tüm pencereleri
   tekrar seçtiği için hız kazandırmamıştır.

HackRF'nin 20 MS/s donanım sınırı yazılım diliyle yükselmez. Yerel 14 Eylül
USB koşularında 20 MS/s taşmalı, 8/10 MS/s kısa tekrarlar taşmasızdı. 10 MS/s
sürekli hedefi önce alım ve kart yolunda birlikte kanıtlanmalıdır. Örnekleme
hızı yükselirken FFT sabitse frekans hücresi genişler ve kare başına gözlem
süresi kısalır; zaman eşikleri ve tespit doğruluğu ayrıca doğrulanır.

## Canlı RX yerleşme sınırı — 15 Eylül 2026

PC, her fiziksel HackRF oturumunun ilk sekiz ham karesini kanal seçici durumunu
yerleştirmek için tüketir. Bu kareler PL/ARM taşımasına veya kullanıcı sonuç
sayısına girmez; giriş ve kanal seçici çıkış kırpılmaları ayrı tanı olarak
tutulur. Sonraki ilk ölçüm karesi FPGA'ya sıra/frame kimliği `0` ile gider ve
bu noktadan sonraki tam ölçek bileşeni mevcut fail-closed kırpılma hatasını
üretir. En çok 64 yerleşme karesine izin veren iç capture sınırı, sunulan
30 dakikalık oturum sınırından ayrıdır.

## Elle alıcı kazancı sınırı — 15 Eylül 2026

PC operatör arayüzü LNA/VGA seçimlerini HackRF canlı oturumuna doğrudan verir.
Başlangıç örneklerinden seviye çıkarıp kazancı değiştiren veya yeni oturum
başlatan otomatik kontrol yolu yoktur. I/Q kırpılması koşuyu durduran ayrı bir
veri bütünlüğü korumasıdır; otomatik kazanç davranışı değildir. 14 Eylül tarihli
otomatik kazanç ölçümleri yalnız geçmiş kaynak sürümünü tanımlar.

## Ölçülen tarama yolu ve darboğaz — 14 Eylül 2026

Güncel sabit frekans izleme yolu HackRF'den 8 MS/s CI8 alır, PC'de 4:1 kanal
seçimiyle 2 MS/s üretir ve 4096 örneklik P0IQ karelerini ZedBoard'a gönderir.
Frekans taraması ise 10 MS/s CI8'i PC'de yeniden örneklemeden, 4096 örneklik
sınırlı burst'ler halinde karta gönderir. PL içindeki
Hann → FFT → güç → OS-CFAR aritmetik hattı 50 MHz'de saat başına bir karmaşık
örnek kabul etmek üzere tasarlanmıştır. Uçtan uca hız yaklaşık 488 kare/s
sınırındadır; kare başına ağ işlemi, DMA ve ARM servis döngüsü PL aritmetiğini
besleyen sınırlayıcı yoldur. Bu nedenle 10 MS/s yolu sürekli gerçek zaman akışı
değil, en fazla 256 karelik tarama burst'üdür.

Deneysel `hackrf_sweep` iki turlu kaba taraması PC'de aday üretebilir; fakat
fiziksel 800–840 MHz koşusunda tüm 67 kart penceresini seçip hız kazandırmadı.
Bu nedenle ürün mimarisine kabul edilmedi ve kullanıcı arayüzünden çıkarıldı.
10 MS/s ham RX aynı USB yerleşiminde üç kısa tekrarda overrun üretmedi;
20 MS/s üretti. 10 MS/s sınırlı, doğrudan CI8 algılama burst'ü P0IQ
metadatasıyla taşınır; PC kanal seçici çalışmaz ve otomatik parametre isteği
reddedilir. Linux köprü loopback'i ve ARM cross-build geçti. Kartta çalışan
eski köprü profili 10 MS/s fiziksel isteği reddetti. Yeni köprü ayrı yetenek
bitiyle ve en fazla 256 karelik sınırla çalıştırıldı; üç 64 karelik
fiziksel burst sıfır USB/taşıma hatasıyla tamamlandı. Ölçülen kart tüketimi
`498,744–505,719 kare/s`, sürekli 10 MS/s için gereken hız `2441,40625 kare/s`
oldu. Köprü `image.ub` kök dosya sistemine alındı; kontrollü yeniden başlatmada
FPGA, ARM hizmetleri ve yetenek sorgusu geçti. Sürekli 10 MS/s için toplu
DMA/servis ve seyrek aday çıkışı gerekir; bunlar henüz uygulanmış özellik değildir.

Deneysel tarama planında 10 MS/s FFT'nin yalnız merkezden en az 1 MHz uzaktaki
ve bant kenarına 1 MHz guard bırakan tarafı sorumluluk alır. 1 MHz'ye kadar tam
sinyal desteği için pencere ilerlemesi 2,5 MHz'dir. İlk geniş bant adayları
mevcut 2 MS/s karşı-LO doğrulamasına gider. Sayısal enjeksiyonda dört dış/iç
tonun hücre eşlemesi tam geçti. Yayın açık iki kör tekrarda 800 MHz dar ve 820 MHz
geniş gözlemleri karşı-LO 2 MS/s yolunda doğrulandı. Her iki hedefin `±1` ve
`±3,25 MHz` yerleşimleri kalıcılık kapısını geçti. Güncel kaynakla gerçek QML
eylemi kullanılarak 128-kare koşu 16/16 pencereyi `8,00 s` içinde sıfır hatayla
bitirdi. TX-kapalı negatif,
genel Pd/Pfa, tam bant ve elektrik kesip açılan soğuk başlangıç açık kalır.

## ED sonuç teslimi ve kayıt ömrü — 13 Eylül 2026

PC görüntü kuyruğu yalnız en son spektrumu tutmaya devam eder. Karttan dönen
otomatik parametre sonuçları ayrı `_LiveSnapshotMailbox` içinde GUI teslimine
kadar korunur; 1.024 sonuç sınırı aşılırsa alım açık hata ile durur. Katalog
işlemleri sonunda SQLite bağlantısı kapatılır. Geçersiz kalibrasyon dBm
üretmez; bozuk katalog dosyası korunarak kayıt özelliği hata durumunda kalır,
ED arayüzü açılabilir. PC/PL/ARM sayısal görev paylaşımı ve protokoller değişmedi.
[İnceleme ve kabul sınırları](../reviews/ED_RELEASE_REVIEW_20260913.md).

## Yalnız ED mimarisi — 13 Eylül 2026

Güncel ürün mimarisi yalnız RX tabanlı ED işlevlerini içerir. ET görev alanı,
dalga biçimi üretimi, HackRF TX platform katmanı ve ET çalışma zamanı
kaldırılmıştır. İkinci HackRF yalnız ED alıcı rolüyle tanımlanabilir; TX rolü
yoktur. Tarihli eski ET mimari bölümleri geçmiş kayıt niteliğindedir.

## İki alıcı rolü ve canlı parametre kayıt yolu — 13 Eylül 2026

Bilgisayar-1 iki HackRF seri kimliğini `ED_RX_PRIMARY` ve `ED_RX_SECONDARY`
olarak ayrı izler. Birincil rol mevcut 8 MS/s RX → 2 MS/s kanal seçici →
ZedBoard tespit yolunu besler. İkincil rol envanterde tanınır; ikinci eşzamanlı
capture, iki akışın zaman/frekans hizası ve bunun performansı henüz fiziksel
kanıtlanmadığı için işlem sahibi olarak gösterilmez.

Kart P0CQ ile destek bildirirse host confirmed olayları güç sırasına koyar ve
bir seferde bir olay için dört P0IQ karesine parametre bağlamı ekler. Ağ köprüsü
bunu yerel ABI v2'ye çevirir; PL tespit/güç işlemi ve ARM temporal karar her
karede çalışmayı sürdürürken aynı güç/CI8 verisi parametre çekirdeğine verilir.
PC sonucu doğrular ve SQLite kataloğuna yazar; sayısal kestirim yapmaz. Eski
köprüde otomasyon kapalı kalır, normal tespit trafiği korunur.

dBFS dijital tam ölçeğe göredir. PC yalnız seri, 2 MS/s çıkış bağlamı, LNA/VGA,
kanal seçici genlik ölçeği, frekans aralığı ve süre tam eşleşen bir ölçülmüş
kalibrasyon profilinden dBm türetir. Boş/geçersiz/eskimiş profil `Kalibre değil`
sonucudur; varsayılan ofset veya extrapolasyon yoktur.

## Saat yönünde bağıl yön arayüzü — 13 Eylül 2026

PC ürün arayüzü anten yönü sensörü gibi davranmaz. Operatörün belirlediği ilk
fiziksel eksen `0°` sayılır; tek ölçüm eylemi yalnız başarılı dört kareli ölçüm
sonrasında hedef etiketi saat yönünde 15° artırır. QML serbest açı veya coğrafi
referans almaz ve yalnız bağıl tepe yönünü gösterir. PC, PL ve ARM arasında
zaman tabanlı açı üretimi eklenmemiştir.

PL/ARM P0PM kanal gücü ve P0DF tam tur hesabı değişmedi. Düşük seviye manuel
coğrafi referans veri sözleşmesi tarihsel kayıt uyumluluğu için korunur; güncel
ürün iş akışının girdisi veya çıktısı değildir. Fiziksel dönüş doğruluğu halen
operatör/mekanik düzen sorumluluğundadır; otomatik sürekli dönüş için ölçülmüş
enkoder/IMU bağı ve yeni kabul kanıtı gerekir.

## Parametre sonuç sunumu — 13 Eylül 2026

PL/ARM hesap paylaşımı değişmedi. PC görünüm modeli doğrulanmış P0PR alanlarını
ve `F1Quality` tanılarını kullanıcıya yönelik satırlara dönüştürür; QML yalnız
bu durumları ve Türkçe ret nedenlerini sunar. Ana parametre hesabı PC'ye
taşınmaz ve kart hatasında sayısal geri dönüş eklenmez. Sonuç ekranındaki alan
geçerliliği fiziksel doğruluk kabulünden açıkça ayrılır.

## Geniş aralık ölçüm sürümü — 12 Eylül 2026

P0PM-v2, PL 4096 FFT/güç ve ARM sayısal hesap paylaşımını korur. ARM yerel
spektrum kapasitesi 3984 analiz + iki yanda 36 hücreye genişletildi; dört
gözlemin kalıcı sayısal yükü 389.376 bayttır. Eski 64 KiB host profiline
ait bellek iddiası bu kart sürümüne aktarılmaz. Yeni kart P0PR-v2 döndürür;
eski 512 hücrelik P0PM-v1 istekleri kabul edilir fakat eski yanıt okuyucuları
yeni sürümü reddeder. Arayüz ve kart hizmeti/ağ köprüsü birlikte güncellenir.
Derleme ve portable eşdeğerlik geçti; yeni ikililer doğrulanmış ZedBoard'a
yüklendi. Altı dar sahne ile bir gerçek kayıtlı geniş ölçüm kartta geçti.
Genel RF doğruluğu ve geniş bant OBW kabulü açıktır.

## Analog/Sayısal sınıflandırma görev paylaşımı — 12 Eylül 2026

PÇ-03 ürün bağlantısında sınıflandırma PC'dedir. Mevcut ölçüm işçisi dört
ardışık CI8 kareyi sabitledikten sonra taşıyıcı, OBW, güç ve SNR için P0PM ile
PL/ARM yolunu çalıştırır. Aynı kareler ve operatörce onaylanan analiz aralığı
PC'deki sınırlı kanal seçme, altı özellik ve lojistik regresyon zincirine girer.
Kart sınıflandırma yapmaz; kart hatasında ilk üç parametre için host geri dönüşü
yoktur. PC sınıflandırma kaydı model/source hash'i, özellikler, olasılık ve
`%90` güven kapısını taşır. Güven geçmezse `Belirsiz` yayımlanır. Sentetik
model sonucu canlı RF veya ürün doğruluk kabulü değildir.

## Yön ölçümünün kanal bağı — 12 Eylül 2026

PC operatörün seçtiği kanalı ve alıcı bağlamını sabitler; her açı isteğinden
sonra host kuyruğundaki eski kareleri dışlayarak dört ardışık, tek confirmed
kanal gözlemini toplar. Olay numaraları değişebilir ve ayrı kaydedilir; verici
özdeşliği çıkarılmaz. Beş saniyelik toplama sınırı ve iptal vardır. PL/ARM P0PM
güç hesabı ve 24 açı sonundaki ARM P0DF kararı değişmedi. Fiziksel RF/RMS kabulü
açıktır. [Güncel sözleşme](../interfaces/SIGNAL_DIRECTION_FINDING_STATUS.md).

## Genlik tabanlı yön bulma görev paylaşımı — 11 Eylül 2026

PL/ARM tespiti hedefin `confirmed` olduğunu ve spektral sınırlarını sağlar.
Güncel arayüz her açıda aynı hedefin dört ardışık karesini sabitler. Kartın P0PM
yolu kareleri PL Hann → 4096 FFT → güç zincirinden geçirir; ARM'ın gürültüsü
çıkarılmış kanal dBFS sonucu hedef frekansı, sabit kanal aralığı, kare kimliği ve
LNA/VGA bağıyla kaydedilir. 24 açılık alan profili tamamlandığında kayıtlar CRC
korumalı `P0DF-v1` isteğiyle karta
taşır; ZedBoard ARM taşınabilir C çekirdeği kapsama, frekans/alıcı tutarlılığı,
tepe belirginliği, ön/arka ayrımı, ham maksimum ve dairesel RMS metriklerini
üretir. PC sonucu doğrular ve gösterir; canlı ürün ARM yanıtı olmadan nihai LOB
göstermez.

Geçici 47008 ve yeniden başlatılmış kalıcı 47007 hizmetleri gerçek kartta yedi
sayısal hazır/ret sahnesini geçti. `image.ub` ve kök dosya sistemi hash ile
bağlandı. Saha öncesi görev paylaşımı tamamlandı; HackRF, yönlü anten, bilinen
bağıl açı ve gerçek ortam derece RMS kabulü henüz tamamlanmamıştır.

## İlk üç parametrenin ürün görev paylaşımı — 11 Eylül 2026

Canlı alım ve kanalizer PC'de kalır. Operatörün seçtiği dört ardışık 4096 CI8
kare PC'de yalnız sabitlenir ve kaydedilir. Ölçüm sırasında aynı baytlar karta
geri gönderilir; PL Hann, 4096 FFT ve doğrusal gücü üretir. ARM emisyon merkezi,
gözlenen taşıyıcı çizgisi, OBW %99, dBFS kanal gücü ve SNR'yi hesaplar. PC
yanıtı doğrular, kaydeder ve gösterir; sayısal parametre kestirimi yapmaz.
Kart başarısızsa ilk üç parametre için PC hesabına geri dönüş yoktur.

Bu ölçüm komutu yeni canlı tespit iddiası üretmez; daha önce dört kare boyunca
doğrulanıp sabitlenmiş operatör seçimini yeniden işler. Ölçüm yalnız FPGA FFT
4096 iken çalışır. Sinyal sınıflandırması aynı karelerde ayrı PC işlevi olarak
çalışır ve ARM sonucuyla karıştırılmaz. dBm için ARM
kalibrasyon kapısı vardır; fiziksel alıcı kalibrasyonu bulunmadığından ürün
şimdilik dBFS gösterir.

## Çalışma zamanı FFT ürün yolu — 11 Eylül 2026

PC arayüzündeki tespit FFT seçimi, destekleyen kartta ABI v2 kontrol mesajıyla
ARM hizmetine; oradan sürücü ioctl'u ve `0x53540602` AXI-Lite kontrol bankasıyla
PL'ye ulaşır. Profil yalnız DSP boşken uygulanır ve etkin 4096/8192/16384 değeri
aynı yoldan geri okunur. Ağ/ARM/DMA çerçevesi FFT başına 8.192/16.384/32.768
bayt CI8 ve 32.768/65.536/131.072 bayt güç taşır.

PL, seçilen uzunluğa ait periyodik UQ1.15 Hann ROM'unu, azami 16384 dinamik
AMD XFFT'yi, uzunluğa göre güç normalizasyonunu ve OS-CFAR'ı yürütür. ARM,
8192 ve 16384 güç hücrelerini enerji toplayarak yerleşik 4096 olay ızgarasına
indirger; böylece mevcut geniş bant ve temporal sözleşmeler korunur. 4096 için
doğrudan çözücü; üst boyutlarda ikiye/dörde indirgeme kaydırmaları kullanılır.
Üç tekrarlı fiziksel sayısal hız kapısı geçti. Hann dışındaki pencere türleri
uygulanmadı. [Kanıt](../interfaces/DETECTION_RUNTIME_CONFIG_CONTRACT.md).

## ST-06 DMA v2 kaynak değişikliği — 10 Eylül 2026

PL güç kelimesinde `63:61=110`, bit 60 zayıf, bit 59 normal karar, bit 58
değerlendirme, alt 58 bit güçtür. CPU0 yeni çözücüyle maskeyi çıkarır;
CPU1 yalnız zayıf bölge tepesinin sıra istatistiğini çıkararak 24/32
biriktirmesine bağlar. Dar/grup, geniş bant ve normal temporal ARM’da kalır.
Eski A biçimi normal yolda desteklenir. Yeni FPGA/hizmet birlikte fiziksel
kabul bekler. Görüntü FFT seçimi PL FFT’sini veya PC RF doğrulama spektrumunu
değiştirmez. [Kaynak kılavuzu](../interfaces/DETECTION_TUNING_AND_SOURCE_GUIDE.md).

## Dört parametrenin gerçek RF durumu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: yeni temiz AM koşusunda dar aralık SNR'si
13,36–15,32 dB iken sabit aday 10/10 Belirsiz kaldı. Yeni `rf_observation`
ürün dışı ön işlemesi uzun I/Q, FIR kanal süzme ve frekans kayması
hipotezlerini uygular; kesin sınıflandırıcı değildir. Kullanılabilir donanım
son beyana göre yalnız iki HackRF'dir; dBm kalibrasyonu diğer işleri durdurmaz.
Ürün/ARM/RTL ve önceki kabul durumları değişmedi.

Yeni modül yalnız PC geliştirme referansıdır; 50–500 ms ham gözlemin
FIR/örnek azaltma ve ikinci/dördüncü kuvvet özelliklerini çıkarır. 250 ms
gerçek kayıt değerlendirmesi yapılmıştır. QML'nin dört karelik F5 akışı,
PL DSP zinciri ve ARM hizmeti bu modülü çağırmaz. ARM süre/bellek kabulü yoktur.

[Ayrıntılı durum, araştırma ve yeniden üretim](../reviews/PARAMETER_EXTRACTION_ASSESSMENT.md).


## Replay BPSK G8 tanı koşusu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı `03_BPSK.C16` için Play teyidi verdi.
RX 24/24 dB kaydında 20,35–26,20 saniye arasında 5,90 saniyelik hedef bant
etkinliği görüldü. Bu süre RF öncesi hazırlanan 6 saniyelik BPSK dosyasıyla
uyumludur. Kayıtta bir USB taşması bulunduğu için koşu kabul paydasına alınmadı.

Dondurulmuş PC adayı 1,32–4,70 dB SNR nedeniyle 10/10 `low_snr` Belirsiz
üretti. AM, NFM ve BPSK fiziksel kayıtlarının aynı kalite kapısında kalması,
sorunun tekrar sayısından çok adayın gerçek Replay veri alanı ve SNR tanımıyla
uyumsuz olduğunu gösterir. Aynı koşu körlemesine tekrarlanmaz; yöntem ayrı
geliştirme verisiyle düzeltilip yeni kör RF ile sınanmalıdır. Ürün, fiziksel
analog/sayısal kabul ve dBm kalibrasyonu açık. Kanıt:
`results/evidence/phase08/replay-bpskg8-diagnostic-20260909.json` ve ZIP.

## Replay NFM G8 fiziksel tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: `02_NFM.C16` için RX 24/24 dB kaydı tam boyutta,
sıfır USB taşması ve sıfır kırpılmayla alındı. Faz ayrıştırıcı 1702,88 Hz
tepe ölçtü; RF öncesi hazırlanan dosyanın mesaj tonu 1700 Hz'dir. Çizgi
etkinliği yalnız kaba zaman seçimi için kullanıldı ve 21,50–27,25 saniye
aralığını işaretledi. NFM taşıyıcı bastırması nedeniyle bu işaretler güç veya
bant ölçümü olarak yorumlanmadı.

Dondurulmuş PC adayı, önceki temiz CW merkezi ve RF öncesi manifest aralığıyla
incelenen on pencerede −2,33 ile +0,99 dB SNR buldu; 10/10 sonuç `low_snr`
nedeniyle Belirsiz kaldı. Fiziksel NFM içeriği gözlendi, fakat analog/sayısal
sınıflandırma kabulü geçmedi. Model ve eşik bu kayıtla değiştirilmedi. Ürün F5,
ARM/FPGA, dBm kalibrasyonu ve genel fiziksel kabul açık. Kanıt:
`results/evidence/phase08/replay-nfmg8-evaluation-20260909.json` ve ZIP.

## Replay AM G8 ve aralık tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı AM G8 hazırlığını bildirdi; RX 24/24 dB
kapalı ve açık kayıtları tam boyutta, sıfır taşma/kırpılmayla alındı. Açık
kayıtta 6,15 saniyelik tek etkin bölüm ve 1699,22 Hz zarf tonu, hazırlanan
6 saniye/1700 Hz AM dosyasıyla uyumludur. Ayrı Play yanıtı kayda ulaşmadı;
TX Gain 8 ekran fotoğrafıyla doğrulanmadı. Sabit nominal 98,1 kHz aralıkta
10/10 sonuç 1,72–3,89 dB SNR nedeniyle Belirsiz kaldı.

Koşu sonrası tanıda aralık gözlenen 824990308 Hz çevresine taşındı. 8,3–16,1
kHz aralıklarda on pencerenin kalite kapısı geçti ve SNR 7,80–13,93 dB oldu;
Analog skor 0,64–0,83 ile sabit 0,90 eşiğin altında kaldı, 10/10 Belirsiz.
Bu sonradan yapılan aralık taraması kabul paydasına alınmaz. Bulgular seviye
ve aralık sorununun yanında gerçek Replay AM için model genelleme açığı
olduğunu gösterir; model/eşik bu kayıtla değiştirilmedi.

Sonraki aileler aynı sabit modelle değerlendirilir; gelecekteki yöntem
geliştirmesi ayrı sayısal veriyle yapılır ve yeni kör RF gerekir. Ürün F5,
ARM/FPGA, dBm ve genel fiziksel kabul açık. Kanıt:
`results/evidence/phase08/replay-amg8-evaluation-20260909.json` ve ZIP.


## Replay AM 32/32 dB karşılaştırması — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: verici kapalı 10 saniye ve AM penceresi RX 32/32
dB'de tam boyutta, sıfır taşma ve sıfır kırpılmayla alındı. AM kaydında
1699,22 Hz zarf tonu hazırlanan 1700 Hz dosyayla uyumludur; Play basışına
ait ayrı operatör yanıtı kayda ulaşmadı. Sabit aday on pencerenin tamamında
−9,09 ile +0,70 dB SNR ve `low_snr` nedeniyle Belirsiz kaldı. RX kazancını
24/24'ten 32/32 dB'ye çıkarmak aday SNR'sini iyileştirmedi; alıcı kazancı
daha fazla yükseltilmez.

Model/eşik değiştirilmedi. En düşük TX kazançta taşmasız CW bağlantısı
görüldüğünden sonraki kontrollü aday, Amp kapalı ve TX Gain 8 ile AM tekrar;
RX yeniden 24/24 dB'dir. Bu güç kalibrasyonu değildir. Verici kimliği,
genel fiziksel kabul, dBm ve ürün/ARM/FPGA kapıları açık kalır. Kanıt:
`results/evidence/phase08/replay-am32-evaluation-20260909.json` ve ZIP.


## Replay AM 24/24 dB değerlendirmesi — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: operatör doğru `01_AM.C16` dosyasını seçip Play'e
bastığını bildirdi. 825,3 MHz, 8 MS/s, RX 24/24 dB kaydı tam boyutta;
USB taşması ve kırpılma sıfırdır. Ayrı zarf tanısı 1699,22 Hz tepe buldu;
hazırlanan 1700 Hz AM mesajıyla uyumludur. Sabit v6 model/v9 adayın on
penceresi 2,04–4,38 dB ölçüm SNR'sinde 10/10 `low_snr` nedeniyle Belirsiz
kaldı. Bu fiziksel AM sınıflandırma kapısını geçmez; eşik/model değiştirilmedi.

Tek yayın kaydının on penceresi bağımsız on RF koşusu değildir. Verici seri
kimliği açık, dBm ve mutlak frekans kalibrasyonu yoktur. Ürün F5, ARM ve FPGA
kullanılmadı. Önceki yanlış dosya olasılıklı kayıt AM paydasına alınmaz ve
özgün tanısıyla korunur. Sıradaki kontrollü adım daha yüksek RX kazancında
kırpılma ve sınıflandırma kontrolüdür. Kanıt:
`results/evidence/phase08/replay-am24-evaluation-20260909.json` ve ZIP.


## Replay CW taşmasız gözlem — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı USB portunu değiştirip alıcıyı HackRF
moduna aldı. Aynı seri 35138247, 825,3 MHz, 8 MS/s ve 24/24 dB'de
10 saniyelik kapalı ve 30 saniyelik CW penceresi tam boyutta, sıfır taşma
ve sıfır kırpılmayla alındı. Kullanıcı Play basıldığını bildirdi. CW
824989819 Hz çevresinde 43/598 tanı penceresinde görüldü; sonrasında
örneklenen seviye eşik altına indi. 50 ms adımlı görünür aralık yaklaşık
2,15 saniyedir; hassas RF süre kalibrasyonu veya acil Stop testi değildir.

Tek temiz kayıt kalıcı USB çözümü sayılmaz; araç hâlâ aynı yolda dört
başka cihaz bildiriyor. Eski taşmalar korunur. AM denemesi öncesi kaynak
seçimi ve alıcı kayıt eşlemesi gerekir. Model/ürün/RTL/ARM değişmedi;
fiziksel genel kabul, verici kimliği ve dBm kalibrasyonu açık kalır.
Kanıt: `results/evidence/phase08/replay-cw-clean-20260909.json` ve ZIP.


## Replay USB karşılaştırması — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: 8 MS/s, RX 24/24 dB, 825,3 MHz ayarında
verici kapalı beş saniyelik depo kaydı 1 taşma; yerel geçici klasörde
beş saniyelik kapalı kayıt 0 taşma verdi. Aynı yerel yoldaki 30 saniyelik
CW denemesi 3 taşma (en uzun 16876896 bayt) verdi. Üç kayıt tam boyutta
ve kırpılmasızdır; tam boyut süreklilik değildir. Kullanıcı Play basıldığını
bildirdi; 598 tanı penceresinde hedef artışı yok, kesin basış zamanı bilinmiyor.
Bu sonuç verici başarısızlığı veya kalibre RF yokluğu sayılmaz.

OneDrive dışına yazmak tek başına çözüm olmadı; kök neden kanıtlanmadı.
HackRF aracı aynı USB yolunda dört başka cihaz bildiriyor. Sonraki adım
alıcı USB bağlantısını doğrudan farklı bağlantı noktasında sınamak; yeni RF
denemesinden önce kapalı süreklilik kontrolüdür. Ürün/model/RTL/ARM değişmedi.
Kanıt: `results/evidence/phase08/replay-usb-comparison-20260909.json` ve ZIP.
Geçici klasörlerdeki ham kayıtlar da arşive alındı; önceki başarısızlıklar korunur.


## Replay CW gözlendi; USB sürekliliği başarısız — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: hazır bildirimi ardından alınan 24/24 dB kayıtta
824989697 Hz çevresinde 43/598 tanı penceresi eşik üstündedir; ardından
örneklenen seviye eşik altına iner. Ham dosya tam boyutta ve kırpılmasızdır,
ancak araç günlüğünde 3 USB taşması, en uzun 4527552 bayt vardır. Örnek
indislerinden görünen yaklaşık 2,15 saniye kesin RF süresi sayılamaz.
CW bağlantı gözlemi vardır; otomatik durdurma/süreklilik kabulü kapanmadı.
`capture.json complete` yalnız boyut/çıkış kodu kontrolüdür.

Önceki 24/24 penceresinde kullanıcı mesajı geç gördü; o negatif kayıt TX
başarısızlığı değildir. Fotoğrafta CW, 825 MHz, 500 kHz, G:0/A:0 ve Loop
kapalı görüldü. Model/ürün/RTL/ARM değişmedi; dBm ve mutlak frekans açık.
Sonraki koşu süreklilik tanısı çözülerek kısa eşzamanlı kayıttır.
Kanıt: `results/evidence/phase08/replay-cw-detected-20260909.json` ve ZIP.


## Replay CW ilk fiziksel tanı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: 825,3 MHz merkez, 8 MS/s, RX 16/16 dB'de
bir saniyelik kapalı kayıt ve iki 30 saniyelik alıcı penceresi alındı.
Operatör ilk 2 saniyelik CW dosyasının kendiliğinden durduğunu, ikinci
denemede Play'e bastığını bildirdi. İki kayıtta 825 MHz ±50 kHz çevresinde
kapalı q99 +6 dB tanı eşiği üstünde 0/598'er pencere bulundu. Bu, hiç RF
yayınlanmadığının kanıtı değildir; Play anı cihaz zamanıyla bilinmiyor.
Üç ham kayıt tam boyutta, yerleşmiş alımda kırpılma sıfırdır.

Alıcı seri sonu 35138247 ve v2.4.0 cihazdan okundu. Verici sürümü yalnız
“alıcıyla aynı” kullanıcı beyanıdır; seri ve gerçek Replay ekran ayarı
doğrulanmadı. CW/otomatik RF durdurma kabulü kapanmadı; sonraki adım ekran
ayarını doğrulamak, ardından gerekli eşleşmiş alıcı denemesidir. Sayısal
yayınlara geçilmedi; model/ürün/RTL/ARM değişmedi, dBm kalibrasyonu açık.
Kanıt: `results/evidence/phase08/replay-cw-initial-attempts-20260909.json`
ve ZIP; ham I/Q, günlük, komut ve tanı kaynakları korunur.


## PortaPack Replay kaynak hazırlığı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcının SD kartla bağımsız verici kullanma
talebi üzerine 825 MHz nominal merkezli, 500 kS/s C16/TXT paketi hazırlandı.
CW 2 saniye; AM/NFM/BPSK/QPSK/FSK altışar saniyedir. Sayısal aileler ayrı
sabit tohumlu rastgele veri taşır. Üretici sınıflandırıcıyı çağırmaz; model,
ürün F5, RTL ve ARM değişmedi. İlk paket CW referansında DC çıkarımı hatası
nedeniyle teslim edilmedi; v2 sonlu referans kontrolünü ve altı testi geçti.

Dosya bitleri ve süreleri doğrulandı; RF gönderilmedi, SD oynatma henüz
sınanmadı. Kullanıcı iki HackRF ile devamı seçti. Bildirilen yaklaşık
XDG2060/60 MHz üreteç ve osiloskop 825 MHz mutlak kalibrasyon kanıtı değildir;
dBm kapalı kalır. İlk adım verici kapalı alım, ardından tek 2 saniyelik CW
ve durdurma kontrolüdür. Ayarlar/sürüm/kimlik kaydedilmeden RF kabulü yapılmaz.
Talimat: `docs/plans/PARAMETER_REPLAY_LAB_GUIDE.md`.
Kanıt: `results/evidence/phase08/parameter-replay-preparation-20260909.json`
ve ZIP. Açık fiziksel sınıflandırma, kalibrasyon ve ürün kapıları korunur.


## Ayrı üreticiyle sınıflandırma kontrolü — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: sabit v6 model baytları ve v9 aday yöntemi,
eğitim üreticisinden ayrı `validate_candidate_numeric.py` dalga biçimleriyle
sınandı. 26000000 kök tohumda AM/NFM/FSK/BPSK/QPSK ailelerinin her birinde
24/24 doğru kesin karar; CW 24/24 Belirsiz. Toplam 144 SNR varyantı,
48 dalga biçimi tohumu vardır; 144 bağımsız yayın değildir. Protokol ve
model özeti sonuçtan önce kaydedildi; model/eşik değiştirilmedi.

Yeni `scripts/validate_candidate_classification.py` aile ve SNR bazında
doğru/yanlış/Belirsiz, karar kapsamı ve kesin karar doğruluğunu raporlar;
başarısız sayısal kapıda başarısız çıkış kodu verir. İlgili 11 test geçti.
Bu sınırlı sayısal sonuç fiziksel BPSK/QPSK kabulünü kapatmaz; OOK/QAM,
gerçek alıcı bozulmaları ve kapsam dışı aileler bu koşuda sınanmadı.
Ürün F5, RTL ve ARM değişmedi; aday ürün dışındadır. Doğrulanmış sayısal RF
kaynağıyla fiziksel kontrol, kalibrasyon ve ürün kabulü açık kalır.
Kanıt: `results/evidence/phase08/parameter-independent-classification-20260909.json`
ve ZIP; model, protokol, tam sonuçlar ve kaynaklar hash bağlıdır.


## Parametre çalışmasına devam — 9 Eylül 2026

Kullanıcının 5.1.2 kapsamındaki devam talebiyle KTR-4.2 / KTR-4.2-F1
adayının sayısal doğrulaması sürdürüldü. Yöntem değiştirilmeden 25000000
kök tohumlu 168 örnekte 96/144 desteklenen bant sonucu üretildi; 96/96
mevcut toleransı geçti. Desteklenen 48 düşük SNR örneğinde ve aralık dışı
24/24 dikdörtgen BPSK örneğinde OBW verilmedi. SNR varyantları bağımsız
yayın değildir. Sayısal güç mutlak hatası en çok 0,184 dB; bu dBm
kalibrasyonu değildir. İlgili aday/tanı testleri 10/10 geçti.

Ürün F5 ve aday yöntemi değişmedi; aday ürün dışındadır. Dört parametrenin
yarışma koşullarında birlikte doğruluğu henüz kanıtlanmadı. Sonraki açık iş,
ayarları doğrulanmış rastgele verili sayısal RF kaynağıyla sabit modelin
bağımsız kontrolü; frekans ve güç için kalibre referans karşılaştırmasıdır.
Ürün profili/ARM entegrasyonu ve fiziksel ürün kabulü ayrıca açıktır.
Bu devam kaydı sonraki fazı açmaz veya önceki başarısız RF sonuçlarını kapatmaz.
Kanıt: `results/evidence/phase08/parameter-numeric-continuation-20260909.json`
ve ZIP; çalıştırma komutu, kaynak özetleri ve tam sayısal sonuçlar korunur.


## QPSK ve kaynak dalga biçimi tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: 825 MHz QPSK beyanıyla 24/24 ve 32/32 dB'de
ikişer sonlu RX kaydı alındı. Dört kayıttaki 40 pencere kalite kapısını
geçti, 40/40 Belirsiz kaldı; model değiştirilmedi, ürün kabulü yapılmadı.
Mayhem upstream `31b25a445b166b13101ea4c6546f78b84dcc6499` incelemesinde
BPSK sabit 0–1, QPSK sabit dört sembollü döngüdür; Shape kullanılmaz.
BPSK ve kare mesajlı DSB'nin 256 faz adresindeki I/Q örnekleri aynıdır.
Bu örnekte yalnız menü etiketiyle farklı kesin Analog/Sayısal karar
beklenemez; Belirsiz tek başına algoritma hatasını kanıtlamaz. Bu bulgu
önceki başarısız RF kapsamını başarıya çevirmez. Rastgele verili sayısal
kaynak kabulü ayrıca açıktır. Ham RF çizgi aralıkları yaklaşık 2 kHz ton
hipoteziyle uyumludur; yüklü verici sürümü ve ayarı doğrulanmış değildir.
Güçlü yan çizgi taşıyıcı referansı sayılamaz. Güncel üretim F5 değişmedi;
ARM/FPGA ürün kabulü ve kalibre dBm açık kalır. Tanı komutu:
`python scripts/diagnose_siggen_reference.py --output <yeni-rapor.json>`.
Kanıt: `results/evidence/phase08/parameter-qpsk825-source-diagnostic-20260909.json`
ve ZIP (21 dosya hash doğrulaması); BPSK ham kayıtları önceki BPSK arşivindedir.

## 825 MHz BPSK fiziksel değerlendirme — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı BPSK yayınının açık olduğunu ve Shape
alanının ayarlanamadığını bildirdi. Pseudo Noise seçilmiş sayılmaz;
sembol hızı ve bit dizisi bilinmiyor. Önceki talimattaki 825 MHz/TX Gain 0/
Amp 0 cihazdan geri okunmuş ayar değildir. İki alıcı merkezinde 16/16,
24/24 ve 32/32 dB kazançlarla altı adet 0,5 saniyelik ham RX kaydı alındı.
16/16 ve 24/24 toplam 40 pencere düşük SNR kapısında kaldı; 32/32 dB'de
20 pencere kalite kapısını geçti fakat 20/20 sınıf Belirsiz kaldı.
Analiz edilen yerleşmiş bölümlerde kırpılma yok. Sayısal sınıflandırma
fiziksel kabulü başarısız; model/eşik değiştirilmedi. Farklı aralıklarla
sonradan yapılan tanılar bağımsız kabul koşusu sayılmaz. FPGA kullanılmadı.
Kanıt: `results/evidence/phase08/parameter-bpsk825-evaluation-20260909.json`
ve ZIP. Bu kullanıcı etiketli fiziksel kaynak kontrolüdür; üretici
uygulaması ve bağımsız modülasyon referansı ayrıca doğrulanmalıdır.


## Yeni 825 MHz AM değerlendirmesi — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: model/eşik değiştirilmeden 825 MHz, AM %100,
2 kHz sinüs kaynak ayarında iki merkez ve iki kazançta dört RF kaydı
alındı. 16/16 dB'de 20/20 düşük SNR reddi, 24/24 dB'de 10/20 Analog
ve 10/20 Belirsiz; yanlış Sayısal sıfır. Yeni koşul %80 karar kapsamını
geçmedi. İki yüksek kazanç kaydında zarf tonu 2000,14 Hz gözlendi.
Pencereler bağımsız RF koşuları sayılmaz; FPGA ve ürün yolu kullanılmadı.
Sınıflandırma genel kabulü açık; başarısız koşul model eğitimine eklenmedi.
Kanıt: `results/evidence/phase08/parameter-am825-evaluation-20260909.json`
ve ZIP. Sayısal aileler yalnız sentetik testlerde; fiziksel OOK/FSK/PSK/QAM,
farklı hızlar ve kapsam dışı yayın kabulü açık kalır.


## Bant kapsamı adayı v9 — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: aralık dışı enerji her uçta %0,5, Hann varyansı
ve ayrı gürültü bölgeleriyle denetlenir. Ayrı 168 sayısal örnekte 96
geçerli OBW toleransı geçti; 48 desteklenen düşük SNR örneğinde ret,
24/24 aralık dışı emisyon örneğinde ret vardır. Genel kabul değildir.
800 örneğin sınıf kararları değişmedi; eski RF AM 16/20, FM 20/20 Analog.
28 test geçti. Aday ürün dışındadır; ARM ve fiziksel ürün kabulü açık.
Kanıt: `results/evidence/phase08/parameter-band-containment-v9-20260909.json`
ve ZIP. Ayrıntı: `docs/plans/PARAMETER_REFINEMENT_PROTOCOL.md`.
Önceki v7/v8 hataları tarihsel sonuçlarıyla korunur.


## Parametre iyileştirme adayı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1 kapsamında ayrı bir sayısal aday geliştirildi:
uzun spektrum, gerçek çizgi araması, DC ayrıştırma, bant ölçekli özellikler
ve 8 bit alıcı bozulmalarıyla eğitilmiş sınıf modeli. Ürün F5 değişmedi.
Son ayrı tohum testinde 700 modülasyonlu örneğin 613'ü doğru kesin karar,
87'si Belirsiz, yanlış kesin karar sıfır; CW 100/100 Belirsiz. Aile
karar kapsamı %82–93. Önceden incelenmiş fiziksel regresyonda AM 16/20,
FM 20/20 Analog; bunlar kör fiziksel kabul değildir. Yeni aday bant
kontrolü geniş kuyruklu BPSK'de 1/6 hatalı kapsam sonucunu hâlâ kaçırır;
OBW kabulü başarısız, ürün entegrasyonu ve ARM taşıması yapılmadı.
27 ilgili test geçti. Parametre çıkarımı tamamlanmadı; aday ürün dışındadır.
Plan: `docs/plans/PARAMETER_REFINEMENT_PROTOCOL.md`. Kanıt:
`results/evidence/phase08/parameter-refinement-candidates-20260909.json`
ve ZIP; eski kaynak/kanıtlar korunur. Sıradaki iş bant kapsam belirsizliğini
ve bağımsız OBW doğrulamasını çözmek, ardından yeni ürün profilidir.


## 735 MHz AM fiziksel karşılaştırması — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: onaylı Faraday kabininde bildirilen AM %100,
1 kHz sinüs kaynağından altı ham RX kaydı alındı. İki alıcı merkezinde
999 Hz zarf tonu ve yaklaşık 1 kHz aralıklı taşıyıcı/yan çizgi deseni görüldü.
Çevrimdışı F5 tanısında 40/40 yeniden hesaplama eşleşti; sınıf 40/40
Belirsiz kaldı. 24/24 dB'de 20/20 model uzaklığı reddi, taşıyıcı 2/20
geçerli, OBW 18/20 geçerli sonucu vardı. Bunlar dört kaydın pencereleridir;
40 bağımsız RF koşusu veya doğruluk kabulü değildir. FPGA kullanılmadı.
Üretim yöntemi değişmedi; sınıflandırma, taşıyıcı ve OBW doğruluğu açık.
Kanıt: `results/evidence/phase08/parameter-rf-am735-20260909.json` ve ZIP.
Ayrıntı: `docs/plans/PARAMETER_VALIDATION_BENCH.md`.


## 735 MHz FM fiziksel parametre tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1 için kullanıcı onaylı Faraday kabininde sekiz ham
HackRF RX kaydı alındı. 16/16 ve 24/24 dB kazançta iki farklı alıcı
merkezinde yaklaşık 999 Hz FM tonu gözlendi. Gerçek I/Q üzerinde çevrimdışı
F5 tanısında 40/40 yeniden hesaplama eşleşti; sınıf 40/40 Belirsiz,
taşıyıcı 40/40 Gözlenmedi kaldı. Model uzaklığı retleri korundu.
Bu pencereler dört fiziksel kayıttandır; 40 bağımsız RF koşusu değildir.
OBW bağımsız hesap farkı, dBm kalibrasyonu ve kart/ürün kabulü açık kaldı.
FPGA kullanılmadı; üretim yöntemi ve eşikleri değiştirilmedi.
Kanıt: `results/evidence/phase08/parameter-rf-fm735-20260909.json` ve ZIP.
Ayrıntı: `docs/plans/PARAMETER_VALIDATION_BENCH.md`. Önceki ET önceliği
kaydı korunur; bu oturum kullanıcının parametre testlerine devam talebidir.


## PHASE-10 Tekli Görev sınırı — 8 Eylül 2026

Kullanıcı onaylı ET önceliği kapsamında PC, tek hedef bant için deterministik
CI8 görev verisini üretir ve fiziksel güvenlik profili geçerse seri kimliğe bağlı
HackRF sürecinin sahibidir. HackRF tekrar modu kullanılmaz; dosya ve örnek sayısı
sonludur. ZedBoard/PL bu PHASE-10 Tekli Görev yolunda bulunmaz. Bağlı cihaz ve
kapalı RF düzeni doğrulanmadığından donanım kapısı kapalıdır.

## Parametre kabul durumu ve PÇ-02 devamı — 8 Eylül 2026

KTR-4.2 / KTR-4.2-F1 tamamlanmadı. Güncel kaynakla aynı 30 sentetik
örnek tekrarlandı ve 30/30 kayıt yeniden hesaplandı; bu doğruluk kabulü
değildir. CW taşıyıcısı 1/6, AM taşıyıcısı 2/6 geçerli; 24 modülasyonlu
örneğin tamamı model uzaklığı kapısında Belirsiz kaldı. Sayısal dBFS
hatası bu kümede en çok 0,189 dB; mutlak dBm kalibrasyonu açık.
Yeni karar kapısı tanısı ve ölçüm/profil kontrolleri 22/22 geçti.
Kanıt: `results/evidence/phase08/parameter-diagnostic-20260908-v1.json`
ve ZIP. Ayrıntı: `docs/plans/PARAMETER_VALIDATION_BENCH.md`.
Kullanıcı cihazların bağlı olmadığını bildirdi; fiziksel kabul yapılmadı.
PÇ-02 sürüyor; PÇ-03–05 ve ST-06 kapanmadı. Ürün yöntemi, eşikleri,
PC/PL/PS görev paylaşımı ve önceki kanıtlar korundu. Aşağıdaki tarihli
kayıtlar kendi sürümlerinin durumunu belirtir.


## ET ürününden hazır senaryoların çıkarılması — 8 Eylül 2026

Kullanıcının hazır/sentetik ET gösterimlerini kaldırma talimatıyla KTR-5.1–5.4
ürün kapsamı güncellendi. QML ET alanından hazır dalga biçimi çalıştırma,
önceden tanımlı hedef sahneleri, otomatik test sesi ve örnek GNSS konum/UTC/PRN
formu kaldırıldı. Görev seçimi yalnız uygulanmamış gönderim durumunu gösterir;
ölçüm, grafik, zaman çizelgesi veya tamamlanmış görev sonucu üretmez.
`quick_et_actions.py` artık model çalıştırma ya da GNSS doğrulama API'si sunmaz.
`algorithms/et` ürün import ve paket sınırının dışındadır; eski konsolun ET
mixin'i de paket dışında tutulur. HackRF gönderim yolu uygulanmamıştır.

Sayısal referans modelleri, doğrulama testleri ve özgün ET-A/B/C kanıtları
geçmiş çalışmanın yeniden üretimi için depoda korunur; güncel ürün yeteneği
sayılmaz. Aşağıdaki eski ET-C arayüz kabulü kayıtları tarihsel kapsamındadır.
ED kaynakları ve açık ST-06/parametre kabul kapıları bu ET düzenlemesiyle kapanmaz.
PHASE-10–12 donanım veya RF kabulü yapılmadı. Güncel ürün sınırı
`tests/test_operator_product_boundary.py` ve
`tests/test_app_f_quick_product.py` içindeki ET yokluk denetimiyle sınanır.


## PÇ-01 ölçüm arayüzü ve güncel gözlem bağı — 7 Eylül 2026

Kullanıcının devam talimatıyla dört zorunlu sonuç ana görünümde ayrıldı:
taşıyıcı frekansı, OBW %99, kalibrasyonsuz kanal gücü (dBFS) ve Analog/Sayısal.
Emisyon merkezi, bant kenarları, SNR, gözlem süresi, hesaplama bitiş UTC zamanı
ve kayıt yolu açılır ayrıntıdadır. Sonuç, alımın durduğu kayıtlı ölçüm olarak
etiketlenir. Taşıyıcı bulunmadığında merkez onun yerine gösterilmez.

Yeni canlı ölçüm, son işlenen kart yanıtına kadar süren dört ardışık gözlemi
ister; geçmiş/seçim önbelleği yeni ölçüm girdisi olamaz. Yeniden alım eski
sonucu ve aralık onayını temizler; operatör güncel tespiti yeniden seçer.
İptal, gecikmiş çalışan sonucu yayımlamaz. Geçersiz aralık girişi önceki
onayı kaldırır. Algoritma, eşik, RTL ve kart hizmeti değişmedi; F5 bilgisayarda.

Son doğrulama: 137/137 test geçti. Main.qml 2.137, görünüm modeli 1.996
satırla mevcut mimari sınırlar içindedir.

KTR-4.2 / KTR-4.2-F1 yazılım kabul kanıtı:
`results/evidence/phase08/parameter-workflow-v1.json` ve ZIP.
1280×720 ve 1920×1080 görünüm kontrolleri kayıtlı I/Q ile yapılır.
Önceki PÇ-00 kanıtı tarihsel baytlarıyla korunur; aşağıdaki 134/135 sonucu
önceki kaynak içindir. Yeni panel ayrımı Main.qml satır sınırı bulgusunu giderir.
ST-06, fiziksel RF doğruluğu, dBm kalibrasyonu ve ARM taşıması açıktır.
PÇ-02 sıradaki planlı çalışma adımıdır; bu değişiklikle uygulanmadı.

## PÇ-00 ölçüm kaydı uygulaması — 7 Eylül 2026

Kullanıcının uygulamaya devam talimatıyla KTR-4.2 / KTR-4.2-F1 için mevcut
F5 ölçümüne kaynak ve I/Q bağlı kayıt eklendi. Canlı ve SigMF ürün ölçümü,
dört normalize I/Q karesini ve alanların birim/yöntem/durum/neden bilgilerini
ayrı ZIP'e kaydeder; kayıt başarısızsa yeni sonuç yayımlamaz. Canlı karelerde
merkez, örnekleme, sıra ve kart yanıtı bağı ayrıca denetlenir. Profil/model
özetleri, oturum ayarları, kanal seçici ölçeği ve bilinen kaynak özetleri
saklanır. Donanım UTC zamanı, çalışan kart imajı ve kalibrasyon gözlenmemişse
bilinmiyor kalır; dBm veya RF doğruluk sonucu üretilmez.
[Kayıt ve yeniden üretim sözleşmesi](../interfaces/OPERATOR_ASSISTED_PARAMETER_CONTRACT.md) sınırları tanımlar.

F5E paket denetimi mevcut iki ek logoyu açık listesine aldı; eksik model ve
izinsiz ek dosya retleri korunur. Eski F5E/PHASE-08 kanıtları değiştirilmedi.
Parametre satırlarını oluşturma işlevi mevcut ölçüm modülüne taşındı; görünen
alanlar ve algoritma eşikleri değişmedi. Yeni kanıt
`results/evidence/phase08/parameter-record-v1.json` ve ZIP içindedir.
Bu yazılım kayıt/entegrasyon kabulüdür; yeni fiziksel kart veya RF deneyi
değildir. ST-06 ve dört parametrenin saha doğruluğu açıktır. PÇ-01 arayüz
sadeleştirmesi sonraki iştir; tercihli özellikler ve PHASE-09 açılmadı.

## Parametre ölçümünün mevcut ve hedef yerleşimi — 7 Eylül 2026

Kullanıcı dört zorunlu parametre için sınırlı devam planlamasını açtı.
Bugünkü QML yolu, karta gönderilmiş ve aynı olaya ait yanıtı doğrulanmış
dört I/Q karesini PC'de sabitler; RX'i durdurup spektrumu ve F5 parametrelerini
PC'de hesaplar. Kartın `p0_ed_service` parametre isteği ve ARM sayısal çekirdeği
mevcuttur; bu QML eylemi o yolu kullanmaz. ARM çekirdeğinde emisyon merkezi,
OBW99 ve dBFS/SNR vardır; taşıyıcı ve Analog/Sayısal ayrımı yoktur.
Hedef, mevcut PL spektrumundan ve PS'ye gelen I/Q'dan dört alanı ARM'da
üretmek; PC'yi alım/taşıma/arayüz/kayıt ve referans karşılaştırmasında tutmaktır.
İlk adım yeni RTL değildir; CPU0/CPU1 tespit yüküne eklenecek maliyet ölçülür.
[PÇ-00–PÇ-05 planı](../plans/IMPLEMENTATION_ROADMAP.md) kapsam ve kabulü tanımlar.
Bu oturum donanım veya üretim yazılımı değiştirmedi; ST-06 açık kalır.

## Son arayüz düzenlemesi — 7 Eylül 2026

PC operatör arayüzünün sabit frekans ve bant taraması görünümleri ortak sayı
hizası ve görev durumlarına göre tek ana eylem kullanır. Bağlantı durumu düğme
olarak sunulmaz. Sonuçların teknik kanıtı modelde ve ipucunda korunurken ana
kartlarda frekans öne çıkar. PL/PS/PC görev paylaşımı ve RF karar yolu değişmedi.
Yedi arayüz durumu ile kaynak hash'leri
`results/evidence/phase08/st06-ui-final-20260907.json` ve ZIP içinde saklandı.
İlgili sinyal tespiti, QML ve depo sözleşmesi paketi 130/130 geçti.

## İkinci kör turun hedef bildirimi — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: operatör ikinci tamamlanan turun hedefini
sonradan 873,4900 MHz olarak açıkladı. Sabitlenmiş normal tarama kaydı
873,490442 MHz (tepe 873,490039 MHz), 120 gözlem; bağımsız alıcı ayarı
873,490094 MHz, 40 gözlem ve otomatik ikinci kontrol 873,490192 MHz,
40 gözlem ile hedefi içerir. İki doğrulama FPGA yöntemindedir; durum
Tekrar görüldü. Kapalı referans veya önceden verilen hedef kullanılmadı.
Bildirim kanıtı `results/evidence/phase08/blind-second-target-873490-20260907.json`;
ham kaynak `blind-second-survey-20260907.json` ve ZIP. Frekans farkları
kalibre mutlak doğruluk iddiası değildir. Bu tek koşul tüm ortamlarda
Pd/Pfa veya otomatik yayıncı kimliği kabulü sayılmaz; ST-06 açık kalır.


## Tam bant ve otomatik ikinci kontrol — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: 700–1000 MHz normal tarama 500/500 pencereyi
239,06 s içinde tamamladı. İlk turda USB taşması, CRC, sıra ve kuyruk kaybı
sıfır. Otomatik ikinci kontrol 124 kayıt için 27,38 s sürdü: 113 tekrar
görüldü, 11 son kontrolde görülmedi, kontrol hatası bildirilmedi.
953 MHz hedefi 952,999935 MHz olarak bulundu; ikinci kontrolde
952,999914 MHz olarak tekrar görüldü. Toplam iki aşama yaklaşık 266,44 s.
11 görülmedi sonucu yanlış alarm veya yayın kapanışı olarak etiketlenmez.
Tekrarlı Pd/Pfa, kesintisiz takip veya ST-06 kabulü değildir.
Kanıt `results/evidence/phase08/full-survey-recheck-20260907.json` ve ZIP;
fiziksel kaynaklar arşivde korunur. Ölçüm sonrasında yalnız ikinci kontrol
sırasında ilk taramanın kalan süre tahminini gizleyen sunum düzeltmesi yapıldı;
4 kontrol testi geçti. Bu son metin düzeltmesinin RF tekrarı yapılmadı.
Tam bant ikinci kontrol çalışma/süre kapısı bu koşulda gözlendi; genel
ortam kabulü ve parametre fazına geçiş açık kalır.


## Otomatik ikinci kontrolün fiziksel doğrulaması — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: operatör önceki boş kısa turda vericinin kapalı
olduğunu düzeltti. 953 MHz açık bildirimi sonrası güncel kaynakla
952,6–953,8 MHz normal tarama iki pencereyi 1,1637 s içinde tamamladı.
952,999962 MHz bulundu; otomatik ikinci kontrol 0,2526 s içinde aynı
sinyali yeniden gördü ve arayüz satırı Tekrar görüldü oldu. Ek kontrolde
48/48 kart yanıtı, USB/CRC/sıra/kuyruk hatası ve kırpılma sıfırdır.
Kaynak hash'leri, ilk tur ve yan kontrol kaydının SHA-256 bağı doğrulandı.
Kanıt `results/evidence/phase08/survey-recheck-live-on-20260907.json` ve ZIP.

Bu hedefi bilinen iki pencerelik testtir; tam bantta yeniden kontrol süresi,
kesintisiz takip, yokluk kararının fiziksel açık/kapalı tekrarı ve genel
Pd/Pfa kabulü değildir. Önceki fiziksel yeniden kontrol bekliyor notu yalnız
bu dar kapsam için kapanır. ST-06 açık; parametre fazına geçilmedi.


## Otomatik ikinci kontrol ve frekans sıralaması — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, ST-06: normal tek tur sonuçları frekans sırasıyla
sunulur. Kontrol edilmemiş enerji bölgeleri listenin sonunda kalır. Normal
tur başarıyla tamamlanınca doğrulanmış ve birleştirilmiş sinyaller bir kez
otomatik yeniden kontrol edilir. Laboratuvar kapalı/açık turları bu ek kontrolü
başlatmaz. İkinci kontrol bitmeden görev tamamlandı bildirimi verilmez.
Tekrar görüldü / son kontrolde görülmedi / kontrol edilemedi ayrı durumlardır;
alım hatası veya iptal sinyal yokluğuna çevrilmez. Kontrol zamanı ipucundadır.
`.recheck.jsonl` yan kaydı özgün taramanın SHA-256 özetini ve her sonucu
saklar; ham tarama kanıtı değiştirilmez. Bu sınırlı bir ikinci turdur,
kesintisiz izleme veya yeni yayınların sürekli keşfi değildir.

102 hedefli test ve 25 arayüz testi geçti. İptal, hatanın yokluktan ayrılması,
kayıt korunması ve görev tamamlanma sırası sınandı. 952,6–953,8 MHz fiziksel
denemede 2/2 pencere tamamlandı fakat sinyal bulunmadı; otomatik ikinci kontrol
çalışmadı. Vericinin güncel durumu soruldu; fiziksel yeniden kontrol kabulü
bekliyor. Kanıt `results/evidence/phase08/survey-recheck-20260907.json` ve ZIP.
Ek kontrol süresi genel tur süresine eklenir; tarama ve kontrol ayrı kaydedilir.
ST-06 açık; parametre fazı başlamadı.


## 953 MHz hedef eşleştirmesi ve kısa tekrar — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: operatör tamamlanan 700–1000 MHz turunun
hedefini sonradan 953 MHz olarak açıkladı. Değiştirilmemiş kayıtta
952,999989 MHz, ilk ölçümde 63 ve ikinci ayarda 23 gözlemle FPGA doğrulaması
vardır; arayüzün saklanan sıralamasında 76. satırdadır. Kapalı referans
kullanılmadan hedef listelenmiştir; otomatik hedef seçimi kanıtlanmamıştır.
Yeni dar-sinyal eşleştirmesiyle 952,6–953,8 MHz kısa fiziksel tarama
2/2 pencereyi 1,0834 s içinde tamamladı: 952,999964 MHz, ikinci ayarda
952,999955 MHz, 91/26 gözlem. Tamamlanan pencerelerde USB taşması,
CRC, sıra ve kuyruk kaybı sıfır. Bu hedefi bilinen dar aralık tekrarıdır;
300 MHz kör tarama süresi veya genel Pd/Pfa kabulü değildir.
Kanıt: `results/evidence/phase08/target953-confirmation-20260907.json`
ve ZIP; iki fiziksel kaynağın hash'leri ayrı korunur. Önceki hedef frekansı
bekleniyor notu bu bildirimle çözülmüştür. ST-06 açık kalır.


## Dar sinyal doğrulama eşleştirmesi — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, ST-06: dar ilk gözlem geniş ikinci-ayarlama
olayının içine düştüğünde yalnız aralık örtüşmesiyle kabul edilebiliyordu.
Dar ilk gözlem için ikinci olayın genişliğinden bağımsız olarak tepe
frekansı mevcut 50 kHz toleransında eşleşmelidir. Geniş ilk gözlemin
aralık tabanlı doğrulaması korunur. Yeni dar/geniş yanlış eşleşme testi ve
mevcut geniş bant tepe değişimi testi dahil 60 hedefli test geçti.
Bu değişiklik hedef frekansı öğrenilmeden yapıldı; frekansa özel kural yoktur.
Kanıt `results/evidence/phase08/survey-narrow-verification-20260907.json`
ve ZIP. Eski kayıttaki özetlerin incelemesi yeni RF sonucu değildir;
tek tek doğrulama kareleri bu kayıtta bulunmadığından başarı sayısı
sonradan değiştirilmedi. Güncel kaynak fiziksel doğrulaması bekleniyor.
ST-06 ve parametre fazına geçiş kapısı açık kalır.


## Güncel kaynakla tek tur fiziksel ölçüm — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: 700–1000 MHz, azami 24/24 dB, harici
verici açık operatör beyanıyla normal tarama 249,10 s sürdü. Kapalı referans
yüklenmedi. 500/500 pencere tamamlandı; tamamlanan pencerelerde USB taşması,
CRC, sıra ve kuyruk kaybı sıfır. 10 kazanç tekrarı, 126 ham gözlem kaydedildi.
Önceki açık turun 257,16 s süresinden yaklaşık %3,13 kısa; değişen RF yükü
ve tekrar sayıları nedeniyle nedensel hız kazancı kanıtlanmadı.
Önceki 826 MHz çevresinde ±50 kHz doğrulanmış gözlem yok; bu turun hedef
frekansı henüz açıklanmadı. Hedef başarısı veya ST-06 kabulü çıkarılmaz.
Arayüz sonuç satırları kaydedildi; pencere görüntüsü kaydedilemedi.
Kaynak hash eşleşmeleri ve ham kayıtlar:
`results/evidence/phase08/survey-optimized-live-20260907.json` ve ZIP.
Önceki mikro ölçümün fiziksel toplam süre kapısı bu gözlemle güncellendi;
tekrarlı hız kabulü ve RF hedef doğruluğu açık kalır.


## Tarama hesaplama maliyeti ve sade görünüm — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: tarama ve ikinci ayar doğrulamasında ilk kareden
sonra yalnız doğrusal FFT gücü hesaplanır; kullanılmayan genlik, logaritmik
PSD ve frekans ekseni dizileri tekrar üretilmez. Referans işlem sırası,
Hann penceresi, kare sayısı, gözlem süresi ve eşikler korunur. Ayrı hız modu yoktur.
`tests/test_detection_power.py` sıfır, DC, ton ve rastgele CI8 girdilerinde
4096/16384 boyutları ve DC çıkarımı seçeneklerinde birebir güç eşitliğini sınar.
Yerel mikro ölçüm medyanı tam yol 1,3607 ms, güç yolu 0,6442 ms;
bu toplam tarama süresi veya fiziksel RF doğruluğu kabulü değildir.

Görünümde tekrarlanan tespit yazıları, yeni etiketi, teknik pencere sayacı
ve renk açıklamaları kaldırıldı. Frekans, varsa kaba aralık ve yalnız
belirsiz bulguda doğrulama durumu gösterilir. Ayrıntılar ipucunda korunur.
Tamamlanan turda son pencere aralığı ana başlık gibi gösterilmez.
Yeni kaynakla fiziksel süre karşılaştırması açık; ST-06 tamamlanmadı.
Kanıt: `results/evidence/phase08/survey-power-20260907.json` ve ZIP.


## Tek tur tarama sunumu — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, PHASE-08 / ST-06 kapsamında bant taraması
kartlarında frekans, tespit durumu ve mevcutsa kaba frekans aralığı gösterilir.
Teknik kanıtlar ipucunda korunur. Yalnız enerji bölgeleri doğrulama bekliyor
olarak ayrılır; geçmiş tarama sonucu kesintisiz canlı yayın sayılmaz.
Dar çizgiler yalnız komşu pencerelerde, aynı kanıt sınıfında ve iki ayardaki
tepe frekansları ayrı ayrı iki FFT hücresi içinde uyuşursa birleştirilir.
Sabit eşleştirme merkezi zincirleme frekans kaymasını önler; geniş emisyonlar
ve aynı penceredeki ayrı çizgiler birleştirilmez. Ham kayıtlar değişmez.

Kanıt: `results/evidence/phase08/survey-single-presentation-20260907.json`
ve ZIP. Önceki 6679a49 kaynağıyla 700–1000 MHz kapalı/açık turları
500/500 pencere tamamladı (282,56 / 257,16 s). Açık tur sonrasında operatör
826 MHz bildirdi. Yeni sunumun yalnız açık kayıt tekrarı kapalı referans
kullanmadan 130 gözlemi 122 satıra birleştirdi; 826 MHz tekrarı da birleşti.
Bu RF algoritmasının yeni fiziksel tekrarı, yayıncı sayısı, otomatik hedef
seçimi veya Pd/Pfa kabulü değildir. Kaynaklar kanıtta ayrı tutulur.

Hedefli 99 yazılım ve 25 arayüz testi geçti. İlk alım oturumları 193,05 s, kabul edilen
130 ek doğrulama 25,92 s tuttu; süreler toplam turun bütün aşamalarını
ayrı ayrı açıklamaz. Alım hızlandırması, sürekli yeniden ziyaret ve ortamdan
bağımsız hedef seçimi henüz uygulanmadı. Eşikler, RTL ve alım süreleri
korundu. ST-06 açık; parametre fazına geçilmedi.


## Gün sonu aktarımı — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: bilinen 853 MHz CW ve 24/24 dB ile önceki fiziksel
sürümün kısa açık/kapalı ayrımı olumludur. Son otomatik kazanç ve arayüz sürümü
henüz fiziksel olarak denenmedi. Sinyal tespitinin temel yolu çalışıyor;
ST-06 tamamlandı veya her ortamda kararlı denemez. Parametre fazı başlamadı.
RF tanı kayıtları, başarısız girişimler ve yeniden üretim araçları artık
`results/evidence/phase08/rf-diagnostics-20260906.zip` içinde korunur; yanındaki
JSON her dosyanın SHA-256 özetini içerir. Arşiv köke açıldığında belgelerdeki
özgün build yolları geri gelir. Var olan dosyalar hash karşılaştırılmadan
üzerine yazılmaz. Eski ölçümler kendi kaynak özetleriyle korunur.
Sonraki oturum: önce kart/servis/çalışan imaj kimliği yeniden kontrol edilir;
yeni sürümle kısa kapalı → açık → kapalı ölçüm, otomatik kazanç yönü/döngü/iptal
ve frekans durumlarının doğruluğu sınanır. Anten konumu ve TX kazancı sabitlenir;
koşullar sonra tek tek değiştirilir. Sonuçlar uygun olursa kalan kör RF,
soğuk açılış ve güncel kaynak kabul kapıları değerlendirilerek faz kararı verilir.
Sırf önceki masaüstü geçişleri nedeniyle uzun GUI koşuları baştan tekrarlanmaz.
Sayısal ölçekleme deneyinin kazancı umut vericidir; canlı güç telafisi ve
fiziksel doğrulaması yapılmadan üretim ölçeği 1'den değiştirilmez. Otomatik
kazanç ilk seviye ayarı ve kırpılma sonrası sınırlı yeniden denemedir; kesintisiz
AGC veya kalibre güç ölçümü değildir. Optimizasyon için ölçülebilir yol vardır;
tamamlanma kararı yeni kanıta dayanacaktır.

## Sinyal tespiti kullanım ve seviye düzenlemesi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, PHASE-08 / ST-06: sabit izleme arayüzünde
isteğe bağlı otomatik kazanç (başlangıçta seçili), MHz girişi ve sade sinyal
durumları uygulandı. Başlangıç görünümü değerlendirilen ±700 kHz'e odaklanır;
kullanıcı genişletirse kapsam işareti korunur. Frekans ve alınıyor/artık alınmıyor
ana bilgidir; teknik sayılar ipucunda kalır. RF kimliği veya çift ayar doğrulaması
bu sade sunumdan çıkarılmaz.
Otomatik mod ilk 16 kareyi seviye hesabından dışlar, sonraki 32 karenin CI8
çıkışında %95'ten fazla sıfır bileşeni varsa kazançları 8 dB artırarak yeni oturum
açar. Kırpılmada 8 dB azaltır. En çok 8 girişim, tekrar ziyaret yasağı ve operatör
iptali vardır. Kırpılmış kare karta gönderilmez; denemeler ayrı oturumlardır ve
kayıpsız kesintisiz alım diye sayılmaz. %95 ölçütü mühendislik sezgisidir; genel
hassasiyet, Pfa/Pd hedefi veya RF yokluk kararı değildir. Başlangıç kırpılması
henüz sürekli kırpılmadan ayrılmıyor. Sürekli düşük-seviye takibi yapılmıyor.
Kanal seçiciye yalnız açıkça seçilen deneyler için 1–16 genlik ölçeği ve çıktı
ölçeği bilgisi eklendi; üretim varsayılanı 1. Kaydedilmiş aynı 16/16 dB açık ham
veride kayan noktalı merkez eşik aşımı ölçek 1'de 14/496, ölçek 8'de 474/496;
kapalıda ikisinde de 0/496. Beş ölçek ve açık/kapalı çiftin tümünde 512/512
Python/yerel çıktı eşleşti; kırpılma sıfır. Bu donanım FFT tekrarı değildir.
Yerel yeniden üretim: `build/acceptance/st06-gui-20260906/analyze_channelizer_scaling.py`;
özet ve SHA-256: `build/acceptance/st06-gui-20260906/channelizer-scaling-diagnosis-01.json`.
Canlı ölçekleme entegrasyonu güç/ölçek izlenebilirliği ve fiziksel doğrulama
bekler; henüz etkin değildir. RTL/CFAR katsayısı değişmedi. Yazılım testleri
kazanç yönü, döngü sınırı, iptal, MHz dönüşümü, kapsam odağı ve referans eşleşmesini
denetler. Yeni sürüm FPGA/HackRF üzerinde bu değişikliklerden sonra denenmedi;
eski fiziksel kanıt bu kaynağa taşınmaz. ST-06 ve sonraki faz kabulü açık kalır.

## Ekran incelemesi ve MHz girişi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında sabit izleme merkez girişi MHz oldu;
ondalık nokta/virgül kabul edilir, iç arayüze tam Hz aktarılır. QML testi birim
dönüşümünü, hatalı değerleri ve gerçek ayarların forma geri yansımasını denetler.
Kullanıcının 933 MHz görsellerinde yaklaşık 929,8 MHz geniş tepe, görünür
932,3–933,7 MHz tespit alanının dışındadır; bu tepenin kaynağı kanıtlanmadı.
Ham 8 MHz görüntünün tamamı aynı anda tespit kapsamı sayılmaz. 931,5 MHz ve
1198,5 MHz merkez çizgileri DC iziyle uyumludur; görüntü tek başına kimlik kanıtı
veya Pd/Pfa hesabı değildir. Tek uç-değer I/Q bileşeni oturumu durdurur; yerel
kanal seçici böyle giriş karesini sıfırladığından yalnız durdurma koşulunu kaldırmak
geçerli çözüm değildir. Kırpılma oranı/başlangıç ayrımı ve kullanıcıya daha açık
kazanç tanısı halen açıktır. MHz değişikliği DSP veya RF kabulünü değiştirmez;
önceki fiziksel sonuçlar yeni arayüz kaynağının fiziksel testi sayılmaz.

## 853 MHz eşleştirilmiş kart sonucu — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında RX LNA/VGA 24/24 dB ile aynı anten
konumunda kısa, kullanıcı beyanlı açık/kapalı kart koşuları tamamlandı. Açıkta
853 MHz olayı ilk kareden son kareye 4.883/4.883 kez gözlendi; örneklenmiş 327
yanıtın ilk tentative yanıtından sonraki 326'sı aynı hedefi confirmed ve observed
olarak taşıdı. Kapalı koşunun 327 örnek yanıtında hedef çevresinde confirmed olay
yoktu. Her iki koşuda USB/CRC/sıra/kuyruk hatası ve kırpılma sıfırdı. Bu bilinen
CW için kısa olumlu ayrım kanıtıdır; kör/tekrarlı RF doğruluğu veya ST-06 kapanışı
değildir. Yerel özet `build/acceptance/st06-gui-20260906/rf853-24db-board-comparison-01.json`.

## 853 MHz 24/24 dB gerçek kart gözlemi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: kullanıcı beyanlı açık vericiyle üç kazanç kaydı alındı.
Her ayarda 512 ardışık ham kare, sıfır USB taşması/kırpılma ve 512/512 yerel /
Python kanal seçici eşleşmesi var. İlk 16 kare dışlanınca 16/16 dB açık kaydında
ham USB merkez hücresi kayan noktalı eşik hesabını 474/496, kanal seçici çıkışı
14/496 kez aştı. 24/24 dB çıkışında 496/496, kapalıda 1/496; medyan açık eşik
marjı +11,06 dB. 32/32 dB kapalı merkezde de 76/496 aşım görüldüğünden daha yüksek
kazanç otomatik olarak tercih edilmedi. Bu hesaplar FPGA bit-tam tekrarı değildir.
Ardından 24/24 dB ile gerçek RX → kart → GUI koşusu 4.883 kareyi sıfır USB/CRC/
sıra/kuyruk hatası ve kırpılmayla bitirdi. İlk örnek tentative; kalan 326 örnek
yanıtta aynı 853 MHz olay kimliği confirmed ve observed idi. Son kart yanıtında
first_frame_id=0, last_seen_frame_id=4882, seen_count=4883: kart sayacı bu kısa
koşunun tüm karelerinde hedef gözlemi bildiriyor. GUI kısa koşu kontrolleri geçti.
Bu sonuç bilinen CW için kısa olumlu gözlemdir; genel Pd/Pfa, uzun süreli hız payı
ve ST-06 kabulü değildir. 24/24 dB eşleştirilmiş kapalı kart koşusu bekleniyor.
Üretim eşikleri değiştirilmedi; kazanç yalnız tanı koşusuna uygulandı.
Yerel raporlar: `build/acceptance/st06-gui-20260906/rf853-gain-comparison-01.json`
ve `build/acceptance/st06-gui-20260906/rf853-on-24db-target-01.json`.

## 853 MHz kapalı kazanç karşılaştırması — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında kullanıcı vericinin kapalı olduğunu bildirdi.
RX LNA/VGA 16/16, 24/24 ve 32/32 dB ayarlarının her birinde 512 ardışık ham
kare (yaklaşık 1,05 saniye) kaydedildi. Üç koşuda USB taşması ve giriş/çıkış
kırpılması sıfır; aynı ham verinin yerel ve Python kanal seçici çıktıları her
koşuda 512/512 bayt-tam eşleşti. Kanal seçici çıkışında sıfır olmayan bileşen
oranı sırasıyla %1,726 / %4,390 / %52,880 oldu. Bu artış kapalı ortamın sayısal
seviyesidir; hedef sinyal iyileşmesi, Pd/Pfa veya FPGA kabulü değildir.
Ham ve türetilmiş I/Q birlikte `build/acceptance/st06-gui-20260906/rf853-gain-off-01/`
içinde; kaynak/girdi özetleri `summary.json` içindedir. Yeniden üretim aracı
`build/acceptance/st06-gui-20260906/rf853_gain_capture.py` (yeni çıktı dizini gerektirir).
Bu tanıda kart gönderimi yapılmadı; üretim yapılandırması ve eşikler değişmedi.
Eşleştirilmiş verici açık kazanç karşılaştırması bekleniyor. ST-06 açık kalır.

## 853 MHz eşik incelemesi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, ST-06 kapsamında mevcut yakın anten kayıtları
çevrimdışı incelendi; üretim eşikleri ve kazançlar değiştirilmedi. Periyodik Hann,
kayan noktalı FFT ve kaynakla aynı OS-CFAR penceresi/rank/katsayısıyla açık kaydın
327 örnek karesinde merkez hücre güçlü eşiği 14 kez, kapalıda sıfır kez aştı.
Açık kayıtta medyan güçlü eşik marjı −4,49 dB; zayıf eşik aşımı güçlüler dahil
119/327 idi. Bu sayılar donanımın bit-tam tekrar sonucu veya Pd değildir.
Normal doğrulama 3 karede 2 gözlem, zayıf yol 32 karede 24 gözlem gerektirir;
15 kare aralıklı kayıtla bu ardışık pencereler yeniden kurulamaz.
Gerçek yanıtların iki merkez confirmed olayında saklanan eşik marjı +0,388 ve
+0,180 dB idi; ilki o karede gözlenmemiş geçmiş olaydır. İkinciyle aynı I/Q
karesinin kayan noktalı marjı +0,158 dB çıktı; tek karşılaştırma genel bit-tam
uyum kanıtı değildir. Açık I/Q bileşenlerinin %98,208'i sıfır, kalanları ±1'dir.
Bu düşük sayısal seviye ve eşik altı dağılım seyrek tespitle uyumludur; kaybın
RF girişinde mi kanal seçimi/yeniden nicemlemede mi oluştuğu bu çiftle ayrılmaz.
Periyodik Hann açık/kapalı merkez güç farkı +7,150 dB; bu değer SNR değildir.
Yerel yeniden üretim: `python build/acceptance/st06-gui-20260906/analyze_rf853_threshold.py`.
Girdi ve kaynak SHA-256 kayıtlı rapor: `build/acceptance/st06-gui-20260906/rf853-threshold-diagnosis-01.json`.
Sonraki tanı kısa, sabit konumlu RX kazanç karşılaştırması ve eşzamanlı ham USB /
kart girdisi kaydıdır; uzun GUI testi gerekmez. ST-06 kabulü açık kalır.

## 853 MHz yakın anten açık/kapalı tanısı — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: kullanıcı beyanlı 853 MHz CW, TX gain 0,
RX LNA/VGA 16/16 dB ile aynı yakın anten konumunda ayrı açık/kapalı 10 saniyelik
koşuların her biri 4.883 kareyi sıfır USB/CRC/sıra/kuyruk hatası ve kırpılmayla
bitirdi. 327 örneklenmiş I/Q karesinin ortalama merkez-hücre gücü açıkta kapalıya
göre 7,15 dB arttı. Örneklenmiş FPGA yanıtlarında tam 853 MHz hücresinde iki
confirmed gözlem (biri o karede observed değil), kapalıda hedef çevresinde sıfır
confirmed gözlem vardı. Bu seyrek bulgu kararlı tespit veya Pd/Pfa kabulü değildir.
Yakın anten mesafesi sayısal kaydedilmedi; kapatma/expiry gecikmesi ayrı oturumlar
nedeniyle ölçülmedi. Yerel ham paket `build/acceptance/st06-gui-20260906/rf853-near-comparison-01.zip`.
Önceki uzak açık/kapalı merkez farkı 0,46 dB idi; koşullar karıştırılmaz. Kanal
seçici 0/0 dB kapalı ham kaydında Python referansıyla 128/128 byte-tam eşleşti;
çok düşük girişin çıkışta sıfıra yuvarlanması tespit yokluğunu tek başına
algoritmaya atfetmeyi engeller. ST-06 ve kontrollü tekrarlı RF kabulü açık kalır.


## 853 MHz kapalı referansı — 6 Eylül 2026

Kullanıcı alıcıyı geçici olarak `…36877e47` ile değiştirdi; ED_RX yapılandırması
bu cihaza bağlandı. KTR-4.1 / KTR-4.1-OPS-B0 kapsamında 853 MHz, LNA/VGA 0/0 dB
ve verici kapalı operatör beyanıyla yaklaşık 30 saniyede 14.648 kare işlendi;
USB/CRC/sıra/kuyruk hatası, kırpılma, ham aday ve etkin olay sayısı sıfırdı.
İlk alım giriş kırpılmasıyla durdu; sonraki aynı ayarlı koşu geçti. Başlangıç
kırpılmasının nedeni kanıtlanmadı. Yerel ham kayıt ve örneklenmiş I/Q paketi:
`build/acceptance/st06-gui-20260906/rf853-off-bundle.zip` (yeni klonda bulunması
varsayılmaz). Bu kısa negatif gözlem ortam sessizliği veya Pd/Pfa kabulü değildir;
verici açık eşleştirilmiş ölçüm henüz yapılmadı. ST-06 açık kalır.


## GUI ve oturum yaşam döngüsü gözlemi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, PHASE-08 / ST-06 kapsamında yeni ham kayıtlar
`results/evidence/phase08/gui-rx-lifecycle-v1.json` ve ZIP içinde saklanır.
900 MHz ayarında tek 15 dakikalık koşu 439.453 kareyi sıfır USB/CRC/sıra/kuyruk
hatasıyla tamamladı. Operatörün doğruladığı son-saniye masaüstü geçişinde
3,53 saniyelik çizim aralığı oluştu; kesintisiz GUI kabulü değildir.
Önceki kısa GUI koşusundaki bir USB taşması ve 104,65 MHz giriş kırpılması
başarısız kayıt olarak korunur. İki dakikalık görünür kısa koşu geçti.

Aynı uygulamada 30 saniye sonra durdurma yaklaşık 124 ms sürdü; yeni oturum
nesli, kare ve RX/FPGA zaman bilgileri sıfırlandı. Yeniden başlatılan 90 saniyelik
koşu 43.945 kareyi sıfır USB/taşıma hatası ve kırpılmayla tamamladı.
Ancak p95 RX→görüntü yaşı 153,47 ms ile 150 ms hedefini aşmıştır; örneklenmiş
kuyruk değerleri 118/512 ve 64/64'tür, kesin tepe değildir. Etkin olay olmadığı
için eski olay kimliklerinin karışmaması fiziksel olarak sınanmış sayılmaz.
Operatör masaüstünden döndüğünü bildirdi, fakat Qt gizlenme geçişi kaydetmedi;
pencereye dönüş gecikmesi ölçülmüş gibi sunulmaz. İlk iptal edilen oturumun
son USB istatistiği yoktur. Pencere kapatılarak kesilen denemeler ayrı korunur.

Çalışan hizmet özeti seri konsoldan doğrulandı; bitstream/imaj özeti okunamadı.
Vericinin kapalı olması operatör beyanıdır. RF doğruluğu, soğuk açılış,
tekrarlı dayanıklılık ve ST-06 kapanışı açık kalır. Sıradaki hedef uzun testleri
körlemesine tekrarlamak değil, yeniden başlatmadaki gecikmeyi kısa ölçümlerle
ayrıştırmak ve olay içeren yaşam döngüsünü sınamaktır. Eski kanıtlar değiştirilmedi.


## Güncel kanıt sınırı — 6 Eylül 2026

PHASE-08 / ST-06 ve KTR-4.1 / KTR-4.1-OPS-B0 kabulü açıktır.
5 Eylül tarihli 439.453 karelik tek arayüzsüz RX koşusunda USB taşması ve
CRC/sıra/kuyruk hatası görülmedi. Ölçülen 488,2153 kare/s, nominal
488,28125 kare/s üzerinde bir hız payı kanıtlamaz. Önceki kaynakla yapılan
iki uzun koşu USB taşmasıyla başarısızdı. GUI sürekliliği, RF tespit doğruluğu
ve kalıcı sorunsuz çalışma bu koşuyla doğrulanmadı; soğuk açılış kabulü de açıktır.

Tarihsel `native-channelizer-v3` ve `st06-parallel-product-v1` kanıtları
özgün kaynak hash'leri ve arşivleriyle korunur. Yeni RX koşusu kendi kaydıdır;
eski fiziksel sonuçlar değiştirilmiş PC kaynağına aktarılmaz.
İnceleme: `results/evidence/phase08/rx-evidence-recovery-v1.json` ve ZIP.
Doğrulama: `python scripts/verify_phase08_evidence_recovery.py`.
Bu işlem yeni donanım ölçümü içermez. Güncel ayrıntılar sinyal tespiti durum
belgesindedir; aşağıdaki tarihli kayıtlar kendi sürümlerinin sonuçlarıdır.

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


5 Eylül 2026 son ST-06 optimizasyonu: ARM güç çözme ve durum yedekleme
maliyeti azaltıldı; eşikler, sekiz karelik pencere ve RTL değişmedi. PetaLinux
paketinden çıkan hizmetle üç fiziksel dijital koşu 464,87 / 460,37 / 463,74
kare/s verdi. Önceki 286–290 kare/s kaydı tarihsel karşılaştırmadır;
488,28125 kare/s kabul sınırı hâlâ geçilemedi. Beş test girdisinin kart
yanıtları önceki sürümle byte-tam eşleşti. Bu, RF doğruluk kabulü değildir.
Kanıt: `results/evidence/phase08/st06-product-optimization-v1.json` ve ZIP.
SD açılış dosyaları değişmedi; güncel hizmet geçici yüklüdür. ST-06 sürer.

Önceki kayıtlar ve mimari açıklamalar:

## Bilgisayar-1 — ED / Operatör

HackRF-1 yalnız RX kaynağıdır ve USB ile Bilgisayar-1'e bağlanır. Bilgisayar-1
bounded `ci8` I/Q frame'lerini CRC'li, sıralı Ethernet sözleşmesiyle ZedBoard PS'ye
gönderir. ST-06 ürün imajında PS DDR ve AXI DMA, PL Hann→4096 FFT→UQ28.30
güç→OS-CFAR hücre kararı zincirini besler. PL her karede 32768 bayt işaretli
güç döndürür. ARM hücreleri çözer, dar adayları gruplar, sekiz karelik geniş
bant kararını ve temporal yaşam döngüsünü yürütür. Dört yuvalı kuyrukta CPU0
DMA ve CPU1 detector işlerini örtüştürür. PySide6 arayüzü kart sonuçlarını ve
host görsel FFT'sini gösterir. Parametre/manuel DF işlevlerinin ayrı mevcut
kabul sınırları KTR izlenebilirlik belgesindedir; bu çalışma sinyal tespitidir.

5 Eylül 2026'da aynı routed XSA ile PetaLinux ürün imajı derlenmiştir.
[Entegrasyon kanıtı](../../results/evidence/phase08/st06-product-integration-v1.json)
paketleme ve host hizmet sınırını doğrular. Güncel imajın soğuk açılışı,
fiziksel ürün hizmeti ve kontrollü kör RF kabulü açıktır. Eski P0 seyrek
aday-paket mimarisinin kart sonuçları ST-06'ya devredilmez.

Aynı gün yapılan geçici FPGA/hizmet/köprü yüklemesinde dijital dar/geniş
yaşam döngüsü gözlenmiştir. Uçtan uca hız 286–290 kare/s olduğundan 2 MS/s
kesintisiz ürün kabulü başarısızdır. ARM tespit iş parçacığı bir çekirdeği
yaklaşık doldurur; alt adım maliyetleri henüz ölçülmemiştir. SD soğuk açılışı
değişmemiştir. Kanıt: `results/evidence/phase08/st06-product-board-diagnostic-v1.json`.

## Bilgisayar-2 — ED alıcı rolü

Bilgisayar-2 için ET veya TX sorumluluğu yoktur. İkinci HackRF yalnız
`ED_RX_SECONDARY` alıcı rolüyle envantere alınabilir. Eşzamanlı ikinci RX akışı
ve iki alıcının zaman/frekans hizası fiziksel kanıt tamamlanmadan çalışıyor
gösterilmez. Bilgisayarlar Python belleği veya süreç durumu paylaşmaz; ileride
ED görev verisi aktarılacaksa sürümlü ağ veya dosya sözleşmesi kullanılır.

## Anten ve DF

Seçilen frekansa uygun FOX-727, 800 MHz–6 GHz UWB veya HackRF bandıyla sınırlı
TEM yönlü anten operatörce elle döndürülür. Her ölçüm açı, seçili confirmed
hedef kanalının doğrusal toplamından elde edilen göreli dBFS, hedef frekansı,
kanal genişliği, alıcı ayar bağı, kaynak kare kimliği, UTC zaman ve güven taşır.
Güncel alan profili 15° adımlı 24 açılı tam tur, 3 dB ana/rakip tepe ve ön/arka
ayrımı ister. Ham maksimum zorunlu LOB sonucudur; P0 interpolasyon kullanmaz.
Alan profili şu anda host Python'dadır; portable C/ARM hizmet bağı açıktır.
Kalibre saha hatası ancak izinli ve bilinen yönlü testte dairesel derece RMS ile
ölçülebilir.
