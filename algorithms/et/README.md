# ET algoritmaları

Bu bileşen yerel `OFFLINE`, `LOOPBACK`, `REPLAY` ve politika olarak onaylanmış
Faraday `CABLED_LAB` görev durumlarını içerir. `CABLED_LAB` görev kabulü ortam
yetkisini günlüğe kaydeder; mevcut kaynak hâlâ bir SDR aygıtı açmaz, RF frekansı
veya kazancı ayarlamaz ve yayın komutu vermez. Genel/açık alan donanım TX yolu
kilitlidir.

Python tabanlı doğrulanmış sürekli, arabakışlı, analog ve GNSS modelleri mevcut
ürün arayüzünü besler. `native/signal_generator.cpp` ile
`native/signal_generator.hpp` ise ek bir C++17 yerel I/Q üretecidir. C++ üreteç
derlendikten sonra Python içinden şöyle kullanılabilir:

```python
from algorithms.et import NativeSignalConfig, NativeSignalGenerator, NativeWaveform

generator = NativeSignalGenerator()
result = generator.generate(
    NativeSignalConfig(
        waveform=NativeWaveform.SINE,
        sample_rate_hz=48_000,
        duration_seconds=1.0,
        frequency_hz=1_000.0,
    )
)
iq_samples = result.samples
```

`iq_samples` yalnız bellekteki kompleks taban bant örnekleridir. Fiziksel RF
çıkışı değildir. Ayrıntılı sınırlar
`docs/interfaces/ET_SIGNAL_GENERATOR_CONTRACT.md` belgesindedir.
