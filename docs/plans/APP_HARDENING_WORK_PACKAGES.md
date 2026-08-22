# Operatör Uygulaması Sağlamlaştırma İş Paketleri

## Amaç ve sınır

Bu plan, mevcut yol haritasındaki faz sırasını değiştirmeden operatör uygulamasını
ve repository yerleşimini sağlamlaştırır. Çalışma PHASE-04, PHASE-06 veya sonraki
donanım fazlarını ilerletmez; doğrulanmış algoritma davranışını ya da dondurulmuş
RTL sözleşmelerini değiştirmez.

Hedef bir video, eğitim demosu veya geçici prototip değildir. Hedef; gerçek veri
kaynaklarıyla çalışan, paketlenebilir, kurulabilir ve yayın adayı kalitesinde
profesyonel bir operatör sistemidir. Uygulanmamış özellikler, gelecek için ayrılmış
kontroller ve yalnız gösterim amacı taşıyan yüzeyler yayın uygulamasında bulunmaz.

Her iş paketi ayrı kullanıcı onayına tabidir. Bir paketin çıkış kapısı geçmeden ve
kullanıcı açıkça onay vermeden sonraki paket başlatılmaz.

## İş paketleri

| Paket | Kapsam | Çıkış kapısı |
|---|---|---|
| APP-A | Baseline, code review ve dosya envanteri | Mevcut test durumu, mock/golden/gerçek/generated ayrımı, dosya karar listesi ve hedef mimari belgelenir; kaynak veya veri silinmez. |
| APP-B | Güvenli repository temizliği | Video/demo artıkları ve yalnız gösterim dosyaları kaldırılır; gerekli gerçek kayıtlar manifestli harici mühendislik veri alanına alınır; repository sözleşmesi ve zorunlu regresyonlar geçer. |
| APP-C | Ürün ve doğrulama sınırının ayrılması | Üretim uygulaması mock backend, eğitim sahnesi veya doğrulama fixture'ı ithal etmez; offline laboratuvar araçları ayrı giriş noktasında kalır. |
| APP-D | Dizin ve bağımlılık mimarisi | `app/`, `algorithms/`, `platform/` ve `verification/` sınırları kurulur; döngüsel/ters katman bağımlılıkları kaldırılır; KTR bağları korunur. |
| APP-E | UX, terminoloji ve teknoloji prototipi | Görev akışları ve sözlük dondurulur; Qt Widgets ve Qt Quick/QML prototipleri aynı veride ölçülür; teknoloji kararı tekrarlanabilir kanıtla verilir. |
| APP-F | Yeni operatör uygulamasının uygulanması | Onaylı tasarım gerçek kaynak durumlarıyla çalışır; minimum ekran, ölçekleme, performans, erişilebilirlik ve dürüst özellik kapıları geçer. |

## Değişmez kurallar

- Golden fixture, RTL vektörü ve kanıt dosyası yalnız gösterim verisi sayılmaz.
- Üretim paketi test/mock kaynağı içermez.
- Üretim paketi `video_data`, test fixture, render scripti, eğitim sahnesi veya
  geçmiş demo ekran görüntüsü içermez.
- Üretim navigasyonunda yalnız gerçek kullanım akışları ve gerçekten bağlı
  yetenekler bulunur.
- Gerçek HackRF, ZedBoard, GNSS veya TX sonucu çalıştırılmadan gösterilmez.
- Algoritma, RTL ve PS davranışı uygulama yeniden düzenlemesi sırasında değiştirilmez.
- Taşıma işlemleri önce bağımlılık ve hash etkisi belirlenerek yapılır.
- Commit, tag ve push ayrı açık izin olmadan yapılmaz.

## İş paketi durumu

- APP-A 2026-08-22 tarihinde tamamlandı. İnceleme, sınıflandırma, baseline ve
  hedef mimari kayıtları oluşturuldu.
- APP-B 2026-08-23 tarihinde uygulandı. Video/demo verileri yayın ağacından
  çıkarıldı, tekil SigMF kayıtları ignore edilen yerel mühendislik alanına
  manifest ve SHA-256 ile taşındı, yinelenen byte kopyaları ile artık geliştirme
  dosyaları kaldırıldı ve repository sözleşmesi salt-okunur kapıyla doğrulandı.
- APP-B kapsam regresyonu 48/48 geçti. Tam takımda APP-A baseline'ından kalan beş
  UI/kabul kusuru bulunuyor; temizlikten doğan yeni hata yok. Bu kusurlar ürün ve
  doğrulama ayrımı ile UX uygulama paketlerine aittir. APP-C, APP-B kapı devri
  kullanıcı tarafından açıkça kabul edilmeden başlatılmaz.
- APP-C 2026-08-23 tarihinde kullanıcı onayıyla uygulandı. Ürün giriş noktası
  yalnız SigMF ve gerçek HackRF RX kaynaklarını sunar. Mock backend, sentetik DF,
  harita eğitimi ve offline ET ayrı laboratuvar bileşiminde korunur; ürün deploy
  tanımı bu importları fail-closed olarak dışlar. ADR-0024 ve otomatik runtime
  import/paket/UI sınır testleri kararın kanıtıdır.
- APP-C çıkış regresyonu 438 passed, 1 kontrollü skip ve 0 failure sonucuyla
  tamamlandı. Skip, yalnız yapılandırılmamış haricî gerçek veri setine aittir;
  ürün paket sınırı veya zorunlu çalışma zamanı kapısı değildir.

Kullanıcının ürünleşme açıklamasıyla video/demo dönemi kapanmış, hedef yayın adayı
profesyonel sistem olarak kesinleştirilmiştir.
