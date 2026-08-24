# PHASE-04-F3A F2D Başarısızlık Analizi

## Karar

F2D sonucu yeniden çalıştırılmadan ve F2 kaynakları değiştirilmeden üç kök neden
sınıfı doğrulanmıştır. Analiz, saklanan binding/OOS metriklerini kilitli scorer
ile yeniden puanlamış ve yalnız eski açık geliştirme seed'lerinde seed-bazlı
teşhis çalıştırmıştır.

## Yeniden üretim

- Binding kararı: geçti, 40/40 kontrol
- OOS kararı: başarısız, 22/24 kontrol
- Karşılaştırma kararı: başarısız
- Altı açık seed'in taşıyıcı ve OOK 6 dB sayımları saklanan F2C geliştirme
  toplamlarıyla birebir eşleşti.
- F2 yöntem, protokol, runner ve sonuç dosyalarının SHA-256 değerleri F3A
  kanıtına kaydedildi.

## F3A-01 — OOK taşıyıcı seed genellemesi

| Popülasyon | Geçerli / toplam | Oran |
|---|---:|---:|
| Açık geliştirme | 272 / 288 | %94,44 |
| Binding | 176 / 192 | %91,67 |
| OOS | 53 / 64 | %82,81 |

OOS kapısı en az 56/64 (%87,5) gerektirir. Açık seed'lerde 48 ölçüm başına
geçerli sayıları `44, 43, 46, 47, 46, 46` olmuştur. En zayıf açık seed 43/48
(%89,58) ile kapının yalnız bir ölçüm üstündedir. Aggregate geliştirme oranı,
seed-bazlı alt sınır için yeterli güvenlik payı sağlamamıştır.

## F3A-02 — Sinyal alanı yanlış karar güvenlik payı

| Popülasyon | Doğru | Yanlış | Abstention | Toplam |
|---|---:|---:|---:|---:|
| Açık geliştirme | 253 | 8 | 27 | 288 |
| Binding | 169 | 4 | 19 | 192 |
| OOS | 50 | 3 | 11 | 64 |

OOS kapısı en fazla 2 yanlış kesin karara izin verir. Açık seed başına yanlış
karar sayıları `2, 2, 1, 2, 0, 1` olmuştur. Aggregate geliştirme yanlış oranı
%2,78 ile OOS oran sınırı %3,125'in altında görünse de %95 Wilson üst sınırı
%5,38'dir. Bu nedenle aggregate oran geçişi, OOS sayım kapısı için istatistiksel
güvenlik payı oluşturmamıştır.

Yeni yöntemde öncelik daha fazla kesin karar vermek değil, Analog yönüne kayan
sınırdaki OOK örneklerini `Belirsiz` sonucuna taşımaktır. Doğru karar minimumu ve
yanlış karar maksimumu birlikte sınanmalıdır.

## F3A-03 — Ortak OOK sınırı

İki OOS ihlalinin de OOK ailesinde oluşması, açık geliştirme kapsamının OOK zarf
ve temporal çeşitliliğini yeterince temsil etmediğini gösterir. Bununla birlikte
taşıyıcı çizgisi gözlemi ile Analog/Sayısal/Belirsiz kararı aynı çıktı değildir;
F3'te ayrı özellik, abstention ve kabul kapıları korunmalıdır.

## Zorunlu sonraki eylemler

1. F1/F2 popülasyonlarından tamamen ayrılmış yeni açık seed kataloğu oluşturmak.
2. V4 yöntemi başlamadan yeni binding/OOS commitment'larını kilitlemek.
3. F2 doğruluk eşiklerini gevşetmemek.
4. OOK taşıyıcı için seed-bazlı minimum, alan kararı için seed-bazlı yanlış kesin
   karar maksimumu tanımlamak.
5. Yöntemden önce ayrılmış diagnostiklerde temporal taşıyıcı kanıtı ve OOK zarf
   çeşitliliğini açıkça kapsamak.

## İddia sınırı

Bu belge yeni yöntem, F2 yeniden koşusu, canlı RF, FPGA/ARM kabulü veya ürün
başarısı değildir. F3B başlamamıştır.
