# KTR Gereksinim İzlenebilirliği

Bu matris yarışma görevlerini ve genel algoritma sırasını gerçek referans donanıma eşler. KTR teknik parametrelerin veya sayısal performans hedeflerinin bağlayıcı kaynağı değildir. Hiçbir satır tamamlanmış bir DSP/RF yeteneği iddiası değildir.

| Gereksinim kimliği | KTR bölümü | Beklenen işlev | Yeni donanımla uygulanma yöntemi | Planlanan faz | Doğrulama yöntemi | Durum |
|---|---|---|---|---|---|---|
| KTR-4.1 | 4.1 Sinyal Tespiti | Aday RF sinyallerini tespit etme | KTR yöntemi OS-CFAR/local adaptive; sayısal değerler ayrı `P0_OS_CFAR_EXPONENTIAL_PFA_1E4` mühendislik profilidir: 16 algorithms/yan, 4 guard/yan, rank 24/32, Pfa `1e-4`, türetilmiş alpha `8.58014304069906`, strict `>`; PL Hann/FFT/güç ve PS sahibi karar korunur | P0 Mandatory Closure Block A | Sekiz deterministik detector sahnesi; 1.038.336 CUT empirical FAR ve %99 Wilson aralığı; Python↔portable C coefficient/hücre/aday eşdeğerliği; fiziksel FPGA güç→ARM OS-CFAR→ABI v1→2/3 temporal host eşdeğerliği; PHASE-06A–J regresyonu | P0 host profili ve üç byte-tam fiziksel FPGA güç çerçevesinde ARM OS-CFAR ile temporal doğrulama çalıştı; ikinci karede doğrulama ve iki boş kare sonunda expiry geçti, olay JSON'u host C ile byte-tam eşleşti. Sayısal değerler KTR sabiti değildir; geniş ARM vektörleri, kalıcı servis ve canlı HackRF açık |
| KTR-4.2 | 4.2 Parametre Çıkarımı | Tespit edilen sinyal parametrelerini çıkarma | Güç ağırlıklı emisyon merkezi; ayrı taşıyıcı frekansı kestirimi yok; aday ROI içinde yerel gürültüye göre 6 dB threshold kenarları ve kararsızlıkta açık etiketli gürültü-çıkarılmış %98 occupied-power fallback; kaba aday aralığı ayrı; Hann-normalize tepe bin/kanal dBFS, SNR ve açıklanabilir Analog/Sayısal/Belirsiz kategorisi | P0 Mandatory Closure Block A | Tek ton, AM, NFM, OOK burst, dikdörtgen spektrum, bant sınırlı gürültü, iki komşu ve eşik yakını fixture; gerçek 250 Hz/bin çözünürlüğe bağlı hata/tolerans; seçili replay olay kimliği→kare→FFT→P0 sonuç Qt regresyonu | P0 host referansı ve ölçüm UI bağı sabit sahnelerde doğrulandı; PHASE-04 bağımsız alan kabulü, kalibrasyon/dBm, ARM/ZedBoard ve canlı RF açık |
| KTR-4.2-F1 | 4.2 Parametre Çıkarımı | PHASE-04 ürün yeteneğini alan bazlı doğrulama | Emisyon merkez frekansı, ayrı gözlenen taşıyıcı frekansı, OBW99, kalibre edilmemiş kanal gücü/SNR ve sınırlı sinyal alanı; confirmed olay ve operatör onaylı izole span; alan bazlı abstention ve digest bağlı fail-closed profil | F1D/F2D/F3D/F4D tamamlandı ve başarısız; F5A-F5E tamamlandı | F1/F2/F3/F4 tek seferlik sonuçları; F5 protokol/yöntem/runner kilitleri, binding 40/40, OOS 24/24, `f5d-verification.json`, digest bağlı ürün profili ve `f5e-verification.json` | Host ürün entegrasyonu tamamlandı — altı ölçüm alanı ve span dayanıklılığı iki popülasyonda geçti; QML ölçümü dört ardışık gözlem ve operatör onaylı span gerektiriyor; profil/kaynak değişiminde fail-closed. FPGA, canlı RF, dBm kalibrasyonu ve saha kabulü açık |
| KTR-4.1-OPS | 4.1 Yarışma İş Akışı | Bilinmeyen, hakem bandı ve hakem frekansı girişleriyle sinyal varlığını doğrulama | Hz domainli `SearchRequest`; ortak replay/gelecek HackRF acquisition backend; `UNKNOWN`, `JUDGE_BAND`, `JUDGE_FREQUENCY`; frekans verilse de OS-CFAR ve confirmation atlanmaz | P0 Mandatory Closure Block A | Üç pozitif replay demo; band dışı, yanlış frekans, NaN, ters band, zarf dışı ve aşırı-span negatifleri; Qt binding | Üç mod replay/host üzerinde doğrulandı; canlı HackRF scan/tune uygulanmadı |
| KTR-4.1-OPS-B0 | 4.1 Yarışma İş Akışı | Üç arama modunu seri seçili HackRF-1 RX'e hazırlama | RX-only `hackrf_transfer`, ED_RX seri config'i, 8 MS/s ve boşluksuz overlap tuning planı | P0 Block B0 | Toolchain self-test; discovery/ci8/argv/plan/mapping/queue/UI unit testleri | B0 READY — fiziksel cihaz yok, seri ve UNKNOWN aralıkları atanmadı; canlı tune/IQ/detection kanıtı değil |
| KTR-4.3 | 4.3 Sinyal İzleme ve Analog Dinleme | Seçilen analog yayını operatör denetiminde dinleme | PHASE-03 confirmed olay veya operatör ayarlı kanal; açık AM/NFM seçimi; bounded DDC, 129 tap kanal filtresi, 48 kHz resample, AM zarf/NFM faz-fark, 65 tap ses filtresi, mono PCM16/WAV | PHASE-05 ve devamı | Deterministik AM/NFM clean ve 20 dB kapıları; bağımsız periodogram/korelasyon oracle'ı; QML tespit/ofset/BW/süre/dalga biçimi/WAV binding'i; noise-only negatif kontrol | Kısmi — AM/NFM HOST/REPLAY bağımsız doğrulandı ve QML ürün akışına bağlandı; beş saniyeden kısa giriş açıkça kısa önizlemedir; canlı HackRF/audio saha kabulü yok |
| KTR-4.4 | 4.4 Yön Bulma | Sinyal geliş yönünü yaklaşık belirleme | HackRF-1 ve uygun yönlü antenle manuel açı; açı/göreli güç/frekans/zaman/güven kaydı; açık `KUZEY / 0°` veya manuel coğrafi baş referansı ile ham maksimum LOB; yalnız geçerli sensör konumu ve açık referansla gerçek basemap üzerinde geodezik LOB sunumu | P0 Mandatory EH Core | 7 köşe fixture'ı ve estimatorü çağırmayan 15° adımlı üç yönlü anten eğitim sahnesi; bağımsız argmax, dairesel hata, 0/360 wrap, manuel referans dönüşümü, kardinal geodezik endpoint; PC konum başarı/hata ve manuel fallback Qt regresyonu | P0 model/eğitim UI ve PC/manuel konum iş akışı doğrulandı; hedef konumu çıkarımı, fiziksel anten açısı kestirimi, canlı anten/HackRF saha ölçümü ve kalibre doğruluk iddiası yok |
| KTR-4.5 | 4.5 Konum Belirleme | Yaklaşık verici konumu çıkarma | Bilinen iki ölçüm noktasından manuel LOB doğrularını birleştirme | Sonraki fazlar | Bilinen konumlu kontrollü hedeflerle hata analizi | Uygulanmadı |
| KTR-5.1 | 5.1 Sürekli Karıştırma | Kontrollü sürekli ET deneyi | Bilgisayar-2 üzerinde tekli, çoklu, baraj ve süpürmeli deterministik kompleks taban bant; OFFLINE/LOOPBACK; HackRF-2 TX kilitli | P0 Mandatory EH Core + ET-A offline kabulü | Tekli/çoklu spektral yapı, seeded baraj bant içi güç ve flatness, doğrusal süpürme ilerlemesi, iki kuyruklu OBW99, finite/normalizasyon ve güvenlik kilidi | ET-A host offline kapısı geçti; gerçek TX backend'i, RF güç/etki veya kapalı düzen deneyi yok |
| KTR-5.2 | 5.2 Arabakışlı Karıştırma | Kontrollü aralıklı ET deneyi | Deterministik yerel analiz girişi üzerinde birbirini dışlayan `DİNLE → GECİKME → GÖREV → KORUMA` pencereleri; enerji eşiği, ardışık onay, histerezis, sınır kontrollü offline görev tamponu ve örnek-seviyesi çıkış maskesi; TX kilitli | ET-B offline zamanlama kabulü; RF kabulü sonraki kontrollü faz | Hedef yok/sürekli/kesintili/eşik-köşe girişleri; dinleme/görev dışlama, gecikme ve koruma sırası, görev çevrimi, maske dışı sıfır, tepe sınırı, görev frekansı ve güvenlik kilidi | ET-B host offline zamanlama kapısı geçti; gerçek zamanlı deadline/latency ölçümü, HackRF-2, RF görev çevrimi, güç/etki ve kapalı düzen spektrum kabulü uygulanmadı |
| KTR-5.3 | 5.3 Analog Telsiz Aldatma | Kontrollü analog aldatma deneyi | 1 kHz doğrulama sesi normalizasyonu, 3 kHz bant sınırlama, AM/FM/NFM kompleks taban bant ve çıkış normalizasyonu; TX kilitli | P0 Mandatory EH Core + ET-A offline kabulü | AM zarf ve FM/NFM quadrature yerel demodülasyon korelasyonu, bant dışı ses gücü, bounded görev ve güvenlik testi | ET-A test sesi taban bant/loopback kapısı geçti; gerçek ses kaydı, mikrofon, kablolu RF ve HackRF-2 TX uygulanmadı |
| KTR-5.4 | 5.4 GNSS Aldatma | Kontrollü GNSS aldatma deneyi | Yalnız GPS L1 C/A offline metadata: konum, açık UTC, 1–63 PRN kodu ve kaynak sözleşmesi; dalga şekli yok, TX kilitli | ET-A offline kabulü; RF kabulü sonraki kontrollü faz | Geçerli metadata; UTC ofseti, aralık dışı PRN, boş metadata kaynağı ve geçersiz konum/zaman negatifleri; sıfır örnek ve TX yokluğu | Metadata sözleşmesi doğrulandı; GNSS RF dalga şekli, ephemeris/NAV işleme, alıcı testi ve her türlü OTA/kablolu GNSS TX uygulanmadı |
| KTR-6 | 6 Simülasyon ve Test | Modelleri ve donanım uygulamasını doğrulama | Deterministik veri, PHASE-06A–J kanıtları, P0 OS-CFAR/parametre/DF/ET host modelleri ve gerçek PS↔DMA↔PL Vivado blok tasarımı | P0 Mandatory EH Core | Golden ölçümler, C eşdeğerliği, Qt binding/lifecycle, 16-bit DMA length Vivado BD/sentez/route/timing/bitstream/XSA, PetaLinux device-tree/modül/rootfs/boot derlemesi, fiziksel boot/FCLK/DMA ve repository regresyonu | ZedBoard önayarlı native PetaLinux zinciriyle DONE/UART/Linux 3/3 soğuk açılış, 50 MHz FCLK, MM2S/S2MM IOC, sıfır çerçeve ve bilinen çerçeve 10/10 byte-tam geçti; Ethernet/throughput, geniş vektör ve canlı HackRF açık |

