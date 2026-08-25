# PHASE-04-F3D Tek Seferlik Değerlendirme Kaydı

## Karar

PHASE-04-F3D tamamlanmış ve başarısız olmuştur. Binding popülasyonu 40/40
kontrolü geçmiş, OOS popülasyonu 23/24 kontrolü geçmiştir. `signal_domain`
alanındaki `domain-family-correct-count` kontrolü başarısız olduğu için bütün
alanların iki popülasyonda birlikte geçme koşulu sağlanmamıştır.

F3E başlatılamaz ve ürün profili oluşturulamaz. Aynı binding/OOS popülasyonları
yeniden çalıştırılamaz.

## Tek sefer sırası ve bütünlük

- v4 yöntem kilidi ve değerlendirme çalıştırıcısı seed reveal öncesinde
  commitlenip uzak dala gönderilmiştir.
- Reveal edilen binding/OOS seed ve salt değerleri önceden yayımlanan SHA-256
  commitment değerleriyle eşleşmiştir.
- `f3d-run-started.json` binding çalışmasından önce yazılmıştır.
- Skorlayıcı, F2'den byte-bağlı korunan 40 binding ve 24 OOS kontrolünü eşik
  değişikliği olmadan uygulamıştır.
- Yedi kanıt bütünlüğü kontrolünün tamamı geçmiştir; değerlendirme kararı ayrıca
  `failed` olarak korunur.

## Sonuç özeti

| Popülasyon / kontrol | Sonuç |
|---|---:|
| Binding | 40 / 40 geçti |
| OOS | 23 / 24 geçti |
| Emisyon merkez frekansı | Binding ve OOS geçti |
| Taşıyıcı çizgisi | Binding ve OOS geçti |
| OBW99 | Binding ve OOS geçti |
| Kalibre edilmemiş kanal gücü | Binding ve OOS geçti |
| SNR kestirimi | Binding ve OOS geçti |
| Span dayanıklılığı | Binding ve OOS geçti |
| Sinyal alanı | Binding geçti, OOS başarısız |

OOS `signal_domain` kontrolünde aile/koşul minimumu 48 doğru karar sınırına
karşı 44 olmuştur. İhlal NFM 6 dB koşulundadır:

| NFM 6 dB OOS sonucu | Sayı |
|---|---:|
| Toplam | 64 |
| Doğru `Analog` | 44 |
| Yanlış kesin karar | 0 |
| `Belirsiz` | 20 |

Yöntem yanlış sınıf atamak yerine fazla abstention üretmiştir. Aynı koşul
binding popülasyonunda 192 ölçümün 156'sını doğru, 0'ını yanlış ve 36'sını
belirsiz sonuçlandırmıştır.

## F3 hedefinin durumu

F2D'deki OOK ihlalleri yeni kapalı OOS popülasyonunda giderilmiştir:

- OOK 12 dB taşıyıcı: 64/64 geçerli.
- OOK 6 dB sinyal alanı: 61/64 doğru, 0 yanlış, 3 belirsiz.
- Taşıyıcı uygulanmayan ailelerde OOS yanlış taşıyıcı sayısı: 0.

Bu iyileşme genel ürün kabulü için yeterli değildir. Korunan sözleşme herhangi
bir zorunlu alanın başka bir ailedeki başarısızlığını OOK başarısıyla örtmeye
izin vermez.

## Sınırlar ve sonraki karar

- Sonuç sentetik, deterministik ve kapalı seed değerlendirmesidir; canlı RF,
  gerçek donanım, dBm kalibrasyonu, FPGA/ARM yürütümü veya yön bulma kanıtı
  değildir.
- F3E kapalıdır. NFM 6 dB abstention genellemesi için yeni bir iyileştirme turu
  ancak ayrı kök neden analizi, yeni veri ayrımı/commitment ve kullanıcı onayıyla
  açılabilir.

## Kanıt dosyaları

- `datasets/fixtures/phase04f3/evaluation-runner-lock-v4.json`
- `datasets/fixtures/phase04f3/evaluation-seeds.json`
- `results/evidence/phase04f3/f3d-run-started.json`
- `results/evidence/phase04f3/binding-results-v4.json`
- `results/evidence/phase04f3/oos-results-v4.json`
- `results/evidence/phase04f3/parameter-comparison-v4.json`
- `results/evidence/phase04f3/f3d-verification.json`
