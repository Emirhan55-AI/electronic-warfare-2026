# PHASE-04-F2D Tek Seferlik Değerlendirme Kaydı

## Karar

PHASE-04-F2D tamamlanmış ve başarısızdır. Binding popülasyonu bütün 40 kontrolü
geçmiştir. OOS popülasyonunda 24 kontrolün 22'si geçmiş; taşıyıcı frekansı ile
sinyal alanı birer kontrol nedeniyle başarısız olmuştur.

F2D tekrar çalıştırılmaz. Eşikler, yöntem, seed'ler, denominator veya sonuç
dosyaları değiştirilmez. Bütün zorunlu alanlar binding ve OOS'ta birlikte
geçmediği için F2E ürün profili oluşturulmaz ve PHASE-04 açık kalır.

## Yürütme sırası

1. v3 yöntem kilidi açık geliştirme sonucundan sonra oluşturuldu.
2. Değerlendirme çalıştırıcısı seed reveal öncesinde kilitlendi.
3. Runner-lock commit'i `bdb659cb36195ac6ea5670826992bd90d806847b`
   uzak dala gönderildi.
4. Temiz ve upstream ile eşit `HEAD` doğrulandı.
5. Binding/OOS commitment preimage'ları doğrulanarak açıldı.
6. Binding ardından OOS aynı kilitli çalıştırıcıyla bir kez çalıştırıldı.
7. Saklanan metrikler kilitli scorer ile salt-okunur yeniden puanlandı.

## Sonuçlar

### Binding

- Durum: geçti
- Kontroller: 40 / 40
- Yedi alan/destek kararı: tamamı geçti
- Gürültü yanlış-geçerli: altı zorunlu alanın tamamında 0
- Taşıyıcı en düşük aile geçerliliği: %91,15
- Taşıyıcı yanlış karar oranı: %0,104
- OBW en düşük aile geçerliliği: %93,23
- Sinyal alanı 6 dB genel doğru / yanlış: %93,82 / %0,52

### OOS

- Durum: başarısız
- Kontroller: 22 / 24 geçti
- Emisyon merkezi, OBW, kalibre edilmemiş kanal gücü, SNR ve span dayanıklılığı geçti.
- Taşıyıcı geçerli aile minimumu OOK nedeniyle 53 oldu; gerekli değer 56 idi.
- Sinyal alanında aile başına en yüksek yanlış karar OOK 6 dB koşulunda 3 oldu;
  izin verilen en yüksek değer 2 idi.
- OOK 6 dB doğru karar sayısı 50 olup 48 minimumunu geçti; başarısızlık yanlış
  kesin karar sayısından kaynaklandı.
- Gürültü yanlış-geçerli: altı zorunlu alanın tamamında 0
- OBW aile minimum geçerli sayısı: 62 / 64
- Taşıyıcı yanlış karar sayısı: 1; sınır 2

## Kanıt bütünlüğü

`f2d-verification.json` içindeki commitment, runner-lock, tek-sefer sırası,
popülasyon sayıları, kilitli skorun yeniden üretimi, karşılaştırma ve digest
kontrollerinin tamamı geçmiştir. `evaluation_status` ayrıca ve değişmeden
`failed` olarak tutulur.

## İddia sınırı

Bu sonuç sentetik kilitli popülasyonlara aittir. Canlı RF, dBm kalibrasyonu,
FPGA/ARM yürütümü, HackRF kabulü veya ürün başarısı değildir. Başarısız F2D
sonucundan ürün profili türetilmez.

## Kanıt dosyaları

- `datasets/fixtures/phase04f2/evaluation-seeds.json`
- `results/evidence/phase04f2/f2d-run-started.json`
- `results/evidence/phase04f2/binding-results-v3.json`
- `results/evidence/phase04f2/oos-results-v3.json`
- `results/evidence/phase04f2/parameter-comparison-v3.json`
- `results/evidence/phase04f2/f2d-verification.json`
