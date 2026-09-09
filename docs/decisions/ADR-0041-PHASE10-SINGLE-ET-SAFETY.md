# ADR-0041 — PHASE-10 Tekli Görev ve fiziksel TX güvenlik kapısı

- Durum: Kabul edildi
- Tarih: 8 Eylül 2026
- Gereksinim: KTR-5.1

## Bağlam

Kullanıcı PÇ-02 ile PHASE-09 çalışmalarını beklemeye alıp ET'ye geçişi açıkça
onayladı. İlk kapsam yalnız operatörün seçtiği tek frekans aralığında süreli,
bant sınırlı gürültüdür. Bu karar yol haritasında kullanıcı onaylı bir öncelik
istisnasıdır; açık ED kabul maddelerini tamamlanmış yapmaz.

## Karar

PHASE-10, deterministik CI8 üreteci, iletimsiz spektrum doğrulaması, tek görevli
Türkçe operatör yüzeyi ve fail-closed HackRF süreç sınırıyla açılır. Donanım
komutu yalnız tarihli fiziksel güvenlik profili geçerse kurulabilir. Görev sonlu
dosya ve sonlu örnek sayısıyla iki kez sınırlandırılır; tekrar modu kullanılmaz.
RF yükselteci ve anten beslemesi kapalıdır. Normal durdurma, zaman aşımı,
uygulama kapanması ve oturum kilitli acil durdurma süreç sahibidir.

## Sonuç

Yazılım kapısı donanım olmadan doğrulanabilir. Fiziksel profil varsayılanında
kapalı kalır. Bağlı cihaz ve kapalı düzen ölçümü olmadan gerçek TX çalıştırılmaz,
RF güç/etki iddiası üretilmez ve PHASE-11 başlatılmaz. Eski çoklu/baraj/süpürme,
arabakış, analog ve GNSS çevrimdışı modelleri ürün paketinin dışında kalır.
