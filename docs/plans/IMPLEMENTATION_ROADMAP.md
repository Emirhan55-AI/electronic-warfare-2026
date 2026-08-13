# Uygulama Yol Haritası

Fazlar sıralıdır; bir fazın çıkış kapısı doğrulanmadan ve kullanıcı onayı alınmadan sonraki faza geçilmez.

| Faz | Ad | Çıkış kapısı |
|---|---|---|
| PHASE-00 | Repository ve mühendislik temeli | Repository sözleşmesi, mimari/karar/güvenlik belgeleri, toolchain envanteri ve PHASE-00 doğrulaması başarıyla tamamlanır. |
| PHASE-01 | SigMF giriş sözleşmesi ve deterministik test verisi | Kanonik `ci8` ve çevrimdışı `ci16_le` sözleşmeleri ile sentetik golden fixture zorunlu doğrulamaları geçer; harici veri kontrolü mevcutsa geçer, yoksa kontrollü atlanır. |
| PHASE-02 | Referans spektrum DSP zinciri | Bounded çerçeveleme, Hann, 4096 FFT, güç/PSD ve üstel ortalama floating-point çıktıları deterministik vektörlerle doğrulanır; aynı gerçek sonuçları gösteren kalıcı Türkçe operatör uygulamasının ilk sürümü iki ekran ölçeğinde geçer. |
| PHASE-03 | Sinyal tespiti | OS-CFAR ve komşu hücre birleştirme, etiketli senaryolarda beklenen aday sinyal listesini üretir. |
| PHASE-04 | Parametre çıkarımı | Tespit adaylarının merkez frekansı, bant genişliği ve güç ölçümleri tanımlı kabul toleranslarında referans sonuçlarla eşleşir. |
| PHASE-05 | Sinyal izleme ve analog dinleme | İzinli kayıtlı analog sinyaller izlenir ve seçilen demodülasyon zinciri tekrarlanabilir testlerde doğrulanır. |
| PHASE-06 | FPGA RTL DSP zinciri | Sabit nokta mimarisi ve RTL spektrum/tespit zinciri, referans modelle tanımlı toleranslarda eşleşir. |
| PHASE-07 | PC–ZedBoard veri aktarımı | Kayıtlı I/Q verisi PC'den Ethernet, ZedBoard PS, DDR/AXI DMA ve PL yoluyla bütünlük ve hız kanıtıyla aktarılır. |
| PHASE-08 | HackRF-1 canlı I/Q ve ED entegrasyonu | HackRF-1 canlı RX akışı uçtan uca ED zincirine ulaşır ve kontrollü alma senaryolarında beklenen adayları üretir. |
| PHASE-09 | Genlik tabanlı yön bulma ve yaklaşık konum | Manuel açı/göreli güç ölçümlerinden yön ve iki bilinen ölçüm noktasından yaklaşık konum, bilinen hedeflerle hata raporu üretecek şekilde doğrulanır. |
| PHASE-10 | ET simülasyonu ve kapalı RF test altyapısı | İletimsiz dalga şekli simülasyonları doğrulanır; kablolu, zayıflatıcılı ve RF olarak kapalı test düzeni güvenlik kontrolünden geçmeden RF TX etkinleştirilmez. |
| PHASE-11 | Sürekli ve arabakışlı karıştırma | Sürekli ve arabakışlı dalga şekilleri önce simülasyonda, ardından yalnız onaylı kapalı RF düzeneğinde güç, spektrum ve görev çevrimi ölçümleriyle doğrulanır. |
| PHASE-12 | Analog telsiz ve GPS L1 aldatma | Analog telsiz ve GPS L1 senaryoları önce iletimsiz simülasyonda, ardından yalnız izinli kablolu/zayıflatıcılı kapalı düzende izole test alıcılarıyla doğrulanır. |
| PHASE-13 | Arayüz, sistem entegrasyonu ve yarışma demosu | PHASE-02'de başlatılan kalıcı operatör uygulamasında ED görev akışı ve yalnız izin verilen ET gösterimleri uçtan uca çalışır; demo provası, güvenlik kontrol listesi ve kanıt paketi tamamlanır. |

## ET güvenlik kapıları

ET geliştirmesi önce iletimsiz simülasyon ve dalga şekli doğrulamasıyla başlar; ardından kablolu, zayıflatıcılı ve RF olarak kapalı test düzenine geçer. Güvenli test düzeneği kurulup doğrulanmadan RF TX etkinleştirilmez. Açık ortam RF testi yalnız yürürlükteki mevzuat, yarışma komitesi izni ve komitenin belirlediği zaman ile test düzeni altında yapılabilir.

KTR yarışma görevlerinin kaynağı olarak korunur; eski donanımın teknik performans hedefleri bağlayıcı değildir. Referans mimari 2× HackRF One, ZedBoard ve laptoptur.

**Mevcut faz: PHASE-02**
