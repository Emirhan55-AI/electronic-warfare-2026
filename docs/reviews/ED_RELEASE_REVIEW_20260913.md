# ED sürüm incelemesi — 13 Eylül 2026

## Karar ve kapsam

Ürün yalnız Elektronik Destek kapsamındadır. ADR-0044 geçerlidir; yeni faz,
ET/TX işlevi veya donanım kabulü açılmamıştır. Bu incelemede kaynak kararlılığı
ve paketleme düzeltildi. **Yarışma/saha kabulü tamamlandı kararı verilmez.**
Güncel imajla sürekli GUI+RX, kör RF doğruluğu, parametre doğruluğu, yön RMS ve
paketlenmiş uygulamanın yeniden derlenerek denenmesi hâlâ ayrı kabul işleridir.

Başlangıç çalışma ağacı temizdi. Envanter 1.657 izlenen dosya, 641 Python
dosyası, 51 C, 22 başlık, 2 C++, 71 SystemVerilog, 4 Verilog, 16 QML ve bir
GNU Radio akışı içeriyordu. Tüm izlenen yollar sınıflandırıldı; Python AST
sözdizimi/import envanteri hatasız çıktı. Ayrıntılı inceleme etkin ürün
girişlerine, RX/taşıma/DSP sınırlarına, yaşam döngüsüne, kalıcı kayda ve
paketlemeye odaklandı. Bu, her tarihsel algoritmanın her yürütüm dalının veya
üçüncü taraf harita kütüphanelerinin doğrulandığı anlamına gelmez.

## Gerçek mimari

```text
RF → HackRF One (birincil seri, 8 MS/s kompleks CI8)
   → hackrf_transfer RX süreci / Windows ikili boru
   → PC durumlu NCO + 193 tap FIR + 4:1 örnek azaltma
   → 2 MS/s CI8 / P0IQ TCP → ZedBoard ağ köprüsü
   → ARM CPU0 DMA → PL Hann → FFT → güç → OS-CFAR
   → ARM CPU0 güç çözme → CPU1 dar/geniş aday ve temporal olay
   → P0IQ yanıtı → PC doğrulama → Qt Quick/QML
```

- Ürün girişleri `baz_operator_console.py` ve `python -m app.operator_console`;
  ikisi de `quick_application.py` üzerinden `OperatorViewModel` ve `Main.qml`
  bileşimini açar. HTTP API/backend sunucusu bulunmaz; QML, QObject
  özelliklerini ve slotlarını kullanır.
- PC alım ve kanal seçici işçileri sınırlı kuyruklarla ayrılır. Tek QThreadPool
  ürün işçisi taşıma oturumunu yönetir. Spektrum önizleme işçisi görüntü için
  son veriyi alır; GUI çizimi bilimsel verinin sahibi değildir. Nesil kimliği
  eski oturum geri çağrılarını reddeder.
- P0CQ desteği olan kartta otomatik parametre: confirmed olay → tek bağlamda
  dört kare → PL güç + ARM kestirimi → SQLite katalog → QML. Bu yol 512 hücreyle
  sınırlıdır. Ayrı P0PM-v2 operatör ölçümü 8–3984 hücreyi işler. Bunlar
  birbirinin yerine geçen aynı kapasitede yollar değildir.
- Ölçüm kaydı aynı dört kareyi, kart yanıtını, CRC ve kaynak bağını saklar.
  Analog/Sayısal ayrımı bu dört kare üzerinde PC'de `digital_analog_detection`
  ile deneysel olarak çalışır. %90 güven kapısı fiziksel RF kabulü değildir.
- Dinleme seçili gerçek I/Q'da PC AM/NFM demodülasyonu ve 48 kHz ses üretir.
  Yön ölçümü açı başına PL/ARM kanal gücü, tur sonunda ARM genlik yöntemi kullanır.
- Kayıtlı SigMF yolu PC referans işleme yoludur. Kart erişim hatasında canlı
  kart ölçümü yerine sessizce bu yol kullanılmaz.
- İkinci HackRF yalnız envanter rolüdür; eşzamanlı ikinci RX ve zaman hizası
  uygulandı/doğrulandı sayılmaz. GNU Radio ürünün zorunlu bir aşaması değildir.

## Bulgular ve düzeltmeler

