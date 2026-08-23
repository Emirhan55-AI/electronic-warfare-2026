# PHASE-04 Parametre Çıkarımı Denetimi

## Sonuç

PHASE-04 açık kalmalıdır. Mevcut P0 parametre çekirdeği yarışma iş akışını
gösterecek deterministik bir host referansıdır; PHASE-04 alanlarını doğrulanmış
ürün yeteneği olarak açmak için yeterli değildir. R1, R2, D1 ve E1 başarısızlık
kanıtları korunacaktır.

## Yeniden üretilen durum

| Yüzey | Sonuç | Yorum |
|---|---|---|
| PHASE-04 R1 | Algoritma kapısı başarısız | Doğrulanmış profil yoktur. |
| PHASE-04 R2 | Tarihsel sonuç başarısız; güncel salt-okunur doğrulayıcı relocation sonrası manifest uyuşmazlığı bildiriyor | Sayısal kanıt değiştirilmeyecek; taşıma bağı ayrıca onarılmalıdır. |
| PHASE-04 D1F | Kanıt bütünlüğü geçti, algoritma kapısı başarısız | `capability_candidate=false`; 57 kapı başarısızdır. |
| PHASE-04 E1 | Bütün alan kararları başarısız | `validated_fields=[]`; ürün profili oluşmamıştır. Güncel implementation digest'i tarihsel özetten farklıdır. |
| P0 parametre çekirdeği | Sabit sentetik host takımı geçti | Sekiz sahne, bağımsız binding/OOS ve alan bazlı abstention sözleşmesinin yerine geçmez. |

Çalıştırılan salt-okunur komutlar:

```text
python scripts/verify_phase04.py --check
python scripts/verify_phase04_r2.py --check
python scripts/verify_phase04d1.py --check
python scripts/verify_phase04e1.py --check
python scripts/verify_p0_algorithms.py --check
```

## Bulgular

### P0 adlandırması fiziksel büyüklüğü doğru ifade etmiyor

`algorithms/p0/parameters.py` aday bölgesindeki güç ağırlıklı frekans merkezini
hesaplar. Bu büyüklük spektral merkezdir; ayrı bir taşıyıcı çizgisi kestirimi
değildir. Modeldeki `carrier_frequency_hz`, ürün kartındaki `Taşıyıcı` etiketi ve
KTR-4.2 açıklaması aynı kavramsal hatayı taşır.

Yeni çalışmada aşağıdaki terimler birbirinden ayrılacaktır:

- yayın merkez frekansı (`emission center frequency`),
- gözlenmiş taşıyıcı çizgisi frekansı (`observed carrier line frequency`),
- yüzde 99 işgal edilmiş bant genişliği (`99% occupied bandwidth`, OBW99),
- kalibre edilmemiş kanal gücü (`dBFS`),
- kestirilen SNR,
- sınırlı sinyal alanı (`Analog`, `Sayısal`, `Belirsiz`).

### P0 sonucu alan bazlı geçerlilik taşımıyor

P0 sonuç nesnesi bütün sayısal alanları her çağrıda doldurur. PHASE-04
sözleşmesinin `valid`, `not_observed`, `not_applicable`,
`insufficient_quality` ve `uncertain` durumları alan bazında temsil edilmez.
`confirmed` yalnız sonuç alanıdır; çekirdeğin public sonuç üretmesini engelleyen
bir ön koşul değildir.

### Kabul kanıtı ürün iddiası için dar

P0 kabulü sekiz deterministik fixture üzerinde açık toleranslarla geçer. Aynı
fixture ailesi geliştirme ve kanıt yüzeyi olduğundan bu sonuç yöntemden bağımsız
kilitli binding/OOS kanıtı değildir. Noise-only yanlış geçerlilik, düşük SNR'de
abstention, yakın yayın ayrımı, alan bazlı geçerlilik oranı ve aile bazlı hata
kapıları eksiktir.

### Repository taşıması tarihsel doğrulayıcı bağlarını etkiledi

APP-D kaynakları `algorithms/` ve `app/` sınırlarına taşımıştır. D1F relocation
bağını açıkça kaydettiği için bütünlük kontrolü geçer. R2 ve E1 doğrulayıcıları
ise çalışma zamanı yol/digest değişimini tarihsel kanıt değişikliği gibi görür.
Tarihsel JSON dosyaları yeniden yazılmadan, eski ve yeni yol kimliklerini
SHA-256 ile bağlayan salt-okunur bir relocation kaydı gereklidir.

## Karar sınırı

Bu denetim yeni bir doğruluk sonucu üretmez. Canlı HackRF, ZedBoard/ARM, dBm,
RF giriş gücü, genel modülasyon tanıma veya tamamlanmış PHASE-04 iddiası yoktur.

