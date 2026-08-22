# Operatör Uygulaması Code Review Baseline'ı

- İnceleme tarihi: 2026-08-22
- İş paketi: APP-A
- Kapsam: repository, operatör uygulaması, test/golden veri sınırı ve paketleme
- Kaynak değişikliği: Yok
- Silinen veya taşınan dosya: Yok

## Yönetici özeti

Mevcut uygulama işlevsel bir replay ve doğrulama temelini korumakla birlikte ürün,
laboratuvar ve test yüzeylerini aynı süreçte birleştirmektedir. Birincil risk Python
dilinin kendisi değil; tek bir pencere sınıfında biriken sorumluluklar, üretim
akışına bağlı mock kaynaklar, merkezi olmayan kullanıcı metinleri ve doğrulama
sözleşmesiyle senkron olmayan son arayüz değişiklikleridir.

Tam regresyon koşusunda 425 test geçmiş, 1 test kontrollü atlanmış ve 7 test
başarısız olmuştur. Bu baseline yeşil değildir; APP-B temizliği başlamadan önce
başarısızlıkların sahipliği korunmalıdır.

## Ürünleşme hedefi

Kullanıcı açıklamasıyla önceki video/demo dönemi kapanmıştır. Bundan sonraki
ürün sınırı yayın adayı bir operatör uygulamasıdır:

- uygulama gerçek SigMF kayıtları ve gerçekten mevcut olduğunda canlı donanım
  adaptörleriyle çalışır,
- donanım yoksa bunu açık durum olarak gösterir; veri veya sonuç taklit etmez,
- test/eğitim/replay kabul araçları ayrı mühendislik giriş noktasında kalır,
- geçmiş video ekranları ve görsel maketler ürün davranışının kaynağı olmaz,
- yayın paketine yalnız runtime için gereken kod, kaynak ve lisanslar girer.

Bu hedef nedeniyle mock yüzeyler yalnız yeniden adlandırılmayacak; üretim bağımlılık
grafiğinden ve paket içeriğinden çıkarılacaktır.

## Öncelikli bulgular

### P0 — Ürün ve test kaynağı aynı çalışma zamanı sınırında

- `host/operator_console/controller.py` içinde `DeterministicMockBackend`,
  controller'ın varsayılan test backend factory'sidir.
- `host/operator_console/main_window.py` veri kaynağı seçicisinde
  `deterministic_test` seçeneğini üretim görünümünde sunar.
- Yön bulma görünümü `video_data/df_000.sigmf-meta` ve
  `video_data/df_090.sigmf-meta` yollarına doğrudan bağlıdır.

Sonuç: Üretim uygulamasının gerçek kaynak durumu ile eğitim/doğrulama durumu
derleme ve giriş noktası seviyesinde ayrılmalıdır.

### P0 — Repository sözleşmesi mevcut ağaçla uyuşmuyor

`scripts/verify_phase00.py` allowlist'i, yeni PetaLinux/FCLK guard kaynaklarının,
gerçek kayıt entegrasyonunun, yeni yön/harita dosyalarının ve bazı kanıtların bir
kısmını tanımamaktadır. Bunun sonucu iki repository sözleşmesi testi düşmektedir.

Bu durum tek başına dosyaların gereksiz olduğunu göstermez. Önce her dosyanın
faz/kontrol noktası sahipliği belirlenmeli, sonra ya allowlist ve KTR güncellenmeli
ya da dosya onaylı kapsam dışına taşınmalıdır.

### P1 — `MainWindow` aşırı sorumluluk taşıyor

`host/operator_console/main_window.py` yaklaşık 189 KiB, yaklaşık 3.900 satır ve
170 metottur. Aynı sınıf:

- altı ana çalışma alanını kurar,
- DF ve harita modellerini yönetir,
- ET motorlarını doğrudan oluşturup çalıştırır,
- animasyon zamanlayıcılarını yönetir,
- replay arama motorunu çağırır,
- kullanıcı metinlerini ve durum dönüşümlerini içerir.

Sunum, use-case ve domain servisleri ayrılmadan yeni tasarım eklemek bakım ve
regresyon maliyetini büyütür.

### P1 — Katman yönü tutarlı değil

`reference/p0/hackrf_search.py`, `host.acquisition` katmanını ithal etmektedir.
Golden/reference katmanının platform adaptörüne bağımlı olması hedeflenen
bağımsız doğrulama sınırını bozar. Araya port/protocol sözleşmesi konulmalıdır.

### P1 — Paketlenen harita yeteneği geliştirme ortamıyla eşleşmiyor