| Kimlik / önem | Tetikleyici ve kök neden | Sonuç |
|---|---|---|
| ED-R01 / P1 | `_LiveMailbox`, GUI henüz tüketmeden sonraki görüntüyü alınca önceki `automatic_parameter_outcomes` alanını da eziyordu. | Ayrı `_LiveSnapshotMailbox` en son görüntüyü tutarken sonuçları biriktirir. 1.024 bekleyen sonuç sınırında açık hata vererek alımı durdurur; sessiz düşürme yoktur. Yavaş GUI, boş sonraki kare, tekrar başlatılan oturum ve SQLite kayıt bağı sınandı. |
| ED-R02 / P1 | `sqlite3.Connection` işlem bağlamı bağlantıyı kapatmaz; katalog her okuma/yazma/dışa aktarmada bağlantı açıyordu. | `_connect` başarı ve hatada işlemi tamamlayıp `finally` ile bağlantıyı kapatır. Geri alma ve kapalı bağlantı testleri eklendi. |
| ED-R03 / P1 | Geçerli JSON içindeki `profiles: null`/sayı vb. değerleri doğrulamadan önce dolaşmak başlangıçta `TypeError` üretiyordu. Python'da `True == 1.0` olması ve çakışan profillerde ilk kaydın seçilmesi yanlış kalibrasyona da izin verebiliyordu. | Konteyner ve sayısal tipler önce doğrulanır; boş profil kimliği, taşan sayılar ve aynı bağlama birden fazla eşleşme reddedilir. Bozuk/eksik/belirsiz kalibrasyondan dBm türetilmez. |
| ED-R04 / P1 | Bozuk SQLite dosyası ürün başlangıcını kesiyor; yenileme ve CSV eylemleri bazı SQLite hatalarını yakalamıyordu. | ED arayüzü açılır, katalog kullanılamıyor durumu görünür, bozuk dosya korunur. Okuma/dışa aktarma hataları Türkçe kayda geçer. Otomatik veritabanı sıfırlama veya veri silme yapılmaz. |
| ED-R05 / P1 | Ürün `scipy` içe aktarırken ana kurulum dosyası bunu içermiyordu; dağıtımda modelin ve ölçüm/tarama kaynaklarının `.py/.c/.h` baytları yoktu. Kaynak özetini okuyan kod başlangıçta veya ilk kayıtta başarısız olabilirdi. | `requirements/product.txt` mevcut sabit bağımlılıklara SciPy 1.16.0 ekler. Manifest ve deploy tanımı kalibrasyon dosyası, sınıflandırıcı kökü ve 51 kaynak/kanıt varlığını taşır. Dondurulmuş F5 kaynak hash kapıları gevşetilmez. |
| ED-R06 / P2 | Eski QWidget alıcı testi birincil seri yerine artık ikincil olan sabit cihaz serisini bekliyordu. | Test, yapılandırmanın birincil seri değerinin arayüzde korunduğunu denetler; gerçek cihaz gerektirmez. |
| ED-R07 / P2 | Önizleme testi eski üç alanlı demeti bekliyordu; güncel kod tespit/görüntü spektrumunu ayrı dört alanla taşıyor. Vivado testinin alt süreci Windows kod sayfasıyla çıktı veriyordu. | Önizleme testi iki spektrumu denetler. Alt süreç UTF-8 çalışır; gizlenen gerçek Vivado kaynak/kanıt uyuşmazlığı artık açıkça raporlanır. Donanım kapısı başarılıya çevrilmez. |

Paket tanımında tutulan kaynak dosyaları çalışma zamanı kaynak kimliği
denetimlerinin girdisidir. Derlenmiş kodun çalıştırılabilir kimliği veya
karttaki hizmetin kimliği yerine kullanılamaz. Yeni standalone ikili bu
incelemede üretilmedi; eski paketlerin güncel ED kaynağını içerdiği varsayılmaz.

## ED dışı ve eski dosyaların kullanım zinciri

| Yüzey | Kullanım zinciri / karar |
|---|---|
| ET/TX/jammer | Etkin kaynak, konfigürasyon, GUI ve paket köklerinde RF yayın arka ucu bulunmadı. Önceki kaldırma korunur. KTR-5.1–5.4 ve tarihli ET belgeleri izlenebilirlik kaydıdır. |
| `tx_off_reference` / `tx_on_comparison` | `quick_scan_actions` → `SurveyController` → RX karşılaştırma ve kayıt. Bunlar harici vericinin operatörce bildirilen durumudur; vericiyi açan komut değildir. ED negatif/pozitif karşılaştırması için korunur. |
| `hackrf_inspector.grc` | SDR RX → spektrum ve ZMQ; bağımsız `feature_extractor_v1.main` abonedir. TX sink bulunmaz. Ürün başlangıcına bağlı değildir; ayrı RX tanı aracı olarak korunur. |
| `feature_extractor_v1.py` | `integration.py` → `extract_features`/`normalize_iq`; kendi ana fonksiyonu → ZMQ dinleyici. `wideband_detect` ve `channelize` bağımsız tanıda çağrılır; ölü kod sayılmaz. |
| `train_classifier.py` | Çevrimdışı sentetik model eğitimi; `classifier_model.py` çalışma zamanı ağırlıklarıdır. Eğitim modülü ürün başlangıcına alınmaz. |
| QWidget / `application.py`, `controller.py`, `_mixin_*` | `build_application` ve tarihsel Qt regresyonları kullanır; ürün girişi `quick_application` bunları yüklemez. Test bağları bulunduğundan silinmedi. |
| `laboratory.py`, `mock.py`, fixture üreticileri | Deterministik RX/DSP ve regresyon testi bağı var; ürün paketinin çalışma zamanı dışında kalır. |
| Eski FPGA `phase06*`, P0 ve F1–F5 modelleri | Testbench, IP sarmalayıcı, alt modül, referans veya donmuş yöntem bağı var. Sadece eski isim taşıdığı için silinmedi. |
| Harita varlıkları / `pyqtgraph` | QWidget harita regresyonları ve ürün `spectral_display.arrayToQPolygonF` bağı var. `pyqtgraph` gereksiz bağımlılık değildir. |
| `pyzmq`, `scikit-learn` | İlki bağımsız GNU Radio/ZMQ RX tanısı, ikincisi eğitim içindir. Temel ürün kurulumu bunları gerektirmez; ilgili dizin bağımlılık listesi korunur. |

