# PHASE-06B RTL Hann Pencereleme Sözleşmesi

## Yetenek sınırı

Bu sözleşme yalnız `signed ci8 AXI4-Stream → 4096 örnek indeksleme → sabit nokta periyodik Hann → SQ1.15 kompleks AXI4-Stream` zincirini tanımlar. Gerçek FFT, FFT IP, FFT sonrası güç, detector, DMA, Ethernet, Vivado, sentez, implementation, timing, resource utilization ve kart çalışması kapsam dışıdır.

## Giriş ve frame

| Alan | Sözleşme |
|---|---|
| Saat/reset | `aclk`; aktif düşük ve yükselen kenarda senkron örneklenen `aresetn` |
| Aktarım | Yalnız `s_axis_tvalid && s_axis_tready` olduğunda kabul edilir |
| Veri | `s_axis_tdata[7:0]=I`, `s_axis_tdata[15:8]=Q`; iki bileşen signed SQ1.7 `ci8` |
| Örnek sırası | Frame içinde `n=0,1,...,4095` |
| Frame sonu | 4096. kabul edilen örnekte `s_axis_tlast=1` |
| Backpressure | Kaynak `tvalid && !tready` süresince `tdata` ve `tlast` değerlerini sabit tutar |

Giriş `axis_skid_buffer` ile bir transfer tutulabilir. Reset kısmi frame'i, örnek indisini, buffer'ı ve bekleyen çıkışı temizler. Ardışık doğru frame'ler arasında boş çevrim gerekmez.

Blok `TLAST` değerini çıkışa aynen taşır. İç katsayı indisi kabul edilen `TLAST` veya fiziksel indeks 4095 sonrasında sıfırlanır. Erken/eksik/geç `TLAST` onarılmaz ve başarı olarak yeniden etiketlenmez; PHASE-06A frame sözleşmesine aykırı kaynak davranışıdır. Bu deterministik yeniden hizalama politikası FFT'ye geçerli frame sağlandığı iddiası değildir.

## Periyodik Hann

PHASE-02 ile aynı tanım kullanılır:

`w[n] = 0,5 - 0,5 cos(2πn/4096)`, `n=0..4095`.

Periyodik simetri `w[n]=w[4096-n]` olur. Katsayı ROM'u `n=0..2048` için 2049 değer taşır; `n>2048` adresi `4096-n` olarak yansıtılır. Float64 PHASE-02 dizisinden katsayı üretimi:

`C[n] = floor(w[n] × 32768 + 0,5)`.

`C[n]` unsigned 16 bit UQ1.15'tir. `C[0]=0`, `C[2048]=32768`; kayan noktalı son katsayı sıfırdan büyük olsa da UQ1.15 nicemlemesinde `C[4095]=0` olur. Katsayılar `hann-coefficients.mem` içinde kanonik ASCII hex olarak dondurulur; üretici normal modda yalnız byte eşitliği denetler.

## Sabit nokta matematiği

| Aşama | Biçim/genişlik | Matematiksel aralık |
|---|---|---|
| Giriş I/Q | signed 8 bit SQ1.7 | `[-1, 127/128]` |
| Katsayı | unsigned 16 bit UQ1.15 | `[0,1]` kullanılan aralık |
| Signed katsayı operandı | signed 17 bit | başına sıfır eklenmiş UQ1.15 |
| Çarpım kabı | signed 25 bit, 22 kesir biti | gerçek ürün `[-1,127/128]` sınırında |
| Çıkış I/Q | signed 16 bit SQ1.15 | `[-1, 32767/32768]` |

Her bileşen için integer ürün `P=X×C` hesaplanır. Çıkış büyüklüğü:

`Ymag = (abs(P) + 64) >> 7`.

Ürün negatifse çıkış `-Ymag`, değilse `Ymag` olur. Bu en yakına, tam yarıda sıfırdan uzağa yuvarlamadır. `>> 7` işlemi ürünün mutlak büyüklüğüne uygulanıp işaret sonradan geri konur; literal signed aritmetik sağa kaydırma kullanılmaz, çünkü bu negatif yarıları aşağı yönde yanlı yuvarlardı. Ayrı truncation aşaması yoktur. Seçilen giriş ve katsayı aralığı SQ1.15'i matematiksel olarak aşmaz; saturation ve wrap yoktur. Beklenmeyen aşım doğrulama hatasıdır.

Önemli sınırlar merkez katsayısında `-128→-32768`, `127→32512`, sıfır girişte daima sıfırdır. I ve Q birbirinden bağımsız aynı matematiği kullanır.

## Çıkış ve FFT sınırı

| Alan | Sözleşme |
|---|---|
| Veri | `m_axis_tdata[15:0]=I`, `m_axis_tdata[31:16]=Q`; iki bileşen signed SQ1.15 |
| Aktarım | Yalnız `m_axis_tvalid && m_axis_tready` olduğunda tüketilir |
| TLAST | Kabul edilen giriş örneğinin `s_axis_tlast` değeriyle birebir hizalıdır |
| Backpressure | `m_axis_tvalid && !m_axis_tready` süresince payload ve `TLAST` sabit kalır |
| Throughput | Hazır downstream altında çevrim başına bir kompleks örnek |

Bu 32 bit veri yolu gelecekteki FFT wrapper'ının giriş sınırıdır; FFT IP'nin kendi port genişliği, konfigürasyonu veya ölçekleme planı değildir. Gelecek wrapper bu sözleşmeyi değiştirecekse yeni bit-doğru karar gerekir.

## Gecikme

Çekirdek gecikmesi, giriş transferinin kabul edildiği yükselen kenardan karşılık gelen çıkış payload'unun `m_axis_tvalid=1` olarak ilk gözlendiği yükselen kenara kadar geçen saat aralığıdır. Boş pipeline ve hazır downstream altında bu gecikme sabit bir çevrimdir. Downstream backpressure transferin tamamlanmasını sınırsız erteleyebilir; bu bekleme çekirdek hesaplama gecikmesi olarak raporlanmaz.

Testbench giriş ve çıkış transfer sıra numaralarını eşleyerek gecikmeyi ölçer; bütün payload'ları bit-doğru vektörle karşılaştırır ve stall altında kararlılığı ayrıca denetler.

## Doğrulama ve iddia sınırı

Zorunlu kapsam PHASE-01 dört frame, sıfır, signed uçlar, alternasyon, impulse, sabit kompleks frame, kesintisiz ardışık frame, deterministik rastgele stall, yönlendirilmiş backpressure, reset öncesi/sırası, ilk/merkez/son katsayı, `TLAST`, X/Z, payload kararlılığı ve watchdog denetimidir.

PHASE-02 float64 Hann algoritmik referans, PHASE-06B integer Python model bit-doğru referans, SystemVerilog ise doğrulanan RTL'dir. Bunların başarısı FFT, Vivado, sentez, timing, resource veya donanım başarısı değildir.
