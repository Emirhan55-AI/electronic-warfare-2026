# HackRF RX Host Acquisition Sözleşmesi

## Bileşen sınırı

`host/acquisition/` Qt ve DSP import etmez. Gerçek ve deterministik test backend'leri aynı `HackRFBackend` sözleşmesini uygular. Controller yalnız bu sözleşmeyi kullanır; UI ve controller `subprocess` çağırmaz. Gerçek backend `hackrf_info`, `hackrf_transfer` ve `hackrf_sweep` dışında executable kabul etmez.

Araç keşfi dosya sistemi üzerinden yapılır. Güvenli yardım sorguları açık `argv`, `shell=False`, iki saniyelik zaman aşımı ve 32.768 byte stdout/stderr sınırıyla çalışır. Cihaz keşfi ancak operatör denetim düğmesine bastığında ve gerekli araç doğrulandığında worker içinde yapılabilir. B0'da araç self-test'i çalıştırılmış, fiziksel cihaz bulunmadığından discovery `NO_DEVICE` dönmüştür; RF alımı çalıştırılmamıştır.

Discovery sonuçları `TOOLCHAIN_UNAVAILABLE`, `NO_DEVICE`, `ONE_DEVICE`,
`MULTIPLE_DEVICES` ve `DEVICE_ERROR` olarak ayrıdır. Bir veya daha çok cihaz
bulunması capture yetkisi vermez; `ED_RX` config'indeki gerçek seriyle eşleşme
zorunludur.

## Bounded süreç ve veri

- Aynı anda en fazla bir dış süreç bulunur.
- İptalde önce `terminate`, 250 ms içinde kapanmazsa `kill` uygulanır.
- Capture örnek sayısı 4.096–65.536 aralığında ve 4.096'nın katıdır; varsayılan 16.384'tür.
- Capture tam olarak `sample_count × 2 byte` olmalıdır. Tek kalan byte, kısa ve uzun çıktı typed hata üretir.
- Gerçek capture yalnız işletim sistemi geçici alanındaki bir dosyaya yazılır; başarı, hata, iptal ve kapanış sonunda dosya silinir.
- `ci8`, signed 8-bit interleaved I/Q'dur ve `128` ile normalize edilerek mevcut kompleks floating-point girişe çevrilir.
- Bounded frame kaynağı yalnız dört çerçevelik varsayılan capture'ı bellekte tutar. Host RX source tek producer thread, en çok 8 frame kuyruk, drop/error sayacı ve bounded stop/join kullanır; sınırsız kuyruk veya sürekli kayıt oluşturmaz.

## CLI seçenek zarfı

Gerçek RX ancak yerel `hackrf_transfer -h` çıktısında `-d`, `-r`, `-f`, `-s`, `-n`, `-a`, `-l` ve `-g` seçeneklerinin tamamı görülürse kurulabilir. `-d` atanmış ED_RX serisini zorunlu kılar. Backend RX-only argv üretir; TX seçenekleri kabul edilmez. Varsayılan RF amplifier kapalı, IF/LNA 16 dB ve Baseband/VGA 16 dB'dir; bunlar optimum, kalibre edilmiş veya dBm karşılığı değildir. Örnekleme zarfı 8, 10 ve 20 MS/s'tir.

Gerçek `hackrf_sweep` çıktı biçimi henüz donanımla doğrulanmadığından production sweep `not_exercised` döner. Bounded fixture parser'ı yalnız iki alanlı `frequency_hz,power_dbfs` test biçimini doğrular. Sweep coarse keşiftir; PHASE-03 detector sonucu değildir.

## Worker ve kullanıcı arayüzü

Araç/cihaz keşfi, capture, `ci8` çözümleme, FFT ve detector worker tarafında çalışır. Mevcut `QThreadPool` üst sınırı `1`, pending niyet üst sınırı `1` ve generation/stale-result reddi korunur. Kaynak değişimi ve pencere kapanışı acquisition işlemini iptal eder, kaynak durumunu ve temporal zinciri sıfırlar.

Kaynak adları `SigMF Kaydı`, `HackRF Canlı RX` ve `Deterministik Test Kaynağı`dır. Test backend'i canlı veya bağlı cihaz olarak gösterilmez. Araç ya da cihaz yokken canlı kontroller pasiftir. PHASE-04 alanları `Henüz doğrulanmadı` kalır.

## Donanım kabulüne kalanlar

Sonraki fiziksel turda gerçek seri keşfi/seçimi, WinUSB erişimi, bounded dört-frame capture, gerçek tuning, USB sürekliliği ve kontrollü RX performansı ayrıca doğrulanacaktır. İlk komut `python -B scripts/check_hackrf_rx_ready.py`dir. Bu sözleşme canlı HackRF, dBm veya saha başarısı kanıtı değildir.
