# ET Yerel Sinyal Üreteci Sözleşmesi

## Kapsam

`algorithms/et/native/signal_generator.cpp` ve `signal_generator.hpp`, sınırlı
bir tampon içine deterministik kompleks `int8` I/Q örnekleri üretir. C++17
kitaplığı C ABI v1 üzerinden `algorithms.et.NativeSignalGenerator` sınıfına
bağlanır. Üreteç ton, FSK, süpürme, PRBS, sinüs, kare, testere, üçgen, chirp,
AWGN ve DC biçimlerini destekler.

Bu bileşen bir RF yayın arka ucu değildir. Aygıt keşfi, USB erişimi, frekans
ayarı, kazanç ayarı, PortaPack ortak belleği veya HackRF TX çağrısı içermez.
Üretilen örnekler yalnız `OFFLINE` ve `LOOPBACK` matematiksel doğrulama girdisidir.

## Sınırlar

- ABI sürümü `1` olmalıdır.
- Örnekleme hızı 8 kHz–20 MHz aralığındadır.
- Tek çağrı en çok 5.000.000 kompleks örnek üretir.
- Normalize genlik `(0, 0.9]` aralığındadır.
- Tüm frekanslar Nyquist aralığının içinde kalır.
- Aynı yapılandırma ve seed aynı I/Q baytlarını üretir.
- Hatalı yapılandırma çıktı üretmeden reddedilir.
- Sonuç sözleşmesi `tx_state: KİLİTLİ` taşır. Bu alan yalnız üretecin bir RF
  çıkışına sahip olmadığını belirtir; ADR-0043'teki `CABLED_LAB` ortam
  yetkilendirmesini geri almaz.

## Derleme ve kullanım

```powershell
cmake -S algorithms/et/native -B build/et-signal-generator -G "MinGW Makefiles"
cmake --build build/et-signal-generator --config Release
```

Oluşan kitaplık açıkça verilen dosya yoluyla yüklenir:

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
```

Derlenmiş kitaplığın varlığı fiziksel RF yeteneği veya donanım kabulü sayılmaz.
Kullanıcının 8 Eylül 2026 Faraday laboratuvar onayı `CABLED_LAB` politika
kilidini ADR-0043 ile kaldırmıştır; bu üreteç sözleşmesi ise yalnız bellek içi
I/Q sınırında kalır. TX arka ucu, HackRF ayarı veya fiziksel kabul bu sözleşmeyle
sağlanmaz. PHASE-10–12 donanım kapıları ayrıca doğrulanır.
