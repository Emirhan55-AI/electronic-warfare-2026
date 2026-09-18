# Parametre çıkarımı ve Analog/Sayısal sınıflandırma incelemesi

16 Eylül 2026 · KTR-4.2 / KTR-4.2-F1 · PHASE-08/ST-06 mevcut kapsamı.

Mevcut ölçüm yöntemi ve sinyal türü modeli geliştirme gerektiriyor. Taşıyıcı
çizgisinin gözlenmemesi tek başına arıza değildir; bant genişliğinin sık
elenmesini yalnız arayüz değişikliği çözmez. İnceleme ürün kodunu, eşikleri,
kart imajını veya faz kabul durumunu değiştirmedi.

## Ekrandaki ölçümün eşleştirilmesi

Yerel `parameter-records` arşivindeki
`a2f955bbea2f40dd87360498e91e0b4f.zip`, 16 Eylül 17:58:29 Türkiye saati ve
−29,60507484 dBFS sonucu ile ekran görüntüsünü eşleştiriyor. Özgün I/Q ve
dört kare SHA-256 özetleri doğrulandı. Karşılaştırılan önceki kayıt
`15c7774e15594edb8bae9e73429b43e5.zip`, aynı gün 17:50:40'a ait.

| Alan | Önceki 820 MHz kaydı | Ekrandaki kayıt |
|---|---:|---:|
| Emisyon merkezi | 819,992725 MHz | 819,941255 MHz |
| Gözlenen taşıyıcı çizgisi | Gözlenmedi | Gözlenmedi |
| OBW | 821,689 kHz, geçerli | Zamansal kararsızlık nedeniyle belirsiz |
| Kanal gücü | −29,5475 dBFS | −29,6051 dBFS |
| OBW kenar kararsızlığı | 3,686 hücre | 15,826 hücre |
| Sınıflandırıcı | Sayısal, 0,97784 model skoru | Sayısal, 0,98666 model skoru |

Bu iki kayıt aynı fiziksel vericinin kimliğini veya gerçek modülasyonunu
kanıtlamaz. “Geçerli” alanın hesaplama kapısını geçtiğini ifade eder;
kalibre RF doğruluğu anlamına gelmez.

## Taşıyıcı alanı

Kart kodu ayrı, belirgin bir çizgi arar: SNR, ortalama ve kare başına çizgi
belirginliği, üç hücrenin enerji payı ve artifakt denetimleri vardır.
Ana ekrandaki `Taşıyıcı Frekans` genel sinyal merkez frekansı değildir.
Bastırılmış taşıyıcılı sayısal sinyallerde bu çizginin bulunması beklenmeyebilir.
Ekrandaki sinyalin modülasyonu bağımsız olarak bilinmediğinden kesin olarak
“taşıyıcısı yok” denilemez; mevcut yöntemin çizgi kapısını geçmemiştir.

Emisyon merkezi aynı sonuçta zaten hesaplanmıştır ve teknik ayrıntıdadır.
Kullanıcının sinyali hangi frekansta aldığını görmesi için ayrı bir ana
`Sinyal merkez frekansı` alanı uygun olur. Bu değer taşıyıcı yerine geçirilmemeli;
komşu enerji, analiz aralığı ve asimetrik spektrumdan etkilenebileceği korunmalıdır.

Kaynak: `platforms/embedded/p0/src/p0_parameter_runtime.c:581`,
`app/operator_console/qml/ParameterMeasurementPanel.qml:15`.

## Bant genişliğinin elenmesi

Ürün 2 MS/s hızında 4 × 4096 örnek kullanıyor: toplam 8,192 ms. Frekans
hücresi 488,28125 Hz. Dört karenin ortalama spektrumundan hesaplanan bant
kenarları, her seferinde bir kare çıkarılarak elde edilen sonuçlarla
karşılaştırılıyor. Bu farkların medyanına dayanan tanı 7 hücreyi
(3,418 kHz) aşarsa OBW reddediliyor. Ekrandaki 15,826 hücre bu sınırın üstünde.
Bu tanı gerçek bant kenarının fiziksel olarak ne kadar hareket ettiğinin
doğrudan ölçümü değildir; kestirimin kısa pencereye duyarlılığını da içerir.

