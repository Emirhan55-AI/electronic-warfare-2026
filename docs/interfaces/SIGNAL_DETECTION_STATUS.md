# Sinyal tespiti: güncel durum ve kabul sınırı

## KTR-4.2 koşullu taşıyıcı kestirimi — 18 Eylül 2026

P0PM-v5, seçili 16 özgün karenin ikinci/dördüncü kuvvet çizgisi ve dört zaman
grubu uzlaşmasıyla ARM'da ayrı koşullu taşıyıcı frekansı kestirir. Doğrudan
gözlenen çizgi veya merkez alanı değiştirilmez; PL FFT ve tespit eşikleri
aynıdır. Yeni hizmet/köprü çalışan karta hash bağlı geçici kuruldu. İki gerçek
kayıt fiziksel PL/ARM tekrarında yaklaşık 820 MHz taşıyıcı kestirimi verdi;
66 C/NumPy, altı normal kart parametre ve sekiz yön protokol sahnesi geçti.
Yeni canlı ölçüm referans uyuşmazlığında reddedildi; bu RF başarı sayılmaz.
Koşullu alan, yöntem/köken ve olumsuz sonuçlar
`docs/interfaces/CARRIER_RECOVERY_20260918.md` içindedir. Genel RF doğruluğu,
kalibrasyon, yeni canlı kestirim ve soğuk açılış kabulü açıktır; yeni faz yoktur.

## KTR-4.3 kesintisiz analog dinleme bağı — 18 Eylül 2026

Mevcut PHASE-08/ST-06 tespit bağı değiştirilmeden, doğrulanmış seçili kanalın ilk
beş saniyelik I/Q penceresinden sonra yalnız yeni ardışık kareleri PC dinleme
yoluna aktarılabilir hale getirildi. RX ve FPGA tespiti kesintisiz dinleme
sırasında çalışmayı sürdürür; kanal gözlem oranı, ardışık boşluk, sıra numarası
ve işleme yığılması kapıları kapanırsa ses fail-closed durur. Bu kaynak/sentetik
işlev doğrulamasıdır; yeni fiziksel tespit veya KTR-4.3 RF kabulü değildir.
PHASE-08/ST-06 kapıları değişmemiş ve açık kalmıştır. Ayrıntı
`docs/interfaces/SIGNAL_MONITORING_LISTENING_STATUS.md` içindedir.

## KTR-4.4 yön sonucu görünürlüğü — 18 Eylül 2026

Uyarlamalı yön taramasının son ARM isteğinde 64 bit uygulama kare kimliği ile
32 bit P0DF-v1 alanı arasındaki uyumsuzluk giderildi. Ölçümler başarısız son
hesapta korunur ve yalnız ARM kararı yeniden denenebilir. Ürün 0° eksenini ilk
ölçümdeki fiziksel anten yönü olarak gösterir; coğrafi referans yoksa kuzey/doğu
iddiası üretmez. Ham en güçlü açı adayı ile ARM doğrulanmış bağıl yön ayrı
sunulur. Fiziksel derece RMS kabulü değişmemiş ve açık kalmıştır. Ayrıntı
`docs/interfaces/SIGNAL_DIRECTION_FINDING_STATUS.md` içindedir.

## KTR-4.2 geniş bant OBW kararlılık düzeltmesi — 18 Eylül 2026

Ekran görüntüsündeki 820 MHz ölçümünün özgün 16 karelik kaydı yeniden oynatıldı.
Merkez `820,031321536 MHz` değerinde kararlıydı; eski mutlak yedi FFT-hücresi
kapısı, yaklaşık `684,420 kHz` genişliğe karşı yalnız `%2,54` olan
`35,618` hücrelik kenar değişimini yine de reddediyordu. Kök neden yayın yokluğu,
PL hesabı veya taşıma hatası değil; geniş bantla ölçeklenmeyen ARM kalite
kapısıdır. Uzun ölçümde sınır artık `maks(7 hücre, ölçülen OBW'nin %5'i)`dir.
Dört karelik tarihsel yol değişmedi.

Aynı kayıt taşınabilir C yolunda `819,658288599–820,342708950 MHz` kenarları ve
`684,420351 kHz` OBW ile geçerli sonuç verdi. On iki sentetik geniş bant sahnesi
geçmeye devam etti; değişen bant ve dört kademeli frekans sıçraması reddedildi.

Yeni ikili çalışan karta yüklenip hash ile doğrulandı. Fiziksel PL/ARM sayısal
kapısı altı sahneyi geçti; aynı özgün kayıt P0PM-v3 üzerinden `684,373127 kHz`
OBW verdi. Yeni gerçek HackRF → FPGA → ARM koşusunda güncel RF sinyali 16/16
kareyle `820,144998 MHz` merkez, `819,664402–820,339253 MHz` kenarlar,
`674,851 kHz` OBW ve `-41,92 dBFS` kanal gücü üretti. Çalışan servis özeti ve
kanıtlar `output/parameter-review-20260918/` altındadır. Soğuk açılış kalıcılığı,
genel RF doğruluğu ve dBm kalibrasyonu kabul edilmedi. Ana sonuçlarda
`Gözlenen Taşıyıcı Frekansı` yeniden gösterilir; dar
taşıyıcı çizgisi bulunmayan yayında sayı uydurulmaz. Sinyal türündeki görünür
`DENEYSEL TAHMİN` rozeti kaldırıldı ve değer ana sonuç rengine alındı; modelin
deneysel sınırı kayıt ve teknik ayrıntıda korunur. PHASE-08/ST-06 ve fiziksel
KTR-4.2 kabulü açıktır.

## KTR-4.4 yön akışı bağı — 16 Eylül 2026

Yön Bulma, doğrulanmış `0°` kanal kilidinden sonra sağ ve sol lob dışı sınırları
bulup tepe çevresini 5° adımlarla hassaslaştıran uyarlamalı akışa geçirilmiştir.
Bu değişiklik FPGA sinyal tespit eşiklerini veya PHASE-08 Pd/Pfa kapılarını
değiştirmez. Lob dışı açıdaki `target_observed=false`, yayın yokluğu veya verici
kimliği iddiası değil, yön planlayıcısının kilitli kanal ölçüm girdisidir.

## Yön bulmada eşik altı kanal ölçümü — 16 Eylül 2026

Yön bulma ilk 0° kanal doğrulamasından sonra her açıda yeniden `confirmed` olay
istemez. Kilitli kanalın dört yeni ardışık karesi, hedef yönlü anten deseninde
tespit eşiğinin altına inse de P0PM güç ölçümüne gider; yakın/taşan başka aday
retleri korunur. Yön ölçümüne özel P0PM-v4, gürültü çıkarılmış sinyal gücü yerine
kilitli kanalın sinyal + alıcı gürültüsü toplamını bütün açılarda aynı yöntemle
verir; derin sönümde bu değer gürültü tabanına yaklaşır. Tespit eşiği ve PL FFT
yolu değişmez, olaysız kare yayın kanıtı sayılmaz. Kaynak regresyonu geçti;
güncel kart hizmeti ve köprüsü doğrulanmış ZedBoard'a geçici kuruldu ve 47007
üzerinde fiziksel PL/ARM işlev testi geçti. SD imajı değişmediği için yeniden
başlatma kalıcılığı, canlı anten RF/RMS kabulü açık kalır. Ayrıntı
`docs/interfaces/SIGNAL_DIRECTION_FINDING_STATUS.md` içindedir.

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

## Kalibrasyonsuz tahmini güç sunumu — 16 Eylül 2026

Parametre sonucuna `Kanal Gücü (dBFS)` ile `Sinyal Türü` arasına `Tahmini Güç
(dBm)` satırı eklendi. Yalnız canlı HackRF bağlamında geçerli dBFS sonucu,
LNA/VGA, RF AMP, kanal seçici genlik ölçeği ve frekans kullanılır. Model,
HackRF One'ın belgelenmiş −5 dBm azami girişini kaba sıfır-kazanç/tam-ölçek
ankrajı kabul eder; yapılandırılmış nominal kazançları ve sayısal ölçeği çıkarır.
Sonuç `TAHMİNİ`, yaklaşık işareti ve en az ±15 dB belirsizlikle gösterilir.
RF AMP, bant uçları ve çok düşük tahminlerde belirsizlik artırılır.

Bu satır kalibrasyon profili, gerçek dBm ölçümü, verici çıkış gücü veya RF
doğruluk kabulü değildir. KTR-4.2'nin kalibre dBm kapısı açık kalır; mevcut dBFS
alanı ve ölçüm kaydı değiştirilmedi. PHASE-08/ST-06 sürer ve yeni faz açılmadı.

## Parametre aralığı uyarısının kaldırılması — 16 Eylül 2026

Parametre ekranındaki `Aralık seçili sinyalin tamamını kapsamıyor` uyarısı
ile `Aralığı Düzenle` eylemi ve buna bağlı elle alt/üst frekans alanları kullanıcı
kararıyla kaldırıldı. Ölçüm başlatıldığında güncel aday onaylı aralığın dışına
taşıyorsa mevcut canlı yol aralığı otomatik genişletmeye devam eder;
geçersiz veya kart sınırını aşan aralıklar yine reddedilir. DSP, RTL, ARM,
ölçüm kaydı ve KTR-4.2 kabul durumu değişmedi. PHASE-08/ST-06 açık kalır ve
yeni faz açılmadı.

## Sistem çalışma alanının kaldırılması — 16 Eylül 2026

Kullanıcı kararıyla ürün arayüzündeki `Sistem` görev girişi ve çalışma alanı
tamamen kaldırıldı. Buna bağlı `Ctrl+5` kısayolu, işlem zinciri denetçisi ve
olay günlüğü de kullanıcı yüzeyinden çıkarıldı. Tespit ekranındaki `Sistemi
Denetle` eylemi, HackRF ve FPGA hizmeti için gerekli bağlantı/kurtarma denetimi
olduğundan korunur. DSP, RTL, ARM, alım ve olay kayıt davranışı değişmedi;
PHASE-08/ST-06 açık kalır ve yeni faz açılmadı.

## Tarama bitişi, dinleme devri ve kararlı listeler — 16 Eylül 2026

Bant turunun ardından çalışan otomatik tekrar kontrolü artık tarama gibi
sunulmaz: işlem sırasında düğme `Son Kontrolü Durdur`, tüm iş bittiğinde
`Taramayı Başlat` gösterir. Tekrar kontrolü ve özgün kanıt kaydı korunur.

Parametre sonucundaki `Dinleme İçin Yeniden Al` her tıklamada Dinleme ekranına
geçer ve başarısız başlangıç nedenini orada gösterir. Başarılı devirde ölçülen
frekans yeni canlı oturumda yeniden aranırken otomatik iki-LO doğrulaması geçici
olarak bekletilir; böylece beş saniyelik ses tamponu başka bir doğrulama koşusu
tarafından kesilmez.

Sabit frekans tespit kartları ilk görülme sırasını ve ilk kullanıcı frekans
etiketini korur; her karede güç veya görülme durumuna göre yer değiştirmez.
Geçmiş ayırıcı satırı kaldırıldı ve tüm kartlar sabit yüksekliktedir. Bant
taraması kartları da tur sürerken ilk görülme sırasını ve sabit yüksekliği
korur; aile sınıflaması ile güç/fark sıralaması tur tamamlandığında bir kez
uygulanır. Ham tespit ve kanıt sıraları değişmez.

OBW `obw_temporal_instability` durumu algoritmik hata veya sıfır bant anlamına
gelmez. Dört ardışık ölçümde bulunan alt/üst bant sınırları kalite kapısının
izin verdiğinden fazla değişmiştir. Arayüz bunu `TEKRAR ÖLÇÜLMELİ` olarak ve
analiz aralığını sinyalin tamamını kapsayacak şekilde genişletme önerisiyle
gösterir. Eşik gevşetilmedi; doğrulanmamış genişlik sayıya çevrilmez.

## Dinleme sesi ve görünüm sadeleştirmesi — 16 Eylül 2026

KTR-4.3 Dinleme yolu gerçek I/Q'dan AM/NFM ses üretmeye devam eder. Analog
konuşma kanalı 2–25 kHz ile sınırlandı, parametreden gelen dinleme önerisi
6–25 kHz'e alındı ve örnek azaltma öncesine 257 tap konuşma filtresi eklendi.
NFM varsayılanı de-emphasis uygulamayan `Net ses`; 750 µs düzeltme yalnız
eşleşen telsiz profili için isteğe bağlıdır. Dinleme görünümü temel kanal
ayarları ile altı sonuç satırına indirildi; dalga biçimi ve sinyal kararlılığı
grafiği korunur. Sentetik regresyon yeni sınırları ve alias reddini doğrular.
Yeni kaynakla fiziksel konuşma anlaşılabilirliği tekrarlanmadı; PHASE-08/ST-06
ve KTR-4.3 kabulü açık kalır. Ayrıntı
`docs/interfaces/SIGNAL_MONITORING_LISTENING_STATUS.md` içindedir.

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

1 MHz–6 GHz canlı tarama başlatıldı; ilk kontrol noktası 366/2400 pencere,
1–916 MHz ve 82 ham gözlemdir. Tam tur sonucu henüz yoktur. İki kayıtta
120 mümkün kareyi aşan sayaç ve beş geniş adayda çok dar ikinci ayar eşleşmesi
görüldü; bunlar açık doğruluk incelemesidir. Ayrıntı ve kaynak sınırları
`output/rx-wideband-20260916/RAPOR.md` içindedir.

PHASE-08/ST-06 açık; bu kayıt yeni fiziksel kabul oluşturmaz.

## Kullanıcıya açık tarama bölümleri — 16 Eylül 2026