## Operatör uygulaması sağlamlaştırma izlenebilirliği

APP-A–F iş paketleri roadmap fazlarını ilerletmez ve algoritma sonucunu değiştirmez.
Amaç, aşağıdaki KTR yüzeylerinde ürün, laboratuvar ve doğrulama sınırlarını açık
tutmaktır.

| Bakım kimliği | Bağlı KTR yüzeyi | Korunan sınır | Doğrulama |
|---|---|---|---|
| APP-A | KTR-4.1-OPS, KTR-4.2, KTR-4.3, KTR-4.4, KTR-5.1–5.4, KTR-6 | Mevcut davranış değiştirilmeden code review, test baseline'ı ve mock/golden/gerçek veri envanteri | `docs/reviews/APP_CODE_REVIEW_BASELINE.md`, `docs/reviews/REPOSITORY_DISPOSITION.md` |
| APP-B | KTR-6 | Golden ve normalized evidence korunarak yalnız onaylı artıkların temizlenmesi | SHA-256 yerel veri manifesti; salt-okunur PHASE-00 repository kapısı; 48/48 kapsam regresyonu geçti; APP-C kapı devri 2026-08-23 tarihinde kullanıcı tarafından onaylandı |
| APP-C | KTR-4.1-OPS, KTR-4.3, KTR-4.4, KTR-5.1–5.4 | Üretim uygulamasının mock/eğitim/offline laboratuvar kaynaklarından ayrılması; canlı olmayan yeteneğin canlı gösterilmemesi | ADR-0024; `config/app/product-package.json`; izole runtime import testi; ürün UI kaynak-doğruluk ve deploy-spec testleri; tam regresyon 438 passed, 1 haricî-veri skip, 0 failure |
| APP-D | KTR-4.1–4.4, KTR-6 | Uygulama, algoritma, platform ve doğrulama katmanlarının taşınırken davranış ve sahiplik koruması | Import sözleşmesi, golden/RTL regresyonu ve KTR yol güncellemesi |
| APP-E | KTR-4.1-OPS, KTR-4.2–4.4 | Görev terminolojisi, bilgi mimarisi ve teknoloji kararının ölçülerek dondurulması | Kullanılabilirlik senaryoları, A/B performans ve ekran ölçeği kanıtı |
| APP-F | KTR-4.1-OPS, KTR-4.2–4.4, izinli KTR-5 yüzeyleri | Yalnız uygulanmış ve doğrulanmış özellikleri sunan görev odaklı operatör uygulaması | ADR-0027; gerçek SigMF uçtan uca işleme; gerçek HackRF araç/cihaz probe durumu; QML ürün import sınırı; 1280×720, 1366×768, 1920×1080 ve %150 render; 10 Hz, heartbeat, bounded çizim, Türkçe metin ve paketleme kapıları |
| ET-C | KTR-5.1–5.4, KTR-6 | Yalnız doğrulanmış çevrimdışı ET modellerinin ana ürün uygulamasında sunulması; RF TX, mock ve doğrulama verilerinin ürün dışında kalması | ED/ET QML alan seçimi; `algorithms.et` ürün import sınırı; sürekli, arabakışlı, analog ve GNSS binding testleri; 1180×680, 1280×720 ve 1440×900 render; TX API yokluğu kapısı |

