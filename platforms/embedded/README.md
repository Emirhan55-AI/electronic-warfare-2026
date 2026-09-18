# Zynq PS

## KTR-4.4 uyarlamalı P0DF profili — 16 Eylül 2026

`p0_amplitude_df.c` ürün profili tam tur zorunluluğu yerine PC'nin iki taraflı
lob sınırı ve 5° hassaslaştırma planından gelen en az sekiz farklı açıyı kabul
eder. Bir karşı-yön noktasıyla 3 dB ön/arka kapısı, 3 dB rakip tepe kapısı,
sabit alıcı/frekans bağı ve aynı-kare reddi korunur. P0DF-v1/P0FR-v1 tel biçimi
değişmemiştir; profil kimliği `P0_AMPLITUDE_DF_ADAPTIVE_V2` olmuştur.
Derlenen `p0-ed-service` (`126a916d…`) doğrulanmış ZedBoard'ın çalışan 47007
yoluna geçici kurulmuş ve sekiz P0DF hazır/ret sahnesini geçmiştir. Tekrarlanabilir
kayıt `results/evidence/phase09/amplitude-df-board-protocol-v2.json` içindedir.
SD açılış imajı değiştirilmedi; yeniden başlatmada eski profil geri gelir.

## KTR-4.4 P0PM-v4 yön kanalı gücü — 16 Eylül 2026

Yön bulma için sürümlenen `P0PM-v4`, dört karede aynı sabit kanalın PL UQ28.30
güç hücrelerini ARM'da ortalayıp sinyal + alıcı gürültüsü toplam dBFS değerini
verir. Normal P0PM'nin gürültü çıkarılmış güç ve anlamlılık kapısı değişmez.
PL 4096 FFT/OS-CFAR yolu değiştirilmemiştir; ağ köprüsü v4 paketini fail-closed
aktarır ve PC sayısal geri dönüşü yoktur. C protokol/çalışma zamanı ile Python
referans regresyonu geçti. Güncel ARM hizmeti ve köprü doğrulanmış ZedBoard'a
geçici kuruldu; P0PM-v4 fiziksel PL/ARM testi ve altı normal parametre sahnesi
47007 üzerinde geçti. SD imajı değişmediği için soğuk açılış kalıcılığı yoktur;
canlı RF ve yön RMS kabulü açıktır.

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

## PHASE-08 10 MS/s burst köprüsü — 14 Eylül 2026

P0IQ v2 ağ köprüsü 10 MS/s, 4096 kompleks CI8 algılama burst'ünü ayrı P0CQ
yetenek bitiyle kabul eder; parametre istekleri bu profilde kapalıdır. ARM
ikilisi `beb168b6…` hash'iyle gerçek kartta geçici yükleme, kontrollü RF ve
iki taraflı ofset koşularını geçti. Doğrulanmış önceki FIT kök dosya sistemi
yalnız bu köprü değiştirilerek yeniden paketlendi; `image.ub` `32245791…`
hash'iyle SD'den kontrollü yeniden başlatıldı. FPGA `operating`, hizmet
`20c151ea…`, köprü ve 47007 yetenek sorgusu açılıştan sonra geçti. Önceki imaj
SD'de hash bağlı yedektir. Tam PetaLinux yeniden derlemesi ve elektrik kesip
açılan soğuk başlangıç yapılmadı.

## PHASE-09 genlik tabanlı yön bulma — 11 Eylül 2026

`p0_amplitude_df.c`, 15° adımlı 24 açılık alan profilini, doğrusal güç
ortalamasını, kapsama/tepe/ön-arka/alıcı/frekans kapılarını ve dairesel RMS
hesabını ARM için taşır. Python referansıyla yedi sahnede sıfır fark elde edildi.
`P0DF-v1/P0FR-v1` CRC korumalı hizmet yolu geçici 47008 ve kalıcı 47007 uçlarında
gerçek ZedBoard `armv7l` üzerinde yedi sahneyi geçti. PetaLinux 5.679/5.679
görevle derlendi; SD `image.ub` yazıldı, kart yeniden başladı ve hizmetler açılışta
çalıştı. Canlı ürün açı başına dört ardışık kareyi P0PM-v4 sabit kanal toplam
güç yoluyla ölçer. Bu yeni sürümün kart kurulumu ile HackRF/yönlü anten ve
bilinen yönle fiziksel RMS kabulü açıktır.
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
