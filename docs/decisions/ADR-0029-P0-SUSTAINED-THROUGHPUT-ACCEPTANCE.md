# ADR-0029 — P0 Sürekli İşleme Hızı Kabulü

- Durum: Kabul edildi
- Kapsam: P0 fiziksel PL→DMA→ARM çalışma zamanı
- Bağlı gereksinim: KTR-4.1

## Sorun

Tekil fiziksel kare kabulü, veri yolunun ve algoritmanın kart üzerinde doğru
çalıştığını gösterir; örneklerin kesintisiz geldiği bir görevde bütün karelerin
zamanında işlenebildiğini göstermez. P0 profili 2 MS/s kompleks `ci8` giriş ve
4096 kompleks örnekli kare kullanır. Bu nedenle gerçek-zaman alt sınırı
`2.000.000 / 4096 = 488,28125 kare/s` olur.

Bu kabul canlı RF doğruluğunu, USB/Ethernet taşımayı veya saha tarama hızını
ölçmez. Yalnız ZedBoard üzerindeki yerel hizmetin bir istek için
`ci8 → PL Hann/FFT/güç → DMA → ARM tespit → 2/3 olay` yolunu sürekli
tamamlayabilmesini sınar.

## Karar

Ürün hizmetiyle aynı yerel `AF_UNIX/SOCK_SEQPACKET` ABI'sini kullanan ayrı bir
`p0-ed-throughput-run` kabul aracı sağlanır. Araç her kare için bağlantı kurma,
istek gönderme, fiziksel DMA/PL işlemi, ARM işleme ve yanıt doğrulamayı ölçüm
süresine dahil eder. Ölçüm, hizmetin mevcut tek-istek/tek-bağlantı davranışını
gizlemez veya özel bir hızlı yol kullanmaz.

Araç yalnız tam 8192 baytlık bir `ci8` kabul karesini tekrarlar. İlk ölçülen
karede temporal durum açıkça sıfırlanır. Her yanıtın ABI, kare kimliği, hizmet
durumu, DMA tamamlanma bayrakları ve aday düşürme sayısı doğrulanır. Gecikmeler
monotonik kart saatiyle ölçülür ve toplam hızla birlikte JSON olarak yayımlanır.

## Önceden kilitlenen fiziksel kabul kapıları

Sonuç görülmeden önce aşağıdaki kapılar kilitlenmiştir:

- Girdi profili: 2.000.000 kompleks örnek/s, 4096 kompleks örnek/kare.
- Isınma: 64 kare; ölçüme dahil edilmez.
- Ölçüm: 4096 ardışık kare.
- Tamamlanan istek: 4096/4096.
- Hizmet, protokol, kare sırası ve DMA bayrağı hatası: `0`.
- Her başarılı yanıtta DMA bayrakları: `0x7`.
- Aday kapasitesi aşımı nedeniyle düşürülen aday: `0`.
- Ölçülen toplam hız: en az `488,28125 kare/s`.
- Giriş ve üretilen sonuç dosyaları SHA-256 ile bağlanır.

Ortalama hız kapısı geçmeden p95/p99 gecikme yalnız karakterizasyon olarak
raporlanır; sonuçtan sonra ek bir gecikme eşiği uydurulmaz. Kapı geçmezse test
veya örnekleme hızı değiştirilmez. Darboğaz profillenip yeni mimari karar ve ayrı
fiziksel kabul yapılır.

## Güvenlik ve iddia sınırı

Kabul koşusu sonrasında darboğazı ayırmak için aynı kartta yalnız
`p0-dma-run` 100 kez çalıştırılmış ve 0,666 s toplam (yaklaşık 6,66 ms/kare)
karakterizasyonu elde edilmiştir. Bu ek ölçüm kabul kapısı değildir; yalnızca
2,048 ms/kare bütçesinin DMA katmanında dahi aşıldığını gösterir. Tam hizmet
ölçümü 50,67380 kare/s sonucunu değiştirmez.

Araç RF yayın işlevi içermez. Yerel hizmet izinlerini, `/dev/p0-dma` sahipliğini
ve sürümlü ABI'yi değiştirmez. Başarılı sonuç yalnız deterministik kabul karesiyle
kart içi sürekli işlem kapasitesidir; canlı HackRF, RF duyarlılığı, dBm
kalibrasyonu, Ethernet aktarımı veya saha doğruluğu değildir.