APP-F arayüz bakımı 2026-08-25 tarihinde işlev değiştirmeden spektrum merkezli
ürün kabuğunu, ED görev göstergesini, ikonlu çalışma alanı seçimini, üç adımlı
sinyal ölçüm sunumunu, polar kerteriz göstergesini, kompakt sistem sağlık
şeridini ve salt-okunur olay konsolunu eklemiştir. Düzenlenemeyen DSP blok
görünümü kaldırılmıştır. Güncel çoklu çözünürlük, %150 ölçek, 10 Hz ve GUI
heartbeat kanıtı `results/evidence/app-f/release-ui-verification.json` altında
korunur; bu bakım algoritma, donanım veya RF doğruluk iddiasını değiştirmez.
İkinci bakım paketi, seçili kaba aday ile operatör analiz aralığını gerçek 4096
FFT hücre koordinatlarından spektrum üzerine taşımış; açılır kaynak paneli ve
ölçümle tetiklenen kerteriz geçişini `Hareketi azalt` ayarına bağlamıştır. Ürün
durum şeridi doğrulanmış çalışma profilindeki `regional` yöntemi literatüre uygun
`Bölgesel Eşik` adıyla gösterir; OS-CFAR çalışıyormuş izlenimi vermez.
Üçüncü bakım paketi tespit listesini kararlı kimlik sırasına ve sabit görev
yüksekliğine taşımış; spektrum ile spektrogramı ortak frekans zoom/pan durumuna
bağlamış ve kayıtlı I/Q için doğrulanmış AM/NFM zincirini seçili tespit bağlamında
QML ürün alanına eklemiştir. Kısa önizleme, kesintisiz kayıt ve canlı HackRF kabulü
ayrı durumlar olarak gösterilir.
Dördüncü bakım paketi ortak frekans imlecini, geri/ileri görünüm geçmişini ve
FFT hücresine bağlı `Shift+sürükle` analiz taslağını eklemiştir. Tespit listesi
sabit tutulurken ölçüm ve dinleme ayarları bağımsız kaydırılır; taslak ayrıca
operatör onayı almadan parametre ölçümünü etkinleştirmez.
Beşinci bakım paketi Sistem çalışma alanını gerçek çalışma durumuna bağlı yedi
aşamalı işlem zinciri, bileşen yürütme/donanım sınırı denetçisi ve yapılandırılmış
salt-okunur olay günlüğüyle yenilemiştir. Host üzerinde çalışan aşamalar FPGA'de
çalışıyormuş gibi gösterilmez; RTL veya taşınabilir C karşılıkları kart kabulü
olarak sunulmaz. Yayın varsayılanında kaynak konumu açma ve komut yürütme yüzeyi
kapalıdır. Bu bakım algoritma doğruluğu veya donanım kabul iddiasını değiştirmez.
Altıncı bakım paketi Spektrum çalışma alanında tarama komutlarını frekans görünümü
başlığında toplamış; seçili tespit kimliği, frekansı, tepe/gürültü oranı ve
durumunu sabit `Sinyal Görevi` bağlamına taşımıştır. `Tespitler` ve `Ölçüm`
görünümleri operatör seçimiyle aynı sabit panelde değiştirilir; seçim, görev
görünümünü kendiliğinden değiştirmez. Minimum çözünürlükte iki görünüm ayrı ayrı
render ve performans kapısına alınmıştır. Algoritma ve RF doğruluk kapsamı
değişmemiştir.
Yedinci bakım paketi Dinleme çalışma alanında seçili kanal bağlamını, hazırlama
eylemini ve sonuç kontrollerini kaydırılan ayarlardan ayırmıştır. Demodüle ses
dalga biçimi ve salt-okunur zaman çizelgesi gerçek PCM uzunluğu ile ses çıkışının
işlediği süreden beslenir; fiziksel ses çıkışı kullanılabilirliği WAV çıktısından
ayrı gösterilir. Hash-kilitli AM kaydıyla kısa önizleme, dalga biçimi, süre ve
çıktı sınırı ürün doğrulama kapısına alınmıştır. Canlı HackRF veya fiziksel ses
saha kabulü kapsamı değişmemiştir.
Sekizinci bakım paketi Yön Bulma çalışma alanını kaynak kimliği ve anten referansı
kilitli bir saha ölçüm oturumuna taşımıştır. Kaynak değişiminde ölçümler temizlenir;
ilk kayıt anten 0° referansını sabitler ve geçmiş satırları anten açısı, geniş bant
kare gücü, anten azimutu, frekans ve kaynakla bağlar. Üç farklı açıda aynı gerçek
I/Q gücü kullanıldığında maksimum ayrışmadığı için kerteriz üretilmemesi ürün
kapısında doğrulanmıştır. Bu bakım yön bulma algoritmasını, saha doğruluğunu,
çok kanallı DoA, menzil veya hedef konumu kapsamını değiştirmez.
Dokuzuncu bakım paketi dört çalışma alanının ortak ürün kabulünü tamamlamıştır.
Spektruma özgü tarama, kaynak paneli ve görünüm kısayolları yalnız ilgili çalışma
alanında etkinleşir; çalışma alanı geçişi klavye odağını seçili gezinme öğesine
taşır. Durum rozetleri erişilebilir açıklama kazanmış, geniş ekran Sistem metin
ölçeği yoğun minimum ekranı etkilemeden yükseltilmiş ve boş günlük filtresi açık
durum metniyle kapatılmıştır. Beş gerçek QML görünümü ve bağlama duyarlı kullanım
kuralları tek doğrulayıcıda 21 kabul kapısına bağlanmıştır. ET-C ile üç ET görünümü,
güvenlik, operatör dili, boş kaynak durumu ve azaltılabilir hareket kapıları
eklenerek güncel toplam 28 olmuştur. Bu bakım algoritma,
donanım, RF doğruluğu veya yeni görev yeteneği iddiası eklemez.