`RxSurveyView.qml`, `SİNYAL TESPİTİ` başlığı altında kayıtları üç sade bölüme
ayırır: `Tekrar doğrulanan adaylar`, `Tekrar ölçülmesi gerekenler` ve `Alıcı
etkisi olabilecekler`. Kayıt özeti, `Tarama geçmişi` ve grup düğmeleri arasındaki
açıklamalar gösterilmez; dikey alan sinyal satırlarına ayrılır. Satır mesajları
inceleme, yeniden ölçme veya yayın kabul etmeme eylemini söylemeye devam eder.
1500 MHz gibi doğrulanan bir aday özel kuralla öne alınmaz;
tekrar gözlemi güven bölümünü, ölçülen sinyal farkı bölüm içi sırayı belirler.
Bölümleme ham aday kayıtlarını
silmez. Aralığı ölçülen her kayıt `Tespit aralığı` satırını taşır; 1 kHz'den dar
çizgilerde kenarların aynı değere yuvarlanmaması için dört ondalık MHz gösterilir.
Aralık alanı yoksa kullanıcıya tahmini sınır gösterilmez.
Farklı alıcı ayarında yeniden görülme güven bölümünü belirler; bu ifade güçlü
sinyal demek değildir. Bölüm içindeki sıra, kalibre edilmiş mutlak güç yerine
ölçülen tepe/gürültü farkını kullanır. Zayıf ve farkı ölçülemeyen kayıtlar
listede kalır. Üç veya daha fazla farklı dar çizgi 40 MHz katlarına oturursa
sunum bunları `Alıcı etkisi olabilecekler` bölümüne ayırır; bu yalnız inceleme
önceliğidir ve fiziksel verici/parazit kabulü anlamına gelmez.

16 Eylül 2026 tarihli 1750–1950 MHz tamamlanmış turda altı ham gözlem dört
sunum satırında birleşti. 1800,000, 1880,000 ve 1919,999 MHz çizgileri dar ve
40 MHz düzenine uyumludur. 1863,029 MHz adayı yaklaşık 1,006 MHz genişlik ve
31,47 dB tepe/gürültü farkıyla ayrı kaldı. Bu kayıt kontrollü kaynak kimliği
kanıtı değildir; PHASE-08/ST-06 kabulü açık kalır.

## Parametre kataloğu ve kayıt eylemleri — 16 Eylül 2026

`ParameterMeasurementPanel.qml` içindeki `KAYITLAR` bölümü, canlı alım sırasında
tamamlanan dört karelik PL/ARM parametre sonuçlarının kalıcı SQLite kayıt
defteridir; seçili sinyalin `Parametre Çıkar` sonucu ayrı ölçüm kaydına yazılır.
Başlık altında yalnız kayıt sayısı ve işlemler kalır. Liste başlangıçta
kapalıdır; `Kayıtları Göster` ile açıldığında ilk sekiz kayıt gösterilir, CSV
dışa aktarma tüm kayıtları içerir. `Parametre
Çıkar` düğmesi mevcut analiz aralığını onaylayıp ölçümü başlatır. `Yenile`, `CSV
Dışa Aktar` ve `Klasörü Aç` sonuçlarını panelde bildirir ve aynı olayı salt
okunur operasyon günlüğüne ekler. Katalogda frekans, OBW, dBFS, SNR, alıcı ve
kalite durumu saklanır; dBm yalnız eşleşen geçerli kalibrasyon varsa yazılır.
Ana ölçüm sunumu `Taşıyıcı Frekans`, `Bant Genişliği` ve `Kanal Gücü (dBFS)`
alanlarıyla sınırlıdır; sinyal türü, OBW analiz aralığı açıklaması ve parametre
düğmesi altındaki canlı FPGA kare sayacı gösterilmez.

## Tespit sunumu ve 1766 MHz gözlemi — 16 Eylül 2026

Kaynak doğrulaması: gerçek QML grubunda 39; canlı görünüm modeli, sabit bant
doğrulama ve tarama sunumu grubunda 105 test geçti (toplam 144).

PHASE-08 / ST-06 açık kalır. Bant taraması eksen uçları artık görüntülenen
spektrumun gerçek merkezinden ve örnekleme hızının yarısından hesaplanır;
10 MS/s görüntüye sabit ±1 MHz etiketi verilmez. Sabit tespitte kaba adayın
belirmesiyle yanıp sönen özet kartı kaldırıldı. `Ek doğrulama sürüyor` satırı
yalnız gerçek doğrulayıcı ve aday birlikte varken görünür. Spektrumla destekli
tespit mavi `Tespit edildi`, iki alıcı ayarında doğrulanan aday yeşil
`Doğrulandı`, diğer adaylar sarı `Aday`, geçmiş kayıt gri `Artık alınmıyor`
olarak sunulur. Alt satır doğrulama sonucunu açıklar; karar algoritması değişmez.

Bu değişiklikten **önceki çalışan uygulamada** 1740–1780 MHz / 24-24 dB /
AMP kapalı kapalı–açık–kapalı koşuları 8,0487 / 8,8059 / 7,5234 saniyede,
her biri 16/16 pencereyle tamamlandı. 1766 MHz hedefi yalnız açık koşuda
listelendi, 120/120 gözlem karesinde görüldü ve farklı alıcı merkezinde tekrar
alındı. Ana koşuların taşıma ve sayısal kırpılma sayaçları sıfırdır. 1760 MHz
çizgisinin kaynağı belirlenmedi. Yerel kayıt paketi
`output/rx-ui-1766-20260916/` altındadır; `audit-comparison.json` özgün audit
kopyalarının hashlerini içerir. Çalışan süreç/kart imajı kaynak eşleşmesi bu
koşuda doğrulanmadığı için sonuç yeni kaynağın fiziksel kabulü değildir.

Açık koşudaki 1,1658 MHz aday aralığı ölçülmüş işgal bant genişliği değildir.
Son birincil kart olayının 475 hücresi, 10 MS/s ve 4096 FFT ile yaklaşık
1,1597 MHz kapsar: genişlik yalnız QML eksen hatasıyla açıklanamaz. Tarama,
kare içi yakın adayları gruplar ve sınırları kareler boyunca ortalar; bunun
payını ve analog/sayısal kök nedeni ayırmak için aynı ham I/Q gerekir.
Audit yalnız I/Q hashlerini içerir. Eşikler değiştirilmedi; aralık arayüzde
`Tespit aralığı` olarak adlandırıldı. dBm ve parametre fazına geçilmedi.

## Bağımsız GNU Radio RX bozulma gözlemi — 15 Eylül 2026

`digital_analog_detection/hackrf_rx_interference_monitor.grc`, kayıtlı
`ED_RX_PRIMARY …36877e47` cihazına seri numarasıyla bağlanan bağımsız bir RX
tanı akışıdır. 2 MS/s başlangıç hızında spektrum, spektrogram ve kompleks I/Q
zaman alanını birlikte gösterir; başlangıç merkezi 1900 MHz, LNA/VGA 16/16 dB,
AMP kapalıdır. Merkez frekansı ve kazançlar GUI üzerinden değiştirilebilir.
Akışta TX sink, sinyal üretimi, kayıt veya otomatik “karıştırıldı” kararı yoktur.

GNU Radio Companion 3.10.12 derleyicisi akışı hatasız üretti. HackRF firmware
`v2.4.0 (API 1.11)` olarak görüldü ve canlı gözlem penceresi yanıt verir durumda
açıldı. Aynı USB veri yolunda üç başka cihaz bulunduğu için yüksek hız uyarısı
korunarak 2 MS/s seçildi. Bu yalnız çalışma zamanı RX görünürlüğüdür; yayın
açık/kapalı karşılaştırması, bozulmanın kaynağı, Pd/Pfa veya ST-06 kabulü olarak
yorumlanmaz.

## Tespit ayarlarının görev odaklı sadeleştirilmesi — 15 Eylül 2026

Sabit frekans alıcı kartında LNA/VGA aynı satırda, AMP hemen altında doğrudan
seçimdir; bant taraması da AMP seçimini kendi alıcı satırında gösterir.
`Ayarlar` penceresinde yalnız tespit kararını değiştiren FPGA FFT,
normal CFAR ve zayıf CFAR alanları bırakıldı. NFM ses düzeltmesi Dinleme ekranına
taşındı ve yalnız NFM seçildiğinde `Kapalı` / `Mevcut profil · 750 µs` olarak
sunulur. Görüntü FFT'si, yenileme aralığı, elle dB ölçeği ve tepe-tut ürün
arayüzünden çıkarıldı; mevcut sabit/otomatik görüntü davranışı korunur.

Pencerenin sabit açıklama ve başlangıç önerisi satırları kaldırıldı; görünür
`FPGA FFT` etiketi `FFT` olarak kısaltıldı ve üç işlem düğmesi eşit genişlikte
hizalandı. Normal/zayıf CFAR katsayıları donanımsal LNA/VGA adımları gibi ayrık
seçimler değildir. Doğrulanmış tek başlangıç çifti yaklaşık 8,58/3,98 olduğundan
kanıtsız hassasiyet profilleri eklenmedi; sınırlı elle giriş, tam kart geri
okuması ve varsayılana dönüş korundu. AMP ayarlanabilir bir dB kademesi değil,
iki durumlu RF yükselteçtir; bu nedenle yanıltıcı `AMP (dB)` yerine sade `AMP`
etiketiyle ortalı seçim olarak gösterilir. Açık/kapalı durumu seçim kutusundadır.
Son sadeleştirme sonrasında gerçek QML, kart profili ve canlı görünüm modeli
grubunda 123 test geçti.

FFT/normal/zayıf alanları iki sütunlu tek forma alınarak etiket ve kutu
başlangıçları hizalandı. Katsayılar operatöre `8,58` / `3,98` biçiminde
gösterilir; alan değiştirilmedikçe karttan okunan tam Q32 karşılığı uygulama
isteğinde korunur. 4096'dan 8192/16384'e büyütme alım durmuşken `Uygula` ile
yapılır; büyük FFT'den küçüğe dönüş uygulamayı kapatıp açmakla değil kontrollü
kart yeniden başlatmasıyla yapılır.

Bant taraması alıcı satırında görünür etiketler `LNA (dB)`, `VGA (dB)` ve
`AMP` olarak sadeleştirildi. Tarama ayarlarından sabit açıklama ve hesaplanmış
`10 MS/s yakalama` satırı çıkarıldı; gerçek tespit davranışını değiştiren
`Gözlem (kare)` ile `Yerleşme (kare)` seçimleri ve varsayılana dönüş korundu.
Gözlem seçimi pencere başına değerlendirilen kare sayısını, yerleşme seçimi ise
frekans değişiminden sonra tespit dışı bırakılan başlangıç karelerini belirler.

`Parametre Çıkarımına Git` akışı, tarama adayını doğrudan ölçüm sonucu saymaz.
Seçilen frekansı parametre ölçümüne hazırlamak için 8 MS/s sabit alımda yeniden
doğrular; bu nedenle üst hızın 10 MS/s'den 8 MS/s'ye geçmesi tarama profilinin
değiştiği anlamına gelmez. Önceki akış yeniden alımı başlatabildiği halde bant
taraması görünümünde kalabiliyordu. Görünüm artık yeniden alımdan önce sabit
frekansa geçer, başlatma reddedilirse korunmuş taramaya döner ve bekleme durumunu
açıkça bildirir. Eşleşen canlı tespit ölçüme hazır olduğunda Parametre sekmesi
otomatik açılır. Tarama/örnekleme algoritması değişmemiştir.

Alım, FPGA profil geri okuması, CFAR sınırları ve AMP'nin bütün RX yollarına
taşınması değişmedi. Yeni RF hassasiyet profili, algoritma veya donanım kabulü
eklenmedi. QML/görünüm modeli/spektrum/ürün sınırı grubunda 136; tespit
ayarları/dinleme/tarama/HackRF grubunda 61 test geçti (ayrı süreçlerde toplam
197). Bu kaynak doğrulamasıdır; yeni fiziksel RX yapılmadı ve PHASE-08/ST-06
açık kalır.

`Karttan Oku`, FPGA'da o anda etkin olan FFT ve iki CFAR katsayısını gösterir;
16384 ve varsayılan yaklaşık 8,58/3,98 değerlerinin görünmesi bu nedenle tek
başına hata değildir. Çalışma sırasında büyük FFT'den 4096'ya küçültme güvenle
reddedilir. Arayüz 4096 için kontrollü kart yeniden başlatmasını ister ve bunun
tam güç kesmeli ST-06 cold-start kabul koşusu olmadığını açıkça ayırır.

4096'dan 8192 FFT'ye geçişte gözlenen `long_capture` hatasının kök nedeni
bulundu. FPGA 8192 iken ham 8 MS/s önizleme 32.768 kompleks örnek taşıyor,
görüntü ve kaba aday yolu ise sabit 16.384 kompleks örnek bekliyordu. Canlı yol
artık büyük FFT önizlemesinin ilk 16.384 gerçek ve bitişik örneğini görüntüleme
penceresine verir; sıfır doldurma yapılmaz ve FPGA'nın tam kare tespit işlemi
değişmez. 8192 ve 16384 profilleri için kaynak regresyonu bu sınırı doğrular.
Eski kullanıcı mesajındaki “FPGA FFT ayarı değildir” yargısı kaldırıldı.

Kart profili 15 Eylül'deki 8192 denemesi sırasında güncel ürün adresi
`192.168.7.2:47007` üzerinden kuşak 4, FFT 8192 ve normal/zayıf katsayıları
8,580143040744588/3,9810717054642737 olarak bulundu. Arayüzde 4096 seçmek büyük
FFT'den küçüğe çalışma zamanı geçişini uygulamaz; kontrollü kart yeniden
başlatması gerekir. Uygulama yeniden başlatması yalnız yeni masaüstü kaynağını
yükler, kartın etkin FFT profilini küçültmez. Düzeltme kaynak testlerinden
geçmiştir; güncel kaynakla fiziksel 8192 RX tekrarı henüz yapılmadığından
PHASE-08/ST-06 kabulü açık kalır.

