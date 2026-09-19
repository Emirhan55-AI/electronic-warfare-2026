# KTR Gereksinim İzlenebilirliği

## KTR-4.1-OPS-B0 AMP düğme sözleşmesi — 19 Eylül 2026

`HackRFControls.qml` ve `RxSurveyView.qml`, RF AMP'yi açılır liste yerine
`Kapalı`/`Açık` metinli, seçili durumu görünür iki durumlu düğme olarak sunar.
`toggleReceiverRFAmplifier()` yalnız alıcı dururken ortak ayarı değiştirir;
canlı veya bant taraması sürerken düğme pasif ve backend çağrısı fail-closed'dur.
Görünüm modeli testi etkin oturum reddini ve ardışık iki tıklamadaki durum
değişimini, QML testi görünür düğme durumunu doğrular. Alım ve tarama
yapılandırmaları mevcut `rf_amplifier` alanını kullanmayı sürdürür.

## KTR-4.4 kuzey işareti ve eşzamanlı spektrum sunumu — 19 Eylül 2026

`Main.qml`, Yön Bulma görevinde 0° kuzey ve saat yönünde artan 0°–359,99°
kullanıcı işaretini pusulada ölçüm sonucundan ayrı renk ve etiketle gösterir.
Değer yalnız görünüm durumudur; `directionPoints`, `AdaptiveDirectionSweep`,
P0PM-v4 veya P0DF-v1 girdilerine bağlanmaz. Aynı görevde alt panelin solunda
`spectralDisplay` kaynağından kalibrasyonsuz dBFS spektrogramı, sağında canlı
spektrum bulunur. KTR-4.4 açı–güç geçmişi eski en güçlü aday kartının yerine
üst alana taşınmıştır. `DetectionGuidePainter.js` aynı
`detectionMarkers` olaylarını tam spektrum koordinatına taşıyarak FPGA tespit
bantlarını ve tepe çizgilerini yön görünümünde de çizer. Görünüm modeli ayrıca
kilitli yön hedefinin frekans/kanal sınırlarını normalize eder; olay görünürlüğü
geçici olarak kaybolsa da bu gerçek kilit bağı turuncu işaret olarak kalır.
Her iki grafik `spectrumViewStart/End` bağını ve aynı tekerlek/sürükleme/çift
tıklama kontrollerini kullanır. `test_app_f_quick_product.py`,
44° girişini, alan temizlenince işaretin kalkmasını, geçmişin yeni konumunu,
spektrogram–spektrum yerleşimini, kilitli FPGA işaretini, eşzamanlı görünüm
aralığını ve erişilebilir nesne
sözleşmesini doğrular.
Bu sunum izi coğrafi yön ölçümü,
anten kalibrasyonu veya fiziksel derece RMS kabulü değildir.

## KTR-4.1 → KTR-4.2 çalışan tarama devri — 19 Eylül 2026

Tarama sürerken seçili geçmiş gözlem için `Parametre Çıkarımına Git` veya
`Sinyali Yeniden Al` verilebilir. `RxSurveyView.qml` bu iki eylemi çalışan
taramada etkin tutar; `quick_scan_actions.py` hedef frekansı ve işlem niyetini
kilitler, taramayı kontrollü iptal eder ve worker kapanışından sonra aynı
kazançlarla sabit 8 MS/s RX başlatır. Böylece tek HackRF üzerinde çakışan iki
alım süreci oluşturulmaz. Görünüm modeli testleri hem doğrudan yeniden alımı hem
parametre için hazır confirmed olay seçimini; QML testi düğme sözleşmesini
doğrular. KTR-4.1 tespiti ve KTR-4.2 parametre matematiği değişmemiştir; bu ürün
akışı doğrulaması yeni fiziksel RF kabulü değildir.

## KTR-4.1 sinyal frekansı aktarımı — 19 Eylül 2026

`RxSurveyView.qml`, `Taramayı Başlat` eyleminin solunda `Taaruz Aktarım`
düğmesini sunar. `SurveyController`, `SİNYAL TESPİTİ` bölümünü oluşturan güncel
sunum satırlarının frekanslarını proje kökündeki `Logs` klasöründe
`gün_saat_dakika_sıra.txt` adlı UTF-8 TXT dosyasına birer satır olarak yazar;
aynı dakika içindeki sıra `_1` değerinden başlar, boş listede dosya oluşturmaz ve mevcut
dosyayı değiştirmez. Birim testleri dosya içeriğini, boş liste davranışını ve
Türkçe sonucu; QML testi düğme adı, çağrı bağı ve `Taramayı Başlat` öncesindeki
yerleşimi denetler. Bu yalnız KTR-4.1 operatör çıktısıdır; tespit hesabı, RF
kanıtı ve açık PHASE-08/ST-06 kabul kapıları değişmez.

## Windows EXE paketi — 18 Eylül 2026

KTR-4.1–4.4 ürün erişimi Windows EXE ve logolu masaüstü kısayoluyla sağlanır. İz: `scripts/build_windows_product.py`, `scripts/verify_windows_product.py`, `scripts/install_desktop_shortcut.ps1`, paket manifesti ve dağıtım tarifi. Taşıyıcı kestirimi ve seçili kanal sınıflandırıcısının eksik dört kaynak izi eklendi; kalibrasyon varlığı denetim listesiyle eşitlendi. İlgili sözleşme testleri 12/12 geçti. 90 zorunlu varlık, bütün 3.229 paket dosyası, kaynaklar, EXE ve ZIP hash ile bağlıdır; izole açılış ve masaüstünden gerçek EXE penceresi doğrulandı. Olumsuz Qt/ICU kaydı korunur. Kanıt `results/evidence/app/windows-product-20260918.json`, sınır `docs/interfaces/WINDOWS_PRODUCT_PACKAGE.md` içindedir. Yeni fiziksel RF/DSP kabulü yoktur.

## Masaüstü kısayolu izi — 18 Eylül 2026

KTR-4.1–4.4 görevlerine erişim, `scripts/install_desktop_shortcut.ps1` üzerinden güncel `app.operator_console` ürün girişiyle sağlanır. `quick_application.py` mevcut `assets/baz-logo.ico` dosyasını pencere simgesi olarak kullanır; paket manifesti ve dağıtım tarifi ICO varlığını içerir. Doğrulama: ürün `--smoke-test` açılışı, kısayol hedef/argüman/çalışma dizini/simge denetimi ve kısayoldan gerçek pencere açılışı. DSP, RTL, ARM hesapları ve fiziksel kabul değişmedi.

Açılış smoke testi ve kısayoldan gerçek `BÂZ` penceresi doğrulandı. İlgili paket testlerinde 10/12 geçiş vardır; iki başarısızlık önceki sürümde de bulunan eksik kaynak izleri ve `release-assets` liste uyuşmazlığıdır. Bunlar yeni bağımsız paket kabulünü açık tutar; yerel masaüstü açılışı başarılıdır.

## KTR-4.2 koşullu taşıyıcı frekansı — 18 Eylül 2026

İz: `p0_parameter_runtime.c`, `parameter_client.py`, `carrier_recovery.py`,
`measurement_record.py` ve `ParameterMeasurementPanel.qml`. P0CQ `0x8` /
P0PM-v5, ikinci/dördüncü kuvvet ve dört zaman grubu uzlaşmasını ARM'da uygular;
köken byte 37, CRC ve özgün 16 CI8 kare bağını korur. Kayıt/arayüz koşullu
kestirimi gözlenen çizgiden ve merkezden ayırır. 66 C/NumPy karşılaştırması,
iki gerçek PL/ARM kayıt tekrarı, altı normal parametre ve sekiz yön kart sahnesi
geçti. 6 dB sentetik kapsam kaybı ve yeni canlı referans uyuşmazlığı retleri
saklanmıştır. Güncel hizmet hash'i, kanıtlar ve açık kalibrasyon/RF/soğuk
açılış kapıları: `docs/interfaces/CARRIER_RECOVERY_20260918.md`. KTR-4.2 veya
PHASE-08/ST-06 tamamlanmış sayılmaz; yeni faz açılmadı.

## KTR-4.3 kesintisiz analog izleme/dinleme — 18 Eylül 2026

- Gereksinim: Tespit edilen ve parametreleri çıkarılan analog yayının
  sürekliliği ile zamansal/frekanssal davranışı izlenir; çözülebilen şifresiz
  ses/veri, demodülasyon sonrasında operatöre sunulur.
- Uygulama: `live_ed.py`, doğrulanmış ilk beş saniyeden sonra yalnız yeni ve
  ardışık FPGA/ARM bağlı I/Q karelerini verir. `StreamingAnalogMonitor`, AM/NFM
  demodülasyon durumunu parçalar arasında korur. `quick_listening_actions.py`
  canlı hoparlör/WAV akışını, yirmi saniyelik PCM halkasını ve fail-closed
  süreklilik kapılarını yönetir. `Main.qml`, 250 ms güç/frekans izini ve açık
  canlı durumu gösterir. `signaling.py` yalnız tutucu DTMF çözümü sağlar.
- Doğrulama: `tests/test_phase05_monitoring.py`, tek/parçalı altı saniyelik NFM
  girdisinde aynı PCM16'yı, DTMF kabul/ret kapılarını ve DSP sınırlarını;
  `tests/test_live_ed_session.py`, yalnız yeni ardışık kareleri ve geride kalma
  boşluğunu; `tests/test_live_ed_view_model.py`, beş saniyeden sonra RX'in açık
  kalmasını, canlı durum/iz/süreklilik/DTMF sunumunu sınar.
- Açık kabul: Gerçek analog amatör telsiz konuşmasının uzun süreli hoparlör
  dinlemesi, uçtan uca gecikme/dropout, verici pre-emphasis eşleşmesi ve
  kontrollü kapalı/açık/kapalı RF tekrarı henüz yapılmadı. DTMF dışındaki analog
  kodlar ile sayısal telsiz protokolleri uygulanmadı. PHASE-08/ST-06 ve KTR-4.3
  fiziksel kabulü açıktır.

## KTR-4.4 bağıl yön ve P0DF sonuç görünürlüğü — 18 Eylül 2026

- Gereksinim: Genlik tabanlı yön bulma, ölçülmüş açı–güç noktalarından sensörün
  0° eksenine göre derece sonucu üretir; coğrafi referans yoksa kuzey/doğu
  kerterizi iddia etmez. Fiziksel doğruluk bilinen gerçek yönlere karşı dairesel
  `Derece RMS` ile değerlendirilir.
- Uygulama: `quick_direction_actions.py`, P0DF-v1 için tarama-yerel 32 bit kaynak
  belirteci ve ölçümleri koruyan ARM yeniden-deneme eylemini sağlar.
  `direction_client.py` uint32 sözleşmesini gönderimden önce doğrular ve kart
  hata sınıflarını ayırır. `quick_view_model.py` ile `Main.qml`, ilk fiziksel
  anten eksenini 0° olarak gösterir; ham en güçlü ölçüm adayını ARM doğrulanmış
  sonuçtan ayırır ve derece RMS kapısının açık olduğunu bildirir.
- Doğrulama: `tests/test_adaptive_direction_sweep.py`,
  `tests/test_phase09_df_protocol.py`, `tests/test_live_ed_view_model.py` ve
  `tests/test_app_f_quick_product.py` protokol sınırı, yeniden başlayan oturum
  belirteçleri, bağıl sektör metni, sonuç yeniden denemesi ve QML görünürlüğünü
  sınar. `scripts/verify_phase09_direction_live_service.py` çalışan 47007 kart
  hizmetindeki sekiz sayısal sahneyi doğrular; sonuç
  `results/evidence/phase09/amplitude-df-live-service-20260918.json` içindedir.
- Açık kabul: Yeni kaynakla bilinen fiziksel açı, uygun yönlü anten ve kontrollü
  yayın kullanılarak tekrarlar tamamlanmadı. RMSE, bias, p95, maksimum hata ve
  geçerli sonuç oranı henüz ürün doğruluğu olarak yayımlanamaz.

## KTR-4.2 OBW ölçekli kararlılık ve sonuç sunumu — 18 Eylül 2026

16 karelik P0PM-v3 yolunda OBW kenar kararlılık kapısı, dar/geniş yayınlarda
aynı göreli anlamı korumak için `maks(7 hücre, ölçülen OBW'nin %5'i)` olarak
ölçeklendi; tarihsel dört kare yolu değişmedi. Özgün 820 MHz kayıt tekrarı eski
`35,618 > 7` retini, yeni `35,618 < 70,085` geçişini ve `684,420351 kHz`
sonucunu doğrular. Yeni uzun ölçüm kayıtları `.groups16-v2` yöntem son ekini
taşır; sentetik değişen bant ve frekans sıçraması retleri korunur.
İz: `platforms/embedded/p0/src/p0_parameter_runtime.c`,
`algorithms/parameters/extended_obw.py`, `scripts/verify_extended_parameter.py`,
`output/parameter-review-20260918/real-820-replay-fixed.json` ve
`output/parameter-review-20260918/extended-numeric-fixed.json`.

Çalışan kartta kurulum ve işlev izi:
`output/parameter-review-20260918/capabilities-v3.json`,
`output/parameter-review-20260918/board-numeric-v3.json`,
`output/parameter-review-20260918/real-820-board-v3.json` ve
`output/parameter-review-20260918/live-820-v3.json`. Son dosya gerçek
HackRF → FPGA → ARM akışında 16/16 kare, geçerli merkez/OBW/güç/SNR ve ayrı
`Gözlenmedi` taşıyıcı sonucunu kaydeder. Soğuk açılış kalıcılığı, genel RF
doğruluğu ve dBm kalibrasyonu açık kabul kapılarıdır.

`ParameterMeasurementPanel.qml` ayrı `Gözlenen Taşıyıcı Frekansı` satırını
yeniden ana sonuçlara alır. Gözlenmeyen taşıyıcıya sayı üretilmez. Sinyal türü
değeri ana sonuç rengiyle gösterilir ve görünür deneysel rozet kaldırılır;
deneysel model bağı kayıt/metot kimliğinde korunur. Tek canlı RF koşusunun
işlev geçişi genel RF doğruluğunu, dBm kalibrasyonunu veya fiziksel KTR-4.2
kabulünü tamamlamaz.

## KTR-4.2 parametre iyileştirmesi — 16 Eylül 2026

Merkez frekansı ve ayrı taşıyıcı çizgisi ana sonuçlarda ayrıldı. Yetenek bildiren
kartta manuel ölçüm 16 özgün kareye (2 MS/s hızda 32,768 ms) uzatıldı; eski
kartta dört kare korunur. P0PM-v3, ARM grup kararlılığı denetimi ve kayıt/CRC
bağı eklendi; sayısal hesap için PC geri dönüşü yoktur. PL'nin kare başına
4096 FFT işlemi değişmedi. Yerel Analog/Sayısal modeli seçili kanal filtresiyle
aynı önişlemede yeniden eğitildi; sonuç deneysel tahmin olarak gösterilir.
Kaynak/test ve ARM derlemesi tamamlandı; karta yükleme ve yeni RF ölçümü
henüz yapılmadı. PHASE-08/ST-06 ve fiziksel KTR-4.2 kabulü açıktır. Yöntem,
kanıtlar, uyumluluk ve sınırlar: `docs/interfaces/PARAMETER_REFINEMENT_20260916.md`.

## KTR-4.3 dinleme kolaylıkları — 16 Eylül 2026

Bilinmeyen yayında aynı I/Q kaydını AM ve dar bant FM ile karşılaştırma,
sade kanal seçimleri, gizlenebilir ince ayar ve isteğe bağlı 200 Hz konuşma
filtresi eklendi. Yöntem seçimi otomatik tür tespiti sayılmaz. Canlı ses
hazırlığı son beş saniyeyi sabitleyip RX'i durdurur; kesintisiz ses akışı ve
sayısal kod çözümü yoktur. PL/ARM/RTL ve tespit kapıları değişmedi.
Kaynak/test doğrulaması yeni fiziksel kabul değildir; PHASE-08/ST-06 ve
KTR-4.3 açık kalır. Güncel ayrıntı `docs/interfaces/SIGNAL_MONITORING_LISTENING_STATUS.md`,
tekrarlanabilir ölçüm ve test kaydı `docs/reviews/LISTENING_ASSISTANCE_20260916.md` içindedir.

## KTR-4.2 kalibrasyonsuz güç tahmini — 16 Eylül 2026

`power_estimate.py`, geçerli canlı kanal gücünü dBFS'den yaklaşık SMA giriş
dBm değerine dönüştürür. Bağ; frekans, LNA/VGA, RF AMP ve kanal seçici genlik
ölçeği tam olduğunda kurulur. Arayüz sonucu `Tahmini Güç (dBm)`, `TAHMİNİ`,
yaklaşık işareti ve en az ±15 dB belirsizlikle sunar. Eksik/uyumsuz bağlam sayı
üretmez. Birim ve durum ayrımı, bu alanın kalibre `channel_power_dbm` olarak
yorumlanmasını engeller. Sayısal model regresyonu kazanç, AMP, ölçek ve geçersiz
bağlamı; canlı ölçüm regresyonu satır sırası ile görünür belirsizliği doğrular.
Kalibre dBm gereksinimi ve fiziksel kabul kapısı kapanmadı.

## KTR-4.2 parametre aralığı sunumu — 16 Eylül 2026

`ParameterMeasurementPanel.qml` içindeki sınırlı analiz aralığı uyarısı,
`Aralığı Düzenle` eylemi ve elle alt/üst frekans alanları kullanıcı kararıyla
kaldırıldı. `quick_measurement_actions.py` canlı adayın seçili aralığın dışına
taşması halinde aralığı otomatik genişletmeyi, kart sınırını aşan veya geçersiz
aralığı reddetmeyi sürdürür. QML regresyonu kaldırılan yüzeyi; canlı ölçüm
regresyonu `automatic_live_expansion` kayıt kökenini doğrular.
KTR-4.2 ölçüm ve kabul kapıları değişmez.

## APP-F Sistem çalışma alanı kaldırma kaydı — 16 Eylül 2026

Kullanıcı kararıyla `Sistem` görev girişi, `Ctrl+5` kısayolu, işlem zinciri
denetçisi ve arayüz olay günlüğü ürün yüzeyinden kaldırıldı. KTR-4.1-OPS-B0
kapsamındaki HackRF/FPGA bağlantı denetimi `Sistemi Denetle` eyleminde korunur.
Değişiklik yalnız sunum kapsamındadır; DSP/RTL/ARM işleyişi, kanıt kayıtları ve
PHASE-08/ST-06 kabul kapısı değişmez.

## Durdurulan tam bant turu — 16 Eylül 2026

Kullanıcı isteğiyle 1–6000 MHz turu 1963/2400 pencerede durduruldu; tamamlanan
kapsam 1–4908,5 MHz, liste 161 geçmiş gözlemdir. 60 kayıt 40 MHz katlarına
±10 kHz yakındır; bu ortak kaynak şüphesidir, kesin parazit/verici sayısı
sınıflaması değildir. İki kare sayacı ve sekiz geniş/dar eşleşme incelemesi
açıktır. İki kazanç ve bir USB taşma tekrarı vardır; başarısız kalan pencere
sayısı sıfırdır. Son tekrar kontrolü yapılmadı. Özgün kayıt, hash ve ayrıntılar
`output/rx-wideband-20260916/RAPOR.md` içindedir. KTR-4.1 / KTR-4.1-OPS-B0,
PHASE-08/ST-06 fiziksel kabulü açık kalır; yeni faz açılmadı.

## Tam bant taraması ve liste gözlemi — 16 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında canlı tam bant taraması başlatıldı.
Kaynak sunumu, listeyi yeni kayıtta başa döndürmez; geçmiş/kayıt sayısını
gösterir. Ham kanıt korunur. Sayaç taşması ve geniş adayın dar ikinci ayarla
eşleşmesi kabulü açık tutar. İlk gözlem raporu
`output/rx-wideband-20260916/RAPOR.md` içindedir.

PHASE-08/ST-06 açık; bu kayıt yeni fiziksel kabul oluşturmaz.

## Kullanıcı mesajları ve bölümleme — 16 Eylül 2026

`RxSurveyView.qml`, `SİNYAL TESPİTİ` başlığı altında üç kullanıcı bölümü sunar:
`Tekrar doğrulanan adaylar`, `Tekrar ölçülmesi gerekenler`, `Alıcı etkisi
olabilecekler`. Kayıt özeti, `Tarama geçmişi` ve grup açıklamaları kaldırılarak
dikey alan aday listesine bırakılmıştır. Aday satırları operatöre önce inceleme,
yeniden ölçme veya yayın olarak kabul etmeme kararını verir. Aralığı ölçülen her kayıt aynı
`Tespit aralığı` satırını taşır; 1 kHz'den dar çizgiler kenarları ayırmak için dört
ondalık MHz ile biçimlenir. Teknik yöntem ayrıntısı üzerine gelme açıklamasında
kalır. Gerçek QML ve sunum regresyonu geçmiştir; bölümleme
fiziksel kabul kapısını değiştirmez.

Liste güven ile seviyeyi ayrı taşır. Farklı alıcı ayarında yeniden görülme
güven bölümünü belirler; bölüm içi sıra, kalibre edilmiş güç iddiası kurmadan
ölçülen tepe/gürültü farkını kullanır. Zayıf veya farkı hesaplanamayan kayıtlar
korunur. Üç farklı dar 40 MHz-kat çizgisi alıcı etkisi şüphesi için yeterlidir;
satırlar silinmez ve kullanıcıya yayın kabul etmeme yönlendirmesi gösterilir.
1750–1950 MHz kayıt örneği ile sunum, sıralama, kayıt koruma ve QML regresyon
gruplarında 95 test geçmiştir. Bu değişiklik PHASE-08/ST-06 fiziksel kabulünü
kapatmaz.

## KTR-4.2 otomatik parametre kataloğu sunumu — 16 Eylül 2026

`KAYITLAR` bölümü dört karelik PL/ARM sonuçlarını kalıcı SQLite kaydında tutar;
seçili sinyalin `Parametre Çıkar` sonucu ayrı ölçüm kaydına yazılır.
QML kartı listeyi varsayılan olarak kapalı gösterir; `Kayıtları Göster` ile ilk sekiz kayıt
görünür ve CSV dışa aktarma tüm kayıtları içerir. `Parametre Çıkar` mevcut
analiz aralığını onaylayarak ölçümü başlatır. Yenileme, CSV dışa aktarma ve
kayıt klasörünü açma sonucunun başarı veya hata mesajı panelde görünür ve
operasyon günlüğüne yazılır. Katalog satırları frekans, OBW, dBFS, SNR, alıcı
bağı ve kalite durumunu taşır; geçerli profil yoksa dBm `Kalibre değil` kalır.
Kart başlığında yalnız kayıt sayısı ve işlemler gösterilir. Ana sonuç alanları
taşıyıcı frekans, bant genişliği, dBFS kanal gücü ve sinyal türüdür. Sinyal
türü satırındaki `PC, deneysel` arayüz eki, OBW açıklaması ve parametre düğmesi
altındaki canlı kare sayacı ana sunumdan kaldırılmıştır; deneysel PC
sınıflandırıcısı kayıt ve teknik izlenebilirlikte belirtilmeye devam eder.
Bu sunum değişikliği fiziksel parametre doğruluğu kabulü oluşturmaz.

## KTR-4.1 / KTR-4.1-OPS-B0 — 16 Eylül 2026

Tarama bitişindeki otomatik yeniden kontrol ayrı `Son Kontrolü Durdur` eylemi
olarak sunulur. Sabit ve bant taraması listeleri canlı güncellemede ilk görülme
sırasını ve sabit kart yüksekliğini korur; nihai aile sınıflaması ile güç/fark
sıralaması tur sonunda bir kez uygulanır. Parametre→Dinleme devri sırasında iki-LO doğrulaması beş
saniyelik ses tamponunu kesmez. OBW zamansal kararsızlığı eşik gevşetmeden
`TEKRAR ÖLÇÜLMELİ` ve eyleme dönük açıklamayla gösterilir. QML, keyed model,
canlı devir ve sunum regresyonları bu bağları denetler; fiziksel kabul durumu
değişmez.

KTR-4.3 dinleme kartındaki süre, ardışık I/Q tamponunun gerçek doluluğuna
bağlandı. Hedef kanal doğrulamasındaki kısa kayıp artık veri sayacını görsel
olarak sıfırlamaz; beş saniyelik veri hazır olduğunda sinyal sürekliliği
`sinyal hazır`, `hedef sinyal kesiliyor` veya çoklu aday açıklamasıyla ayrı
sunulur. Dinleme için mevcut FPGA süreklilik kapısı gevşetilmemiştir.

`RxSurveyView.qml` frekans etiketlerini gerçek spektrum merkezi ve hızına bağlar.
`Main.qml` tespit ile ek doğrulamayı ayrı sunar; `fixedVerificationActive`
yalnız çalışan doğrulama bağlamından türetilir. Gerçek QML regresyonu 10 ve
2 MS/s eksenlerini, boş/kuyruk/aktif doğrulama ayrımını ve tespit ekranındaki
özet kartının gizliliğini sınar. Aday aralığı `Tespit aralığı` olarak gösterilir.
16 Eylül yerel RF gözlemi eski çalışan süreç kapsamındadır; yeni kaynağa kabul
aktarılmaz. Kanıt sınırları `docs/interfaces/SIGNAL_DETECTION_STATUS.md` içindedir.

## KTR-4.3 analog dinleme ses yolu — 16 Eylül 2026

AM/NFM demodülasyonu gerçek seçili I/Q üzerinde çalışır. Analog konuşma kanal
sözleşmesi 2–25 kHz, parametre kaynaklı öneri 6–25 kHz ile sınırlandı. NFM
varsayılanı de-emphasis uygulamayan `Net ses`; 750 µs yalnız isteğe bağlı
eşleşen telsiz profilidir. 48 kHz'e örnek azaltmadan önce 257 tap konuşma
alçak geçiren süzgeci yüksek frekanslı NFM ayrıştırıcı gürültüsünün ses bandına
katlanmasını bastırır. Arayüz temel ayarlara ve altı sonuç satırına indirildi;
dalga biçimi ile seviye/frekans kararlılığı korunur. Sentetik AM/NFM, 20 dB,
blok sürekliliği, profil ve alias reddi testleri izlenebilirliği sağlar. Yeni
kaynakla gerçek telsiz konuşması denenmedi; KTR-4.3 fiziksel kabulü açıktır.

