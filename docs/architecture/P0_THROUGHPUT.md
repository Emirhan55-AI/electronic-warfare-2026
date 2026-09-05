# P0 FPGA Akış Hızı Gerçekliği

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

## Güncel ST-06 ürün sonucu — 5 Eylül 2026

2 MS/s / 4096 örnek için gereken hız 488,28125 kare/s'dir. Bağımsız
DMA/güç çözme/geniş bant profili 551,22–577,68 kare/s ölçmüştür; tam ürün
dar aday gruplama, olay yaşam döngüsü ve Ethernet yanıtlarını da içerir.
Fiziksel ürün denemeleri 287,27 ve 286,45 kare/s; PC çözümlemesi ölçüm
dışında 289,76 kare/s vermiştir. Hız kapısı başarısızdır. Kartın ARM tespit
iş parçacığı bu son koşuda CPU1'in 1469 toplam sayacına karşılık 1435
CPU sayacı tüketmiştir. Alt adım profili çıkarılmadan bu maliyet tek bir
algoritmaya bağlanmaz; kuyruk büyüterek veya veri atarak kabul üretilemez.

Bu ölçüm dijital I/Q'nun Ethernet→PS/DMA→PL→ARM→Ethernet yoludur;
HackRF/USB ve UI içermez. Güncel ST-06'da geniş bant ARM'dedir.
`results/evidence/phase08/st06-product-board-diagnostic-v1.json` ham girdiler
ve yanıtları bağlar. Aşağıdaki ölçümler önceki sürümlerin tarihsel kapsamıdır.

## Önceki ölçümler

> 31 Ağustos 2026: İlk iki bölüm tarihsel alt blok kapasitesidir; güncel tam
> tespit kapasitesi olarak kullanılamaz. OS-CFAR ve geniş bant kurtarma artık
> PL'dedir. Güncel 2 MS/s hizmet ölçümü aşağıdaki fiziksel sürekli-hız bölümünde,
> kapsam sınırı [durum belgesinde](../interfaces/SIGNAL_DETECTION_STATUS.md) bulunur.
> ADR-0037 RTL simülasyonunda final azaltıcıyı 45.557 çevrimde tutmuştur;
> güncel sentez ve fiziksel 2 MS/s hizmet ölçümü yeniden yapılmadan aşağıdaki
> kart marjı yeni kaynaklara aktarılmaz.

## Hann → FFT → lineer güç

P0 çalışma saati 50 MHz'dir. Üç blok da kararlı durumda bir karmaşık
örnek/çevrim AXI akışını kabul edecek biçimde tasarlanmıştır. Bu nedenle PL
aritmetik üst sınırı:

- Saat: 50.000.000 çevrim/s
- Kararlı durum çevrim/frame: 4096
- En yüksek frame/s: 12.207,03125
- En yüksek karmaşık örnek/s: 50.000.000

PHASE-06D davranışsal kanıtında FFT wrapper ilk girişten ilk çıkış transferine
8348 çevrim gecikmiştir. Bu başlangıç gecikmesidir; sürekli akışta frame başına
4096 çevrim kapasitesinin yerine kullanılmaz.

HackRF'ın P0 için izin verilen en yüksek 20 MS/s akışı PL aritmetik üst sınırının
%40'ıdır; salt PL aritmetik kapasitesi 2,5 kat pay sağlar. Buna rağmen PC
Ethernet, PS DDR ve iki yönlü DMA bant genişliği kartta
ölçülmediğinden uçtan uca 20 MS/s iddiası yoktur.

İlk 100 MHz uygulama denemesi route edilmiş, fakat WNS −6,541 ns ve TNS
−507,301 ns ile setup timing'i geçememiştir. Bu denemede bitstream üretilmemiştir.
50 MHz seçimi bu sonucu saklamak veya timing'i olduğundan iyi göstermek için
değil, 20 MS/s gereksinimini hâlâ aşan gerçek çalışma hedefini tanımlamak içindir.
Vivado 2025.2 post-route sonucu WNS +0,258 ns, TNS 0, WHS +0,025 ns, THS 0 ve
sıfır failing endpoint ile timing'i kapatmıştır. Bu PL aritmetik kapasite kanıtı,
kart üzerinde Ethernet/DDR/DMA akış hızı ölçümü değildir.

## PHASE-06G detector borcu

PHASE-06G tek frame buffer kullanır; input toplama sonrasında processing ve replay
süresince `TREADY` düşer. Kanıtlanan mimari sayıları 4096 giriş çevrimi, son
girişten ilk çıkışa 476.131 saat aralığı ve 4096 çıkış çevrimidir. Yaklaşık
484.322 çevrim/frame üzerinden 50 MHz'de teorik üst sınır yaklaşık 103,24 frame/s
veya 422.859 karmaşık örnek/s'dir. Post-detector 50 MHz timing doğrulanmadığı için bu
yalnız mimari üst sınırdır, canlı detector hızı değildir. P0 yetkili tespit kararı
bu nedenle PS OS-CFAR'dır.

## Fiziksel sürekli-hız ölçümü

ADR-0029 ile kilitlenen 2 MS/s profilinde (64 ısınma ve 4096 ölçüm karesi)
Güncel aday-paket ZedBoard `PL → DMA → ARM` hizmet yolu, kompakt ABI v3,
dört derinlikli sınırlı istek kuyruğu ve çekirdek yerleşimiyle beş bağımsız
4096-kare koşusunun tamamını kalıcı SD imajından geçmiştir.
Toplam 20.480/20.480 karede her yanıtta DMA `0x7`; hizmet, sıra ve aday düşürme
hatası sıfırdır. Ölçülen en düşük/ortalama/en yüksek hız sırasıyla
`508,759225230 / 509,458386609 / 509,884071480 kare/s`, gerekli alt sınır
`488,28125 kare/s` ve en düşük gerçek-zaman marjı `1,041938893` olmuştur.
Kilitli kart içi 2 MS/s hizmet kapısı tekrarlanabilir biçimde kapanmıştır.

