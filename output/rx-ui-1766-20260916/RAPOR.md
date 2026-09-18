# 1766 MHz sinyal tespiti — 16 Eylül 2026

## Kapsam
PHASE-08 / ST-06 kapsamında mevcut çalışan uygulamada yapılan sınırlı GUI ve RF gözlemidir. Faz kabulü verilmedi. Kaynak kod değiştirilmedi. Harici TX durumu kullanıcı beyanıyla kaydedildi; alıcının RX-only bayrağından çıkarılmadı. Harici LNA kullanıcı beyanına göre bağlı değildi.

## Koşullar
1740–1780 MHz, LNA 24 dB, VGA 24 dB, AMP kapalı; pencere başına 128 kare, 8 yerleşme karesi. Ana tarama 10 MS/s, 16 pencere. Kullanıcı TX frekansını 1766 MHz olarak bildirdi; TX ayarları değiştirilmedi.

| Koşul | Ana tarama süresi | Pencereler | 1766 MHz hedefi |
|---|---:|---:|---|
| Kapalı | 8,0487 s | 16/16 | Listelenmedi |
| Açık | 8,8059 s | 16/16 | 1766,001882 MHz; tekrar görüldü |
| Kapalı | 7,5234 s | 16/16 | Listelenmedi |

Her ana koşuda 2048 FPGA yanıt karesi tamamlandı. Ana koşuların USB taşması, CRC, sıra, kuyruk kaybı ve giriş/çıkış sayısal kırpılma sayaçları sıfır. Bu sonlu yakalamalar kesintisiz gerçek zaman performansını veya analog doğrusal çalışmayı kanıtlamaz.

Açık koşuda hedef birincil pencerede yerleşme sonrası 120/120 karede gözlendi; farklı alıcı merkezinde FPGA doğrulaması ve sonraki tekrar alımda 40 gözlem kaydedildi. Bu oran istatistiksel tespit olasılığı değildir. 1760 MHz civarı dar çizgi üç koşulda da listelendi; kaynağı belirlenmedi, yanlış alarm olduğu kanıtlanmadı.

## Bulgular ve sonraki sıra
1. Tarama frekans ekseni etiketleri RxSurveyView.qml içinde centerFrequencyHz ±1e6 olarak sabit. Tarama önizlemesi kare örnekleme hızını kullanıyor; 10 MS/s taramayla etiketler uyuşmuyor. Etiketler gerçek spektrum merkezi ve kapsamından türetilmeli.
2. Sabit frekanstaki turuncu Alınıyor ile ek doğrulamayı geçmiş yeşil durumun farkı ekranda yeterince açık değil. Kullanıcıya tespit ve ek doğrulama ayrı anlatılmalı; sırf renk değiştirmek doğrulama sayılmamalı.
3. Sinyal kontrol ediliyor kartının görünürlüğü gerçek doğrulama işi yerine kaba aday varlığına bağlı. Yanıp sönen büyük kart yerine gerçek işlem durumunu gösteren kalıcı satır önerilir.
4. Açık hedefin aday aralığı ana taramada 1,1658 MHz, farklı ayardaki FPGA doğrulamasında 0,8340 MHz, tekrar alımda 0,8386 MHz. Bunlar kalibre edilmiş işgal bant genişliği ölçümü değildir. Ham I/Q ve canlı TX ayarları birlikte incelenmeden genişliğin kök nedeni belirlenemez. Kayıtlardaki dar RX destek bileşeni de bütün FM bant genişliği olarak yorumlanamaz.
5. Sabit izleme frekans etiketi onlu kHz düzeyinde oynuyor; arayüzde çok basamak gösterilmesi o doğruluğun kanıtı değildir.

Önce eksen ve durum gösterimi düzeltilmeli, ardından aday aralığı aynı ham I/Q üzerinden incelenmeli. Sonrasında tekrarlı kör frekans ve sınır frekans denemeleriyle kabul değerlendirilmelidir. dBm kalibrasyonu ve parametre fazı bu koşuda yapılmadı.

## Kanıt sınırları
Çalışan süreç/kart imajı hash eşleştirmesi bu GUI koşusunda doğrulanmadı. Audit başlangıcındaki kaynak hashleri diskteki dosyalara aittir; çalışan sürecin aynı sürüm olduğunu tek başına kanıtlamaz. Ham I/Q baytları bu rapor paketinde yok; audit I/Q hashleri bulunuyor. Kesin tespit/kaybolma gecikmesi ölçülmedi. Önceki sabit alım sonuçları zaman damgalı aralıklı GUI gözlemleridir.

## Dosyalar
- observations.json: GUI erişilebilirlik gözlemleri ve kullanıcı TX koşulları.
- audit-comparison.json: üç koşunun özeti ve altı audit dosyasının SHA-256 değerleri.
- Aynı dizindeki özgün JSONL kopyaları: ana taramalar ve tekrar alımlar. Orijinaller build/acceptance/rx-survey dizininde korundu.

Son durum: kullanıcı TX kapalı olduğunu bildirdi; son tarama tamamlandı, RX taraması çalışmıyor.

## Sonraki kaynak düzeltmesi

Kullanıcı onayı sonrası frekans ekseni gerçek spektrum merkez/hızına bağlandı.
Yanıp sönen tespit özet kartı kaldırıldı; gerçek doğrulama çalışırken ayrı kısa
satır gösterilir. Tespit, doğrulanmış aday ve geçmiş kayıt metinleri ayrıldı.
Tarama aralığı açıkça Tespit aralığı olarak adlandırıldı. 39 QML ve 105 görünüm
modeli/doğrulama/sunum testi geçti. Bu yeni kaynakla fiziksel RF tekrarı yapılmadı.
Aday genişliği tespit aralığıdır: son kart olayında 475 * 10e6 / 4096 =
1.15966796875 MHz. Kareler arası sınır ortalaması 1.16583251953125 MHz.
Kök neden için ham I/Q gerektiğinden eşik veya aday algoritması değiştirilmedi.
