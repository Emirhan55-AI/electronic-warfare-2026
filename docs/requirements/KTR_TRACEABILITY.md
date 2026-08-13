# KTR Gereksinim İzlenebilirliği

Bu matris yarışma görevlerini ve genel algoritma sırasını gerçek referans donanıma eşler. KTR teknik parametrelerin veya sayısal performans hedeflerinin bağlayıcı kaynağı değildir. Hiçbir satır tamamlanmış bir DSP/RF yeteneği iddiası değildir.

| Gereksinim kimliği | KTR bölümü | Beklenen işlev | Yeni donanımla uygulanma yöntemi | Planlanan faz | Doğrulama yöntemi | Durum |
|---|---|---|---|---|---|---|
| KTR-4.1 | 4.1 Sinyal Tespiti | Aday RF sinyallerini tespit etme | HackRF uyumlu `ci8` giriş/değişim sözleşmesi; metadata-temelli örnekleme hızı; doğrulanmış PHASE-02 Hann/4096 FFT/güç/PSD golden modeli; sonraki OS-CFAR ve hücre birleştirme | PHASE-01–09 | SigMF sözleşmesi, PHASE-02 referans spektrum kanıtı, sonraki tespit/RTL karşılaştırması ve kayıtlı/canlı veri testleri | Planlandı |
| KTR-4.2 | 4.2 Parametre Çıkarımı | Tespit edilen sinyal parametrelerini çıkarma | HackRF-1 verisi ve doğrulanmış tespit adayları üzerinde sonraki faz işleme | Sonraki fazlar | Etiketli kayıtlar ve kontrollü sinyal testleri | Uygulanmadı |
| KTR-4.3 | 4.3 Sinyal İzleme/Dinleme | Analog amatör telsiz sinyalini izleme/dinleme | HackRF-1 RX ve laptop tarafında ileride geliştirilecek güvenli alıcı zinciri | Sonraki fazlar | Kayıtlı ve izinli canlı alma senaryoları | Uygulanmadı |
| KTR-4.4 | 4.4 Yön Bulma | Sinyal geliş yönünü yaklaşık belirleme | Yönlü antenin manuel çevrilmesi, manuel açı girişi ve açı başına göreli güç/PSD | Sonraki fazlar | Bilinen verici yönleriyle kontrollü saha ölçümü | Uygulanmadı |
| KTR-4.5 | 4.5 Konum Belirleme | Yaklaşık verici konumu çıkarma | Bilinen iki ölçüm noktasından manuel LOB doğrularını birleştirme | Sonraki fazlar | Bilinen konumlu kontrollü hedeflerle hata analizi | Uygulanmadı |
| KTR-5.1 | 5.1 Sürekli Karıştırma | Kontrollü sürekli ET deneyi | HackRF-2 ile yalnız izinli, ekranlı veya iletim hattına bağlı güvenli düzende düşük güçlü test | Sonraki fazlar | RF güvenlik onayı ve kontrollü düzen ölçümü | Uygulanmadı |
| KTR-5.2 | 5.2 Arabakışlı Karıştırma | Kontrollü aralıklı ET deneyi | HackRF-2 ile yalnız izinli ve kontrollü test düzeninde zamanlanmış kaynak | Sonraki fazlar | RF güvenlik onayı, görev çevrimi ve spektrum ölçümü | Uygulanmadı |
| KTR-5.3 | 5.3 Analog Telsiz Aldatma | Kontrollü analog aldatma deneyi | HackRF-2 ile yalnız kapalı/izinli test ortamında laboratuvar kaynağı | Sonraki fazlar | İzole test alıcısı ve kayıtlı sonuç karşılaştırması | Uygulanmadı |
| KTR-5.4 | 5.4 GNSS Aldatma | Kontrollü GNSS aldatma deneyi | Yalnız yasal izinli, RF yalıtımlı veya kablolu laboratuvar düzeninde ileride değerlendirme | Sonraki fazlar | Güvenlik incelemesi ve yalıtılmış alıcı testi | Uygulanmadı |
| KTR-6 | 6 Simülasyon ve Test | Modelleri ve donanım uygulamasını doğrulama | Deterministik veri, PHASE-02 floating-point spektrum modeli ve aşamalı yazılım/RTL/donanım kanıtları | PHASE-00 ve devamı | Otomatik golden ölçümler, UI render/performance testleri, sonraki karşılaştırmalı RTL ve donanım sonuçları | Planlandı |
