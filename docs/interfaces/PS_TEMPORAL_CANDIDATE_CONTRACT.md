# PHASE-06J PS Temporal Candidate Contract

## Giriş ve yerleşim

Giriş yalnız committed `PHASE-06I PL→PS Candidate Transport ABI v1` packet'ıdır. Header 32 byte, record 40 byte, trailer 32 byte, little-endian, maksimum 1352 candidate ve 54.144 byte sınırları değiştirilmez. Decoder magic/version/length/FFT size/count/flags/reserved/status/CRC32 ve her record'un bin, span, Pfa ve fixed-width alanlarını doğrular. Status sıfır değilse packet algoritmik input değildir. Malformed packet temporal state'i değiştirmez.

## Frame sırası

İlk geçerli `uint32` frame ID kabul edilir. Sonraki ID, modulo `2^32` successor olmalıdır; `FFFFFFFF→00000000` ardışıktır. Başka bir gap görüldüğünde bütün active/ended state, event sayacı ve eviction sayacı sıfırlanır; mevcut frame yeni state'in ilk frame'i olarak işlenir. Açık reset aynı davranışı uygular. Wall-clock timestamp kullanılmaz.

## Association ve tie sırası

Her active track'in önceki inclusive `[start,end]` span'ı iki bin sola/sağa genişletilir. Current candidate ile inclusive overlap pozitif değilse pair kurulmaz. Bütün mümkün pair'ler arasında greedy seçim anahtarı sırayla şöyledir:

1. daha büyük overlap,
2. daha küçük absolute peak-bin displacement,
3. daha küçük event ID,
4. daha küçük current start bin,
5. daha küçük current input index.

Bir track ve bir candidate frame başına en fazla bir kez eşleşir. Pfa/evaluate-center/threshold association anahtarı değildir.

## Confirmation, miss ve expiry

Yeni candidate `history=[true]`, `seen_count=1`, `tentative` state ve monoton event ID ile doğar. Her eşleşme `true`, her miss `false` ekler; deque derinliği üçtür. Son üç konumda en az iki `true` olduğunda track confirmed olur ve confirmed state expiry'ye kadar geri alınmaz. Bir miss active track'i `observed_this_frame=false` ile korur; ikinci ardışık miss ended event üretir ve active state'ten çıkarır. Empty frame bütün active track'lere bir miss uygular.

## Admission, bellek ve karmaşıklık

Active kapasite 64'tür. Unmatched candidate admission sırası peak/noise oranı azalan, peak bin artan, start bin artan ve input index artan biçimdedir; `noise=0, peak>0` sonsuz oran, `peak=0` ise PHASE-03'teki 0 dB sırasına eşdeğer oran 1 kabul edilir. Fazla candidate sayılır ve sessizce active state'e eklenmez. Ended history 128 record'luk ring'dir ve overwrite sayacı vardır.

Pair listesi dinamik ayrılmaz; deterministik repeated-min scan kullanılır. Konservatif üst sınırlar frame başına 5.537.792 association pair değerlendirmesi ve 84.512 admission karşılaştırmasıdır. Input packet 54.144 byte, sonuç yapısı 8.724 byte ve C state boyutu host build evidence'ında ayrıca kaydedilir; unbounded vector/map yoktur.

## Kapsam dışı

Fiziksel frequency offset/absolute frequency/coarse span Hz, precise bandwidth, PHASE-04 ölçümleri, dBFS/dBm, gerçek DMA, PetaLinux, device tree, ARM execution, yeni PL RTL, continuous detector throughput iyileştirmesi, live HackRF ve PC UI entegrasyonu bu sözleşmenin dışındadır.
