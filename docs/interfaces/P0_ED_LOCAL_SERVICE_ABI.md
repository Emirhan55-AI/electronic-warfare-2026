# P0 Yerel ED Kart Hizmeti ABI v1

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

## İstek mesajı

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

## Yanıt mesajı

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

## İşleme ve iddia sınırı

Başarılı istek yolu `ci8 → DMA → FPGA Hann/FFT/UQ28.30 güç → ARM OS-CFAR →
PHASE-06I ABI v1 → PHASE-06J 2/3 temporal` zinciridir. Hizmet temporal durumu
ardışık istemci bağlantıları arasında korur. DMA başarısızsa reset isteği dahil
temporal durum değiştirilmez. Bu ABI; Ethernet taşıma, canlı HackRF, parametre
çıkarımı, sürekli gerçek-zaman throughput veya RF yayın başarısı kanıtı değildir.
