# ADR-0023 — ET Offline Görev Konsolu ve TX-Kilitli Modeller

- Durum: Kabul edildi
- Kapsam: Kullanıcı onaylı ET arayüzü ve yalnız bilgisayar üzerindeki deterministik modeller
- Önceki doğrulanmış sınır: P0 ET taban bant modelleri ve fail-closed görev denetleyicisi

## Karar

ET çalışma alanı dört ayrı görev olarak sunulur: sürekli karıştırma,
arabakışlı karıştırma, analog aldatma ve GNSS senaryosu. Her görev ortak bir
`OFFLINE`/`LOOPBACK`/`REPLAY` durum başlığı, `TX KİLİTLİ` etiketi, yalnız kendi denetimleri,
salt-okunur işlem akışı ve yapılandırılmış sonuç kaydı kullanır.

Sürekli model tekli, çoklu, seeded bant-sınırlı baraj ve doğrusal süpürmeli
kompleks taban bant tamponlarını üretir. Arabakışlı görev denetleyicisi
deterministik yerel analiz girişinde enerji eşiği, ardışık pencere onayı,
histerezis ve `DİNLE → GECİKME → GÖREV → KORUMA → DİNLE` akışını doğrular.
Analiz ve görev pencereleri eşzamanlı olamaz; örnek-seviyesi maske yalnız görev
penceresinde sınırlı offline kompleks ton tamponunu açar. Bu tampon aygıt veya
RF çıkışı değildir. Analog model üretilmiş 1 kHz doğrulama sesini
normalize eder, ses bandını sınırlar ve AM/FM/NFM kompleks taban bantlarını
yerel loopback ile denetler. GNSS görevi yalnız GPS L1 C/A senaryo metadatasını
doğrular; ephemeris, NAV verisi veya RF dalga şekli üretmez.

Tüm görevler ortak `ETTaskResult` veri sözleşmesi ile sonuç verir. Bu sözleşme UI
metninden bağımsız olarak görev tipi, mod, kaynak, zaman, süre, dalga biçimi,
örnekleme, normalizasyon, doğrulama ve TX kilidi alanlarını taşır.

## ET-C Ürün Bağı

ET-C ile dört görev, ana Qt Quick/QML ürün uygulamasındaki ED/ET seçicisine
bağlanmıştır. QML katmanı ayrı bir hesaplama veya örnek veri üretmez; sonuç
başlıkları, sınırlı grafik dizileri, zamanlama pencereleri ve ölçüm satırları
doğrudan `algorithms.et` modellerinden gelir. Ürün paket manifesti bu nedenle
`algorithms/et` kaynaklarını açıkça dahil eder. Mock alım, eski QWidget
laboratuvarı, doğrulama veri setleri ve yayın arka ucu dışlama listesinde kalır.

ET görünümü 1180×680, 1280×720 ve 1440×900 çözünürlüklerde tekrarlanabilir QML
render kapısına bağlıdır. Arabakışlı görünüm ölçüm olmayan görev pencerelerini
boşluk olarak, GPS görünümü ise dalga şekli yokluğunu açık durum olarak gösterir.
ViewModel herhangi bir `transmit` arayüzü sunmaz.

Operatör yüzeyinde çalışma biçiminin iç adı gösterilmez. Yayın sınırı üst durumda
yalnız `YAYIN — DEVRE DIŞI` olarak bir kez belirtilir; görev kartı, sonuç başlığı,
ölçüm listesi ve alt durum şeridinde aynı uyarı tekrarlanmaz. Teknik mod ve kilit
alanları sonuç sözleşmesinde korunur. Görev seçimi, buton basımı ve sonuç yenileme
geri bildirimleri 140–350 ms aralığında kalır ve `Hareketi azalt` seçeneğiyle
sıfırlanır.

## Güvenlik Sınırı

Bu karar RF çıkış yolu, SDR aygıt erişimi, OTA iletim, kablolu RF gönderim,
güç/frekans reçetesi veya GNSS RF üretimi eklemez. `CABLED_LAB` ve
`HARDWARE_TX_LOCKED` modları fail-closed kalır. `OFFLINE` ve `LOOPBACK` sonuçları
canlı ya da fiziksel RF sonucu olarak etiketlenmez.

## Kanıt ve Ertelenen İşler

Deterministik birim ve Qt binding testleri host üzerinde çalışır. Bu kanıt
HackRF-2, GNSS alıcısı, RF spektrum ölçümü, RF etkisi, RF güç seviyesi, gerçek
zamanlı tepki süresi veya fiziksel görev çevrimi ölçümü değildir. Bu fiziksel çalışmalar yol haritasındaki kontrollü
RF güvenlik kapıları ve ayrı kullanıcı onayı olmadan başlatılmaz.
