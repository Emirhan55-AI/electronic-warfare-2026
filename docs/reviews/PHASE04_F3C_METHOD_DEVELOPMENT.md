# PHASE-04-F3C Yöntem Geliştirme Kaydı

## Karar

PHASE-04-F3C tamamlanmıştır. Ayrı v4 kestirimci yalnız sekiz açık geliştirme
seed'i üzerinde geliştirilmiş, korunan 40 temel kontrolün ve F3'e özgü 14 risk
kontrolünün tamamını geçmiştir. Yöntem, yeni binding/OOS seed'leri açılmadan
önce kaynak ve kanıt özetleriyle kilitlenmiştir.

Bu sonuç ürün başarısı veya PHASE-04 kapanışı değildir. F3D başlamamıştır;
binding/OOS değerlendirmesi için ayrı kullanıcı onayı gerekir.

## Yöntem dayanağı

- v3'ün enerji algılama, emisyon merkezi, OBW99, güç ve SNR yöntemleri
  değiştirilmeden korunmuştur.
- Taşıyıcı kararı, ortalama spektrumdaki çizgi belirginliği ve güç payını dört
  karenin her birindeki zamansal destekle birleştirir. Yüksek spektral entropi
  ile negatif zarf çarpıklığının birlikte görüldüğü çizgi-benzeri sayısal
  artifaktlar reddedilir.
- Sinyal alanı kararı, v3 karmaşık zarf/faz istatistiklerine normalize
  zarfın dönüşüm spektrumundan yüksek bant güç oranı ve spektral merkez ekler.
  Sınıflandırma, seed dışarıda bırakmalı prototip geliştirmesi ve mesafe/marj
  reddi kullanır.
- Zarf dönüşümleri ve bu dönüşümlerde oluşan spektral çizgilerin otomatik
  modülasyon sınıflandırmasında kullanımı Reichert'in çalışmasıyla uyumludur:
  [Automatic classification of communication signals using higher order statistics](https://doi.org/10.1109/ICASSP.1992.226530).
- Zarf değişim ölçülerinin analog/sayısal modülasyon ayrımındaki dayanağı:
  [Identification of modulation type with a view to demodulation](https://doi.org/10.1016/0165-1684(89)90093-5).

Literatür yöntem ailesini destekler; sayısal eşikler makaleden kopyalanmamış,
yalnız F3 açık geliştirme kataloğunda ve önceden kilitlenmiş kapılar altında
seçilmiştir. Runtime ground-truth kullanılmaz.

## Açık geliştirme sonuçları

Tam koşu sekiz seed, sekiz aile, dört SNR koşulu, 384 trial/aile ve 512 bağımsız
gürültü ölçümünden oluşur. Her ölçüm dört adet 4096 kompleks kare kullanır.

| Kontrol grubu | Sonuç |
|---|---:|
| Korunan temel kontrol | 40 / 40 geçti |
| F3 seed/risk kontrolü | 14 / 14 geçti |
| Gürültü yanlış-geçerli | Her alan için 0 |
| Taşıyıcı 12 dB genel geçerlilik | %97,05 |
| Taşıyıcı en düşük aile geçerliliği | %93,49 |
| Uygulanmayan ailelerde yanlış taşıyıcı | 0 / 1.920 |
| OOK taşıyıcı en düşük seed geçerliliği | 46 / 48 |
| OOK taşıyıcı en düşük kare desteği | 189 / 192 |
| Sinyal alanı 12 dB genel doğru / yanlış | %99,14 / %0 |
| Sinyal alanı 6 dB genel doğru / yanlış | %91,74 / %0,074 |
| OOK 6 dB en düşük seed doğru / yanlış | 44 / 48, yanlış 0 |
| Belirsiz aile reddi | %100 |

OOK taşıyıcı tespitinde 384 açık geliştirme ölçümünün 375'i geçerli sonuç
vermiştir. BPSK, QPSK, 2-FSK, burst-QPSK ve geniş bant gürültü-benzeri 1.920
uygulanamaz ölçümün hiçbirine taşıyıcı çizgisi atanmamıştır.

Sinyal alanı kararında 6 dB'de bütün aileler birlikte 2.688 değerlendirmenin
%91,74'ünü doğru sınıflandırmış, %0,074'ünde yanlış kesin karar vermiştir. OOK
özel risk sayımında 384 ölçümde yanlış kesin karar yoktur; 368 doğru, 16
belirsiz sonuç vardır. 0 dB ana geliştirme popülasyonunda iki OOK ölçümü yanlış
karar almıştır; düşük SNR sonuçları bu nedenle ürün doğruluğu iddiasına dahil
edilmez.

## Kilit ve sınırlar

- Yöntem kilidi: `505e9c0e7e563412f1f51a50830f38fb493bf609a7a62b4b8f48bdc64f24c1ce`
- Kalıcı sayısal model: 18.880 bayt
- Toplam kalıcı kestirim yükü: 52.964 bayt; sınır 65.536 bayt
- F1/F2 yöntemleri, sonuçları ve ürün kararları değiştirilmemiştir.
- F3 binding/OOS preimage'ları açılmamıştır.
- Canlı RF, gerçek cihaz, dBm kalibrasyonu, FPGA/ARM yürütümü, yön bulma ve ürün
  kabulü iddia edilmez.

## Kanıt dosyaları

- `datasets/fixtures/phase04f3/domain-model-v4.json`
- `datasets/fixtures/phase04f3/method-lock-v4.json`
- `results/evidence/phase04f3/development-results-v4.json`
- `results/evidence/phase04f3/carrier-analysis-v4.json`
