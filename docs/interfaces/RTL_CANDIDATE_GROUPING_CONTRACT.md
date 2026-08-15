# PHASE-06H Detector Aday Gruplama RTL Sözleşmesi

## Giriş

Giriş, `axis_regional_detector` çıkışının tamamını natural sıra ile tüketen AXI4-Stream'dir:

| Alan | Genişlik | Anlam |
|---|---:|---|
| `TDATA` | 58 | Original `UQ28.30` power |
| natural index | 12 | `0..4095` |
| shifted index | 12 | `natural XOR 12'h800` |
| median twice | 59 | PHASE-06G bölgesel exact median metadata'sı |
| regional noise | 58 | `UQ28.30`; unevaluated hücrede sıfır |
| threshold | 62 | `UQ32.30`; unevaluated hücrede sıfır |
| evaluated | 1 | PHASE-06G evaluation mask |
| detected | 1 | `evaluated && power > threshold` |
| Pfa selector | 2 | `0/1/2` |
| evaluate center | 1 | Frame boyunca sabit policy |
| `TLAST` | 1 | Yalnız natural index 4095 |

Payload yalnız `TVALID && TREADY` ile kabul edilir. Shifted/natural eşlemesi, index sırası, TLAST, config sabitliği, evaluation mask ve `detected -> evaluated` denetlenir. Bozuk frame discard edilir ve sticky frame error üretilir.

## Gruplama

Authoritative sıra shifted `0..4095` sırasıdır. İlk detected hücre aday açar. Sonraki detected hücre ile son detected index farkı `<=2` ise aday devam eder; fark `>=3` ise önceki aday kapanır. Arada en fazla bir detected-olmayan bin köprülenir. Region veya shifted `2047/2048` yarı sınırı grubu kapatmaz. Excluded uçlarda detection olamaz; shifted `4095/0` wrap boyunca grup kurulmaz.

Peak yalnız `power > stored_peak_power` olduğunda güncellenir. Eşit güçte daha düşük/ilk shifted index kazanır. Noise ve threshold peak hücresinin region metadata'sıdır.

## Çıkış

Çıkış AXI4-Stream candidate packet'ıdır:

| Alan | Genişlik | Anlam |
|---|---:|---|
| `TDATA` | 58 | Exact peak power `UQ28.30` |
| start shifted bin | 12 | İlk detected bin, inclusive |
| end shifted bin | 12 | Son detected bin, inclusive |
| peak shifted bin | 12 | First-maximum peak |
| coarse span bins | 12 | `end-start+1`; hassas bandwidth değildir |
| regional noise | 58 | Peak region `UQ28.30` |
| threshold | 62 | Peak region `UQ32.30` |
| Pfa selector | 2 | Latched frame selector |
| evaluate center | 1 | Latched frame policy |
| candidate valid | 1 | Semantic aday/sentinel ayrımı |
| `TLAST` | 1 | Frame'in son candidate record'u |

No-detection frame tek sıfır payload'lı `candidate_valid=0, TLAST=1` sentinel üretir. Geçerli candidate frame'inde bütün record'lar valid'dir. Stall boyunca bütün output alanları ve TLAST sabit kalır.

## Kapasite ve throughput

Low ve high shifted yarılar için ayrı 676-entry, 94-bit candidate RAM vardır. Toplam kesin kapasite 1352 candidate/frame'dir. Yeni 4096-cell buffer yoktur. Input collect sırasında bir record/clock kabul edilir; candidate replay sırasında yeni frame kabul edilmez. PHASE-06G zaten processing/replay sırasında input durdurduğu için full-system continuous frame acceptance desteklenmez ve deterministik frame gap zorunludur.

## Reset ve malformed frame

Active-low synchronous reset partial group, buffered candidates ve pending output'u flush eder. Early/missing/late TLAST, index veya shifted-map hatası, frame boyunca config değişimi, invalid Pfa, yanlış evaluation metadata'sı ve unevaluated detection frame discard eder. Resynchronization bilinen frame sınırında veya sonraki TLAST'ta yapılır. Bozuk frame candidate üretmez.

## Kapsam dışı

Candidate ID, physical frequency, Hz/dB dönüşümü, precise/occupied bandwidth, PSD normalization, temporal confirmation/association, PHASE-04 parameter extraction, PetaLinux transport, hardware ve post-route timing bu sözleşmenin dışındadır.
