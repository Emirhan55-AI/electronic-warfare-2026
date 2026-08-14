# PHASE-06A RTL Frame İstatistik Sözleşmesi

## Yetenek sınırı

Bu sözleşme yalnız `ci8 → AXI4-Stream → 4096 örnekli frame denetimi → kompleks güç ve frame istatistikleri` zincirini tanımlar. FFT, Hann, PSD, detector, canlı HackRF, Ethernet, DMA, ZedBoard kart çalışması ve RF/TX kapsam dışıdır.

## Giriş

| Alan | Sözleşme |
|---|---|
| Saat/reset | `aclk`; aktif düşük senkron örneklenen `aresetn` |
| El sıkışma | Aktarım yalnız `s_axis_tvalid && s_axis_tready` olduğunda kabul edilir |
| Veri | `s_axis_tdata[7:0]`: signed I; `s_axis_tdata[15:8]`: signed Q |
| Frame sonu | 4096. kabul edilen örnekte `s_axis_tlast=1` |
| Backpressure | Kaynak `tvalid && !tready` süresince `tdata` ve `tlast` değerlerini sabit tutar |

Bir giriş buffer'ı sonuç backpressure'ı sırasında en fazla bir transferi tutar. Sessiz veri kaybı, sınırsız kuyruk veya hazır olmayan transferin tüketilmesi yoktur.

## Tam sayı matematiği

`ci8` aralığı `[-128,127]` olur. Tek örnek kompleks gücü:

`P[n] = I[n]² + Q[n]²`

| Nicelik | Genişlik | En büyük değer |
|---|---:|---:|
| Bileşen karesi | 15 bit unsigned | 16384 |
| Kompleks güç | 16 bit unsigned | 32768 |
| 4096 örnek enerji toplamı | 28 bit unsigned | 134217728 |
| Tepe indisi | 12 bit unsigned | 4095 |
| Örnek sayısı | 13 bit unsigned | 4096 |

Enerji ve güç doygunlaştırılmaz; seçilen genişlikler matematiksel en kötü durumu kapsar. Eşit tepe güçlerinde ilk indeks korunur.

## Sonuç ve protokol durumu

Sonuç ready/valid arabirimi backpressure altında sabittir. Alan sırası 72 bit golden sözcükte şöyledir:

`energy[27:0], peak_power[15:0], peak_index[11:0], sample_count[12:0], protocol_error, error_code[1:0]`

Hata kodları:

- `0`: temiz frame.
- `1`: 4096. örnekten önce `TLAST`.
- `2`: 4096. örnekte `TLAST` yok.

Erken `TLAST` mevcut kısa frame'i hata sonucu olarak kapatır. Eksik `TLAST`, 4096 örneklik sonucu hata olarak kapatır ve blok bir sonraki geç `TLAST` aktarımına kadar veriyi kontrollü biçimde bırakır; ardından temiz frame sınırına döner. Reset kısmi frame'i, bekleyen sonucu, buffer'ı ve toparlanma durumunu temizler.

## Doğrulama sınırı

PHASE-01 fixture'ının dört frame'i, signed uç değerler, sıfır, alternasyon, impulse, eşit tepe, erken/eksik/geç `TLAST`, rastgele backpressure, reset ve ardışık frame senaryoları bit-doğru Python modeli ve self-checking testbench tarafından paylaşılır. Simülatör yoksa RTL çalıştırılmış sayılmaz; evidence `skipped/tool_unavailable` ve faz durumu `prepared_not_simulated` olur.

## Gelecek bağlantı sınırı

PHASE-07 AXI DMA adaptörünün bu çekirdeğe bağlanabilmesi için çıkışında aynı 16 bit `ci8`, ready/valid ve 4096 örnekte `TLAST` sözleşmesini üretmesi beklenir; bu adaptör PHASE-06A'da uygulanmaz. Gelecek FFT bloğunun giriş genişliği, ölçekleme, gecikme, konfigürasyon ve `TLAST` davranışı ayrı bit-doğru kararla tanımlanacaktır. Bu dosya AMD FFT IP, AXI DMA veya ZedBoard bağlantısının mevcut olduğunu göstermez.