Kontrollü kart yeniden başlatmasından sonra kartın kuşak 1 / FFT 4096'a
döndüğü fiziksel geri okumayla doğrulandı. Açık kalan masaüstü uygulaması önceki
8192 profilini bellekte tutarsa, elle 4096 seçimi eski ön denetimde küçültme
isteği sanılıp reddediliyor ve kutu yeniden 8192'ye dönüyordu. `Uygula` artık bu
durumda önce kartın güncel profilini okur; kart zaten 4096 ise güncel kuşakla
tek işlemde devam eder, kart gerçekten büyük FFT'deyse güvenli yeniden başlatma
uyarısını korur. Kartın geçerli ABI-v4 hata yanıtı da başlık hatası olarak
sunulmaz: fiziksel tanıda 8192 örnek/4096 kart eşleşmezliği `status=2`, sıfır DMA
bayrağı; 4096 örnek ise `status=0`, DMA bayrağı 7 döndürmüştür. Bu sınırlı tanı
genel fiziksel kabul değildir.

Tespit kartındaki sayısal `P/N` değeri kalibre edilmiş dBm değildir; tepenin
yerel gürültüye göre bağıl oranıdır. “FPGA gözlemi” de olayın kaç kez
gözlendiğini belirten süreklilik kanıtıdır. Bunlar tespit/ranklama içinde
korunur fakat parametre çıkarımı sonucu gibi yorumlanmaması için sinyal ve bant
taraması üzerine-gelme metinlerinden kaldırılmıştır. Mutlak dBm ancak eşleşen,
süresi geçmemiş kalibrasyonla parametre ölçümünde sunulur.

## Alıcı ve dinleme ayarlarının tamamlanması — 15 Eylül 2026

Alanların üzerinde bekleyince Türkçe kısa yardım gösterilir; ayrıntılı
başlangıç/değişim tablosu `DETECTION_TUNING_AND_SOURCE_GUIDE.md` içindedir.
İlgili arayüz testi grubu 37, alım/ayar/protokol grubu 125,
DSP/katalog/tarama/doğrulama grubu 75 ve operatör alım/dinleme grubu 12 test
geçti (ayrı süreçlerde toplam 249). Bu yazılım doğrulamasıdır; yeni fiziksel
RX veya TX testi yapılmadı. Genel depo sözleşme kapısı dosya-listesi
uyumsuzlukları (çıktı/kanıt dosyaları dahil) ve faz kayıt sayısı nedeniyle
açıktır; bu çalışma o kapıyı başarılı olarak raporlamaz.

LNA/VGA konumları korunarak AMP hemen altlarına doğrudan seçim olarak eklendi;
NFM ses düzeltmesi Dinleme görevine ayrıldı. AMP varsayılan kapalıdır;
LiveEDConfiguration, SurveyConfig, sabit iki-LO ve tarama aday doğrulamalarında
aynı seçim korunur. Oturum sürerken değişmez. AMP değişikliği eski hedef ve
ölçüm bağlamını temizler. Kalibrasyon eşlemesi AMP durumuna da bağlıdır; eski
alanı olmayan profiller yalnız AMP kapalı kabul edilir. Manuel ölçüm RX
yapılandırması ve otomatik katalog ayrıntıları AMP durumunu kaydeder.

CFAR normal `[1,16)`, zayıf `[1,4)` ve zayıf ≤ normal sınırları korunur;
değerler sade FPGA tespit penceresinde karttan okunur, düzenlenir, uygulanır
veya varsayılana döndürülür. Bunlar RF ortamına göre kalibre edilmiş yeni
hassasiyet profilleri değildir. Tespit FFT'sinde 4096 parametre uyumu ve
küçültmede yeniden başlatma uyarıları görünürdür. Dinleme AM/NFM genişlik
başlangıç seçimleri, ±100 Hz ve NFM için kapalı/750 µs ses düzeltmesi sunar.
İç 0–2000 µs sözleşmesi korunur. Kısa önizleme aynı de-emphasis ayarını uygular;
bu sayısal değişiklik önceki fiziksel ses kanıtına aktarılmaz.

Güncel 10 MS/s tarama süresi sunumu `4096/Fs` ile düzeltilmiş, geniş bant
menüsü 256 kare sınırına uydurulmuştur. Analog filtre alıcı aracının
varsayılanında kalır. Bias-T, WFM, susturma, PPM ve fiziksel olarak doğrulanmamış
filtre/CFAR hazır profilleri etkinleştirilmedi. Yeni fiziksel alım yapılmadı;
gerçek GUI+RX, AMP açık/kapalı ve ses karşılaştırmaları kabul için açıktır.
PHASE-08/ST-06 kapanmadı; yeni faz açılmadı.

## Örnekleme hızı sunumu ve hız değerlendirmesi — 15 Eylül 2026

Üst bilgi artık yalnız `ÖRNEKLEME HIZI` ve fiziksel alıcıya verilen örnekleme
ayarını gösterir: sabit izleme 8 MS/s, geniş bant taraması 10 MS/s. Sabit
izlemenin 2 MS/s işleme alt bandı değişmedi; `sampleRateHz` hesap/ölçüm bağlamında
işleme hızını korur. Görüntü hızı veya alıcı ayarı sürekli işleme kapasitesi
olarak yorumlanmaz. Veri yoksa `—`, kayıt açılmışsa kaydın örnekleme hızı görünür.

Kaynak ve geçmiş kanıt incelemesi: 10 MS/s / 4096 örnek sürekli işleme için
2441,40625 kare/s gerekir; 14 Eylül kısa kart burst gözlemi 498,744–505,719
kare/s idi. Bu nedenle mevcut burst sürekli 10 MS/s kabulü değildir.
`wideband-qml-live-scan-20260914.jsonl` başlangıcı **128 kare/pencere** kaydeder:
16 pencerede ana aşama toplam 5,608 s, ek doğrulama 1,608 s, ana RF gözlem
süresi 0,839 s. Önceki metinlerde bu 8 saniyelik QML koşusuna yazılmış 256
kare ifadesi yanlıştı; ham kanıt korunarak açıklama düzeltildi. Ayrı 256 karelik
12,33 saniye koşusu kendi kapsamındadır. Tüm 1 MHz–6 GHz turunun 45 dakika
sürdüğü bu incelemede doğrulanmadı. Mimari seçenekler ve sınırlar
`docs/architecture/P0_SYSTEM_ARCHITECTURE.md` başındadır; yeni fiziksel ölçüm
veya hız artışı uygulanmadı.

## Sağlık denetiminde sabit eylem görünümü — 15 Eylül 2026

Periyodik HackRF sağlık denetiminin kısa çalışma aralığı artık `Taramayı Başlat`
ve `Bant Taraması` eylemlerinin etkin görünümünü değiştirmez. Denetimle aynı ana
denk gelen tarama isteği kaybedilmez; denetim sonuçlanınca yalnız alıcı hâlâ
hazırsa başlatılır. 81 görünüm-modeli testi ile iki odaklı gerçek QML testi
geçti. Bu kaynak/QML doğrulamasıdır; fiziksel kullanıcı tıklama tekrarı değildir.

## Alıcı USB durumunun canlı izlenmesi — 15 Eylül 2026

Birleşik sistem hazırken etkin HackRF seri kimliği boşta yaklaşık 1,5 saniyede
bir arka planda yeniden denetlenir. Etkin alıcı USB alıcı modundan çıkarsa hazır
durumu iptal edilir, tarama eylemi kapanır ve `Sistemi Denetle` yeniden görünür.
Tarama başlangıcındaki `binary_pipe_failed` da teknik kod olarak gösterilmez;
`Alıcı bağlantısı koptu` başlığı ve yeniden denetleme yönlendirmesi kullanılır.
Yanlış bir tanı çalışması tek başına bağlantı kaybı sayılmaz. 79 görünüm-modeli
ve 34 gerçek QML regresyonu geçti. Bu kaynak/QML kanıtıdır; fiziksel tak-çıkar ve
PortaPack mod değişimi güncel kaynakla henüz tekrarlanmadı.

## Sistem denetiminde PortaPack USB geçişi — 15 Eylül 2026

Kayıtlı alıcı seçimi artık sabit COM veya yalnız birincil seri varsayımına bağlı
değildir. `ED_RX_PRIMARY …36877e47` görünürse önceliklidir; görünmüyor ve
`ED_RX_SECONDARY …35138247` görünüyorsa ikincil güvenli yedek olarak seçilir.
Etkin seri sabit frekans, 10 MS/s bant taraması, aday doğrulama, dinleme ve yön
ölçümü yollarının tamamına verilir; alıcıya özgü bilinen-spur profili de yeniden
yüklenir. İki alıcı birlikteyse birincil etkin, ikincil hazır yedektir.
Yapılandırılmamış HackRF kabul edilmez. 76 görünüm-modeli, 33 gerçek QML ve yedi
HackRF arka uç regresyonu geçti. İkincil cihazla güncel fiziksel fallback koşusu
henüz yapılmadı; PHASE-08/ST-06 açık kalır.

`Sistemi Denetle`, HackRF zaten USB alıcı modunda değilse FPGA hizmeti hazır
olduktan sonra PortaPack Mayhem'in USB-seri arayüzünü kesin `VID/PID` kimliğiyle
arar. Tam olarak bir eşleşme varsa `hackrf` komutunu gönderir, aygıtın HackRF
olarak yeniden bağlanmasını bekler ve yapılandırılmış `ED_RX_PRIMARY` seri
numarasını yeniden doğrular. FPGA hazır değilken, araç zinciri eksikken, denetim
portu yokken veya birden çok eşleşme varken mod değiştirilmez. Genel COM portu
tahmin edilmez. İlk fiziksel denemede seri yazma tamamlandıktan hemen sonra port
kapatıldığı için cihaz yeniden bağlanmadı. Mayhem'in Windows geçiş yordamındaki
500 ms komut tüketme aralığı ve port temizleme eklendi. Ardından
`COM4 / 1D50:6018` aygıtı tek fiziksel koşuda `HackRF One / 1D50:6089` olarak
yeniden bağlandı; `hackrf_info` yapılandırılmış `…36877e47` seri numarasını ve
`v2.4.0 (API 1.11)` firmware'i doğruladı. Yedi odaklı regresyon geçti. Kanıt
[`portapack-usb-handoff-20260915.json`](../../results/evidence/phase08/portapack-usb-handoff-20260915.json)
içindedir. Bu tek geçiş tekrarlı açılış/geçiş veya gerçek QML düğmesi kabulü
değildir; PHASE-08/ST-06 açık kalır.

Üst durum alanındaki canlı zincir bilgisi `ALICI → FPGA` ve
`8 MS/s → 2 MS/s` olarak sadeleştirildi. Bu yalnız mevcut 8 MS/s HackRF alımı
ile 2 MS/s FPGA işleme hızını açıklar; örnekleme ayarını veya DSP'yi değiştirmez.

## Uzun koşuda FPGA tespit kapasitesi — 15 Eylül 2026

Kullanıcının uzun sabit-frekans koşusunda gördüğü `candidate_drop`, HackRF veya
FPGA bağlantısının kesildiğini değil, FPGA/ARM tespit zincirinin bir karede
izleyebileceğinden fazla aday oluştuğunu bildirir. Temporal zincir aynı anda en
fazla 64 etkin olay tutar; protokoldeki `dropped_candidates` ayrıca aday
birleştirme kapasitesinde dışarıda kalan dar adayları da aynı toplamda taşır.
Bu nedenle önceki kısa mesaj alt kapasiteyi tek başına ayırmıyordu.

Canlı hata ayrıntısı artık kare numarası, ham aday, etkin olay ve izlemeye
alınamayan aday sayılarını gösterir. `candidate_drop` birleşik donanım
hazırlığını iptal etmez; bağlantılar hazır kalır ve operatör LNA/VGA'yı azaltıp
yeniden başlayabilir. Oturum ise eksik tespiti başarılı/kesintisiz sonuç gibi
sunmamak için fail-closed durmaya devam eder. Sentetik kaynak ve gerçek QML
sınır testleri geçmiştir; bu değişiklik fiziksel uzun-koşu kabulü değildir.
PHASE-08/ST-06 açık kalır.

## Sabit frekans spektrum başlangıcı — 15 Eylül 2026

Canlı sabit frekans oturumu başlarken görünümün FPGA tespit alt bandına
otomatik daraltılması kaldırıldı. `Taramayı Başlat`, görünüm geçmişini temizler
ve spektrumu tam alım genişliğinde açar. Tespit alt bandı grafik kılavuzu ve
işleme sınırı olarak korunur; yalnız görünüm ölçeğini zorlamaz. Gerçek QML
regresyonu önceden daraltılmış görünümün başlatmada `0..1` tam genişliğe
döndüğünü doğrular. DSP, alım ayarları ve PHASE-08/ST-06 kabul durumu
değişmemiştir.

## Eksik canlı akış tanılarının ayrılması — 15 Eylül 2026