## KTR-4.1-OPS-B0 tespit ayarlarının görev ayrımı — 15 Eylül 2026

`HackRFControls.qml` sabit frekans LNA/VGA/AMP seçimlerini tek doğrudan alıcı
grubunda, `RxSurveyView.qml` tarama AMP seçimini kendi alıcı satırında sunar.
`DetectionSettings.qml` yalnız FPGA FFT ile normal/zayıf CFAR eşiklerini ve
ayrı tarama modunda pencere gözlem ayarlarını taşır. NFM ses düzeltmesi
`Main.qml` Dinleme görevine taşınmış; salt görüntü FFT/yenileme/seviye/tepe-tut
kontrolleri ürün yüzeyinden çıkarılmıştır. `test_app_f_quick_product.py` gerçek
QML nesne ayrımını, `Ayarlar` başlığını, AMP/ses seçimini, CFAR sınırlarını ve sade pencereyi
doğrular. İlgili iki ayrı regresyon sürecinde 136 + 61 test geçti. DSP, kart
profil protokolü ve fiziksel kabul durumu değişmemiştir.

Son sadeleştirmede iki sabit yönlendirme satırı kaldırılmış, görünür `FPGA FFT`
etiketi `FFT` yapılmış ve `Karttan Oku` / `Varsayılana Dön` / `Uygula`
düğmeleri eşitlenmiştir. Alternatif CFAR eşik profili için fiziksel doğrulama
olmadığından katsayılar sınırlı elle giriş ve tam kart geri okuması olarak
korunur. AMP iki durumlu RF yükselteci olduğundan dB değeri gibi sunulmaz;
Sade `AMP` etiketi ve ortalı açık/kapalı seçim kullanılır. Gerçek QML denetimi bu
metin, boyut ve hizalama sözleşmesini doğrular; ilgili QML/kart profili/canlı
görünüm modeli regresyonunda 123 test geçmiştir.

Alanlar iki sütunlu forma hizalanmıştır. CFAR değerleri iki ondalıkla sunulurken
değiştirilmemiş alanın tam kart geri okuması korunur. QML testi biçimlendirmeyi,
ortak etiket/kutu başlangıçlarını ve tam değeri seçen uygulama dalını denetler.

Bant taraması görünür alıcı etiketleri `LNA (dB)` / `VGA (dB)` / `AMP` olarak
sadeleştirilmiş; teknik 10 MS/s süre metni kaldırılmıştır. `Gözlem (kare)` ve
`Yerleşme (kare)` doğrudan tespit penceresini etkilediği için korunur. Gerçek
QML testi metinlerin varlık/yokluk sözleşmesini ve sade pencereyi doğrular.

Tarama adayından parametre görevine geçişte `RxSurveyView.qml` önce sabit frekans
yeniden alım görünümünü açar; `quick_scan_actions.py` seçilen adayı 8 MS/s RX ile
yeniden doğruladığını bildirir. Başlatma durum yarışı nedeniyle reddedilirse
korunmuş tarama görünümüne dönülür. Canlı aday ölçüme hazır olduğunda mevcut
`surveyParameterReady` bağı Parametre sekmesini açar. QML ve görünüm modeli
testleri görünüm geçişini, 8 MS/s alıcı yapılandırmasını ve hazır sinyal seçimini
doğrular.

`quick_view_model.py`, etkin FFT 8192/16384 iken 4096 varsayılanına dönüşün
kontrollü kart yeniden başlatması istediğini ve bunun tam güç kesmeli cold-start
kabul koşusu olmadığını kullanıcıya bildirir. Kart profili veya güvenli küçültme
reddi değiştirilmemiştir; `test_card_detection_settings.py` bu ayrımı doğrular.

`quick_runtime.py`, 8192/16384 FPGA FFT'nin daha uzun ham önizlemesini sabit
16.384 kompleks örnekli görüntü/kaba aday penceresine gerçek bitişik örneklerle
sınırlar. FPGA tespit karesi veya güç hesabı değiştirilmez.
`test_detection_settings.py` iki büyük FFT profilinde çıktı uzunluğunu ve kaba
aday yolunu; `test_live_ed_view_model.py` kullanıcı hata metnini doğrular.
Kartın son geri okuması FFT 8192'dir; 4096 seçiminin uygulanması kontrollü kart
yeniden başlatması gerektirir. Güncel kaynakla fiziksel tekrar açık kalır.

Kontrollü yeniden başlatma sonrasında kartın kuşak 1 / FFT 4096 profiliyle açık
uygulamadaki eski 8192 önbelleği ayrışabildiği için `quick_view_model.py`, şüpheli
küçültme uygulamasından önce güncel kart profilini tekrar okur ve ayarı güncel
kuşağa bağlar. `test_card_detection_settings.py` eski 8192 önbelleğiyle tek
tıklamada 4096 uzlaşmasını doğrular. `transport.py` yapısal olarak geçerli kart
başlığındaki sıfır dışı hizmet durumunu ayrı hata koduna çevirir;
`test_p0_transport.py` DMA hatasının `local_response_header` olmadığını denetler.

`Main.qml` ve `RxSurveyView.qml`, kalibre edilmemiş bağıl P/N ile FPGA gözlem
sayısını kullanıcı üzerine-gelme metninde parametre gibi sunmaz. İç model bu
değerleri tespit sürekliliği ve sıralaması için korur. QML regresyonu sayısal
P/N sunumunun bulunmadığını doğrular; mutlak dBm yalnız geçerli kalibrasyonlu
parametre ölçüm sözleşmesindedir.

## KTR-4.1 / KTR-4.2 alıcı ayarları ve ölçüm bağlamı — 15 Eylül 2026

`LiveEDConfiguration.rf_amplifier` ve `SurveyConfig.rf_amplifier`, sabit alım,
geniş bant ve bağımsız aday doğrulamalarına aynı AMP seçimini taşır. Tarama
referans anahtarı AMP'yi içerir. `parameter_catalog.py` AMP durumunu kalibrasyon
eşlemesine ve kayıt ayrıntılarına bağlar; kapalı profili açık alıma uygulanmaz.
Testler: `test_live_ed_view_model.py`, `test_rx_survey.py`,
`test_fixed_band_verification.py`, `test_parameter_catalog.py`.

`DetectionSettings.qml` CFAR giriş sınırlarını ve birbirinden bağımsız alıcı/ses
taslaklarını denetler. `test_app_f_quick_product.py` gerçek QML'de katlanma,
virgüllü giriş ve geçersiz katsayı engelini sınar.
Alan yardımları ve görüntü değişiminde alıcı/ses taslaklarının korunması aynı
QML testinde denetlenir. Operatör başlangıç/değişim tablosu
`DETECTION_TUNING_AND_SOURCE_GUIDE.md` içindedir.
Mevcut dinleme yolunda `nfm_deemphasis_us` kısa ve sürekli işleme sonucuna bağlıdır;
`test_phase05_monitoring.py` aynı seçimin iki yoldaki etkisini doğrular.
Bu kayıt kaynak/sentetik kapsamındadır; RF doğruluğu, PHASE-08/ST-06 veya
parametre fiziksel kabulünü tamamlamaz.

## KTR-4.1 örnekleme hızı sunumu — 15 Eylül 2026

`quick_scan_actions.py`, fiziksel alıcı hızını oturum RX yapılandırmasından veya
tarama profilinin aynı alım sabitlerinden alır. `quick_view_model.py` bunu
`ÖRNEKLEME HIZI` altında tek değerle gösterir; hesaplamaların `sampleRateHz`
işleme anlamı korunur. `tests/test_live_ed_view_model.py` sabit izleme 8 MS/s,
bant taraması 10 MS/s ve 2 MS/s işleme ayrımını doğrular. Kaynak/ölçüm
performans değerlendirmesi mimari belgesindedir; fiziksel kabul artışı yoktur.

## KTR-4.1 sağlık denetimi ve tarama eylemi yarışı — 15 Eylül 2026

`quick_scan_actions.py`, kısa alıcı sağlık denetimiyle çakışan sabit/bant tarama
isteğini 50 ms aralıklarla denetim sonuna taşır. `HackRFControls.qml` sağlık
işçisinin iç durumunu düğme stiline bağlamaz. Kaynak regresyonunda 81 test;
düğme kararlılığı ve bağlantı kaybı için iki odaklı gerçek QML testi geçti.

## KTR-4.1 alıcı USB bağlantı kaybı — 15 Eylül 2026

`quick_view_model.py`, hazır ve boşta olan etkin tam HackRF seri kimliğini ayrı
işçi havuzunda periyodik denetler. Kimlik kaybolduğunda etkin seri, RX aracı ve
spur profili temizlenir; `hackrfReady=false` ile tarama kapanır.
`quick_runtime.py`, tarama başlangıcındaki `binary_pipe_failed` kodunu
`Alıcı bağlantısı koptu` ve `Sistemi Denetle` yönlendirmesine eşler.
`tests/test_live_ed_view_model.py` boşta kaybı ve ikili boru hatasını;
`tests/test_app_f_quick_product.py` gerçek QML'de sistem denetimi düğmesinin geri
gelmesini doğrular. İlgili tam koşular 79 ve 34 test geçti. Fiziksel tak-çıkar
tekrarı yapılmadığından KTR-4.1/ST-06 kabulü açık kalır.

## KTR-4.1 PortaPack USB hazırlığı ve veri hızı sunumu — 15 Eylül 2026

`quick_view_model.py`, görünür kayıtlı alıcıları rol önceliğiyle seçer:
`ED_RX_PRIMARY …36877e47`, yoksa `ED_RX_SECONDARY …35138247`. Seçilen tam seri
`quick_scan_actions.py` ve `quick_detection_state.py` üzerinden sabit frekans,
bant taraması, bağımsız aday doğrulama, dinleme ve yön ölçümüne taşınır; seri
değişiminde bilinen-spur profili de değişir. İki cihaz varsa birincil seçilir,
yapılandırılmamış cihaz kabul edilmez ve COM numarası kullanılmaz.
`tests/test_live_ed_view_model.py` yalnız ikincil bağlı fallback'i, iki cihazda
birincil önceliğini ve sabit/bant yollarına seri aktarımını doğrular. İlgili tam
regresyonlarda 76 görünüm-modeli, 33 QML ürün ve yedi HackRF arka uç testi geçti.
İkincil alıcıyla fiziksel tekrar yapılmadı; kabul kapısı açık kalır.

`platforms/acquisition/portapack.py`, yalnız PortaPack Mayhem USB-seri
`VID 1D50 / PID 6018` kimliği tekil bulunduğunda `hackrf` komutunu gönderir.
`quick_view_model.py`, bunu yalnız FPGA hizmeti hazır ve yapılandırılmış HackRF
henüz görünür değilken çalıştırır; yeniden bağlanan cihazı `ED_RX_PRIMARY` seri
numarasıyla doğrular. `tests/test_portapack_mode.py` yanlış/eksik/çoklu port ve
eksik yazma sınırlarını; `tests/test_live_ed_view_model.py` FPGA kapısını,
yeniden keşfi ve `8 MS/s → 2 MS/s` sunumunu doğrular. Gerçek QML kaynak sözleşmesi
`tests/test_app_f_quick_product.py`, ürün bağımlılığı
`tests/test_operator_product_boundary.py` ile izlenir. İlk fiziksel yeniden
bağlanmama sonrasında seri komut teslimine port temizleme ve 500 ms tüketme
aralığı eklendi; yedi regresyon geçti. Tek fiziksel koşuda `1D50:6018` CDC
aygıtı `1D50:6089` HackRF olarak yeniden bağlandı ve `…36877e47` seri numarası
doğrulandı. Hash bağlı kayıt
`results/evidence/phase08/portapack-usb-handoff-20260915.json` içindedir.
Tekrarlı gerçek QML düğmesi kabulü yapılmadığından KTR-4.1/ST-06 açık kalır.

## KTR-4.1 FPGA tespit kapasitesi tanısı — 15 Eylül 2026

`live_ed.py`, `dropped_candidates != 0` olduğunda kare, ham aday, etkin olay ve
alınamayan aday sayılarını kontrollü `candidate_drop` ayrıntısına yazar.
`quick_runtime.py` bunu `FPGA tespit kapasitesi aşıldı` başlığıyla sunar;
`quick_view_model.py` bu veri-kapasitesi hatasını bağlantı hazırlığını iptal
eden hata kümesinden ayırır. `tests/test_live_ed_session.py` sayısal tanıyı,
`tests/test_live_ed_view_model.py` hata sonrasında donanımın hazır kaldığını,
`tests/test_rx_survey.py` kapasite kaybının başarıya veya otomatik kazanç
değişimine çevrilmediğini doğrular.

## KTR-4.1 normal spektrum başlangıcı — 15 Eylül 2026

`HackRFControls.qml`, sabit frekans başlatmasında
`clearSpectrumViewHistory()` çağırır; alım ayarı ve kaynak durumu sinyalleri
tespit bandına otomatik `setSpectrumView()` uygulamaz. Gerçek QML regresyonu
`tests/test_app_f_quick_product.py` içinde önceden dar görünümü kurar ve
başlatmadan sonra tam `0..1` görünümü doğrular. Tespit bandı kılavuzu ve FPGA
işleme aralığı değişmemiştir.

## KTR-4.1 eksik canlı akış tanıları — 15 Eylül 2026

`platforms/acquisition/continuous.py`, erken EOF'ta alınan/beklenen kare
sayısını, `hackrf_transfer` dönüş kodunu ve son stderr tanısını koruyarak ham
alım `short_stream` kodunu üretir. `live_ed.py`, hata bildirmeden biten PC
zincirini `live_pipeline_short_stream`, eksik FPGA alışverişini
`fpga_short_stream` olarak ayırır. `quick_runtime.py` her kodu ayrı Türkçe
başlık ve kurtarma mesajına eşler. `tests/test_hackrf_continuous.py` alt süreç
tanısını; `tests/test_live_ed_session.py` FPGA/USB ayrımını;
`tests/test_app_f_quick_product.py` gerçek QML mesajını doğrular. Eksik kareli
oturum fail-closed kalır.

## KTR-4.1 sabit tarama eylemi yerleşimi — 15 Eylül 2026

`app/operator_console/qml/HackRFControls.qml`, `Taramayı Başlat` ve
`Taramayı Durdur` eylemlerini aynı `liveSessionActionSlot` içinde tutar.
`tests/test_app_f_quick_product.py` gerçek QML üzerinde boşta/çalışıyor durum
geçişini kurar; eylem yuvası ve ayarlar düğmesinin düşey konumlarının aynı
kaldığını, doğru eylemin görünür olduğunu doğrular. İşlev ve fiziksel kabul
sözleşmesi değişmemiştir.

## KTR-4.1 başlangıç kırpılma ayrımı — 15 Eylül 2026

`LiveEDConfiguration.startup_settling_frames`, sunulan karelerden ayrı ve
0–64 arasında sınırlı bir ham alım başlangıcı tanımlar. Operatör ürün yolları
sekiz kare kullanır. `LiveEDSession`, bu karelerle kanal seçiciyi hazırlar,
giriş/çıkış tam ölçek sayaçlarını `last_diagnostics` içinde ayrı tutar ve
FPGA'ya yalnız sıfırdan başlayan ölçüm karelerini gönderir. Alım süreci için
`MAX_CAPTURE_FRAMES`, 30 dakikalık `MAX_STREAM_FRAMES` üzerine yalnız 64
karelik kesin yerleşme payı ekler.

`tests/test_live_ed_session.py` başlangıçta kırpılmış/sonrasında temiz akışın
geçtiğini, FPGA'ya istenen sayıda ve `0..N-1` sıralı kare gittiğini; yerleşme
sonrası kırpılmanın yine `iq_saturation` ile durduğunu doğrular.
`tests/test_app_f_quick_product.py` gerçek QML başlatmasının sekiz karelik
ürün ayarını kullandığını, `tests/test_hackrf_continuous.py` genişletilmiş iç
alım üst sınırının hâlâ fail-closed olduğunu sınar. Fiziksel tekrar yapılmadı;
KTR-4.1/ST-06 kabulü açık kalır.

## KTR-4.1 sistem denetimi metinleri — 15 Eylül 2026

`HackRFControls.qml` ve `RxSurveyView.qml` ortak donanım denetimini `Sistemi
Denetle` etiketiyle sunar. `quick_runtime.py`, eşzamanlı HackRF/FPGA yokluğunu
başlık ve açıklamada `FPGA ve Alıcı algılanamadı` olarak eşler. Gerçek QML metin
sözleşmesi `tests/test_app_f_quick_product.py`, birleşik hata davranışı
`tests/test_live_ed_view_model.py` ile doğrulanır. `tests/test_live_ed_session.py`
I/Q kırpılmasının `iq_saturation` ile fail-closed kaldığını sınar.

## KTR-4.1 elle alıcı kazancı — 15 Eylül 2026

`app/operator_console/qml/HackRFControls.qml` LNA/VGA seçimlerini doğrudan
`startLiveEDSession` çağrısına aktarır; AMP aynı alıcı kartında seçilir ve ortak
RX yapılandırmasına taşınır.
Yönetimli kazanç slotu, alım seviyesi değerlendirme alanı, otomatik tekrar
durumu ve bunların hata kodları ürün kaynağından kaldırılmıştır. Gerçek QML
regresyonu otomatik kazanç nesnesinin bulunmadığını ve seçili kazançların canlı
konfigürasyona değişmeden ulaştığını doğrular. I/Q kırpılma reddi ayrı veri
bütünlüğü kapısı olarak korunur. PHASE-08/ST-06 fiziksel kabulü açık kalır.

## KTR-4.1 alıcı kazancı kontrol erişimi — 15 Eylül 2026

`app/operator_console/qml/AppCombo.qml`, uzun LNA/VGA seçeneklerini pencere
dışına taşırmak yerine sınırlı ve kaydırılabilir açılır görünümde sunar; mevcut
seçim açılışta görünür konuma alınır. `tests/test_app_f_quick_product.py` gerçek
QML üzerinde 62 dB seçimine erişimi, 280 piksel sınırını ve kaydırma konumunu
doğrular. Alıcı kazanç sözleşmesi ve donanım kabul durumu değişmemiştir.

## KTR-4.1 / KTR-4.2 sabit frekans kararlılığı — 14 Eylül 2026

`app/operator_console/quick_view_model.py` Qt işçilerini tamamlanma/hata sinyali
GUI'de tüketilene kadar saklar ve katalog işlerini ayrı, tek işçili havuza
aktarır. Aynı katalog bağlamındaki teslimler 500 ms pencerede birleşir.
`app/operator_console/parameter_catalog.py` bir GUI teslimini tek
SQLite işlemiyle yazar. `app/operator_console/automatic_parameter.py` ölçüme
alınmamış sonlanan olayları katalog sonucu değil telemetri sayacı yapar;
`live_ed.py` sayacı oturum tanısına taşır. Yaşam döngüsü, GUI'yi bloklamama,
toplu işlem ve olay sonu regresyonları sırasıyla
`tests/test_live_ed_view_model.py`, `tests/test_parameter_catalog.py` ve
`tests/test_automatic_parameter.py` içindedir; güçlü geniş olayda kazanç azaltma
ve ince düşük-seviye VGA artışı da görünüm modeli testleriyle bağlıdır. İlgili
küme 161 testte geçti.

`scripts/verify_fixed_frequency_gui_stability.py` gerçek QML, seri bağlı RX,
kart taşıması, Qt heartbeat, katalog ve kaynak SHA-256 değerlerini tek JSON'da
toplar. 16/14 dB 4.096-kare donma tekrarı ve 0/0 dB 2.048-kare parametre tanısı
`results/evidence/phase08/fixed-frequency-stability-20260914-after.json` ile
`fixed-frequency-stability-20260914-gain-zero.json` üzerinden izlenir. Nihai
otomatik kazanç ve toplu katalog koşusu
`fixed-frequency-stability-20260914-managed-batched.json` içindedir. İlkinde
GUI azami aralık `43,38 ms` ve USB taşması sıfırdır; ikincide 10 geçerli ölçüm
vardır; nihai otomatik koşuda 9 geçerli sonuç, sıfır USB taşması ve `48,68 ms`
azami heartbeat ölçüldü. Kart hızı nominal sürekli eşiğin altında, dBm kalibrasyonu yok ve
eşleştirilmiş negatif/Pd-Pfa eksiktir; KTR fiziksel kabulü ile ST-06 açık kalır.

## KTR-4.1 tarama hızı izlenebilirliği — 14 Eylül 2026

`scripts/measure_hackrf_rx_rates.py` seri numarasına bağlı, sınırlı ve yalnız
RX 8/10/20 MS/s tekrarlarını kaydeder. Fiziksel sonuç
`results/evidence/phase08/hackrf-rx-rate-observation-20260914.json` içindedir.
Güncel bağlı `…36877e47` alıcı `ED_RX_PRIMARY`, önceki `…35138247` alıcı
`ED_RX_SECONDARY` rolündedir; rol bağı
`config/p0/hackrf_ed_rx.json` ve `tests/test_hackrf_acquisition.py` ile izlenir.
`scripts/compare_rx_scan_profiles.py` aynı alıcı/aralıkta 128 kare, 64 kare ve
deneysel kaba profili özgün JSONL kayıtlarıyla karşılaştırır.

`platforms/acquisition/sweep.py` iki tam tur, sonlu CSV, seri bağı, iptal ve
sınırlı süreç çıktısını doğrular. `tests/test_hackrf_sweep.py` eksik/bozuk,
geçici aday, iptal, çıktı kesilmesi ve seçilmiş kart pencerelerini sınar;
`tests/test_rx_survey.py` mevcut örtüşme ve ikinci LO yolunu korur. Fiziksel
kaba profil hız kazanmadığından QML ürün seçeneği kaldırılmıştır.

10 MS/s algılama-only burst için `algorithms/p0/direct_frame.py` CI8'i
değiştirmeden çerçeveler. Python/C P0IQ sözleşmesi yalnız 2 veya 10 MS/s kabul
eder; 10 MS/s'de parametre isteğini reddeder. İzlenebilirlik
`tests/test_direct_p0_frame.py`, `tests/test_live_ed_session.py`,
`tests/test_p0_transport.py`, C11 taşıma testi ve 10 MS/s Linux köprü
loopback'iyle sağlanır. Ayrı P0CQ yetenek biti eski köprüde HackRF başlamadan
fail-closed davranışı, 256 kare sınırı ise tamponlu burst kapsamını doğrular.
ARM ikilisi seri porttan kimliği doğrulanan karta geçici yüklenerek üç 64/64
fiziksel koşuda sıfır USB/CRC/sıra/kuyruk hatasıyla geçti. Kalıcı köprü yeniden
başlatıldı. Kaynak ve ilk ret kaydı
`results/evidence/phase08/wideband-burst-host-gate-20260914.json`, tekrarlı
fiziksel ölçüm `results/evidence/phase08/wideband-burst-physical-20260914.json`
içindedir. Sayısal gürültü/ton hücre eşlemesi
`wideband-digital-mapping-20260914.json` ile; 67→16 pencere ve `3,817 s`
fiziksel tarama gözlemi `wideband-burst-scan-20260914.json` ile bağlanır.
Yayın-açık kör tekrarlar `wideband-burst-live-rf-run1/2-20260914.json[l]`,
iki taraflı analog yerleşim `wideband-burst-rf-placement-20260914.json`, kalıcı
SD/FIT yeniden başlatma `wideband-persistent-image-20260914.json`, 256-kare ürün
ve gerçek QML düğmesi koşuları `wideband-persistent-product-scan-20260914.json[l]`
ile `wideband-qml-live-scan-20260914.json[l]` üzerinden izlenir. Doğrulama
oturumunda otomatik parametre kapalıdır; `tests/test_rx_survey.py` her-kare ve
tespit-only sözleşmesini sınar. TX-kapalı negatif, genel Pd/Pfa, tam bant ve
elektrik kesip açılan soğuk başlangıç açık kalır; ST-06 tamamlanmadı.

## KTR-4.1–4.4 ED sürüm incelemesi — 13 Eylül 2026

KTR-4.1/4.2 için yavaş GUI'de otomatik parametre teslimi ve oturumlar arası
kalıcı kayıt `tests/test_live_ed_view_model.py` ile izlenir. Katalog bağlantı
kapatma/geri alma ve geçersiz kalibrasyon `tests/test_parameter_catalog.py`;
bozuk veritabanında başlangıç ve hata sunumu görünüm modeli testleriyle
doğrulanır. KTR-4.2 kaynak kimliği dosyalarının paketlenmesi ve KTR-4.1–4.4
ürün başlangıç sınırı `tests/test_operator_product_boundary.py` içindedir.
49 C/Python parametre senaryosu yeniden geçti. Donanım/algoritma kabul durumu
değişmedi; KTR-5.1–5.4 kapsam dışıdır.
[Bulgular ve test kaydı](../reviews/ED_RELEASE_REVIEW_20260913.md).

## KTR-5.1–5.4 kapsam kararı — 13 Eylül 2026

Kullanıcı kararıyla ürün yalnız ED sistemiyle devam eder. KTR-5.1–5.4 için
arayüz, uygulama/TX kaynakları, yapılandırma, yürütülebilir doğrulayıcı ve özel
test bulunmaz. Gereksinim kimlikleri kaynak KTR izlenebilirliğini kaybetmemek
için aşağıdaki tabloda tutulur; durumları `Kapsam dışı — kullanıcı kararı`dır.
Tarihli eski ADR ve ölçümler güncel kaynak kanıtı değildir.

## KTR-4.1 / KTR-4.2 otomatik paralel sonuç kataloğu — 13 Eylül 2026

Confirmed olaylar canlı P0IQ akışında güç sırasıyla seçilir; dört ardışık
80-bayt başlıklı istek aynı olay/niyet/aralıkla yerel ED ABI v2'ye çevrilir.
Her yanıtta tam temporal tespit tablosu da bulunduğundan parametre gözlemi
tespiti durdurmaz. Tek kart bağlamı, sekiz adaylık host kuyruğu, iki sahiplik
tekrarı, 512 hücre/FFT kenarı/komşu referans retleri ve eski köprüye güvenli
geri dönüş `tests/test_automatic_parameter.py`, `tests/test_p0_transport.py`,
`tests/p0/p0_iq_transport_test.c` ve Linux ağ köprüsü loopback'iyle izlenir.

