# P0 PC→ZedBoard I/Q Taşıma Sözleşmesi

## FPGA giriş profili

HackRF-1 alımı `8 MS/s` ve `16.384` kompleks örneklik bloktur. PC kanal seçici,
istenen çıkış merkezini sayısal olarak temel banda taşır; `193` tap Kaiser
pencereli FIR ile anti-alias süzme uygular ve `4:1` polyphase örnek azaltma
sonunda tam `2 MS/s`, `4.096` kompleks `ci8` örnek üretir.

Kilitli süzgeç zarfı ±800 kHz geçiş bandı ve ±1 MHz stopband başlangıcıdır.
Canlı HackRF yolunda çıkış merkezi fiziksel tuning merkezinden en az 1,25 MHz
uzakta seçilir; ürün profili 1,5 MHz ofset kullanır. Böylece zero-IF merkez
çıkıntısı çıkış Nyquist bandının dışında kalır. Kaynak veya merkez değişiminde
FIR gecikme hattı ve NCO fazı sıfırlanır. FIR grup gecikmesi 96 giriş örneğidir.

## PC→ZedBoard istek paketi

Sürüm 2 paketi 48 bayt little-endian başlık ve ardından bounded `ci8` yük taşır.
Başlık alanları sırasıyla şöyledir:

| Ofset | Boyut | Alan |
|---:|---:|---|
| 0 | 4 | `P0IQ` magic |
| 4 | 1 | sürüm `2` |
| 5 | 1 | örnek biçimi `1` = `ci8` |
| 6 | 2 | başlık boyu `48` |
| 8 | 4 | sıra numarası |
| 12 | 4 | frame kimliği |
| 16 | 2 | chunk indisi |
| 18 | 2 | chunk adedi |
| 20 | 8 | çıkış merkez frekansı, Hz |
| 28 | 4 | örnekleme hızı, Hz |
| 32 | 4 | kompleks örnek adedi |
| 36 | 4 | payload bayt adedi |
| 40 | 4 | payload IEEE CRC32 |
| 44 | 4 | ilk 44 baytın IEEE CRC32 değeri |

Genel codec en çok 131.072 bayt ve 1–65.535 chunk çözebilir. FPGA ürün yolu
bunun dar bir alt kümesidir: tek chunk, `2.000.000` örnek/s, `4.096` kompleks
örnek ve tam `8.192` bayt payload. Ağ köprüsü bu alanlardan herhangi biri
uyuşmazsa isteği DMA'ya göndermeden bağlantıyı kapatır.

## ZedBoard→PC yanıt paketi

Kartın sürümlü yerel ED hizmet yanıtı değiştirilmeden `P0RS` zarfına alınır.
Yanıt başlığı 24 bayttır: magic, sürüm `2`, yanıt türü `1`, başlık boyu,
istekle aynı sıra numarası, payload uzunluğu, payload CRC32 ve ilk 20 baytın
başlık CRC32 değeri. Payload en çok 16.384 bayttır. PC istemcisi sıra, uzunluk
ve iki CRC'yi doğrulamadan sonucu uygulamaya vermez.

## Akış kontrolü ve ağ sınırı

PC istemcisi ve Linux köprüsü en çok dört ardışık çerçeveyi yanıt beklemeden
boruhatlar. Daha büyük batch reddedilir. TCP akış kontrolü yavaş tüketicide
üreticiye backpressure uygular; sessiz drop veya sınırsız kuyruk yoktur.

Linux köprüsü yalnız yapılandırılmış IPv4 adresine bind eder, `0.0.0.0` kabul
etmez, backlog değerini `1` tutar ve yalnız yapılandırılmış PC IPv4 adresini
kabul eder. TCP çerçevelerini doğruladıktan sonra mevcut
`AF_UNIX/SOCK_SEQPACKET` kart hizmetine sürüm 3 kompakt istek olarak iletir.
Her yeni ağ oturumunun ilk karesi temporal reset taşır. Ağ süreci DMA aygıtını
doğrudan açmaz.

## Doğrulanan ve açık sınırlar

Host kabulünde süzgeç ripple değeri `0,00528 dB` altında, stopband tepesi
`−65,97 dB` bulunmuştur. Üç adet 1.024-kare koşusunda en düşük hız gerekli
`488,28125 kare/s` değerini geçmiştir; sıra hatası, queue drop ve doyum sıfırdır.
Python codec, taşınabilir C11 decoder ve gerçek Linux TCP→`SOCK_SEQPACKET`
dört-kare loopback yolu geçmiştir. Kanıt
`results/evidence/p0/phase07-host-loopback.json` dosyasındadır.

Doğrudan PC–ZedBoard 1 Gbps fiziksel linki ve kart üzerindeki ağ hızı geçmiştir.
Bilinen CI8 yaşam döngüsünün ardından yapılan beş adet 64+4.096-kare koşusunda
20.480/20.480 ölçüm karesi tamamlanmış; sıra hatası ve aday düşümü sıfır,
en düşük hız `504,759253742 kare/s` ve en düşük gerçek zaman marjı
`1,033746952` olmuştur. Kanıt
`results/evidence/p0/phase07-ethernet-physical-acceptance.json` dosyasındadır.

Ağ köprüsü kalıcı PetaLinux imajından soğuk açılış sonrası çalıştırılmıştır.
Değişken MAC tabanlı ad yerine tek fiziksel ağ arayüzü açılış betiğinde `auto`
seçilir; sıfır veya birden fazla fiziksel arayüzde başlangıç kapalı kalır. Ürün
varsayılanı güvenlik için kapalıdır ve kabul oturumunda açıkça etkinleştirilmiştir.
Canlı HackRF'nin kesintisiz callback akışı, 8→2 MS/s canlı kanal seçimi ve bu
canlı verinin FPGA sonucuna dönüşmesi henüz doğrulanmamıştır.
