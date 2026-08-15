# ADR-0019 — PHASE-06H Aday Gruplama ve PL/PS Sınırı

## Durum

Kabul edildi.

## Kaynak algoritma

Bağlayıcı davranış `reference/detection/pipeline.py` içindeki `DetectionPipeline._group` yöntemidir. Shifted sıradaki detected hücreler arasında index farkı en fazla iki ise aynı kaba adayda kalır; bu, `max_gap_bins=1` ile arada en fazla bir detected-olmayan binin köprülenmesidir. Başlangıç ve bitiş ilk/son detected bindir. Peak, exact power'ın ilk maksimumudur. Noise ve threshold peak hücresinden alınır.

## PL/PS kararı

Her detector hücresini tüketen grouping, peak ve coarse bin-span üretimi PL'de gerçekleştirilir. Sparse adayların temporal 2-of-3 association'ı, fiziksel frekans dönüşümü, PHASE-04 ölçümleri ve daha yüksek seviyeli düzensiz işlemler Zynq PS için sonraki kontrollü sınıra bırakılır. PC yalnız display/operator rolündedir; kritik algoritma motoru değildir.

## Sıra ve tampon kararı

PHASE-06G hücreleri natural `0..4095` sırasında, shifted index metadata'sıyla replay eder. Bu sıra shifted `2048..4095, 0..2047` olur; authoritative candidate sırası ise shifted artandır. Excluded FFT uçları nedeniyle bir aday shifted `4095/0` wrap'ını geçemez; ancak `2047/2048` yarı sınırını geçebilir. PHASE-06H her yarıyı tek geçişte gruplar, frame sonunda low-half son adayı ile high-half ilk adayını aynı `delta<=2` kuralıyla koşullu birleştirir ve low-half ardından kalan high-half sırasıyla replay eder.

Her yarıda 2028 evaluated bin vardır. Yeni aday için önceki detected binden en az üç index ayrılmak gerektiğinden kesin üst sınır `ceil(2028/3)=676`, frame toplamı 1352 adaydır. Her candidate RAM 676×94 bit start/end/peak/peak-power taşır. Noise ve threshold 16-entry bölgesel metadata kaydından peak bölgesine göre replay edilir. Yeni 4096-cell frame RAM eklenmez.

## Transport kararı

Semantic model no-detection frame için boş aday tuple'ı üretir. AXI4-Stream'de frame varlığını kaybetmemek için böyle bir frame tek `candidate_valid=0, TLAST=1` sentinel üretir. Geçerli aday frame'inde her record `candidate_valid=1` olur ve yalnız son aday `TLAST=1` taşır. Overflow geçerli sözleşmede matematiksel olarak erişilemez; savunmacı overflow/frame-error sticky durumunda frame discard edilir.

## Kapsam sınırı

Coarse span `end-start+1` bin sayısıdır; hassas veya occupied bandwidth değildir. Hz, RF center frequency, dBFS, PSD, temporal event, yön bulma ve localization üretilmez. PHASE-06G tek-frame buffering ve zorunlu frame gap sınırı değişmez. PHASE-06H için post-route 100 MHz timing ve hardware sonucu ancak ayrıca çalıştırılırsa iddia edilebilir.
