# PHASE-04 Parametre Çıkarımı Sözleşmesi

## Çıktılar

Her olay sonucu spektral merkez, gözlenmiş taşıyıcı, alt/üst bant sınırı, bant
genişliği, göreli `FS²/dBFS`, bant içi SNR ve `Analog / Sayısal / Belirsiz`
alanlarını taşır. Alan durumları yalnız `valid`, `not_observed`,
`not_applicable`, `insufficient_quality` veya `uncertain` olabilir.

`nominal_center_frequency_hz` yalnız sentetik ground truth ve metadata bağlamıdır.
Estimator çıktısı değildir. Bastırılmış taşıyıcılı sinyallerde yalnız “taşıyıcı
çizgisi gözlenmedi” sonucu verilir; spektral merkez ayrıca raporlanabilir.

## Temporal olay ve sahiplik

Parametre zinciri byte-sabit PHASE-03 profilinin `2-of-3` temporal olaylarını
kullanır. Bağımsız frame elle `confirmed` yapılmaz. Yalnız `confirmed` ve aynı
frame'de `observed_this_frame` olan event public parametre sonucu üretebilir;
tentative veya miss frame'inde parametre ve sahte sıfır özellik kaydı yoktur.

Birleştirilmiş candidate sahibi ground truth kullanılmadan, önce ardışık özellik
geçmişi, sonra en erken `first_frame`, sonra en küçük `event_id` sırasıyla seçilir.
Merge yalnız seçilen owner geçmişini korur; split geçmiş miras almaz. Ground truth,
detector, candidate, owner, search veya reference seçimine verilmez.

## Analysis-window ve gürültü referansı

`analysis.single-region-v1` her PHASE-03 region'ını ayrı hull yapar;
`analysis.clustered-regions-v1` aralarında en fazla 24 bin boşluk bulunan en fazla
32 region'ı, hull 112 bini aşmıyorsa birleştirir. İki yöntem de hull çevresinde
`±32` bin, en fazla 176-bin search kullanır. Sol reference
`[search_lo-20,search_lo-5]`, sağ reference `[search_hi+5,search_hi+20]` aralığıdır;
search ile arada dört guard ve iki tarafta tam 16 hücre gerekir. Eksik reference,
taşma veya owner yokluğunda global fallback uygulanmaz.

`band.multi-component-excess-99-v1`, owner peak component'ini anchor alır. Sol ve
sağ yönde en yakın component'ten dışarı; gap en fazla 16 bin ve toplam significant
excess payı en az `0,02` olacak şekilde deterministik genişler. Eşitlik küçük gap,
büyük excess ve düşük shifted bin sırasıyla çözülür. Bir yönde koşul bozulursa daha
uzaktaki component'e atlanmaz. Retained excess için `[0,005,0,995]` desteği ve
search içinde en fazla bir-bin dış genişletme kullanılır.

## Frame-local kanal görünümü

Ham frame `FFT → fftshift → dört bin raised-cosine geçişli maske → ifftshift →
IFFT` sırasıyla işlenir. Global örnek indisi yalnız merkeze kaydırma osilatörünün
faz referansıdır. İşlem kesintisiz kanal alıcısı değildir ve frame'ler
birleştirilmez.

Maske impulse-response enerjisinin en az `0,999` kısmı için en kötü yarıçap
`1106` örnektir. 64 örnek sınırına yukarı yuvarlanan sabit guard `1152` örnektir.
Özellikler yalnız `[1152,2944)` aralığındaki `1792` örnekten çıkarılır.

Faz-sıçrama oranı bant-normalize azaltılmış dizide hesaplanır:

`D = clamp(floor(Fs/(4·B_est)), 1, 256)`

Eşik aşan bitişik farklar tek olay olarak kümelenir. Frame sınırında karşılaştırma
yapılmaz. BPSK için 256 örnek/sembol ve `D=47`; QPSK için 128 örnek/sembol ve
`D=23` analitik tutarlılık kapısıdır.

## Güç ve bant içi SNR

PHASE-02'nin pencere enerji kazancı düzeltilmiş iki taraflı kompleks
`psd_fs2_per_hz` dizisi kullanılır:

- `P_total = Σ PSD[k]·Δf`
- `P_noise = noise_density·bin_count·Δf`
- `P_signal = P_total-P_noise`
- `SNR = 10·log10(P_signal/P_noise)`

Hann veya FFT ölçeği ikinci kez uygulanmaz. `0 dBFS`, normalize kompleks örnekte
`|I+jQ|²=1 FS²` referansıdır. Sonuç dBm veya kalibre edilmiş RF gücü değildir.
Estimator kendi seçtiği bant desteğini kullanır; ground-truth banttan yardım almaz.

## Bellek ve geçmiş

