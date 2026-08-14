# İşgal Edilen Bant Genişliği Sözleşmesi

## Durum ve kapsam

- Sözleşme kimliği: `phase04d1-obw99-contract`
- Sürüm: `1`
- Durum: `Accepted`
- Capability profil kimliği: `phase04d1-occupied-bandwidth-capability`

Bu belge yalnız `%99 İşgal Edilen Bant Genişliği (OBW99)` ölçümünün önerilen veri, referans, kabul ve dürüstlük sözleşmesini tanımlar. Estimator uygulaması, method-lock, runtime profili veya başarı kanıtı değildir.

## Ölçüm tanımı

OBW99, gürültü çıkarılmış gözlenen PSD üzerindeki toplam excess gücün alt `%0,5` ve üst `%0,5` kümülatif noktaları arasında kalan aralıktır:

`OBW99 = f_upper_99_5 − f_lower_0_5`

Bu çıktı gerekli bant, nominal kanal bant genişliği, protokol bant genişliği veya eski KTR eşik zarfı değildir.

## Kamuya açık sonuç modeli

Gelecekteki capability çıktısı yalnız şu alanları taşıyabilir:

| Alan | Birim/anlam |
|---|---|
| `occupied_bandwidth_hz` | OBW99 genişliği, Hz |
| `lower_occupied_edge_hz` | Alt `%0,5` güç kenarı, Hz |
| `upper_occupied_edge_hz` | Üst `%99,5` güç kenarı, Hz |
| `occupied_power_fraction` | Sabit `0.99` |
| `state` | Mevcut public geçerlilik durumu |
| `observation_count` | Aynı event için ardışık confirmed+observed frame sayısı |
| `temporal_state` | Isınma, kararlı veya sıfırlanmış durum |
| `quality_reasons` | Sabit sıralı typed neden listesi |
| `analysis_clipped` | Analysis sınırının ölçümü kısıtlayıp kısıtlamadığı |
| `candidate_isolated` | Yayının komşu candidate'lardan güvenle ayrılıp ayrılmadığı |

Kamuya açık frekans sonuçları Hz cinsindedir. Shifted bin konumları yalnız tanısal kanıtta tutulur. Sonuç, native FFT çözünürlüğünün desteklemediği fiziksel hassasiyetle sunulmaz. Fractional-bin interpolasyonu grid üzerinde daha düzgün kenar verir; yeni RF bilgisi üretmez.

Taşıyıcı, spektral merkez, güç/SNR, sinyal alanı, gerekli bant ve nominal bant bu capability sonucuna sayı olarak eklenmez.

## Durum semantiği

| Koşul | Sonuç |
|---|---|
| Capability profili yok/devre dışı | Sonuç nesnesi yok; UI: `Henüz doğrulanmadı` |
| Yayın gözlenmedi | `not_observed` |
| Ölçüm yapıldı, güç/kararlılık yetersiz | `insufficient_quality` |
| Candidate ayrılamadı veya clipping çözülemedi | `uncertain` |
| Ölçüm kavramsal olarak uygulanabilir değil | `not_applicable` |
| Bütün bağlar ve kalite koşulları sağlandı | `valid` |

İlk confirmed frame kesin OBW sonucu üretmez; `observation_count=1` ile `insufficient_quality` durumundadır. En az dört ardışık confirmed+observed frame tamamlanmadan `valid` yayımlanmaz.

## Clean OBW99 referans sözleşmesi

Referans aşağıdaki zincirle üretilecektir:

1. Runtime ile aynı örnekleme hızında uzun, gürültüsüz ve deterministik I/Q üretilir.
2. Yalnız aktif segmentler 4096 örneklik periyodik Hann frame'lerine ayrılır.
3. PHASE-02 ile aynı enerji normalizasyonu kullanılır.
4. 256 aktif frame'in PSD'si ortalanır; 64 ve 128 frame ara yakınsama noktaları kaydedilir.
5. Frekans grid'i yalnız kenar interpolasyonu için 8 kat sıfır doldurulur.
6. Toplam gücün kümülatif `%0,5` ve `%99,5` noktaları fractional-grid interpolasyonuyla bulunur.
7. 128 ve 256 frame sonuçları arasındaki her kenar farkı en fazla `0.125` native bin olmalıdır.

Sıfır doldurma öncesi ve sonrası toplam güç korunumu bağıl `1e-10`, sıfıra yakın güçte mutlak `1e-12 FS²` toleransıyla kontrol edilir. Byte eşitliği beklenmez. Analitik Carson, RRC veya nominal kanal formülleri OBW99 ground truth'u değildir.

## Doğrudan estimator yapısı

D1 için tek bir label-free cumulative-OBW99 yolu planlanır:

1. PHASE-03 confirmed ve o frame'de observed event alınır.
2. Candidate hull çevresinde bounded analysis span kurulur.
3. Dış reference hücrelerinden robust gürültü seviyesi hesaplanır.
4. `max(PSD − noise, 0)` ile excess PSD elde edilir.
5. Dört ardışık aktif frame için bounded PSD ring-buffer ortalaması alınır.
6. Toplam excess gücün kümülatif toplamı hesaplanır.
7. `%0,5` ve `%99,5` noktaları bulunur.
8. İki komşu grid değeri arasında fractional-bin interpolasyonu yapılır.
9. Clipping, yetersiz excess veya zamansal kararsızlıkta kesin sonuçtan kaçınılır.
10. Kenarlar ve OBW99 mutlak Hz olarak raporlanır.

