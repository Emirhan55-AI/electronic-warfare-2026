# P0 Yerel ED Kart Hizmeti ABI v1/v2

## Amaç ve güvenlik sınırı

`p0-ed-service`, ZedBoard üzerindeki `/dev/p0-dma` aygıtının tek ürün sahibidir.
Aygıtın `root:root 0600` izni değiştirilmez. Hizmet açılışta aygıtı yetkili olarak
açar, yalnız `/run/p0-ed/p0-ed.sock` yerel soketini oluşturur ve ardından ek
gruplarını temizleyerek `p0ed` kullanıcı/grubuna geçer. TCP/UDP dinleyicisi,
uzaktan komut, istemciden dosya yolu veya kabuk çalıştırma yüzeyi yoktur.

Soket `AF_UNIX/SOCK_SEQPACKET`, sahibi `p0ed:petalinux`, modu `0660` olur. Böylece
operatör hesabının ek grup üyeliği gerekmez. Her bağlantı tam bir istek ve tam bir yanıtla
sınırlıdır; iki saniyelik alma/gönderme zaman aşımı uygulanır. Çekirdek dosya
izinleri bağlantı yetkisini denetler. İstek boyutu, sürüm, izinli bayraklar ve iki
CRC alanı geçmeden DMA veya algoritma durumu değiştirilmez.

## ABI uyumluluğu

ABI v1, yalnız tespit ve zamansal olay sonucu isteyen mevcut istemciler için byte
düzeyinde korunur. ABI v2 aynı hizmet üzerinde operatörce başlatılmış parametre
ölçümünü ekler. Hizmet isteğin sürümüyle yanıt verir; bilinmeyen sürüm, boyut,
bayrak veya ayrılmış alan sıfır olmadan reddedilir.

## ABI v1 istek mesajı

Bütün çok baytlı alanlar little-endian'dır. Mesaj boyu daima 8224 bayttır:

| Ofset | Boyut | Alan | Değer |
|---:|---:|---|---|
| 0 | 4 | magic | `0x31514550` |
| 4 | 2 | ABI sürümü | `1` |
| 6 | 2 | header boyu | `32` |
| 8 | 4 | mesaj boyu | `8224` |
| 12 | 4 | frame ID | `uint32` |
| 16 | 4 | I/Q boyu | `8192` |
| 20 | 4 | bayraklar | bit 0: temporal reset; diğer bitler sıfır |
| 24 | 4 | I/Q CRC32 | IEEE CRC32 |
| 28 | 4 | header CRC32 | ilk 28 baytın IEEE CRC32 değeri |
| 32 | 8192 | I/Q | 4096 adet `{I:int8,Q:int8}` örneği |

## ABI v1 yanıt mesajı

Header 48 bayttır. Başarılı yanıt 8724 baytlık açıkça serileştirilmiş
`phase06j_frame_result_v1` yüküyle toplam 8772 bayt olur. Hata yanıtı yalnız
48 bayt header taşır.

| Ofset | Boyut | Alan | Açıklama |
|---:|---:|---|---|
| 0 | 4 | magic | `0x31534550` |
| 4 | 2 | ABI sürümü | `1` |
| 6 | 2 | header boyu | `48` |
| 8 | 4 | mesaj boyu | `48` veya `8772` |
| 12 | 4 | frame ID | İstekle aynı kimlik |
| 16 | 4 | hizmet durumu | 0 başarı; 1 istek; 2 DMA; 3 zincir; 4 iç hata |
| 20 | 4 | sonuç boyu | 0 veya 8724 |
| 24 | 4 | ham aday sayısı | OS-CFAR sonucu |
| 28 | 4 | DMA durum bayrakları | MM2S, S2MM, geçerli çıktı, timeout, hata |
| 32 | 4 | sonuç CRC32 | Başarı yükünün IEEE CRC32 değeri |
| 36 | 8 | ayrılmış | sıfır |
| 44 | 4 | header CRC32 | ilk 44 baytın IEEE CRC32 değeri |

Sonuç içindeki reserved alanlar sıfırdır. Active/ended sayıları ayrı ayrı en fazla
64'tür. Olay, aday ve UQ28.30/UQ32.30 alanları native struct kopyasıyla değil,
alan alan little-endian serileştirilir. İstemci; mesaj boyunu, iki CRC'yi, reserved
alanları, sayaç sınırlarını ve header/sonuç frame ID eşitliğini doğrulamadan sonuç
yayınlamaz.

## ABI v2 parametre isteği

