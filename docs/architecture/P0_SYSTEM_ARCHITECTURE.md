# P0 Gerçek Sistem Mimarisi

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
yalnız `OFFLINE` ve `LOOPBACK` modlarındadır. `CABLED_LAB` güvenlik/interlock
kanıtı olmadan kilitlidir; gerçek TX backend'i uygulanmamıştır.

İki bilgisayar Python belleği veya süreç durumu paylaşmaz. Gelecekte görev verisi
aktarılması gerekirse sürümlü ağ veya dosya sözleşmesi kullanılır.

## Anten ve DF

Seçilen frekansa uygun FOX-727, 800 MHz–6 GHz UWB veya HackRF bandıyla sınırlı
TEM yönlü anten operatörce elle döndürülür. Her ölçüm açı, göreli güç, frekans,
UTC zaman ve güven taşır. Ham maksimum zorunlu LOB sonucudur; P0 interpolasyon
kullanmaz. Kalibre saha hatası ancak izinli ve bilinen yönlü testte ölçülebilir.
