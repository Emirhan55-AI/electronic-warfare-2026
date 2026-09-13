# Sistem Temel Çizgisi

## Yalnız ED ürün kapsamı — 13 Eylül 2026

Güncel ürün yalnız alıcı tabanlı Elektronik Destek (ED) sistemidir. İkinci
HackRF gerektiğinde bağımsız bir ED alıcısı olarak kullanılabilir. ET/TX görevi,
uygulama katmanı, yapılandırması veya planlanan ürün yeteneği yoktur. Eski ET
kayıtları yalnız tarihsel karar ve kanıt niteliğindedir; ADR-0044 güncel kapsamı
belirler.

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

## Durum

Bu belge PHASE-00 sistem hedefini ve donanım sınırlarını tanımlar. P0/PHASE-07
çalışmalarında gerçek DMA, PetaLinux, ARM ve FPGA zinciri fiziksel olarak
çalıştırılmıştır; eski kabul yalnız kayıttaki kaynak/imaj sürümünü kapsar.
5 Eylül 2026 itibarıyla etkin çalışma PHASE-08 / ST-06 sinyal tespitidir.
Güncel PL/ARM ürün imajı derlenmiştir; bu imajın soğuk açılışı, fiziksel ürün
hizmeti ve kontrollü kör RF kabulü açıktır. Güncel kanıt ve aşama
[sinyal tespiti durum belgesinde](../interfaces/SIGNAL_DETECTION_STATUS.md) tutulur.

Aynı gün geçici fiziksel yüklemeyle dijital dar/geniş olay tanısı yapılmıştır.
Ürün hızı 286–290 kare/s ile gereken 488,28125 kare/s altında kalmıştır;
ARM tespit iş parçacığı darboğazdır. Bu nedenle fiziksel ürün kabulü kapanmaz.

## Fiziksel bileşenler ve görev ayrımı

| Bileşen | Planlanan görev |
|---|---|
| HackRF-1 + PortaPack H2 | ED/RX, kayıt ve canlı I/Q kaynağı |
| HackRF-2 + PortaPack H2 | İkinci bağımsız ED/RX kaynağı (`ED_RX_SECONDARY`) |
| Laptop | HackRF USB erişimi, kayıt, veri aktarımı ve kullanıcı arayüzü |
| ZedBoard PS | Gigabit Ethernet, kontrol, DDR ve PL veri aktarımı |
| ZedBoard PL | Gerçek zamanlı FPGA DSP işlemleri |
| Antenler ve RF kabloları | Banda ve ED alma görevine uygun bağlantılar |

Referans donanım; geniş bant omni antenleri, alt/orta bant teleskobik anteni, FOX 727 dual-band Yagi'yi, üst bant yönlü UWB antenleri ve GPS L1 aktif antenini içerir.

## Hedef veri ve geliştirme akışı

Giriş veri yolu `SigMF veya HackRF-1 → PC kanal seçici → Gigabit Ethernet →
ZedBoard PS → DDR/AXI DMA → ZedBoard PL` biçimindedir. ST-06 ürününde PL,
Hann/FFT/güç/OS-CFAR hücre kararını üretir; her karede 4096×64 bit işaretli
güç kelimesi S2MM üzerinden ARM'a döner. ARM geniş bant, gruplama ve temporal
sonuçlarını PC'ye gönderir. Önceki seyrek aday-paket mimarisi tarihsel P0
tasarımıdır. Host alım, kanal seçimi ve görsel FFT de çalıştırır; ürün tespit
kararı doğrulanmış kart yanıtına bağlıdır.

ED işlevleri sinyal tespitinden başlayarak parametre çıkarımı, yön bulma, konum
ve dinlemeye doğru sıralı geliştirilecektir. ET/TX işlevleri ürün kapsamı
dışındadır.

Yön bulma; yönlü antenin elle döndürülmesi ve her açı için göreli güç/PSD ölçümüyle planlanır. Açı ve ölçüm konumu kullanıcı tarafından elle girilecektir. Yaklaşık konum, bilinen iki ölçüm noktasından elde edilen LOB doğrularının birleştirilmesine dayanacaktır.

## KTR'ye göre mimari değişiklikler ve sınırlar

KTR 4.1 sinyal tespit zinciri korunur. Buna karşılık bladeRF, KrakenSDR, faz
uyumlu çok kanallı alıcı, motorlu anten, PA, kuplör ve RF çıkış zinciri referans
sistemde yoktur. Bu nedenle MUSIC veya faz karşılaştırmalı DF uygulanamaz ve
otomatik anten taraması iddia edilmez. ET ise bir sınırlama veya gelecek planı
değil, kullanıcı kararıyla ürün kapsamı dışıdır.
