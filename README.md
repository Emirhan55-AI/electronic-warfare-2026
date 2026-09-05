# Elektronik Harp Operatör ve FPGA Sinyal İşleme Sistemi

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

Bu proje; RF I/Q verisinin alınması, spektral analizi, sinyal tespiti, operatör
onaylı parametre ölçümü ve FPGA üzerinde gerçek zamanlı işlenmesi için geliştirilen
bir mühendislik sistemidir. Referans platform HackRF One, ZedBoard Zynq-7000 ve
Türkçe Qt Quick operatör uygulamasından oluşur.

Proje yalnız ölçülmüş veya tekrarlanabilir testle doğrulanmış sonuçları yetenek
olarak kabul eder. Canlı donanım, RF doğruluğu ya da performans kanıtı bulunmayan
işlevler uygulamada çalışıyormuş gibi gösterilmez.

## Sistem mimarisi

```text
SigMF / HackRF RX
       │
       ▼
Operatör bilgisayarı ── kontrol ve kayıt ──► ZedBoard PS / DDR
       │                                         │
       │                                         ▼
       ◄──────────── sonuçlar ───── ZedBoard PS: güç çözme → geniş bant → 2/3
                                                  ▲
                                               AXI DMA
                                                  ▲
                                     ZedBoard PL: Hann → 4096 FFT → Güç
                                                  → OS-CFAR hücre kararı
                                                  → 4096 işaretli güç kelimesi
```

Bu çizim ST-06 ürün imajının görev paylaşımıdır. PL→PS sınırı her karede
32 KiB işaretli güçtür; aday gruplama, sekiz karelik geniş bant kararı ve
temporal olaylar ARM'da işlenir. PC alım, 8→2 MS/s kanal seçimi, görünüm ve
kayıttan sorumludur. Host referansları sayısal eşdeğerliği denetler.

## Güncel aşama — 5 Eylül 2026

Çalışma PHASE-08 / ST-06 sinyal tespitindedir. ST-05 Python referansı seçilmiş,
C eşdeğerliği ve güç nicemleme kontrolleri geçmiştir. ARM geniş bant çekirdeği
kayan nokta kullanır. Güncel FPGA tasarımı 50 MHz zamanlamayı geçmiş; LUT
kullanımı 19.587/53.200 (`%36,82`), BRAM `%16,79`, DSP `%21,36` olmuştur.
Bu sonuç [Vivado kaydına](results/evidence/phase08/st06-power-vivado-v1.json) aittir.

Bağımsız kart DMA/ARM profili beş adet 2.000-kare tekrarda 551,22–577,68
kare/s ölçmüştür; 2 MS/s için gereken hız 488,28125 kare/s'dir. Ölçüm ürün
ağ hizmetinin veya canlı RF'nin kabulü değildir;
[profilin kapsamı](results/evidence/phase08/st06-pipelined-dma-profile-v1.json)
korunur. Güncel bitstream ve ARM hizmeti PetaLinux ürün imajında paketlenmiştir;
[ürün entegrasyon kanıtı](results/evidence/phase08/st06-product-integration-v1.json)
paket 5.679/5.679 ve tam imaj 6.090/6.090 derleme görevini doğrular.

5 Eylül kart tanısında FPGA/hizmet/ağ köprüsü geçici yüklenmiştir. Bağımsız
256 gürültü karesinde doğrulanmış olay yoktur; dar ton 255/256, geniş bant
249/256 karede doğrulanmış ve sıfır giriş kuyruğunda olaylar sonlanmıştır.
Bu kısa dijital deney RF doğruluğu kabulü değildir. Ürün yolu 286–290 kare/s
ile gerekli 488,28125 kare/s hızını **geçememiştir**; ARM tespit iş parçacığı
darboğazdır. [Ham verili tanı kaydı](results/evidence/phase08/st06-product-board-diagnostic-v1.json)
başarısız hız kapısını da korur. SD açılış dosyaları değişmemiştir.
Soğuk açılış, ürün hızı ve kontrollü kör RF doğruluğu açık kalır.
ST-06 ve PHASE-08 tamamlanmamıştır.
Sonraki çalışma bu kabul kapılarıdır. Güncel durumun ayrıntıları
[sinyal tespiti durum belgesinde](docs/interfaces/SIGNAL_DETECTION_STATUS.md),
faz sırası [yol haritasında](docs/plans/IMPLEMENTATION_ROADMAP.md) tutulur.

