# Referans Spektrum Sözleşmesi

## Amaç ve kapsam

PHASE-02 spektrum zinciri, SigMF `ci8` ve `ci16_le` çerçeveleri için floating-point PC golden modelidir. İlerideki ZedBoard PL uygulaması bu modelle karşılaştırılacaktır; bu katman PL iç sayı biçimini veya sabit nokta genişliğini belirlemez.

Zincir `bounded çerçeve okuma → datatype full-scale ölçekleme → isteğe bağlı DC giderimi → periyodik Hann → FFT → güç/PSD → frekans ekseni` sırasını izler. Sinyal var/yok kararı, CFAR, sınıflandırma veya parametre çıkarımı yapmaz.

## Giriş ve çerçeveleme

- `ci8`: `x[n] = (I[n] + jQ[n]) / 128`
- `ci16_le`: `x[n] = (I[n] + jQ[n]) / 32768`
- Çıktı `complex128` olur. Bu sabit datatype yorumudur; veri bağımlı otomatik normalizasyon, AGC, clipping veya datatype dosya dönüşümü değildir.
- Varsayılan ve PHASE-02 doğrulama çerçevesi `N=4096` karmaşık örnektir.
- `Fs` ve merkez frekansı metadata'dan alınır; algoritmada 8 MS/s veya başka bir kayıt değeri sabitlenmez.
- Yalnız tam çerçeveler okunur. Eksik son çerçeve düşürülür ve sıfırla doldurulmaz.
- Her `read_frame(index)` çağrısı data dosyasını yalnız `rb` modunda açar, `index × frame_size_bytes` konumuna gider ve tam bir çerçeve okur. Bütün dosya belleğe alınmaz veya hashlenmez.

## DC ve Hann

DC giderimi varsayılan kapalıdır. Açıldığında `xDC[n] = x[n] - mean(x)` işlemi pencerelemeden önce uygulanır.

Periyodik Hann:

`w[n] = 0,5 - 0,5 cos(2πn/N)`

Bu pencere için koherent kazanç `Gc=0,5`, ortalama pencere gücü `U=0,375` ve eşdeğer gürültü bant genişliği `1,5 × Fs/N` olur.

## FFT, güç ve PSD

İleri FFT ölçeklenmez:

`X[k] = Σ xDC[n]w[n] exp(-j2πkn/N)`

Pozitif kompleks üstel pozitif frekans binine düşer. İki taraflı kompleks spektrum kullanıldığı için pozitif frekanslara iki kat katsayısı uygulanmaz.

- Genlik: `A[k] = |X[k]| / (N Gc)`
- Bin/ton gücü: `Pbin[k] = A[k]²`
- PSD: `Sxx[k] = |X[k]|² / (Fs Σw[n]²)`
- dB hesabı: `10 log10(max(value, 10⁻²⁰))`
- Sayısal alt sınır: `-200 dB`

`dBFS/bin`, Hann koherent kazancı düzeltilmiş bin-merkezli ton gücüdür. Geniş bant gürültü gücü, fiziksel dBm veya kalibre edilmiş saha ölçümü değildir. Gürültü yoğunluğu karşılaştırmasında pencere gücü düzeltilmiş iki taraflı `dBFS/Hz` PSD kullanılır. dBm dönüşümü ancak gerçek RF zinciri kazançları, kayıpları ve kalibrasyonu belirlendiğinde ayrı karara bağlanır.

## Ortalama ve eksen

Üstel ortalama logaritmadan önce FFT gücünde yapılır:

`Q̄0=Q0`

`Q̄m=αQm+(1-α)Q̄m-1`

Varsayılan `α=0,2` değeridir. Kaynak, DSP ayarı, görüntü türü veya sıralı olmayan çerçeve konumu değiştiğinde geçmiş sıfırlanır.

Frekans hücresi `Δf=Fs/N` olur. `fftshift` sonrası ofset ekseni `[-Fs/2, Fs/2-Δf]`, mutlak eksen `fc + foffset` biçimindedir.

## Golden fixture

`known-tone-ci8`, matematiksel olarak kusursuz bir sinüs değildir. On altı örneklik signed-integer lookup tablosunun tekrarından oluşur ve küçük, deterministik nicemleme harmonikleri içerir. Golden kapı diğer bütün binlerin sıfır olduğunu varsaymaz.

Zorunlu ölçütler:

- Fixture SHA-256/SHA-512 değerleri PHASE-01 manifestiyle eşleşir.
- Dört çerçevenin tamamında baskın unshifted index `256`, shift edilmiş index `2304` olur.
- Baskın ofset `+500.000 Hz`, mutlak frekans `100.500.000 Hz` olur.
- Genlik yaklaşık `0,7802479253 FS`, bin/ton gücü `-2,155347549 dBFS/bin`, PSD `-36,82356053 dBFS/Hz` değeridir.
- Shift edilmiş eksen 4096 değerden oluşur; uçları `-4.000.000 Hz` ve `+3.998.046,875 Hz` olur.
- Bütün çıktılar sonludur.

İndisler ve hashler kesin; frekanslar `atol=1e-9 Hz`, lineer ölçümler `atol=1e-12/rtol=1e-10`, dB ölçümleri `atol=1e-8 dB` ile doğrulanır. Tam kayan noktalı spektrum dizisinin hash'i platformlar arası başarı kapısı değildir.
