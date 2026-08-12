# SigMF Giriş Sözleşmesi

## Amaç ve sınır

PHASE-01 yalnız metadata, binary I/Q yerleşimi ve örtüşmesiz çerçeveleme sözleşmesini tanımlar. FFT, Hann, PSD, normalizasyon, yeniden örnekleme ve örnek değeri dönüşümü yapmaz. KTR teknik parametrelerin bağlayıcı kaynağı değildir; yalnız yarışma görevleri ve genel algoritma sırası korunur.

## Profil A — Kanonik `ci8` değişim biçimi

`ci8`, HackRF/PC giriş, kayıt ve sistemler arası değişim biçimidir. FPGA PL iç veri biçimi veya sonraki sabit nokta genişliği değildir; bunlar DSP/RTL fazında ayrı mühendislik kararı olacaktır.

- I ve Q signed 8-bit değerlerdir; düzen `[I0,Q0,I1,Q1,...]` ve karmaşık örnek başına 2 byte'tır.
- Tek kanal zorunludur. `core:num_channels` yoksa SigMF varsayımı `1/defaulted`, mevcut `1` ise `1/explicit` raporlanır.
- Sample rate metadata'dan alınır ve genel parser'da sabitlenmez. Golden fixture 8 MS/s kullanır.
- Bir çerçeve 4096 karmaşık örnek ve 8192 byte'tır; çerçeveler örtüşmez.
- Tam I/Q çiftlerinden oluşan eksik son çerçeve düşürülür ve raporlanır. Tek byte artığı bozuk I/Q çifti hatasıdır.
- Otomatik normalizasyon, ölçekleme, clipping veya datatype dönüşümü yoktur.

## Profil B — Genel çevrimdışı `ci16_le` kaynak biçimi

`ci16_le`, desteklenen genel çevrimdışı kaynak datatype profilidir. I ve Q little-endian signed 16-bit değerlerdir; düzen `[I0,Q0,I1,Q1,...]`, karmaşık örnek başına 4 byte ve çerçeve başına 16.384 byte'tır. Sample rate, merkez frekansı, donanım ve kaydedici her datasetin kendi metadata'sından alınır.

İncelenen `ism_band_24` kaydı bu genel profilin belirli bir örneğidir: 56 MS/s, 2,43 GHz, USRP B210 ve GNU Radio değerleri yalnız bu datasete aittir. Bunlar genel `ci16_le` kabul koşulu, canlı HackRF temsili veya KTR performans uyumluluğu değildir.

## Metadata kabul kuralları

- Metadata UTF-8 ve geçerli JSON olmalıdır.
- PHASE-01 `core:version = 1.0.0` değerini destekler.
- Desteklenen `core:datatype`, pozitif/sonlu `core:sample_rate` ve sayısal/sonlu capture `core:frequency` zorunludur.
- Tam olarak bir capture olmalı ve `core:sample_start = 0` olmalıdır. Çoklu capture reddedilir; ilk capture sessizce seçilmez.
- Tek kanal zorunludur. Eksik `core:num_channels`, SigMF varsayımına göre `1/defaulted` olur.
- Frekans hücresi metadata-temelli `Δf = Fs / 4096` ile hesaplanır.
- Parser metadata'daki lisans metnini değiştirmeden raporlar; lisans kabul kararı vermez.

## Dosya keşfi

Standard mod yalnız gerçek `.sigmf-meta` uzantısını kabul eder ve aynı temel addaki `.sigmf-data` dosyasını arar. `.sigmf-meta.txt` sessizce standart çift kabul edilmez.

Explicit modda metadata ve data yolları ayrı verilebilir. Metadata uzantısı standart değilse data yolu zorunludur, ad tahmini yapılmaz ve `nonstandard_metadata_extension` uyarısı üretilir. Mutlak yollar tracked belge veya kanıt JSON'una yazılmaz.

## Hata ve uyarı modeli

Hatalar sabit kodlarla raporlanır: metadata bulunamaması, UTF-8/JSON bozukluğu, desteklenmeyen core sürümü/datatype/kanal sayısı/capture sayısı, geçersiz capture başlangıcı, eksik explicit data yolu, bulunamayan data ve bozuk I/Q çifti.

Parser uyarıları yalnız `nonstandard_metadata_extension`, `channel_count_defaulted` ve `incomplete_frame_dropped` durumlarıdır. `license_unverified`, harici dataset kabul ve manifest politika katmanına aittir.

## Harici veri güvenliği

Normal parser data payload'ını veya 11,3 GB kaynağı hashlemez; yalnız metadata ve dosya boyutunu inceler. Kesit çıkarıcı kaynağı yalnız `rb` modunda açar ve gerekli byte aralığını okur. Kaynak boyutu ile mtime öncesi/sonrası karşılaştırılır; bu kontrol kriptografik bütünlük kanıtı değildir.