Güncel C çekirdeği bilgisayarda derlenip değişmemiş iki I/Q kaydı işlendi.
Kartın kaydettiği alan durumları yeniden elde edildi. Ekrandaki kayıtta
sayısal tanı 15,838 hücre oldu; yazılım FFT'si ile fiziksel PL FFT'si birebir
aynı olmadığı için bu tekrar bit düzeyinde fiziksel eşitlik iddiası değildir.

| Her iki yana eklenen aralık | Önceki kayıtta kenar tanısı | Ekrandaki kayıtta kenar tanısı |
|---|---:|---:|
| 0 hücre | 3,661 — geçerli | 15,838 — belirsiz |
| 64 hücre | 6,653 — geçerli | 9,041 — belirsiz |
| 128 hücre | 21,167 — belirsiz | 12,707 — belirsiz |
| 256 hücre | 13,281 — belirsiz | 21,167 — belirsiz |

Dolayısıyla “aralığı genişletip tekrar ölçün” genel bir çözüm değildir.
Önceki kayıtta yalnız aralık genişletme 821,689 kHz sonucunu 748,855 kHz'e
değiştirdi; daha fazla genişletme sonucu geçersizleştirdi. Gürültü referansı
seçimi ve spektral kuyruk kestiriminin aralığa duyarlılığı görülüyor.
Gerçek bant için bu sonuçlardan biri seçilmedi. Daha uzun ve çeşitli zaman
pencereleri ile temiz referans bölgelerini birlikte değerlendiren yöntem
gerekli; gereken süre bu iki kısa kayıttan belirlenemez.

Kaynak: `platforms/embedded/p0/src/p0_parameter_runtime.c:655` ve `:887`,
`app/operator_console/quick_measurement_actions.py:595`.

## Sinyal türünü veren model

Model yerelde PC üzerinde çalışan lojistik regresyondur. Sabit ağırlıklıdır;
canlı ölçümlerden kendiliğinden öğrenmez, buluta istek göndermez. Kart taşıyıcı,
OBW, güç ve SNR üretir; PC aynı dört I/Q karesinden Analog/Sayısal sonucunu ekler.

İşlem sırası: analiz aralığından spektral merkez hesabı → frekans kaydırma
(2500 Hz artık bırakılır) → 127 katsayılı, sabit 800 kHz kanal filtresi →
başlangıç örneklerini atma → ortalama/güç normalizasyonu → altı özellik →
standartlaştırma → ağırlıklı toplam ve sigmoid → karar.

Özellikler genliğin ve anlık frekansın standart sapması/basıklığı,
genlik spektrumundaki baskın tepe oranı ve dördüncü dereceden kümülanttır.
SNR 4 dB altındaysa, örnekleme hızı 2 MS/s değilse veya model skoru 0,90
eşiğini geçmezse Belirsiz döner. Taşıyıcı ve OBW'nin geçersiz olması bu
kararı doğrudan engellemez: SNR alanı geçerliyse model çalışabilir.

