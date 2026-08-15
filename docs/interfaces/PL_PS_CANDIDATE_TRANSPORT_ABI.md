# PHASE-06I PL→PS Candidate Transport ABI v1

## Transport

Her PHASE-06H candidate frame'i bir AXI4-Stream packet'tır. Fiziksel data width 64 bit, `TKEEP=8'hFF`; yalnız trailer'ın son beat'inde `TLAST=1` olur. Byte offset 0, `TDATA[7:0]` üzerindedir. Bütün çok-byte alanlar unsigned little-endian'dır.

Seçilen deployment sınırı packetizer → AXI DMA S2MM → bounded PS DDR buffer'dır. DMA descriptor maksimum 54.144 byte kabul eder; önerilen iki buffer toplam 108.288 byte'dır. Packet completion interrupt/descriptor actual-length ile PS'ye bildirilir. DMA/IP/device-tree/driver bu fazda uygulanmaz.

## Header — 32 byte

| Offset | Byte | Alan |
|---:|---:|---|
| 0 | 4 | magic `P6IH` (`0x48493650`) |
| 4 | 2 | ABI version = 1 |
| 6 | 2 | header bytes = 32 |
| 8 | 4 | frame ID, modulo `2^32` |
| 12 | 2 | FFT size = 4096 |
| 14 | 2 | candidate record bytes = 40 |
| 16 | 4 | flags; bit0 empty frame |
| 20 | 12 | reserved, zero |

## Candidate record — 40 byte

| Offset | Byte | Alan |
|---:|---:|---|
| 0 | 2 | start shifted bin |
| 2 | 2 | end shifted bin |
| 4 | 2 | peak shifted bin |
| 6 | 2 | coarse span bins |
| 8 | 1 | Pfa selector |
| 9 | 1 | flags: bit0 candidate-valid, bit1 evaluate-center |
| 10 | 6 | reserved, zero |
| 16 | 8 | peak power; düşük 58 bit `UQ28.30`, üst bitler zero |
| 24 | 8 | regional noise; düşük 58 bit `UQ28.30`, üst bitler zero |
| 32 | 8 | threshold; düşük 62 bit `UQ32.30`, üst bitler zero |

Candidate record yalnız semantic candidate için vardır. PHASE-06H sentinel'i wire packet'a record olarak yazılmaz.

## Trailer — 32 byte

| Offset | Byte | Alan |
|---:|---:|---|
| 0 | 4 | magic `P6IT` (`0x54493650`) |
| 4 | 2 | ABI version = 1 |
| 6 | 2 | trailer bytes = 32 |
| 8 | 4 | header ile aynı frame ID |
| 12 | 2 | candidate count, `0..1352` |
| 14 | 2 | status: bit0 input-contract, bit1 overflow, bit2 internal error |
| 16 | 4 | payload bytes = count×40 |
| 20 | 4 | total packet bytes |
| 24 | 4 | IEEE CRC32, yalnız candidate payload |
| 28 | 4 | reserved, zero |

Empty frame 32-byte empty-flag header + sıfır record + 32-byte trailer'dır. Candidate count sıfır, CRC32 `0`, packet size 64 byte olur.

## Hata ve akış politikası

Normal akışta sessiz loss veya duplicate kabul edilmez. Downstream stall bütün output payload/TLAST'ı sabit tutar ve `TREADY` upstream backpressure uygular. Malformed candidate veya 1352 sınır aşımı status ile işaretlenir; PS status'u sıfır olmayan packet'ı algoritmik input olarak kullanmaz. Reset partial packet'ı flush eder ve frame ID'yi sıfırlar.

## PS sahipliği ve kapsam dışı

PS runtime metadata olarak RF center frequency, sample rate ve FFT size kullanarak bin→Hz dönüşümü yapacaktır. Shifted bin convention PHASE-02 ile aynı `[-Fs/2, Fs/2)` düzenidir. `coarse_span_hz = span_bins × Fs / 4096` yalnız coarse detected span'dir; precise/occupied bandwidth değildir. Power/noise/threshold integer alanları korunur; kalibrasyon olmadan dBm değildir.

Temporal confirmation, C/C++ ARM runtime, DMA IP, PetaLinux driver, device tree, physical frequency output, precise bandwidth, live HackRF, post-route timing ve hardware execution PHASE-06I kapsamında değildir.
