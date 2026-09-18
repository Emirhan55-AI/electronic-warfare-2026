# Parametre ölçümü iyileştirmesi — 16 Eylül 2026

Kullanıcının parametre belirsizliği ve Analog/Sayısal ayrımı için istediği
düzeltmenin kaynak kapsamıdır. PHASE-08/ST-06 ve KTR-4.2 kabulü açıktır;
yeni faz veya fiziksel doğruluk kabulü oluşturulmadı.

## 18 Eylül 2026 geniş bant OBW düzeltmesi

Sonraki aynı-gün devamında ayrı koşullu taşıyıcı kestirimi P0PM-v5 olarak
çalışan karta bağlandı. Doğrudan çizginin yokluğu taşıyıcı merkezinin yokluğu
sayılmaz; mevcut merkez/OBW/çizgi anlamları değişmedi. Güncel ikili hash'leri,
66 karşılaştırma, iki gerçek kart tekrarı ve başarısız yeni canlı kapılar
`docs/interfaces/CARRIER_RECOVERY_20260918.md` içindedir. Aşağıdaki v3 ölçümleri
tarihsel ikili bağlarıyla korunur; yeni ikiliye taşınmış kabul sayılmaz.

`8ab4893c9d5a4c16a8c3befc77375f30.zip` adlı 16 karelik 820 MHz kaydında
merkez kararlılığı `1,070` hücre, OBW kenar değişimi `35,618` hücre ve tam
gözlem OBW genişliği `1401,693` hücredir. Eski yedi-hücre kapısı, kenar
değişimi genişliğin yalnız `%2,54`'ü olduğu halde sonucu reddetmiştir.
P0PM-v3 uzun ölçüm yolu için kenar kararlılık sınırı bu nedenle
`maks(7 hücre, OBW genişliğinin %5'i)` olarak değiştirildi. Dört karelik
dondurulmuş yol ve sıkışma/gürültü/komşu sinyal retleri korunur. Değişen uzun
ölçüm yöntemi yeni kayıtlarda `.groups16-v2` son ekiyle izlenir; eski
`.groups16-v1` kayıtları yeniden etiketlenmez.

Kayıtlı I/Q'nun taşınabilir C tekrarı merkez için `820,031321536 MHz`, alt/üst
kenar için `819,658288599/820,342708950 MHz` ve OBW için `684,420351 kHz`
üretti. `extended-numeric-fixed.json` on iki kararlı geniş bant sahnesini,
FM merkezini ve C/NumPy eşdeğerliğini geçirdi; `398,117` hücrelik bant değişimi
ile `483,949` hücrelik frekans sıçraması reddedilmeye devam etti.

Yeni hizmet ikilisi 18 Eylül'de çalışan karta yüklendi. `/usr/sbin/p0-ed-service`
SHA-256 özeti `f8588228f861cd36aa6d87bbdfde6e6d281248418884290a85e32a5f739d2ddf`,
ağ köprüsü özeti
`4797d7c300fb38e09869984b13bece5618f7ebcb34b459a4df5d96c601bb6bc1`dir.
Kart yetenek yanıtı P0PM-v3 uzun ölçümü bildirdi; fiziksel PL/ARM sayısal kapısı
altı sahneyi geçti. Sorunlu özgün kayıt çalışan hizmette `820,031321536 MHz`
merkez ve `684,373127 kHz` OBW verdi. Ayrı yeni HackRF → kanalizer → FPGA → ARM
koşusu 16/16 kareyle `820,144998 MHz` merkez, `674,851 kHz` OBW,
`-41,92 dBFS` kanal gücü ve `9,30 dB` SNR üretti. Kanıtlar sırasıyla
`real-820-board-v3.json`, `board-numeric-v3.json` ve `live-820-v3.json`
dosyalarındadır. Soğuk açılışta hizmet kalıcılığı, genel RF doğruluğu ve dBm
kalibrasyonu bu koşularla kabul edilmedi.