## Mevcut yetenekler

Bu bölümdeki tarihli ölçümler ilgili eski kaynak sürümlerine aittir. ST-06
ürününün güncel kabul durumu yukarıdadır; aşağıdaki aday-paket PL mimarisi ve
kaynak kullanım sayıları tarihsel tasarımları anlatır.

31 Ağustos sinyal tespiti bakımında spektrum ve waterfall çizimi Qt görüntü
tamponuna taşınmıştır: 128 satır, dar tepe koruma, sabit güç/renk ölçeği ve
15 DSP karesinde bir canlı görünüm hedefi bulunur. Tarama görünümü, bütünlüğü
geçen pencerenin gerçek karelerinden geçmiş gösterir. Yeni görünümün canlı
kabulü eski fiziksel kayıtlardan devralınmaz. Geniş bant kurtarmanın bölgesel
gürültü tabanı kirlenmesi sınırı ve güncel SystemVerilog/ARM sahipliği
[durum belgesinde](docs/interfaces/SIGNAL_DETECTION_STATUS.md) açıklanmıştır.

8 MS/s, 16.384 noktalı canlı görünüm gücü için ayrıca hostta kaba aday yolu
bulunur. Dörder hücrenin enerjisi toplanarak mevcut 4.096-hücre OS-CFAR ve
geniş bant referansına verilir; sarı kaba RX alanı, yeşil FPGA doğrulamasından
ayrıdır. Bağımsız sentetik kabulte 100 kHz–4 MHz aileleri 32/32 geçmiş, 6 MHz
31/32 ile yalnız karakterize edilmiş, bütün 8 MHz doluluğu çözülememiştir.
Bu sonuç RF veya FPGA kabulü değildir; ayrıntı ADR-0038 ve
`results/evidence/phase08/coarse-rx-detection-v1.json` içindedir.

Güncel çalışma, frekansı bilinmeyen yayının **yalnız alımla aranmasına** odaklanır.
HackRF görünümündeki `Frekans Taraması`, 1–6.000 MHz aralığını 9.999 bitişik
600 kHz sorumluluk hücresinde, örtüşen 2 MHz alıcı ayarlarıyla sırayla işler;
bütün aralık aynı anda dinlenmez. Her pencere 128 gerçek
I/Q karesinin kartta işlenmesi ve alım bütünlüğünün geçmesiyle kapsama eklenir.
Başarısız ve ziyaret edilmemiş bantlar boş bant sayılmaz. Gözlemler tur boyunca
korunur; tarama durdurulduktan sonra seçilen frekans sabit bantta izlenebilir.
Bu geometri 1 MHz desteği en az bir ayarın doğrulanmış kanal seçici geçiş bandı
içinde tutar; RF algılama olasılığı garantisi değildir. Kısa yayınlar kaçabilir
ve tek antenin bütün aralıkta duyarlı olduğu varsayılmaz.

**Kanıt sürümü sınırı:** Aşağıdaki eski fiziksel kabul kayıtları, içlerinde
belirtilen kaynak sürümlerine aittir. Yeni tarama ve Windows ikili I/Q taşıma
değişiklikleri bu kayıtların güncel kaynak kabulü olduğu anlamına gelmez;
kaynak özeti denetimleri korunur. Yeni çalıştırmalar, yapılandırma/kaynak özetleri
ve gerçek kart sonuçlarıyla `build/acceptance/rx-survey/` altında ayrı JSONL
kayıtları oluşturur. Kısa alıcı denemeleri tam bant doğruluğu, gizli vericiyi
bulma başarısı veya saha kabulü değildir.