Canlı alımın beklenen kare sayısından önce kapanması daha önce bütün katmanlarda
`short_stream` olarak taşınıyor, arayüz de bunu kesin USB kesintisi gibi
sunuyordu. Ham HackRF verisinin eksik kalması, PC alım/kanal-seçici zincirinin
erken bitmesi ve FPGA yanıt sayısının eksik kalması artık ayrı kod ve mesajlara
sahiptir. Ham alım mesajı fiziksel kablo kopması iddia etmez. EOF yolunda
alınan/beklenen kare sayısı, süreç dönüş kodu ve son `hackrf_transfer` tanısı
korunur. Eksik oturum otomatik tekrarla başarıya çevrilmez. Bu oturumdaki
`hackrf_info` denetimi alıcıyı erişilebilir buldu ancak aynı USB veri yolunda üç
başka cihaz için yüksek hız uyarısı verdi; bu olası bir yoğunluk göstergesidir,
kök neden kanıtı değildir. Fiziksel tekrar yapılmadı; PHASE-08/ST-06 açık kalır.

## Sabit frekans başlat/durdur yerleşimi — 15 Eylül 2026

Sabit frekans görünümündeki başlatma ve durdurma eylemleri daha önce ayarlar
düğmesinin iki yanında ayrı yerleşim öğeleriydi; canlı oturum başladığında
`Taramayı Durdur` bu nedenle aşağı kayıyordu. İki eylem artık aynı sabit
yükseklikteki yuvada birbirinin yerini alır. Gerçek QML regresyonu eylem
yuvasının ve `Ayarlar` düğmesinin düşey konumlarının durum
geçişinde değişmediğini doğrular. Alım, DSP ve kabul durumu değişmemiştir;
PHASE-08/ST-06 açık kalır.

## Başlangıç kırpılmasının sürekli kırpılmadan ayrılması — 15 Eylül 2026

İlk başlatmada `iq_saturation`, aynı 16/16 dB ayarıyla ikinci başlatmada temiz
alım gözlemi yazılımda yeniden incelendi. Canlı oturum daha önce ilk ham karedeki
tek bir tam ölçek bileşenini bile sürekli koşu kırpılması gibi reddediyordu;
başlangıç yerleşmesi ile ölçüm bölümü ayrılmamıştı. Ürün yolları artık ilk sekiz
ham kareyi tuner/kanal-seçici yerleşmesine ayırır, FPGA'ya göndermez ve mantıksal
kareleri sıfırdan yeniden numaralandırır. Bu bölümdeki giriş/çıkış kırpılmaları
ayrı tanı sayaçlarında korunur. Yerleşme sonrasındaki herhangi bir kırpılma
`iq_saturation` ile koşuyu durdurur; koruma veya operatör kazanç seçimi
gevşetilmemiştir. 30 dakikalık sunulan kare sınırı değişmez; iç alım payı da
kesin sınırlıdır. Sentetik regresyon geçmiştir, güncel fiziksel HackRF tekrarı
henüz yapılmadığından donanım kabul iddiası yoktur. PHASE-08/ST-06 açık kalır.

## Sistem denetimi arayüz metni — 15 Eylül 2026

Sabit frekans ve bant taraması görünümlerindeki ortak donanım denetimi
`Sistemi Denetle` olarak adlandırıldı. HackRF ve FPGA birlikte bulunamadığında
başlık ve açıklama `FPGA ve Alıcı algılanamadı` mesajını verir. Tekil alıcı ve
FPGA hata ayrımları korunur. I/Q kırpılma koruması değişmedi; otomatik kazanç
uygulamadan koşuyu güvenli hata ile durdurur. PHASE-08/ST-06 açık kalır.

## Otomatik kazancın kaldırılması — 15 Eylül 2026

Kullanıcı kararıyla sabit frekans görünümündeki `Kazancı otomatik ayarla`
seçeneği ve ona bağlı sınırlı yeniden-deneme mantığı kaldırıldı. Canlı alım
artık yalnız operatörün seçtiği LNA/VGA değerleriyle başlar; düşük seviye,
kırpılma veya geniş aday sonucunda yazılım kazancı değiştirmez. I/Q kırpılma
koruması güvenlik ve veri bütünlüğü sınırı olarak korunur ve koşuyu hata ile
durdurur. Aşağıdaki 14 Eylül otomatik kazanç ölçümleri geçmiş kanıttır; güncel
kaynak yeteneğine aktarılmaz. PHASE-08/ST-06 açık kalır.

## Alıcı kazancı açılır listesi — 15 Eylül 2026

Sabit frekans görünümündeki uzun VGA listesi pencere yüksekliğini aşarak
22 dB'den sonraki seçenekleri erişilemez bırakıyordu. Ortak açılır liste 280
piksel yüksekliğinde kaydırılabilir görünümle sınırlandı; açılışta güncel seçim
görünür konuma taşınır ve 0–62 dB seçeneklerinin tamamına erişilir. Gerçek QML
regresyonu 62 dB seçimini, sınırlı görünümü ve aşağı kaydırılmış liste konumunu
doğrular. Bu yalnız arayüz erişim düzeltmesidir; kazanç aralığını, DSP'yi veya
fiziksel kabul durumunu değiştirmez. PHASE-08/ST-06 açık kalır.

## Sabit frekans arayüzü ve canlı parametre kararlılığı — 14 Eylül 2026

Sabit frekans görünümündeki donmanın üç yazılım nedeni giderildi. Kısa Qt
işçileri tamamlanma sinyali GUI kuyruğunda tüketilene kadar canlı tutulur;
parametre kataloğu tek tek `synchronous=FULL` işlemler yerine toplu işlem
kullanır; aynı bağlamdaki sonuçlar 500 ms teslim penceresinde birleştirilir ve
yazma/yeniden okuma ayrı tek işçili havuzda yürür. Ölçüme hiç
alınmadan sonlanan kısa ömürlü kart olayları artık sonuç/katalog satırı üretmez;
sayısal `automatic_parameter_expired_before_measurement` tanısı olarak kalır.
64 satırlık katalog yazımı aynı bilgisayarda `1,393 s` değerinden `0,0407 s`
değerine indi; bu mikro ölçüm RF veya sürekli çalışma kabulü değildir.

Gerçek QML + `…36877e47` RX + ZedBoard yolunda, kullanıcı tarafından açık
bırakılmış 820 MHz NFM kaynakla 16/14 dB ve 4.096 karelik tekrar 4.096/4.096
kare, sıfır USB taşması ve sıfır süreç hatasıyla tamamlandı. 20 ms GUI heartbeat
ölçümünde p95 `25,37 ms`, en büyük aralık `43,38 ms`, `100 ms` üstü aralık
`0` oldu. Kart yanıt hızı `460,412 kare/s` olduğundan `488,28125 kare/s`
sürekli gerçek-zaman kabulü hâlâ geçilmedi; sonlu koşunun sıfır taşması bu açığı
kapatmaz. Tespit, tepeyi `820,046875 MHz` ve birleşik desteği yaklaşık
`819,453613–820,514160 MHz` aralığında kararlı/RX-destekli gösterdi. Bu geniş
birleşik olay, 512 hücrelik canlı inline parametre sınırını aştığı için değer
uydurulmadan reddedildi.

Ürün varsayılanındaki otomatik kazanç, kırpma sayacı oluşmasa da 512 hücreyi
aşan güçlü adayı alıcı-seviyesi belirtisi sayar. Aralığı kesmek yerine önce
16/14 → 8/6 → 0/0 dB ile yeniden dener; düşük seviyede LNA ve VGA'yı birlikte
sıçratmak yerine yalnız VGA'yı 4 dB artırır. Nihai otomatik fiziksel koşu
16/14 dB'den 0/0 dB'ye iki güvenli tekrar yaptı; 4.096/4.096 kare ve sıfır USB
taşmasıyla tamamlandı. GUI heartbeat p95/en büyük `26,71/48,68 ms`, 100 ms üstü
aralık `0`; 19 katalog sonucunun 9'u geçerliydi. Geçerli merkez
`819,996190–820,002468 MHz`, OBW `101,05–102,91 kHz`, güç
`−58,48…−55,77 dBFS`, SNR `3,51–5,00 dB` aralığındaydı. Bu koşudaki kart yanıt
hızı `444,933 kare/s` olduğundan sürekli gerçek-zaman kapısı açık kalır.

Aynı açık kaynakta 0/0 dB ve 2.048 karelik tanı sıfır USB taşmasıyla tamamlandı;
GUI p95/en büyük heartbeat `27,42/39,99 ms` oldu. Kartın 21 ölçümünden 10'u
geçerliydi: merkez `819,997411–820,002380 MHz`, OBW
`100,76–103,32 kHz`, güç `−59,57…−55,81 dBFS`, SNR `3,15–4,74 dB`.
Kaynak ayarı 1 kHz ton ve 50 kHz azami sapmadır; sonuç bunun tek kontrollü açık
koşudaki gözlemidir, genel doğruluk/Pd/Pfa veya kalibre dBm kabulü değildir.
Geniş gerçek emisyonlarda 512 hücreye otomatik kırpma yapılmaz; operatör onaylı
8–3984 hücre P0PM-v2 yolu korunur. Tekrarlanabilir koşu ve kaynak özetleri
[`fixed-frequency-stability-20260914-before.json`](../../results/evidence/phase08/fixed-frequency-stability-20260914-before.json),
[`fixed-frequency-stability-20260914-after.json`](../../results/evidence/phase08/fixed-frequency-stability-20260914-after.json),
[`fixed-frequency-stability-20260914-gain-zero.json`](../../results/evidence/phase08/fixed-frequency-stability-20260914-gain-zero.json),
[`fixed-frequency-stability-20260914-managed-batched.json`](../../results/evidence/phase08/fixed-frequency-stability-20260914-managed-batched.json)
ve `scripts/verify_fixed_frequency_gui_stability.py` içindedir. PHASE-08/ST-06
açık kalır; sonraki faza geçilmedi.

## Tarama arayüzü sadeleştirmesi ve kararlılık — 14 Eylül 2026

Alıcı ayarlarında iki cihazın seri numarası ve durumunu gösteren envanter bloğu
kaldırıldı. Tarama ekranındaki örnekleme zinciri, profil ve pencere süre dökümü
metinleri de kaldırıldı. Donanım denetimi başarısız olduğunda kullanıcıya yalnız
`Alıcı algılanmadı` ve/veya `FPGA algılanmadı` gösterilir; ayrıntılı hata kodu
yerel olay günlüğünde korunur.

Güncel QML ile gerçek HackRF→FPGA taraması 800–840 MHz aralığında 16/16
pencereyi `8,00 s` içinde sıfır taşıma hatasıyla tamamladı. Ayrı kararlılık
koşusunda devam eden tarama arayüzden durduruldu, durum `Durduruldu` oldu;
800–805 MHz taraması yeniden başlatılıp 2/2 pencere ve sıfır hatayla tamamlandı.
En büyük 20 ms heartbeat aralığı `88,38 ms`, uygulama kapanışı `1,7 ms` oldu;
donma veya çökme gözlenmedi. Kanıt
[`ui-simplification-stability-20260914.json`](../../results/evidence/phase08/ui-simplification-stability-20260914.json)
içindedir. Bu kısa koşu uzun süreli GUI dayanıklılık kabulünün yerine geçmez.

## Kontrollü kör RF ve ürün yolu — 14 Eylül 2026

Fiziksel olarak bağlı `…36877e47` HackRF, `ED_RX_PRIMARY` rolüne alındı;
`…35138247` ikincil rolde korunur. Yayın açıkken 800–840 MHz aralığındaki iki
64-kare kör tekrar 16/16 pencereyi `5,06/4,96 s` içinde tamamladı. Her koşuda
800,000 MHz dar taşıyıcı ile 820 MHz çevresindeki yaklaşık 1 MHz geniş yayın,
ilk 10 MS/s taramadan sonra bağımsız 2 MS/s yeniden ayarlamada doğrulandı.
USB overrun, taşıma CRC, sıra ve kuyruk hataları iki koşuda da sıfırdı. Ham
kayıtlar `wideband-burst-live-rf-run1-20260914.jsonl` ve
`wideband-burst-live-rf-run2-20260914.jsonl` ile aynı adlı JSON özetlerindedir.

İki RF hedefi alıcı merkezine göre `±1 MHz` ve `±3,25 MHz` noktalarına kondu.
Sekiz yerleşimin 8/8'i en az sekiz confirmed gözlem karesine ulaştı; toplam
taşıma hata sayaçları sıfır kaldı. Bu analog HackRF geçiş bandı ve mutlak
frekans eşlemesinin pozitif kontrollü gözlemidir. Ayrıntı
[`wideband-burst-rf-placement-20260914.json`](../../results/evidence/phase08/wideband-burst-rf-placement-20260914.json)
içindedir.

Aday doğrulamasında otomatik parametre oturum sonu aynı son kareyi ikinci kez
yayımlayarak `survey_sequence` üretiyordu. Doğrulama oturumu tespit-only yapıldı;
her kare teslimi korunuyor ve regresyon testi eklendi. Köprü, önce çalışma
zamanında sonra SD imajında sınandı. Yalnız çalışma zamanı kopyasının yeniden
başlatmada eski imaja döndüğü gözlendi; bunun üzerine doğrulanmış temel FIT'in
kök dosya sistemi tek köprü değişikliğiyle yeniden paketlendi. Yeni `image.ub`
SHA-256 değeri `322457912d3bcefa84d3fe36f8751160729e16b02ff6fd3525071bd8b1b98a68`.
Kontrollü yeniden başlatmada FPGA `operating`, hizmet `20c151ea…`, köprü
`beb168b6…`, 47007 portu ve geniş bant yetenek biti geçti. Önceki imaj SD'de
hash bağlı yedektir. Bu tam PetaLinux yeniden derlemesi değildir; FIT kök dosya
sistemi yeniden paketlenmiştir. Kanıt
[`wideband-persistent-image-20260914.json`](../../results/evidence/phase08/wideband-persistent-image-20260914.json)
içindedir.

