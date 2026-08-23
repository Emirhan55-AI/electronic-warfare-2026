# APP-E UX ve Terminoloji İncelemesi

- İnceleme tarihi: 2026-08-23
- İncelenen giriş noktası: `python -m app.operator_console`
- Ekran boyutu: 1366×768, Qt offscreen render
- Karar kapsamı: terminoloji, görev akışı ve sunum teknolojisi

## Bulgular

| Öncelik | Bulgu | APP-E kararı |
|---|---|---|
| P0 | Parametre, Dinleme ve Konum sağ panellerinin viewport arka planı açık renkte kalıyor; metin kontrastı kayboluyor | Ortak scroll viewport teması koyu yüzeye sabitlendi |
| P0 | Ürün Konum ekranında bağlı olmayan `LIVE GNSS` için rezerve seçenek gösteriliyor | Seçenek kaldırıldı; gerçek entegrasyon olmadan geri gelmeyecek |
| P1 | `Coğrafi Azimut`, `Manuel Baş` ve `Yön çizgisi` aynı referans sistemini açıkça anlatmıyor | Kerteriz, bağıl geliş açısı, anten referans yönü ve LOB sözleşmesi donduruldu |
| P1 | Doğrulama uygulamasında `HOST/SYNTHETIC`, `EĞİTİM` ve `REPLAY` gibi mühendislik içi ifadeler operatör metnine taşıyor | `Yazılım Referans Verisi`, `Doğrulama` ve `Kayıt Oynatma` kullanıldı |
| P1 | `Otomatik öneri` deterministik tespit aralığını belirsiz bir yetenek gibi sunuyor | `Tespit aralığı` olarak değiştirildi |
| P1 | Ana gezinme altı ayrı sayfa gösteriyor; seçili sinyal bağlamı Parametre ve Dinleme sayfalarında parçalanıyor | APP-F bilgi mimarisi üç çalışma alanı ve seçili sinyal görevleri olarak donduruldu |
| P2 | Alt kontrol şeridinde dar alanda metin kesiliyor | APP-F ölçekleme kapısına alındı; yeni QML kabuğunda sabit genişlik yerine uyarlanabilir düzen kullanılacak |
| P2 | Sistem ekranı yalnız anahtar–değer listesi; veri zinciri ve hata kaynağı görünmüyor | Salt okunur blok akışı APP-F kapsamına alındı |
| P2 | Mevcut arayüzde hareket görev bağlamını açıklamıyor | Yalnız durum/geçiş amaçlı 120–180 ms hareket sözleşmesi donduruldu |

## Araç ve içerik izi taraması

Ürün kaynaklarında geliştirme aracına veya otomasyon sürecine ait kullanıcı metni
bulunmadı. Üçüncü taraf harita varlıkları tarama dışında tutuldu; bunlar lisanslı,
minified upstream dağıtımlardır ve uygulama metin kataloğu değildir.

Ürün paketi mock backend, doğrulama fixture'ı, laboratuvar giriş noktası ve gömülü
gösterim verisini dışlamaya devam eder. Doğrulama uygulamasındaki referans veri
fiziksel ölçüm olarak sunulmaz.

## Görsel inceleme sonucu

Mevcut Widgets kabuğu görevleri çalıştırabiliyor ancak büyük `MainWindow`, çoklu
dock/scroll davranışı ve parça parça stil kuralları APP-F için güvenli bir görsel
temel değildir. QML prototipi aynı bilgi yoğunluğunu daha düzenli grid, durum
akışı ve tek tip panel hiyerarşisiyle kurabildi. Bu sonuç yalnız tasarım ve sunum
katmanı içindir; algoritma davranışını değiştirmez.

## Kapanış

APP-E içinde mevcut ürünün yanlış veya yapay duran metinleri ile kritik kontrast
kusuru giderildi. Yeni kabuğun, uyarlanabilir yerleşimin, erişilebilirlik
ayarlarının ve gerçek ViewModel bağlantılarının uygulanması APP-F onay kapısında
bekler.
