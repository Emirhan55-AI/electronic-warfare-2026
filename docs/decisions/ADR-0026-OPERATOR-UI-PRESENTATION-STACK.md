# ADR-0026: Operatör Arayüzü Sunum Teknolojisi

- Durum: **Accepted**
- Karar tarihi: 2026-08-23
- İlgili paket: APP-E

## Bağlam

Mevcut PySide6/Qt Widgets uygulaması doğrulanmış iş akışlarını taşıyor, ancak tek
bir büyük pencere sınıfı, parçalı tema kuralları ve yoğun widget ağacı yeni yayın
arayüzünün uyarlanabilir yerleşim ve durum tabanlı geçiş gereksinimini pahalı hale
getiriyor. Tam C++ yeniden yazımı ise algoritma referans modellerini ikinci dilde
çoğaltma ve doğrulanmış davranışı taşıma riski doğuruyor.

APP-E, aynı hash-kilitli SigMF kaydından işlenen dört spektrum çerçevesini Qt
Widgets ve Qt Quick/QML prototiplerine verdi. Her teknoloji beş bağımsız süreçte,
5 ısınma ve 40 ölçüm güncellemesiyle 1280×720 offscreen yazılım çiziminde ölçüldü.

## Ölçüm sonucu

Kanıt: `results/evidence/app-e/ui-technology-comparison.json`

| Ölçüt, beş koşunun medyanı | Qt Widgets | Qt Quick/QML |
|---|---:|---:|
| Başlangıç | 35,92 ms | 244,29 ms |
| Güncelleme p95 | 1,16 ms | 1,61 ms |
| RSS | 67,36 MiB | 86,15 MiB |

QML başlangıç ve bellek maliyeti daha yüksektir. Bununla birlikte 10 Hz veri
güncelleme bütçesi 100 ms iken QML p95 değeri 1,61 ms'dir ve önceden tanımlanan üç
yeterlilik kapısını geçmiştir. Sonuç, offscreen yazılım çizimine aittir; hedef
bilgisayarın GPU performansı veya uzun süreli kararlılığı hakkında iddia değildir.

## Karar

APP-F sunum katmanı Qt Quick/QML ile geliştirilecektir. Python/PySide6; ViewModel,
kaynak adaptörleri, worker koordinasyonu ve doğrulanmış algoritma çağrıları için
korunacaktır. Tam C++ yeniden yazımı yapılmayacaktır.

Spektrum ve spektrogram verisi sunum sınırında bounded, görüntü çözünürlüğüne göre
indirgenmiş bir modelle QML'e aktarılır. 4096-bin bilimsel veri ve hesaplama sonucu
değiştirilmez; yalnız çizilecek nokta sayısı viewport genişliğine göre hazırlanır.
Canvas prototip için yeterlidir. APP-F hedef donanım profili Canvas kapısını
geçmezse özel Qt Quick çizim öğesi değerlendirilir.

C++ yalnız profiler ile gösterilmiş ve Python/Qt sınırında giderilemeyen bir
darboğaz için, dar kapsamlı uzantı olarak yeniden değerlendirilir.

## Sonuçlar

- ADR-0003'ün Qt Widgets sunum kararı bu ADR ile değiştirilir; Python algoritma ve
  worker sınırı geçerliliğini korur.
- QML ekranları ürün kaynak durumu dışında veri üretmez.
- Hareketler 120–180 ms görev geçişleriyle sınırlıdır; ölçüm grafikleri dekoratif
  hareket kullanmaz.
- APP-F çıkışında 1280×720, 1366×768, 1920×1080 ve %150 ölçekleme; klavye odağı,
  hareket azaltma, 10 Hz veri güncellemesi ve uzun süreli kaynak geçiş testi
  zorunludur.
- Hedef donanım ölçümü yapılmadan 60 FPS veya GPU hızlandırma iddiası kurulmaz.
