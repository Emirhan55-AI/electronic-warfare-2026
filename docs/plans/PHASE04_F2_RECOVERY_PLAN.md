# PHASE-04-F2 Kontrollü İyileştirme Planı

## Amaç

Başarısız F1D kanıtını değiştirmeden, protokol ile çalıştırıcı arasındaki kapsama
açıklarını kapatmak ve alan bazlı parametre yöntemini tamamen yeni veri ayrımıyla
yeniden doğrulamak. F2, F1'in yeniden koşusu değildir.

## Alt fazlar

| Alt faz | Kapsam | Çıkış kapısı |
|---|---|---|
| PHASE-04-F2A | F1D salt-okunur kök neden ve kapı kapsama analizi | Kayıtlı kararlar yeniden üretilir; protokol, skor ve yöntem sorunları ayrılır; F1 kaynaklarının değişmediği doğrulanır. |
| PHASE-04-F2B | Yeni protokol, veri ayrımı ve seed commitment kilidi | Her kabul anahtarının yürütülebilir skor karşılığı vardır; kare/sekans anlamı tek anlamlıdır; yeni binding/OOS seed'leri yöntemden önce kapatılır. |
| PHASE-04-F2C | Ayrı v3 estimator ve açık geliştirme kanıtı | Yalnız yeni açık geliştirme kataloğu kullanılır; gürültü reddi, OBW ve sinyal alanı bağımsız geliştirme kapılarını geçer; yöntem reveal öncesi kilitlenir. |
| PHASE-04-F2D | Yeni çalıştırıcı kilidi ve tek seferlik değerlendirme | Çalıştırıcı commit/push sonrası seed'ler açılır; binding ve OOS bir kez çalıştırılır; sonuç değişmeden korunur. |
| PHASE-04-F2E | Digest bağlı ürün entegrasyonu | Yalnız bütün zorunlu alanlar iki popülasyonda da geçerse profil oluşturulur; aksi durumda fail-closed kalır. |

## F2B protokol kuralları

- F1'de açılmış seed ve sahneler yalnız teşhis kanıtıdır; geliştirme girdisi olamaz.
- Yeni açık geliştirme kataloğu birden fazla bağımsız seed ve daha geniş negatif
  kontrol örneklemi içerir.
- Yeni binding ve OOS seed preimage'ları repository dışında tutulur; commitment
  değerleri yöntem geliştirilmeden önce kaydedilir.
- Kabul JSON'undaki her anahtarın skorlayıcıda kullanıldığını doğrulayan otomatik
  kapsama matrisi reveal öncesi zorunludur.
- `frames_per_measurement`, `measurements_per_noise_population` ve toplam örnek
  sayısı ayrı adlandırılır; sekans/kare terimleri birbirinin yerine kullanılmaz.
- Negatif kontrol her alan için ayrı karar üretir. Bir alanın yanlış sayısal sonucu
  başka alanın yerel kararını değiştirmez; bütün-profil kararı yine bütün zorunlu
  alanların geçmesini gerektirir.
- Sayısal doğruluk eşikleri sonuçlara bakılarak gevşetilmez. Her değişiklik yöntem
  geliştirmeden önce gerekçelendirilir ve kilitlenir.

## F2C yöntem sınırları

- F1C dosyaları değiştirilmez; v3 uygulaması ayrı kaynak ve model dosyalarında
  geliştirilir.
- Gürültü reddi, parametre hesaplarından önce ortak ölçüm geçerliliği üretir;
  güç/SNR için tesadüfi pozitif toplam güç tek başına yeterli değildir.
- OBW ve sinyal alanı iyileştirmeleri ayrı ablasyon sonuçlarıyla değerlendirilir.
- Sinyal alanında `Belirsiz` geçerli ve birinci sınıf sonuçtur; düşük güven sayısal
  sınıfa zorlanmaz.
- Bellek, dört kare/ölçüm, tek worker, tek pending intent ve runtime ground-truth
  yasağı korunur.

## Onay kapıları

F2A tamamlanınca F2B için yeniden kullanıcı onayı alınır. Aynı kural F2C, F2D ve
F2E geçişlerinde uygulanır. F2D başarısız olursa yeniden koşu yapılmaz; yeni tur
ancak ayrı plan ve yeni popülasyonlarla açılabilir.

## Durum

PHASE-04-F2A tamamlanmıştır. Beş kök neden sınıfı makinece doğrulanmış, F1 kayıtlı
kararlarının tamamı yeniden üretilmiş ve üç protokol/skor kapsama açığı
belirlenmiştir. F2B başlamamıştır.
