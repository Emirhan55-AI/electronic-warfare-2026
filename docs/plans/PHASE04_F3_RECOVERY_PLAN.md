# PHASE-04-F3 OOK Dayanıklılık Planı

## Amaç

Başarısız F2D kanıtını değiştirmeden, OOK taşıyıcı geçerliliği ile 6 dB sinyal
alanı yanlış kesin kararlarının seed-bazlı güvenlik payını güçlendirmek ve tamamen
yeni veri ayrımıyla doğrulamak.

F3, F2'nin yeniden koşusu değildir. F1 ve F2 binding/OOS popülasyonları yöntem
geliştirme girdisi olamaz.

## Alt fazlar

| Alt faz | Kapsam | Çıkış kapısı |
|---|---|---|
| PHASE-04-F3A | F2D salt-okunur kök neden ve seed-bazlı açık veri analizi | F2 kararları yeniden üretilir; OOK taşıyıcı ve alan kararındaki güvenlik payı eksikleri makine kanıtıyla ayrılır. |
| PHASE-04-F3B | Yeni protokol, veri ayrımı ve commitment kilidi | Yeni açık seed'ler F1/F2'den ayrılır; binding/OOS preimage'ları yöntemden önce kapatılır; F2 eşikleri gevşetilmez. |
| PHASE-04-F3C | Ayrı v4 OOK dayanıklılık yöntemi | Taşıyıcı ve sinyal alanı ayrı geliştirme kapılarında seed-bazlı alt/üst risk sınırlarını geçer; yöntem reveal öncesi kilitlenir. |
| PHASE-04-F3D | Çalıştırıcı kilidi ve tek seferlik değerlendirme | Commit/push sonrası seed reveal; binding ve OOS bir kez çalıştırılır; sonuç değişmeden korunur. |
| PHASE-04-F3E | Digest bağlı ürün entegrasyonu | Yalnız bütün zorunlu alanlar iki popülasyonda da geçerse profil oluşturulur. |

## F3A bulguları

- OOK taşıyıcı geçerliliği geliştirmede 272/288, binding'de 176/192 ve OOS'ta
  53/64'tür. OOS minimumu 56'dır.
- Açık altı seed'in OOK taşıyıcı sayıları 48 ölçümde 44, 43, 46, 47, 46 ve
  46'dır. Aggregate başarı seed-bazlı alt sınır sağlamamıştır.
- OOK 6 dB yanlış sinyal alanı kararları geliştirmede 8/288, binding'de 4/192,
  OOS'ta 3/64'tür. OOS maksimumu 2'dir.
- Açık seed başına yanlış karar sayıları 2, 2, 1, 2, 0 ve 1'dir. Geliştirme
  yanlış oranının %95 Wilson üst sınırı %5,38; OOS izin oranı %3,125'tir.
- İki OOS ihlali aynı OOK ailesinde olsa da taşıyıcı varlığı ile sinyal alanı
  güveni ayrı alan kapıları olarak korunmalıdır.

## F3B protokol gereksinimleri

- En az altı yeni açık geliştirme seed'i kullanılmalı; F1/F2 açık ve reveal
  popülasyonlarıyla kesişim otomatik reddedilmelidir.
- Yeni binding/OOS seed ve salt değerleri v4 kaynakları oluşmadan önce repository
  dışında üretilip commitment olarak kilitlenmelidir.
- F2 kabul eşikleri gevşetilmemelidir.
- OOK taşıyıcı geliştirme kapısı aggregate oranla yetinmemeli; seed-bazlı minimum
  geçerli sayısı ve temporal kanıt dağılımı içermelidir.
- OOK sinyal alanı kapısı seed-bazlı yanlış kesin karar sayısını sınamalı;
  belirsiz sınır örneklerinin abstention'a taşınmasına izin vermelidir.
- Gürültü yanlış-geçerli kapıları alan bazlı ve sıfır sınırında kalmalıdır.
- Runtime ground-truth yasağı, dört kare, tek worker, tek pending intent ve
  65.536 bayt kalıcı yük sınırı korunmalıdır.

## Onay kapıları

F3A tamamlanınca F3B için yeniden kullanıcı onayı alınır. Aynı kural F3C, F3D
ve F3E geçişlerinde uygulanır. Tek seferlik değerlendirme başarısız olursa aynı
popülasyon yeniden çalıştırılmaz.

## Durum

PHASE-04-F3A tamamlanmıştır. F2D sonuçları ve açık geliştirme sayımları yeniden
üretilmiş; OOK taşıyıcı seed genellemesi, sinyal alanı yanlış karar güvenlik payı
ve ortak OOK sınırı olmak üzere üç kök neden sınıfı doğrulanmıştır. F3B
başlatılmamış ve ayrı kullanıcı onayı beklemektedir.