Sonuç kataloğu `automatic-parameter-catalog-v1` SQLite şemasında oturum, alıcı
rolü/serisi, olay/niyet, merkez/alt-üst kenar/OBW/dBFS/SNR, durum/neden ve
kalibrasyon bağını saklar. Görünüm geçerli dBFS'i azalan sırada verir; CSV dışa
aktarımı vardır. `tests/test_parameter_catalog.py`, tekrar kayıt reddini,
sıralamayı ve tam alıcı bağlamı eşleşmeyen kalibrasyonda dBm üretilmediğini
doğrular. İkinci HackRF'nin rol/seri tanınması yazılımsal; eşzamanlı fiziksel RX,
güncel kart imajı ve gerçek-zaman hız kabulü açık olduğundan KTR fiziksel kabulü
kapanmaz. Güncel sınırlı donanım gözlemi, başarılı yazılım/C kapıları ve
sonuçsuz RF koşuları
`results/evidence/phase08/automatic-inline-parameter-diagnostic-20260913.json`
içinde tutulur.

## KTR-4.4 uyarlamalı iki taraflı lob taraması — 16 Eylül 2026

`algorithms/p0/adaptive_df.py` ilk doğrulanmış `0°` noktasından saat yönünde
15° adımlarla ilk lob dışı sınırı bulur; sonra `0°`a fiziksel dönüş talimatıyla
345°, 330°, … sırasını kullanarak ters sınırı arar. Hedefin görülmediği sınır
ölçümü başarısız sayılmaz; P0PM-v4 kilitli kanal gücü ve gözlem maskesi kayıtta
kalır. İki sınır arasındaki kaba tepe 5° adımlarla hassaslaştırılır ve tek
karşı-yön noktası 3 dB ön/arka kapısını besler.

`P0_AMPLITUDE_DF_ADAPTIVE_V2` en az sekiz farklı açı, 3 dB rakip tepe ve ön/arka
ayrımı, sabit alıcı/frekans bağı ve aynı-kare reddini uygular. İzlenebilir testler
`tests/test_adaptive_direction_sweep.py`, `tests/test_phase09_amplitude_df.py`,
`tests/test_live_ed_view_model.py`, `tests/test_phase09_df_protocol.py` ve
`results/evidence/phase09/amplitude-df-adaptive-numeric-v2.json` içindedir.
Doğrulanmış ZedBoard üzerinde sekiz hazır/ret P0DF ağ sahnesi de
`results/evidence/phase09/amplitude-df-board-protocol-v2.json` kaydıyla geçmiştir.
Çalışan hizmet geçici güncellenmiştir; fiziksel derece RMS ve kalıcı SD imaj
kabulü açıktır.

## KTR-4.4 kilitli kanalda eşik altı açı ölçümü — 16 Eylül 2026

İlk yön ölçümü seçili kanalı dört yeni confirmed gözlemle kilitler. Sonraki
açılarda aynı kanal ve alıcı bağı korunarak dört yeni ardışık kare, hedef olay
tespit eşiğinin altına inse de `P0PM-v4` kart kanal gücü ölçümüne alınır. Her
açıda aynı sabit kanalın sinyal + alıcı gürültüsü toplamı kullanılır; hedefin
görülmediği nokta yayın kanıtı değil, gürültü tabanıyla sınırlı güç örneğidir.
Yakın koruma
alanında başka, taşan veya birden çok gözlenen aday varsa kayıt yapılmaz.
Arşiv olay görünürlüğünü kare başına saklar; olay yokluğu yayın yokluğu veya
verici kimliği sayılmaz. İzlenebilirlik `tests/test_live_ed_session.py` eşik altı
kare/komşu retleri, `tests/test_board_parameter_measurement.py` P0PM-v4 ve Python
referans modeli, `tests/p0/p0_parameter_runtime_test.c` normal/yön kalite kapısı
ayrımı, `tests/p0/p0_ed_service_protocol_test.c` sürüm/CRC sınırı ve
`tests/test_live_ed_view_model.py` confirmed 0° ardından olaysız 15° kart ölçümü
ile kayıt tekrar denetimiyle sağlanır. PL FFT güç üretimi ve P0DF nihai karar
değişmemiştir. Fiziksel kart kanıtı normal yolun düz spektrumu reddettiğini,
P0PM-v4'ün aynı girdide sonlu kanal gücü ürettiğini ve altı normal parametre
sahnesinin gerilemediğini doğrular. Güncel hizmet/köprü 47007'ye geçici kuruldu;
SD imaj kalıcılığı ve fiziksel anten/RMS kabulü açıktır. Kanıt:
`results/evidence/phase09/p0pm-v4-direction-power-physical-20260916.json` ve
`results/evidence/phase09/p0pm-v4-runtime-deployment-20260916.json`.

## KTR-4.4 saat yönünde bağıl açı akışı — 13 Eylül 2026

PHASE-09 ürün arayüzünde ilk başarılı kayıt `0°`, sonraki kayıtlar otomatik
olarak saat yönünde 15° artan bağıl açılardır. Arayüz serbest açı, gerçek kuzey,
elle coğrafi kerteriz ve anten azimutu sunmaz. Tek ölçüm düğmesi yalnız uygun
dört kareli kanal gücü tamamlandığında bir sonraki açıya geçer; süre aşımı ve
iptal aynı açıda kalır. Düşük seviye manuel referans sözleşmesi tarihsel kayıt
uyumluluğu için korunur fakat ürün görünümüne bağlanmaz.

İzlenebilirlik `tests/test_live_ed_view_model.py` içindeki ardışık `0°/15°`
canlı kart ölçümü, `tests/test_app_f_quick_product.py` içindeki QML düğme/durum
ve kaldırılan coğrafi kontrol denetimleriyle sağlanır. DF sayısal/ARM yöntemi
değişmemiştir; fiziksel dönüş algılama, anten ve derece RMS kabulü açık kalır.

## KTR-4.2 / KTR-4.2-F1 sonuç ve doğrulama görünürlüğü — 13 Eylül 2026

`parameterRows` artık dört ana parametreye ek olarak kart ölçüm kalite kapısı,
gürültü referans farkı, tespit anlamlılığı, merkez kararsızlığı ve zamansal OBW
kenar değişimini taşır. `ParameterMeasurementPanel.qml` ana alanların durumunu
değer yanında gösterir, teknik doğrulamayı yeni sonuçta otomatik açar ve ret
nedenini aynı alanda sunar. `tests/test_live_ed_view_model.py` model değerlerini;
`tests/test_app_f_quick_product.py` gerçek QML görünürlüğü, başlangıçta açık
teknik bölüm ve gizle/göster davranışını doğrular. Toplam 94 ilgili test geçti.
Ekrandaki `GEÇERLİ` kart/profil kapısıdır; `accuracy_proven: false` ve açık
fiziksel RF kabul sınırı değişmedi.

## KTR-4.1 / KTR-4.2 / KTR-4.3 canlı ürün bağı — 13 Eylül 2026

Kontrollü laboratuvarda bildirilen `820 MHz` NFM ton yayını, gerçek kaynak
arayüzünde tespit edildi; iki P0PM-v2 parametre kaydı ve bir beş saniyelik NFM
dinleme sonucu üretildi. Dinleme kanalı artık değişken FPGA olay kimliğine
değil operatörün seçtiği RF frekansına bağlıdır. ARM `active` tablosundaki o
karede gözlenmeyen yaşam döngüsü kaydı ikinci yayın sayılmaz; aynı karede iki
gözlenen eşleşme belirsizlik olarak reddedilir. `%95` gözlem ve sekiz ardışık
eksik kare kapısı korunur.

İki parametre kaydında merkez `819,985633 / 819,962533 MHz`, OBW
`422,087 / 451,932 kHz`, güç `−31,340 / −28,193 dBFS` ve deneysel PC sınıfı
`Analog` oldu. Dinleme `2.442` toplam karenin `2.422` gözlenenini, üç kare
azami boşluğu ve `1,02301 kHz` baskın sesi kaydetti. Doğrulama kümesi 182
testte hatasızdır. Kanıt ve kaynak özetleri
`results/evidence/phase08/live-820mhz-e2e-product-20260913.json` içindedir.
Kayıtlar `accuracy_proven: false`, sınıflandırma
`product_acceptance: false` sınırlarını korur. Kör/negatif/gerçek konuşma ve
genel Pd/Pfa eksik olduğundan ilgili KTR'lerin tam fiziksel kabulü kapanmaz.

## KTR-4.2 / PÇ-03 otomatik Analog/Sayısal ayrımı — 12 Eylül 2026

Arayüz alt/üst MHz değeri bulunmadığında sessiz onay üretmez. Hatalı tepe
merkezli 512 hücreye kesme kaldırıldı. KTR-4.2 / PÇ-02/PÇ-04 kapsamında
kullanıcı sayısal PL/ARM hesabını koruyarak P0PM-v2 geniş aralık desteğini
onayladı. Tam aday korunur; 8–3984 hücre ve 389.376 bayt kalıcı ARM yükü
açık sözleşmedir. Eski host profilinin sınırları değiştirilmedi.
`tests/test_board_parameter_measurement.py`, `tests/test_live_ed_view_model.py`,
`tests/p0/p0_ed_service_protocol_test.c`, `scripts/verify_p0_parameter_runtime.py
--extended --wide` ve `scripts/verify_p0_wide_parameter_record.py` sınır,
sahiplik, kayıt-tekrar ve sayısal eşdeğerlik bağını korur. 49 portable kontrol
geçti; kart kimliği ve hash bağlı yükleme, altı dar regresyon ve bir gerçek
kayıtlı geniş P0PM-v2 ölçümü geçti. PC sınıflandırıcısı geniş sentetik kapıyı da
geçti; canlı karar deneysel kalır. Arayüz kısmi/başarısız sonucu ve nedenleri ayırır.

`Parametreleri Çıkar` aynı dört CI8 kare üzerinde iki açıkça ayrılmış yürütüm
üretir: taşıyıcı/OBW/güç/SNR için ZedBoard PL/ARM P0PM ve Analog/Sayısal için
PC `domain.digital-analog-logreg-pc-v1`. PC sonucu model/source SHA-256,
özellik sırası/değerleri, sayısal olasılık, `%90` güven kapısı ve
`physical_acceptance: false` / `product_acceptance: false` sınırlarıyla kayıtlıdır.
SNR 4 dB altında, örnekleme 2 MS/s dışında, enerji yoksa veya güven kapısı
geçmezse kesin sınıf yerine `Belirsiz` yayımlanır. FPGA/ARM sınıflandırma
değişikliği yoktur. Birim, kayıt-tekrar, kart ayrımı ve QML görünürlüğü testleri
PÇ-03 izlenebilirliğini sağlar; bağımsız canlı RF kabulü açıktır.
[Güncel geliştirme kanıtı](../../results/evidence/phase08/automatic-domain-pc-wide-guard-20260912.json)
`scripts/verify_automatic_domain_integration.py --check` ile kaynak özetleri de
dahil yeniden doğrulanır.

## KTR-4.4 kanal bağlı yön ölçümü — 12 Eylül 2026

PHASE-09: seçilen kanal ve alıcı ayarı korunur; her açı isteğinden sonra dört
ardışık, izole confirmed kanal gözlemi alınır. Gerçek olay numaraları ayrı
kaydedilir; kimlik değişimi verici özdeşliği sayılmaz. Süre aşımı, iptal,
komşu aday, eski kare ve ayar değişimi retleri yazılım testleriyle denetlenir.
P0PM PL/ARM güç ve P0DF nihai karar yöntemleri değişmedi. Fiziksel RF/RMS kapısı
açıktır. [Sözleşme ve test bağı](../interfaces/SIGNAL_DIRECTION_FINDING_STATUS.md).

## KTR-4.2 kalıcı kart yolu ve matematik sınırı — 11 Eylül 2026

PÇ-04 ürünü PetaLinux 2025.2 SD imajına alındı. Dört yeniden başlatmada FPGA,
DMA modülü, ARM ED hizmeti ve ağ köprüsü otomatik açıldı; cihaz ağacı kontrol
düğümü, 4096 varsayılan profil ve altı PL→ARM sayısal sahne doğrulandı. 33 C↔F5
eşdeğerlik sahnesi uygulama sadakatini gösterir. Bağımsız 30 uzun kayıt güçte
30/30 geçerli ve en çok 0,189 dB hata verdi; merkezde 10,209 kHz, tam emisyonu
kapsamayan BPSK OBW'sinde 325,644 kHz'e varan hata korundu. dBm kalibrasyon
yoksa üretilmez. Bu sonuçlar canlı RF frekans/OBW doğruluğunu kapatmaz.
Kanıt: `parameter-persistent-image-20260911.json`,
`parameter-board-persistent-20260911.json`, `parameter-math-audit-20260911.json`
ve `parameter-obw-containment-audit-20260911.json`. Son kapsama denetimindeki
16.384 örnekli aday altı aralık dışı BPSK sonucunu da tuttu, ancak 12 dB'deki
diğer ailelerde de OBW kapsamını sıfıra indirdiği ve ARM eşdeğerliği olmadığı
için ürün kabulü yapılmadı.

## KTR-4.2 ilk üç parametrenin kart yolu — 11 Eylül 2026

PÇ-02/PÇ-04: taşıyıcı frekansı, emisyon merkezi, OBW %99 ve kalibre edilmemiş
kanal gücü artık canlı ürün ölçümünde PC kestirimcisine değil fiziksel PL güç
karelerini kullanan ZedBoard ARM çekirdeğine bağlıdır. Sinyal türü ertelenmiştir.
`P0PM-v1` istek/yanıtı dört CI8 karenin CRC'sini, ölçüm kimliğini, olay kimliğini,
kare aralığını ve FPGA profil kuşağını bağlar; hata halinde host fallback yoktur.

33 host C eşdeğerlik sahnesi ve altı gerçek PL→ARM sayısal sahne geçti. Fiziksel
sayısal azami hata merkez/taşıyıcı/kenar/OBW için 0,00691/0,00093/0,02057/0,02042
Hz; dBFS/SNR için 0,000049/0,000100 dB'dir. CRC reddi, profil değişmezliği ve
normal tespit öncesi/sonrası DMA durumu doğrulandı. Kanıtlar:
`results/evidence/phase08/parameter-carrier-equivalence-20260911.json`,
`parameter-board-integration-20260911.json` ve
`parameter-arm-state-calibration-20260911.json`.

Bu KTR'nin gerçek RF doğruluk, dBm kalibrasyon, frekans referansı ve canlı
HackRF/GUI dayanıklılık kapıları açıktır. Kalıcı imajın soğuk açılışı üstteki
güncel kayıtla geçmiştir; sayısal eşdeğerlik kalan kapıları veya saha
doğruluğunu kanıtlamaz.

## Tespit ayarları arayüzü — 11 Eylül 2026

KTR-4.1-OPS-B0: tespit ve spektrum kontrolleri iki gruba ayrıldı; kısa teknik adlar ve büyük panel başlığı kullanıldı. Ayar uygulama/geri okuma ve doğrulayıcılar korunur. Sunum değişikliği fiziksel RF kabulü değildir.


KTR-4.1 / KTR-4.1-OPS-B0 çalışma zamanı katsayı zinciri:
`tests/test_cfar_runtime_config.py` model/RTL karar eşitliği, geçersiz istek,
geri okuma, kare yalıtımı, geri basınç ve reseti denetler. AXI, sürücü, ARM
hizmeti ve arayüz bağlantısı fiziksel kartta geçti. Varsayılan/hassas/geri
yüklenmiş ham aday toplamı 33/862/33; üç 4.096 karelik hız koşusunun en düşüğü
507,587 kare/s, gereken 488,281 kare/s'dir. CRC/sıra/kuyruk/DMA/düşüm sıfırdır.
Kanıt `results/evidence/phase08/st06-runtime-config-physical-20260910-v3.json` ve
ZIP'tedir. Bu KTR'nin kontrollü RF Pd/Pfa ve soğuk açılış kapıları açıktır;
eski derleme kanıtı yeni RTL'ye taşınmaz.
[Sözleşme](../interfaces/DETECTION_RUNTIME_CONFIG_CONTRACT.md).

KTR-4.1 değişken FPGA FFT kanıtı: 4096/8192/16384 seçim kodları 12/13/14,
uzunluğa bağlı periyodik Hann, dinamik XFFT, güç/CFAR, DMA ABI v3, ARM hizmet
ABI v4 ve arayüz geri okuması birlikte uygulanmıştır. Tam tasarım 50 MHz'te
WNS `+0,613 ns`, WHS `+0,030 ns` ve sıfır yönlendirme hatasıyla geçti. Her
uzunluk üç bağımsız 4.096-kare fiziksel sayısal koşuda hedef hızını geçti;
en düşük gerçek zaman marjları sırasıyla `%10,609`, `%2,388`, `%13,148` oldu.
Kart ve yerel bitstream/modül/hizmet/köprü hash'leri eşleşti. Daha sonra
post-downshift veri işleme hatası bulundu; güncel sürücü aynı açılışta küçültmeyi
reddeder ve yeniden başlatma 4096'a döndürür. Kanıt:
`results/evidence/phase08/st06-runtime-fft-physical-repeated-20260911.json` ve ZIP.
Kalıcı imaj/dört yeniden başlatma `parameter-persistent-image-20260911.json`
ile geçti. HackRF RF Pd/Pfa kapısı açıktır.

## KTR-4.1 ayar ve zayıf yol bağlantısı — 10 Eylül 2026

ST-06 / KTR-4.1-OPS-B0 ayarları `DetectionSettings.qml`, gerçek oturum
yapılandırması ve SurveyConfig’e bağlıdır. `test_detection_settings.py`
görüntü FFT’sinin tespit spektrumunu koruduğunu; `p0_weak_power_run.c`
güç/çözülmüş giriş eşitliğini, zayıf doğrulamayı, sıra kesintisini, sönmeyi
ve eski biçimi denetler. `check_st06_weak_power_rtl.py` 49.152 v2 DMA
kelimesini referansla karşılaştırır. Güncel ikiliyle fiziksel sayısal kontrol
ve sürekli hız geçti; HackRF/RF Pd/Pfa ve soğuk açılış kabulü açık kalır.
[Ayar ve kaynak kılavuzu](../interfaces/DETECTION_TUNING_AND_SOURCE_GUIDE.md).

`verify_st06_weak_power_build.py` yerleştirme/zamanlama, XSA/bitstream
eşliği, ARM ve test kaynak hash'leri ile 4.096 karelik geri alma testini
birleştirir. Kanıt: `results/evidence/phase08/st06-weak-power-20260910.json`.

## KTR-4.1 → KTR-4.2 seçim aktarımı — 10 Eylül 2026

Bant taramasında seçilen frekans, KTR-4.2 parametre girişine canlı yeniden
alım üzerinden bağlandı. Eşleşen güncel FPGA adayı ve dört ardışık ölçüm karesi
oluşmadan Parametre görünümüne geçilmez. `test_survey_parameter_action_...`,
mevcut bant taraması durum testi ve QML düğme testi 3/3 geçti. Bu yalnız ürün
akışı kanıtıdır; RF doğruluğu, Pd/Pfa, dBm kalibrasyonu ve fiziksel KTR-4.2
kabulü açık kalır.

## Dört parametrenin gerçek RF durumu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: yeni temiz AM koşusunda dar aralık SNR'si
13,36–15,32 dB iken sabit aday 10/10 Belirsiz kaldı. Yeni `rf_observation`
ürün dışı ön işlemesi uzun I/Q, FIR kanal süzme ve frekans kayması
hipotezlerini uygular; kesin sınıflandırıcı değildir. Kullanılabilir donanım
son beyana göre yalnız iki HackRF'dir; dBm kalibrasyonu diğer işleri durdurmaz.
Ürün/ARM/RTL ve önceki kabul durumları değişmedi.

§5.1.2'nin dört alanı için durum ve kanıt ayrı tutulur. `parameter-rf-readiness-20260909`
üç eski gerçek kaydı; `parameter-am-linkcheck-20260909` yeni AM'yi;
`parameter-bpsk-linkcheck-20260909` eşleşmemiş BPSK alıcı penceresini;
`rf-observation-records-20260909` dört gerçek kayıttaki ön işlemeyi hash bağlı
saklar. Tam RF OBW/kalibre frekans/dBm veya sınıf doğruluğu kapatılmadı.

[Ayrıntılı durum, araştırma ve yeniden üretim](../reviews/PARAMETER_EXTRACTION_ASSESSMENT.md).


## Replay BPSK G8 tanı koşusu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı `03_BPSK.C16` için Play teyidi verdi.
RX 24/24 dB kaydında 20,35–26,20 saniye arasında 5,90 saniyelik hedef bant
etkinliği görüldü. Bu süre RF öncesi hazırlanan 6 saniyelik BPSK dosyasıyla
uyumludur. Kayıtta bir USB taşması bulunduğu için koşu kabul paydasına alınmadı.

Dondurulmuş PC adayı 1,32–4,70 dB SNR nedeniyle 10/10 `low_snr` Belirsiz
üretti. AM, NFM ve BPSK fiziksel kayıtlarının aynı kalite kapısında kalması,
sorunun tekrar sayısından çok adayın gerçek Replay veri alanı ve SNR tanımıyla
uyumsuz olduğunu gösterir. Aynı koşu körlemesine tekrarlanmaz; yöntem ayrı
geliştirme verisiyle düzeltilip yeni kör RF ile sınanmalıdır. Ürün, fiziksel
analog/sayısal kabul ve dBm kalibrasyonu açık. Kanıt:
`results/evidence/phase08/replay-bpskg8-diagnostic-20260909.json` ve ZIP.

## Replay NFM G8 fiziksel tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: `02_NFM.C16` için RX 24/24 dB kaydı tam boyutta,
sıfır USB taşması ve sıfır kırpılmayla alındı. Faz ayrıştırıcı 1702,88 Hz
tepe ölçtü; RF öncesi hazırlanan dosyanın mesaj tonu 1700 Hz'dir. Çizgi
etkinliği yalnız kaba zaman seçimi için kullanıldı ve 21,50–27,25 saniye
aralığını işaretledi. NFM taşıyıcı bastırması nedeniyle bu işaretler güç veya
bant ölçümü olarak yorumlanmadı.

Dondurulmuş PC adayı, önceki temiz CW merkezi ve RF öncesi manifest aralığıyla
incelenen on pencerede −2,33 ile +0,99 dB SNR buldu; 10/10 sonuç `low_snr`
nedeniyle Belirsiz kaldı. Fiziksel NFM içeriği gözlendi, fakat analog/sayısal
sınıflandırma kabulü geçmedi. Model ve eşik bu kayıtla değiştirilmedi. Ürün F5,
ARM/FPGA, dBm kalibrasyonu ve genel fiziksel kabul açık. Kanıt:
`results/evidence/phase08/replay-nfmg8-evaluation-20260909.json` ve ZIP.

## Replay AM G8 ve aralık tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı AM G8 hazırlığını bildirdi; RX 24/24 dB
kapalı ve açık kayıtları tam boyutta, sıfır taşma/kırpılmayla alındı. Açık
kayıtta 6,15 saniyelik tek etkin bölüm ve 1699,22 Hz zarf tonu, hazırlanan
6 saniye/1700 Hz AM dosyasıyla uyumludur. Ayrı Play yanıtı kayda ulaşmadı;
TX Gain 8 ekran fotoğrafıyla doğrulanmadı. Sabit nominal 98,1 kHz aralıkta
10/10 sonuç 1,72–3,89 dB SNR nedeniyle Belirsiz kaldı.

Koşu sonrası tanıda aralık gözlenen 824990308 Hz çevresine taşındı. 8,3–16,1
kHz aralıklarda on pencerenin kalite kapısı geçti ve SNR 7,80–13,93 dB oldu;
Analog skor 0,64–0,83 ile sabit 0,90 eşiğin altında kaldı, 10/10 Belirsiz.
Bu sonradan yapılan aralık taraması kabul paydasına alınmaz. Bulgular seviye
ve aralık sorununun yanında gerçek Replay AM için model genelleme açığı
olduğunu gösterir; model/eşik bu kayıtla değiştirilmedi.

Sonraki aileler aynı sabit modelle değerlendirilir; gelecekteki yöntem
geliştirmesi ayrı sayısal veriyle yapılır ve yeni kör RF gerekir. Ürün F5,
ARM/FPGA, dBm ve genel fiziksel kabul açık. Kanıt:
`results/evidence/phase08/replay-amg8-evaluation-20260909.json` ve ZIP.


## Replay AM 32/32 dB karşılaştırması — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: verici kapalı 10 saniye ve AM penceresi RX 32/32
dB'de tam boyutta, sıfır taşma ve sıfır kırpılmayla alındı. AM kaydında
1699,22 Hz zarf tonu hazırlanan 1700 Hz dosyayla uyumludur; Play basışına
ait ayrı operatör yanıtı kayda ulaşmadı. Sabit aday on pencerenin tamamında
−9,09 ile +0,70 dB SNR ve `low_snr` nedeniyle Belirsiz kaldı. RX kazancını
24/24'ten 32/32 dB'ye çıkarmak aday SNR'sini iyileştirmedi; alıcı kazancı
daha fazla yükseltilmez.

Model/eşik değiştirilmedi. En düşük TX kazançta taşmasız CW bağlantısı
görüldüğünden sonraki kontrollü aday, Amp kapalı ve TX Gain 8 ile AM tekrar;
RX yeniden 24/24 dB'dir. Bu güç kalibrasyonu değildir. Verici kimliği,
genel fiziksel kabul, dBm ve ürün/ARM/FPGA kapıları açık kalır. Kanıt:
`results/evidence/phase08/replay-am32-evaluation-20260909.json` ve ZIP.


## Replay AM 24/24 dB değerlendirmesi — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: operatör doğru `01_AM.C16` dosyasını seçip Play'e
bastığını bildirdi. 825,3 MHz, 8 MS/s, RX 24/24 dB kaydı tam boyutta;
USB taşması ve kırpılma sıfırdır. Ayrı zarf tanısı 1699,22 Hz tepe buldu;
hazırlanan 1700 Hz AM mesajıyla uyumludur. Sabit v6 model/v9 adayın on
penceresi 2,04–4,38 dB ölçüm SNR'sinde 10/10 `low_snr` nedeniyle Belirsiz
kaldı. Bu fiziksel AM sınıflandırma kapısını geçmez; eşik/model değiştirilmedi.

