# RF Test Sınırları

## Güncel ürün kapsamı — 13 Eylül 2026

ADR-0044 ile ET/TX uygulama, yapılandırma ve test yolları üründen kaldırılmıştır.
Depoda RF yayın çalışma zamanı yoktur; iki HackRF yalnız ED/RX rolleri için
değerlendirilir. Aşağıdaki kayıtlar önceki geliştirme döneminin tarihsel güvenlik
sınırlarıdır ve güncel üründe TX yetkisi veya yeteneği oluşturmaz.

## Güncel ET laboratuvar sınırı — 8 Eylül 2026

Kullanıcı, fiziksel ET-TX çalışmalarının yalnız hazır korumaları bulunan Faraday
kabini içinde yürütüleceğini bildirmiş ve `CABLED_LAB` geliştirmesini onaylamıştır.
Bu ortam onayı sonraki oturumlar için kayıtlıdır; aynı beyan tekrar istenmez.

Bağlayıcı sınırlar şunlardır:

- `CABLED_LAB`, yalnız kapalı Faraday kabini içinde veya aynı kabin içindeki
  uygun zayıflatmalı kablolu düzende kullanılabilir.
- Faraday kabini dışında açık alan, saha veya denetimsiz antenli TX yapılmaz;
  genel `HARDWARE_TX_LOCKED` yolu fail-closed kalır.
- TX yalnız tam seri numarasıyla seçilmiş cihaz, sınırlandırılmış süre ve kazanç,
  operatör başlatması, otomatik durma, acil durdurma ve ölçüm kaydıyla çalışır.
- İlk fiziksel koşu en düşük TX kazancında kısa bir doğrulama tonu olur. Gürültü
  veya diğer dalga biçimleri ancak bu koşu başarıyla kaydedildikten sonra denenir.
- PA bulunmadığından yüksek güçlü yayın veya yüksek güçlü ET yeteneği iddia edilmez.
- GNSS RF dalga şekli bu onayın kapsamında değildir; ilgili ayrı faz ve kabul
  tamamlanmadan GNSS TX eklenmez.
- Ortamın hazır olduğuna ilişkin kullanıcı beyanı fiziksel izolasyon ölçümü veya
  RF başarı kanıtı sayılmaz; ölçülen sonuçlar ayrı kanıt olarak saklanır.

Mevcut kaynakta PHASE-10 Tekli Görev için güvenlik kapılı HackRF süreç arka ucu
vardır; fiziksel olarak doğrulanmış değildir. Depo profili kapalıdır ve seri,
izinli bant, ölçülmüş zayıflatma ile tarihli kapı kaydı eksikken RF süreci
başlamaz. `CABLED_LAB` ortam onayı tek başına RF üretmez ve eksik interlockları
atlamaz. Güncel karar ADR-0043'tedir; PHASE-00'a ilişkin önceki yayınsız
sonuçlar tarihsel kayıt olarak geçerliliğini korur.

## Tarihsel PHASE-00 sınırı

PHASE-00 kapsamında RF yayını yoktur. Antene bağlı kontrolsüz TX testi yapılmaz.
GNSS aldatma ve karıştırma bu başlangıç fazında yalnız gelecekteki kontrollü
çalışma olarak kaydedilmiştir. HackRF-2 bu aşamada kullanılmaz ve uygun
zayıflatma, yalıtım, ölçüm ve acil durdurma düzeni kurulmadan TX kodu eklenmez.
Bu tarihsel ifadeler PHASE-00 sonucunu korur; güncel `CABLED_LAB` yetkisi üstteki
8 Eylül kararı ve ADR-0043 ile değerlendirilir.