Olay başına dört adet 32 elemanlı `float64` özellik kaydı tutulur. 64 olay için
özellikler `65.536`, frame indisleri `2.048`, maskeler `256`; toplam `67.840 byte`tır.
Seek, sarma, atlanan frame, kaynak, profil, Pfa, merkez veya DC değişimi geçmişi
temizler. Split geçmiş miras almaz; merge yalnız kalan track kimliğini korur.

R2 bant kenarı geçmişi ham I/Q veya tam PSD saklamaz. 64 olay için en fazla üç
alt kenar, üst kenar, noise, frame indisi ve iki boolean maske tutar; ek yük
`6.528 byte`, bütün parametre geçmişinin üst sınırı `74.368 byte`tır. İlk miss,
seek, frame atlama, split, owner değişimi veya nesil sıfırlaması R2 kenar
geçmişini temizler.

## Sınırlı sinyal alanı ayrımı

Doğru kesin karar paydasında yalnız AM/NFM ile OOK/2-FSK/BPSK/QPSK bulunur.
DSB-SC ve karma sınır zorunlu `Belirsiz` sahneleridir. Gürültü-only kesin sınıf
alamaz. En az üç gerçek frame ve en az 6 dB bant içi SNR olmadan kesin karar yoktur.
Bu sözleşme genel modülasyon tanıma iddiası değildir.

## Başarı kapılarının uygulanması

Yalnız donmuş katalogdaki `success_gates` alanları binding'dir. Aile, SNR ve
aile×SNR kırılımları katalog ayrıca zorunlu kılmadıkça tanısal rapordur. Bant için
kanonik binding koşulu 12 dB'dir; `-6/0/6 dB` ayrıca raporlanır fakat yeni bant
kapısı oluşturmaz. Spektral merkez, güç ve SNR için katalogda ayrı valid-rate
kapısı yoktur; invalid count/coverage tanısaldır ve sayısal q95/medyana girmez.

### Gate Applicability Matrix

Aşağıdaki tablo `parameter-scenes.json` içindeki bütün ve yalnız `success_gates`
alanlarını gösterir. “Tekil” ölçüler global başarı oranına giren her geçerli kestirime
uygulanır; kendiliğinden yeni aile veya SNR alt-grup kapısı oluşturmaz.

| Katalog alanı | Değer | Bağlayıcı uygulama |
|---|---:|---|
| `carrier_valid_rate_minimum` | `0.90` | Gözlenmiş taşıyıcısı `valid` beklenen global popülasyon |
| `carrier_q95_error_bins_maximum` | `0.50` | Geçerli taşıyıcı kestirimlerinin global q95 hatası |
| `spectral_center_q95_error_bins_maximum` | `1.50` | Geçerli spektral merkez kestirimlerinin global q95 hatası |
| `false_carrier_rate_maximum` | `0.02` | Taşıyıcı `not_observed` beklenen global popülasyon |
| `carrier_abstention_rate_minimum` | `0.90` | Taşıyıcı `not_observed` beklenen global popülasyon |
| `band_edge_q95_error_bins_floor` | `4.0 bin` | Her alt ve üst kenar için normalize limitin tabanı |
| `band_edge_q95_error_width_fraction` | `0.10` | Her alt ve üst kenar için truth genişliği çarpanı |
| `bandwidth_q95_relative_error_maximum` | `0.20` | 12 dB global geçerli bant popülasyonu |
| `bandwidth_valid_rate_minimum` | `0.95` | 12 dB global beklenen-geçerli bant popülasyonu |
| `region_success_rate_minimum` | `0.90` | Aşağıdaki üç tekil koşulu birlikte geçen 12 dB global hedef oranı |
| `region_coverage_minimum` | `0.85` | Tekil kestirim |
| `region_iou_minimum` | `0.75` | Tekil kestirim |
| `region_overreach_maximum` | `0.20` | Tekil kestirim |
| `close_pair_separate_rate_minimum` | `0.90` | 12 dB yakın-çift frame popülasyonu |
| `close_pair_cross_match_rate_maximum` | `0.02` | 12 dB yakın-çift frame popülasyonu |
| `noise_false_valid_rate_maximum` | `0.02` | 4096 noise-only temporal frame paydası |
| `power_q95_error_db_maximum` | `1.50 dB` | 6 ve 12 dB SNR global geçerli güç sonuçları |
| `snr_q95_error_db_maximum` | `2.00 dB` | 6 ve 12 dB SNR global geçerli SNR sonuçları |
| `zero_snr_power_median_error_db_maximum` | `2.00 dB` | 0 dB SNR global geçerli güç sonuçları |
| `zero_snr_median_error_db_maximum` | `3.00 dB` | 0 dB SNR global geçerli SNR sonuçları |
| `classification_wrong_definite_total_maximum` | `0.02` | 6 ve 12 dB kesin-sınıf ailelerinin global toplamı |
| `classification_wrong_definite_family_maximum` | `0.05` | 6 ve 12 dB'de her kesin-sınıf ailesi |
| `classification_correct_definite_total_minimum` | `0.85` | 6 ve 12 dB kesin-sınıf ailelerinin global toplamı |
| `classification_correct_definite_family_minimum` | `0.75` | 6 ve 12 dB'de her kesin-sınıf ailesi |
| `zero_snr_wrong_definite_maximum` | `0.05` | 0 dB kesin-sınıf ailelerinin global toplamı |
| `uncertain_rejection_rate_minimum` | `0.90` | Belirsiz aileler ile -6 dB kalite-ret popülasyonu |
| `noise_definite_count_maximum` | `0` | Noise-only ham kesin sınıf olay sayısı |

