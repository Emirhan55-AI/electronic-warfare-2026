# Repository Dosya Karar Envanteri

- Envanter tarihi: 2026-08-22
- İş paketi: APP-A envanteri, APP-B uygulama kaydı
- Durum: APP-B temizliği 2026-08-23 tarihinde uygulandı

## Karar kodları

| Kod | Anlam |
|---|---|
| KORU | Ürün, algoritma, platform, doğrulama veya lisans açısından gerekli. |
| AYIR | Gerekli fakat üretim uygulamasından ayrı doğrulama/laboratuvar sınırına taşınmalı. |
| HARİCİLEŞTİR | Gerçek ve büyük yerel veri; hash manifesti korunarak repository dışına alınmalı. |
| YENİDEN ÜRET | Yerel build/cache ürünü; yeniden üretilebilirlik doğrulandıktan sonra temizlenebilir. |
| SİL ADAYI | Açıkça artık, bozuk veya yinelenen çalışma dosyası; APP-B onayı bekler. |
| İNCELE | Sahipliği veya faz bağı henüz tek başına güvenli karar vermeye yeterli değil. |

## Ürün/mock/golden ayrımı

| Yüzey | Karar | Gerekçe |
|---|---|---|
| `DeterministicMockBackend` ve Test Kaynağı UI seçeneği | AYRILDI | Backend `host/acquisition/mock.py`, doğrulama bileşimi `host/operator_console/laboratory.py` altında; ürün import grafiği ve paket manifesti dışında. |
| `datasets/fixtures/**` | KORU | Python, C ve RTL eşdeğerliğinin deterministik golden girdileri. |
| `results/evidence/**` normalized JSON ve kabul görselleri | KORU/İNCELE | KTR ve faz kanıtı; yalnız güncellik ve sahiplik kontrolü yapılabilir. |
| Eğitim DF sahneleri | AYRILDI | Algoritma kabulü için yalnız laboratuvar bileşiminde yüklenir; yayın uygulamasında eğitim modu yoktur. |
| Offline ET modelleri | AYRILDI | TX-kilitli doğrulama kapsamı ayrı laboratuvar girişindedir; yayın navigasyonunda ve paketinde yoktur. |
| `video_data/**` | HARİCİLEŞTİR | Önceki video/demo döneminden kalmış yerel veri; yayın repository'sinde ve paketinde bulunmayacak. Mühendislik değeri olan tekil SigMF kayıtları provenance manifestiyle harici alana alınacak. |

## İzlenmeyen dosyalar

