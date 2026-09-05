# Zynq PS

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