Ürün ayarı olan 256 kareyle kalıcı imaj üzerinde doğrudan tarama 16/16
pencereyi `12,33 s` içinde tamamladı. Son gerçek QML koşusunda ekrandaki
`Taramayı Başlat` düğmesi kullanıldı; `10 MS/s`, 16/16 pencere, sıfır hata ve
iki sonuç gösterildi. Duvar süresi `8,00 s`, en büyük 20 ms arayüz heartbeat
aralığı `46,39 ms` oldu. Kanıtlar
[`wideband-persistent-product-scan-20260914.json`](../../results/evidence/phase08/wideband-persistent-product-scan-20260914.json)
ve [`wideband-qml-live-scan-20260914.json`](../../results/evidence/phase08/wideband-qml-live-scan-20260914.json)
içindedir. Aynı ayarlı TX-kapalı negatif, genel Pd/Pfa, tüm 1 MHz–6 GHz turu ve
elektrik kesip açılan soğuk başlangıç açık kaldığından ST-06 tamamlanmadı.

## Tarama hızı fiziksel tanısı — 14 Eylül 2026

KTR-4.1 / PHASE-08 ilk hız tanısında HackRF `…35138247` fiziksel olarak görüldü
ve o koşuların alıcısı olarak kullanıldı. Sonraki kör RF çalışmasında bağlı
`…36877e47` güncel `ED_RX_PRIMARY` rolüne, `…35138247` ise ikincil role alındı.
Araç/libhackrf sürümü
`2026.01.2 / 0.9.1`, firmware `v2.4.0 (API 1.11)` olarak okundu. Aynı USB
veri yolunda bir saniyelik üçer RX tekrarında 8 ve 10 MS/s koşularının her
birinde sıfır overrun; 20 MS/s koşularında sırasıyla 154, 155 ve 153 overrun
ölçüldü. Bu bilgisayar ve USB yerleşiminde 20 MS/s temiz canlı giriş kabul
edilmedi; geniş bant geliştirme hedefi 10 MS/s ile sınırlandı. Ham gözlem ve
kaynak özetleri
[`hackrf-rx-rate-observation-20260914.json`](../../results/evidence/phase08/hackrf-rx-rate-observation-20260914.json)
içindedir.

800–840 MHz fiziksel karşılaştırmasında 128 karelik tam tarama 67 pencereyi
25,762 saniyede, 64 karelik tam tarama 16,344 saniyede tamamladı. İki turlu
`hackrf_sweep` kaba aşaması yaklaşık 0,20 saniye sürdü; ortamda 270 kaba hücre
aday seçtiği için 67 kart penceresinin tamamı yine işlendi ve toplam süre
25,934 saniye oldu. Bu profil ölçülen durumda hız kazandırmadığından ürün
arayüzünden çıkarıldı. Sweep kodu yalnız tanı ve kontrollü karşılaştırma için
kalır; varsayılan ürün yolu bütün pencereleri FPGA/ARM ile doğrular. Ham JSONL
kayıtları ve karşılaştırma `build/acceptance/rx-scan-profile-comparison-20260914.json`
içindedir. Koşuda bağımsız kontrol edilen bir RF kaynağı bulunmadığından sonuç
algılama duyarlılığı veya yayın yokluğu kanıtı değildir.

Güncel canlı zincir `HackRF 8 MS/s → PC 4:1 kanal seçici → 2 MS/s P0IQ →
kart` düzenindedir. 4.096 karelik fiziksel koşuda USB/CRC/sıra/kuyruk hatası
oluşmadı; uçtan uca hız `487,125 kare/s` ile gereken `488,28125 kare/s`
değerinin az altında kaldı. PL veri yolu 50 MHz saatle kararlı durumda saat
başına bir karmaşık örnek kabul edecek şekilde tasarlanmıştır; 50 MS/s
aritmetik kapasite, kart hizmetinin ölçülen yaklaşık 500 kare/s işlem hızından
çok yüksektir. Darboğaz FFT aritmetiği değil, kare başına PC↔kart işlemi,
DMA ve ARM servis döngüsüdür. Kartta çalışan taşıma köprüsü yalnız 2 MS/s
işleme örnekleme hızını kabul eder; arayüzde 10/20 MS/s FPGA yolu varmış gibi
gösterilmez.

Kaynakta 10 MS/s algılama-only P0IQ profili eklendi. CI8 burst PC'de
değiştirilmeden 4096 örneklik kareler olarak PL/ARM'a gönderilir; otomatik
parametre yolu bu profilde fail-closed kapalıdır. Köprü geniş bant yeteneğini
ayrı bir P0CQ bitiyle bildirmek zorundadır; eski köprüde HackRF başlatılmadan
`wideband_profile_unavailable` üretilir. Burst en fazla 256 kareyle sınırlıdır.
Python, C11 ve 10 MS/s Linux köprü loopback'i geçti. Cortex-A9 köprüsü
üretildi; SHA-256
`beb168b6a87188c82f63d5b5310240bd83fe89ddfea2dbe84943199253493d0c`.
Eski köprüyle yapılan ilk 64 karelik deneme ilk yanıtı almadan kapandı; bu
başarısız koşu da korunur. Ayrıntı
[`wideband-burst-host-gate-20260914.json`](../../results/evidence/phase08/wideband-burst-host-gate-20260914.json)
içindedir.

Kartın güncel SSH anahtarı COM6 seri konsolundan doğrulandı. Yeni köprü kalıcı
imaja yazılmadan `/tmp` altında çalıştırıldı. Aynı 64 karelik RX-only koşusu üç
kez 64/64 tamamlandı; USB overrun, taşıma CRC, sıra ve kuyruk hatalarının toplamı
sıfırdı. Kart tüketimi `498,744–505,719 kare/s`, 10 MS/s sürekli gereksinimi
`2441,40625 kare/s` ve gerçek zaman marjı `0,2043–0,2071` ölçüldü. Her burst'ün
RF örnekleme süresi `26,2144 ms`, uçtan uca süresi yaklaşık `149–153 ms` oldu.
Geçici ikili kaldırıldı ve kalıcı `e0ae46d5…` köprüsü yeniden başlatıldı. Kanıt
[`wideband-burst-physical-20260914.json`](../../results/evidence/phase08/wideband-burst-physical-20260914.json)
içindedir.

Kareden kareye değişen kontrollü sayısal gürültü üzerinde gürültü-only durumda
doğrulanmış olay oluşmadı. `±1,001 MHz` ve `±3,250 MHz` tonları PL/ARM'da
beklenen dört FFT hücresine sıfır hücre hatasıyla yerleşti; ek kalıcı tepe
oluşmadı. Bu sonuç sayısal frekans eşlemesini doğrular, HackRF analog bant
geçişini doğrulamaz. Ayrıntı
[`wideband-digital-mapping-20260914.json`](../../results/evidence/phase08/wideband-digital-mapping-20260914.json)
içindedir.

Deneysel burst taraması her pencerenin yalnız DC'den ve kenardan uzaktaki bir
tarafına `2,5 MHz` sorumluluk verir. Böylece 800–840 MHz aralığı 67 yerine 16
pencereye indi. Gerçek HackRF→kart koşusu 16/16 pencereyi `3,817 s` içinde,
sıfır USB/CRC/sıra/kuyruk hatasıyla tamamladı; aynı 64-kare ayarlı tam tarama
`16,344 s` idi. Gözlenen hızlanma `4,28×` oldu. Ortamda yalnız bir karede bir
ilk-aşama aday çıktı; sekiz karelik kalıcılık kapısına ulaşmadığı için 2 MS/s
doğrulama retune'u başlatılmadı. Kontrollü yayın kaynağı bulunmadığından bu
sonuç kaçırmama, Pd/Pfa veya yayın yokluğu kanıtı değildir. Ham pencere kaydı ve özet
[`wideband-burst-scan-20260914.json`](../../results/evidence/phase08/wideband-burst-scan-20260914.json)
içindedir.

Bu yol kısa geniş bant bloklarını daha hızlı toplar; sürekli 10 MS/s değildir.
DC merkez deliği, örtüşen pencere kenarları ve mutlak frekans eşleme kontrollü
RF ile ölçülmeden ürün arayüzünde açılmaz. Sürekli 10 MS/s için kare başına
işlemleri toplulaştıran DMA/servis ve seyrek aday çıktısı ayrıca gerekir. Yeni
kalıcı kart imajı, gerçek GUI+RX, kontrollü kör RF ve soğuk açılış kabul kapıları
açıktır.

## ED sürüm kararlılığı incelemesi — 13 Eylül 2026

Arayüz bildirim birleştirmesi otomatik parametre sonuçlarını artık düşürmez;
1.024 bekleyen sonuç sınırında açık hata ile alım durur. Katalog bağlantıları
başarı/hata sonunda kapanır; bozuk kalibrasyon ve veritabanı ED başlangıcını
kesmez, kayıt hatası görünür kalır. Paket tanımı kaynak kimliği dosyaları ve
SciPy ürün bağımlılığıyla tamamlandı. Sayısal C/Python karşılaştırması 49/49
geçti; algoritma/RTL değişmedi. Yeni imaj veya standalone kabulü yapılmadı.
[Ayrıntılı inceleme ve açık kapılar](../reviews/ED_RELEASE_REVIEW_20260913.md).
ST-06 ve fiziksel doğruluk kabulü açık kalır.

## Yalnız ED ürün kapsamı — 13 Eylül 2026

Kullanıcı kararıyla ET arayüzü, görev/TX kaynakları, yapılandırması,
doğrulayıcıları ve özel testleri kaldırıldı. Güncel ürün yalnız ED tespit,
parametre, dinleme ve yön bulma akışlarını içerir. Aşağıdaki tarihli ET
bölümleri geçmiş durum kaydıdır; güncel yetenek veya yeniden açılmış faz
değildir. Bu kaldırma ST-06 ve diğer açık ED kabul kapılarını kapatmaz.

## Güncel kaynakla 820 MHz tanısı — 13 Eylül 2026

Güncel çalışma ağacında birincil `…36877e47` HackRF görüldü; yapılandırılmış
ikincil `…35138247` aynı `hackrf_info` gözleminde görünmedi. Kartın
`192.168.7.2:47007` normal IQ bağlantısı kurulabildi, ancak çalışan ağ köprüsü
P0CQ canlı parametre yeteneğini doğrulamadı. Bu nedenle uygulama otomatik
parametre paketini göndermeden normal tespiti sürdürdü; karttaki ikili bu yeni
kaynakla eşleştirilmiş veya güncellenmiş sayılmaz.

820 MHz merkezli güncel tanıda 16/16 dB koşusu giriş I/Q kırpılmasıyla güvenli
biçimde durdu. 8/8, 8/16 ve 16/8 dB koşuları kalıcı confirmed olay üretmedi.
16/14 dB olay-kimliği tekrarında 820,000 MHz hücresi de görüldü, fakat en uzun
confirmed olay yalnız üç gözlem karesinde kaldı; kalıcı hedef bağı kurulmadı.
Tamamlanan koşularda USB overrun ile taşıma CRC/sıra/kuyruk hatası sıfırdı.
Hazırlık/kapanıştan ayrılan ilk-son kart yanıt aralığıyla son 4.096 karelik koşu
`487,431 kare/s` ile gerekli `488,28125 kare/s` sınırının altında kaldığından
güncel kaynak performans kabulü de açıktır. Harici verici durumu ve dalga biçimi
bağımsız doğrulanmadığından bu
sonuç ne yayın yokluğu ne de algılama başarısıdır. Ayrıntı
[`automatic-inline-parameter-diagnostic-20260913.json`](../../results/evidence/phase08/automatic-inline-parameter-diagnostic-20260913.json)
içindedir. Güncel kart ikilisi yüklenip iki alıcı boş ve görünür olmadan canlı
otomatik katalog, çift RX ve RF doğruluk kabulü açık kalır.

## Çoklu alıcı kimliği ve canlı otomatik parametre yolu — 13 Eylül 2026

İki HackRF, `config/p0/hackrf_ed_rx.json` içinde benzersiz
`ED_RX_PRIMARY`/`ED_RX_SECONDARY` rolleriyle tanımlıdır. Donanım denetimi her
rolü ayrı raporlar. Birincil seri mevcut tespit/parametre/yön yoluna bağlıdır;
ikincil seri tanınsa bile eşzamanlı ikinci örnek akışı ve zaman hizası fiziksel
kanıt olmadan çalışıyor gösterilmez.

Kart köprüsü P0CQ sorgusuyla canlı parametre yeteneğini bildirirse confirmed
olaylar güç sırasıyla tek bağlamlı dört-kare PL/ARM ölçümüne alınır. Tespit
yanıtları aynı karelerde kesilmez. Yetenek yoksa normal 48 baytlık P0IQ akışı
değişmeden sürer ve otomasyon kapalı görünür. 512 hücreyi aşan, referans bandı
FFT dışında kalan veya komşu sinyal içeren olaylar gerekçeli olarak kaydedilir.
Bu kaynak, C11 ve loopback doğrulamasıdır; güncel fiziksel kart imajı/iki HackRF
kabulü henüz yapılmamıştır. Güncel Qt görünüm modeli iki rolün birlikte
tanınmasını ve yeniden başlayan canlı oturumlarda olay kimliği çakışmadan kalıcı
kayıt oluşmasını ayrıca sınar. İlgili Python ve gerçek Qt/QML paketi son
kaynakta `186/186` geçti.

## Parametre doğrulama sonuçlarının görünürlüğü — 13 Eylül 2026