Bant için `-6/0/6 dB` aile×SNR kırılımları; güç/SNR için aile×güç×SNR
kırılımları ve ayrıca raporlanan invalid sayıları tanısaldır. Tabloda açıkça aileye
uygulanan sınıflandırma kapıları dışında hiçbir kırılım yeni bir zorunlu kapı değildir.

Noise-only doğrulaması 128 bağımsız dizi ve dizi başına 32 ardışık frame kullanır.
Bant false-valid oranı benzersiz doğrulanmış valid olay sayısının 4096 frame'e
oranıdır. Sinyal alanı için herhangi bir kesin Analog/Sayısal event bir kez sayılır
ve katalogdaki zorunlu ham count sıfırdır.

## Runtime ve başarısızlık

Operasyon zinciri yalnız allowlist içindeki `analysis.core-parameters/v1` bloğunun
validated profil parametrelerinden kurulur. Benchmark kapısı geçmezse validated
PHASE-04 profili üretilmez; eski profil başarı kanıtı sayılmaz. Profil ancak exact
comparison SHA ile güncel katalog, implementation ve PHASE-03 profil digestleri
eşleşirse yüklenir. Bağ geçersizse parametre katmanı kapatılır ve PHASE-03 profiline
dönülür.

## PHASE-04-R2 kilitli bant zinciri

R2 yalnız şu pre-binding zincirini çalıştırır:

1. `analysis.clustered-regions-v1`
2. `noise.trimmed-mean-20-hann-calibrated-v1`
3. `band.temporal-morphology-envelope-v1`

32 reference hücresinin sıralı 7–26. order-statistic ortalaması iid üstel modelde
`0,7827495643569612` beklenen orana ve `1,2775478205746595` düzeltmeye sahiptir.
Bu iid sonucu runtime katsayısı değildir. Periyodik Hann covariance modeli için
sabit seed `20260421`, `1.048.576` bağımsız frame ve gerçek PHASE-02 zincirinde
ayrı seed `20260422`, `16.384` frame ile doğrulanan düzeltme
`1,2601468855166762` değeridir. Kalibrasyon binding sahnelerini kullanmaz.

Seed ve grow kararları smoothing öncesi raw PSD/noise oranlarında sırasıyla
`6,907755278982137` ve `2,995732273553991` nominal oranlarıyla verilir. Bu
değerler exact Pfa veya CFAR katsayısı değildir. `[0,25, 0,50, 0,25]` smoothing
yalnız excess, fractional kenar ve ikinci moment hesabında uygulanır.

Anchor owner peak'ini içermelidir. Anchor dışı component ancak seed hücresi
içeriyorsa veya aynı analysis candidate'ın constituent region'larından biriyle
kesişiyorsa retained adayıdır. Salt grow/noise component zarfı genişletemez,
köprü olamaz ve arkasındaki bileşene atlanamaz. Gap `24` dahildir, `25` frontier'i
kapatır; en fazla 32 component ve 176 search hücresi işlenir.

Çizgisel/geniş ayrımı Hann ENBW karesinden türetilmez. Tam-bin ve fractional-bin
Hann tonları ile sabit RRC-benzeri analitik takım arasındaki ölçülmüş ikinci
moment aralığının orta noktası `2,7005873918882553 bin²` olarak method-lock'ta
sabitlenmiştir. Ayrışma marjı pre-binding kapısıdır.

İlk confirmed+observed frame public bant kenarı üretmez ve
`insufficient_quality/temporal_warmup` durumundadır. İkinci ardışık
confirmed+observed frame'de iki kenarın temporal medyanı yayımlanabilir. Bu
warm-up, katalogdaki beklenen-valid paydasını sessizce azaltmaz; benchmark yalnız
önceden sabit scoring frame'ini değerlendirir.

Frozen binding yalnız bir kez çalıştırılır. Ayrı seed `20260423` ve aile başına
32 trial içeren OOS sonuçları yalnız karakterizasyondur; selector, katalog kapısı
veya eşik ayarı için kullanılamaz. Harici ISM annotation içermediğinden bant
doğruluğu ground truth'u değildir.
