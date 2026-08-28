# ADR-0032 — P0 Doğrulanmış Aday Yolunun Kısaltılması

- Durum: Host eşdeğerliği ve geçici ARM ölçümü tamamlandı; imaj/gerçek-zaman kapısı beklemede
- Kapsam: P0 `PL → DMA → ARM` aday üretim yolu
- Bağlı gereksinimler: KTR-4.1, KTR-6
- Ön koşul: ADR-0031

## Bağlam

ADR-0031 sonrası hizmet yolu işlevsel olarak hatasız olsa da fiziksel 2 MS/s
kapısı `196,966411503 / 488,28125 kare/s` ile geçilememiştir. Stage profiler,
aday üretimini ARM süresinin en büyük bölümü olarak göstermiştir. PL decoderi
aynı güç ve karar kelimelerini zaten biçim, aralık, değerlendirme ve tespit
maskeleriyle doğrulamaktadır. Buna rağmen aday gruplama fonksiyonu her karede
aynı güç ve karar dizisini ikinci kez taramaktadır.

## Karar

Strict dış API korunur. Decoder sonrasında çağrılan ürün yolu için ayrı bir
`trusted` giriş noktası eklenir. Bu giriş noktası yalnız decoderin başarıyla
doğruladığı 4096 güç ve karar hücrelerini kabul eder; genel çağrılarda kullanılan
`p0_os_cfar_group_detections()` doğrulamaları ve `p0_multiscale_process_pl()`
strict davranışı değişmez. Böylece fail-closed sınırı decoder öncesinde kalır,
ham veya işaretlenmemiş DMA verisi bu kısa yola ulaşamaz.

Uygulama yalnız yinelenen giriş doğrulamasını kaldırır. OS-CFAR profili,
aday birleştirme, 32-bin bütünleşik enerji, geniş bant kurtarma, sıralama,
PHASE-06I/06J ABI, temporal durum ve eşikler değiştirilmez.

## Uygulama

- `p0_os_cfar_group_detections_trusted()` ortak çekirdeğin decoder-sonrası kısa
  yolu olarak eklendi.
- `p0_multiscale_process_pl_trusted()` yalnız `p0_pl_os_cfar_decode()` başarıyla
  tamamlandıktan sonra P0 pipeline ve stage profiler tarafından çağrılıyor.
- Strict API dışarıdan gelen veya bağımsız kullanılan diziler için korunuyor.
- Host C doğrulaması strict ve trusted yolları bütün kayıt, karar, gürültü,
  eşik ve recovery çıktılarında bit/semantik olarak karşılaştırıyor.

## Kabul kapıları

- Host PL decoder, strict yol ve trusted yol: sıfır decode/adayı/recovery farkı.
- Bozuk marker, değerlendirme veya sınır tespiti: decoder tarafından reddedilir;
  trusted yol bu verilerle doğrudan çağrılmaz.
- Mevcut protocol, ABI ve Python golden testleri değişmeden geçer.
- PetaLinux ARM imajı yeniden derlenmeden fiziksel hız veya donanım sonucu
  ilan edilmez.
- Yeni imajla 64 ısınma + 4.096 ölçüm ve `488,28125 kare/s` kapısı yeniden
  çalıştırılır; sonuç başarısızsa başarısız olarak saklanır.

## Sınır

Bu karar yeni RTL, DMA ping-pong, örnekleme hızı, FFT boyu, eşik, RF yayın,
HackRF canlı alımı veya kalibrasyon eklemez. Trusted giriş noktası decoder
sonrası iç sözleşmedir; genel amaçlı veri doğrulama API'si değildir.

## Geçici ARM ölçümü

Kaynaktaki değişiklikleri içeren, PetaLinux imajına kalıcı olarak kurulmamış ARM
hard-float ikilisi aynı ZedBoard kernel/driver/PL üzerinde `/tmp` altında
çalıştırıldı. 64 ısınma ve 4.096 ölçüm karesinin tamamı DMA `0x7`, pipeline,
probe ve aday düşürme hatası olmadan tamamlandı. ARM ortalaması `2,723289 ms`,
birleşik yol `4,173240 ms` oldu; ADR-0031 referansına göre sırasıyla `%4,232`
ve `%2,410` daha yüksektir. Bu nedenle kısa yol işlevsel olarak kabul edilmiş,
ölçülebilir hız kazanımı olarak kabul edilmemiştir. Ayrıntılı kayıt
`results/evidence/p0/ed-stage-profile-adr0032-transient-arm.json` içindedir.
