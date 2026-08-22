# Analog Telsiz Alıcısı: I/Q'dan 48 kHz Sese

Bu not, doğrudan `reference/monitoring/dsp.py` içindeki PHASE-05 alıcısını
açıklar. Zincir kayıtlı/sentetik I/Q üzerinde çalışan HOST referansıdır; canlı
HackRF, FPGA veya fiziksel RF kabulü değildir.

## I/Q nedir?

Bir dar bant RF sinyali kompleks taban bantta

`z[n] = I[n] + jQ[n]`

olarak tutulur. I ve Q, aynı sinyalin 90° faz ayrımlı iki bileşenidir. Kompleks
gösterim genlik ve anlık fazı birlikte korur; bu nedenle pozitif/negatif frekans
ofsetleri ve FM faz değişimi ayırt edilebilir. Uygulamada `SigMFFrameSource`,
`ci8` örneklerini `complex128` diziye dönüştürür; dinleme worker'ı dört adet
4096 örnekli kareyi birleştirir.

## Kanal seçimi ve DDC

Tespit edilen taşıyıcı, kayıt merkezinden `f0` kadar uzaktaysa kanal sıfıra
taşınır:

`z_DDC[n] = z[n] · exp(-j 2π f0 n / Fs)`

`AnalogMonitor.process()` bu osilatörü üretip IQ ile çarpar. Örneğin 192 kS/s
IQ içinde `+24 kHz` AM taşıyıcı için `f0=+24 kHz` seçilir. İşaret yanlışsa
taşıyıcı sıfıra gelmez; filtre sinyali zayıflatır veya yanlış kanalı geçirir.

## Neden alçak geçiren filtre var?

Karıştırma istenen kanalı sıfıra taşır fakat komşu kanalları silmez. Kod,
kanal bant genişliğinin `%45`ini kesim olarak kullanan 129 tap Hamming-pencereli
FIR uygular. Filtre geçici rejiminin her iki ucundan 64 giriş örneği atılır.
Çok dar BW faydalı yan bantları keserek sesi bozar; çok geniş BW komşu kanal ve
gürültüyü geçirir.

## Decimation ve 48 kHz'e yeniden örnekleme

Decimation, örnekleme hızını düşürmeden önce alias oluşmasını engelleyecek
filtreleme yapıp daha seyrek örnek almaktır. Bu uygulama ayrı bir tam-sayı
`x[M·n]` decimatorü kullanmaz: kanal filtresinden sonra zaman ekseninde lineer
interpolasyonla doğrudan 48 kHz'e yeniden örnekler. Dolayısıyla doğru ifade
"filtreli resampling"dir.

IQ hızı RF kanalını temsil eder (`192 kS/s` fixture); ses hızı hoparlör/WAV
alanını temsil eder (`48 kS/s`). 48 kHz mono PCM16, yaygın ses aygıtları ve WAV
araçlarıyla uyumludur ve 24 kHz Nyquist ses bandı sağlar.

## AM ve NFM demodülasyonu

AM'de bilgi zarf üzerindedir:

`a[n] = |z_DDC[n]|`

Kod zarfın DC ortalamasını çıkarır. NFM'de ardışık örnek faz farkı kullanılır:

`f_anlık[n] = Fs/(2π) · angle(z[n] · conj(z[n-1]))`

Bu ifade taşıyıcının ortak fazını yok eder ve örnekler arası frekans değişimini
ses sinyaline dönüştürür. Ardından 48 kHz alanında 65 tap ses FIR filtresi,
geçici rejim kırpma, DC giderme ve tepe normalizasyonu uygulanır.

Bu PHASE-05 zincirinde analog yayın standartlarına özgü 50/75 µs FM
de-emphasis uygulanmıyor. UI veya belge bunu varmış gibi göstermez.

## Çalışılmış NFM örneği

Fixture gerçeği: `Fs=192000 Hz`, taşıyıcı ofseti `-24000 Hz`, kaynak ses
`2000 Hz`, kanal BW `16000 Hz`. Dört kare `16384` IQ örneğidir. Filtre/resample
sonunda `3999` adet 48 kHz mono örnek, yani `0,0833125 s` ses üretilmiştir.
Bağımsız Blackman-periodogram oracle'ı `2003,90625 Hz` bulmuştur:

`hata = 2003,90625 - 2000 = 3,90625 Hz`

İzin `12 Hz`, normalize korelasyon `0,9959166`, clipping `0`; sonuç PASS'tir.

## Terminal ve UI yürüyüşü

| Alan | İçerik |
|---|---|
| INPUT | AM veya NFM SigMF; doğrulanmış olay; mod; taşıyıcı ofseti; kanal BW |
| PROCESS | DDC → 129 tap LPF → AM/NFM demod → 48 kHz resample → 65 tap ses LPF → PCM16 |
| EQUATION | AM: `|z[n]|`; NFM: `angle(z[n]conj(z[n-1]))` |
| OUTPUT | Sonlu 48 kHz mono ses, tepe/RMS, baskın ton, WAV ve varsa oynatma |
| UI'da bakılacak | `REPLAY / HOST`, doğru taşıyıcı/BW, 48 kHz, süre, sıfır hata durumu |

Uygulamayı `python -B -m host.operator_console` ile açın. AM fixture için
`datasets/fixtures/phase05/am-tone-ci8.sigmf-meta`, NFM için
`nfm-tone-ci8.sigmf-meta` seçilir. Replay başlatılır, doğrulanmış olay seçilir,
`Dinleme` sekmesinde doğru mod seçilip `Dinle` basılır. Ses aygıtı yoksa
`WAV Dışa Aktar` kullanılır. Otomatik kabul WAV'ları ayrıca
`build/acceptance/audio/` altındadır. `*-listen.wav` dosyaları, 83 ms kanonik
çıktıyı yeni örnek üretmeden 24 kez art arda koyar; yaklaşık iki saniyelik tonu
insanın daha rahat duymasını sağlar.