Tespitten başlatılan parametre ölçümünün sayısal sonucu artık yalnız kayıt ve
durum mesajında kalmaz. Dört ana alanın değeri/durumu, kaynağa bağlı ölçüm kalite kapısı ve
dört kalite metriği Parametre ekranında görünür; teknik doğrulama yeni sonuçta
otomatik açılır. Başarısız veya belirsiz alanın Türkçe nedeni aynı ekranda
verilir. Görünür özet kart/profil geçerliliği ile fiziksel doğruluk kabulünü
ayırır. İlgili 94 regresyon geçti; bu arayüz değişikliği açık RF kabul
kapılarından hiçbirini kapatmaz.

## 820 MHz canlı tespit, parametre ve dinleme bağı — 13 Eylül 2026

Kontrollü laboratuvarda kullanıcı tarafından bildirilen `820 MHz` NFM ton
yayını kaynak arayüzünde canlı olarak bulundu. Seçim anındaki aday
`819,9863 MHz`, FPGA + RX spektrumu uyumlu ve `35,3 dB` tepe/gürültü olarak
gösterildi. Olay kimliği değişimleri sırasında operatörün seçtiği RF kanalı
artık sabit kalır; eski fakat o karede gözlenmeyen ARM yaşam döngüsü kayıtları
dinlemede eşzamanlı ikinci yayın sayılmaz. Aynı karede gerçekten gözlenen iki
eşleşme ise güvenli biçimde belirsizlik olarak kalır.

İki P0PM-v2 canlı parametre tekrarı merkez, OBW ve güç için geçerli sonuç
üretti; ardından `5,001 s` canlı pencere NFM sesine çevrilip oynatıldı ve
durduruldu. Ayrıntılı değerler, arşiv özetleri, 182 geçen regresyon ve açık
kabul sınırları
[`live-820mhz-e2e-product-20260913.json`](../../results/evidence/phase08/live-820mhz-e2e-product-20260913.json)
içindedir. Dalga biçimi önceden bildirildi; kapalı/yanlış-kanal negatifleri ve
kör tekrar yapılmadı. Bu nedenle PHASE-08/ST-06, genel Pd/Pfa, yayıncı kimliği
ve parametre doğruluk kabulü kapanmaz.

## Otomatik Analog/Sayısal ürün bağlantısı — 12 Eylül 2026

Analiz aralığı arayüzündeki boş-taslak çıkmazının ardından kullanılan tepe
merkezli 512 hücreye kesme yaklaşımı hatalıydı ve kaldırıldı. Kullanıcının
2286 hücrelik aday kaydında iki referansın farkı 12,98 dB idi; güç/SNR de
reddediliyordu. Tam aday + kenar payıyla C yazılım tekrarında fark 0,65 dB,
güç -29,276 dBFS ve SNR 14,459 dB oldu. OBW, zamansal kenar değişimi 12,075
hücre olup mevcut 7 hücre kapısını aştığı için hâlâ belirsizdir. Eşik gevşetilmedi.

Kullanıcı sayısal hesapların PL/ARM'da kalmasını ve kartın genişletilmesini
onayladı. P0PM-v2 kaynak yolu 8–3984 hücre, 389.376 bayt kalıcı ARM yüküyle
uygulandı. Kilitli host F5 profilinin 512 hücre/64 KiB sınırı değiştirilmedi.
49 portable C↔Python kontrolü ve protokol testi geçti. Kart kimliği seri
konsolda ZedBoard modeli, FPGA `operating`, USB MAC ve SSH parmak iziyle
doğrulandı. Yeni hizmet ve ağ köprüsü yedekli olarak `/usr/sbin` yoluna
yüklendi ve SD `image.ub` içine işlendi. Kontrollü yeniden başlatma sonrasında
iki süreç aynı yeni özetlerle otomatik açıldı; FPGA `operating` kaldı. Altı dar
kart regresyonu geçti. Değişmemiş gerçek kayıt 2414 hücrelik
P0PM-v2 yolunda kartla işlendi: merkez 820,002879 MHz, güç -29,276 dBFS,
SNR 14,458 dB ve referans farkı 0,646 dB oldu. Kart ve portable C alan durumları
ve değerleri tolerans içinde eşleşti. OBW 12,075 hücre zamansal kenar değişimi
nedeniyle 7 hücrelik kapıda belirsiz kaldı. Bu tek kayıt genel RF doğruluğu
değildir. Kalıcı fiziksel kanıt
`results/evidence/phase08/parameter-wide-persistent-20260912.json` içindedir.
[Sözleşme ve tekrar komutları](P0_ARM_PARAMETER_RUNTIME_CONTRACT.md).

Taslak üretilemiyorsa onay düğmesi boş değerle çalışmaz;
`Aralığı Düzenle` alt/üst MHz alanlarını gerçekten düzenlenebilir açar ve ret
nedenini aynı panelde gösterir. Gerçek QML testi virgüllü MHz girişiyle boş
taslaktan geçerli onaya ilerlemeyi doğrular.

19:12 canlı tekrarında aday sınırı onay ile dört kareyi sabitleme arasında
değişti; sahiplik kapısı doğru biçimde reddetti fakat alım önceden durduğu için
panel sonuçsuz `Alım durdu` görünümünde kaldı. Akış tek düğmeye indirildi:
`Aralığı Onayla ve Parametreleri Çıkar`. İstek geçici eksik karede korunur,
sonraki dört ardışık FPGA karesi otomatik beklenir. Onaylı aralık bu dört
karedeki aynı olayın birleşik sınırını kesiyorsa 8–3984 kart sözleşmesi içinde
otomatik genişletilir; sahiplik denetimi RX iptalinden önce yapılır. Genişleme
ve iki ölçümlü canlı tekrar senaryosu hedefli testte geçmiştir. Bu arayüz yarışı
düzeltmesi RF doğruluk kabulü değildir.

Tüm alanları geçersiz kayıt artık yeşil `SONUÇ HAZIR` değildir; `ÖLÇÜM
DOĞRULANAMADI` veya `KISMİ SONUÇ` ve alan retleri görünür. PC modelinin 512
hücre üzerindeki aralık aynı sentetik 4 × 400 geliştirme kümesinde sınandı;
canlı RF sınıf kararı hâlâ deneysel ve fiziksel kabul dışıdır.

Kullanıcının PÇ-03 devam onayıyla `digital_analog_detection` PC sınıflandırıcısı
mevcut `Parametreleri Çıkar` işçisine bağlandı. İlk üç parametre P0PM PL/ARM
yolunda kalır; aynı dört CI8 kare, seçili aralık ve kart SNR sonucu PC'deki altı
özellikli lojistik modele otomatik verilir. `%90` güven altında `Belirsiz`
sonucu üretilir. Model/source hash'i, özellikler, olasılık ve kabul bayrakları
ölçüm arşivinde saklanır ve tekrar okunurken yeniden hesaplanır.

40.000 örnekli özgün sentetik iddia doğrudan ürüne aktarılmadı. Tam ürün
adaptörü, 16.384 örnekli ve aile başına 400 kontrollü sentetik geliştirme
örneğinde sınandı. `%90` güvenli kesin karar doğruluğu AM için `%98,96`,
FM/BPSK/QPSK için `%100`; karar kapsamı sırasıyla `%96,5 / %100 / %82,75 / %87,5`
gözlendi. Bu aynı üretici alanındaki geliştirme kontrolüdür; bağımsız RF, canlı
HackRF veya saha kabulü değildir. FPGA/ARM sınıflandırması uygulanmadı.
[Tekrarlanabilir geliştirme kanıtı](../../results/evidence/phase08/automatic-domain-pc-integration-20260912.json)
ve [doğrulayıcısı](../../scripts/verify_automatic_domain_integration.py) kaynak
özetleriyle birlikte saklanır.
İlk kanıt tarihsel olarak korunur. Geniş aralığı açıklamalı reddeden adaptörün
güncel kaynak bağı [yeniden üretilen geliştirme kaydındadır](../../results/evidence/phase08/automatic-domain-pc-wide-guard-20260912.json);
doğrulayıcının `--check` komutu bu yeni kaydı denetler.

## Yön ölçümüne seçim aktarımı — 12 Eylül 2026

Yön bulma tek kanal seçimiyle, açı isteğinden sonra yeni dört kare toplayan
sınırlı ölçüm akışına geçirildi. Listedeki `Alınıyor` etiketi anlık dört
ölçüm karesi hazır anlamına gelmez. Tespit algoritması ve ST-06 kabulü
değişmedi. [Güncel yön ölçümü](SIGNAL_DIRECTION_FINDING_STATUS.md).

5.1.3 sinyal izleme/dinleme çalışması kullanıcı onayıyla başlatılmıştır;
tespit durumundan ayrı güncel kayıt
[`SIGNAL_MONITORING_LISTENING_STATUS.md`](SIGNAL_MONITORING_LISTENING_STATUS.md)
içindedir. Bu başlangıç ST-06 canlı RF doğruluğunu kapanmış saymaz.

## Kalıcı imaj, matematik denetimi ve güvenli FFT sınırı — 11 Eylül 2026

PetaLinux 2025.2 tam imajı 6.090/6.090 görevle derlendi ve SD açılış
dosyalarına yazıldı. Dört yeniden başlatmada FPGA `operating` durumuna geçti;
DMA modülü, yerel ED hizmeti ve ağ köprüsü otomatik başladı. Cihaz ağacındaki
`detection-control@43c00000` düğümü ve DMA phandle'ı gözlendi. Karttan ilk
profil `4096`, kuşak `0` ve çalışma zamanı FFT desteği açık okundu. Aynı kalıcı
imajda altı sayısal sahne yeniden fiziksel PL→ARM yolundan geçti; bozuk CRC
reddi ve ölçüm öncesi/sonrası normal DMA durumu `7` olarak doğrulandı.
[Kalıcı imaj kanıtı](../../results/evidence/phase08/parameter-persistent-image-20260911.json),
[kart parametre kanıtı](../../results/evidence/phase08/parameter-board-persistent-20260911.json).

Önceki artan FFT koşuları 4096→8192→16384 yolunu işlemiş, 4096 geri dönüşünü
yalnız profil geri okumasıyla kontrol etmişti. Yeni post-downshift veri deneyi
8192→4096 sonrasında XFFT/DMA'nın kilitlenebildiğini gösterdi. Güncel sürücü
aynı açılışta FFT küçültmeyi fail-closed reddeder; arayüz yeniden başlatma
gerektiğini söyler. Fiziksel testte 4096→8192 geçti, 8192→4096 reddedildi,
hizmet çalışmaya devam etti ve yeniden başlatma 4096/kuşak 0'ı geri getirdi.
Dolayısıyla keyfî iki yönlü çalışma zamanı FFT iddiası yoktur.

Matematik denetiminde ARM C ile kilitli Python F5, 33/33 sahnede alan durumu ve
değer olarak eşleşti. Bağımsız uzun kayıtlı 30 sayısal örnekte güç 30/30
geçerliydi ve en büyük hata 0,189 dB oldu. Buna karşı emisyon merkezi hatası
BPSK'de 10,209 kHz'e ulaştı; taşıyıcı çizgisi sıkça doğru biçimde sonuç
vermekten kaçındı. Seçili aralık tüm emisyonu kapsamadığında BPSK OBW'si üç
örnekte yanlış biçimde geçerli kaldı ve hata 325,644 kHz'e ulaştı. Bu nedenle
PL/ARM uygulamasının gerçek hesap yaptığı ve referansı doğru izlediği
kanıtlıdır; geniş emisyon aralığı kapsama kapısı ve canlı RF doğruluğu henüz
kapanmamıştır. [Matematik denetimi](../../results/evidence/phase08/parameter-math-audit-20260911.json).

Kapsama açığı için iki yazılım adayı ayrıca sınandı. Dört kısa dikdörtgen FFT'nin
aralık dışı enerji oranı 30 örnekte dar bir ayrım verdi; bu kadar küçük sentetik
kümeyle güvenli eşik sayılamaz. Dört karenin tek 16.384 örnekli Hann gözlemiyle
hesaplanan muhafazakâr kuyruk-belirsizlik kapısı, aralık dışı altı BPSK'nin
tamamında OBW vermedi; fakat 12 dB'deki diğer dört ailenin tümünde de OBW'yi
tuttu. Bu aday yanlış dar bant sonucunu azaltabilir, ancak kapsam bedeli,
komşu yayın/renkli gürültü davranışı ve C/ARM karşılığı henüz doğrulanmadığı için
kilitli ürüne eklenmedi. [Kapsama denetimi](../../results/evidence/phase08/parameter-obw-containment-audit-20260911.json).

dBFS alıcının sayısal tam ölçeğine göre kanal gücü, dB ise bant içi spektral
SNR oranıdır. dBm yalnız aynı cihaz/frekans/örnekleme/LNA/VGA/filtre/ölçek
bağlamında ölçülmüş kalibrasyon ofseti, süre ve belirsizlik denetimleri
geçerse üretilebilir. Güncel P0PM yanıtı dBm taşımaz; kalibrasyon olmadığı için
arayüz tahmini dBm göstermez.

## Parametre çıkarımı PL/ARM ürün bağlantısı — 11 Eylül 2026

Kullanıcının taşıyıcı frekansı, bant genişliği ve güç için PÇ-02/PÇ-04'e
devam; analog/sayısal ayrımını erteleme talebi uygulanmıştır. Canlı ürün
ölçümü dört ardışık CI8 karesini sabitler, alımı durdurur ve `P0PM-v1` ile aynı
kareleri ZedBoard'a gönderir. Kart, her kareyi fiziksel PL Hann→4096 FFT→güç
yolundan yeniden geçirir; ARM taşıyıcı çizgisi, emisyon merkezi, OBW %99,
kanal gücü dBFS ve SNR'yi hesaplar. Bağlantı veya kart işlemi başarısızsa PC
F5'e geri dönüş yapılmaz. Sinyal türü aynı dört karede ayrı deneysel PC
sınıflandırıcısıyla hesaplanır; FPGA/ARM parametre yanıtının parçası değildir.

