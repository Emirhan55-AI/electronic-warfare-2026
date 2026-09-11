# Zynq PS

## PHASE-09 genlik tabanlı yön bulma — 11 Eylül 2026

`p0_amplitude_df.c`, 15° adımlı 24 açılık alan profilini, doğrusal güç
ortalamasını, kapsama/tepe/ön-arka/alıcı/frekans kapılarını ve dairesel RMS
hesabını ARM için taşır. Python referansıyla yedi sahnede sıfır fark elde edildi.
`P0DF-v1/P0FR-v1` CRC korumalı hizmet yolu geçici 47008 ve kalıcı 47007 uçlarında
gerçek ZedBoard `armv7l` üzerinde yedi sahneyi geçti. PetaLinux 5.679/5.679
görevle derlendi; SD `image.ub` yazıldı, kart yeniden başladı ve hizmetler açılışta
çalıştı. Canlı ürün açı başına dört ardışık kareyi mevcut PL/ARM parametre güç
yoluyla ölçer. HackRF/yönlü anten ve bilinen yönle fiziksel RMS kabulü açıktır.
Ayrıntı:
[yön bulma durum sözleşmesi](../../docs/interfaces/SIGNAL_DIRECTION_FINDING_STATUS.md).

## PÇ-04 ilk üç parametre — 11 Eylül 2026

`p0_parameter_runtime.c` artık emisyon merkezi, gözlenen taşıyıcı, OBW %99,
dBFS güç ve SNR için F5 sayısal yöntemini ARM'da yürütür. `P0PM-v1` hizmet yolu
dört kayıtlı CI8 kareyi gerçek PL'den geçirir ve çözülmüş PL gücünü ARM'a verir.
PC kestirimci fallback'i yoktur. Altı fiziksel sayısal sahne kartta, 33 sahne
host C referansında geçti. PetaLinux 2025.2 imajı SD'ye yazıldı; üç yeniden
başlatmada FPGA, DMA modülü, hizmet ve ağ köprüsü otomatik başladı. dBm
kalibrasyon kapısı uygulanmıştır fakat gerçek alıcı kalibrasyonu yapılmadı.

## ST-06 dinamik FFT ve zayıf doğrulama — 11 Eylül 2026

Hizmet CPU0 çözümünde `p0_pl_os_cfar_decode_with_weak` kullanır. Pipeline,
zayıf hücreleri normal gruplamadan ayırıp 24/32 biriktirmesine bağlar.
Normal/grup ve geniş bant yolları korunur; hata durumunda zayıf durum da
geri alınır. Eski A biçimi normal karar desteğini korur, zayıf bilgi taşımaz.
ARM hedef derlemesi, Linux hizmet testi ve güncel fiziksel sayısal kart kabulü
geçmiştir. Üç uzun koşunun en düşüğü 507,587 kare/s'dir; HackRF/RF ve soğuk
açılış kabulü ayrıdır.
[Biçim, kaynaklar ve testler](../../docs/interfaces/DETECTION_TUNING_AND_SOURCE_GUIDE.md).

4096/8192/16384 XFFT, uzunluğa bağlı Hann, güç/CFAR, DMA ABI v3 ve ARM hizmet
ABI v4 birlikte uygulanmıştır. ARM 8192/16384 hücrelerini yerleşik 4096 olay
ızgarasına enerji korunarak indirger. Her boyut üç tekrarlı fiziksel sayısal
hız kapısını geçti. Aynı açılışta FFT küçültme XFFT/DMA kilitlenmesine yol
açabildiğinden sürücü bunu `EOPNOTSUPP` ile reddeder; yeniden başlatma 4096'a
döndürür. Pencere türü Hann olarak sabittir. Entegrasyon sınırı
[çalışma zamanı sözleşmesinde](../../docs/interfaces/DETECTION_RUNTIME_CONFIG_CONTRACT.md)
tanımlıdır.

