# Elektronik Harp Operatör ve FPGA Sinyal İşleme Sistemi

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
853 MHz olayı ilk kareden son kareye 4.883/4.883 kez gözlendi; örneklenmiş 327
yanıtın ilk tentative yanıtından sonraki 326'sı aynı hedefi confirmed ve observed
olarak taşıdı. Kapalı koşunun 327 örnek yanıtında hedef çevresinde confirmed olay
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
sıra/kuyruk hatası ve kırpılmayla bitirdi. İlk örnek tentative; kalan 326 örnek
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
327 örnek karesinde merkez hücre güçlü eşiği 14 kez, kapalıda sıfır kez aştı.
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
bitirdi. 327 örneklenmiş I/Q karesinin ortalama merkez-hücre gücü açıkta kapalıya
göre 7,15 dB arttı. Örneklenmiş FPGA yanıtlarında tam 853 MHz hücresinde iki
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
kırpılmasının nedeni kanıtlanmadı. Yerel ham kayıt ve örneklenmiş I/Q paketi:
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
Ancak p95 RX→görüntü yaşı 153,47 ms ile 150 ms hedefini aşmıştır; örneklenmiş
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
