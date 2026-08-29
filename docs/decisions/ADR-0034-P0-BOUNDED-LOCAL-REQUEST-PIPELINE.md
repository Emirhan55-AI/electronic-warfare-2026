# ADR-0034 — P0 Sınırlı Yerel İstek Boruhattı

- Durum: Kabul edildi
- Kapsam: P0 kart içi `AF_UNIX/SOCK_SEQPACKET` ED hizmet akışı
- Bağlı gereksinimler: KTR-4.1, KTR-6
- Ön koşullar: ADR-0029, ADR-0030–0033

## Bağlam

ABI v3 tek-istek/tek-yanıt ölçümü fiziksel işleme yolunu doğru çalıştırmış,
ancak kalıcı PetaLinux imajındaki ek tekrarlanabilirlik kontrolünde beş koşunun
biri `487,986461398 kare/s` ile `488,28125 kare/s` sınırının `%0,0604` altında
kalmıştır. Koşu 4.096/4.096 kareyi sıfır hizmet, sıra, DMA ve aday düşürme
hatasıyla tamamlamıştır. Aşama profili aynı servis ikilisinin gerçek
`PL → DMA → ARM` hesap yolunu ortalama `1,928347 ms` ölçmüştür; dar boğaz,
hesap sonucundan çok her karede zorunlu senkron istemci/hizmet bağlam değişimidir.

Derleyici LTO denemesi güvenlik sertleştirmelerini korumasına rağmen beş
koşunun birinde yine kapıyı geçememiş ve ortalama hızı düşürmüştür; ürüne
alınmamıştır. Hizmet önceliğini `nice -10` yapmak 5/5 geçmiştir, fakat en düşük
pay yalnız `%0,105` olduğundan kalıcı çözüm kabul edilmemiştir.

## Karar

Kabul ve ürün istemci akışı tek yerel bağlantıda en fazla dört isteği sırayla
önden kuyruğa alır. Hizmet istekleri yine tek tek ve sırayla işler; FPGA, DMA,
detector, temporal durum, ABI v3 mesajı ve yanıt sırası değişmez. İstemci her
yanıtı beklenen kare kimliği, hizmet durumu, DMA `0x7` ve düşen aday sayısıyla
doğrular. İlk ölçüm karesindeki reset ve 64-kare ısınma sözleşmesi korunur.

Dört derinlik sabittir ve ölçüm JSON'unda `request_pipeline_depth` alanıyla
kanıta bağlanır. Bu derinlik, bilinen aday-paket yolunda yaklaşık 8 ms'lik
sınırlı uçtan uca kuyruk gecikmesi oluştururken Unix soket tamponlarını küçük
tutar. Başarı ölçütü, örnekleme hızı, 4096 örnekli kare ve 4.096-kare ölçüm
paydası değiştirilmez.

## Fiziksel kabul

Kaynaklar PetaLinux 2025.2 ile paket için 5.679/5.679, tam imaj için
6.090/6.090 görevle derlenmiştir. `image.ub` SHA-256 değeri
`da735531487a652cd98a30679f15d1d5706037e705d016ae81c886a9479dcd18`'dir.
Bu imaj SD karttan soğuk açılmış; FPGA `operating`, hizmet otomatik başlangıç,
CPU1 yerleşimi, ayrıcalık düşürme ve DMA izinleri doğrulanmıştır.

Bilinen karede 54 final aday ve beş karelik 2-of-3 olay yaşam döngüsü host
referansıyla alan alan aynıdır. Beş bağımsız 64+4.096 koşuda toplam
20.480/20.480 kare tamamlanmış; bütün hizmet, sıra, DMA ve aday düşürme
sayaçları sıfır kalmıştır. En düşük/ortalama/en yüksek hız
`508,759225230 / 509,458386609 / 509,884071480 kare/s`, en düşük gerçek-zaman
payı `1,041938893` olmuştur. Beş koşunun en yüksek p95 gecikmesi
`7,790058 ms`, en yüksek tekil gecikmesi `8,189214 ms` olarak
karakterize edilmiştir; ADR-0029 sonradan bir gecikme kabul eşiği eklemez.

## Sınır

Bu karar canlı HackRF alımı, USB/Ethernet taşıması, RF kalibrasyonu, saha
doğruluğu veya RF yayın işlevi kanıtlamaz. Sonuç deterministik bilinen kareyle
fiziksel kart içi yerel hizmet kapasitesidir.
