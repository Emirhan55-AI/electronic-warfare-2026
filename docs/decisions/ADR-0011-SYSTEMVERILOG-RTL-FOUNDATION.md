# ADR-0011 — SystemVerilog RTL Temeli

- Durum: Accepted
- Kapsam: PHASE-06A

## Bağlam

ZedBoard PL tarafındaki blokların bit-doğru Python referanslarıyla karşılaştırılması, veri yolu davranışının açık tanımlanması ve sonraki FFT/detector çalışmalarının tek RTL dili üzerinde ilerlemesi gerekir. PHASE-06A gerçek kart, sentez sonucu veya zamanlama başarısı kanıtlamaz; yalnız vendor-bağımsız giriş ve frame-istatistik temelini kurar.

## Karar

- Özel RTL blokları SystemVerilog ile yazılır. Yeni VHDL kaynağı eklenmez.
- Akış arabirimi AXI4-Stream el sıkışma kurallarını izler.
- PHASE-06A veri biçimi `tdata[7:0]=I`, `tdata[15:8]=Q` signed `ci8` ve frame uzunluğu 4096 karmaşık örnektir.
- İlk sentezlenebilir zincir güvenli giriş buffer'ı, `I²+Q²`, frame enerjisi, tepe gücü/ilk tepe indisi, örnek sayısı ve frame-protokol durumundan oluşur.
- Python standart-kütüphane modeli bit-doğru golden kaynaktır; HDL testbench aynı deterministik vektörleri kullanır.
- Üretim RTL'sinde `real`, kayan nokta ve zamansal testbench yapıları bulunmaz.
- PHASE-06A vendor IP, XCI, block design, XDC veya kart bağlantısı oluşturmaz.

SystemVerilog seçiminin gerekçeleri ZedBoard/Vivado sentez desteği, package/type yapısıyla açık genişlikli arayüzler, assertion ve self-checking testbench kolaylığı, Verilator gibi açık kaynak araçlarla doğrulanabilme ve AXI4-Stream veri yoluna doğal uyumdur. Vendor-bağımsız çekirdek ile ileride gerekebilecek AMD'ye özgü üst sarmalayıcı ayrı tutulacaktır.

## Sonuçlar

PHASE-06A, FFT veya PHASE-03 `regional` detectorünün RTL karşılığı değildir. Hann/FFT/detector zinciri, sabit nokta ölçekleri, AMD/Xilinx FFT IP değerlendirmesi, sentez, kaynak, gecikme ve kart üstü doğrulama PHASE-06B ve sonraki kontrollü adımlarda ayrıca ele alınır. Görsel işlem profilinin otomatik HDL ürettiği iddia edilmez.