Tek yayın kaydının on penceresi bağımsız on RF koşusu değildir. Verici seri
kimliği açık, dBm ve mutlak frekans kalibrasyonu yoktur. Ürün F5, ARM ve FPGA
kullanılmadı. Önceki yanlış dosya olasılıklı kayıt AM paydasına alınmaz ve
özgün tanısıyla korunur. Sıradaki kontrollü adım daha yüksek RX kazancında
kırpılma ve sınıflandırma kontrolüdür. Kanıt:
`results/evidence/phase08/replay-am24-evaluation-20260909.json` ve ZIP.


## Replay CW taşmasız gözlem — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı USB portunu değiştirip alıcıyı HackRF
moduna aldı. Aynı seri 35138247, 825,3 MHz, 8 MS/s ve 24/24 dB'de
10 saniyelik kapalı ve 30 saniyelik CW penceresi tam boyutta, sıfır taşma
ve sıfır kırpılmayla alındı. Kullanıcı Play basıldığını bildirdi. CW
824989819 Hz çevresinde 43/598 tanı penceresinde görüldü; sonrasında
öneklenen seviye eşik altına indi. 50 ms adımlı görünür aralık yaklaşık
2,15 saniyedir; hassas RF süre kalibrasyonu veya acil Stop testi değildir.

Tek temiz kayıt kalıcı USB çözümü sayılmaz; araç hâlâ aynı yolda dört
başka cihaz bildiriyor. Eski taşmalar korunur. AM denemesi öncesi kaynak
seçimi ve alıcı kayıt eşlemesi gerekir. Model/ürün/RTL/ARM değişmedi;
fiziksel genel kabul, verici kimliği ve dBm kalibrasyonu açık kalır.
Kanıt: `results/evidence/phase08/replay-cw-clean-20260909.json` ve ZIP.


## Replay USB karşılaştırması — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: 8 MS/s, RX 24/24 dB, 825,3 MHz ayarında
verici kapalı beş saniyelik depo kaydı 1 taşma; yerel geçici klasörde
beş saniyelik kapalı kayıt 0 taşma verdi. Aynı yerel yoldaki 30 saniyelik
CW denemesi 3 taşma (en uzun 16876896 bayt) verdi. Üç kayıt tam boyutta
ve kırpılmasızdır; tam boyut süreklilik değildir. Kullanıcı Play basıldığını
bildirdi; 598 tanı penceresinde hedef artışı yok, kesin basış zamanı bilinmiyor.
Bu sonuç verici başarısızlığı veya kalibre RF yokluğu sayılmaz.

OneDrive dışına yazmak tek başına çözüm olmadı; kök neden kanıtlanmadı.
HackRF aracı aynı USB yolunda dört başka cihaz bildiriyor. Sonraki adım
alıcı USB bağlantısını doğrudan farklı bağlantı noktasında sınamak; yeni RF
denemesinden önce kapalı süreklilik kontrolüdür. Ürün/model/RTL/ARM değişmedi.
Kanıt: `results/evidence/phase08/replay-usb-comparison-20260909.json` ve ZIP.
Geçici klasörlerdeki ham kayıtlar da arşive alındı; önceki başarısızlıklar korunur.


## Replay CW gözlendi; USB sürekliliği başarısız — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: hazır bildirimi ardından alınan 24/24 dB kayıtta
824989697 Hz çevresinde 43/598 tanı penceresi eşik üstündedir; ardından
öneklenen seviye eşik altına iner. Ham dosya tam boyutta ve kırpılmasızdır,
ancak araç günlüğünde 3 USB taşması, en uzun 4527552 bayt vardır. Önek
indislerinden görünen yaklaşık 2,15 saniye kesin RF süresi sayılamaz.
CW bağlantı gözlemi vardır; otomatik durdurma/süreklilik kabulü kapanmadı.
`capture.json complete` yalnız boyut/çıkış kodu kontrolüdür.

Önceki 24/24 penceresinde kullanıcı mesajı geç gördü; o negatif kayıt TX
başarısızlığı değildir. Fotoğrafta CW, 825 MHz, 500 kHz, G:0/A:0 ve Loop
kapalı görüldü. Model/ürün/RTL/ARM değişmedi; dBm ve mutlak frekans açık.
Sonraki koşu süreklilik tanısı çözülerek kısa eşzamanlı kayıttır.
Kanıt: `results/evidence/phase08/replay-cw-detected-20260909.json` ve ZIP.


## Replay CW ilk fiziksel tanı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: 825,3 MHz merkez, 8 MS/s, RX 16/16 dB'de
bir saniyelik kapalı kayıt ve iki 30 saniyelik alıcı penceresi alındı.
Operatör ilk 2 saniyelik CW dosyasının kendiliğinden durduğunu, ikinci
denemede Play'e bastığını bildirdi. İki kayıtta 825 MHz ±50 kHz çevresinde
kapalı q99 +6 dB tanı eşiği üstünde 0/598'er pencere bulundu. Bu, hiç RF
yayınlanmadığının kanıtı değildir; Play anı cihaz zamanıyla bilinmiyor.
Üç ham kayıt tam boyutta, yerleşmiş alımda kırpılma sıfırdır.

Alıcı seri sonu 35138247 ve v2.4.0 cihazdan okundu. Verici sürümü yalnız
“alıcıyla aynı” kullanıcı beyanıdır; seri ve gerçek Replay ekran ayarı
doğrulanmadı. CW/otomatik RF durdurma kabulü kapanmadı; sonraki adım ekran
ayarını doğrulamak, ardından gerekli eşleşmiş alıcı denemesidir. Sayısal
yayınlara geçilmedi; model/ürün/RTL/ARM değişmedi, dBm kalibrasyonu açık.
Kanıt: `results/evidence/phase08/replay-cw-initial-attempts-20260909.json`
ve ZIP; ham I/Q, günlük, komut ve tanı kaynakları korunur.


## PortaPack Replay kaynak hazırlığı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcının SD kartla bağımsız verici kullanma
talebi üzerine 825 MHz nominal merkezli, 500 kS/s C16/TXT paketi hazırlandı.
CW 2 saniye; AM/NFM/BPSK/QPSK/FSK altışar saniyedir. Sayısal aileler ayrı
sabit tohumlu rastgele veri taşır. Üretici sınıflandırıcıyı çağırmaz; model,
ürün F5, RTL ve ARM değişmedi. İlk paket CW referansında DC çıkarımı hatası
nedeniyle teslim edilmedi; v2 sonlu referans kontrolünü ve altı testi geçti.

Dosya bitleri ve süreleri doğrulandı; RF gönderilmedi, SD oynatma henüz
sınanmadı. Kullanıcı iki HackRF ile devamı seçti. Bildirilen yaklaşık
XDG2060/60 MHz üreteç ve osiloskop 825 MHz mutlak kalibrasyon kanıtı değildir;
dBm kapalı kalır. İlk adım verici kapalı alım, ardından tek 2 saniyelik CW
ve durdurma kontrolüdür. Ayarlar/sürüm/kimlik kaydedilmeden RF kabulü yapılmaz.
Talimat: `docs/plans/PARAMETER_REPLAY_LAB_GUIDE.md`.
Kanıt: `results/evidence/phase08/parameter-replay-preparation-20260909.json`
ve ZIP. Açık fiziksel sınıflandırma, kalibrasyon ve ürün kapıları korunur.


## Ayrı üreticiyle sınıflandırma kontrolü — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: sabit v6 model baytları ve v9 aday yöntemi,
eğitim üreticisinden ayrı `validate_candidate_numeric.py` dalga biçimleriyle
sınandı. 26000000 kök tohumda AM/NFM/FSK/BPSK/QPSK ailelerinin her birinde
24/24 doğru kesin karar; CW 24/24 Belirsiz. Toplam 144 SNR varyantı,
48 dalga biçimi tohumu vardır; 144 bağımsız yayın değildir. Protokol ve
model özeti sonuçtan önce kaydedildi; model/eşik değiştirilmedi.

Yeni `scripts/validate_candidate_classification.py` aile ve SNR bazında
doğru/yanlış/Belirsiz, karar kapsamı ve kesin karar doğruluğunu raporlar;
başarısız sayısal kapıda başarısız çıkış kodu verir. İlgili 11 test geçti.
Bu sınırlı sayısal sonuç fiziksel BPSK/QPSK kabulünü kapatmaz; OOK/QAM,
gerçek alıcı bozulmaları ve kapsam dışı aileler bu koşuda sınanmadı.
Ürün F5, RTL ve ARM değişmedi; aday ürün dışındadır. Doğrulanmış sayısal RF
kaynağıyla fiziksel kontrol, kalibrasyon ve ürün kabulü açık kalır.
Kanıt: `results/evidence/phase08/parameter-independent-classification-20260909.json`
ve ZIP; model, protokol, tam sonuçlar ve kaynaklar hash bağlıdır.


## Parametre çalışmasına devam — 9 Eylül 2026

Kullanıcının 5.1.2 kapsamındaki devam talebiyle KTR-4.2 / KTR-4.2-F1
adayının sayısal doğrulaması sürdürüldü. Yöntem değiştirilmeden 25000000
kök tohumlu 168 önekte 96/144 desteklenen bant sonucu üretildi; 96/96
mevcut toleransı geçti. Desteklenen 48 düşük SNR öneğinde ve aralık dışı
24/24 dikdörtgen BPSK öneğinde OBW verilmedi. SNR varyantları bağımsız
yayın değildir. Sayısal güç mutlak hatası en çok 0,184 dB; bu dBm
kalibrasyonu değildir. İlgili aday/tanı testleri 10/10 geçti.

Ürün F5 ve aday yöntemi değişmedi; aday ürün dışındadır. Dört parametrenin
yarışma koşullarında birlikte doğruluğu henüz kanıtlanmadı. Sonraki açık iş,
ayarları doğrulanmış rastgele verili sayısal RF kaynağıyla sabit modelin
bağımsız kontrolü; frekans ve güç için kalibre referans karşılaştırmasıdır.
Ürün profili/ARM entegrasyonu ve fiziksel ürün kabulü ayrıca açıktır.
Bu devam kaydı sonraki fazı açmaz veya önceki başarısız RF sonuçlarını kapatmaz.
Kanıt: `results/evidence/phase08/parameter-numeric-continuation-20260909.json`
ve ZIP; çalıştırma komutu, kaynak özetleri ve tam sayısal sonuçlar korunur.


## QPSK ve kaynak dalga biçimi tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: 825 MHz QPSK beyanıyla 24/24 ve 32/32 dB'de
ikişer sonlu RX kaydı alındı. Dört kayıttaki 40 pencere kalite kapısını
geçti, 40/40 Belirsiz kaldı; model değiştirilmedi, ürün kabulü yapılmadı.
Mayhem upstream `31b25a445b166b13101ea4c6546f78b84dcc6499` incelemesinde
BPSK sabit 0–1, QPSK sabit dört sembollü döngüdür; Shape kullanılmaz.
BPSK ve kare mesajlı DSB'nin 256 faz adresindeki I/Q önekleri aynıdır.
Bu önekte yalnız menü etiketiyle farklı kesin Analog/Sayısal karar
beklenemez; Belirsiz tek başına algoritma hatasını kanıtlamaz. Bu bulgu
önceki başarısız RF kapsamını başarıya çevirmez. Rastgele verili sayısal
kaynak kabulü ayrıca açıktır. Ham RF çizgi aralıkları yaklaşık 2 kHz ton
hipoteziyle uyumludur; yüklü verici sürümü ve ayarı doğrulanmış değildir.
Güçlü yan çizgi taşıyıcı referansı sayılamaz. Güncel üretim F5 değişmedi;
ARM/FPGA ürün kabulü ve kalibre dBm açık kalır. Tanı komutu:
`python scripts/diagnose_siggen_reference.py --output <yeni-rapor.json>`.
Kanıt: `results/evidence/phase08/parameter-qpsk825-source-diagnostic-20260909.json`
ve ZIP (21 dosya hash doğrulaması); BPSK ham kayıtları önceki BPSK arşivindedir.

## 825 MHz BPSK fiziksel değerlendirme — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: kullanıcı BPSK yayınının açık olduğunu ve Shape
alanının ayarlanamadığını bildirdi. Pseudo Noise seçilmiş sayılmaz;
sembol hızı ve bit dizisi bilinmiyor. Önceki talimattaki 825 MHz/TX Gain 0/
Amp 0 cihazdan geri okunmuş ayar değildir. İki alıcı merkezinde 16/16,
24/24 ve 32/32 dB kazançlarla altı adet 0,5 saniyelik ham RX kaydı alındı.
16/16 ve 24/24 toplam 40 pencere düşük SNR kapısında kaldı; 32/32 dB'de
20 pencere kalite kapısını geçti fakat 20/20 sınıf Belirsiz kaldı.
Analiz edilen yerleşmiş bölümlerde kırpılma yok. Sayısal sınıflandırma
fiziksel kabulü başarısız; model/eşik değiştirilmedi. Farklı aralıklarla
sonradan yapılan tanılar bağımsız kabul koşusu sayılmaz. FPGA kullanılmadı.
Kanıt: `results/evidence/phase08/parameter-bpsk825-evaluation-20260909.json`
ve ZIP. Bu kullanıcı etiketli fiziksel kaynak kontrolüdür; üretici
uygulaması ve bağımsız modülasyon referansı ayrıca doğrulanmalıdır.


## Yeni 825 MHz AM değerlendirmesi — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: model/eşik değiştirilmeden 825 MHz, AM %100,
2 kHz sinüs kaynak ayarında iki merkez ve iki kazançta dört RF kaydı
alındı. 16/16 dB'de 20/20 düşük SNR reddi, 24/24 dB'de 10/20 Analog
ve 10/20 Belirsiz; yanlış Sayısal sıfır. Yeni koşul %80 karar kapsamını
geçmedi. İki yüksek kazanç kaydında zarf tonu 2000,14 Hz gözlendi.
Pencereler bağımsız RF koşuları sayılmaz; FPGA ve ürün yolu kullanılmadı.
Sınıflandırma genel kabulü açık; başarısız koşul model eğitimine eklenmedi.
Kanıt: `results/evidence/phase08/parameter-am825-evaluation-20260909.json`
ve ZIP. Sayısal aileler yalnız sentetik testlerde; fiziksel OOK/FSK/PSK/QAM,
farklı hızlar ve kapsam dışı yayın kabulü açık kalır.


## Bant kapsamı adayı v9 — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: aralık dışı enerji her uçta %0,5, Hann varyansı
ve ayrı gürültü bölgeleriyle denetlenir. Ayrı 168 sayısal önekte 96
geçerli OBW toleransı geçti; 48 desteklenen düşük SNR öneğinde ret,
24/24 aralık dışı emisyon öneğinde ret vardır. Genel kabul değildir.
800 öneğin sınıf kararları değişmedi; eski RF AM 16/20, FM 20/20 Analog.
28 test geçti. Aday ürün dışındadır; ARM ve fiziksel ürün kabulü açık.
Kanıt: `results/evidence/phase08/parameter-band-containment-v9-20260909.json`
ve ZIP. Ayrıntı: `docs/plans/PARAMETER_REFINEMENT_PROTOCOL.md`.
Önceki v7/v8 hataları tarihsel sonuçlarıyla korunur.


## Parametre iyileştirme adayı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1 kapsamında ayrı bir sayısal aday geliştirildi:
uzun spektrum, gerçek çizgi araması, DC ayrıştırma, bant ölçekli özellikler
ve 8 bit alıcı bozulmalarıyla eğitilmiş sınıf modeli. Ürün F5 değişmedi.
Son ayrı tohum testinde 700 modülasyonlu öneğin 613'ü doğru kesin karar,
87'si Belirsiz, yanlış kesin karar sıfır; CW 100/100 Belirsiz. Aile
karar kapsamı %82–93. Önceden incelenmiş fiziksel regresyonda AM 16/20,
FM 20/20 Analog; bunlar kör fiziksel kabul değildir. Yeni aday bant
kontrolü geniş kuyruklu BPSK'de 1/6 hatalı kapsam sonucunu hâlâ kaçırır;
OBW kabulü başarısız, ürün entegrasyonu ve ARM taşıması yapılmadı.
27 ilgili test geçti. Parametre çıkarımı tamamlanmadı; aday ürün dışındadır.
Plan: `docs/plans/PARAMETER_REFINEMENT_PROTOCOL.md`. Kanıt:
`results/evidence/phase08/parameter-refinement-candidates-20260909.json`
ve ZIP; eski kaynak/kanıtlar korunur. Sıradaki iş bant kapsam belirsizliğini
ve bağımsız OBW doğrulamasını çözmek, ardından yeni ürün profilidir.


## 735 MHz AM fiziksel karşılaştırması — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: onaylı Faraday kabininde bildirilen AM %100,
1 kHz sinüs kaynağından altı ham RX kaydı alındı. İki alıcı merkezinde
999 Hz zarf tonu ve yaklaşık 1 kHz aralıklı taşıyıcı/yan çizgi deseni görüldü.
Çevrimdışı F5 tanısında 40/40 yeniden hesaplama eşleşti; sınıf 40/40
Belirsiz kaldı. 24/24 dB'de 20/20 model uzaklığı reddi, taşıyıcı 2/20
geçerli, OBW 18/20 geçerli sonucu vardı. Bunlar dört kaydın pencereleridir;
40 bağımsız RF koşusu veya doğruluk kabulü değildir. FPGA kullanılmadı.
Üretim yöntemi değişmedi; sınıflandırma, taşıyıcı ve OBW doğruluğu açık.
Kanıt: `results/evidence/phase08/parameter-rf-am735-20260909.json` ve ZIP.
Ayrıntı: `docs/plans/PARAMETER_VALIDATION_BENCH.md`.


## 735 MHz FM fiziksel parametre tanısı — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1 için kullanıcı onaylı Faraday kabininde sekiz ham
HackRF RX kaydı alındı. 16/16 ve 24/24 dB kazançta iki farklı alıcı
merkezinde yaklaşık 999 Hz FM tonu gözlendi. Gerçek I/Q üzerinde çevrimdışı
F5 tanısında 40/40 yeniden hesaplama eşleşti; sınıf 40/40 Belirsiz,
taşıyıcı 40/40 Gözlenmedi kaldı. Model uzaklığı retleri korundu.
Bu pencereler dört fiziksel kayıttandır; 40 bağımsız RF koşusu değildir.
OBW bağımsız hesap farkı, dBm kalibrasyonu ve kart/ürün kabulü açık kaldı.
FPGA kullanılmadı; üretim yöntemi ve eşikleri değiştirilmedi.
Kanıt: `results/evidence/phase08/parameter-rf-fm735-20260909.json` ve ZIP.
Ayrıntı: `docs/plans/PARAMETER_VALIDATION_BENCH.md`. Önceki ET önceliği
kaydı korunur; bu oturum kullanıcının parametre testlerine devam talebidir.


## KTR-5.1 Tekli Görev / PHASE-10 geçişi — 8 Eylül 2026

Kullanıcının PÇ-02 ve PHASE-09'u beklemeye alma ve ET'ye geçme onayıyla PHASE-10
yalnız Tekli Görev için açıldı. Tek hedef bantta deterministik bant sınırlı CI8,
iletimsiz spektrum/OBW özeti, 0,1–30 saniye sınırı, 8 MS/s profil, sonlu görev
dosyası ve fail-closed HackRF süreç sözleşmesi uygulanmıştır. Ürün yalnız Tekli
Görev'i gösterir; çoklu, baraj, süpürme, arabakış, analog ve GNSS kapsam dışıdır.

Fiziksel profil kapalı, seri kimliği ve izin listesi boştur; cihaz bağlı değildir.
Yazılım testi 10/10 ve güncel Qt Quick ürün doğrulaması 28/28 geçmiştir. Kanıt
`results/evidence/phase10/single-et-software-v1.json` dosyasındadır. Bu, RF çıkış, güç,
etki veya KTR-5.1 kabulü değildir. Kapalı düzen kimliği/zayıflatması ile kısa
fiziksel spektrum ve durdurma negatifleri tamamlanmadan PHASE-10 kapanmaz;
PHASE-11 açılmaz. Bağ: `docs/interfaces/ET_SINGLE_TASK_CONTRACT.md` ve ADR-0041.

## Parametre kabul durumu ve PÇ-02 devamı — 8 Eylül 2026

KTR-4.2 / KTR-4.2-F1 tamamlanmadı. Güncel kaynakla aynı 30 sentetik
önek tekrarlandı ve 30/30 kayıt yeniden hesaplandı; bu doğruluk kabulü
değildir. CW taşıyıcısı 1/6, AM taşıyıcısı 2/6 geçerli; 24 modülasyonlu
öneğin tamamı model uzaklığı kapısında Belirsiz kaldı. Sayısal dBFS
hatası bu kümede en çok 0,189 dB; mutlak dBm kalibrasyonu açık.
Yeni karar kapısı tanısı ve ölçüm/profil kontrolleri 22/22 geçti.
Kanıt: `results/evidence/phase08/parameter-diagnostic-20260908-v1.json`
ve ZIP. Ayrıntı: `docs/plans/PARAMETER_VALIDATION_BENCH.md`.
Kullanıcı cihazların bağlı olmadığını bildirdi; fiziksel kabul yapılmadı.
PÇ-02 sürüyor; PÇ-03–05 ve ST-06 kapanmadı. Ürün yöntemi, eşikleri,
PC/PL/PS görev paylaşımı ve önceki kanıtlar korundu. Aşağıdaki tarihli
kayıtlar kendi sürümlerinin durumunu belirtir.


## ET ürününden hazır senaryoların çıkarılması — 8 Eylül 2026

Kullanıcının hazır/sentetik ET gösterimlerini kaldırma talimatıyla KTR-5.1–5.4
ürün kapsamı güncellendi. QML ET alanından hazır dalga biçimi çalıştırma,
önceden tanımlı hedef sahneleri, otomatik test sesi ve önek GNSS konum/UTC/PRN
formu kaldırıldı. Görev seçimi yalnız uygulanmamış gönderim durumunu gösterir;
ölçüm, grafik, zaman çizelgesi veya tamamlanmış görev sonucu üretmez.
`quick_et_actions.py` artık model çalıştırma ya da GNSS doğrulama API'si sunmaz.
`algorithms/et` ürün import ve paket sınırının dışındadır; eski konsolun ET
mixin'i de paket dışında tutulur. HackRF gönderim yolu uygulanmamıştır.

Sayısal referans modelleri, doğrulama testleri ve özgün ET-A/B/C kanıtları
geçmiş çalışmanın yeniden üretimi için depoda korunur; güncel ürün yeteneği
sayılmaz. Aşağıdaki eski ET-C arayüz kabulü kayıtları tarihsel kapsamındadır.
ED kaynakları ve açık ST-06/parametre kabul kapıları bu ET düzenlemesiyle kapanmaz.
PHASE-10–12 donanım veya RF kabulü yapılmadı. Güncel ürün sınırı
`tests/test_operator_product_boundary.py` ve
`tests/test_app_f_quick_product.py` içindeki ET yokluk denetimiyle sınanır.


## Dört parametre bağımsız tanılama — 7 Eylül 2026

KTR-4.2 / KTR-4.2-F1 kapsamında PÇ-02 sayısal başlangıç çalıştırıldı:
`scripts/validate_parameter_bench.py` ile beş ailede 30 bağımsız sentetik
I/Q kaydı üretildi; ürün F5 ölçümü ve 30/30 yeniden hesaplama eşleşti.
Bu doğruluk kabulü değildir: 24 modülasyonlu öneğin tamamında sınıf Belirsiz;
CW taşıyıcı alanı 1/6 sonuç verdi. Geniş kuyruklu BPSK tam emisyonu ölçüm
aralığını aşıyor. Güç hatası bu sentetik öneklerde en çok 0,189 dB;
dBm kalibrasyonu ve canlı ölçüm sürekliliği açık. İlgili 82 yazılım testi geçti.
Yöntem/eşik/RTL değişmedi; eski kanıtlar korunur. Ayrıntılı referans, paydalar,
sınırlamalar ve fiziksel deney düzeni `docs/plans/PARAMETER_VALIDATION_BENCH.md`
içindedir. Yerel rapor: `build/acceptance/parameter-bench-20260907-v1/report.json`.

## Test alıcısının değişimi — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 ve KTR-4.2 test hazırlığında kullanıcı cihazları
değiştirdi; ED_RX artık `0000000000000000a32868dc35138247` kimliğidir.
Önceki alıcı kanıtları yeni cihaza taşınmaz. Oturum gözlemi ve açık sınırlamalar
`docs/interfaces/SIGNAL_DETECTION_STATUS.md` içindedir; yeni kabul kanıtı oluşmadı.

## PÇ-01 ölçüm arayüzü ve güncel gözlem bağı — 7 Eylül 2026

Kullanıcının devam talimatıyla dört zorunlu sonuç ana görünümde ayrıldı:
taşıyıcı frekansı, OBW %99, kalibrasyonsuz kanal gücü (dBFS) ve Analog/Sayısal.
Emisyon merkezi, bant kenarları, SNR, gözlem süresi, hesaplama bitiş UTC zamanı
ve kayıt yolu açılır ayrıntıdadır. Sonuç, alımın durduğu kayıtlı ölçüm olarak
etiketlenir. Taşıyıcı bulunmadığında merkez onun yerine gösterilmez.

Yeni canlı ölçüm, son işlenen kart yanıtına kadar süren dört ardışık gözlemi
ister; geçmiş/seçim önbelleği yeni ölçüm girdisi olamaz. Yeniden alım eski
sonucu ve aralık onayını temizler; operatör güncel tespiti yeniden seçer.
İptal, gecikmiş çalışan sonucu yayımlamaz. Geçersiz aralık girişi önceki
onayı kaldırır. Algoritma, eşik, RTL ve kart hizmeti değişmedi; F5 bilgisayarda.

Son doğrulama: 137/137 test geçti. Main.qml 2.137, görünüm modeli 1.996
satırla mevcut mimari sınırlar içindedir.

