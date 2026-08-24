# PHASE-04-F3 Parametre Dayanıklılık Sözleşmesi

## Amaç

Bu sözleşme, F2D'de yalnız OOK ailesinde kalan iki ihlalin yeni ve bağımsız
popülasyonlarda nasıl değerlendirileceğini yöntem geliştirilmeden önce sabitler.
F2'nin 40 binding ve 24 OOS kontrolü byte-bağlı olarak korunur; hiçbir kabul
eşiği gevşetilmez.

## Veri ayrımı

- Açık geliştirme kataloğu sekiz yeni seed içerir ve F1/F2 açık ya da açılmış
  değerlendirme seed'leriyle kesişemez.
- F3 binding ve OOS seed/salt değerleri repository dışında tutulur. Repository
  yalnız SHA-256 commitment değerlerini içerir.
- Preimage değerleri v4 yöntem ve değerlendirme çalıştırıcısı commit edilip uzak
  dala gönderilmeden açılamaz.
- Açılan F1/F2 popülasyonları yöntem, eşik veya prototip seçimi için kullanılamaz.

## Korunan kabul kapıları

`datasets/fixtures/phase04f2/acceptance-gates.json` dosyasındaki bütün kontroller
ve eşikler SHA-256 bağıyla F3'e taşınır. Ürün profili için bütün zorunlu alanlar
hem binding hem OOS popülasyonunda geçmelidir.

F3 açık geliştirme popülasyonunda binding oran kapılarına ek olarak şu OOK risk
payları zorunludur:

| Alan | Koşul | Kapı |
|---|---|---|
| Taşıyıcı çizgisi | OOK, 12 dB, seed başına 48 ölçüm | En az 45 geçerli ölçüm |
| Temporal taşıyıcı kanıtı | OOK, 12 dB, seed başına 192 kare | En az 180 yeterli kare ve en az 42 tam dört-kare desteği |
| Yanlış taşıyıcı | Taşıyıcısız aileler, 12 dB | Seed başına en fazla 1, toplamda en fazla 2 yanlış geçerli |
| Sinyal alanı doğruluğu | OOK, 6 dB, seed başına 48 ölçüm | En az 40 doğru kesin karar |
| Sinyal alanı riski | OOK, 6 dB | Seed başına en fazla 1, sekiz seed toplamında en fazla 2 yanlış kesin karar |
| Gürültü reddi | 512 noise-only ölçüm | Her parametre alanında sıfır yanlış geçerli |

Taşıyıcı için seed-alt sınırı %93,75'tir; bu değer OOS kapısındaki %87,5'in
6,25 yüzde puan üzerindedir. Kare desteği aynı %93,75 oranını, tam dört-kare
desteği ise en az %87,5'i zorunlu tutar. Sinyal alanı doğru karar alt sınırı
%83,33 ile OOS sınırının 8,33 yüzde puan üzerindedir. Yanlış kesin karar riski
seed başına en fazla %2,083, bütün açık popülasyonda en fazla %0,521'dir; ikisi
de OOS'ta izin verilen %3,125'in altındadır.

Sinyal alanı kapısı sınırdaki bir örneği zorla Analog veya Sayısal yapmayı
gerektirmez. Gerekli doğru karar alt sınırı korunmak şartıyla `Belirsiz` sonucu,
yanlış kesin karara tercih edilir.

## Çalışma zamanı sınırı

Ground truth çalışma zamanına taşınamaz. Ölçüm dört kare kullanır; bir worker,
en fazla bir bekleyen intent ve 65.536 bayt kalıcı yük sınırı korunur.

## İddia sınırı

Bu sözleşme bir yöntem veya başarı sonucu değildir. Canlı HackRF, RF
kalibrasyonu, dBm, ARM/ZedBoard çalıştırması ya da ürün kabulü göstermez.
