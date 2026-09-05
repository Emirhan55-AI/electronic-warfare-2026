# Repository Çalışma Kuralları

- Proje fazları `docs/plans/IMPLEMENTATION_ROADMAP.md` sırasıyla uygulanır.
- Kullanıcı açıkça onaylamadan sonraki faza geçilmez.
- KTR gereksinim izlenebilirliği her değişiklikte korunur.
- Donanım, doğruluk veya performans iddiaları tekrarlanabilir test kanıtına dayanır.
- RTL, yazılım referans modeli ve doğrulama testleri birlikte geliştirilir.
- Kullanıcı tarafından oluşturulan veya değiştirilen dosyalar korunur.
- Görev kapsamı dışındaki yeniden düzenlemeler yapılmaz.
- Açık izin olmadan commit, tag veya push yapılmaz.
- Genel kullanıma açık dosyalarda geliştirme araçlarına veya otomasyon sürecine ait atıflar kullanılmaz.
- RF yayın işlevleri yalnızca güvenli, kontrollü ve izinli test koşulları için geliştirilir.
- Kullanıcıya görünen arayüz metinleri Türkçe ve UTF-8 olur; `ç Ç ğ Ğ ı İ ö Ö ş Ş ü Ü` karakterleri ASCII karşılıklarına çevrilmez.
- Teknik kısaltmalar korunabilir; kullanıcıya yönelik açıklamalar Türkçe olur.
- Uygulanmamış donanım veya algoritma özellikleri çalışıyormuş gibi gösterilmez.
- Arayüz sade, profesyonel ve görev odaklı tutulur.

## Başlangıçta okunacak belgeler

1. `docs/interfaces/SIGNAL_DETECTION_STATUS.md`: güncel sinyal tespiti durumu,
   kaynak/kanıt bağlantıları ve açık kabul kapıları.
2. `docs/plans/IMPLEMENTATION_ROADMAP.md`: onaylı faz sırası ve çalışma kapsamı.
3. `docs/requirements/KTR_TRACEABILITY.md`: gereksinim ve doğrulama bağı.
4. `README.md` ve `docs/architecture/P0_SYSTEM_ARCHITECTURE.md`: sistem özeti
   ve PC/PL/PS görev paylaşımı.
5. İlgili `docs/interfaces/` sözleşmeleri ve `docs/decisions/` karar kayıtları.

Tarihli faz/ADR kayıtları o sürümün sonucudur. Güncel yetenek için kaynak ve
imaj hash'leri eşleşen kanıt aranır; eski fiziksel sonuç yeni ikiliye aktarılmaz.
Durum değişikliğinde yukarıdaki belgeler ile etkilenen bileşen README'leri
birlikte güncellenir. Geçmiş ölçümler ve dondurulmuş yöntem kayıtları korunur.

## Güncel kanıt aktarımı — 6 Eylül 2026

- PHASE-08 / ST-06 ve KTR-4.1 / KTR-4.1-OPS-B0 kabulü açıktır.
- Tarihsel `native-channelizer-v3.json`, `st06-parallel-product-v1.json`
  ve ZIP özgün `559d496` baytlarıyla korunur. Hash veya yeniden doğrulama
  tarihi değiştirilerek eski ölçüm yeni kaynağa bağlanmaz.
- `live-rx-endurance-v3` tek 439.453 karelik arayüzsüz alım/taşıma
  gözlemidir: USB/CRC/sıra/kuyruk hatası 0, 488,2153 kare/s,
  `preview_frames: 0`. GUI, RF doğruluğu veya nominal hız marjı kabulü değildir.
  Önceki kaynakla iki uzun koşu `usb_overrun` ile başarısızdır.
- Kuyruk/işlem tanıları son kaynakta 16 karede bir örneklenir; 6/512 kesin
  kuyruk tepesi değildir. USB kök nedeni veya kalıcı çözüm kanıtlanmadı.
- `python scripts/verify_phase08_evidence_recovery.py` üç koşuyu ve
  özgün kanıt bütünlüğünü doğrular. ST-06 arşivi `--historical` ile denetlenir;
  `verify_st06_parallel_product.py` seçeneksiz güncel kaynak kontrolü
  değiştirilmiş `live_ed.py` nedeniyle başarısız olmalıdır. Bu açık kapıdır.