KTR-4.2 / KTR-4.2-F1 yazılım kabul kanıtı:
`results/evidence/phase08/parameter-workflow-v1.json` ve ZIP.
1280×720 ve 1920×1080 görünüm kontrolleri kayıtlı I/Q ile yapılır.
Önceki PÇ-00 kanıtı tarihsel baytlarıyla korunur; aşağıdaki 134/135 sonucu
önceki kaynak içindir. Yeni panel ayrımı Main.qml satır sınırı bulgusunu giderir.
ST-06, fiziksel RF doğruluğu, dBm kalibrasyonu ve ARM taşıması açıktır.
PÇ-02 sıradaki planlı çalışma adımıdır; bu değişiklikle uygulanmadı.

## PÇ-00 ölçüm kaydı uygulaması — 7 Eylül 2026

Kayıt/entegrasyon doğrulamasında 134 kontrol geçti; değiştirilmemiş QML
dosyasının 2.255/2.200 satır sınırı bir açık mimari bulgu olarak kaldı.
Genel test paketi başarısızdır; bu tek bulgu PÇ-00 alan kayıtları, girdi
bütünlüğü veya yeniden hesaplama testinde başarısızlık değildir.

Kullanıcının uygulamaya devam talimatıyla KTR-4.2 / KTR-4.2-F1 için mevcut
F5 ölçümüne kaynak ve I/Q bağlı kayıt eklendi. Canlı ve SigMF ürün ölçümü,
dört normalize I/Q karesini ve alanların birim/yöntem/durum/neden bilgilerini
ayrı ZIP'e kaydeder; kayıt başarısızsa yeni sonuç yayımlamaz. Canlı karelerde
merkez, önekleme, sıra ve kart yanıtı bağı ayrıca denetlenir. Profil/model
özetleri, oturum ayarları, kanal seçici ölçeği ve bilinen kaynak özetleri
saklanır. Donanım UTC zamanı, çalışan kart imajı ve kalibrasyon gözlenmemişse
bilinmiyor kalır; dBm veya RF doğruluk sonucu üretilmez.
[Kayıt ve yeniden üretim sözleşmesi](../interfaces/OPERATOR_ASSISTED_PARAMETER_CONTRACT.md) sınırları tanımlar.

F5E paket denetimi mevcut iki ek logoyu açık listesine aldı; eksik model ve
izinsiz ek dosya retleri korunur. Eski F5E/PHASE-08 kanıtları değiştirilmedi.
Parametre satırlarını oluşturma işlevi mevcut ölçüm modülüne taşındı; görünen
alanlar ve algoritma eşikleri değişmedi. Yeni kanıt
`results/evidence/phase08/parameter-record-v1.json` ve ZIP içindedir.
Bu yazılım kayıt/entegrasyon kabulüdür; yeni fiziksel kart veya RF deneyi
değildir. ST-06 ve dört parametrenin saha doğruluğu açıktır. PÇ-01 arayüz
sadeleştirmesi sonraki iştir; tercihli özellikler ve PHASE-09 açılmadı.

## Dört zorunlu parametre kapsamı — 7 Eylül 2026

Kullanıcının paylaştığı yarışma §5.1.2 metni, mevcut `KTR-4.2` / `KTR-4.2-F1`
kimlikleri korunarak taşıyıcı frekansı, bant genişliği, güç seviyesi ve
Analog/Sayısal ayrımına bağlanır. Tercihli alanlar sonraki kapsamdır.
[Uygulama sırası ve alan kabul kapıları](../plans/IMPLEMENTATION_ROADMAP.md)
PÇ-00–PÇ-05 olarak planlandı. Sayısal hedefler mühendislik önerisidir;
paylaşılan metinde resmî hata toleransı veya güç birimi verilmemiştir.
KTR-4.1 / ST-06 kabulü açıkken bu sınırlı parametre çalışmasına kullanıcı
izin verdi; PHASE-09 açılmadı. Bugünkü QML ölçümü PC/F5 yoludur; ARM'da
emisyon merkezi, OBW99 ve kanal dBFS vardır, taşıyıcı ve sınıf yoktur.
Mevcut host C karşılaştırması geçti; 32/33 profil/arşiv/QML kontrolü geçti.
Tek başarısızlık F5E doğrulayıcısının eski paket dosya listesidir; dBm ve
kontrollü dört-alan RF doğruluğu ayrıca açıktır. Aşağıdaki tarihsel tamamlanma
ifadeleri kendi sürümleriyle sınırlıdır; güncel bütün ürün kabulü sayılmaz.
## ET Faraday laboratuvar kapsamı — 8 Eylül 2026

KTR-5.1–5.3 için kullanıcı, fiziksel ET-TX çalışmalarının yalnız korumaları
hazır Faraday kabini içinde yürütüleceğini bildirmiş ve `CABLED_LAB` politika
kilidinin kaldırılmasını onaylamıştır. `algorithms/et/mission.py` bu modu görev
ve günlükleme için kabul eder; genel `HARDWARE_TX_LOCKED` modu reddedilmeye
devam eder. `tests/test_p0_et.py`, Faraday laboratuvar kabulünü, süre sınırını,
acil durdurmayı ve genel donanım kilidini izler.

Ortam kararı tek başına TX arka ucu eklemez. Birleşik güncel kaynakta Tekli
Görev için güvenlik kapılı HackRF süreç arka ucu ayrıca bulunur. HackRF seri kimliği, host araçları,
sınırlı kazanç/süre, otomatik ve acil durdurma ile bağımsız ölçüm kanıtı olmadan
RF yeteneği geçilmiş sayılmaz. Bu karar PHASE-08/09 durumunu değiştirmez;
PHASE-10/11 fiziksel kabulü açık kalır. Ayrıntı ADR-0043 ve
`docs/safety/RF_TEST_BOUNDARIES.md` içindedir.

## ET yerel C++ sinyal üreteci — 8 Eylül 2026

KTR-5.1 / KTR-5.2 kapsamında ton, FSK, süpürme, PRBS, sinüs, kare,
testere, üçgen, chirp, AWGN ve DC biçimleri için bağımsız C++17 `int8` I/Q
üreteci eklenmiştir. C ABI v1, Python bağı, yapılandırma sınırları,
deterministik seed ve fail-closed negatifler
`tests/test_et_native_signal_generator.py` ile izlenir. Bileşen aygıt,
USB, frekans/kazanç ayarı veya TX API'si içermez; yalnız `OFFLINE/LOOPBACK`
kapsamındadır. Sözleşme `docs/interfaces/ET_SIGNAL_GENERATOR_CONTRACT.md`
dosyasındadır. Bu çevrimdışı bakım kendi başına PHASE-10–12'yi başlatmaz ve
fiziksel RF yeteneği kanıtı değildir; sonraki Tekli Görev uygulamasından ayrı
bir referanstır.

## Son arayüz düzenlemesi — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: sabit frekans ve bant taraması kontrolleri ortak
merkez hizası, eşit alan yüksekliği ve tek görünür ana eylemle sunulur. Bağlı
durum düğmesi ve yinelenen sonuç metinleri kaldırılmıştır. QML durum görüntüleri
ile boşta/çalışıyor/hata/sonuç durumları; ürün testinde alan genişliği,
yüksekliği, merkez hizası ve başlat/durdur görünürlüğü doğrulanır. RF karar
algoritması bu düzenlemede değişmemiştir; ST-06 kabulü açık kalır.
Yedi arayüz durumu ile kaynak hash'leri
`results/evidence/phase08/st06-ui-final-20260907.json` ve ZIP içinde saklandı.
İlgili sinyal tespiti, QML ve depo sözleşmesi paketi 130/130 geçti.

## İkinci kör turun hedef bildirimi — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: operatör ikinci tamamlanan turun hedefini
sonradan 873,4900 MHz olarak açıkladı. Sabitlenmiş normal tarama kaydı
873,490442 MHz (tepe 873,490039 MHz), 120 gözlem; bağımsız alıcı ayarı
873,490094 MHz, 40 gözlem ve otomatik ikinci kontrol 873,490192 MHz,
40 gözlem ile hedefi içerir. İki doğrulama FPGA yöntemindedir; durum
Tekrar görüldü. Kapalı referans veya önceden verilen hedef kullanılmadı.
Bildirim kanıtı `results/evidence/phase08/blind-second-target-873490-20260907.json`;
ham kaynak `blind-second-survey-20260907.json` ve ZIP. Frekans farkları
kalibre mutlak doğruluk iddiası değildir. Bu tek koşul tüm ortamlarda
Pd/Pfa veya otomatik yayıncı kimliği kabulü sayılmaz; ST-06 açık kalır.


## Tam bant ve otomatik ikinci kontrol — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: 700–1000 MHz normal tarama 500/500 pencereyi
239,06 s içinde tamamladı. İlk turda USB taşması, CRC, sıra ve kuyruk kaybı
sıfır. Otomatik ikinci kontrol 124 kayıt için 27,38 s sürdü: 113 tekrar
görüldü, 11 son kontrolde görülmedi, kontrol hatası bildirilmedi.
953 MHz hedefi 952,999935 MHz olarak bulundu; ikinci kontrolde
952,999914 MHz olarak tekrar görüldü. Toplam iki aşama yaklaşık 266,44 s.
11 görülmedi sonucu yanlış alarm veya yayın kapanışı olarak etiketlenmez.
Tekrarlı Pd/Pfa, kesintisiz takip veya ST-06 kabulü değildir.
Kanıt `results/evidence/phase08/full-survey-recheck-20260907.json` ve ZIP;
fiziksel kaynaklar arşivde korunur. Ölçüm sonrasında yalnız ikinci kontrol
sırasında ilk taramanın kalan süre tahminini gizleyen sunum düzeltmesi yapıldı;
4 kontrol testi geçti. Bu son metin düzeltmesinin RF tekrarı yapılmadı.
Tam bant ikinci kontrol çalışma/süre kapısı bu koşulda gözlendi; genel
ortam kabulü ve parametre fazına geçiş açık kalır.


## Otomatik ikinci kontrolün fiziksel doğrulaması — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: operatör önceki boş kısa turda vericinin kapalı
olduğunu düzeltti. 953 MHz açık bildirimi sonrası güncel kaynakla
952,6–953,8 MHz normal tarama iki pencereyi 1,1637 s içinde tamamladı.
952,999962 MHz bulundu; otomatik ikinci kontrol 0,2526 s içinde aynı
sinyali yeniden gördü ve arayüz satırı Tekrar görüldü oldu. Ek kontrolde
48/48 kart yanıtı, USB/CRC/sıra/kuyruk hatası ve kırpılma sıfırdır.
Kaynak hash'leri, ilk tur ve yan kontrol kaydının SHA-256 bağı doğrulandı.
Kanıt `results/evidence/phase08/survey-recheck-live-on-20260907.json` ve ZIP.

Bu hedefi bilinen iki pencerelik testtir; tam bantta yeniden kontrol süresi,
kesintisiz takip, yokluk kararının fiziksel açık/kapalı tekrarı ve genel
Pd/Pfa kabulü değildir. Önceki fiziksel yeniden kontrol bekliyor notu yalnız
bu dar kapsam için kapanır. ST-06 açık; parametre fazına geçilmedi.


## Otomatik ikinci kontrol ve frekans sıralaması — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, ST-06: normal tek tur sonuçları frekans sırasıyla
sunulur. Kontrol edilmemiş enerji bölgeleri listenin sonunda kalır. Normal
tur başarıyla tamamlanınca doğrulanmış ve birleştirilmiş sinyaller bir kez
otomatik yeniden kontrol edilir. Laboratuvar kapalı/açık turları bu ek kontrolü
başlatmaz. İkinci kontrol bitmeden görev tamamlandı bildirimi verilmez.
Tekrar görüldü / son kontrolde görülmedi / kontrol edilemedi ayrı durumlardır;
alım hatası veya iptal sinyal yokluğuna çevrilmez. Kontrol zamanı ipucundadır.
`.recheck.jsonl` yan kaydı özgün taramanın SHA-256 özetini ve her sonucu
saklar; ham tarama kanıtı değiştirilmez. Bu sınırlı bir ikinci turdur,
kesintisiz izleme veya yeni yayınların sürekli keşfi değildir.

102 hedefli test ve 25 arayüz testi geçti. İptal, hatanın yokluktan ayrılması,
kayıt korunması ve görev tamamlanma sırası sınandı. 952,6–953,8 MHz fiziksel
denemede 2/2 pencere tamamlandı fakat sinyal bulunmadı; otomatik ikinci kontrol
çalışmadı. Vericinin güncel durumu soruldu; fiziksel yeniden kontrol kabulü
bekliyor. Kanıt `results/evidence/phase08/survey-recheck-20260907.json` ve ZIP.
Ek kontrol süresi genel tur süresine eklenir; tarama ve kontrol ayrı kaydedilir.
ST-06 açık; parametre fazı başlamadı.


## 953 MHz hedef eşleştirmesi ve kısa tekrar — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: operatör tamamlanan 700–1000 MHz turunun
hedefini sonradan 953 MHz olarak açıkladı. Değiştirilmemiş kayıtta
952,999989 MHz, ilk ölçümde 63 ve ikinci ayarda 23 gözlemle FPGA doğrulaması
vardır; arayüzün saklanan sıralamasında 76. satırdadır. Kapalı referans
kullanılmadan hedef listelenmiştir; otomatik hedef seçimi kanıtlanmamıştır.
Yeni dar-sinyal eşleştirmesiyle 952,6–953,8 MHz kısa fiziksel tarama
2/2 pencereyi 1,0834 s içinde tamamladı: 952,999964 MHz, ikinci ayarda
952,999955 MHz, 91/26 gözlem. Tamamlanan pencerelerde USB taşması,
CRC, sıra ve kuyruk kaybı sıfır. Bu hedefi bilinen dar aralık tekrarıdır;
300 MHz kör tarama süresi veya genel Pd/Pfa kabulü değildir.
Kanıt: `results/evidence/phase08/target953-confirmation-20260907.json`
ve ZIP; iki fiziksel kaynağın hash'leri ayrı korunur. Önceki hedef frekansı
bekleniyor notu bu bildirimle çözülmüştür. ST-06 açık kalır.


## Dar sinyal doğrulama eşleştirmesi — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, ST-06: dar ilk gözlem geniş ikinci-ayarlama
olayının içine düştüğünde yalnız aralık örtüşmesiyle kabul edilebiliyordu.
Dar ilk gözlem için ikinci olayın genişliğinden bağımsız olarak tepe
frekansı mevcut 50 kHz toleransında eşleşmelidir. Geniş ilk gözlemin
aralık tabanlı doğrulaması korunur. Yeni dar/geniş yanlış eşleşme testi ve
mevcut geniş bant tepe değişimi testi dahil 60 hedefli test geçti.
Bu değişiklik hedef frekansı öğrenilmeden yapıldı; frekansa özel kural yoktur.
Kanıt `results/evidence/phase08/survey-narrow-verification-20260907.json`
ve ZIP. Eski kayıttaki özetlerin incelemesi yeni RF sonucu değildir;
tek tek doğrulama kareleri bu kayıtta bulunmadığından başarı sayısı
sonradan değiştirilmedi. Güncel kaynak fiziksel doğrulaması bekleniyor.
ST-06 ve parametre fazına geçiş kapısı açık kalır.


## Güncel kaynakla tek tur fiziksel ölçüm — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: 700–1000 MHz, azami 24/24 dB, harici
verici açık operatör beyanıyla normal tarama 249,10 s sürdü. Kapalı referans
yüklenmedi. 500/500 pencere tamamlandı; tamamlanan pencerelerde USB taşması,
CRC, sıra ve kuyruk kaybı sıfır. 10 kazanç tekrarı, 126 ham gözlem kaydedildi.
Önceki açık turun 257,16 s süresinden yaklaşık %3,13 kısa; değişen RF yükü
ve tekrar sayıları nedeniyle nedensel hız kazancı kanıtlanmadı.
Önceki 826 MHz çevresinde ±50 kHz doğrulanmış gözlem yok; bu turun hedef
frekansı henüz açıklanmadı. Hedef başarısı veya ST-06 kabulü çıkarılmaz.
Arayüz sonuç satırları kaydedildi; pencere görüntüsü kaydedilemedi.
Kaynak hash eşleşmeleri ve ham kayıtlar:
`results/evidence/phase08/survey-optimized-live-20260907.json` ve ZIP.
Önceki mikro ölçümün fiziksel toplam süre kapısı bu gözlemle güncellendi;
tekrarlı hız kabulü ve RF hedef doğruluğu açık kalır.


## Tarama hesaplama maliyeti ve sade görünüm — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: tarama ve ikinci ayar doğrulamasında ilk kareden
sonra yalnız doğrusal FFT gücü hesaplanır; kullanılmayan genlik, logaritmik
PSD ve frekans ekseni dizileri tekrar üretilmez. Referans işlem sırası,
Hann penceresi, kare sayısı, gözlem süresi ve eşikler korunur. Ayrı hız modu yoktur.
`tests/test_detection_power.py` sıfır, DC, ton ve rastgele CI8 girdilerinde
4096/16384 boyutları ve DC çıkarımı seçeneklerinde birebir güç eşitliğini sınar.
Yerel mikro ölçüm medyanı tam yol 1,3607 ms, güç yolu 0,6442 ms;
bu toplam tarama süresi veya fiziksel RF doğruluğu kabulü değildir.

Görünümde tekrarlanan tespit yazıları, yeni etiketi, teknik pencere sayacı
ve renk açıklamaları kaldırıldı. Frekans, varsa kaba aralık ve yalnız
belirsiz bulguda doğrulama durumu gösterilir. Ayrıntılar ipucunda korunur.
Tamamlanan turda son pencere aralığı ana başlık gibi gösterilmez.
Yeni kaynakla fiziksel süre karşılaştırması açık; ST-06 tamamlanmadı.
Kanıt: `results/evidence/phase08/survey-power-20260907.json` ve ZIP.


## Tek tur tarama sunumu — 7 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, PHASE-08 / ST-06 kapsamında bant taraması
kartlarında frekans, tespit durumu ve mevcutsa kaba frekans aralığı gösterilir.
Teknik kanıtlar ipucunda korunur. Yalnız enerji bölgeleri doğrulama bekliyor
olarak ayrılır; geçmiş tarama sonucu kesintisiz canlı yayın sayılmaz.
Dar çizgiler yalnız komşu pencerelerde, aynı kanıt sınıfında ve iki ayardaki
tepe frekansları ayrı ayrı iki FFT hücresi içinde uyuşursa birleştirilir.
Sabit eşleştirme merkezi zincirleme frekans kaymasını önler; geniş emisyonlar
ve aynı penceredeki ayrı çizgiler birleştirilmez. Ham kayıtlar değişmez.

Kanıt: `results/evidence/phase08/survey-single-presentation-20260907.json`
ve ZIP. Önceki 6679a49 kaynağıyla 700–1000 MHz kapalı/açık turları
500/500 pencere tamamladı (282,56 / 257,16 s). Açık tur sonrasında operatör
826 MHz bildirdi. Yeni sunumun yalnız açık kayıt tekrarı kapalı referans
kullanmadan 130 gözlemi 122 satıra birleştirdi; 826 MHz tekrarı da birleşti.
Bu RF algoritmasının yeni fiziksel tekrarı, yayıncı sayısı, otomatik hedef
seçimi veya Pd/Pfa kabulü değildir. Kaynaklar kanıtta ayrı tutulur.

Hedefli 99 yazılım ve 25 arayüz testi geçti. İlk alım oturumları 193,05 s, kabul edilen
130 ek doğrulama 25,92 s tuttu; süreler toplam turun bütün aşamalarını
ayrı ayrı açıklamaz. Alım hızlandırması, sürekli yeniden ziyaret ve ortamdan
bağımsız hedef seçimi henüz uygulanmadı. Eşikler, RTL ve alım süreleri
korundu. ST-06 açık; parametre fazına geçilmedi.


## Gün sonu aktarımı — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: bilinen 853 MHz CW ve 24/24 dB ile önceki fiziksel
sürümün kısa açık/kapalı ayrımı olumludur. Son otomatik kazanç ve arayüz sürümü
henüz fiziksel olarak denenmedi. Sinyal tespitinin temel yolu çalışıyor;
ST-06 tamamlandı veya her ortamda kararlı denemez. Parametre fazı başlamadı.
RF tanı kayıtları, başarısız girişimler ve yeniden üretim araçları artık
`results/evidence/phase08/rf-diagnostics-20260906.zip` içinde korunur; yanındaki
JSON her dosyanın SHA-256 özetini içerir. Arşiv köke açıldığında belgelerdeki
özgün build yolları geri gelir. Var olan dosyalar hash karşılaştırılmadan
üzerine yazılmaz. Eski ölçümler kendi kaynak özetleriyle korunur.
Sonraki oturum: önce kart/servis/çalışan imaj kimliği yeniden kontrol edilir;
yeni sürümle kısa kapalı → açık → kapalı ölçüm, otomatik kazanç yönü/döngü/iptal
ve frekans durumlarının doğruluğu sınanır. Anten konumu ve TX kazancı sabitlenir;
koşullar sonra tek tek değiştirilir. Sonuçlar uygun olursa kalan kör RF,
soğuk açılış ve güncel kaynak kabul kapıları değerlendirilerek faz kararı verilir.
Sırf önceki masaüstü geçişleri nedeniyle uzun GUI koşuları baştan tekrarlanmaz.
Sayısal ölçekleme deneyinin kazancı umut vericidir; canlı güç telafisi ve
fiziksel doğrulaması yapılmadan üretim ölçeği 1'den değiştirilmez. Otomatik
kazanç ilk seviye ayarı ve kırpılma sonrası sınırlı yeniden denemedir; kesintisiz
AGC veya kalibre güç ölçümü değildir. Optimizasyon için ölçülebilir yol vardır;
tamamlanma kararı yeni kanıta dayanacaktır.

## Sinyal tespiti kullanım ve seviye düzenlemesi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, PHASE-08 / ST-06: sabit izleme arayüzünde
isteğe bağlı otomatik kazanç (başlangıçta seçili), MHz girişi ve sade sinyal
durumları uygulandı. Başlangıç görünümü değerlendirilen ±700 kHz'e odaklanır;
kullanıcı genişletirse kapsam işareti korunur. Frekans ve alınıyor/artık alınmıyor
ana bilgidir; teknik sayılar ipucunda kalır. RF kimliği veya çift ayar doğrulaması
bu sade sunumdan çıkarılmaz.
Otomatik mod ilk 16 kareyi seviye hesabından dışlar, sonraki 32 karenin CI8
çıkışında %95'ten fazla sıfır bileşeni varsa kazançları 8 dB artırarak yeni oturum
açar. Kırpılmada 8 dB azaltır. En çok 8 girişim, tekrar ziyaret yasağı ve operatör
iptali vardır. Kırpılmış kare karta gönderilmez; denemeler ayrı oturumlardır ve
kayıpsız kesintisiz alım diye sayılmaz. %95 ölçütü mühendislik sezgisidir; genel
hassasiyet, Pfa/Pd hedefi veya RF yokluk kararı değildir. Başlangıç kırpılması
henüz sürekli kırpılmadan ayrılmıyor. Sürekli düşük-seviye takibi yapılmıyor.
Kanal seçiciye yalnız açıkça seçilen deneyler için 1–16 genlik ölçeği ve çıktı
ölçeği bilgisi eklendi; üretim varsayılanı 1. Kaydedilmiş aynı 16/16 dB açık ham
veride kayan noktalı merkez eşik aşımı ölçek 1'de 14/496, ölçek 8'de 474/496;
kapalıda ikisinde de 0/496. Beş ölçek ve açık/kapalı çiftin tümünde 512/512
Python/yerel çıktı eşleşti; kırpılma sıfır. Bu donanım FFT tekrarı değildir.
Yerel yeniden üretim: `build/acceptance/st06-gui-20260906/analyze_channelizer_scaling.py`;
özet ve SHA-256: `build/acceptance/st06-gui-20260906/channelizer-scaling-diagnosis-01.json`.
Canlı ölçekleme entegrasyonu güç/ölçek izlenebilirliği ve fiziksel doğrulama
bekler; henüz etkin değildir. RTL/CFAR katsayısı değişmedi. Yazılım testleri
kazanç yönü, döngü sınırı, iptal, MHz dönüşümü, kapsam odağı ve referans eşleşmesini
denetler. Yeni sürüm FPGA/HackRF üzerinde bu değişikliklerden sonra denenmedi;
eski fiziksel kanıt bu kaynağa taşınmaz. ST-06 ve sonraki faz kabulü açık kalır.

## Ekran incelemesi ve MHz girişi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında sabit izleme merkez girişi MHz oldu;
ondalık nokta/virgül kabul edilir, iç arayüze tam Hz aktarılır. QML testi birim
dönüşümünü, hatalı değerleri ve gerçek ayarların forma geri yansımasını denetler.
Kullanıcının 933 MHz görsellerinde yaklaşık 929,8 MHz geniş tepe, görünür
932,3–933,7 MHz tespit alanının dışındadır; bu tepenin kaynağı kanıtlanmadı.
Ham 8 MHz görüntünün tamamı aynı anda tespit kapsamı sayılmaz. 931,5 MHz ve
1198,5 MHz merkez çizgileri DC iziyle uyumludur; görüntü tek başına kimlik kanıtı
veya Pd/Pfa hesabı değildir. Tek uç-değer I/Q bileşeni oturumu durdurur; yerel
kanal seçici böyle giriş karesini sıfırladığından yalnız durdurma koşulunu kaldırmak
geçerli çözüm değildir. Kırpılma oranı/başlangıç ayrımı ve kullanıcıya daha açık
kazanç tanısı halen açıktır. MHz değişikliği DSP veya RF kabulünü değiştirmez;
önceki fiziksel sonuçlar yeni arayüz kaynağının fiziksel testi sayılmaz.

## 853 MHz eşleştirilmiş kart sonucu — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında RX LNA/VGA 24/24 dB ile aynı anten
konumunda kısa, kullanıcı beyanlı açık/kapalı kart koşuları tamamlandı. Açıkta
853 MHz olayı ilk kareden son kareye 4.883/4.883 kez gözlendi; öneklenmiş 327
yanıtın ilk tentative yanıtından sonraki 326'sı aynı hedefi confirmed ve observed
olarak taşıdı. Kapalı koşunun 327 önek yanıtında hedef çevresinde confirmed olay
yoktu. Her iki koşuda USB/CRC/sıra/kuyruk hatası ve kırpılma sıfırdı. Bu bilinen
CW için kısa olumlu ayrım kanıtıdır; kör/tekrarlı RF doğruluğu veya ST-06 kapanışı
değildir. Yerel özet `build/acceptance/st06-gui-20260906/rf853-24db-board-comparison-01.json`.