| Alan | Durum |
|---|---|
| SigMF kayıt açma, sözleşme denetimi ve gerçek I/Q işleme | Doğrulandı |
| HackRF araç/cihaz denetimi ve RX alımı | Seri numarasına bağlı fiziksel HackRF-1 ile 8 MS/s RX, DC-güvenli offset tuning ve host tespiti önceki kaynaklarda geçti. Güncel ADR-0039 sürümünde görünüm 32,15 Hz hedefini geçmiştir; ancak hem ürün hem doğrudan aktarım shortfall ürettiğinden farklı USB port/kablo tekrarı ve uzun kabul açıktır |
| PC kanal seçici ve ZedBoard ağ taşıması | 8→2 MS/s, 193 tap anti-alias kanal seçici C++17 AVX2/FMA3 yolunda NumPy referansına 80 karede bayt-tam eşdeğerdir; p95 süre 0,525 ms'dir. Tam CI8/4096 çerçeve ve çift CRC'li dört derinlikli TCP→yerel hizmet yolu önceki fiziksel kaynak sürümünde doğrulanmıştır. Güncel kartta TCP 47007 açıktır; son ADR-0037 bitstream kabulü açıktır |
| Hann, 4096 FFT, dBFS spektrum ve spektrogram | Host referansında doğrulandı |
| Uyarlanabilir hücre tespiti, bütünleşik geniş bant enerjisi, aday gruplama ve 2/3 zamansal doğrulama | Host referansı ve fiziksel PL→DMA→ARM zincirinde doğrulandı. Kalıcı kart imajıyla yapılan beş sürekli 2 MS/s kabul koşusunda toplam 20.480/20.480 kare sıfır hatayla işlendi; en düşük hız 508,76 kare/s oldu |
| Emisyon merkezi, gözlenen taşıyıcı, OBW99, göreli güç, SNR ve sınırlı sinyal türü ölçümü | Host ürün profilinde operatör onaylı analiz aralığında doğrulandı; emisyon merkezi, bant kenarları, OBW99, kalibrasyonsuz dBFS güç ve SNR fiziksel PL→DMA→ARM zincirinde dört gözlemle çalıştı. Taşıyıcı çizgisi ve sinyal türü ARM paketinde yok |
| Manuel açı–güç ölçümüne dayalı bağıl geliş açısı ve kerteriz | Host modelinde doğrulandı; saha doğruluğu ölçülmedi |
| ZedBoard PL CI8→Hann→FFT→güç→aday paketi zinciri | SystemVerilog ve AMD FFT IP ile kanonik P0 blok tasarımına alındı; Vivado sentez, route, 50 MHz setup/hold, bitstream ve XSA kapıları geçti |
| FPGA tespit, gruplama ve aday paketleme blokları | Bit-doğru alt blok doğrulamalarına ek olarak tam kart tasarımında 27.453 LUT, 81,5 BRAM tile ve 71 DSP ile route edildi; setup WNS +0,423 ns, hold WHS +0,021 ns |
| ZedBoard üzerinde DMA ve tespit zinciri | Değişken 64–54.144 bayt aday paketi, S2MM gerçek uzunluk sürücüsü ve yerel Linux hizmeti kalıcı PetaLinux imajında doğrulandı. Soğuk açılış, bit-doğru 54 aday yaşam döngüsü ve tekrarlı 2 MS/s hız kapıları geçti |
| AM/NFM izleme zinciri | Kayıtlı I/Q ve QML ürün akışında doğrulandı; canlı HackRF/ses saha kabulü bekliyor |
| ET işlevleri | Python host üzerinde çevrimdışı/loopback modeller; SystemVerilog, FPGA veya RF yayın yolu yok |

Parametre sonuçları kalibrasyonsuz `dBFS` ölçeğindedir; `dBm` ölçümü değildir.
Faz uyumlu çok kanallı DoA, menzil veya otomatik hedef konumu üretilmez.

## Operatör uygulaması

Uygulama ED ve ET görevlerini aynı ürün kabuğunda açıkça ayırır. ED alanı; veri
kaynağı, bağlı spektrum/spektrogram görünümü, tespitler, üç adımlı sinyal ölçümü,
AM/NFM dinleme, manuel yön bulma, sistem sağlığı ve salt okunur olay konsolunu
birleştirir. ET alanı yalnız doğrulanmış çevrimdışı sürekli, arabakışlı, analog
loopback ve GPS L1 C/A metadata modellerini sunar. RF TX yolu yoktur ve bütün ET
sonuçları fiziksel RF sonucu olmadığını açıkça belirtir. Yayın çalışma zamanı
yalnız gerçek SigMF/HackRF RX kaynaklarını ve doğrulanmış çevrimdışı ET
modellerini içerir; mock kaynaklar, gösterim verileri ve eski laboratuvar
arayüzleri ürün paketine girmez.

`HackRF Canlı RX` görünümü izleme merkezini, LNA/VGA kazançlarını ve sınırlı
canlı ED oturumunu yönetir. Gösterilen geniş spektrum aynı alımın ham 8 MS/s
I/Q karesine, ayrıntılı tespitler ise 2 MS/s kanal seçilmiş kareye verilen
ZedBoard FPGA/ARM yanıtına bağlıdır. Sarı kaba RX adayı host önerisidir; yeşil
durum FPGA doğrulamasıdır. Kart bağlantısı yoksa uygulama FPGA sonucu üretmez.

