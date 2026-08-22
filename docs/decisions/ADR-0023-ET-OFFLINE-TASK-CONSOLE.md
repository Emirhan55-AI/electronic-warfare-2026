# ADR-0023 — ET Offline Görev Konsolu ve TX-Kilitli Modeller

- Durum: Kabul edildi
- Kapsam: Kullanıcı onaylı ET arayüzü ve yalnız bilgisayar üzerindeki deterministik modeller
- Önceki doğrulanmış sınır: P0 ET taban bant modelleri ve fail-closed görev denetleyicisi

## Karar

ET çalışma alanı dört ayrı görev olarak sunulur: sürekli karıştırma,
arabakışlı karıştırma, analog aldatma ve GNSS senaryosu. Her görev ortak bir
`OFFLINE`/`LOOPBACK`/`REPLAY` durum başlığı, `TX KİLİTLİ` etiketi, yalnız kendi denetimleri,
salt-okunur işlem akışı ve yapılandırılmış sonuç kaydı kullanır.

Sürekli model tekli, çoklu, seeded bant-sınırlı baraj ve lineer süpürmeli kompleks
taban bant tamponlarını üretir. Arabakış modeli deterministik yerel analiz
girişinde enerji eşiği, ardışık pencere onayı, hysteresis ve
`DİNLE → KARAR → GÖREV → GUARD → DİNLE` akışını doğrular. Analog model kayıtlı
test sesini normalize eder, ses bandını sınırlar ve AM/FM/NFM karmaşık taban
bantlarını yerel loopback ile denetler. GNSS görevi yalnız GPS L1 C/A senaryo
metadatasını doğrular; RF dalga şekli üretmez.

Tüm görevler ortak `ETTaskResult` veri sözleşmesi ile sonuç verir. Bu sözleşme UI
metninden bağımsız olarak görev tipi, mod, kaynak, zaman, süre, dalga biçimi,
örnekleme, normalizasyon, doğrulama ve TX kilidi alanlarını taşır.

## Güvenlik Sınırı

Bu karar RF çıkış yolu, SDR aygıt erişimi, OTA iletim, kablolu RF gönderim,
güç/frekans reçetesi veya GNSS RF üretimi eklemez. `CABLED_LAB` ve
`HARDWARE_TX_LOCKED` modları fail-closed kalır. `OFFLINE` ve `LOOPBACK` sonuçları
canlı ya da fiziksel RF sonucu olarak etiketlenmez.

## Kanıt ve Ertelenen İşler

Deterministik birim ve Qt binding testleri host üzerinde çalışır. Bu kanıt
HackRF-2, GNSS alıcısı, RF spektrum ölçümü, RF etkisi, RF güç seviyesi veya fiziksel
görev çevrimi ölçümü değildir. Bu fiziksel çalışmalar yol haritasındaki kontrollü
RF güvenlik kapıları ve ayrı kullanıcı onayı olmadan başlatılmaz.