## 853 MHz 24/24 dB gerçek kart gözlemi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: kullanıcı beyanlı açık vericiyle üç kazanç kaydı alındı.
Her ayarda 512 ardışık ham kare, sıfır USB taşması/kırpılma ve 512/512 yerel /
Python kanal seçici eşleşmesi var. İlk 16 kare dışlanınca 16/16 dB açık kaydında
ham USB merkez hücresi kayan noktalı eşik hesabını 474/496, kanal seçici çıkışı
14/496 kez aştı. 24/24 dB çıkışında 496/496, kapalıda 1/496; medyan açık eşik
marjı +11,06 dB. 32/32 dB kapalı merkezde de 76/496 aşım görüldüğünden daha yüksek
kazanç otomatik olarak tercih edilmedi. Bu hesaplar FPGA bit-tam tekrarı değildir.
Ardından 24/24 dB ile gerçek RX → kart → GUI koşusu 4.883 kareyi sıfır USB/CRC/
sıra/kuyruk hatası ve kırpılmayla bitirdi. İlk önek tentative; kalan 326 önek
yanıtta aynı 853 MHz olay kimliği confirmed ve observed idi. Son kart yanıtında
first_frame_id=0, last_seen_frame_id=4882, seen_count=4883: kart sayacı bu kısa
koşunun tüm karelerinde hedef gözlemi bildiriyor. GUI kısa koşu kontrolleri geçti.
Bu sonuç bilinen CW için kısa olumlu gözlemdir; genel Pd/Pfa, uzun süreli hız payı
ve ST-06 kabulü değildir. 24/24 dB eşleştirilmiş kapalı kart koşusu bekleniyor.
Üretim eşikleri değiştirilmedi; kazanç yalnız tanı koşusuna uygulandı.
Yerel raporlar: `build/acceptance/st06-gui-20260906/rf853-gain-comparison-01.json`
ve `build/acceptance/st06-gui-20260906/rf853-on-24db-target-01.json`.

## 853 MHz kapalı kazanç karşılaştırması — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0 kapsamında kullanıcı vericinin kapalı olduğunu bildirdi.
RX LNA/VGA 16/16, 24/24 ve 32/32 dB ayarlarının her birinde 512 ardışık ham
kare (yaklaşık 1,05 saniye) kaydedildi. Üç koşuda USB taşması ve giriş/çıkış
kırpılması sıfır; aynı ham verinin yerel ve Python kanal seçici çıktıları her
koşuda 512/512 bayt-tam eşleşti. Kanal seçici çıkışında sıfır olmayan bileşen
oranı sırasıyla %1,726 / %4,390 / %52,880 oldu. Bu artış kapalı ortamın sayısal
seviyesidir; hedef sinyal iyileşmesi, Pd/Pfa veya FPGA kabulü değildir.
Ham ve türetilmiş I/Q birlikte `build/acceptance/st06-gui-20260906/rf853-gain-off-01/`
içinde; kaynak/girdi özetleri `summary.json` içindedir. Yeniden üretim aracı
`build/acceptance/st06-gui-20260906/rf853_gain_capture.py` (yeni çıktı dizini gerektirir).
Bu tanıda kart gönderimi yapılmadı; üretim yapılandırması ve eşikler değişmedi.
Eşleştirilmiş verici açık kazanç karşılaştırması bekleniyor. ST-06 açık kalır.

## 853 MHz eşik incelemesi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, ST-06 kapsamında mevcut yakın anten kayıtları
çevrimdışı incelendi; üretim eşikleri ve kazançlar değiştirilmedi. Periyodik Hann,
kayan noktalı FFT ve kaynakla aynı OS-CFAR penceresi/rank/katsayısıyla açık kaydın
327 önek karesinde merkez hücre güçlü eşiği 14 kez, kapalıda sıfır kez aştı.
Açık kayıtta medyan güçlü eşik marjı −4,49 dB; zayıf eşik aşımı güçlüler dahil
119/327 idi. Bu sayılar donanımın bit-tam tekrar sonucu veya Pd değildir.
Normal doğrulama 3 karede 2 gözlem, zayıf yol 32 karede 24 gözlem gerektirir;
15 kare aralıklı kayıtla bu ardışık pencereler yeniden kurulamaz.
Gerçek yanıtların iki merkez confirmed olayında saklanan eşik marjı +0,388 ve
+0,180 dB idi; ilki o karede gözlenmemiş geçmiş olaydır. İkinciyle aynı I/Q
karesinin kayan noktalı marjı +0,158 dB çıktı; tek karşılaştırma genel bit-tam
uyum kanıtı değildir. Açık I/Q bileşenlerinin %98,208'i sıfır, kalanları ±1'dir.
Bu düşük sayısal seviye ve eşik altı dağılım seyrek tespitle uyumludur; kaybın
RF girişinde mi kanal seçimi/yeniden nicemlemede mi oluştuğu bu çiftle ayrılmaz.
Periyodik Hann açık/kapalı merkez güç farkı +7,150 dB; bu değer SNR değildir.
Yerel yeniden üretim: `python build/acceptance/st06-gui-20260906/analyze_rf853_threshold.py`.
Girdi ve kaynak SHA-256 kayıtlı rapor: `build/acceptance/st06-gui-20260906/rf853-threshold-diagnosis-01.json`.
Sonraki tanı kısa, sabit konumlu RX kazanç karşılaştırması ve eşzamanlı ham USB /
kart girdisi kaydıdır; uzun GUI testi gerekmez. ST-06 kabulü açık kalır.

## 853 MHz yakın anten açık/kapalı tanısı — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0: kullanıcı beyanlı 853 MHz CW, TX gain 0,
RX LNA/VGA 16/16 dB ile aynı yakın anten konumunda ayrı açık/kapalı 10 saniyelik
koşuların her biri 4.883 kareyi sıfır USB/CRC/sıra/kuyruk hatası ve kırpılmayla
bitirdi. 327 öneklenmiş I/Q karesinin ortalama merkez-hücre gücü açıkta kapalıya
göre 7,15 dB arttı. Öneklenmiş FPGA yanıtlarında tam 853 MHz hücresinde iki
confirmed gözlem (biri o karede observed değil), kapalıda hedef çevresinde sıfır
confirmed gözlem vardı. Bu seyrek bulgu kararlı tespit veya Pd/Pfa kabulü değildir.
Yakın anten mesafesi sayısal kaydedilmedi; kapatma/expiry gecikmesi ayrı oturumlar
nedeniyle ölçülmedi. Yerel ham paket `build/acceptance/st06-gui-20260906/rf853-near-comparison-01.zip`.
Önceki uzak açık/kapalı merkez farkı 0,46 dB idi; koşullar karıştırılmaz. Kanal
seçici 0/0 dB kapalı ham kaydında Python referansıyla 128/128 byte-tam eşleşti;
çok düşük girişin çıkışta sıfıra yuvarlanması tespit yokluğunu tek başına
algoritmaya atfetmeyi engeller. ST-06 ve kontrollü tekrarlı RF kabulü açık kalır.


## 853 MHz kapalı referansı — 6 Eylül 2026

Kullanıcı alıcıyı geçici olarak `…36877e47` ile değiştirdi; ED_RX yapılandırması
bu cihaza bağlandı. KTR-4.1 / KTR-4.1-OPS-B0 kapsamında 853 MHz, LNA/VGA 0/0 dB
ve verici kapalı operatör beyanıyla yaklaşık 30 saniyede 14.648 kare işlendi;
USB/CRC/sıra/kuyruk hatası, kırpılma, ham aday ve etkin olay sayısı sıfırdı.
İlk alım giriş kırpılmasıyla durdu; sonraki aynı ayarlı koşu geçti. Başlangıç
kırpılmasının nedeni kanıtlanmadı. Yerel ham kayıt ve öneklenmiş I/Q paketi:
`build/acceptance/st06-gui-20260906/rf853-off-bundle.zip` (yeni klonda bulunması
varsayılmaz). Bu kısa negatif gözlem ortam sessizliği veya Pd/Pfa kabulü değildir;
verici açık eşleştirilmiş ölçüm henüz yapılmadı. ST-06 açık kalır.


## GUI ve oturum yaşam döngüsü gözlemi — 6 Eylül 2026

KTR-4.1 / KTR-4.1-OPS-B0, PHASE-08 / ST-06 kapsamında yeni ham kayıtlar
`results/evidence/phase08/gui-rx-lifecycle-v1.json` ve ZIP içinde saklanır.
900 MHz ayarında tek 15 dakikalık koşu 439.453 kareyi sıfır USB/CRC/sıra/kuyruk
hatasıyla tamamladı. Operatörün doğruladığı son-saniye masaüstü geçişinde
3,53 saniyelik çizim aralığı oluştu; kesintisiz GUI kabulü değildir.
Önceki kısa GUI koşusundaki bir USB taşması ve 104,65 MHz giriş kırpılması
başarısız kayıt olarak korunur. İki dakikalık görünür kısa koşu geçti.

Aynı uygulamada 30 saniye sonra durdurma yaklaşık 124 ms sürdü; yeni oturum
nesli, kare ve RX/FPGA zaman bilgileri sıfırlandı. Yeniden başlatılan 90 saniyelik
koşu 43.945 kareyi sıfır USB/taşıma hatası ve kırpılmayla tamamladı.
Ancak p95 RX→görüntü yaşı 153,47 ms ile 150 ms hedefini aşmıştır; öneklenmiş
kuyruk değerleri 118/512 ve 64/64'tür, kesin tepe değildir. Etkin olay olmadığı
için eski olay kimliklerinin karışmaması fiziksel olarak sınanmış sayılmaz.
Operatör masaüstünden döndüğünü bildirdi, fakat Qt gizlenme geçişi kaydetmedi;
pencereye dönüş gecikmesi ölçülmüş gibi sunulmaz. İlk iptal edilen oturumun
son USB istatistiği yoktur. Pencere kapatılarak kesilen denemeler ayrı korunur.

Çalışan hizmet özeti seri konsoldan doğrulandı; bitstream/imaj özeti okunamadı.
Vericinin kapalı olması operatör beyanıdır. RF doğruluğu, soğuk açılış,
tekrarlı dayanıklılık ve ST-06 kapanışı açık kalır. Sıradaki hedef uzun testleri
körlemesine tekrarlamak değil, yeniden başlatmadaki gecikmeyi kısa ölçümlerle
ayrıştırmak ve olay içeren yaşam döngüsünü sınamaktır. Eski kanıtlar değiştirilmedi.


## Güncel kanıt sınırı — 6 Eylül 2026

PHASE-08 / ST-06 ve KTR-4.1 / KTR-4.1-OPS-B0 kabulü açıktır.
5 Eylül tarihli 439.453 karelik tek arayüzsüz RX koşusunda USB taşması ve
CRC/sıra/kuyruk hatası görülmedi. Ölçülen 488,2153 kare/s, nominal
488,28125 kare/s üzerinde bir hız payı kanıtlamaz. Önceki kaynakla yapılan
iki uzun koşu USB taşmasıyla başarısızdı. GUI sürekliliği, RF tespit doğruluğu
ve kalıcı sorunsuz çalışma bu koşuyla doğrulanmadı; soğuk açılış kabulü de açıktır.

Tarihsel `native-channelizer-v3` ve `st06-parallel-product-v1` kanıtları
özgün kaynak hash'leri ve arşivleriyle korunur. Yeni RX koşusu kendi kaydıdır;
eski fiziksel sonuçlar değiştirilmiş PC kaynağına aktarılmaz.
İnceleme: `results/evidence/phase08/rx-evidence-recovery-v1.json` ve ZIP.
Doğrulama: `python scripts/verify_phase08_evidence_recovery.py`.
Bu işlem yeni donanım ölçümü içermez. Güncel ayrıntılar sinyal tespiti durum
belgesindedir; aşağıdaki tarihli kayıtlar kendi sürümlerinin sonuçlarıdır.

## Son ST-06 ürün güncellemesi — 5 Eylül 2026

Paketlenmiş hizmette CPU0 DMA sonrası güç çözme/doğrulamayı, CPU1 dar/geniş
aday ve olay işlerini yürütür. Kuyruk tamponlarının sahipliği değiştirilerek
ek kopya önlenir; hata geri alımında ortalama kayıtlı toplamdan türetilir.
Algoritma, medyan, eşikler ve RTL değişmedi. Üç zaman damgalı dijital ürün
koşusu 508,56 / 502,40 / 508,93 kare/s; 16.000 karelik karma tekrar ölçümü
529,30 kare/s verdi. Gerekli 488,28125 kare/s bu iş yüklerinde sağlandı.
Beş kısa testin ham yanıtları önceki paketle birebir eşleşti. Aktarım hatası
ve aday düşümü sıfırdı. Ek ARM kuyruk belleği 272 KiB'dir; FPGA artışı yoktur.
Kanıt: `results/evidence/phase08/st06-parallel-product-v1.json` ve ZIP.
Bu sonuç RF veya soğuk açılış kabulü değildir. SD değişmedi, hizmet geçici
yüklüdür. Hız payı sınırlıdır; saf periyodik ton/yoğun olay kapasitesi,
sürekli HackRF RX ve kör RF kapıları açıktır. ST-06 tamamlanmamıştır.
Aşağıdaki eski hız kayıtları kendi kaynak sürümlerinin tarihsel sonuçlarıdır.


5 Eylül 2026 son ST-06 optimizasyonu: ARM güç çözme ve durum yedekleme
maliyeti azaltıldı; eşikler, sekiz karelik pencere ve RTL değişmedi. PetaLinux
paketinden çıkan hizmetle üç fiziksel dijital koşu 464,87 / 460,37 / 463,74
kare/s verdi. Önceki 286–290 kare/s kaydı tarihsel karşılaştırmadır;
488,28125 kare/s kabul sınırı hâlâ geçilemedi. Beş test girdisinin kart
yanıtları önceki sürümle byte-tam eşleşti. Bu, RF doğruluk kabulü değildir.
Kanıt: `results/evidence/phase08/st06-product-optimization-v1.json` ve ZIP.
SD açılış dosyaları değişmedi; güncel hizmet geçici yüklüdür. ST-06 sürer.

Önceki kayıtlar ve mimari açıklamalar:

5 Eylül 2026 ST-06 kart tanısı, KTR-4.1 / KTR-4.1-OPS / KTR-6 için geçici
FPGA ve ARM ürün hizmeti üzerinde dijital I/Q işlevini sınamıştır. 256
bağımsız gürültü karesinde doğrulanmış olay yok; dar ton 255/256, geniş bant
249/256 karede doğrulanmıştır. Olaylar sıfır girişte sonlanmıştır. Ürün hızı
286–290 kare/s olduğundan 488,28125 kare/s kapısı başarısızdır. Bu sonuç
RF Pd/Pfa, soğuk açılış veya saha kabulü değildir. Önceki kaynakların hız
kanıtları güncel ürüne aktarılmaz. Ham veri ve açık sorunlar:
`results/evidence/phase08/st06-product-board-diagnostic-v1.json`.

## Güncel sinyal tespiti kapsamı

1 Eylül 2026 bağlantısız alıcı bakımında `KTR-4.1-OPS-B0` operatör sunumu
netleştirilmiştir. Uygulama otomatik cihaz denetimi yapmadan `Bekliyor` durumunda
açılır. Operatörün açık denetimi HackRF keşfi ile ZedBoard FPGA hizmet uç noktası
bağlantısını iki sınırlı işte paralel yürütür; `Hazır` yalnız ikisi de geçerse
verilir. Tekil HackRF/FPGA ve birleşik hata nedenleri `Alıcı Ayarları` alanında
ayrı gösterilir; üst başlıkta bağlantı veya hata mesajı tekrarlanmaz. Hata 10
saniye boyunca işlem alanında görünür. Süre sonunda
bağlantı kurulmamışsa yüzey yeniden `Bekliyor` durumuna döner. TCP hizmet bağlantısı
PL algoritmasının işlediğini veya doğru sonuç verdiğini tek başına kanıtlamaz; bu
yalnız cihaz/hizmet erişimi ve dürüst operatör geri bildirimi sözleşmesidir. Donanım,
RF doğruluğu veya faz kabulü oluşturmaz. Sözleşme
`tests/test_live_ed_view_model.py` ve `tests/test_app_f_quick_product.py` ile
doğrulanır.

31 Ağustos 2026 bakım kaydı: `KTR-4.1` görünümü için Qt görüntü tamponu,
tepe koruyan frekans projeksiyonu, sabit renk ölçeği, gerçek kare zamanı,
sınırlı GUI bildirimi ve tarama penceresine bağlı waterfall uygulanmıştır.
`tests/test_spectral_display.py`, RX/görünüm testleri ve
`scripts/measure_detection_display.py` yalnız yazılım/görünüm kanıtıdır.
`results/evidence/phase08/detection-display-rendering.json` beşer yerel çizim
koşusunu ve canlı RF kabulünden ayrılan ölçüm sınırlarını kaydeder.
`results/evidence/phase08/detection-scale-characterization.json` yeni geniş
bant körlük karşı öneklerini korur; `KTR-4.1` saha kabulü açık kalır.
Güncel donanım sahipliği, kaynaklar ve kabul sırası
[Sinyal tespiti durum belgesindedir](../interfaces/SIGNAL_DETECTION_STATUS.md).
Kullanıcının sonraki planlama yönlendirmesi aynı belgede ST-01–ST-08 kapanış
işlerine ayrılmıştır. Bunlar `KTR-4.1` / `KTR-4.1-OPS-B0` için önerilen alım,
görünüm, geniş bant tespiti, tarama ve kabul işleridir; gereksinimler yalnız
plan yazıldığı için tamamlanmış veya yeni donanım yeteneği kazanılmış sayılmaz.
Kullanıcının uygulama yetkisiyle RX görüntüsü/FPGA tespiti ayrımı, GUI dışında
görsel FFT, sınırlı görüntü kuyruğu, veri yaşı, erken tarama önizlemesi ve aday
kapasitesi hatasının doygunluktan ayrılması uygulanmıştır. Gerçek RX/görüntü
ölçüm aracı `scripts/measure_live_rx_display.py` bütün kaynaklarını arşivler;
önceki kaynakta 15 dakika / 439.454-kare RX-only koşusu sıfır USB taşması,
30,51 taze görüntü/s ve 21,82 ms p95 veri yaşıyla geçmiştir; kaynak bağlı tarihsel
kanıt `results/evidence/phase08/live-rx-display-8msps-v1.zip` içindedir. ADR-0039
ile kanal seçici C++17 AVX2/FMA3 çekirdeğine alınmış, 80 karede sıfır CI8 LSB
farkı ve `0,524815 ms` p95 süreyle `native-channelizer-v3.json` kanıtını
geçmiştir. Güncel görünüm 32,15 taze görüntü/s, 40,04 ms p95 çizim ve 20,72 ms
p95 veri yaşı hedeflerini geçse de üç USB shortfall nedeniyle genel kabul
başarısızdır; `live-rx-display-8msps-v2.json` açık kapıyı korur. Uygulamasız
doğrudan aktarımda da shortfall görüldüğünden farklı fiziksel USB port/kablo
A/B tekrarı gerekir. Bu araçlar kart cevabı veya RF tespit olasılığı kabulü
üretmez. Güncel kart erişimi
ve geniş bant karar kapsamı açık olduğundan KTR-4.1 tamamlandı sayılmaz.

