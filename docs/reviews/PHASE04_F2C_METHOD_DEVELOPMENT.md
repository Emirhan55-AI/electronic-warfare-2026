# PHASE-04-F2C Yöntem Geliştirme Kaydı

## Karar

PHASE-04-F2C tamamlanmıştır. Ayrı v3 kestirimci yalnız altı açık geliştirme
seed'i üzerinde geliştirilmiş, kilitli 40 binding kontrolünün tamamını geçmiş ve
F2 binding/OOS seed'leri açılmadan yöntem kilidine bağlanmıştır.

Bu sonuç PHASE-04'ü veya ürün profilini doğrulamaz. F2D başlamamıştır; binding ve
OOS değerlendirmesi için ayrı kullanıcı onayı gerekir.

## Yöntem

- Gürültü reddi, span toplam gücüyle birlikte 64 referans hücresinden kestirilen
  gürültü seviyesinin belirsizliğini hesaba katan sabit eşikli bir anlamlılık
  kapısı kullanır. Enerji algılamada sabit yanlış alarm yaklaşımının eşik ve
  gürültü istatistikleriyle birlikte ele alınması gerektiği birincil çalışmayla
  uyumludur: [Energy detection with constant false alarm rate](https://link.springer.com/article/10.1186/s13638-021-01915-5).
- OBW, ITU-R SM.443-4'teki %0,5/%99,5 kümülatif güç kenarlarını korur. Ölçüm
  açıklığı, çözünürlük bant genişliği, gürültü ve tekrar sayısının doğruluğu
  etkilediği sınırları da korunmuştur: [ITU-R SM.443-4](https://www.itu.int/rec/R-REC-SM.443-4-200702-I/en).
- Sinyal alanı kararı, dört kareden çıkarılan zarf, faz, spektral ve normalize
  yüksek mertebe istatistiklerini aile-duyarlı prototiplerle değerlendirir.
  Yüksek mertebe çevrimsel istatistiklerin bilinmeyen faz ve zamanlamaya karşı
  dayanıklılığına ilişkin yöntem dayanağı:
  [Higher-order cyclic cumulants for modulation classification](https://web.njit.edu/~abdi/PaperOctavia.pdf).
- `Belirsiz` bir hata değil, düşük güven veya geniş bant gürültü-benzeri giriş
  için birinci sınıf abstention sonucudur. Runtime ground-truth kullanılmaz.

## Açık geliştirme sonuçları

Tam koşu altı seed, sekiz aile, dört SNR koşulu, 288 trial/aile ve 384 bağımsız
gürültü ölçümünden oluşur. Her ölçüm dört 4096 kompleks kare kullanır.

| Kontrol grubu | Sonuç |
|---|---:|
| Kilitli binding kontrolü | 40 / 40 geçti |
| Gürültü yanlış-geçerli | Her alan için 0 |
| Emisyon merkezi genel q95 | 0,612 bin |
| Taşıyıcı en düşük aile geçerliliği | %94,44 |
| Taşıyıcı yanlış karar oranı | %0,139 |
| OBW en düşük aile geçerliliği | %96,53 |
| OBW alt / üst kenar q95 | 1,442 / 1,411 bin |
| SNR genel q95 hata | 1,517 dB |
| Sinyal alanı 12 dB genel doğru | %100 |
| Sinyal alanı 6 dB genel doğru / yanlış | %93,95 / %0,55 |
| Belirsiz aile reddi | %100 |

OBW ablasyonunda değiştirilmeyen F1 tabanı 2.304 ölçümün 2.239'unu geçerli
sayarken v3 zamansal toparlama 2.259 ölçümü geçerli saymıştır. En düşük aile
geçerliliği %94,44'ten %96,53'e çıkmış; alt ve üst kenar q95 sınırları 2 binin
altında kalmıştır.

Taşıyıcı analizinde 12 dB uygulanamaz 1.440 ölçümde yanlış karar sayısı 28'den
2'ye düşürülürken en düşük uygulanabilir aile geçerliliği %94,44 kalmıştır.

## Kilit ve sınırlar

- Yöntem kilidi: `34e617f03cd898cd9e17f1699d09e299614c667ac67fb2ae3280f513b5372c23`
- Kalıcı sayısal model: 16.704 bayt
- Toplam kalıcı kestirim yükü: 50.788 bayt; sınır 65.536 bayt
- F1 yöntem ve tek seferlik sonuç dosyaları değiştirilmemiştir.
- F2 binding/OOS preimage'ları açılmamıştır.
- Canlı RF, dBm kalibrasyonu, FPGA/ARM yürütümü ve ürün kabulü iddia edilmez.

## Kanıt dosyaları

- `datasets/fixtures/phase04f2/domain-model-v3.json`
- `datasets/fixtures/phase04f2/method-lock-v3.json`
- `results/evidence/phase04f2/development-results-v3.json`
- `results/evidence/phase04f2/carrier-threshold-analysis-v3.json`
- `results/evidence/phase04f2/obw-ablation-v3.json`