Bu incelemede bağımlılığı kanıtlanmamış dosya silinmedi. Yeni ürün özellikleri,
geniş mimari yeniden yazımı veya sayısal algoritma değişikliği yapılmadı.

## Sinyal zinciri ve birim denetimi

| Sınır | Kaynakta denetlenen sözleşme |
|---|---|
| I/Q | İşaretli CI8, I ve Q ayrı `/128` normalizasyonu; kompleks örnek başına 2 bayt. Kırpılan giriş/çıkış canlı koşuyu reddeder. |
| Örnekleme | Varsayılan 16.384 giriş örneği → 4.096 çıkış; 8 MS/s → 2 MS/s. NCO/FIR durumu kareler arasında korunur. Dinamik FFT'de giriş de dört katına büyür. |
| Frekans | Kaydırılmış 4096 olay ızgarasında `f = merkez + (bin − 2048) × 2.000.000 / 4096`. Kartın büyük FFT'si ARM'da olay ızgarasına indirgenir; ham FFT boyu ile olay ızgarası karıştırılmaz. |
| Görüntü | Ton/bin gücü `10 log10(|FFT|²/(N·CG)²)`; PSD ayrı `|FFT|²/(Fs·Σw²)` ve dBFS/Hz. Görüntü FFT'si tespit FFT'si değildir. |
| Kanal gücü | ARM gürültü çıkarılmış PSD'yi bin aralığıyla bütünleştirir. dBFS mutlak RF dBm değildir. Ölçülmüş ve bağlamı eşleşen kalibrasyon olmadan dBm yoktur. |
| Bant genişliği | ARM OBW %99 onaylanan analiz aralığına koşulludur; olayın kaba hücre genişliği hassas OBW kabulü sayılmaz. |
| Sınıflandırma | PC, dört 4096 örnekli 2 MS/s çerçeveyi kullanır; sonlu değer/SNR/güven kapıları vardır. Sentetik genelleme sınırı korunur. |
| Taşıma | Uzunluk, CRC, sıra, çerçeve, DMA ve aday düşümü kapıları vardır. P0CQ desteği yoksa normal P0IQ sürer; yeni parametre isteği gönderilmez. |

Taşıyıcı, emisyon merkezi, OBW, dBFS ve SNR için mevcut geniş C/Python
karşılaştırması yeniden çalıştırıldı: **49/49 geçti**. Bu saf yazılım sayısal
eşdeğerliktir; yeni FPGA yerleştirme/zamanlama, fiziksel RF veya ARM hız ölçümü
değildir. DSP veya RTL değiştirilmedi.

## Doğrulama ve açık kabul işleri

Komutlar ve son sonuçlar bu bölümde aşağıda kaydedilir. Yerel ayrıntılı
çıktılar `build/ed-review-*.log`, `build/ed-review-inventory.json` ve
`build/ed-review-parameter-runtime.json` altındadır; eski `results/evidence`
ölçümleri yeniden yazılmadı.

