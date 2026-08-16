# P0 Block B0 HackRF RX Hazırlık Sözleşmesi

## Makine-local araç zinciri

Computer-1, Windows 11 Home 64 bit (`10.0.26200`) ve Python 3.13.7 kullanır.
Python yürütülebiliri
`C:\Users\emirhan55\AppData\Local\Programs\Python\Python313\python.exe`
ve 64 bittir. Kurulum öncesi PATH içinde `C:\msys64\ucrt64\bin` zaten vardı;
`winget`, Chocolatey ve MSYS2/pacman denetlendi. HackRF araçları, libhackrf veya
Python HackRF binding'i önceden bulunmadı; bu nedenle aynı aracın ikinci bir
kopyası kurulmadı.
Mevcut MSYS2 UCRT64 kurulumu üzerinden yalnız
`mingw-w64-ucrt-x86_64-hackrf 2026.01.2-1` kurulmuştur. Paket upstream Great
Scott Gadgets HackRF kaynağını kullanır; MSYS2 paketi SHA-256 ve imzayla
doğrulanmıştır. Bir SDR GUI suite veya rastgele DLL kurulmamıştır.

| Bileşen | Konum |
|---|---|
| `hackrf_info` | `C:\msys64\ucrt64\bin\hackrf_info.exe` |
| `hackrf_transfer` | `C:\msys64\ucrt64\bin\hackrf_transfer.exe` |
| `hackrf_sweep` | `C:\msys64\ucrt64\bin\hackrf_sweep.exe` |
| `libhackrf` | `C:\msys64\ucrt64\bin\libhackrf.dll` |
| `libusb` | `C:\msys64\ucrt64\bin\libusb-1.0.dll` |

UCRT64 `bin` klasörü kurulumdan önce PATH içindeydi; yeni PATH değişikliği
yapılmadı. `hackrf_info` ve `libhackrf` sürümü `2026.01.2 (API 0.9.1)` olarak
çalışmış, `hackrf_transfer -h` RX için `-d -r -f -s -n -a -l -g` seçeneklerini
sunmuştur. Fiziksel aygıt bulunmadığından `No HackRF boards found` beklenen B0
sonucudur; bu bir canlı RX kanıtı değildir.

Self-test çıktısı ve dönüşleri:

```text
hackrf_info version: 2026.01.2
libhackrf version: 2026.01.2 (0.9.1)
No HackRF boards found.
hackrf_info exit: 1 (beklenen: fiziksel cihaz yok)
hackrf_transfer -h exit: 0
```

`ldd`, iki çalıştırılabilir için `libhackrf.dll`, `libusb-1.0.dll` ve
`libwinpthread-1.dll` bağımlılıklarını UCRT64 `bin` altından çözmüştür; eksik DLL
bildirimi yoktur. Paket kaynağı `https://github.com/greatscottgadgets/hackrf`,
paket doğrulaması `SHA-256 Sum` ve `Signature` olarak raporlanmıştır.

## Kanonik üretim yöntemi

Üretim backend'i yalnız bounded `hackrf_transfer` subprocess yöntemidir. Komut
shell stringi değil argv dizisidir ve `-d <ED_RX serial> -r <bounded-file>`
zorunludur. Backend TX metodu sunmaz; `-t`, `-x`, `-c` ve `-R` üretemez.
Native HackRF `ci8`, signed `I,Q` byte çiftleri olarak açıkça `complex128`
`I/128 + jQ/128` biçimine çevrilir.

`SearchRequest` çevirisi her tuning penceresini `HackRFHostRxSource` bounded
kuyruğundan alır. Backend tamamlanan/toplam pencere ilerlemesini callback ve
`last_progress` ile sunar; fiziksel throughput veya tarama süresi tahmin etmez.

`config/p0/hackrf_ed_rx.json` rolü `ED_RX`, cihaz türünü `HackRF One` olarak
kilitler. Fiziksel cihaz görülmeden seri `null`, arama aralıkları boş kalır.
Seri atanmadan capture; aralık atanmadan `UNKNOWN` araması fail-closed'dur.

Tuning mühendislik profili 8 MS/s, her kenarda 1 MHz guard, 6 MHz kullanılabilir
analiz genişliği ve 0,5 MHz overlap kullanır. Adım 5,5 MHz'dir. `JUDGE_FREQUENCY`
tek merkez tuning'i; `JUDGE_BAND` boşluksuz bir veya daha çok pencere;
`UNKNOWN` yalnız config'teki bounded aralıkları üretir. Bu değerler ölçülmüş
canlı throughput veya yarışma-wide tarama süresi iddiası değildir.

## Sonraki fiziksel oturum

1. Computer-1'e yalnız ED için seçilen HackRF-1'i bağlayın.
2. USB enumeration tamamlanınca repository kökünde
   `python -B scripts/check_hackrf_rx_ready.py` çalıştırın.
3. Çıktıdaki gerçek seri ve board bilgilerini kaydedin; birden çok cihaz varsa
   hiçbirini otomatik seçmeyin.
4. Gerçek ED seri numarasını `config/p0/hackrf_ed_rx.json` içindeki `serial`
   alanına yazın; bounded `search_ranges_hz` aralıklarını görev planına göre atayın.
5. Aynı readiness komutunu yeniden çalıştırıp configured serial eşleşmesini görün.
6. `hackrf_info` ile kimliği yeniden doğrulayın.
7. Önce bounded RX kabulü yapın; received byte/sample sayısı ve hash kanıtını alın.
8. Ancak bundan sonra `python -B -m host.operator_console.application` ile UI'yı
   açıp `HackRF Canlı RX` kaynağını seçin.
9. Sırayla `Hakem Frekans Bildirdi`, `Hakem Bant Bildirdi` ve bounded
   `Bilinmeyen Frekans` kabulünü çalıştırın.

Bu prosedür RX-only'dir. Fiziksel capture, canlı spektrum/waterfall, gerçek
detector sonucu, dBm, ZedBoard/FPGA yürütümü veya herhangi bir TX bu B0
checkpoint'inde yapılmamış ve doğrulanmamıştır.