| Yol veya grup | Yaklaşık boyut | Karar | Not |
|---|---:|---|---|
| `docs/decisions/ADR-0023-ET-OFFLINE-TASK-CONSOLE.md` | <0,01 MiB | KORU/AYIR | Offline ET ürün sınırı kararı olarak gerekli; kapsam adı APP-C'de kesinleşmeli. |
| `docs/learning/**` | <0,01 MiB | KORU | Mühendislik öğrenme notları; ürün paketine girmez. |
| `host/operator_console/map_assets/**` | 2,07 MiB | KORU | MapLibre/PMTiles runtime ve lisansları; paketleme yolu düzeltilmeli. |
| `host/operator_console/map_direction.py` | 0,01 MiB | KORU | Harita sunumu; APP-D'de `app/` sınırına taşınacak. |
| `host/operator_console/map_providers.py` | <0,01 MiB | KORU | Harita provider sözleşmesi. |
| `host/operator_console/pc_location.py` | <0,01 MiB | KORU | İzinli kullanıcı isteğiyle konum adaptörü. |
| `host/operator_console/profiler.py` | <0,01 MiB | SİL ADAYI | Çalışmıyor ve kök profiler ile yineleniyor. Gerekli ölçümler tek araçta yeniden kurulacak. |
| `prof2.py` | <0,01 MiB | SİL ADAYI | Kök çalışma dosyası; sözdizimi hatalı. |
| `ps/p0/include/p0_fclk_guard_*.h` | 0,02 MiB | İNCELE/KORU | FCLK güvenlik sınırı; repository allowlist ve P0 sözleşmesiyle sahipliği doğrulanmalı. |
| `ps/p0/src/p0_fclk_guard*.c` | 0,04 MiB | İNCELE/KORU | Aynı platform özelliğinin kaynakları; gereksiz olduğuna dair kanıt yok. |
| `ps/p0/petalinux/p0-fclk-guard*` | <0,01 MiB | İNCELE/KORU | PetaLinux paketleme kaynakları; platform katmanına aday. |
| `reference/et/gnss.py` | <0,01 MiB | AYIR | Offline metadata doğrulaması; ürün ET görev yüzeyinden ayrılmalı. |
| `reference/et/interleaved.py` | 0,01 MiB | AYIR | Offline state machine doğrulaması. |
| `reference/et/results.py` | <0,01 MiB | AYIR | Offline ET sonuç sözleşmesi. |
| `reference/p0/df_fixtures.py` | <0,01 MiB | AYIR | Golden/eğitim üretimi; ürün uygulaması ithal etmemeli. |
| `reference/p0/field_df.py` | <0,01 MiB | KORU | Saha ölçüm sözleşmesi. |
| `reference/p0/map_direction.py` | 0,01 MiB | KORU | Sunumdan bağımsız coğrafi geometri sözleşmesi. |
| `reference/p0/recorded_df.py` | 0,01 MiB | İNCELE/KORU | Gerçek kayıt analizi; yerel veri manifestine bağlanmalı. |
| `reference/p0/two_point_df.py` | <0,01 MiB | İNCELE | KTR-4.5 konum fazıyla karışmamalı; yalnız iki yönlü güç kararıysa adı ve kapsamı netleştirilmeli. |
| `reference/sigmf/hackrf.py` | <0,01 MiB | KORU | Gerçek HackRF kayıt metadata sözleşmesi. |
| `results/evidence/et-offline/**` | 0,47 MiB | İNCELE/KORU | Offline doğrulama kanıtı; ADR/KTR sahipliği doğrulanmalı. |
| `results/evidence/p0/fclk-guard-build.json` | 0,01 MiB | İNCELE/KORU | Platform build kanıtı; kaynaklarıyla aynı sahiplik kararı verilmeli. |
| `results/evidence/p0/training-functional-acceptance-v1.json` | 0,01 MiB | KORU | Birleşik kabul kanıtı; mevcut test baseline'ında stale/FAIL. |
| Yeni `results/evidence/phase08a/*.png` dosyaları | 0,65 MiB | SİL ADAYI | Video/UI yenileme çalışmasının kanonik olmayan ekranları; zorunlu release acceptance kanıtı oldukları gösterilmedikçe kaldırılacak. |
| `scripts/analyze_hackrf_amplitude_df.py` | <0,01 MiB | KORU | Gerçek kayıt analiz aracı; yerel veri yolu parametreleştirilmeli. |
| `scripts/verify_p0_training_acceptance.py` | 0,02 MiB | KORU | Birleşik kabul kapısı. |
| `scripts/wrap_hackrf_iq_as_sigmf.py` | <0,01 MiB | KORU | Gerçek IQ'yu sözleşmeli SigMF'e dönüştürür. |
| `tests/p0/**` | 0,02 MiB | İNCELE/KORU | FCLK guard kaynaklarıyla birlikte allowlist kararı gerekir. |
| Yeni `tests/test_*` entegrasyon dosyaları | 0,03 MiB | KORU/İNCELE | Karşılık gelen ürün/platform dosyası korunursa testleri de korunur. |
| `video_data/**` | 763,25 MiB | HARİCİLEŞTİR | Video/demo dönemi yerel kayıtları. Yayın repository'sinden çıkarılacak; korunacak tekil mühendislik kayıtları için provenance ve hash manifesti zorunlu. |

### `video_data` byte eşitliği baseline'ı

2026-08-22 tarihinde dört `.iq` dosyasının karşılık gelen `.sigmf-data`
dosyasıyla SHA-256 özeti eşit bulunmuştur. Yalnız `.iq` kopyalarının kaldırılması
381,71 MiB yinelenen `.iq` içeriği APP-B onayıyla kaldırıldı; byte olarak aynı
SigMF veri dosyaları yerel mühendislik alanında korunuyor.

| Kayıt | Byte | SHA-256 | `.iq == .sigmf-data` |
|---|---:|---|---|
| `analog_voice` | 120.000.000 | `9ac85403bff4f04e8906d7c787767d0d3fe86904fdbd666d493a43d822f083d1` | Evet |
| `detection` | 256.163.840 | `2648e5ee872fbe764c74d4bce7f9c002f32235836805f0e4d4c35bd4b004d126` | Evet |
| `df_000` | 12.000.000 | `5d3e4eeb5f388e20372552884e433a34569910958217ccd5062fdf8c2a531956` | Evet |
| `df_090` | 12.000.000 | `ffda7fbcb80d98dedb8d4ad2e1db96b7543d9620e03f070edff6cb9024e806a8` | Evet |

