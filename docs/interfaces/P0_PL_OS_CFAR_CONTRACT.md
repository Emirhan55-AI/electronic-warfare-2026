# P0 PL OS-CFAR Sözleşmesi

10 Eylül 2026: kaynak v2 zayıf metaverisini içerir. Yeni RTL ile yeni ARM
hizmetinin birlikte fiziksel kabulü ayrıdır; tarihsel v1 kanıtı değiştirilmez.

## Kanonik profil

| Alan | Değer |
|---|---:|
| Frame | 4096 natural-order güç hücresi |
| Güç | unsigned 58-bit `UQ28.30` |
| Shift eşleme | `shifted = natural XOR 12'h800` |
| Referans hücresi | 16/yan |
| Koruma hücresi | 4/yan |
| Sıra istatistiği | yükselen 24/32 |
| Değerlendirilen shifted binler | `20..4075` |
| Alpha Q32 | `36.851.433.755` |
| Karar | `(CUT << 32) > X_(24) × 36.851.433.755` |

Q32 katsayısı kanonik float64 `8,58014304069906` değerinin en yakın unsigned
tam sayıya yuvarlanmasıdır. RTL bu sabit için ara threshold yayımlamaz; 90-bit
sol tarafı ve 94-bit sağ tarafı sıfır genişleterek strict karşılaştırır. Eşitlik
tespit değildir.

## AXI4-Stream girişi

Giriş `TVALID/TREADY`, 58-bit güç `TDATA`, 12-bit natural index ve `TLAST`
taşır. Index `0..4095` olmalı ve `TLAST` yalnız 4095'te gelmelidir. Erken,
eksik veya geç `TLAST/index` karesi çıktı üretmeden atılır; sticky frame-error
durumu kurulur ve akış bilinen sınırda veya sonraki `TLAST` ile eşzamanlanır.

## DMA çıkış kelimesi

Çıkış natural sıradadır ve her beat 64 bittir:

| Bit | Alan |
|---:|---|
| `57:0` | exact giriş gücü |
| `58` | `evaluated` |
| `59` | `detected` |
| `60` | `weak_nomination`: `(CUT << 32) > X_(24) × 17098572778` |
| `63:61` | v2 biçim işareti `3'b110` |

Üst nibble bu nedenle `C` veya `D` olur. Normal güçlü karar zayıf kararı da
gerektirir; değerlendirme dışı hücrelerde iki karar biti de sıfırdır. ARM v2
çözücüsü karışık biçim ve tutarsız bitleri reddeder. Eski `4'hA` kareleri
normal karar yolunda desteklenir; zayıf aday bilgisi içermez. Eski boole
çözücü API’si normal karar döndürmeye devam eder; hizmetin kullandığı
`p0_pl_os_cfar_decode_with_weak` bit 0 güçlü / bit 1 zayıf maskesini döndürür.
Pipeline bu maskeden zayıf adayları ayırıp normal gruplamaya boole maske verir.

`TKEEP=8'hFF`, son natural binde `TLAST=1` olur. Output stall boyunca kelime,
index ve `TLAST` sabit kalır. Eski güç-only kelimelerinin üst altı biti sıfırdır;
ARM bu kareleri PL-OS-CFAR biçimi olarak kabul etmez.

## Mimari ve çevrim bütçesi

Tek 4096×58 frame RAM ve 4096×3 metadata RAM kullanılır. İlk 41 shifted hücre
ile iki sıralı 16-hücre referans kümesi kurulur. Sonraki her CUT'ta iki küme
birer değer silme/ekleme ile güncellenir. Birleşik rank, iki sıralı 16-elemanlı
kümenin sabit sınırlı ikili bölünmesiyle bulunur.

Blok collect, evaluate ve natural-order replay sırasında aynı frame belleğini
kullanır; ping-pong yoktur. Bu nedenle girişte frame arası backpressure vardır.
Kabul ölçütü kesintisiz bir-beat/clock iddiası değil, 50 MHz'te bir tam frame'in
`102.400` çevrimden kısa tamamlanmasıdır. Gerçek hizmet hızı DMA, sürücü, ARM ve
yerel protokol ile ayrıca ölçülür.

## Kapsam sınırı

Bu blok aday gruplama, geniş bant kurtarma, temporal doğrulama, Hz/dBFS dönüşümü,
parametre çıkarımı, yön bulma veya RF işlevi üretmez. Biçim işareti yalnız veri
biçimini tanımlar; fiziksel kabul veya doğruluk işareti değildir.