- Sonraki kabul tekrarlı gerçek GUI+RX, kontrollü kör RF ve soğuk açılıştır.
  RX-only bayrağından harici vericinin kapalı olduğu çıkarılmaz.
- Aşağıdaki 5 Eylül aktarımı tarihsel kapsamındadır; güncel ayrıntı
  `docs/interfaces/SIGNAL_DETECTION_STATUS.md` içindedir.

## Tarihsel aktarım — 5 Eylül 2026

- Kapsam PHASE-08 / ST-06 sinyal tespitidir; ST-06 tamamlanmadı.
  Parametre, yön bulma veya ET için yeni faz açılmaz.
- PL: Hann → 4096 FFT → UQ28.30 güç → OS-CFAR hücre kararı.
  Kartın ARM CPU0 çekirdeği DMA ve güç doğrulama/çözmeyi; ARM CPU1
  dar/geniş aday, sekiz karelik geniş bant ve temporal yaşam döngüsünü yürütür.
  CPU0 bilgisayar değildir. PC HackRF USB alımı, taşıma, görselleştirme ve
  kayıt yolundadır. Geniş bant C çekirdeği kayan noktalıdır.
- Son üretim değişikliği tampon sahipliği değişimi ve geri alma kopyalarının
  azaltılmasıdır. Ek kuyruk belleği 272 KiB; medyan, eşikler ve RTL değişmedi.
  Medyan/hibrid/döngü birleştirme deneyleri üretime alınmadı.
- Güncel kanıt `results/evidence/phase08/st06-parallel-product-v1.json` ve ZIP:
  paket hizmeti 508,56 / 502,40 / 508,93 kare/s; 16.000 ölçüm karelik karma
  tekrar 529,30 kare/s. Gerekli 488,28125 kare/s bu dijital yüklerde sağlandı.
  En düşük pay yaklaşık %2,89; beş ham yanıt eski paketle birebir eşleşti.
  Bu sonuç saha doğruluğu veya bütün ST-06 kabulü değildir.
- Güncel yerel çıktı `build/p0/st06-parallel-product/`; yeni ortamda varlığı
  varsayılmaz. Hizmet SHA-256:
  `4bc02505c81254219cceaaf8adf74c5a742cdf8114deb6a288b8d68d5dce1dbf`.
  İmaj SHA-256:
  `d640cb1caab5b76c13aebdb645cb3399dd975fa1ccb9d032429c9dec2c8051b9`.
  Yükleme öncesi kaynak/bitstream/hizmet/imaj özetlerini yeniden doğrula.
- Kart yüklemesi geçicidir; SD/BOOT.BIN değişmedi. Yeniden başlatmada yeni
  hizmetin korunduğunu varsayma. Seri port, ağ, SSH anahtarı ve çalışan ikiliyi
  yeniden gözle; parola veya geçici oturum kimliği kaydetme.
- Sıradaki iş: gerçek HackRF → PC → kart → arayüz yolunda sürekli RX testi.
  Önce test vericisi kapalıyken kare/sıra kaybı, kuyruk, gecikme ve görüntü
  sürekliliğini ölç. Verici kapalı olması ortamın RF sessiz olduğu anlamına gelmez.
  Ardından kontrollü kör RF doğruluğu; ayrıca soğuk açılış kabulü gerekir.
  Saf periyodik ton fazla adayları ve yoğun girdide 64 olay kapasitesi açıktır.
- 286–290 ve 460–465 kare/s kayıtları tarihsel sürümlere aittir; silinmez.
  Eski kanıtların güncel kaynakla doğrulanamaması başarıya çevrilmez.
  Güncel doğrulayıcı: `python scripts/verify_st06_parallel_product.py`.
  Tarihsel kaynaklar ilgili kanıt arşivinden doğrulanır.
- Depoda proje özelinde SKILL.md yoktur. Diğer projelerin kişisel becerileri
  değiştirilmez. Güncel ayrıntılar SIGNAL_DETECTION_STATUS.md içindedir.
- Bu aktarım işleminde kullanıcı kayıt/commit/push ve master-yedek arayüz
  değişikliklerini master ile birleştirmeyi açıkça istedi. Bu işlemden sonraki
  commit/tag/push için bu talep sürekli yetki sayılmaz.