Runtime kararına ground truth, scene kimliği, modülasyon etiketi, nominal merkez veya SNR etiketi verilmez.

## Bounded analysis span

Kesin öneri `reference-contract.json` içindedir. Özet:

- başlangıç: candidate hull çevresinde her iki yana `32` bin,
- genişletme: gerekli tarafta `16` bin,
- maksimum: `256` bin,
- candidate dışı reference guard: `4` bin,
- her tarafta `32` reference hücresi,
- analysis kenar kalite guard'ı: `4` bin,
- komşu confirmed candidate'a doğru orta nokta aşılmaz ve `4` bin ayırma rezervi korunur,
- global shifted güvenli sınır `[20, 4075]` dışına çıkılmaz,
- sınır gücü çözülemeden komşu/global/maksimum sınıra gelinirse sonuç `uncertain` olur.

Bir taraf, kenar guard'ındaki kümülatif quantile veya o taraftaki guard excess payı toplam excess gücün `0.005` bölümünü aşıyorsa genişletilir. İki taraf temizlenene kadar veya bounded durma koşuluna kadar sürdürülür.

## Temporal ve bellek sözleşmesi

- Yalnız confirmed+observed frame feature kaydı üretir.
- Dört ardışık aktif frame zorunludur.
- Miss, seek, frame atlama, kaynak/profil/ayar nesli değişimi geçmişi temizler.
- Split sonrasında çocuklar geçmiş miras almaz.
- Merge sonrasında ilgili geçmişlerin tamamı temizlenir; yayınlar yeniden dört frame gözlenir.
- Owner değişiminde geçmiş temizlenir.
- Dört PSD frame'i, running sum ve dört kenar çifti ring-buffer içinde bounded tutulur.

Float64 Python referansında event başına üst sınır `10.304 byte`, en fazla 64 event için toplam `659.456 byte`tır. Bu sayı RF örnek tamponunu içermez ve FPGA bit genişliği iddiası değildir.

## Kabul kapıları

Tek sayısal sözleşme [acceptance-gates.json](../../datasets/fixtures/phase04d1/acceptance-gates.json) içindedir. Kapılar şartname tarafından verilmemiştir; proje içi ölçüm doğruluğu ve dürüst abstention kapılarıdır. Binding ve kilitli OOS ayrı değerlendirilir. Binding `valid-rate ≥0,95` global olarak ve her desteklenen sinyal ailesinde ayrı sağlanır. OOS `valid-rate ≥31/32` her desteklenen ailede ayrı sağlanır. Aggregate sonuç aile başarısızlığını gizleyemez.

Invalid, abstention, `insufficient_quality` ve `uncertain` sonuçlar sayısal q95 dağılımına girmez, ancak beklenen-valid popülasyonun OBW valid-rate paydasında başarısız sayılır. Noise-only ve gerçekten ölçüm beklenmeyen negatif popülasyonlar valid-rate paydasına girmez; kendi false-valid kapılarıyla değerlendirilir. Empirik q95, sıralı dizide bir tabanlı `ceil(0,95 × N)` rank kullanan deterministic nearest-rank yöntemidir. Noise-only false-valid, gerçek PHASE-03 temporal zincirinde confirmed+observed ve `state=valid` sonuç üretildiği frame üzerinden ölçülür.

## Profil bağı ve güvenli fallback

Capability profili ancak aşağıdaki bağlar birlikte geçerse kullanılabilir:

- PHASE-03 profil kimliği ve SHA,
- D1 method-lock kimliği ve SHA,
- reference-contract SHA,
- acceptance-gates SHA,
- binding comparison SHA,
- locked OOS comparison SHA,
- bütün zorunlu kapıların `passed` durumu.

Bağlardan biri eksik, stale, bozuk veya başarısızsa D1 sonuçları yüklenmez; uygulama saf PHASE-03 `regional` tespit profiline döner. Eski capability profilinin diskte bulunması kullanılabilir olduğu anlamına gelmez.

## Arayüz sınırı

Capability etkin olduğunda yalnız aşağıdakiler görünür:

- `İşgal Edilen Bant Genişliği`,
- `Alt Bant Sınırı`,
- `Üst Bant Sınırı`,
- `Ölçüm: %99 güç`,
- gözlem/temporal durumu,
- kalite nedeni.

Gerekli/nominal bant, taşıyıcı, güç/SNR ve analog/sayısal alanları sayı göstermez. Genel “PHASE-04 başarılı” ifadesi kullanılmaz.

## Bu aşamada uygulanmayacaklar

Estimator, reference generator, sahne üretici, evaluator, runtime blok, profil, UI ve evidence bu D1A/D1B sözleşme turunda oluşturulmaz. Yeni dependency, ML, PHASE-05, RTL veya SystemVerilog eklenmez.