1 Eylül 2026 sabit bant karar kaydı: tek LO'daki FPGA 2/3 olayı sarı `FPGA
ADAYI` olarak sunulur. En az 8 FPGA gözleminden sonra dört olası HackRF LO
ayarından iki başarılı ayar bulunana kadar 96'şar karelik sınırlı tekrar
yapılır; 16 yerleşme karesi atıldıktan sonra en az 24 eşleşen gözlem bulunan
mutlak RF bileşeni yeşil `KARARLI RF ADAYI` olur. Dar aday eşlemesi ±50 kHz,
geniş aday eşlemesi mutlak destek örtüşmesidir. FPGA alanının içindeki veya
dışındaki doğrulanmış 8 MHz kaba aday bu sınamayı başlatabilir; sonuçtan sonra
operatörün seçtiği sabit merkez değiştirilmez. 128 karelik liste histerezisi canlı grafik
kılavuzunu ve FPGA olay ömrünü uzatmaz. Birim testleri sabit adayın iki LO'da
korunmasını, ilk alıcı tarafı zayıfken sonraki iki ayarla kabulü, alıcı ayarıyla
hareket eden ürünün reddini ve 6 GHz kenarındaki geçerli ayar seçimini doğrular.
Bu sonuç harici verici kimliği veya saha
Pd/Pfa kanıtı değildir. `live-user-tx-on-off-900mhz.json` tanı turunda
900,191406 MHz bileşeni iki LO'da TX kapatılınca 21,30/21,81 dB düşmüş;
900,000 MHz bileşeni TX kapalıyken kalmıştır. Birden fazla aynı-kare adayı artık
en fazla dört elemanlı sınırlı kuyrukta P/N sırasıyla iki-LO doğrulamasına
alınır ve ikinci BÂZ süreci tek-önek kilidiyle engellenir. 45 ilgili regresyon
testi geçmiştir. Tek operatör beyanlı tur saha Pd/Pfa kabulünü kapatmaz.

1 Eylül 2026 operatör sunumu kaydı: doğrulanmış FPGA olaylarındaki 75 kHz'e
kadar tepe oynaması yalnız arayüz/geçmiş katmanında tek emisyon satırına
gruplanır; ham olay kimliği ve ölçüm penceresi değiştirilmez. Canlı sayaç geçmiş
satırlarını dışlar, baskın güncel olay P/N oranına göre seçilir ve eski kayıt
spektrumda canlı kılavuz üretmez. Geniş host kaba adayı ile tek LO FPGA sonucu
sarı, iki ayarda yeniden görülen RF adayı yeşil gösterilir. Yakın alan
doyum riskini azaltmak için varsayılan LNA/VGA 16/16 dB'dir. Yazılım testleri
sunum sözleşmesini doğrular; fiziksel yanlış alarm, kaçırma ve kontrollü TX
kapalı/açık kabulü açık kaldığından bu kayıt KTR-4.1'i kapatmaz.

31 Ağustos 2026 geniş bant temel kayıt: ADR-0037, KTR-4.1'in mevcut
rank-24/32 OS-CFAR ve 41–256 bin bölgesel yolunu değiştirmeden 257 bin ve üzeri
desteklere dördüncü bölge sıra istatistiği ile iki taraflı tam-bölge kontrolü
ekler. Yazılım/sabit nokta/SystemVerilog vektörlerinde 512 ve 2048 bin pozitif,
12 dB basamak negatif dahil sekiz karede 24 geniş aday / 27 kayıt; birleşik
azaltıcıda 63 aday / 65 kayıt ve paket sınırında 379 AXI64 beat sıfır metadata
farkıyla geçmiştir. 1 Eylül'de güncel tam Vivado yapısı 50 MHz setup/hold,
yönlendirme, DRC, bitstream ve XSA kapılarını geçmiştir. Kart yükleme ve
kontrollü RF kabulü açık olduğundan bu kayıt KTR-4.1'i tamamlamaz ve eski
fiziksel imajı kendiliğinden güncellemez.

31 Ağustos 2026 tarama kenarı kaydı: sahiplik adımı 600 kHz'e indirilmiş ve
örtüşen 2 MHz ayarlar merkezi kendi hücresinde olan 1 MHz desteği en az bir
ayarın ±800 kHz kanal seçici geçiş bandında tutacak şekilde test edilmiştir.
257 hücre ve üzeri adayın bağımsız yeniden ayar doğrulaması tepe hücresi yerine
mutlak destek aralığı örtüşmesine bağlanmış; tepe konumu 800 kHz'den fazla
değişen 1 MHz sentetik aday doğrulanmıştır. Bu yazılım/geometri kanıtıdır;
güncel kart, kontrollü RF, bütün pencere işgali ve Pd/Pfa kabulü açık kalır.
Kanıt `results/evidence/phase08/survey-overlap-v1.json` dosyasındadır.

31 Ağustos 2026 geniş host kaba arama kaydı: ADR-0038, 8 MS/s görüntü FFT
gücünü dörder hücre enerji toplamıyla kanonik 4.096 hücrelik tespit profiline
bağlar. Kaba RX adayları arayüzde FPGA tespitinden ayrı gösterilir. Bağımsız
sentetik kabulte 100 kHz–4 MHz aileleri 32/32; düz, 12 dB eğimli ve 12 dB
basamaklı negatifler 0/32 geçmiştir. 6 MHz 31/32 ile yalnız karakterize edilmiş,
8 MHz tam doluluk 0/32 ile açık sınırı korumuştur. Host sonucu RF/FPGA kabulü
değildir ve KTR-4.1'i tamamlamaz. Kanıt
`results/evidence/phase08/coarse-rx-detection-v1.json` dosyasındadır.

Kullanıcının paylaştığı 2026 şartnamesindeki **5.1.1 Sinyal Tespiti**,
bu depodaki tarihsel `KTR-4.1` ve `KTR-4.1-OPS-B0` satırlarıyla eşleştirilir;
eski kimlikler ve ET maddeleri yeniden numaralandırılmaz. Frekansı bilinmeyen
yayın için 1 MHz–6 GHz sıralı RX taraması, gerçek kart yanıtlı kapsama kaydı,
geçmiş gözlemler ve sabit bant izlemeye geçiş PHASE-08 kapsamındadır.
`tests/test_rx_survey.py` kapsam/iptal/hata ayrımını,
`tests/test_windows_receive_pipe.py` ikili I/Q bütünlüğünü denetler.
`scripts/check_rx_survey.py` fiziksel alıcı denemesi için ayrı kayıt üretir.
Durum: uygulandı, sınırlı alıcı denemesi var; tam bant kör RF deneyi, anten
kapsamı, kaçırma/yanlış alarm oranı ve şartname saha kabulü **açık**.

4 Eylül 2026 ST-04 başlangıç ölçümünde 20 MHz–6 GHz aralığının resmî
`hackrf_sweep` ile 1 MHz hücreli tek RX-only turu 0,798792 saniye ve sıfır kapsam
boşluğuyla tamamlanmıştır. Mevcut 600 kHz sorumluluklu 2 MHz FPGA/ARM taraması
aynı aralıkta yalnız ham önek için 9.967 pencere / 2.612,789248 saniye; mevcut
DC-güvenli 8 MS/s kaba plan üç gözlemle 2.392 pencere / 14,696448 saniye alt
sınırı üretir. Kaynak ve ham CSV hashleri
`results/evidence/phase08/st04-search-profile-baseline-v1.json` içindedir. Bu
karşılaştırma host kaba arama fizibilitesidir; FPGA tespiti, RF doğruluğu,
Pd/Pfa, kısa yayın yakalama veya ST-04 kapanışı değildir. Doğrudan ZedBoard USB
OTG bağlantısı anlık RF bandını genişleten bir özellik sayılmaz ve ayrı taşıma /
PetaLinux / PS→PL kabulü olmadan seçilmiş mimari değildir.

ST-04 tekrarlı çözünürlük ölçümünde 1 MHz, 100 kHz ve 25 kHz istenen hücre
genişliklerinin her biri üç bağımsız süreçte üçer turla denenmiştir. 27/27
RX-only tur 20 MHz–6 GHz aralığını sıfır boşlukla kapatmış, USB shortfall
sayacı ölçüm sonunda sıfır kalmıştır. Tur başına süreç medyanları 0,768583 /
0,764985 / 0,794019 saniye; ham çıktı medyanları yaklaşık 129 kB / 568 kB /
2,00 MB'dır. Araç gerçek hücre genişliklerini 1 MHz / 98,03922 kHz /
24,87562 kHz üretmiştir. Süre medyanlarının %3,80 içinde olması çözünürlük
seçimi için RF doğruluk kanıtı değildir; yaklaşık 15,57 kat çıktı yükü aynı-IQ
ve kontrollü kör yayın ölçümüyle birlikte değerlendirilecektir. Kaynak ve ham
arşiv hashleri `results/evidence/phase08/st04-sweep-resolution-v1.json`
içindedir. KTR-4.1'in Pd/Pfa ve bilinmeyen yayın kabulü açık kalır.

Aynı-I/Q çözünürlük karşılaştırması iki LO'daki 955,7 MHz açık/kapalı fiziksel
kayıtların aynı 0,507904 saniyelik bölümünü kullanmıştır. Truth frekansı aday
üretimine verilmeden 4.096 ve 8.192 FFT hedefi kaçırmış; 16.384 FFT hedefi iki
LO'da geri kazanmış ve kapalı kayıtta ortak aday üretmemiştir. 32.768 ve 65.536
FFT hedefi geri kazanırken kapalı kayıtta sırasıyla bir ve üç ortak aday
üretmiştir. Bu sonuç yalnız açıklanmış tek frekans kaydını karakterize eder;
16.384 değeri farklı bant, yayın ailesi, seviye ve kör holdout tamamlanmadan
ürün profili olarak yeniden seçilmiş sayılmaz. Kanıt
`results/evidence/phase08/st04-same-iq-resolution-v1.json` dosyasındadır.

ADR-0041 kontrollü kör deney mimarisini 20 MS/s / 25 kHz host tam bant adayı,
8 MS/s / 16.384 FFT iki-LO host RX kanıtı ve 2 MS/s / 4.096 FFT FPGA/ARM
ayrıntılı karar olarak kilitler. Mevcut RTL 991,375 kare/s işlevsel kapasiteyle
2 MS/s gereksinimini karşılar; aynı 4.096-hücre zincirin doğrudan 8 MS/s
gereksiniminin yalnız %50,76'sına ulaşır. Route tasarımının %90,30 LUT
kullanımı yeni geniş FPGA yolunun ölçülmeden kabul edilmesine izin vermez.
Karar kaydı
`results/evidence/phase08/st04-hierarchical-detection-architecture-v1.json`
dosyasındadır. ST-04 mimari seçimi tamamlanmıştır; profil ürün kabulü ve
KTR-4.1 saha kabulü değildir.

4 Eylül 2026 ST-05 çalışmasında dar bant OS-CFAR değiştirilmeden çok ölçekli
geniş bant Python referansı seçilmiştir. Önceden dondurulmuş 15 sahne ve sahne
başına 64 holdout dizisinin tamamı beklenen kapıları geçmiştir. Gürültü, kenar,
tam-pencere tanımlanabilirliği, yakın/uzak güçlü-zayıf yayın, birleştirme ve
zamansal aileler ayrı ölçülmüştür. Sonuç
`results/evidence/phase08/st05-wideband-holdout-v2.json` içindedir. V2'de her
gerçek desteğin ayrı adaya eşlenmesi zorunludur; eşikler ve holdout değişmemiştir.
Bu kayıt
ST-05 algoritma seçimini tamamlar; FPGA/ARM uygulaması, fiziksel RF Pd/Pfa,
ürün bağlantısı ve KTR-4.1 saha kabulü değildir.

5 Eylül 2026 ST-06 ürün uygulamasında Hann/FFT/UQ28.30 güç/OS-CFAR PL'de,
sekiz karelik geniş bant karar ve temporal olay yaşam döngüsü ARM'da tutulmuştur.
Routed Zynq-7020 tasarımı `%36,82` LUT ile 50 MHz zamanlamayı; dört derinlikli
CPU0 DMA/CPU1 detector profili ise beş fiziksel tekrarda en az `551,2206
kare/s` ile 2 MS/s kapasite kapısını geçmiştir. Güncel kaynak, XSA, bitstream,
ARM ikilisi ve PetaLinux ürün imajı
`results/evidence/phase08/st06-product-integration-v1.json` ile hash-bağlıdır;
5.679 paket ve 6.090 tam imaj görevinin tamamı geçmiştir. Bu, KTR-4.1 için
uygulama/derleme kanıtıdır. Aynı imajın kartta soğuk açılışı, fiziksel ürün
hizmeti ve frekansı saklı kontrollü RF Pd/Pfa kabulü açık kalır.

Eski fiziksel özetler yalnız kaydettikleri kaynak sürümünün kanıtıdır. Yeni
tarama/Windows taşıma kaynakları için bu arşivlerin hash kapıları geçilmiş
sayılmaz; yeni alımlar `build/acceptance/rx-survey/` altında saklanır.

19 Eylül 2026 KTR-4.3 kanal sahipliği regresyonu, seçili frekansı ölçülen
sınırları içinde taşıyan tek güncel FPGA olayını yalnız `50 kHz` izleme
toleransında kalan yakın adaydan ayırır. Seçili frekansta iki gerçek örtüşme
yine fail-closed reddedilir. Bu kaynak testi fiziksel RF kabulü değildir.

Bu matris yarışma görevlerini ve genel algoritma sırasını gerçek referans donanıma eşler. KTR teknik parametrelerin veya sayısal performans hedeflerinin bağlayıcı kaynağı değildir. Hiçbir satır tamamlanmış bir DSP/RF yeteneği iddiası değildir.

| Gereksinim kimliği | KTR bölümü | Beklenen işlev | Yeni donanımla uygulanma yöntemi | Planlanan faz | Doğrulama yöntemi | Durum |
|---|---|---|---|---|---|---|
| KTR-4.1 | 4.1 Sinyal Tespiti | Aday RF sinyallerini tespit etme | KTR yöntemi OS-CFAR/local adaptive; sayısal değerler ayrı `P0_OS_CFAR_EXPONENTIAL_PFA_1E4` profilidir: 16 reference/yan, 4 guard/yan, rank 24/32, Pfa `1e-4`, alpha `8.58014304069906`, strict `>`; ADR-0028 yalnız tam 41-bin OS penceresinden geniş desteklerde 16×256 median tabanlı, 32-bin bütünleşik enerji önerisi ekler; ADR-0030 ile PL Hann/FFT/güce OS-CFAR hücre kararı eklenir; ADR-0033 sürekli tespitte final OS+geniş bant aday kümesini seyrek PL→PS sınırına taşır, temporal PS'de kalır | P0 Mandatory Closure Block A / geniş bant ve throughput düzeltmesi | 1.038.336 CUT empirical FAR; Python↔portable C OS ve çok ölçekli aday eşdeğerliği; 256 geniş bant, 7.168 gürültü, 4.992 yerel sinyal ve 128 temporal dizi; fiziksel FPGA güç→ARM→ABI v1→2/3; ADR-0029 fiziksel hizmet kapısı; ADR-0030 45.056 kelime bit-doğru RTL ve Zynq-7020 post-route 50 MHz setup/hold; ADR-0031 paket/typed 33 kare/1.501 aday sıfır fark; ADR-0032 strict/trusted host çıktıları sıfır fark; ADR-0033 14 kare final aday/metadata/packet sıfır fark, median+geniş bant RTL'de 8 kare/24 aday/27 AXI kaydı ve final reducer RTL'de 8 kare/63 aday/65 AXI kaydı sıfır metadata farkı; final reducer → PHASE-06I AXI64 packetizer bağlantısı 8 kare/63 aday/379 beat ve 37 backpressure kararlılık kontrolüyle sıfır fark; CI8→Hann→AMD 4096 FFT→güç→final reducer→PHASE-06I paket tam kart tasarımında Vivado sentez/route/timing/bitstream/XSA kapıları | Hann katsayı bağı düzeltilen imaj PetaLinux 6.090/6.090 derleme ve fiziksel ZedBoard boot kapılarını geçti. Dondurulmuş CI8 bilinen-ton karesinde 2.224 bayt fiziksel paket, 54 nihai aday ve bütün metadata alanları bit-doğru referansla eşdeğerdir; DMA timeout/error sıfırdır. Üç pozitif ve iki sıfır karelik servis dizisi 54 olayda 2-of-3 confirmation ve iki-miss expiry davranışını geçti. Güncel ABI v3 PetaLinux paketi ve tam imaj 6.090/6.090 görevle derlendi. ADR-0040 işletim imajında doğrudan kabloya bağlı `192.168.7.2:47007` köprüsü yalnız `192.168.7.1` eşine izin verecek ve başarısız başlangıçta kart hizmetini durduracak biçimde açılış yaşam döngüsüne bağlandı; P09 imajında kalıcıdır. SHA-256 değeri `070d3dc0c6e3bf4b91513cb54597213b677e83ef1e640588a21fc0340eed2548` olan P09 imajının soğuk açılışında kurulu ikili hash eşitliği ve bit-doğru yaşam döngüsü yeniden doğrulandı. ADR-0034 dört derinlikli sınırlı yerel istek kuyruğuyla beş fiziksel koşuda toplam 20.480/20.480 kareyi sıfır hatayla işledi; en düşük/ortalama/en yüksek hız `508,759225230 / 509,458386609 / 509,884071480 kare/s`, gerekli alt sınır `488,28125 kare/s` ve en düşük marj `1,041938893` olduğundan kart içi 2 MS/s hizmet kapısı tekrarlanabilir biçimde kapanmıştır. HackRF host RX ve tespit 5/5 fiziksel koşuda geçti. ADR-0036 kayıtlı CI8 verisini doğrudan 1 Gbps Ethenet üzerinden ZedBoard hizmetine taşıyan beş koşuda 20.480/20.480 ölçüm karesini sıfır sıra hatası ve sıfır aday düşümüyle tamamlamıştır. Kalıcı ağ köprüsüyle kesintisiz canlı HackRF→FPGA yolu ayrıca beş koşuda 20.480/20.480 ölçüm karesi ve sıfır USB overrun/sıra hatasıyla geçmiştir. Ürün QML bağı fiziksel olarak beş ardışık 4.096-kare oturumunda geçti: 20.480 kare, sıfır USB taşması/CRC/sıra hatası/kırpılma. Kanıt: `results/evidence/phase08/product-live-acceptance.json`. Sınırlı ham RX kuyruğuyla güncel ürün sekiz tam fiziksel koşuda 32.768 kareyi sıfır USB/taşıma hatasıyla işlemiş; 750. karede operatör iptali ve ardından tam yeniden başlatma geçmiştir. Kanıt: `results/evidence/phase08/detection-ui-decoupling.json`. Kesintisiz 15 dakikalık dayanıklılık kabulü 439.453/439.453 kareyi ve 14.399.995.904 ham baytı sıfır USB/CRC/sıra/kuyruk hatası ve sıfır kırpılmayla tamamlamıştır. Kanıt: `results/evidence/phase08/live-rx-endurance.json`. Canlı parametre ürün bağı dört ardışık gerçek FPGA karesiyle işlevsel olarak geçmiştir. ADR-0037 güncel geniş bant RTL'si için yazılım/sabit nokta/SystemVerilog eşdeğerliği ve tam Vivado 50 MHz sentez/route/timing/bitstream/XSA kapısı geçmiştir. Güncel imaj kayıtlı fiziksel HackRF I/Q ile Ethenet→PS/DMA→PL yolunda iki LO oturumunda hedef tepeyi 119/120 ve 118/120 karede geri kazanmış; eski imaj iki oturumda 0/120 üretmiştir. CRC/sıra/kuyruk hatası sıfırdır; kanıt `results/evidence/phase08/fpga-p2-wideband-physical-replay.json`. Kontrollü canlı RF doğruluğu, canlı ses ve saha kalibrasyonu açıktır |
| KTR-4.2 | 4.2 Parametre Çıkarımı | Tespit edilen sinyal parametrelerini çıkarma | Operatör onaylı izole aralıkta dört ardışık confirmed+observed kare; PL Hann→4096 FFT→güç; ARM'da ayrı gözlenen taşıyıcı, emisyon merkezi, ITU-R SM.443 yaklaşımıyla OBW99, kalibre edilmemiş kanal dBFS ve SNR; alan bazlı fail-closed sonuç | P0 Mandatory Closure Block A / kontrollü ARM bağı | F5 binding 40/40 ve OOS 24/24; 33 sahnede ARM C11 ↔ host F5 eşdeğerliği; `P0PM-v1` CRC/kimlik/profil retleri; gerçek ZedBoard'da altı sayısal sahne PL→ARM karşılaştırması; yapay katsayılı kalibrasyon API negatifleri | İlk üç teknik parametrenin ürün hesap yolu PC kestirimci fallback'i olmadan FPGA/ARM'a bağlandı. Kart sahnelerinde merkez/taşıyıcı/kenar/OBW azami farkı 0,02057 Hz altında, güç/SNR farkı 0,000100 dB altında kaldı; bastırılmış taşıyıcı `gözlenmedi` döndü. Bu sayısal entegrasyon kanıtıdır. Kalıcı imaj dört yeniden başlatmada geçti. Bağımsız sayısal tanıda güç hatası en çok 0,189 dB; merkez hatası 10,209 kHz ve aralık dışı BPSK OBW hatası 325,644 kHz oldu. Kontrollü HackRF RF doğruluğu, mutlak frekans referansı, dBm kalibrasyonu ve analog/sayısal ayrımı açıktır |
| KTR-4.2-F1 | 4.2 Parametre Çıkarımı | PHASE-04 ürün yeteneğini alan bazlı doğrulama | Emisyon merkez frekansı, ayrı gözlenen taşıyıcı frekansı, OBW99, kalibre edilmemiş kanal gücü/SNR; confirmed olay ve operatör onaylı izole span; alan bazlı abstention ve digest bağlı fail-closed profil | F1D/F2D/F3D/F4D tamamlandı ve başarısız; F5A-F5E tamamlandı; PÇ-02/PÇ-04 sayısal bağ uygulandı | F5 protokol/yöntem kilitleri, binding 40/40, OOS 24/24; 33 sahnelik C eşdeğerliği; altı sahnelik fiziksel PL/ARM entegrasyonu; bozuk CRC, profil ve kayıp bağ negatifleri | Canlı HackRF ölçüm komutu dört sabitlenmiş CI8 kareyi karta gönderir ve yalnız doğrulanmış PL/ARM yanıtını kaydeder; kart hatasında PC hesabına dönmez. Taşıyıcı çizgisi dahil sayısal alanlar ARM'dadır. Analog/sayısal alan ertelendi. Kontrollü RF doğruluğu, geniş bant fiziksel kapsama ve dBm kalibrasyonu açık |
| KTR-4.1-OPS | 4.1 Yarışma İş Akışı | Bilinmeyen, hakem bandı ve hakem frekansı girişleriyle sinyal varlığını doğrulama | Hz domainli `SearchRequest`; ortak replay/HackRF acquisition backend; `UNKNOWN`, `JUDGE_BAND`, `JUDGE_FREQUENCY`; frekans verilse de OS-CFAR ve confirmation atlanmaz; 600 kHz sorumluluk adımlı örtüşen ayar, ikinci fiziksel LO kontrolü ve kontrollü TX kapalı/açık fark sınıflandırması | P0 Mandatory Closure Block A + PHASE-08 | Üç pozitif replay demo; band dışı, yanlış frekans, NaN, ters band, zarf dışı ve aşırı-span negatifleri; Qt binding; tamamlanmış iki JSONL taramasında aynı ayar, mutlak RF eşleştirmesi ve en az 6 dB güç artışı oracle'ı | Replay/host modları ve canlı HackRF tarama/ikinci-LO ürün akışı uygulandı. Sabit bant 2/3 sonucu yalnız `FPGA adayı`; kontrollü A/B olmadan harici yayın sayılmaz. 1,3 GHz yakınında iki-LO fiziksel aday bir turda görüldü, sonraki turda yoktu. Kontrollü TX kapalı/açık fiziksel kabul, tam-pencere geniş yayın ve saha Pd/Pfa ölçümü açık |
| KTR-4.1-OPS-B0 | 4.1 Yarışma İş Akışı | Üç arama modunu seri seçili HackRF-1 RX'e hazırlama | RX-only `hackrf_transfer`, seri bağlı ED_RX config'i, 8 MS/s, ±100 kHz DC dışlama ve 500 kHz offset tuning | P0 Block B0 + PHASE-08 fiziksel RX | Toolchain self-test; discovery/ci8/argv/plan/mapping/queue/UI unit testleri; beş tekrarlı fiziksel bounded RX ve host tespit kabulü | Fiziksel HackRF tek cihaz ve yapılandırılmış seriyle eşleşti. Beş canlı koşuda toplam 81.920 kompleks önek eksiksiz, doyum sıfır ve her koşuda en az bir `LIVE_HACKRF` doğrulanmış aday elde edildi. Sürekli USB→kanal seçici→ZedBoard FPGA yolu ayrı 5/5 kabulde geçti. Ürün QML bağı, gerçek olay çözümü, yazılım iptal ve kart-yok fail-closed testleri geçti; beş fiziksel tam ürün oturumunda 20.480 kare hatasız tamamlandı. USB okuma, 512 karelik sınırlı ham-I/Q kuyruğuyla kanal seçimi ve FPGA taşımasından ayrılmıştır. Güncel ürün sekiz tam fiziksel oturumda 32.768 kareyi sıfır USB/taşıma hatasıyla işlemiş; 750. karede operatör iptali ve ardından yeniden başlatma geçmiştir. Hash-bağlı kanıt `results/evidence/phase08/detection-ui-decoupling.json` içindedir. Kesintisiz 15 dakikalık kabulde 439.453/439.453 kare ve 14.399.995.904 ham bayt sıfır USB/taşıma hatasıyla geçmiş; kuyruk tepe kullanımı 28/512 olmuştur. Hash-bağlı kanıt `results/evidence/phase08/live-rx-endurance.json` içindedir. Kontrollü RF doğruluğu kabulü açıktır |
| KTR-4.3 | 5.1.3 / 4.3 Sinyal İzleme ve Analog Dinleme | Tespit edilip parametreleri çıkarılan analog yayının sürekliliğini, zamansal/frekanssal davranışını izleme ve operatör denetiminde dinleme | Parametre ölçümünden emisyon merkezi/OBW aktarımı; yeni canlı oturumda yeniden FPGA doğrulaması; açık AM/NFM seçimi veya aynı kayıtla tek işlem AM/FM karşılaştırması; 5,001216 saniyelik sınırlı başlangıç I/Q halkası; ARM confirmed bağı, en az %95 gözlem, en çok 8 ardışık eksik kare ve sıra sürekliliği; ilk kapıdan sonra yalnız yeni yaklaşık 250 ms parçalar; durum koruyan bounded DDC, 129 tap kanal filtresi, 48 kHz resample, AM zarf/NFM faz-fark, DC/isteğe bağlı 200 Hz konuşma filtresi, 65 tap ses filtresi, yavaş AGC, mono PCM16 ve son 20 saniyelik WAV halkası; 250 ms dBFS güç/artık merkez frekansı izi; tutucu DTMF çözümü | PHASE-05 ve onaylı PHASE-08 canlı devamı | Deterministik AM/NFM clean ve 20 dB kapıları; bağımsız periodogram/korelasyon oracle'ı; bilinen −200…+200 Hz kayma; altı saniyelik NFM girdisinde tek parça/0,5 saniyelik parçalar arasında bit düzeyinde PCM16 eşitliği; DTMF `5#` kabulü ve tek-ton reddi; yalnız yeni canlı kare, tüketici-geride sıra boşluğu ve süreklilik negatifleri; QML canlı RX'in açık kalması, tespit/ofset/BW/süre/güç/frekans/DTMF/WAV bağları; korunmuş fiziksel HackRF NFM tekrarında 1.700 Hz ton için 0,048828 Hz hata ve sıfır kırpılma | Kısmi — kesintisiz AM/NFM PC akışı, sınırlı bellek, fail-closed sıra/süreklilik kapıları ve görünür 250 ms kanal izlemesi kaynak/sentetik testlerde doğrulandı. FPGA tespiti ve ARM yaşam döngüsü canlı kalır; demodülasyon, ses ve DTMF PC'dedir. Fiziksel NFM tekrar kaydı güncel DSP'de doğru tonu verdi, ancak içerik sentetik tondu ve yeni kesintisiz ürün/FPGA olayı bağıyla tekrar edilmedi. Kontrollü analog amatör telsiz konuşması, hoparlör gecikmesi/dropout, cihaz profiline uygun de-emphasis ve saha kabulü yoktur. DTMF dışındaki analog kodlar ve isteğe bağlı sayısal telsiz protokolü uygulanmadı |
| KTR-4.4 | 5.1.4 / 4.4 Yön Bulma | Sinyal geliş yönünü yaklaşık belirleme ve derece RMS ile değerlendirme | HackRF-1 ve uygun yönlü antenle manuel dönüş; seçili hedef kanalında dört taze karelik P0PM-v4 toplam dBFS ölçümü; sabit frekans/kanal/kare/LNA/VGA bağı; `0°` doğrulanmış başlangıçtan saat yönünde ilk lob dışı sınır, `0°`a dönüşten sonra ters yöndeki sınır, sınırlar içinde 5° tepe hassaslaştırması ve tek karşı-yön ölçümü; 3 dB tepe/ön-arka kapıları; bağıl ham maksimum LOB. Lob dışı nokta başarısızlık değil gözlem maskeli kilitli kanal ölçümüdür. Sensör/enkoder ve doğrulanmış coğrafi referans yokken gerçek kuzey, harita, hedef konumu veya coğrafi kerteriz üretilmez | PHASE-09 uyarlamalı saha öncesi entegrasyon ve geçici kart çalışma zamanı tamam; fiziksel RMS kabulü açık / P0 Mandatory EH Core | Uyarlamalı sıra ve sınır birim testleri; 61 sentetik yerel tepe sahnesi; bağımsız argmax, dairesel hata/RMS, ön/arka belirsizliği, ayar değişimi ve aynı-kare negatifleri; Python↔portable C sekiz hazır/ret sahnesinde ara metrik eşdeğerliği; doğrulanmış ZedBoard üzerinde sekiz P0DF ağ sahnesi; `P0DF-v1/P0FR-v1` CRC protokolü; canlı dört-kare PL/ARM güç ve `target_observed` bağı; QML/view-modelde sağ sınırdan sonra `0°`a dönüş ve 345° talimatı; tarihsel manuel referans ve harita regresyonu | `P0_AMPLITUDE_DF_ADAPTIVE_V2` sayısal 61/61 sahnede LOB üretti; portable C sekiz sahnede Python'la sıfır fark verdi; aynı sekiz durum geçici 47008 kart ağ yolunda geçti ve çalışan 47007 hizmeti `126a916d…` hash'iyle güncellendi. Eski tam-tur ve kalıcı SD kanıtı tarihsel `FIELD_V1` profilinde korunur, yeni profile aktarılmaz. SD imajı ve fiziksel HackRF/yönlü anten derece RMS tekrarı tamamlanmadan kalıcılık veya fiziksel doğruluk iddiası kurulmaz |
| KTR-4.5 | 4.5 Konum Belirleme | Yaklaşık verici konumu çıkarma | Bilinen iki ölçüm noktasından manuel LOB doğrularını birleştirme | Sonraki fazlar | Bilinen konumlu kontrollü hedeflerle hata analizi | Uygulanmadı |
| KTR-5.1 | 5.1 Sürekli Karıştırma | Kaynak KTR maddesi | Uygulama, arayüz, yapılandırma ve test yok | Kapsam dışı — kullanıcı kararı | Yok | ADR-0044 uyarınca ürün kapsamından çıkarıldı; tarihli eski kayıtlar güncel yetenek değildir |
| KTR-5.2 | 5.2 Arabakışlı Karıştırma | Kaynak KTR maddesi | Uygulama, arayüz, yapılandırma ve test yok | Kapsam dışı — kullanıcı kararı | Yok | ADR-0044 uyarınca ürün kapsamından çıkarıldı; tarihli eski kayıtlar güncel yetenek değildir |
| KTR-5.3 | 5.3 Analog Telsiz Aldatma | Kaynak KTR maddesi | Uygulama, arayüz, yapılandırma ve test yok | Kapsam dışı — kullanıcı kararı | Yok | ADR-0044 uyarınca ürün kapsamından çıkarıldı; tarihli eski kayıtlar güncel yetenek değildir |
| KTR-5.4 | 5.4 GNSS Aldatma | Kaynak KTR maddesi | Uygulama, arayüz, yapılandırma ve test yok | Kapsam dışı — kullanıcı kararı | Yok | ADR-0044 uyarınca ürün kapsamından çıkarıldı; tarihli eski kayıtlar güncel yetenek değildir |
| KTR-6 | 6 Simülasyon ve Test | Modelleri ve donanım uygulamasını doğrulama | Deterministik veri, PHASE-06A–J kanıtları, P0 OS-CFAR/parametre/DF host modelleri ve gerçek PS↔DMA↔PL Vivado blok tasarımı | P0 Mandatory EH Core | Golden ölçümler, C eşdeğerliği, Qt binding/lifecycle, 16-bit DMA length Vivado BD/sentez/route/timing/bitstream/XSA, PetaLinux device-tree/modül/rootfs/boot derlemesi, fiziksel boot/FCLK/DMA, PHASE-07 kanal seçici/çift CRC/TCP→yerel hizmet loopback ve repository regresyonu | ADR-0037 öncesi CI8→aday-paket imajı ZedBoard'da DONE/UART/Linux, FPGA `operating`, DMA ve 54-aday bit-doğru paket kapılarını geçti. Beş karelik fiziksel servis dizisi 2-of-3 confirmation ve expiry alanlarında host oracle ile eşdeğerdir. Beş bağımsız 4.096-kare kart içi koşuda toplam 20.480 kare sıfır işlevsel hatayla işlendi; en düşük hız `508,759225230 kare/s` ve marj `1,041938893` ile 2 MS/s yerel hizmet kapısı geçti. Güncel ADR-0040 RTL/C kaynakları Vivado 50 MHz sentez/route/timing/bitstream/XSA, PetaLinux P09 kalıcı soğuk açılış ve 20.480 karelik dijital kart kabulünü geçmiştir; kör canlı RF Pd/Pfa kabulü açıktır. HackRF bounded host RX 5/5 geçti. PHASE-07 host alt kapısında 8→2 MS/s anti-alias kanal seçici, sürüm 2 çift CRC, portable C decoder ve dört derinlikli Linux ağ köprüsü loopback'i geçti. Köprünün PetaLinux kurulumu, fiziksel Ethenet ve güncel P09 kart kabulü geçti; kalibrasyon ve kör canlı RF Pd/Pfa kabulü açıktır |

