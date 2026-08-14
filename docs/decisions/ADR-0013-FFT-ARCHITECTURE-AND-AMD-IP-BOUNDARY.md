# ADR-0013 — FFT Mimarisi ve AMD IP Sınırı

- Durum: Accepted
- Kapsam: PHASE-06C

## Bağlam

PHASE-06B, 4096 örnekli frame için signed SQ1.15 I/Q taşıyan 32 bit AXI4-Stream FFT giriş sınırını bit-doğru doğrulamıştır. Sonraki gerçek FFT uygulaması PHASE-02'nin ölçeklenmemiş ileri DFT tanımına bağlanmalı; özel FFT geliştirme riski, vendor IP bağımlılığı, sabit nokta büyümesi, sıralama ve konfigürasyon açık karara dönüştürülmelidir.

Karar çalışmasının vendor kaynağı AMD *Fast Fourier Transform LogiCORE IP Product Guide* PG109, v9.1, 2026.1 yayınıdır (17 Temmuz 2026): `https://docs.amd.com/r/en-US/2026.1/pg109-xfft/Pipelined-Streaming-I/O`. IP Facts, Feature Support Matrix, Finite Word Length Considerations, Configuration Channel, Port Descriptions, TUSER Fields, Applying a New Configuration While Idle ve Controlling the FFT Core sayfaları kapanışta ayrıca çapraz kontrol edilmiştir. Yerel PG109 kopyası ve Vivado kurulumu mevcut değildir; gerçek IP üretimi, port haritası ve hedef parça bağlanması gelecekte kullanılan Vivado sürümüyle yeniden doğrulanacaktır.

## Mimari karşılaştırma

| Ölçüt | Özel SystemVerilog FFT | AMD/Xilinx FFT LogiCORE |
|---|---|---|
| Geliştirme riski | Yüksek; butterfly, twiddle, bellek ve reorder tasarımı gerekir | Daha düşük; doğrulanmış vendor çekirdeği hedeflenir |
| Doğrulama yükü | Bütün FFT aritmetiği ve mimarisi projeye aittir | Wrapper ve vendor C-model/XSim birlikte doğrulanır |
| Zynq-7000 | Mümkün fakat bu repository'de kanıtlanmamış | PG109 v9.1 desteklenen aileler arasında Zynq-7000'i listeler; ZedBoard parçası ve gerçek üretilmiş konfigürasyon Vivado'da teyit edilir |
| AXI4-Stream | Baştan tasarlanmalıdır | Native veri ve config kanalları vardır |
| 4096 fixed-point | Baştan tasarlanmalıdır | PG109 kapsamında desteklenir |
| Sürekli throughput | Yüksek tasarım riski | Pipelined Streaming I/O ardışık frame'leri destekler; waitstate yine mümkündür |
| Ordering/scaling | Tamamen özel | Natural/reversed ve üç fixed-point aritmetik seçeneği vardır |
| Kaynak ölçümü | Vivado gerekir | Vivado IP/sentez raporuyla ölçülebilir |

Özel 4096 FFT, proje takvimi ve bağımsız doğrulama yükü nedeniyle seçilmez. Gelecekteki gerçek uygulama mimarisi AMD/Xilinx FFT LogiCORE olur. PHASE-06C yalnız vendor-independent wrapper sınırını kurar; IP üretmez, XCI oluşturmaz ve vendor FFT davranışı simüle etmez.

## Dondurulan IP konfigürasyon varsayımları

- Tek kanal, fixed `N=4096`; runtime transform length kapalıdır.
- Sistem politikası yalnız ileri FFT'dir. PG109 mantıksal alan düzeninde tek kanal için channel 0 `FWD_INV`, bit 0'dadır ve `1` forward anlamına gelir. Bu nedenle wrapper'ın **beklenen mantıksal config yükü** `0x01` olur. Wrapper bunu soyut 8 bit portunda resetten sonra bir kez gönderir; gerçek üretilmiş `s_axis_config_tdata` genişliği ve tam port haritası henüz doğrulanmamıştır. Runtime reconfiguration yoktur.
- `Pipelined Streaming I/O`, Non-Realtime AXI modu seçilir. Non-Realtime, kesintisiz işlemeyi kapatmaz; giriş ve çıkış AXI kanallarının sınırsız waitstate uygulayabilmesini sağlar. Hazır sistemde çevrim başına bir örnek hedeflenir fakat IP waitstate üretebilir. Burst seçenekleri daha küçük çekirdek karşılığında ayrı load/process ve daha uzun transform süresi getirdiğinden sürekli DSP zinciri için seçilmez; gerçek throughput ve kaynak ölçülmüş değildir.
- Giriş doğal zaman sırası `n=0..4095`, çıkış natural unshifted `k=0..4095` olur. Wrapper içinde `fftshift` yoktur.
- Giriş bileşeni 16 bit signed SQ1.15, phase factor 24 bit ve selectable convergent rounding olur. PG109, bu seçimin datapath içindeki her word-length reduction noktasını convergent yapmadığını belirtir; bu nedenle NumPy ideal yuvarlama ile gerçek AMD sonucu eşit sayılmaz ve C-model karşılaştırması gelecekte zorunludur.
- Aritmetik `unscaled full precision fixed-point` olur. PG109 genişlik kuralıyla beklenen vendor sayısal alanı 29 bit ve 15 kesir bitidir; her bileşenin 32 bit signed lane'e sign-extend edilmesiyle dış AXI payload 64 bit olur. Gerçek üretilmiş TDATA port/padding haritası gelecekte Vivado'da doğrulanır.
- `XK_INDEX` 12 bit etkin; `BLK_EXP` ve `OVFLO` unscaled full-precision modunda devre dışıdır. Cyclic prefix yoktur.
- `event_frame_started`, unexpected/missing TLAST ve channel-halt olayları resetle temizlenen sticky status bitlerine taşınır. Event görülmesi başarılı FFT sonucu değildir.

