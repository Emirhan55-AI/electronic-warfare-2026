# PHASE-04-F2A F1D Başarısızlık Analizi

## Sonuç

F1D'nin tek seferlik binding ve OOS sonucu değiştirilmeden korunmuştur. F2A,
kayıtlı sonuçları yeniden çalıştırmadan kilitli eşiklere göre kapı kapı ayırmış ve
F1 kararlarının tamamını yeniden üretmiştir. Analiz başarılıdır; F1 değerlendirme
kararı başarısız kalır.

## Alan bazlı ayrım

| Alan | Binding yerel kapıları | Binding kayıtlı karar | OOS yerel kapıları | OOS kayıtlı karar |
|---|---|---|---|---|
| Emisyon merkez frekansı | Geçti | Başarısız | Geçti | Geçti |
| Gözlenen taşıyıcı frekansı | Geçti | Başarısız | Geçti | Geçti |
| OBW99 | Geçti | Başarısız | Başarısız | Başarısız |
| Span dayanıklılığı | Geçti | Geçti | Geçti | Geçti |
| Kalibre edilmemiş kanal gücü | Geçti | Başarısız | Geçti | Geçti |
| SNR kestirimi | Geçti | Başarısız | Geçti | Geçti |
| Sinyal alanı | Başarısız | Başarısız | Başarısız | Başarısız |

Binding negatif kontrolünde merkez, taşıyıcı ve OBW yanlış sayısal sonuç
üretmemiştir. Kanal gücü ile SNR dört kez sayısal sonuç üretmiştir. Kilitli F1
skorlayıcısı herhangi bir sayısal alandaki tek ihlali bütün sayısal alanlara
uyguladığı için yerel kapıları geçen merkez, taşıyıcı, OBW, güç ve SNR birlikte
başarısız kaydedilmiştir. Bu karar F1 için değiştirilmez.

OOS'ta ortak negatif kontrol geçmiştir. OBW başarısızlığı aile başına en az 31/32
geçerli ölçüm kapısından, sinyal alanı başarısızlığı ise aile doğru/yanlış karar
sayılarından gelmiştir. Binding sinyal alanında 6 dB global yanlış karar oranı ile
aile doğru ve yanlış karar kapıları sağlanmamıştır.

## Protokol ve çalıştırıcı kapsama açıkları

Kilitli kabul belgesindeki aşağıdaki maddeler F1 skorlayıcısı tarafından
çalıştırılmamıştır:

- `binding.carrier_line_frequency.abstention_rate_minimum`
- `binding.noise_frames_per_sequence`
- `oos.noise_frames_per_sequence`

Kabul belgesi negatif kontrol için 32 kare/sekans tanımlarken skorlayıcı her ölçümde
dört ardışık kare kullanmıştır. Ayrıca taşıyıcı abstention alt sınırı kodda
okunmamıştır. F1 zaten başarısız olduğu için bu açıklar bir ürün başarısı doğurmaz;
ancak F1 çalıştırıcısının F2'de yeniden kullanılmasını engeller.

## Kök neden sınıfları

1. Protokol anahtarlarının yürütülebilir skor kapsamıyla birebir doğrulanmaması.
2. Alan bazlı negatif kontrol ile bütün-profil kararı arasında ayrı katman
   bulunmaması.
3. Gürültüde güç ve SNR yayımlanmasını engelleyen kapının seed değişimine karşı
   yeterince genelleşmemesi.
4. OOS OBW geçerli ölçüm sayısının aile tabanlı sınırı karşılamaması.
5. Sinyal alanı modelinin 6 dB ve OOS aile kararlarında genelleşmemesi.

## Değişmezler

- F1 yöntem, eşik, seed, sonuç ve kanıt dosyaları değiştirilmez.
- Açılmış F1 binding/OOS popülasyonları F2 yöntem ayarı veya eğitiminde kullanılmaz.
- F2 eşikleri sonuç görüldükten sonra değiştirilmez.
- Ground truth runtime'a verilmez.
- Bütün zorunlu alanlar yeni binding ve OOS kapılarını birlikte geçmeden ürün
  profili oluşturulmaz.

Makinece doğrulanabilir ayrıntı
`results/evidence/phase04f2/f2a-analysis.json` dosyasındadır.