Taşıyıcı yöntemi bastırılmış veya yeterince belirgin olmayan çizgilerde merkez
frekansını taşıyıcı diye kopyalamaz; `gözlenmedi` döndürür. 33 sentetik host C
karşılaştırması tüm alan durum/değerlerinde F5 ile eşleşti. Gerçek ZedBoard'da
altı sayısal sahne PL→ARM yolundan geçti: merkez/taşıyıcı/kenar/bant hatalarının
azami değerleri sırasıyla 0,00691 / 0,00093 / 0,02057 / 0,02042 Hz; güç ve SNR
hataları 0,000049 / 0,000100 dB oldu. Kart hesap süresi 15,253–78,448 ms idi.
Bozuk I/Q CRC'si reddedildi; ölçüm öncesi/sonrası normal tespit DMA durumu 7,
FPGA profili 4096 ve kuşak 0 olarak değişmeden kaldı.
[Fiziksel sayısal kanıt](../../results/evidence/phase08/parameter-board-integration-20260911.json),
[C eşdeğerlik kanıtı](../../results/evidence/phase08/parameter-carrier-equivalence-20260911.json).

dBFS→dBm dönüşümü yalnız cihaz, ayar frekansı, örnekleme, LNA/VGA, filtre ve
örnek ölçeğini bağlayan; ölçülmüş aralığı, geçerlilik süresi ve belirsizliği
olan profil için açılacak şekilde ARM API'sinde fail-closed uygulanmıştır.
Güncel ARM test ikilisi kartta geçti; test katsayıları yapaydır ve dBm kabulü
değildir. Güncel `P0PM-v1` yanıtı dBm alanı taşımaz; fiziksel profil ölçülmeden
profil yükleme ve kullanıcıya dBm sunma yolu etkinleştirilmeyecektir. Bu nedenle
mutlak güç için yalnız test değil, kalibrasyon sonrasında sınırlı bir hizmet/UI
bağlantısı da kalır. [ARM kalibrasyon API kanıtı](../../results/evidence/phase08/parameter-arm-state-calibration-20260911.json).

Bu bölümde anlatılan geçici ikili deneyi daha sonra yukarıdaki kalıcı imaj ve
iki yeniden başlatma kanıtıyla aşılmıştır. Canlı HackRF RF doğruluğu, gerçek
dBm kalibrasyonu, frekans referansı ve uzun/iptalli GUI koşusu açıktır.
Dolayısıyla ilk üç parametrenin ürün hesap yolu uygulanmış ve sayısal olarak
doğrulanmıştır; fiziksel RF doğruluğu henüz kabul edilmemiştir.

## Ayar panelinin sadeleştirilmesi — 11 Eylül 2026

KTR-4.1-OPS-B0: FPGA tespit kontrolleri üstte, spektrum kontrolleri altta toplandı. Uzun açıklamalar ve sabit zincir dökümü kaldırıldı; kısa FFT boyutu, eşik katsayısı ve yenileme aralığı adları kullanılıyor. Hata/işlem geri bildirimi ve backend kilitleri korunuyor. 1280×800 QML görünümü incelendi. Bu yalnız sunum değişikliğidir; önceki fiziksel kanıtın QML hash’i güncel değildir ve değiştirilmez. Hann dışı pencere mevcut işin kabul şartı değildir.


## Son denetim ve devam noktası — 11 Eylül 2026

Ürün ViewModel komutlarının bu tarihli deneyi fiziksel kartta 8192 → 16384 →
4096 profil geri okumasını, normal/zayıf eşik uygulamasını ve varsayılana
dönüşü geçti. Ancak 4096 geri okumasından sonra yeni veri işlenmedi. Üstteki
güncel post-downshift deneyi bu eksikliği ortaya çıkardı ve küçültme artık
yeniden başlatma gerektiriyor. Tarihsel kanıt:
[`st06-runtime-fft-ui-20260911.json`](../../results/evidence/phase08/st06-runtime-fft-ui-20260911.json).
Bu, QML tıklama/render veya canlı HackRF koşusu değildir.

Seçili 169 denetimin ilk koşusunda 163 geçti. Eski RF kaynak ayrışım listesi
ve yeni RTL envanteri düzeltildikten sonra ilgili 33 denetimde 30 geçti;
üç kalan hata önceden bulunan parametre geliştirme dosyalarının faz envanteri
uyuşmazlığıdır. Bu dosyalar silinmedi ve topluca onaylı sayılmadı.
Linux gerçek hizmet/köprü/ARM ve sahte DMA testinde 13 durum geçti; test
profilinin alan sırası designated initializer ile düzeltildi. Gerçek kart
ikilisi değişmedi. FFT derleme ve üç tekrarlı kanıtın hash kontrolü geçti.

Sonraki iş: değişken FFT'de görüntü hızı açıklamasındaki sabit 4096 varsayımını
düzeltip yeni UI kanıtını ayrı sürümlemek; ardından kayıtlı I/Q ile uzun
GUI/kart koşusu ve Hann dışı pencere fizibilitesi. Önceki yüzde/süre tahmini
bu açık işleri tam temsil etmiyordu; bütün ST-06 için tamamlanma iddiası yoktur.

## Dinamik FPGA FFT fiziksel sayısal kabulü — 11 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, ST-06: arayüzdeki tespit FFT seçimi artık gerçek
FPGA Hann→XFFT→güç→OS-CFAR zincirini 4096/8192/16384 arasında değiştirir.
FPGA kontrol bankası, Linux sürücüsü, ARM hizmeti, Ethernet sözleşmesi ve PC
geri okuması aynı etkin profili kullanır. Uyuşmayan çerçeve boyu reddedilir;
ayar yalnız DSP boşken atomik uygulanır. Başlangıç ve son profil 4096'dır.

Tam Zynq-7020 tasarımı Vivado 2025.2 ile 50 MHz'te WNS `+0,613 ns`, WHS
`+0,030 ns`, sıfır yönlendirme hatasıyla geçti; 24.251 LUT, 20.802 register,
94,5 BRAM ve 61 DSP kullanır. Kartta her FFT boyutu üç bağımsız koşuda 4.096
ölçüm karesiyle sınandı. En düşük hızlar 540,081 / 249,970 / 138,120 kare/s;
gerekli hızlar 488,281 / 244,141 / 122,070 kare/s'dir. Toplam 36.864 ölçüm
karesinde DMA durumu, CRC, sıra ve kuyruk kontrolleri geçti. Karttaki bitstream,
modül, hizmet ve köprü hash'leri paketlenen ürünlerle eşleşti.
[Tekrarlı fiziksel sayısal kanıt](../../results/evidence/phase08/st06-runtime-fft-physical-repeated-20260911.json).

Bu sonuç gerçek FPGA ve ARM işlemesidir; HackRF bağlı olmadan üretilen sınırlı
sayısal I/Q ile alınmıştır. Pencere türü hâlâ Hann'dır. Kalıcı SD imajı, güncel
GUI+HackRF dayanıklılığı, kontrollü RF Pd/Pfa, dBm kalibrasyonu ve soğuk açılış
kabulü açıktır; ST-06 tamamlanmış sayılmaz.
[SDRangel/GNU Radio karşılaştırması ve saha öncesi çalışma planı](../reviews/SIGNAL_DETECTION_COMPETITIVE_RESEARCH_20260911.md).

## Değişken FPGA FFT fizibilitesi — 10 Eylül 2026

Vivado 2025.2 ile aynı XFFT ayarlarında yapılan iki ayrı OOC sentez, mevcut
sabit 4096 çekirdeğin ve azami 16384/çalışma zamanı seçilebilir çekirdeğin
Zynq-7020'ye sentezlendiğini doğruladı. Dinamik çekirdek 4096/8192/16384 için
NFFT 12/13/14 kabul ediyor. Çekirdek farkı +2.636 LUT, +2.751 register,
+34,5 BRAM ve +8 DSP'dir. Mevcut yönlendirilmiş tam tasarıma yalnız bu fark
eklendiğinde kaba üst kullanım %42,352 LUT, %19,236 register, %41,429 BRAM ve
%27,727 DSP olur; kaynak kapasitesi engeli görünmemektedir.

Bu sonuç tam tasarım sentezi, zamanlama, DMA/ARM entegrasyonu veya kart kabulü
değildir. Hann, FFT adaptörü, CFAR, DMA ve hizmet protokolü birlikte
sürümlenmeden arayüz FPGA FFT'sini değiştirmiş sayılmaz. Çalışan 4096 kart
yolu korunmuştur. [Tekrarlanabilir fizibilite kanıtı](../../results/evidence/phase08/st06-runtime-fft-feasibility-20260910.json).

## FPGA eşik kontrolü ve sayısal kart kabulü — 10 Eylül 2026

CFAR normal/zayıf katsayıları artık AXI-Lite → Linux sürücüsü → ARM hizmeti →
PC arayüzü boyunca gerçek FPGA'ya bağlıdır. Arayüzde karttan okuma, durdurulmuş
alımda uygulama, kuşak numaralı tam geri okuma ve varsayılana dönüş vardır.
Fiziksel kartta aynı dört I/Q karesi varsayılanda 33, hassas profilde 862,
geri yüklemede yeniden 33 ham aday üretmiştir. Son profil varsayılan
`36851433755 / 17098572778` değerleridir.

Geçici yüklenen imajın kontrol kimliği `0x53540601`; bitstream, modül, hizmet
ve köprü hash'leri kart ile yerel derleme arasında eşleşmiştir. Vivado 50 MHz
sonuçları WNS `+0,234 ns`, WHS `+0,011 ns`, yönlendirme hatası `0`'dır. Son
ARM hizmeti üç bağımsız 4.096 karelik ölçümde 507,587 / 509,211 / 511,557
kare/s vermiş; alt sınır 488,281 kare/s ve en düşük pay `%3,954` olmuştur.
Tüm koşularda DMA/CRC/sıra/kuyruk/düşüm sayıları sıfır, uzun koşu yanıt hash'i
aynıdır. [Hash bağlı fiziksel sayısal kanıt](../../results/evidence/phase08/st06-runtime-config-physical-20260910-v3.json).

Bu yükleme geçicidir; SD açılış dosyaları değiştirilmedi. Bu bölümün imajında
FPGA FFT'si 4096 ve pencere Hann'dı; 11 Eylül tarihli üst bölüm bu sabit FFT
sınırını yeni kaynak ve fiziksel kanıtla aşar. HackRF RF etkisi, kontrollü
Pd/Pfa, GUI+HackRF dayanıklılığı ve soğuk açılış kabulü açıktır.
[Kapsam ve doğrulama](DETECTION_RUNTIME_CONFIG_CONTRACT.md).

## Sinyal ayarları ve zayıf yol bağlantısı — 10 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: görüntü FFT’si, görüntü sıklığı, tarama gözlem ve
yerleşme süreleri ilgili ayar panellerine bağlandı. VGA tüm 2 dB adımlarıyla
0–62 dB seçilebilir. Bu bölümdeki FPGA FFT profili sabitti; 11 Eylül ürünü
4096/8192/16384 tespit FFT seçimini gerçek karta bağladı. Güncel hizmetin güç girişine
DMA v2 zayıf biti ve ARM 24/32 yolu eklendi; eski A biçimi zayıf bilgi içermez.
RTL simülasyonunda 49.152 kelime referansla eşleşti; 48.910 çevrim değişmedi.
Yeni Vivado yerleştirme/yönlendirmesi ve XSA/bitstream eşliği geçti;
50 MHz setup marjı +0,708 ns. Zayıf durum geri alma kopyası 63.624 bayttan
1.616 bayta indirildi ve 4.096 karede bayt eşitliği doğrulandı.
[Güncel dijital kanıt](../../results/evidence/phase08/st06-weak-power-20260910.json).
ARM hedef derlemesi ve Linux hizmet testleri geçti. Güncel kaynak/imajın
FPGA eşik bağlantısı ve sayısal hızı üstteki yeni kanıtla doğrulandı; gerçek
HackRF RX, RF doğruluğu ve soğuk açılış kabulü açık, eski kanıt aktarılmaz.
[Ayarlar, biçim geçişi ve kaynak kılavuzu](DETECTION_TUNING_AND_SOURCE_GUIDE.md).

## Bant taramasından parametre seçimine geçiş — 10 Eylül 2026

Seçili bant taraması sonucu için `Parametre Çıkarımına Git` işlemi eklendi.
İşlem, geçmiş satırı doğrudan ölçüm sonucu saymaz; seçilen frekansta sabit alımı
başlatır, frekans aralığı eşleşen güncel ve doğrulanmış FPGA adayını seçer ve
dört ardışık ölçüm karesi hazır olduğunda Parametre görünümüne geçer. Yayın
yeniden bulunamazsa sabit alım ekranında kalır. Tespit, ölçüm eşikleri ve RF
kabul durumu değişmedi. İlgili durum ve QML regresyonları 3/3 geçti.

## Dört parametrenin gerçek RF durumu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: yeni temiz AM koşusunda dar aralık SNR'si
13,36–15,32 dB iken sabit aday 10/10 Belirsiz kaldı. Yeni `rf_observation`
ürün dışı ön işlemesi uzun I/Q, FIR kanal süzme ve frekans kayması
hipotezlerini uygular; kesin sınıflandırıcı değildir. Kullanılabilir donanım
son beyana göre yalnız iki HackRF'dir; dBm kalibrasyonu diğer işleri durdurmaz.
Ürün/ARM/RTL ve önceki kabul durumları değişmedi.