Ana sunumda `Gözlenen Taşıyıcı Frekansı` korunur. 820 MHz kaydında dar taşıyıcı
çizgisi kapısı geçmediği için alan `Gözlenmedi` kalır; merkez frekansı taşıyıcı
diye kopyalanmaz. Analog/Sayısal sonucundaki görünür deneysel rozet kaldırıldı
ve değer ana sonuç renginde gösterilir; sınıflandırıcının deneysel kökeni kayıt
ve teknik izlenebilirlikten kaldırılmadı.

## Bulgular ve kullanıcıya sunulan sonuç

820 MHz çevresindeki iki özgün arşiv dört adet 4096 örnekli I/Q karesi içerir:
2 MS/s hızda yalnız 8,192 ms gözlem. Ekrandaki son kayıtta merkez frekansı
819,941255 MHz hesaplanmış, ayrı taşıyıcı çizgisi bulunamamış, bant kenarı
değişimi 15,826 hücre ile 7 hücrelik kapıyı aşmıştır. Aynı I/Q üzerinde aralığı
64/128/256 hücre genişletmek bu ret durumunu düzeltmemiştir.
İnceleme: `output/parameter-review-20260916/RAPOR.md` ve `evidence-v2.json`.

Arayüzde `Sinyal Merkez Frekansı` ile `Gözlenen Taşıyıcı Frekansı` ayrı ana
satırlardır. Ayrı taşıyıcı çizgisinin gözlenmemesi merkez frekansının yokluğu
olarak sunulmaz. Bant kararsızlığı açıklaması yalnız aralığı genişletmeyi
çözüm olarak önermez. Dört sayısal alanın geçerlilik özeti sınıflandırıcı
puanını içermez; sinyal türü `DENEYSEL TAHMİN` durumuyla gösterilir.

## Uzatılmış kart ölçümü

P0CQ yetenek yanıtının `0x4` biti uzun parametre ölçümünü bildirir. Yeni PC,
bu bit yoksa eski dört kare yolunu kullanır. Bit varsa operatör isteğinden
sonra 16 özgün, ardışık, aynı alım bağlamına ve seçili kanala bağlı kare
toplanır: 2 MS/s hızda 32,768 ms. Atlanan kare toplama penceresini yeniden
başlatır; iptal ve aralık/bağlam denetimleri korunur. Yön bulma ve otomatik
akış içi parametre ölçümü dört kare olarak kalır.

P0PM-v3 isteği 64 bayt başlık ve 131.072 bayt I/Q olmak üzere 131.136 bayttır.
P0PR-v3 yanıtı 176 bayttır. Son kare, gözlem sayısı, istek kimliği, I/Q CRC ve
yanıt CRC eşleşmelidir. Eski v1/v2 istekleri ve dört kare aritmetiği korunur.
Köprü ile ARM hizmeti birlikte güncellenmelidir; yeni köprünün yetenek bayrağı
eski hizmetle kullanılmaz. Eski PC'nin bilinmeyen yetenek bayrağını reddetmesi
mümkündür; geri dönüşte eşleşen PC/köprü/hizmet sürümleri kullanılır.

PL aynı 4096 FFT/güç işlemini her karede yürütür; RTL değişmez. Sayısal merkez,
OBW, taşıyıcı ve güç hesabı ARM'dadır. 16 karede kalıcı parametre tamponunun
üst sınırı 1.557.504 bayttır; ilk uzun istek öncesinde eski 389.376 baytlık
tampon kullanılır. Bu sınır toplam hizmet RAM'i veya fiziksel hız kanıtı değildir.

OBW tanısı 16 kareyi dört bitişik gruba ayırır. Her grubu dışarıda bırakan
hesaba ek olarak her dört karelik grubun bant kenarları tam pencereyle
karşılaştırılır. En büyük grup farkı da 7 hücreyi geçmemelidir; kısa süreli
genişleme uzun ortalamada gizlenmez. Kuyruk kesirleri ve mevcut düzeltmeler
korunur. Dört kare yolu dondurulmuş yöntem olarak kalır; uzun kayıtta yöntem
kimliğine `.groups16-v1` eklenir. Bağımsız NumPy modeli yalnız doğrulama içindir,
üründe PC sayısal geri dönüşü yoktur.

## Analog/Sayısal model