Harita görünümü çalışma zamanında `QtWebEngine` kullanmayı denerken
`host/operator_console/pysidedeploy.spec` QtWebEngine'i dışlamaktadır. Kaynak
uygulamada görülen haritanın paketli uygulamada bulunmaması riski vardır.

### P1 — Kullanıcı metni ve tema regresyonları

- Parametre ve Dinleme sağ panelleri 1920×1080 offscreen görüntülerde açık renk
  palete düşmüştür.
- 960×600 görünümünde `Tüm bant taranır` etiketi ayrılan genişliğe sığmaz.
- `Secili Sinyal`, `Gelismis`, `ac/kapat` gibi Türkçe karakter kuralını ihlal
  eden metinler vardır.
- `main_window.py` içinde yaklaşık 800 benzersiz kullanıcı metnine benzeyen sabit
  bulunur; `ui_text.py` tek kaynak değildir.

### P2 — Profiling araçları çalışmıyor

- `host/operator_console/profiler.py`, `from __future__` yerleşimi nedeniyle
  parse edilememektedir.
- Kök dizindeki `prof2.py`, f-string sözdizimi nedeniyle çalışmamaktadır.
- İki dosya da izlenmeyen çalışma dosyasıdır ve aynı amacı kısmen tekrarlar.

APP-B'de tek, tekrarlanabilir ve test verisini açıkça belirten benchmark aracına
karar verilmelidir.

## Test baseline'ı

Komut:

```text
python -m pytest -q -p no:cacheprovider
```

Sonuç:

```text
425 passed, 1 skipped, 7 failed in 456.34s
```

| Başarısız test | Kök neden sınıfı | Sahip paket |
|---|---|---|
| `test_all_visible_labels_fit_at_minimum_logical_size` | Minimum ekranda metin taşması | APP-E/APP-F |
| `test_df_training_fixture_is_independent_and_truthfully_labelled` | Eğitim etiketi ile kabul testi senkron değil | APP-C |
| `test_required_ed_areas_and_real_result_binding` | `ET` kabul adı ile `Elektronik Taarruz` sekme adı senkron değil | APP-C/APP-E |
| `test_three_judge_modes_execute_real_replay_backend_and_validate_input` | Hata metni sözleşmesi senkron değil | APP-E |
| `test_compact_evidence_is_current_and_all_host_gates_pass` | Önceki UI/kabul hatalarının birleşik sonucu | İlgili paket sonrası |
| `test_every_repository_contract_check_passes` | Allowlist ile izlenmeyen dosyalar uyuşmuyor | APP-B |
| `test_only_approved_later_phase_paths_extend_the_baseline` | Aynı repository sahiplik uyuşmazlığı | APP-B |

Testler yeni metne körlemesine uydurulmamalıdır. Önce görev terminolojisi ve ürün
sınırı karara bağlanmalı, ardından test ve kullanıcı metni aynı sözleşmeden
üretilmelidir.

## Ölçülen uygulama performansı

Kayıtlı PHASE-01 fixture'ı ile izole benchmark sonucu:

- 10 FPS hedefi: 15 frame, yaklaşık 10,07 FPS.
- 30 FPS hedefi: beş koşunun her birinde 34 frame; yaklaşık 28,89–29,46 FPS.
- En büyük ölçülen heartbeat aralığı: yaklaşık 52,7 ms.
- Beş cold smoke koşusu: 1,58–1,66 saniye duvar süresi; her koşu 200 ms açık
  kalma zamanlayıcısını içerir.

Bu ölçüm gerçek HackRF, 763 MiB yerel kayıtlar, harita veya FPGA veri yolu
performansını kanıtlamaz. Yalnız mevcut replay/spektrum yolunda tam C++ yeniden
yazımını zorunlu kılan bir kanıt bulunmadığını gösterir.

## APP-A kararı

- Kaynak, test, kayıt veya kanıt dosyası silinmez.
- Mevcut kullanıcı değişiklikleri korunur.
- Video/demo dönemi kapanmış kabul edilir; bu amaçla üretilmiş ürün yüzeyleri ve
  kanonik olmayan ekranlar APP-B'de kaldırılacak adaylardır.
- Golden fixture ve replay kabul verisi yalnız `verification`/test sınırında
  korunur; yayın paketine girmez.
- APP-B yalnız `REPOSITORY_DISPOSITION.md` içinde `SİL` veya `HARİCİLEŞTİR`
  adayı olarak işaretlenen girdiler için ayrıca onay alındıktan sonra başlayabilir.