Yeni AM kaydı 480.000.000 bayt, sıfır taşma/kırpılma; yaklaşık altı saniye
yayın ve 1699,22 Hz zarf tonu içerir. Son BPSK penceresinde hedef etkinliği
bulunmadı; Play ile kayıt kesin eşleşmediğinden RF/sınıf başarısızlığı sayılmaz.
Eski taşmalı BPSK yalnız geliştirme tanısıdır. Yeni AM'de frekans düzeltmesi,
ikinci kuvvet uyumunu 0,0129–0,0439'dan 0,8477–0,9386'ya taşıdı; bu sınıf
başarısı değildir. Dört gerçek kayıtta 40 yayın/4 ön pencere incelendi.
Taşıyıcı doğruluğu, tam emisyon OBW, Analog/Sayısal ve mutlak dBm açıktır.
Sonraki iş mevcut gerçek veride ön işlemeyi sınıflandırma geliştirmesine
bağlamak ve zaman eşleşmesi net bağımsız sayısal RF sağlamaktır; aynı AM
ayarı körlemesine tekrarlanmaz. Yeni faz veya ürün profili açılmadı.

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


## ET'ye kullanıcı onaylı geçiş — 8 Eylül 2026

Kullanıcı PÇ-02 ile PHASE-09'u beklemeye alıp PHASE-10 Tekli Görev çalışmasını
başlatmayı onayladı. Açık ED ve parametre kabul maddeleri korunur; tamamlanmış
sayılmaz. Tek bantta iletimsiz gürültü/CI8 doğrulaması ve fiziksel profil kilitli
HackRF süreç sınırı uygulandı. HackRF bağlı değildir; ET_TX profili kapalıdır ve
RF gönderimi yapılmamıştır. PHASE-10 fiziksel kapısı ve PHASE-11 kapalıdır.

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


## Dört parametre bağımsız tanılama — 7 Eylül 2026

KTR-4.2 / KTR-4.2-F1 kapsamında PÇ-02 sayısal başlangıç çalıştırıldı:
`scripts/validate_parameter_bench.py` ile beş ailede 30 bağımsız sentetik
I/Q kaydı üretildi; ürün F5 ölçümü ve 30/30 yeniden hesaplama eşleşti.
Bu doğruluk kabulü değildir: 24 modülasyonlu örneğin tamamında sınıf Belirsiz;
CW taşıyıcı alanı 1/6 sonuç verdi. Geniş kuyruklu BPSK tam emisyonu ölçüm
aralığını aşıyor. Güç hatası bu sentetik örneklerde en çok 0,189 dB;
dBm kalibrasyonu ve canlı ölçüm sürekliliği açık. İlgili 82 yazılım testi geçti.
Yöntem/eşik/RTL değişmedi; eski kanıtlar korunur. Ayrıntılı referans, paydalar,
sınırlamalar ve fiziksel deney düzeni `docs/plans/PARAMETER_VALIDATION_BENCH.md`
içindedir. Yerel rapor: `build/acceptance/parameter-bench-20260907-v1/report.json`.

## Alıcı değişimi — 7 Eylül 2026

Kullanıcı alıcı ve vericinin yerini değiştirdi. `config/p0/hackrf_ed_rx.json`
ED_RX kimliği USB envanterinde gözlenen `0000000000000000a32868dc35138247`
olarak güncellendi. Önceki cihazın ölçüm ve mahmuz kayıtları bu cihaza aktarılmaz.
700 MHz merkez, LNA/VGA 16/16 dB ve otomatik kazanç kapalı ilk GUI alımı
`iq_saturation` ile durdu; aynı ayarlı ikinci denemede canlı spektrum görüldü.
Bu oturum gözlemi arşivlenmiş RF doğruluk kabulü değildir. Yeni vericinin açık/kapalı
beyanı ve eşleştirilmiş ölçümler bekleniyor; KTR-4.1 / ST-06 ve KTR-4.2 kabulü açık.

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

Doğrulama 134 geçti / 1 başarısızdır. Başarısızlık değişmemiş `Main.qml`
dosyasındaki önceden mevcut 2.255/2.200 satır sınırıdır; paket genel sonucu
başarısız tutulur. PÇ-00 kayıt ve yeniden hesaplama kontrolleri geçti.

Kullanıcının uygulamaya devam talimatıyla KTR-4.2 / KTR-4.2-F1 için mevcut
F5 ölçümüne kaynak ve I/Q bağlı kayıt eklendi. Canlı ve SigMF ürün ölçümü,
dört normalize I/Q karesini ve alanların birim/yöntem/durum/neden bilgilerini
ayrı ZIP'e kaydeder; kayıt başarısızsa yeni sonuç yayımlamaz. Canlı karelerde
merkez, örnekleme, sıra ve kart yanıtı bağı ayrıca denetlenir. Profil/model
özetleri, oturum ayarları, kanal seçici ölçeği ve bilinen kaynak özetleri
saklanır. Donanım UTC zamanı, çalışan kart imajı ve kalibrasyon gözlenmemişse
bilinmiyor kalır; dBm veya RF doğruluk sonucu üretilmez.
[Kayıt ve yeniden üretim sözleşmesi](OPERATOR_ASSISTED_PARAMETER_CONTRACT.md) sınırları tanımlar.

F5E paket denetimi mevcut iki ek logoyu açık listesine aldı; eksik model ve
izinsiz ek dosya retleri korunur. Eski F5E/PHASE-08 kanıtları değiştirilmedi.
Parametre satırlarını oluşturma işlevi mevcut ölçüm modülüne taşındı; görünen
alanlar ve algoritma eşikleri değişmedi. Yeni kanıt
`results/evidence/phase08/parameter-record-v1.json` ve ZIP içindedir.
Bu yazılım kayıt/entegrasyon kabulüdür; yeni fiziksel kart veya RF deneyi
değildir. ST-06 ve dört parametrenin saha doğruluğu açıktır. PÇ-01 arayüz
sadeleştirmesi sonraki iştir; tercihli özellikler ve PHASE-09 açılmadı.

## Zorunlu parametre planlamasına sınırlı geçiş — 7 Eylül 2026

Kullanıcı taşıyıcı frekansı, bant genişliği, güç seviyesi ve Analog/Sayısal
ayrımı için mevcut çalışmaya devam edilmesini ve önce plan hazırlanmasını
istedi. [Kontrollü devam planı](../plans/IMPLEMENTATION_ROADMAP.md) mevcut
PHASE-04-F5 / PHASE-08 ölçüm yolunu, PC/PL/PS sınırını ve PÇ-00–PÇ-05 sırasını
tanımlar. Bu kapsam önceki yalnız tespit bakım talimatını günceller;
ST-06 ve PHASE-08 kabulünü kapatmaz. Tercihli parametreler ve PHASE-09 açılmaz.
Canlı QML ölçümü bugün bilgisayarda F5 çalıştırır; ARM sayısal çekirdeği vardır
ancak taşıyıcı ve sınıflandırma ARM'a taşınmamıştır. dBm kalibrasyonu açıktır.
Başlangıç kontrolünde host C/Python sayısal karşılaştırması geçti; 33 profil/
arşiv/QML testinin 32'si geçti, eski paket dosya-listesi kontrolü başarısızdır.
Bu oturumda üretim kodu veya donanım değiştirilmedi; yeni RF kabulü yoktur.
Aşağıdaki tarihli kayıtların sonuçları ve özgün kanıt sınırları korunur.
## ET Faraday laboratuvar kararı — 8 Eylül 2026

Kullanıcı, bundan sonraki fiziksel ET-TX çalışmalarının hazır korumaları bulunan
Faraday kabini içinde yapılacağını bildirmiş ve `CABLED_LAB` politika kilidinin
kaldırılmasını onaylamıştır. Genel/açık alan `HARDWARE_TX_LOCKED` yolu kapalı
kalır. Karar sırasında HackRF TX arka ucu ve bağlı cihaz yoktu; RF yayını
yapılmadı. Birleşik güncel kaynakta güvenlik kapılı Tekli Görev HackRF süreç
arka ucu vardır; depo profili ve fiziksel kapı kapalı, bağlı cihaz yoktur.
Çevrimdışı C++17 üreteç ürün dışında kalır. Ayrıntı ADR-0043 ve RF güvenlik
sözleşmesindedir. Bu karar PHASE-08 / ST-06 durumunu değiştirmez ve fiziksel ET
kabulü sayılmaz.

## Son arayüz düzenlemesi — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında sabit frekans ve bant taraması ekranları
boşta, çalışırken, bağlantı yokken ve sonuç varken görsel olarak denetlendi.
Frekans ve kazanç değerleri aynı yükseklik, yazı boyutu ve merkez hizasını
kullanır. Bağlı durumu düğme olmaktan çıkarıldı; yalnız bağlantı yokken
`Sistemi Denetle` görünür. Başlat/durdur aynı anda gösterilmez. Sonuçlarda
tekrarlanan tespit cümleleri ve teknik sayaçlar kaldırıldı; frekans ve varsa
kaba aralık ana bilgidir. Teknik kanıt ipucunda korunur. Algoritma eşikleri,
RTL ve RF kararları bu son görsel düzenlemede değiştirilmedi. Parametre fazına
geçilmedi; ST-06 açık kapıları korunur.
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


## Güncel kanıt sınırı ve düzeltme — 6 Eylül 2026

Kapsam PHASE-08 / ST-06 ve KTR-4.1 / KTR-4.1-OPS-B0'dır; kabul açık kalır.
Tarihsel `native-channelizer-v3.json`, `st06-parallel-product-v1.json` ve ZIP,
`559d496` sürümündeki özgün baytlarına döndürülmüştür. Sonradan eklenen
kaynak hash'leri ve yeniden doğrulama tarihleri yeni ölçüm kanıtı değildi.
ST-06 arşivindeki fiziksel ölçümler değişmemişti; yalnız PC kaynak kopyasının
değiştirilmesi eski ölçümleri yeni kaynağa geçersiz biçimde bağlıyordu.
Özgün manifest ve arşiv özetleri doğrulayıcıda sabittir; yeni ölçümler yeni
adlı kayıtlara yazılır. Bu düzeltmede donanım prosedürü tekrarlanmadı.

5 Eylül RX kayıtlarının kapsamı:

- Önceki PC kaynağıyla iki 439.453 karelik koşu `usb_overrun` ile başarısızdır.
- Değiştirilmiş PC kaynağıyla tek 439.453 karelik arayüzsüz koşu tamamlandı:
  USB taşması, CRC/sıra/kuyruk hatası ve I/Q kırpılması 0; taşıma
  439.453/439.453 karedir. Kaynak hash'i `2f56a143…c105080` olarak kayıtlıdır.
- Ölçülen toplam süre 900,1213107 saniye, hız 488,2153047 kare/s'dir.
  Nominal 488,28125 kare/s karşısındaki yaklaşık %0,0135 fark hız payı
  sağlamaz; toplam süre ölçümü tek başına sürekli işleme kapasitesini ayırmaz.
- `preview_frames: 0`: Qt arayüzü, çizim sürekliliği ve görüntü gecikmesi
  bu koşuda sınanmadı. Eski “arayüz RX kabulü” ve “sürekli RX kapısı geçti”
  ifadeleri geri çekilmiştir. Kanıt, tek koşunun alım/taşıma bütünlüğüdür.
- Kuyruk ve işlem süresi tanıları uzun koşuda 16 karede bir örneklenir.
  6/512 ve 64/64 kaydedilen örneklenmiş kuyruk değerleridir; 6/512 kesin
  tepe veya kuyruk güvenlik payı değildir. Daha az tanı maliyetinin taşmayı
  kalıcı çözdüğü veya USB denetleyicisinin kök neden olduğu kanıtlanmadı.
- `transmit_enabled: false` yalnız RX yazılım yolunu ifade eder; harici
  vericinin kapalı veya ortamın RF sessiz olduğunu doğrulamaz. Kartın çalışan
  imaj kimliği ham RX kaydında bulunmaz; başka ölçümden devralınmaz.

`live-rx-endurance-v3.json` ve ZIP, kendi ham koşusuyla değiştirilmeden
korunur. `endurance_passed` alanı o betiğin sınırlı bütünlük kontrolüdür;
GUI, nominal hız marjı, RF Pd/Pfa, soğuk açılış veya ST-06 kabulü değildir.
İki başarısız koşu, son koşu ve kayıtlı kaynakların doğrulanmış kopyaları
`results/evidence/phase08/rx-evidence-recovery-v1.json` / ZIP içindedir.

Denetim komutları:

- `python scripts/verify_phase08_evidence_recovery.py`: özgün kanıtları,
  üç koşunun ham kayıtlarını ve kabul kapsamını denetler; yeni ölçüm yapmaz.
- `python scripts/verify_st06_parallel_product.py --historical`: özgün
  ST-06 arşivindeki kaynakları, yanıtları ve süre hesaplarını denetler.
- `python scripts/verify_st06_parallel_product.py`: güncel kaynak bağı
  için sıkı kontroldür; değişmiş `live_ed.py` nedeniyle başarısız olması
  beklenir. Bu başarısızlık hash değiştirerek giderilmez.

Sonraki kabul gerçek arayüz açıkken tekrarlı RX bütünlüğü, görüntü/olay
gecikmesi ve durdur/başlat; ardından kontrollü kör RF doğruluğu ve soğuk
açılıştır. Saf ton fazla adayları ve 64 olay kapasitesi de açık kalır.
Aşağıdaki tarihli kayıtlar kendi sürümlerinin sonuçlarıdır.

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
Güncel kaynak bağını `python scripts/verify_st06_parallel_product.py` denetler;
uyuşmazlık beklenir ve kabul sayılmaz. Özgün arşiv `--historical` ile
denetlenir; bu seçenek yeni kaynak için fiziksel kabul oluşturmaz.
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
