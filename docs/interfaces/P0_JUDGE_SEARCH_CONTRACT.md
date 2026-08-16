# P0 Hakem Arama Modları Sözleşmesi

## Domain modeli

İç frekans birimi yalnız Hz'dir. UI MHz gösterir ve `×1.000.000` dönüşümü domain
constructor'larında açıkça test edilir.

| UI etiketi | Domain modu | Davranış |
|---|---|---|
| `Bilinmeyen Frekans` | `UNKNOWN` | Backend tarama planındaki bütün tuning pencerelerini işler |
| `Hakem Bant Bildirdi` | `JUDGE_BAND` | Yalnız `[alt, üst]` bandıyla kesişen adayları analiz eder |
| `Hakem Frekans Bildirdi` | `JUDGE_FREQUENCY` | Verilen merkez çevresinde bounded 50 kHz pencereyi analiz eder |

Üç mod da aynı `SearchRequest → SearchAcquisitionBackend → P0SearchEngine`
sınırını kullanır. Frekans verilmesi tespiti atlamaz: her pencere IQ→periyodik
Hann→FFT→güç→OS-CFAR→2/3 confirmation→zorunlu parametre zincirinden geçer.

`JUDGE_BAND` için alt ve üst sonlu, alıcı zarfında, `alt < üst` ve span en fazla
20 MHz olmalıdır; sınırlar sessizce yer değiştirmez. `JUDGE_FREQUENCY` merkezi
1 MHz–6 GHz zarfında olmalıdır. NaN/sonsuz, ters bant, aşırı span ve zarf dışı
değerler fail-closed reddedilir.

Bugünkü backend iki frame'li deterministik `REPLAY/HOST` tuning penceresidir.
İkinci frame bağımsız deterministik gürültü taşır; aynı replay gürültüsünü iki kez
görerek false-alarm doğrulama yapılmaz. `HackRFHostRxSource` ileride aynı backend
sözleşmesini uygular; bu checkpoint canlı HackRF scan/tune kanıtı değildir.
