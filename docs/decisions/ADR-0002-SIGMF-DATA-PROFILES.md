# ADR-0002: SigMF Veri Profilleri

- Durum: **Accepted**
- Karar tarihi: 2026-08-12

## Bağlam

Satın alınmış sistem 2× HackRF One, ZedBoard ve laptoptan oluşur. KTR teknik parametrelerin bağlayıcı kaynağı değildir; yalnız yarışma görevleri ve genel algoritma sırası korunur. bladeRF için yazılmış 56 MHz hedefi HackRF sistemine aktarılmaz.

## Karar

İki ayrı profil desteklenecektir:

1. `ci8`, HackRF/PC giriş, kayıt ve sistemler arası değişim biçimidir. Başlangıç golden fixture'ı 8 MS/s kullanır; genel parser sample rate'i metadata'dan alır.
2. `ci16_le`, gerçek kayıtların source-native incelenmesi için genel çevrimdışı kaynak biçimidir. Örnek değerleri PHASE-01'de `ci8`e dönüştürülmez.

Her iki profilde tek kanal, `[I0,Q0,I1,Q1,...]`, 4096 örneklik örtüşmesiz çerçeve ve metadata-temelli `Fs/4096` hesabı kullanılır. PL iç veri biçimi bu kararın parçası değildir ve DSP/RTL fazına bırakılmıştır.

## Golden fixture tercihi

`known-tone-ci8`, 8 MS/s ve 100 MHz merkez frekansında 16.384 örneklik, +500 kHz kompleks tondur. PHASE-01 mühendislik tercihi olarak tepe genliği `100 count` seçilmiştir. Bu değer signed ci8 sınırlarından headroom bırakır ve platform bağımsız 16 örneklik tam sayı lookup tablosuna izin verir. RF genliği, dBm veya gerçek HackRF kazancı değildir.

## Harici dataset kararı

`ism_band_24` kaydı `ci16_le`, 56 MS/s, 2,43 GHz, USRP B210 ve GNU Radio özelliklerine sahiptir. Bunlar yalnız incelenen datasetin değerleridir; tüm `ci16_le` girdiler için şart değildir. Kayıt `DÖNÜŞTÜRÜLEREK KULLANILABİLİR`, ancak PHASE-01'de dönüşüm veya yeniden örnekleme yapılmaz.

Gerçek metadata adı `.sigmf-meta.txt` olduğu için yalnız explicit modda ve açık data yoluyla uyarılı okunur. Kaynak ve türetilmiş binary kesit Git dışında kalır. Metadata'daki `CC BY-SA` metni kesin sürüm veya kaynak URL sağlamadığından manifest `license_status: unverified` taşır.

## Sonuçlar

- Sentetik fixture ve repository sözleşmesi zorunlu başarı kapısıdır.
- Harici dataset entegrasyonu mevcutsa `passed`, mevcut değilse genel başarıyı düşürmeden `skipped` olur.
- Sample rate veya frekans çözünürlüğü algoritmada sabitlenmez.
- 10 ve 20 MS/s çalışma, sonraki fazlarda ayrı doğrulama noktalarıdır.
- FFT ve diğer DSP işlemleri PHASE-02 veya sonraki fazlara aittir.
