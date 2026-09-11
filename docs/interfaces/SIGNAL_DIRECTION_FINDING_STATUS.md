# Yön bulma: güncel durum ve kabul sınırı

## 11 Eylül 2026 — 5.1.4 genlik tabanlı yön bulma başlangıcı

Kullanıcı KTR §5.1.4 için genlik tabanlı yön bulma yöntemini seçmiş ve
PHASE-09 çalışmasını açıkça başlatmıştır. 5.1.3 dinleme kabul kapıları kapanmış
sayılmaz; kullanıcı önceliğiyle yön bulma çalışması açılmıştır.

Ürün yöntemi tek HackRF ve elle döndürülen uygun yönlü anten içindir. Aynı
doğrulanmış hedef kanalının farklı fiziksel anten açılarında ölçülen göreli
güçleri karşılaştırılır. Zorunlu sonuç ölçülmüş açılar arasındaki ham maksimum
LOB'dur; faz uyumlu DoA, menzil veya verici konumu üretilmez.

Yön girişi bütün 2 MHz görünür bandın ortalama gücünden ayrılmıştır. Canlı
ölçümde aynı confirmed hedefin dört ardışık CI8 karesi sabitlenir; kartın mevcut
P0PM yolu her kareyi PL Hann → 4096 FFT → güç zincirinden geçirir ve ARM'ın
gürültüsü çıkarılmış kanal dBFS sonucunu açı kaydı olarak kullanır. İlk açıda
hedef kanal aralığı sabitlenir; sonraki açılarda aynı frekans aralığı ve LNA/VGA
bağı korunur. Her ölçümden sonra alım yeniden başlar ve hedef tekrar confirmed
olmadan yeni açı kaydedilemez. Kayıt hedef frekansı, kanal genişliği, kaynak,
alıcı ayar bağı ve kaynak kare kimliğini taşır; aynı kare iki farklı açı olarak
kullanılamaz.

`P0_AMPLITUDE_DF_FIELD_V1` profili aşağıdaki kapıları uygular:

- 0°–345° arasında 15° adımlı 24 farklı açı,
- en büyük dairesel açı boşluğu en çok 15°,
- ana lob dışındaki rakip tepeye göre en az 3 dB belirginlik,
- ölçülen karşı yöne göre en az 3 dB ön/arka ayrımı,
- sabit hedef frekansı, kanal ve alıcı ayar bağı,
- yalnız ölçülmüş açıdan ham maksimum; interpolasyon yok.

Deterministik 0°–359° sayısal sahnelerde 15° ızgara 360/360 `LOB HAZIR`
üretmiş; RMS `4,377975°`, p95 `7°`, en büyük hata `8°` olmuştur. 45° ve 30°
ızgaralar daha düşük örnek sayısı nedeniyle fail-closed reddedilmiştir. Açı
kümelenmesi, ön/arka belirsizliği ve alıcı ayarı değişimi kendi ret durumlarını
üretmiştir. Kanıt:
[`amplitude-df-numeric-v1.json`](../../results/evidence/phase09/amplitude-df-numeric-v1.json).

Bu sayılar bağımsız deterministik anten deseni örnekleridir; anten veya saha
doğruluğu değildir.

Alan profilinin taşınabilir C çekirdeği eklendi. Yedi hazır/ret sahnesinde
Python referansıyla bütün ara metrik ve durumlar sıfır sayısal farkla eşleşti;
dairesel RMS ve aynı-kare tekrarı ayrıca sınandı. Cortex-A9 hard-float ikilisi
gerçek ZedBoard `armv7l` işlemcisinde çalıştı. CRC korumalı `P0DF-v1/P0FR-v1`
protokolü, kart hizmeti ve ağ köprüsü önce 47008 geçici uçta, ardından yeniden
başlatılmış kalıcı 47007 uçta yedi sahnenin tamamını ARM'da doğru sonuçlandırdı.
PetaLinux 5.679/5.679 görevi tamamladı. Karttaki kalıcı `image.ub` SHA-256 değeri
`1f7899b537e765d3f77e040221a26553b5abb54ca8d2d87908f3e8a0d94e8705`;
`BOOT.BIN` değişmeden
`de0d333ad4b5b87b17a9c675018cf079a8e4c37e1e899c92c68b8c4337e4f61c`
kaldı. Önceki imaj SD kartta tarihli yedek altında korunmuştur. Kanıtlar:

- [`amplitude-df-arm-equivalence-v1.json`](../../results/evidence/phase09/amplitude-df-arm-equivalence-v1.json)
- [`amplitude-df-board-protocol-v1.json`](../../results/evidence/phase09/amplitude-df-board-protocol-v1.json)
- [`amplitude-df-persistent-image-v1.json`](../../results/evidence/phase09/amplitude-df-persistent-image-v1.json)

Canlı ürün 24 açı tamamlandığında başarı veya ret kararını kart ARM'ından alır;
ARM yanıtı olmadan nihai LOB göstermez. Saha öncesi yazılım, PL/ARM ölçüm bağı ve
kalıcı kart imajı tamamlanmıştır. HackRF bu koşuda bağlı olmadığı için fiziksel
anten açısı referansı, yönlü anten deseni, kontrollü bilinen yön deneyi, çok
yollu ortam etkisi ve gerçek derece RMS kabulü açıktır. Bu yüzden henüz fiziksel
yön doğruluğu iddia edilmez.

Bilimsel temel, KrakenRF karşılaştırması, hata bütçesi ve deney sırası
[`AMPLITUDE_DIRECTION_FINDING_RESEARCH_20260911.md`](../reviews/AMPLITUDE_DIRECTION_FINDING_RESEARCH_20260911.md)
içindedir.