Güncel ayrıştırma, aday-paket çekirdek yolunun ortalama `1,928347 ms` ile
hesaplama bütçesine sığdığını; tek-istek/tek-yanıt akışındaki kalan kaybın IPC
ve zamanlayıcı bağlam değişiminden geldiğini göstermiştir. ADR-0034'teki dört
derinlikli sıra bu maliyeti kareler arasında örter. v3 yalnız
oluşan olayları taşır; bilinen 54-olay karesinde yanıt 3.740 bayttır. v1/v2
uyumluluğu ve yük CRC'leri korunur; v3 aynı çekirdekteki `SOCK_SEQPACKET`
güvencesiyle başlık CRC'sini korur. DMA kesmeleri CPU0'da kalırken hizmet CPU1'e,
kabul istemcisi CPU0'a sabitlenir. Kanıt
`results/evidence/p0/ed-throughput-physical-acceptance.json` dosyasındadır.
Güncel kaynaklar PetaLinux 2025.2'de 5.679/5.679 paket ve 6.090/6.090 tam
imaj göreviyle yeniden derlenmiştir; yeni `image.ub` SHA-256 değeri
`da735531487a652cd98a30679f15d1d5706037e705d016ae81c886a9479dcd18`'dir.
Bu imaj fiziksel kartta soğuk açılmış; FPGA `operating`, kurulu ikili hashleri
derleme çıktısıyla aynı ve 54-aday işlevsel yaşam döngüsü bit-doğru bulunmuştur.
Aynı kalıcı imajdaki beş 64+4.096 kabul koşusu toplam 20.480/20.480 kare,
sıfır hata, en düşük `508,759225230 kare/s` ve `1,041938893` marjla geçmiştir.
Kalıcı imaj kanıtı
`results/evidence/p0/ed-service-v3-cold-boot-acceptance.json` dosyasındadır.

## ADR-0032 doğrulanmış aday kısa yolu

ADR-0032 ile PL decoder sonrasında aday gruplamada yinelenen güç/karar giriş
doğrulaması kaldırılmış, strict dış API korunmuştur. Host C doğrulamasında
strict ve decoder-sonrası trusted yolun karar, aday, gürültü, eşik ve recovery
çıktıları sıfır fark vermiştir. Aday-paket DMA sürücüsü ve yerel hizmet kaynak
entegrasyonu hostta, PetaLinux imajında ve fiziksel kartta doğrulanmıştır.
Güncel kalıcı imaj ADR-0034'teki sınırlı istek boruhattıyla aynı 64+4.096
kapısını beş kez geçmiştir.

Geçici ARM ölçümünde ADR-0032 ikilisi mevcut kernel/driver/PL üzerinde
4096/4096 kareyi sıfır hatayla tamamladı; ARM `2,723289 ms`, birleşik yol
`4,173240 ms` ölçüldü. Bu tarihsel ara sonuç ADR-0031'e göre hızlanma
göstermemiştir; sonraki kalıcı imaj ve fiziksel kabul yukarıda ayrıca kayıtlıdır.

## ADR-0033 seyrek çok ölçekli aday sınırı

Kilitli 64+4.096 fiziksel ayrıştırmada OS aday gruplama `0,635712 ms`, OS
gruplamayı içeren çok ölçekli tespit `1,551391 ms`, ARM `2,654336 ms` ve DMA
`1,443685 ms` ölçüldü. Yalnız gruplamayı kaldıran ortalama ARM alt sınırı
`2,018624 ms` ile `2,048 ms` bütçesine yalnız `%1,455` marj bırakır. Çok ölçekli
tespit tamamen kaldırıldığında bile ardışık DMA+ARM tahmini `2,546630 ms` olur.
Bu nedenle ADR-0033, sürekli tespit karesinde final çok ölçekli adayların
PHASE-06I seyrek paketiyle taşınmasını ve DMA/ARM örtüşmesini birlikte zorunlu
kılar. Tam güç/IQ yalnız açık parametre ölçüm yolunda korunur. Bit-doğru referans
14 karede sıfır aday/metadata/packet farkı vermiştir. Paralel median RTL
alt-aşaması beş kare/80 bölgede sıfır fark ve en fazla `29.756` çevrim vermiştir;
Bütünleşik enerji/fusion RTL'si ve final fusion, Zynq-7020 üzerinde synthesis,
place/route ve 50 MHz setup/hold kapısını `WNS=+0,670 ns`, `WHS=+0,053 ns`,
sıfır timing ihlali ve sıfır route hatasıyla geçmiştir. Bu sonuç
synthesis-only wrapper'a aittir. Final reducer → PHASE-06I AXI64 packetizer
bağlantısı sekiz kare/63 aday/379 beat ve 37 backpressure kararlılık kontrolüyle
bit-doğru geçmiştir. CI8 girişten FFT/güce ve aynı packetizer sınırına uzanan
`p0_candidate_dsp_runtime_top` hiyerarşisi compile-only olarak doğrulanmıştır;
vendor FFT işlevsel simülasyonu, güncel ADR-0037 kaynaklarıyla Vivado
sentez/route/bitstream, DMA/driver ve fiziksel kart kapıları hâlâ açıktır.