Metadata yalnız `HackRF recorded IQ replay` açıklamasını, örnekleme hızını ve
merkez frekansını içerir. Kayıt zamanı, fiziksel düzen, izin/provenance ve cihaz
seri kimliği bulunmaz. Bu bilgiler tamamlanmadan kayıtlar saha doğruluk veya RF
performans kanıtı sayılamaz.

## Yayın paketi dışlama listesi

Aşağıdaki sınıflar repository'de doğrulama amacıyla korunsa bile yayın paketine
giremez:

- `tests/**`, `datasets/fixtures/**` ve golden vektör üreticileri,
- `results/evidence/**` geliştirme ve tarihsel kanıtları,
- `scripts/render_*`, `scripts/run_*_demo.py` ve eğitim araçları,
- deterministic/mock backend implementasyonları,
- `video_data/**` ve operatörce seçilmemiş yerel kayıtlar,
- offline ET laboratuvar arayüzü,
- geleceğe ayrılmış fakat bağlı olmayan GNSS/TX/kart kontrolleri,
- profiler, benchmark scratch dosyaları ve geliştirme logları.

Paket içeriği APP-C'de otomatik allowlist testiyle doğrulanacaktır.

## Ignore edilen yerel çıktılar

| Yol | Yaklaşık boyut | Karar | Temizlik ön koşulu |
|---|---:|---|---|
| `build/` | 391,90 MiB | YENİDEN ÜRET | Gerekli Vivado/PetaLinux artifact'larının komut, sürüm ve normalized evidence ile yeniden üretilebildiği doğrulanmalı. |
| `.pytest_cache/` | 0,05 MiB | YENİDEN ÜRET | Doğrudan temizlenebilir; işlevsel veri değildir. |
| `.benchmarks/` | <0,01 MiB | YENİDEN ÜRET | Kalıcı benchmark kanıtı içerip içermediği kontrol edilmeli. |
| `.Xil/` | <0,01 MiB | YENİDEN ÜRET | Xilinx geçici durum alanı. |
| `__pycache__/**` | Değişken | YENİDEN ÜRET | Python cache'i. |
| `vivado*.log`, `vivado*.jou` | 0,21 MiB | YENİDEN ÜRET | Normalized evidence içinde benzersiz bilgi olmadığı doğrulanmalı. |
| `dfx_runtime.txt` | <0,01 MiB | YENİDEN ÜRET | Geçici Vivado runtime kaydı. |

## APP-B uygulama sonucu

1. Dört `.iq` dosyasının karşılık gelen `.sigmf-data` dosyalarıyla SHA-256
   eşitliği yeniden doğrulandı; yalnız yinelenen `.iq` kopyaları kaldırıldı.
2. Tekil SigMF kayıtları `datasets/external/local/video_data/` altında,
   `release_package_allowed=false` ve eksik provenance beyanıyla manifestlendi.
   Bu alan Git ve yayın paketi dışındadır.
3. Bozuk `prof2.py`, yinelenen `host/operator_console/profiler.py`, yedi kanonik
   olmayan PHASE-08A ekran görüntüsü, Python/Xilinx cache'leri ve kök Vivado
   log/journal dosyaları kaldırıldı.
4. `build/` altında boot, bitstream, XSA, kernel modülü ve PetaLinux çıktıları
   bulunduğu için yeniden üretilebilirlik kanıtı olmadan silinmedi.
5. FCLK guard kaynakları güvenlik/platform sahipliğiyle; gerçek-kayıt dönüştürme
   ve analiz kaynakları offline mühendislik sahipliğiyle repository sözleşmesine
   işlendi. Yerel kayıt byte'ları allowlist'e alınmadı.
6. PHASE-00 doğrulayıcısına tarihsel kanıtı değiştirmeyen `--check` modu ve bunun
   byte-salt-okunur regresyon testi eklendi.

APP-B kapsamındaki repository ve tarihsel kanıt regresyonu 48/48 geçti. Tam test
takımında temizlik öncesi baseline'dan kalan beş UI/kabul hatası vardır; APP-C/E/F
kapsamına devredilmeleri kullanıcı kapı onayı bekler.