Natural order, PHASE-02 doğrudan golden karşılaştırmasını ve sonraki lineer-power/regional-detector sırasını sadeleştirir. IP iç reorder belleğinin olası kaynak/gecikme bedeli kabul edilir; gerçek bedel Vivado olmadan ölçülmüş sayılmaz.

## Sayısal karar

Unscaled full precision, PHASE-02 ile ölçek ilişkisini doğrudan korur ve frame-bağımlı exponent üretmez. Matematiksel DFT'nin `N=4096` toplamı `log2(N)=12` bit akümülasyon büyümesi getirir. PG109, kompleks rotasyonda `1+j` gibi büyüklüğü 1'i aşan değerlerin tek seferlik koruma ihtiyacı için buna ek `+1` bit ayırır. Böylece vendor genişlik artışı `12+1=13`, fiziksel genişlik `16+13=29` bittir; 12 bit DFT toplam büyümesi ile 13 bit vendor genişlik artışı aynı kavram değildir.

İkili nokta girişteki gibi 15 kesir bitinde kalır. Repository gösteriminde `SQm.n`, `m` alanı sign biti dahil ikili noktanın solundaki toplam bit sayısıdır. Bu nedenle 29 bit değer `SQ14.15` olarak adlandırılır ve aralığı `[-8192, 8192-2^-15]` olur. “29-bit Q15” yalnız 15 kesir bitini söyleyen kısa addır. İdeal NumPy FFT'nin convergent-rounded bu grid modeli PHASE-06C dış sayısal sözleşmesidir; AMD C-model bit doğruluğu değildir.

Scaled fixed-point 16 bit aday, overflow'u önlemek için toplam 13 bit sağa ölçek ve sabit normalizasyon bağı gerektirir. Ters ölçeklemeden sonra bir quantization adımı `2^13=8192` giriş LSB olduğundan en yakın-even yuvarlamanın yarım-adım sınırı `4096` LSB'dir; gözlenen büyük hata saturation veya wrap değildir. Block floating-point adayında exponent 13 kullanan frame'ler aynı `8192` LSB geri-ölçeklenmiş adımı ve `4096` LSB yarım-adım sınırını üretir. Bu iki aday seçilmez. Power genişliği PHASE-06C'de dondurulmaz.

Phase-factor proxy çalışmasında 16/20/24/32 bit adayları impulse, exact-bin tone ve temsilî Hann frame üzerinde karşılaştırılır. Maksimum bileşen hatası `≤16 input LSB` ve en kötü frame RMS hatası `≤0,25 input LSB`, PHASE-06C sırasında mimari aday seçimini yönlendirmek için kurulmuş **planlama baseline kriteridir**; önceki bir fazda kilitlenmiş kabul kapısı veya AMD doğruluk garantisi değildir. 20 bit aday bu kriteri karşılamaz; 24 bit aday yaklaşık `9,2104` maksimum ve `0,1304` RMS LSB ile karşılar. 32 bit daha düşük hata verir fakat planlama kriteri için gerekli değildir ve daha geniş phase-factor storage/arithmetic taşır. Bu proxy AMD C-model sonucu değildir; gerçek vendor kabul kapısı ileride C-model/XSim karşılaştırmasından önce ayrıca kilitlenmelidir.

## Sonuç ve iddia sınırı

PHASE-06C SystemVerilog wrapper'ı gerçek IP portlarını soyutlar. Icarus testbench yalnız config, AXI, reset, backpressure, TLAST, index ve event plumbing için matematiksel FFT yapmayan transport stub kullanır. Gerçek AMD IP generation, C-model, XSim, XCI, latency, synthesis, implementation, timing, resource utilization ve ZedBoard sonucu uygulanmış sayılmaz. Otomatik HDL üretildiği iddia edilmez.