Eğitim yalnız sentetik AM/FM ve BPSK/QPSK içerir: 2000 örnek, 20 ms
gözlem, 4–30 dB SNR; yüzde 25'i test için ayrılır. Eğitim FM sapması
10–100 kHz, PSK hızı yaklaşık 50–500 ksym/s kapsamındadır. OFDM, QAM,
FSK, gerçek kanal bozulmaları ve bilinmeyen aileler için ayrı bir güvence yoktur.
0,98666 model skoru “bu gerçek RF sinyali yüzde 98,666 kesinlikle sayısaldır”
anlamına gelmez. Olasılıkların doğruluğu ayrı kalibrasyon verisiyle değerlendirilir:
[scikit-learn olasılık kalibrasyonu](https://scikit-learn.org/1.8/modules/calibration.html).

Somut kanal ayırma eksiği: seçilen aralık filtre genişliğini belirlemiyor,
yalnız merkez hesabına giriyor. Sabit 800 kHz filtre dar hedefte dış komşuyu
geçirebilir, geniş hedefte içeriği kesebilir. Sentetik tanıda dar hedef AM
değişmeden, merkezden 220 kHz'deki PSK komşusu eklenince Analog sonucu
Belirsiz'e döndü. Komşunun spektral sızıntısı da bu tanının parçasıdır;
deney ekran kaydındaki sınıfın yanlış olduğunu kanıtlamaz. Ek dokuz dar FM
tanısı Analog verdi; bu koşullarda hata üretilmedi. Her iki deney tek tohumlu
kapsam tanısıdır, başarı oranı veya RF kabulü değildir.

Modelin karar nedeni deneysel olduğunu söylüyor; ancak ana kart geçerli
alanlarda neden metnini gizleyip yalnız yeşil `GEÇERLİ` gösteriyor. Model
tahmini ile fiziksel olarak doğrulanmış sınıfın sunumda ayrılması gerekir.

Kaynak: `digital_analog_detection/integration.py`, `classifier_model.py`,
`train_classifier.py`; `app/operator_console/measurement_record.py:135`.

## Geliştirme sırası ve doğrulama

1. Sinyal merkezi ile gözlenen taşıyıcı çizgisini kullanıcıya ayrı göstermek;
   OBW kararsızlığında tek çözüm olarak aralık genişletmeyi önermemek.
2. Kısa pencere, gürültü referansı ve aralık duyarlılığını kayıtlı I/Q üzerinde
   birlikte incelemek; daha uzun toplama yöntemini RTL/ARM/referans model
   sınırlarıyla tasarlamak. Ret eşiğini gelişigüzel gevşetmemek.
3. Sınıflandırıcı için hedefe bağlı kanal ayırma, aynı eğitim/çalışma ön
   işlemesi, gerçek etiketli RF verisi ve bilinmeyen aile reddi geliştirmek.
   Önişleme değişirse mevcut ağırlıkların geçerli kaldığını varsaymamak.

`test_digital_analog_integration.py`, `test_board_parameter_measurement.py`
ve `test_operator_parameters.py`: **18 test geçti**. Bunlar içinde mevcut
sentetik sınıflandırma kanıtının yeniden üretimi de var. Bu sonuç yukarıdaki
saha/genelleme açıklarını kapatmaz.

Sayısal inceleme ve kaynak özetleri [evidence-v2.json](evidence-v2.json),
tekrarlama aracı [reproduce.py](reproduce.py) içindedir. Çalıştırma:

```powershell
python -X utf8 output/parameter-review-20260916/reproduce.py --output output/parameter-review-20260916/evidence-repeat.json
```

Özgün iki yerel ZIP ve C11 derleyicisi gerekir. Çıktı adı yeni olmalıdır;
araç mevcut kanıtı ezmez. Fiziksel kart/RF çalıştırılmaz; PL gücü kayıtlı
I/Q'dan yazılımda yeniden oluşturulur. Eski kartın çalışan hizmet hash'i
protokolde bulunmadığından güncel kaynakla fiziksel kabul eşleştirmesi yapılmaz.

Son kaynak kontrolünde bu inceleme dışında `quick_measurement_actions.py`
dosyasına tahmini güç sunumu eklendiği görüldü. Bu dosyanın kanıttaki özeti
inceleme anına aittir ve son çalışma ağacıyla eşleşmez; değiştirilmedi.
C sayısal çekirdeği, model, özellik çıkarımı, eğitim ve sınıflandırıcı adaptörü
ile tekrarlama aracının özetleri eşleşmektedir. Yukarıdaki 18 test, koşulduğu
andaki kaynak içindir; eşzamanlı arayüz değişikliklerinin kabulü değildir.