`selected_integration.py`, `channel_features.py` ve `selected_channel_model.py`
ürünün yeni manuel parametre sınıflandırma yoludur. Önceki `integration.py`,
modeli ve eğitim aracı tarihsel doğrulama için korunur.

Sınıflandırıcı bilgisayarda yerel çalışır: seçili aralıkta merkez kestirimi,
frekans kaydırma, seçime uyarlanan 127–2049 katsayılı FIR, normalizasyon ve
altı özellik üzerinden standartlaştırılmış lojistik regresyon. Eğitim ve
çalışma zamanı aynı önişlemeyi kullanır. İnternete veri göndermez. Dört karelik
özellik penceresi korunur; 16 karelik ölçümde son dört özgün kare kullanılır ve
`classification_frame_indices` ile kayda bağlanır.

Yeni eğitim kümesi AM, FM, dar bant FM, BPSK ve QPSK ailelerinden 2.000 sentetik
örnektir. Örnekleme hızı 2 MS/s, eğitim SNR aralığı 4–30 dB'dir. Karar için
en az 4 dB SNR, 0,90 model skoru ve eğitim özellik aralığı denetimi gerekir.
Özellik aralığı denetimi bütün bilinmeyen modülasyonları tanıma garantisi değildir.
Skor RF doğruluk olasılığı veya kalibre güven düzeyi olarak yorumlanmaz.

## Tekrarlanabilir doğrulama ve açık kapı

- `python scripts/verify_p0_parameter_runtime.py --extended --wide`: eski
  dört kare yolunda 49 referans eşdeğerliği senaryosu; durum makinesi 16 kare
  tamamlanması, kopma, sıfırlama ve dört kareye geri dönüşü de denetler.
- `python scripts/verify_extended_parameter.py --output YENI_DOSYA.json`:
  12 geniş bant sentetik senaryoda C/NumPy karşılaştırması. 16 karede 12/12,
  dört karede de 12/12 geçerli; bu kümede başarı oranı artışı gösterilmedi.
  Kırpılmış bant, yalnız gürültü ve değişen bant reddedilir.
- `python scripts/train_selected_channel_domain.py --help`: model yeniden
  üretme seçenekleri. Ayrı tohumlu, aynı aile üreticilerini kullanan 1.000
  geliştirme örneğinde 989 doğru, 11 kararsız, 0 yanlış karar. Bağımsız RF
  deneyi veya yeni modülasyonlara genelleme kabulü değildir.
- `tests/test_selected_channel_domain.py`: seçili AM yanında güçlü komşu,
  kapsam dışı özellik, düşük SNR, hız ve kaynak hash denetimi.
- `tests/test_extended_parameter_record.py`, `test_live_ed_session.py` ve
  `test_live_ed_view_model.py`: 16 kare, tazelik, olay kimliği değişimi,
  CRC, kayıt/tekrar okuma ve PC sayısal geri dönüş yasağı.
- `tests/p0/p0_parameter_bridge_loopback_test.py`: v1/v2/v3 isteklerinin
  parçalı TCP'den tek yerel pakete eksiksiz aktarımı; sahte hizmetle Linux testi.

Son geliştirme çıktıları `output/parameter-fix-20260916/` altındadır:
`model-development.json`, `extended-numeric-final.json`, `transport.json`,
`record-classification.json`. Özgün iki RF arşivi değiştirilmedi; yeni model
ikisinde de Sayısal tahmini vermiştir, gerçek etiketleri bilinmemektedir.
Dört karelik arşivden örnek tekrarlayarak 16 karelik fiziksel sonuç üretilmedi.

ARM hizmeti ve köprüsü `build/p0/parameter-extended-20260916/software-v2/`
altında derlendi; kaynak/ikili hash'leri `build.json` içindedir. Henüz karta
yüklenmedi. SSH kimliği kart konsolundan doğrulandıktan sonra eşleşen ikililerle
özgün 16 karelik RX ölçümü, gecikme, iptal ve tekrar koşuları gerekir. Mevcut
820 MHz yayında belirsizliğin azaldığına ilişkin fiziksel kanıt henüz yoktur.