Fiziksel ürün arayüzünden başlatılan beş ardışık 4.096-kare oturumu toplam
20.480 kareyi sıfır USB taşması, taşıma CRC/sıra hatası ve I/Q kırpılmasıyla
tamamlamıştır. Bu kabul 104,65 MHz izleme merkezi ve LNA/VGA 0/0 dB koşulundadır;
ortam RF sinyallerinden tespit doğruluğu yüzdesi çıkarılmaz. İlk 16/16 dB
denemesinde kırpılma oluşmuş ve oturum sonuç üretmeden reddedilmiştir.
[Ölçüm kaydı](results/evidence/phase08/product-live-acceptance.json) başarısız
denemeyi de korur. Oturum açılışını içeren hızlar FPGA azami kapasitesi veya
C/C++ karşısında hızlanma iddiası değildir. Fiziksel durdurma ve yeniden
başlatma geçmiştir. Canlı parametre ürün bağı dört ardışık gerçek FPGA karesiyle
işlevsel olarak geçmiştir; kontrollü RF doğruluğu, canlı ses ve saha kalibrasyonu
ayrı kapılardır.

Kayıtların bütünlüğü `python scripts/verify_phase08_product.py` ile denetlenir.
Yeni fiziksel gözlem için `python scripts/capture_phase08_product.py --output
build/acceptance/new-product-run` ürün penceresini açar; cihaz denetimi ve oturum
başlatma operatör tarafından yapılır. Araç yalnız gerçek alımı gözlemler;
örnek veri veya kart yanıtı üretmez.

8 MS/s canlı ürün yolu derlenmiş kanal seçici gerektirir. Windows Release
çekirdeği şu komutlarla hazırlanır; DLL oluşmazsa fiziksel ürün yavaş Python
yoluna sessizce düşmez:

```powershell
cmake -S algorithms\p0\native -B build\native\p0_channelizer -G "Visual Studio 17 2022" -A x64
cmake --build build\native\p0_channelizer --config Release
python scripts\verify_phase08_native_channelizer.py
```

Canlı tespit listesi varsayılan olarak doğrulanmış gözlemleri gösterir;
`Adayları göster` henüz doğrulanmamış olayları açar. Ölçüm için gereken son dört
ardışık FPGA karesi görünür tespitlerle birlikte otomatik korunur; operatörün
listeyi dondurması gerekmez. Seçili olay kaybolduğunda `Son gözlem`, oturum bittiğinde
`Son oturum` gösterilir; aynı frekanstaki yeni olay otomatik olarak eski
seçime bağlanmaz. Spektrum ve spektrogram seçili frekansı ortak kılavuzla
gösterir. Önceki kabulde görüntüleme yaklaşık 10 Hz'dir. Yeni görünüm 15 karede
bir, nominal 32,55 Hz güncelleme hedefler; FPGA bütün I/Q karelerini işler.
Güncel arayüz ölçüsü geçmiştir, fakat USB shortfall nedeniyle uzun fiziksel
kabul açıktır.
[Canlı seçim görünümü](results/evidence/phase08/detection-selection-aligned.png)
frekans kılavuzunun spektrum ve spektrogramdaki ortak konumunu gösterir.
UI yük karşılaştırmasının olumlu ve olumsuz ham kayıtları ile sınırları
[`detection-ui-decoupling.json`](results/evidence/phase08/detection-ui-decoupling.json)
özetindedir; `python scripts/verify_phase08_detection_ui.py` arşivi yeniden
hesaplayarak doğrular. USB okuma, 512 karelik sınırlı ham-I/Q kuyruğuyla kanal
seçimi ve FPGA taşımasından ayrılmıştır. Önceki kaynak sürümü sekiz tam fiziksel ürün
koşusunda 32.768/32.768 kareyi sıfır USB taşmasıyla tamamlamış; operatör iptali
750. karede ve ardından yeniden başlatma ayrı ayrı geçmiştir. En yüksek kuyruk
kullanımı 111/512'dir. Ayrı kesintisiz dayanıklılık kabulü 15 dakika boyunca
439.453/439.453 kareyi ve 14.399.995.904 ham baytı sıfır USB/CRC/sıra/kuyruk
hatası ve sıfır kırpılmayla tamamlamıştır; ham kuyruk tepe kullanımı
170/512'dir. Hash-bağlı özet
[`live-rx-endurance-v2.json`](results/evidence/phase08/live-rx-endurance-v2.json)
içindedir ve `python scripts/verify_phase08_endurance.py` ile yeniden
doğrulanır. Bu kayıtlar ADR-0039 kaynak sürümüne devredilmez; güncel
`live-rx-display-8msps-v2.json` üç USB shortfall nedeniyle başarısızdır. Ortam
sinyalleri kontrollü RF doğruluğu kanıtı değildir.

