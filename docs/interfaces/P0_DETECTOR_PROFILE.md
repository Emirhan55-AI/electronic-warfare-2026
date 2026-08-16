# P0 Kanonik OS-CFAR Profili

## Yöntem ve mühendislik profili ayrımı

KTR niyeti yerel uyarlamalı `OS-CFAR` yöntemidir. KTR; reference/guard hücre
adetlerini, sıra istatistiğini, Pfa değerini veya eşik katsayısını sayısal sabit
olarak vermez. Aşağıdaki değerler KTR sabiti değil, P0 için doğrulanan mühendislik
profilidir.

| Alan | Kanonik değer |
|---|---:|
| Profil adı | `P0_OS_CFAR_EXPONENTIAL_PFA_1E4` |
| Reference hücresi | 16/yan, toplam 32 |
| Guard hücresi | 4/yan |
| Sıra istatistiği | Küçükten büyüğe 24/32 |
| İstenen Pfa/CUT | `1e-4` |
| Türetilen alpha | `8.58014304069906` |
| Kenar politikası | `require_full_window` |
| Karar | `CUT > alpha × X_(24)`; eşitlik tespit değildir |
| Aday içi azami boşluk | 1 bin |

## Matematiksel temel

Varsayım, reference hücrelerinin bağımsız ve aynı dağılımlı exponential
square-law güç örnekleri olmasıdır. `N=32`, `k=24` ve yükselen sıra istatistiği
için katsayı şu denklemden sabit 160 bisection iterasyonuyla çözülür:

`Pfa(alpha) = product(i=0..k-1) ((N-i) / (N-i+alpha))`

Bu varsayım gerçek RF ortamının her zaman exponential olduğunu iddia etmez.
Changing-noise ve interferer sahneleri deterministik sağlamlık kontrolüdür; saha
Pfa kabulünün yerine geçmez.

256 gürültü frame'inde 1.038.336 değerlendirilen CUT üzerinde 95 false alarm
ölçülmüştür: gözlenen oran `9.1492541913215e-5`, iki taraflı %99 Wilson aralığı
`[7.029883509434694e-5, 1.1907497080798152e-4]` olur. Yapılandırılan `1e-4`
bu sonlu-örnek aralığındadır; gözlenen değer teorik değere eşit ilan edilmez.

Python ve portable C aynı katsayıyı bağımsız türetir. Host doğrulamasında katsayı
farkı `0.0`, 8 frame/32.768 hücre ve adaylarda mismatch `0` olmuştur. ARM ve
ZedBoard çalıştırılmamıştır.