PHASE-08 FPGA-bağlı dayanıklılık yeniden kabulü, üstteki KTR-4.1 ve
KTR-4.1-OPS-B0 satırlarındaki ilk koşunun yerine kendi kaynak sürümündeki v2
kaydını geçirir. V2
koşusu 439.453/439.453 kare ve 14.399.995.904 ham baytı sıfır USB/CRC/sıra/
kuyruk hatası ve sıfır kırpılmayla tamamlamış; ham RX kuyruğu en fazla 170/512
kullanılmıştır. Bu sürümün hash-bağlı kanıtı
`results/evidence/phase08/live-rx-endurance-v2.json` dosyasındadır; v1 tarihsel
kayıt olarak korunur. Güncel RX/görüntü kaynak sürümünün RX-only 15 dakikalık
kabulü `results/evidence/phase08/live-rx-display-8msps-v1.json` dosyasındadır
ve artık tarihsel kaynak sürümüne aittir. Güncel ADR-0039 sürümünün
`live-rx-display-8msps-v2.json` koşusu USB shortfall nedeniyle başarısızdır;
FPGA tespit veya taşıma kabulü sayılmaz.

## PHASE-07 kalıcı imaj güncellemesi

KTR-4.1 ve KTR-6 için ağ köprüsünün kalıcı imajda açık olduğu önceki kayıtların
yerine şu sonuç geçer: SHA-256 değeri
`5d749d4c2a8a86f2bbcc3be9a700ea32efc8104196b237700740886003e2e61d` olan
PetaLinux imajı soğuk açılıştan sonra FPGA `operating` durumuyla başlamış ve
MAC tabanlı adı değişen tek fiziksel ağ arayüzünü `auto` seçmiştir. Beş fiziksel
Ethenet koşusunda 20.480/20.480 ölçüm karesi sıfır sıra hatası ve sıfır aday
düşümüyle tamamlanmış; en düşük hız `505,184524010 kare/s`, gerekli alt sınır
`488,28125 kare/s` olmuştur. Tek süreçli canlı HackRF→kanal seçici→Ethenet→
ZedBoard→FPGA kabulü beş koşuda ayrıca geçmiştir: 20.480/20.480 ölçüm karesi,
sıfır USB overrun, sıfır sıra hatası, 32.927 FPGA adayı ve
`488,746900919 kare/s` en düşük hız. Bu kayıt KTR-4.1, KTR-4.1-OPS-B0 ve KTR-6
satırlarındaki sürekli USB/ZedBoard/FPGA yolunun açık olduğuna dair eski sınırı
geçersiz kılar; ürün UI, dBm kalibrasyonu ve saha doğruluğu kapsam dışıdır.

## Operatör uygulaması sağlamlaştırma izlenebilirliği

APP-A–F iş paketleri roadmap fazlarını ilerletmez ve algoritma sonucunu değiştirmez.
Amaç, aşağıdaki KTR yüzeylerinde ürün, laboratuvar ve doğrulama sınırlarını açık
tutmaktır.

| Bakım kimliği | Bağlı KTR yüzeyi | Korunan sınır | Doğrulama |
|---|---|---|---|
| APP-A | KTR-4.1-OPS, KTR-4.2, KTR-4.3, KTR-4.4, KTR-6 | Mevcut davranış değiştirilmeden code review, test baseline'ı ve mock/golden/gerçek veri envanteri | `docs/reviews/APP_CODE_REVIEW_BASELINE.md`, `docs/reviews/REPOSITORY_DISPOSITION.md` |
| APP-B | KTR-6 | Golden ve normalized evidence korunarak yalnız onaylı artıkların temizlenmesi | SHA-256 yerel veri manifesti; salt-okunur PHASE-00 repository kapısı; 48/48 kapsam regresyonu geçti; APP-C kapı devri 2026-08-23 tarihinde kullanıcı tarafından onaylandı |
| APP-C | KTR-4.1-OPS, KTR-4.3, KTR-4.4 | Üretim uygulamasının mock/eğitim/offline laboratuvar kaynaklarından ayrılması; canlı olmayan yeteneğin canlı gösterilmemesi | ADR-0024; `config/app/product-package.json`; izole runtime import testi; ürün UI kaynak-doğruluk ve deploy-spec testleri |
| APP-D | KTR-4.1–4.4, KTR-6 | Uygulama, algoritma, platform ve doğrulama katmanlarının taşınırken davranış ve sahiplik koruması | Import sözleşmesi, golden/RTL regresyonu ve KTR yol güncellemesi |
| APP-E | KTR-4.1-OPS, KTR-4.2–4.4 | Görev terminolojisi, bilgi mimarisi ve teknoloji kararının ölçülerek dondurulması | Kullanılabilirlik senaryoları, A/B performans ve ekran ölçeği kanıtı |
| APP-F | KTR-4.1-OPS, KTR-4.2–4.4 | Yalnız uygulanmış ve doğrulanmış ED özelliklerini sunan görev odaklı operatör uygulaması | ADR-0027 ve ADR-0044; gerçek SigMF uçtan uca işleme; gerçek HackRF araç/cihaz probe durumu; QML ürün sınırı; 1280×720, 1366×768, 1920×1080 ve %150 render; 10 Hz, heartbeat, bounded çizim, Türkçe metin ve paketleme kapıları |
| RX-GRC | KTR-4.1-OPS-B0 | Seri numarasına bağlı yalnız RX spektrum/spektrogram/IQ gözlemi; TX bloğu ve otomatik bozulma kararı yok | `digital_analog_detection/hackrf_rx_interference_monitor.grc`; GNU Radio 3.10.12 derleme geçişi ve canlı pencere gözlemi; belirli yayın açık/kapalı ölçümü ve ST-06 kabulü açık |

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
görev alanında sabit yükseklikte kalırken ölçüm ve dinleme ayarları bağımsız kaydırılır; taslak ayrıca
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
Onuncu bakım paketi canlı tespit listesindeki manuel dondurma denetimini
kaldırmıştır. Görünür olayların ölçüme uygun son dört ardışık FPGA karesi sınırlı
bir önbellekte otomatik korunur; seçili olay kaybolsa bile yakın frekanstaki yeni
kimliğe aktarılmaz. Gerçek HackRF→ZedBoard ürün oturumunda seçili confirmed olay,
operatör onaylı analiz aralığı, dört ardışık I/Q kare kimliği ve dokuz parametre
alanı hash-bağlı kanıtla geçmiştir. Bu sonuç işlevsel ürün bağını kanıtlar;
kontrollü RF doğruluğu, dBm kalibrasyonu veya sinyal türü doğruluğu iddiası eklemez.
On birinci bakım paketi ED görev gezinmesini `Sinyal Tespiti` ve `Parametre
Çıkarımı` için ayrı operatör girişlerine ayırmış, seçili olay ile ortak
spektrum/spektrogram bağlamını korumuştur. Canlı analog dinleme için host kanal
seçicisinin karta gönderilmiş ve yanıtı doğrulanmış ardışık I/Q karelerinden
5,001216 saniyelik sınırlı tampon eklenmiştir; FPGA I/Q geri döndürmez. Sıra
boşluğu tamponu temizler ve demodülasyon yalnız seçili olay pencerenin her
karesinde confirmed+observed ise başlatılabilir. Bu bakım KTR-4.2 ve KTR-4.3 ürün bağını
iyileştirir; fiziksel RF doğruluk veya ses aygıtı kabulü oluşturmaz.

On ikinci bakım paketi, KTR-4.1 yarışma taramasında FPGA aday listesini
tamamlayan yerel kanal-gücü sıralamasını eklemiştir. ±10 pencerelik yerel
medyan, adayın ±2 komşusunu referans dışında bırakır; yalnız en az 6 dB yükselen
ve en az iki bitişik 600 kHz sorumluluk penceresinde süren bölgeler öne çıkar.
İki tam 1490–1600 MHz fiziksel turda aynı 1587,5 MHz tepe penceresi bulunmuş;
ham I/Q iki bağımsız LO ayarında 1.586.923.828,125 Hz tepesini 0 Hz farkla
yeniden üretmiştir. Host çok ölçekli yol tepeyi 120/120 ve 119/120 karede,
karttaki önceki bitstream ise 0/120 ve 0/120 karede kapsamıştır. Yeni sunum
yalnız 1585,3–1588,5 MHz bölgesini +9,04 dB yerel farkla öne çıkarır. Bu sonuç
RX enerji tanısıdır; dış verici kimliği, kontrollü A/B, Pd/Pfa veya güncel
bitstream fiziksel kabulü değildir. PHASE-08 açık kalır.

Harici yayın yeniden ayarlandıktan sonraki üçüncü 1490–1600 MHz turu 184/184
pencereyi 95,65 saniyede sıfır hatayla tamamlamıştır. Önceki 1586,9 MHz enerji
bölgesinin aynı yerde kalması onun test vericisine atfedilmesini engellemiştir.
1595,3 MHz çevresindeki iki-LO PSD deseni 0,916 korelasyon ve kart/host tarafında
120/120 kare kapsamı üretmiş, ancak tam turlar arasındaki +4,10 dB fark kilitli
+6 dB A/B sınırını geçmemiştir. KTR-4.1 bakım sunumu bunu yalnız `kararlı RF
adayı` olarak gösterebilir; `harici verici doğrulandı` iddiası kontrollü TX kapalı
referans ve aynı ayarlı TX açık tur olmadan üretilemez.

On üçüncü bakım paketi KTR-4.1 operatör akışını iki göreve indirmiştir: sabit
frekansta tarama ve bant taraması. Sonraki bağlantı bakımıyla alıcı açılışta
otomatik denetlenmez; operatör `Sistemi Denetle` eylemini açıkça başlatır. Frekans,
LNA ve VGA kontrolleri korunurken SigMF seçimi, olay konsolu, görünür
yakınlaştırma/geçmiş, taban/aralık ve tepe-tut kontrolleri yarışma yüzeyinden
kaldırılmıştır. Kayıtlı I/Q arka ucu yalnız hash-bağlı tekrarlanabilir doğrulama
için kalır. İlgili canlı görünüm, tarama ve ürün sınırı koşusu 98/98 geçmiştir.
Bu bakım detector eşiklerini veya kontrollü RF kabul sınırını değiştirmez.

On dördüncü bakım paketi KTR-4.1 sabit bant yüzeyinde tekil durum sunumunu
zorunlu kılmıştır. Ürün logo ile `BÂZ` kimliğini kullanır; bağlantı veya
alım hatası yalnız alıcı ayarlarında neden ve kurtarma eylemiyle gösterilir. Geçerli
spektrum öneği yokken FPGA izleme penceresi, merkez çizgisi ve aday kılavuzu
çizilmez. Ham 2/3 öncesi aday denetimi yarışma yüzeyinden kaldırılmış, yalnız
kararlı aday listesi korunmuştur. Değişiklik eşik/RTL/ARM davranışını etkilemez;
canlı görünüm ve ürün sınırı regresyonu 98/98 geçmiştir.

1 Eylül seçenek menüsü bakımında ana görev şeridi başlangıçta kapatılmış; `Tespit`,
`Parametre`, `Dinleme`, `Yön Bulma` ve `Sistem` girişleri `BÂZ` logosuna bağlı
erişilebilir aç/kapat menüsüne taşınmıştır. `Alıcı Ayarları` da başlangıçta kapalıdır
ve açılan görev şeridindeki `Tespit` sembolüyle yönetilir. Tespit sembolü başka
bir görevden kullanılırsa ED/Tespit sabit-frekans yüzeyine döner; view-model
başlatma, durdurma veya donanım denetimi çağrısı yapmaz. Bu yalnız
`KTR-4.1-OPS-B0` sunum bağıdır; RX/FPGA işleyişi veya faz durumu değişmez.

Aynı gün yapılan hazır-durum bakımında canlı oturumun FPGA hizmet/taşıma erişim
hataları önceki birleşik `Hazır` yetkisini ve tarama başlatma iznini iptal eder;
yeniden açık HackRF+FPGA denetimi gerekir. Üst başlıktaki bağlantı başlığı, hata
metni ve durum rozeti kaldırılmıştır. ED/ET görev seçimi başlığın sağ kenarına
taşınmıştır. Bağlantı ve alım hataları yalnız `Alıcı Ayarları` işlem alanında
gösterilir. Son görünüm bakımında marka işaretinin koyu zemindeki okunurluğu beyaz
ön plan ile arkasındaki hale katmanlanarak artırılmış; ED/ET ayırıcısı ve görev için gereksiz
açıklamalar kaldırılmış; spektrum başlıkları grafiklere ortalanmıştır. Bu sunum ve
ardından sabit bant dış marjı kaldırılarak alıcı sütunu ortalanmış ve tespit
ayırıcısı tam yüksekliğe bağlanmıştır. Spektrum tuvali dört kenara genişletilmiş,
ızgara hücreleri görünür en-boy oranına göre kareye yakın tutulmuş ve
tespit başlığı diğer grafik başlıklarıyla aynı ölçüde ortalanmıştır. Bu sunum ve
fail-closed yetki bağı algoritma, RTL veya fiziksel
doğruluk kabulü değildir.

On beşinci bakım paketi sabit bant iki-LO doğrulamasındaki merkez/DC hatasını
gidermiştir. Aday doğrulama çıkış merkezinden 300 kHz uzakta yürütülür. Aynı
HackRF→kanal seçici→ZedBoard/FPGA oturumundaki 8 MHz alıcı spektrumu, FPGA/ARM
2/3 olayının canlı dalga biçiminde seyrek kaldığı durumda ayrı ve açıkça
etiketlenen iki-LO kanıtı sağlar. 900,183 MHz kontrollü tanı adayı iki fiziksel
LO'da 79/79 RX karesi ve 22 dB üzeri P/N ile tekrar bulunmuş; FPGA zamansal
olayı 0/0 kaldığı için ürün bunu `RX çift ayar` olarak sunmuştur. Bu bakım FPGA
doğrulaması, verici kimliği, Pd/Pfa veya kalibre güç iddiası eklemez. Kanıt
`results/evidence/phase08/live-user-tx-on-off-900mhz.json` dosyasındadır.

2 Eylül 2026 KTR-4.1 sabit bant bakımında iki-LO kapısı iki farklı HackRF giriş
merkeziyle birlikte iki farklı FPGA çıkış merkezini zorunlu kılmıştır. Seri
bağlı ED_RX için fiziksel anten-sökme ve TX açık/kapalı ölçümüyle kanıtlanan
1 GHz dar spur profili eklenmiştir. Yalnız bu kalibre edilmiş ±5 kHz çekirdekte,
2–25 kHz omuz alanında yerel gürültünün 3 dB üstünde en az sekiz hücre şartı
aranır. Anten sökülü negatif koşu dört ayarda 0 hücreyle `not_reproduced`
olmuştur. Pozitif diye kaydedilen 18/16 hücreli koşudan sonra kullanıcı
vericinin kapalı olduğunu bildirdiğinden bu kayıt pozitif kabul için geçersiz
ve `superseded_positive_state_uncontrolled` durumundadır. Sabit iki-ayar kararı
sekiz canlı geniş bant omuz ölçümüyle tekrar denetlenir; omuz kanıtı kaybolursa
yeşil karar geri çekilir. TX kapalı, anten bağlı tekrarı dört ayarda 0 hücre ve
`not_reproduced` sonucu vermiş; arayüz 27 saniye yanlış tespit üretmemiştir.
Geçerli negatif kanıt
`results/evidence/phase08/receiver-spur-1ghz-tx-off-live-guard.json`
dosyasındadır. Pozitif kontrollü TX, genel saha yanlış alarm olasılığı ve tespit
olasılığı kapıları açıktır.

Aynı bakımda `0000000000000000a32868dc36877e47` seri numaralı ED_RX için TX
kapalı referansındaki 720, 760 ve 840 MHz dar iç ürünleri cihaz profiline
eklenmiştir. Dört farklı giriş/çıkış merkezinde 720 MHz omuz sayısı 1/1/1/1,
760 ve 840 MHz omuz sayıları 0/0/0/0 olmuş; üç aday da
`not_reproduced` sonucunda kalmıştır. Profil yalnız listelenen seri numarası ve
frekansları kapsar; verici kimliği, pozitif TX kabulü, Pd veya Pfa iddiası
oluşturmaz. Kanıt
`results/evidence/phase08/receiver-spur-harmonics-36877e47.json`
dosyasındadır.

KTR-5.1 kör keşif hassasiyeti bakımında FPGA OS-CFAR profili ve yanlış alarm
hedefi korunmuş, ham 8 MHz RX spektrumuna ayrı çok-kareli aday yolu eklenmiştir.
Bu yol en az 32 kare, en az 6 dB ortalama P/N, en az %75 aynı-hücre doluluğu ve
bağımsız ikinci LO'da mutlak RF tekrarını ister. Kabul edilen sonuç arayüzde
`RX 2 AYARDA` olarak gösterilir ve FPGA olayı olarak sunulmaz. 955,7 MHz
fiziksel açık/kapalı tanısında açık iki LO %88,8/%86,9 dolulukla aynı adayı,
kapalı iki LO sıfır aday üretmiştir. Frekans operatör tarafından açıklandığı
için bu yalnız algoritma tanı kanıtıdır; KTR-5.1 frekansı açıklanmamış canlı
geniş bant kabul kapısı açık kalır.

ADR-0040, tek kare OS-CFAR'a ulaşmayan fakat çok kare boyunca kararlı kalan dar
bant yayın için frekanstan bağımsız altın modeli tanımlar. Hann/FFT doğrusal güç
ortalaması, sağlam yerel gürültü, en az 6 dB ve yüzde 75 doluluk ile ikinci LO
kapıları hostta uygulanmıştır. Dört RF merkezinde değişmezlik, çok bileşenli
emisyon merkezi ve iki yakın bağımsız taşıyıcının birleştirilmemesi yazılım
testleriyle denetlenir. Ürün yolu aynı rank-24/32 PL referansına karşı 6 dB
zayıf aday kapısı ile ARM'da ±2 hücre destekli 24/32 doğrulamayı kullanır.
Python/NumPy yalnız referans model ve tekrarlanabilir doğrulama sahibidir.
Python/C eşdeğerlik testi ve 5×/10× hücreli SystemVerilog karar
benzetimi geçmiştir. 64'er beyaz, eğimli ve dalgalı gürültü penceresinde sıfır
yanlış doğrulama ile beş frekans-konumsuz enjeksiyonun beşi doğrulanmıştır;
kanıt `results/evidence/phase08/persistent-weak-model-v1.json` içindedir.
Sınıflı zayıf gruplama, PHASE-06I paket bayrakları ve ARM `p0_ed_pipeline`
24/32 yolu tamamlanmıştır. Dondurulmuş gerçekçi
FFT karesinde 321 zayıf grup görülmesiyle 256 sınırı yetersiz bulunmuş, ortak
PL/paket sınırı 1352'ye çıkarılmış; ARM izleyiciye her karede yalnız en güçlü
sekiz zayıf aday alınmıştır. Tam RTL paket kapısı 8 karede 113 aday/629 beat ve
60 backpressure kararlılık kontrolüyle sıfır fark vermiştir; portable C boru
hattı 24/32 kabul, sıra boşluğunda reset, normal 2/3 yol ve sona-erme testlerini
geçmiştir. Tam Zynq-7020 uygulaması 50 MHz'te WNS
`+0,199 ns`, WHS `+0,010 ns`, sıfır failing endpoint ve sıfır route/DRC hatasıyla
bitstream/XSA üretmiştir; `%90,30` LUT kullanımı kaynak payı riski olarak izlenir.
PetaLinux 2025.2 bu XSA ve güncel ARM kaynaklarını 5679 görevde hatasız
paketlemiştir. P09 kalıcı imajı kartta soğuk açılmış; 104 adaylı işlev dizisi
sıfır düşümle tamamlanmış ve beş koşuda 20.480 ölçüm karesi en az
525,8263 kare/s hızla sıfır sıra hatası vermiştir. Bu, bilinen dijital
çerçevenin FPGA/ARM kabulüdür. Kör canlı RF Pd/Pfa, kalibrasyon ve farklı yayın
ailelerinin saha kabulü açık kaldığından KTR-5.1 kapanmış sayılmaz. Güncel
kaynak/simülasyon/fiziksel hashler
`results/evidence/phase08/persistent-weak-integration-v1.json` ve
`results/evidence/p0/adr0040-physical-acceptance.json` kayıtlarında tutulur.

Fiziksel hata ayrıştırmasında bağlı HackRF'in 8 MS/s önek ürettiği ve FPGA
hizmetinin erişilebilir olduğu doğrulanmıştır. Yüksek kazançtaki I/Q kırpılması
genel kuyruk zaman aşımıyla maskelenmeyecek biçimde ilk hatada `iq_saturation`
olarak taşınır; alım ve kanal seçici zaman aşımı kodları ayrılmıştır. 32/32 ile
16/16 dB tanı koşulları kırpılmış, 8/8 ve 0/0 dB koşulları 64/64 FPGA yanıtını
sıfır USB taşmasıyla tamamlamıştır. Bu tanı kontrollü RF doğruluk kapısını kapatmaz.

On beşinci bakım paketi KTR-4.1 sunumunu düz tek yüzeye taşımış ve doğrulanmış
frekans geçmişini eklemiştir. Ham FPGA adayları gösterilmez; 2/3 koşulunu geçen
gözlemler frekans destek örtüşmesine göre tekilleştirilir ve oturum boyunca
`Algılanıyor`/`Son görüldü` olarak korunur. Bu yalnız sunum belleğidir; FPGA/ARM
olay yaşam döngüsünü, eşikleri veya dış yayın doğrulama sınırını değiştirmez.
`İZLEME` kaldırılmış ve geçerli FPGA penceresi `TESPİT ALANI` olarak açıkça
etiketlenmiştir. İlgili regresyon paketi 100/100 geçmiştir.

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
ADR-0040 ile PL'deki 6 dB zayıf aday sınıfı ve ARM'daki kare başına en güçlü
sekiz zayıf aday/24-of-32 doğrulaması güncel P09 imajına alınmıştır. P09 kalıcı
soğuk açılıştan sonra 104 adaydan 50 etkin olay ve iki boş karede 50 sona erme
dizisini sıfır düşümle işlemiştir. Beş bağımsız koşuda toplam 20.480 ölçüm
karesi sıfır sıra hatasıyla tamamlanmış; en düşük 525,8263 kare/s hız,
488,28125 kare/s alt sınırını geçmiştir. Bu kanıt bilinen dijital çerçeveye
aittir; kör canlı HackRF RF Pd/Pfa, frekans/genlik kalibrasyonu ve saha kapıları
açık kalır. Kalıcı ayrıcalıklı kart hizmeti; otomatik başlangıç,
yetki düşürme, normal kullanıcı istemcisi, fiziksel DMA ve yeniden başlatma
kapılarıyla kabul edilmiştir.

Ürünleşme sınırı: video/demo dönemi kapanmıştır. Yayın operatör uygulaması mock,
eğitim, gösterim verisi veya geleceğe ayrılmış bağlı-olmayan kontrol içermez.
Yalnız doğrulanmış çevrimdışı ET modelleri ürün yüzeyine dahildir. ADR-0043
sonrasında üst durum `ET ORTAMI — FARADAY LAB` ile kayıtlı ortam onayını gösterir;
bu durum mevcut görev düğmelerinin RF gönderdiği anlamına gelmez. Golden/replay
verileri doğrulama paketinde kalır; gerçek donanım sonucu ancak fiziksel kabul
kanıtı varsa yayın yüzeyinde etkinleştirilir.

## PHASE-08 arayüz sadeleştirmesi ve kararlılık — 14 Eylül 2026

14 Eylül 2026 PHASE-08 arayüz bakımında alıcı seri/envanter görünümü ve bant
taramasındaki profil/süre açıklamaları kaldırıldı. Bağlantı başarısızlıkları
yalnız `Alıcı algılanmadı` ve/veya `FPGA algılanmadı` metniyle sunulur; ayrıntılı
kod olay günlüğünde kalır. Gerçek QML + HackRF + FPGA durdur/yeniden başlat
koşusu `results/evidence/phase08/ui-simplification-stability-20260914.json`
kanıtıyla KTR-4.1-OPS-B0 ve APP-F bağına eklenmiştir. Bu kısa koşu uzun süreli
GUI dayanıklılık veya ST-06 kabulü değildir.