ET-C bakım paketi, doğrulanmış KTR-5.1–5.4 host modellerini ana QML ürün
yüzeyindeki ayrı ET alanına bağlamıştır. Sürekli ve analog sonuçlar sınırlı zaman
alanı/spektrum dizilerinden, arabakışlı görünüm gerçek pencere durumlarından,
GPS görünümü ise yalnız metadata doğrulama sonucundan beslenir. Paket manifesti
çevrimdışı ET modellerini dahil ederken mock kaynak, eski QWidget laboratuvarı,
doğrulama veri setleri ve RF yayın yolunu dışarıda tutar. Bu bakım PHASE-10–12
fiziksel kapılarını tamamlamaz.

KTR-6 için kanonik P0 Vivado kaynak yolları depo düzeniyle birlikte
`algorithms/fpga/` altında sabitlenmiştir. Yol düzeltmesinden sonra ZedBoard
`xc7z020clg484-1` hedefi temiz projeden yeniden sentezlenmiş, route ve zamanlama
kapılarını geçmiş, bitstream ile XSA yeniden üretilmiştir. ZedBoard önayarlı XSA'dan
üretilen native PetaLinux paketi fiziksel kartta DONE/UART/Linux, 50 MHz FCLK,
DMA IOC, sıfır çerçeve ve bilinen çerçeve 10/10 byte-tam kabulünü geçmiştir. DONE
ve UART Linux giriş kapısı üç ardışık soğuk açılışta 3/3 tekrarlanmıştır.
Bilinen FPGA güç çıktısı kart üzerindeki ARM OS-CFAR aracında çalıştırılmış ve aday
JSON'u host C çıktısıyla byte-tam eşleşmiştir. Ardından üç ayrı byte-tam FPGA güç
çerçevesi ABI v1 paket köprüsüyle PHASE-06J çekirdeğine verilmiş; 2/3 doğrulama,
iki boş kare expiry ve host/ARM byte-tam olay JSON eşdeğerliği geçmiştir.
Ethernet/throughput, geniş detector vektörü, parametre ARM bağı, kalıcı ayrıcalıklı
kart servisi, canlı HackRF ve RF saha kapıları açık kalır.

Ürünleşme sınırı: video/demo dönemi kapanmıştır. Yayın operatör uygulaması mock,
eğitim, gösterim verisi veya geleceğe ayrılmış bağlı-olmayan kontrol içermez.
Yalnız doğrulanmış çevrimdışı ET modelleri, operatöre tek noktada gösterilen
`YAYIN — DEVRE DIŞI` sınırıyla ürün yüzeyine dahildir. Golden/replay verileri doğrulama paketinde
kalır; gerçek donanım sonucu ancak fiziksel kabul kanıtı varsa yayın yüzeyinde
etkinleştirilir.