ABI v2 istek boyu 8272, header boyu 80 bayttır. İlk 32 baytın anlamı v1 ile
aynıdır; sürüm, header ve toplam boy değerleri sırasıyla `2`, `80` ve `8272`
olur. Header CRC ofset 76'da bulunur ve ilk 76 baytı kapsar. I/Q yükü ofset
80'de başlar.

| Ofset | Boyut | Alan | Açıklama |
|---:|---:|---|---|
| 20 | 4 | bayraklar | bit 0 reset, bit 1 parametre ölçümü, bit 2 yeni ölçüm başlangıcı |
| 24 | 4 | I/Q CRC32 | IEEE CRC32 |
| 28 | 4 | ayrılmış | sıfır |
| 32 | 8 | örnekleme hızı | Hz, `uint64`, sıfır olamaz |
| 40 | 8 | tuner merkez frekansı | Hz, `int64` |
| 48 | 8 | ölçüm niyeti kimliği | `uint64`, sıfır olamaz |
| 56 | 8 | temporal olay kimliği | `uint64`, sıfır olamaz |
| 64 | 2 | onaylı alt shifted bin | dahil |
| 66 | 2 | onaylı üst shifted bin | dahil |
| 68 | 8 | ayrılmış | sıfır |
| 76 | 4 | header CRC32 | ilk 76 baytın IEEE CRC32 değeri |

Parametre aralığı 8–512 bin genişliğinde olur ve iki yanında ölçüm referans
hücreleri için 36 bin bulunur. `PARAMETER_START`, `PARAMETER` olmadan geçersizdir.
Parametre bayrağı olmayan v2 isteğinde bütün parametre üstverisi sıfır olmak
zorundadır.

## ABI v2 yanıtı

ABI v2 header boyu 64 bayttır. Temporal sonuç 8724 bayt olarak aynen korunur.
Parametre sonucu varsa buna 128 baytlık yük eklenir ve başarılı en büyük yanıt
8916 bayt olur.

| Ofset | Boyut | Alan | Açıklama |
|---:|---:|---|---|
| 0–32 | 36 | ortak alanlar | v1 ile aynı anlam; header/mesaj boyları v2 değerleridir |
| 36 | 4 | parametre sonucu boyu | `0` veya `128` |
| 40 | 4 | parametre CRC32 | parametre yükünün IEEE CRC32 değeri |
| 44 | 4 | parametre şema sürümü | yük varsa `1`, yoksa `0` |
| 48 | 12 | ayrılmış | sıfır |
| 60 | 4 | header CRC32 | ilk 60 baytın IEEE CRC32 değeri |

128 baytlık parametre yükü; niyet/olay/frame kimliklerini, gözlem sayısını,
emisyon merkez frekansı, alt/üst OBW99 kenarı, işgal edilmiş bant genişliği,
kalibre edilmemiş kanal gücü ve SNR kestirimi alanlarını taşır. Her sayısal alan
`durum + neden + IEEE-754 binary64 değer` biçimindedir. Geçerli alanın nedeni
`NONE` ve değeri sonlu olmak zorundadır. Kullanılamayan veya belirsiz alan
operatöre sayı olarak yayımlanmaz. Dört kalite metriği wire üzerinde daima sonlu
değerdir; ölçüm tamamlanmadan mevcut olmayan metrikler sıfırla serileştirilir.

## İşleme ve iddia sınırı

Başarılı temel yol `ci8 → DMA → FPGA Hann/FFT/UQ28.30 güç → ARM OS-CFAR +
41-bin geniş bant kurtarma → PHASE-06I ABI v1 → PHASE-06J 2/3 temporal`
zinciridir. ABI v2 parametre isteği,
aynı karelerin FPGA güç çıktısını ve giriş `ci8` örneklerini dört ardışık
doğrulanmış gözlem boyunca ARM parametre çekirdeğine verir. Seçilen olay mevcut
karede doğrulanmış ve gözlenmiş olmalı, tepe bini onaylı aralıkta bulunmalı ve
referans bölgede başka doğrulanmış olay bulunmamalıdır. Koşul kaybında ölçüm
fail-closed sıfırlanır.

Hizmet temporal durumu ardışık istemci bağlantıları arasında korur. DMA
başarısızsa reset isteği dahil temporal durum değiştirilmez. Bu ABI; Ethernet
taşıma, canlı HackRF, dBm kalibrasyonu, taşıyıcı çizgisi/sinyal alanı ARM ölçümü,
sürekli gerçek-zaman throughput veya RF yayın başarısı kanıtı değildir.