## PÇ-01 sınırı — 7 Eylül 2026

KTR-4.2 / KTR-4.2-F1 arayüz ve güncel gözlem bağı uygulanmıştır.
Kestirimci, RTL ve kart hizmeti değişmedi; F5 ölçümü bilgisayarda kalır.
Yazılım kanıtı `results/evidence/phase08/parameter-workflow-v1.json` ve ZIP;
RF doğruluğu, dBm kalibrasyonu ve ARM taşıması bu kabulün dışındadır.

## PÇ-00 kart kimliği ve ölçüm sınırı — 7 Eylül 2026

Bilgisayardaki F5 ölçüm kaydı dört kart yanıtının sıra/kare/DMA bağını
denetler; çalışan hizmet/imaj özeti gözlenmediyse kart kimliğini bilinmiyor
tutar. Yerel kaynak veya eski fiziksel kanıt çalışan kart kimliği sayılmaz.
Bu adım ARM'a yeni parametre taşımadı ve kart yüklemesi yapmadı; ölçüm hâlâ
PC'dedir. KTR-4.2 PÇ-00 kanıtı `results/evidence/phase08/parameter-record-v1.json`
ve ZIP içindedir. ARM sayısal çekirdeğinin önceki kabul sınırı korunur.

## Parametre ARM entegrasyonu planı — 7 Eylül 2026

Mevcut `p0_parameter_runtime` emisyon merkezi, OBW99 kenarları/genişliği,
kanal dBFS ve SNR hesaplar. Taşıyıcı ve Analog/Sayısal alanı taşınmamıştır.
Kart hizmeti ölçüm isteğini destekler; QML canlı ölçümü bugün PC/F5 yolunu
kullanır. [Kontrollü devam planı](../../docs/plans/IMPLEMENTATION_ROADMAP.md)
önce dört alanın doğrulanmasını, sonra aynı yöntemlerin ARM'da birleşmesini
tanımlar. CPU0/CPU1 tespit yüküne ek bellek/gecikme ölçülmeden sürekli ölçüm
kabulü verilmez. Bu oturum MSVC C11 karşılaştırması geçti; yeni kart yükleme
veya fiziksel ARM testi yapılmadı. ST-06 kabulü açık kalır.

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

## Güncel ST-06 durumu — 5 Eylül 2026

PL'den her karede 32768 bayt işaretli UQ28.30 güç alınır; ARM dar adayları,
sekiz karelik geniş bant kararını ve olay yaşam döngüsünü birleştirir. Geçici
fiziksel yüklemede dijital işlev tanısı yapılmıştır, fakat ürün hızı 286–290
kare/s ile gerekli 488,28125 kare/s sınırının altındadır. SD soğuk açılışı ve
kontrollü RF kabulü açık kalır. Kaynak ve kanıt bağlantıları
[güncel durum belgesindedir](../../docs/interfaces/SIGNAL_DETECTION_STATUS.md).

## Önceki aday-paket sürümünün derleme kaydı

Bu dizin Zynq ARM/PetaLinux üzerinde çalışması hedeflenen, PC'yi algoritma motoru yapmayan PS sözleşmelerini taşır. `phase06i/` içindeki C ABI tanımı ve decoder kaynakları hostta doğrulanmıştır. Hann katsayı belleği yükleme düzeltmesini içeren güncel aday-paket XSA, ABI v2 DMA kernel modülü, P0 runtime ve ED hizmeti PetaLinux 2025.2 ile birlikte derlenmiş; tam imaj 6.090/6.090 görev kapısını geçmiştir. SHA-256 doğrulanmış SD paketi hazırdır. Bu sonuç düzeltilmiş imajın fiziksel ZedBoard açılışını, pozitif-sinyal DMA aday üretimini, canlı RF çalışmasını veya kalibre doğruluğu kanıtlamaz; kart kabulü ayrı kapıdır.