| Çalıştırma | Gözlenen sonuç / sınır |
|---|---|
| Python AST envanteri | 641 izlenen Python dosyasında sözdizimi hatası yok. |
| `pytest tests` ilk geniş deneme, 20 hata sınırı | 670 geçti, 20 başarısız, 1 atlandı; 434,52 saniye. P0 alt dizini de bu koşuya dahildir. Koşu sürerken değişiklik yapıldığı için temiz bir öncesi/sonrası karşılaştırması değildir. |
| `pytest tests --ignore=tests/p0` geniş koşu | 1.002 geçti, 22 başarısız, 1 atlandı; 582,38 saniye. Bu koşu da son düzeltmelerden önce başladı; sonraki hedefli sonuçlarla birlikte okunmalıdır. |
| Son katalog + görünüm modeli + ürün sınırı + mimari + depo testleri | 110/110 geçti; `build/ed-review-changes.xml`. |
| Eski QWidget alıcı modülü, ayrı süreç | 7/7 geçti. |
| Önizleme + katalog + depo + Vivado tekrar grubu | 40 geçti, 1 başarısız. Tek ret eski Vivado kanıtının güncel kaynak/çıktıyla uyuşmamasıdır; UTF-8 okuma hatası giderildi. |
| `verify_p0_parameter_runtime.py --extended --wide` | 49/49 C/Python durum ve sayısal karşılaştırması geçti. |
| `requirements/product.txt`, yeni sanal ortam | Temiz kurulum ve `pip check` geçti. NumPy 2.2.6, SciPy 1.16.0, PySide6 6.10.2, pyqtgraph 0.14.0, pywin32 311. |
| Temiz ortam başlangıcı/ölçüm bağı | Offscreen başlangıç çıkış kodu 0; 37 ölçüm kaynak kimliği doğrulandı, `native-cpp` kanal seçici yüklendi. RF alımı yapılmadı. |
| Kalan kök test kapılarının son tekrarı | 19/19 yeniden başarısız; adları ve iletileri doğrulama kaydında. İlk geniş koşuda P0 alt dizininde ayrıca 13 başarısız kapı vardı. Bunlar bu bakımla kapatılmış sayılmaz. |
| Son depo sözleşmesi | `python -X utf8 scripts/verify_phase00.py --check` ve `git diff --check` geçti. |

Ortak Python ortamındaki `pip check`, bu projede kullanılmayan boxmot,
FastAPI, googletrans ve transformers gibi paketlerde uyuşmazlık bildirdi.
Bu paketler değiştirilmedi; ED bağımlılıkları ayrı temiz ortamda doğrulandı.

Geniş koşudaki hataların tümü kapatılmadı. Eski F2–F5 protokol kaynak
özetleri, P0/PL/ARM/RX ölçüm kaynak listeleri, eski ürün sunum sözleşmesi,
PHASE-06I/J kanıtları ve ST-06 tarihsel arşiv kaynak bağları açık kalır.
Özellikle `verify_st06_parallel_product --historical` ve ürün optimizasyonu
arşivlerindeki beklenen kaynak baytlarının bulunamaması, tarihsel bütünlüğün de
tam doğrulanamadığını gösterir; yalnız güncel kaynak farkı olarak geçiştirilmez.
Yeni sonuç kaydı her başarısız testin adını ve hata iletisini korur:
[ED inceleme doğrulama kaydı](../../results/evidence/phase08/ed-release-review-20260913.json).

- Kaynak başlangıcı: `python -m app.operator_console --smoke-test --no-intro`
  (`QT_QPA_PLATFORM=offscreen`). Bu fiziksel GPU, RF veya yeni standalone testi
  değildir.
- Katalog/Qt ürün regresyonları aynı süreçte QApplication/QGuiApplication
  türlerini karıştırmadan çalıştırılır. Eski QWidget modülü ayrı süreçte
  sınanır; aksi sıra Qt test altyapısında `setStyle` hatası üretebilir.
- Tarihsel kanıt hash uyuşmazlıkları, imza tarihini/hash'i güncelleyerek veya
  başarısız testi atlayarak kabul edilmiş sayılmaz. Güncel kaynak kapısı ile
  tarihsel arşiv bütünlüğü ayrı doğrulanmalıdır.
- Fiziksel kabul için eşleşen kart imajı/hizmet, tekrar eden gerçek GUI+RX,
  kesinti/iptal/yeniden bağlanma ve bağımsız açık/kapalı/kör RF gerekir.
- Eşzamanlı ikinci alım, dBm kalibrasyonu, gerçek konuşma, genel Pd/Pfa ve yön
  doğruluğu bu incelemenin testleriyle kapanmaz.
- `quick_view_model.shutdown` iki saniyelik işçi bekleme sonucunu kullanmadan
  kaynak kapatıyor. Normal kapanış regresyonları geçse de uzun/bloke işte
  kaynak ömrü riski ayrıca incelenmelidir; burada donanımsız bir arıza
  yeniden üretimi veya davranış değişikliği yapılmadı.
- Katalog yazımları GUI slotunda senkron kalır. Uzun disk kilidi/yavaş depolama
  altında ekran gecikmesi ölçülmedi; kuyruk düzeltmesi sürekli performans
  kabulü değildir.

KTR bağı: ED-R01/02/04, KTR-4.1 ve KTR-4.2 kayıt bütünlüğü; ED-R03/05,
KTR-4.2 ölçüm/kalibrasyon izlenebilirliği; ED-R05/06, KTR-4.1–4.4 ürün
başlangıcı ve yapılandırma sınırları. KTR-5.1–5.4 kapsam dışı kalır.
