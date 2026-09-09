# P0 Gerçek Sistem Mimarisi

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

## Bilgisayar-2 — ET

Bilgisayar-2, HackRF-2 rolünden ve ET kontrolünden sorumludur. P0 yazılım kabulü
`OFFLINE` ve `LOOPBACK` modlarında tamamlanmıştır. Kullanıcının 8 Eylül 2026
Faraday kabini beyanı ve onayıyla `CABLED_LAB` politika kilidi kaldırılmıştır;
genel/açık alan `HARDWARE_TX_LOCKED` yolu kapalıdır. Mevcut denetleyici laboratuvar
görevini ve günlüğünü kabul eder ancak gerçek TX backend'i uygulanmamıştır.
Fiziksel TX; tam cihaz serisi, doğrulanmış araçlar, sınırlı süre/kazanç, acil
durdurma ve bağımsız ölçüm birlikte geçtikten sonra bu mimariye eklenebilir.

İki bilgisayar Python belleği veya süreç durumu paylaşmaz. Gelecekte görev verisi
aktarılması gerekirse sürümlü ağ veya dosya sözleşmesi kullanılır.

## Anten ve DF

Seçilen frekansa uygun FOX-727, 800 MHz–6 GHz UWB veya HackRF bandıyla sınırlı
TEM yönlü anten operatörce elle döndürülür. Her ölçüm açı, göreli güç, frekans,
UTC zaman ve güven taşır. Ham maksimum zorunlu LOB sonucudur; P0 interpolasyon
kullanmaz. Kalibre saha hatası ancak izinli ve bilinen yönlü testte ölçülebilir.