Dört ardışık confirmed+observed FPGA karesine bağlı canlı parametre ürün akışı
gerçek HackRF oturumunda dokuz sonuç alanını üretmiştir. Hash-bağlı işlevsel kanıt
[`live-parameter-functional.json`](results/evidence/phase08/live-parameter-functional.json)
içindedir ve `python scripts/verify_phase08_live_parameter.py` ile yeniden
doğrulanır. Bu kayıt ürün bağını kanıtlar; ortam sinyalinden frekans, bant
genişliği, güç veya sınıflandırma doğruluğu yüzdesi çıkarmaz.

### Kurulum

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements\phase02.txt
```

### Çalıştırma

```powershell
python -m app.operator_console
```

Klavye kısayolları:

- `Ctrl+O`: SigMF kaydı açar.
- `Boşluk`: Spektrum alanında taramayı başlatır veya duraklatır.
- `Ctrl+1`, `Ctrl+2`, `Ctrl+3`, `Ctrl+4`: çalışma alanları arasında geçer ve
  klavye odağını seçilen alana taşır.
- `Ctrl+5`: ET görev doğrulama alanını açar.
- `Ctrl+B`: Spektrum alanında veri kaynağı panelini açar veya kapatır.
- `Alt+Sol`, `Alt+Sağ`: frekans görünümü geçmişinde geri veya ileri gider.
- `Ctrl+0`: spektrum ve spektrogramı tam banda döndürür.
- `Esc`: açık olay konsolunu kapatır.

## Doğrulama

Tam yazılım regresyonu:

```powershell
python -m pytest tests
```

Operatör arayüzü; ED için 1280×720, 1366×768, 1920×1080 ve %150 ölçek
koşullarında; ET için 1180×680, 1280×720 ve 1440×900 koşullarında aşağıdaki
doğrulayıcıyla yeniden üretilebilir:

```powershell
python -B scripts\verify_app_f_release_ui.py
```

Sistem çalışma alanı etkin işlem zincirini ve host/FPGA kabul sınırını açıkça
ayırır. Filtrelenebilir olay günlüğü çalışma durumunu salt okunur olarak izler;
ürün görünümü komut çalıştıran bir terminal içermez.

Ayrıntılı gereksinim durumu ve yöntem sınırları
[`docs/requirements/KTR_TRACEABILITY.md`](docs/requirements/KTR_TRACEABILITY.md),
sistem hedefi ise
[`docs/architecture/SYSTEM_BASELINE.md`](docs/architecture/SYSTEM_BASELINE.md)
altında tutulur.

## Depo düzeni

- `app/`: Qt Quick operatör uygulaması ve sunum katmanı.
- `app/operator_console/quick_*_actions.py`: tarama, ölçüm, dinleme, yön bulma
  ve çevrimdışı ET kullanıcı eylemlerini ayıran sunum denetleyicileri.
- `app/operator_console/qml/`: ana kabuk, görev çalışma alanları ve ortak görsel
  bileşenler; QML dosyaları tek bir dev ekran tanımı olarak tutulmaz.
- `algorithms/`: host referans DSP, tespit, parametre, izleme ve FPGA RTL kaynakları.
- `platforms/`: HackRF alım katmanı ile Zynq PS/embedded bileşenleri.
- `profiles/`: doğrulama kapılarını geçmiş çalışma profilleri.
- `tests/` ve `verification/`: otomatik regresyonlar ve bağımsız doğrulama araçları.
- `docs/`: mimari, gereksinim izlenebilirliği ve teknik kararlar.

## RF güvenliği

Depoda genel kullanıma açık bir RF yayın arka ucu bulunmaz. ET çalışmaları yalnız
çevrimdışı veya kapalı çevrim doğrulama kapsamındadır. Her fiziksel RF deneyi;
yetkili, kontrollü, uygun zayıflatma ve ekranlama kullanılan bir test düzeninde
yürütülmelidir.
