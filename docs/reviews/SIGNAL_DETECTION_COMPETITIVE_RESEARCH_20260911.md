# Sinyal tespiti mimarisi ve açık kaynak karşılaştırması

11 Eylül 2026 · ST-06 · KTR-4.1 / KTR-4.1-OPS-B0

## Karar özeti

Projedeki sinyal tespiti bir arayüz gösterimi değildir. Güncel ürün yolu
`HackRF/SigMF → PC kanal seçimi ve taşıma → ZedBoard PS → DMA → PL Hann →
4096/8192/16384 FFT → doğrusal güç → OS-CFAR → ARM aday ve zamansal yaşam
döngüsü → PC olay ve spektrum arayüzü` zinciridir. FPGA FFT uzunluğu, normal ve
zayıf CFAR katsayıları durdurulmuş oturumda arayüzden uygulanır ve karttan geri
okunur. Üç FFT boyutu fiziksel ZedBoard üzerinde üçer bağımsız, 4.096 karelik
sayısal hız koşusunda hedef gerçek zaman hızını geçti.[^local-fft]

Bu sonuç sistemi SDRangel veya GNU Radio'dan genel olarak “daha iyi” yapmaz.
SDRangel genel amaçlı cihaz, kanal, demodülasyon, spektrum ölçümü ve uzaktan
kontrol kapsamı bakımından çok daha olgundur. GNU Radio yeni akışları ve
algoritmaları hızlı kurup karşılaştırmak için daha güçlü bir deney ortamıdır.
Bu proje ise belirli Zynq-7020 hedefinde doğrulanmış FPGA/ARM görev paylaşımı,
sınırlı kaynakla deterministik çalışma, fail-closed profil geçişi ve Türkçe
görev arayüzü bakımından daha özeldir. Hangi sistemin zayıf sinyali daha iyi
tespit ettiği henüz kanıtlanmamıştır; bunun için aynı I/Q veri kümesi ve kör RF
koşullarında Pd/Pfa, gecikme ve kaynak maliyeti birlikte ölçülmelidir.

Saha testine gitmeden önce önemli ilerleme mümkündür. Aynı I/Q tekrar oynatma,
Monte Carlo SNR/frekans ofseti/bant genişliği taraması, SDRangel ve GNU Radio ile
aynı kayıt karşılaştırması, pencere adaylarının bit-doğru geliştirilmesi,
bozuk taşıma ve uzun GUI yük testleri laboratuvarda tamamlanabilir. Anten,
ortam gürültüsü, analog ön uç sıkışması, gerçek kazanç, mutlak dBm ve kör RF
Pd/Pfa ise fiziksel ölçüm olmadan kapatılamaz.

## Güncel sistem gerçekten ne yapıyor?

### PL, PS ve PC görevleri

| Katman | Güncel sorumluluk | Kanıt durumu |
|---|---|---|
| HackRF ve PC | USB RX, merkez frekans/örnek hızı/LNA/VGA kontrolü, kanal seçimi, Ethernet taşıma, arayüz ve kayıt | Kaynak ve arayüz uygulanmış; son dinamik FFT imajıyla HackRF+GUI uzun koşusu açık |
| ZedBoard PS CPU0 | Ağ paketi alma, DMA sahipliği, PL sonuç çözme ve bütünlük kontrolleri | Fiziksel kartta dinamik FFT koşularında çalıştı |
| ZedBoard PS CPU1 | Dar/geniş aday işleme ve zamansal olay yaşam döngüsü | Ürün hizmetinin parçası; RF doğruluğu güncel imajla yeniden kabul bekliyor |
| ZedBoard PL | Hann, çalışma zamanı seçilen FFT, doğrusal güç, OS-CFAR hücre kararı | 4096/8192/16384 için fiziksel hız ve profil geri okuma geçti |

Dinamik FFT yalnız ekrandaki çizgi yoğunluğunu değiştiren bir ayar değildir.
Arayüz isteği hizmet ABI v4 ve DMA ABI v3 üzerinden AXI-Lite denetim bloğuna
gider. PL boşken NFFT 12, 13 veya 14 uygulanır. Hann katsayı adreslemesi, XFFT
çerçevesi, güç hücre sayısı, CFAR çerçeve sınırı, DMA uzunluğu ve ARM çözümü aynı
boyuta geçer. Uyuşmazlıkta yeni I/Q kabulü durdurulur. Ayrı “Görüntü FFT”
seçimi yalnız PC sunum yolunu etkiler ve arayüz bunu açıkça söyler.

Üç tekrarlı kart ölçüminde en düşük hızlar şöyledir:

| FPGA FFT | Gerekli hız | En düşük ölçüm | En düşük gerçek zaman payı |
|---:|---:|---:|---:|
| 4096 | 488,281 kare/s | 540,081 kare/s | 1,106× |
| 8192 | 244,141 kare/s | 249,970 kare/s | 1,024× |
| 16384 | 122,070 kare/s | 138,120 kare/s | 1,131× |

Her koşuda profil geri okuması, tüm kareler, kare kimlikleri, DMA durumu,
CRC/sıra/kuyruk denetimi ve başlangıç profiline dönüş geçti. Bitstream zamanlama
sonucu WNS +0,613 ns, WHS +0,030 ns ve sıfır yönlendirme hatasıdır. Kanıt aynı
bitstream, sürücü modülü, ARM hizmeti ve ağ köprüsünün kart/yerel SHA-256
eşliğini de içerir. Yükleme geçicidir; SD karttaki kalıcı açılış ürünleri
değiştirilmemiştir.[^local-fft]

Bu ölçümler sayısal gerçek zaman ve entegrasyon kanıtıdır. RF hassasiyeti,
yanlış alarm olasılığı, mutlak güç doğruluğu veya soğuk açılış kanıtı değildir.

## SDRangel ile karşılaştırma

SDRangel birden çok SDR cihazını, kanal alıcı/vericilerini ve özellik
eklentilerini ortak masaüstü ya da sunucu ortamında birleştiren geniş bir
uygulamadır.[^sdrangel-repo] Spektrum bileşeni 64–32768 FFT, dokuz pencere,
örtüşme, hareketli/sabit ortalama, min/max tutma, matematik kipleri, RBW,
işaretçiler ve görüntü FPS sınırı sunar.[^sdrangel-spectrum] Frekans Tarayıcı
eklentisi eşik, tarama aralığı, bekleme süresi, yeniden iletim sayısı, etkin
kanal sayısı ve kanal başına ayarlarla geniş bir operatör iş akışı sağlar;
ayarlar Web API üzerinden de yönetilebilir.[^sdrangel-scanner] Spektrum ölçüm
yüzeyi tepe, kanal gücü, işgal edilen bant genişliği, SNR, SINAD, THD ve SFDR
gibi ölçümleri içerir.[^sdrangel-measurements]

Bu nedenle SDRangel şu alanlarda belirgin biçimde ileridedir:

- cihaz ve demodülatör çeşitliliği;
- spektrum görüntüleme ve ölçüm araçlarının olgunluğu;
- pencere, örtüşme ve ortalama seçeneklerinin genişliği;
- Web API ve başsız sunucu kullanımının hazır olması;
- uzun süredir kullanılan genel amaçlı kullanıcı deneyimi.

Ancak SDRangel'deki bir FFT veya pencere kontrolünün varlığı, bu projedeki
ZedBoard PL yoluna doğrudan taşınabileceği anlamına gelmez. SDRangel'in ana
spektrum kontrolleri yazılım işleme ve görüntüleme katmanındadır. Burada aynı
kontrolün PL katsayı belleği, AMD XFFT yapılandırma kanalı, güç ölçeği, CFAR
komşuluğu, DMA çerçevesi ve ARM tüketicisiyle birlikte doğrulanması gerekir.
SDRangel kaynak kodu iyi bir davranış ve arayüz referansıdır; bu donanıma hazır
bir bitstream veya OS-CFAR kabul kanıtı değildir.

## GNU Radio ve gr-inspector ile karşılaştırma

GNU Radio FFT bloğu FFT uzunluğu, ileri/ters yön ve pencere katsayılarını akış
grafiğinde yapılandırılabilir tutar ve FFTW kullanır.[^gnuradio-fft] Bu yapı yeni
dedektörleri, filtreleri ve kayıt kaynaklarını hızla bağlamak için uygundur.
`gr-inspector` enerji tespiti, elle ya da otomatik eşik, sinyal ayırma, OFDM
parametre kestirimi ve GUI blokları sağlar.[^gr-inspector] Bu iki proje birlikte
özellikle aynı I/Q üzerinde alternatif algoritma prototiplemek için güçlü bir
referans oluşturur.

GNU Radio şu alanlarda ileridedir:

- yeni DSP grafiği kurma ve blokları değiştirme hızı;
- geniş hazır blok ve donanım kaynak ekosistemi;
- araştırma algoritmalarını gözlemleme ve aynı kayıt üzerinde karşılaştırma;
- Python/C++ ile hızlı özel blok geliştirme.

Bu projenin avantajı deney grafiğinin üretim sisteminde serbestçe değişmemesi;
profilin bütün katmanlarda aynı nesil numarasıyla uygulanması ve donanım
uyuşmazlığında veri kabulünün kapanmasıdır. Bu avantaj ancak hedef görev ve bu
donanım için geçerlidir. GNU Radio'nun daha geniş algoritma ekosistemine karşı
genel bir üstünlük iddiası değildir.

## FPGA yaklaşımı sektör örnekleriyle uyumlu mu?

AMD XFFT IP, çalışma zamanı uzunluğu seçildiğinde NFFT yapılandırma alanıyla
boyut değiştirmeyi destekler. Güncel PG109 tablosunda NFFT 12/13/14 sırasıyla
4096/8192/16384'tür. AMD aynı zamanda dinamik uzunluğun daha fazla mantık
kaynağı tüketebileceğini ve azami saati düşürebileceğini belirtir; araçtaki hedef
veri hızı gerçek uygulama garantisi değildir.[^amd-size][^amd-config] Bu nedenle
projede OOC tahminle yetinmeyip tam yerleştirme/yönlendirme ve fiziksel kart hız
ölçümü yapılması doğru yaklaşımdır.

Ettus RFNoC da pencere ve FFT'yi ayrı FPGA blokları olarak sunar. FFT denetim
sınıfı yön, uzunluk, ölçekleme, kaydırma ve çevrimsel önek ayarlarını; pencere
denetimi katsayı yüklemeyi sağlar.[^rfnoc-fft][^rfnoc-window] Bu örnek, pencere
ve FFT'nin donanımda denetlenebilir olmasının yaygın bir yaklaşım olduğunu
gösterir. Aynı zamanda iki ayarın paket/çerçeve boyuyla birlikte ele alınması
gerektiğini de destekler.

## Hangi ayarlar arayüzde olmalı?

“Donanımda bulunan her şeyi göster” yaklaşımı yerine operatörün görev sonucunu
etkileyen, gerçek alt katmana bağlı ve güvenli sınırları doğrulanmış ayarlar
gösterilmelidir. Tanı register'ları ve uygulanmamış seçenekler sistem ekranında
salt okunur olabilir; tespit ekranında çalışıyormuş gibi sunulmamalıdır.

| Ayar | Doğru yer | Bugünkü durum | Karar |
|---|---|---|---|
| FPGA FFT 4096/8192/16384 | Sinyal tespiti ayarları | PL/PS/PC ve kartta doğrulandı | Kullanıcıya açık |
| Normal/zayıf CFAR katsayısı | Sinyal tespiti ayarları | Kartta uygulama ve geri okuma doğrulandı | Uzman kontrolü olarak açık; uyarı ve varsayılan dönüş korunur |
| HackRF LNA/VGA | Canlı RX / kaynak denetimi | Donanıma ait alım kazancı | Canlı kaynakla ilişkili yerde açık; SigMF için gösterilmez |
| Görüntü FFT, dBFS tabanı/aralığı, tepe tut | Spektrum görünümü | PC sunum yolu | Tespit FFT'sinden ayrı etiketle açık |
| Hann dışı pencere | Sinyal tespiti ayarları | PL ürün yolunda uygulanmadı | Şimdilik kapalı; bit-doğru ve RF kabulinden sonra açılabilir |
| Örtüşme ve spektral ortalama | Spektrum veya deney profili | Ürün tespit sözleşmesinde yok | Önce PC replay deneyinde değerlendir; görev kazancı kanıtlanırsa uygula |
| CFAR referans/koruma hücresi ve sıra | Geliştirici profil/preset | RTL yapısını ve maliyeti etkiler | Serbest sayı alanı yerine doğrulanmış profiller kullan |
| ARM M/N ve geniş bant yaşam döngüsü | Tespit profili | Sabit doğrulanmış politika | Aynı-IQ Pd/Pfa taramasından sonra sınırlı preset düşünülebilir |

HackRF One için resmi libhackrf başlığında baseband VGA 0–62 dB, 2 dB adım;
LNA 0–40 dB, 8 dB adım olarak tanımlıdır.[^hackrf-gain] Arayüz doğrulayıcıları
bu gerçek sınırlarla uyumlu kalmalı, kullanıcı değeri kabul edildi sanılırken
sürücüde yuvarlama veya kırpma oluşmamalıdır. Kazanç artışı doğrudan “daha iyi
tespit” değildir: ADC kırpılması, intermodülasyon ve yükselen gürültü tabanı
yanlış alarmı artırabilir.

## Hann ve FFT seçimi ne kazandırır, ne kaybettirir?

4096'dan 8192 veya 16384'e çıkmak 2 MS/s tespit yolunda bin aralığını yaklaşık
488,28 Hz'den 244,14 ve 122,07 Hz'e düşürür. Yakın dar taşıyıcıları ayırmak ve
frekans kestirimini iyileştirmek için yararlıdır. Buna karşılık tek karenin zaman
süresi 2,048 ms'den 4,096 ve 8,192 ms'ye çıkar. Kısa darbelerde zaman çözünürlüğü
azalır; ARM/PL yükü ve olay semantiği değişebilir. Bu yüzden büyük FFT otomatik
olarak daha hassas değildir.

Hann genel kullanım için iyi sızıntı azaltma ve makul ana lob dengesi sağlar.
Dikdörtgen pencere bin merkezindeki tonlarda daha dar ana lob verir fakat bin
dışı tonlarda yan lob sızıntısı artar. Flat-top genlik ölçümü için yararlı,
Blackman-Harris güçlü komşu yayın yanında zayıf ton için yararlı olabilir; her
biri farklı koherent kazanç ve eşdeğer gürültü bant genişliği taşır. Pencere
değiştiğinde yalnız katsayı ROM'u değişmez. Güç normalizasyonu, CFAR gürültü
istatistiği, eşik profili ve ölçüm kalibrasyonu da yeniden doğrulanmalıdır.

Bu nedenle pencere seçimini kontrol altına almak uzun vadede doğrudur; bugün
arayüze bir açılır liste eklemek doğru değildir. İlk uygulanacak sıra:

1. Hann, Hamming, Blackman-Harris ve dikdörtgen için float64 referans ve sabit
   nokta katsayı üretimi.
2. Tüm 4096/8192/16384 boyutlarında taşma, koherent kazanç, ENBW ve bit-doğru
   RTL karşılaştırması.
3. Aynı-IQ sahnelerinde dar ton, iki yakın ton, güçlü-zayıf komşu, geniş bant ve
   kısa darbe Pd/Pfa taraması.
4. PL kaynak/zamanlama ölçümü ve kare sınırında atomik pencere+FFT+CFAR profili.
5. Yalnız geçen kombinasyonları adlandırılmış preset olarak arayüze açma.

## Saha olmadan tamamlanabilecek geliştirme

### 1. Ortak tekrar oynatma korpusu

Kayıtların örnek hızı, merkez frekansı, veri türü, donanım, kazanç ve zamanını
makinece okunabilir saklamak gerekir. SigMF, örnek verisiyle JSON metadata'yı
bir kayıt nesnesinde birleştirir ve veri SHA-512 alanı tanımlar; farklı araçların
aynı veri üzerinde çalışmasını ve sonuçların yeniden üretilmesini amaçlar.[^sigmf]
Mevcut kayıt yolu bu yönde ilerliyor. Sonraki korpus şu etiketleri içermelidir:

- TX kapalı, yalnız gürültü ve yerel girişim;
- tek ton ve bin içi/bin dışı frekans ofsetleri;
- yakın güçlü/zayıf iki ton;
- AM, NFM, BPSK, QPSK ve geniş bant örnekler;
- değişen SNR, süre, görev çevrimi ve bant genişliği;
- kırpılmış, paket kayıplı ve eksik metadata olumsuz örnekleri.

### 2. Aynı-IQ rakip karşılaştırması

Her araç aynı örnek kesitini kullanmalıdır. SDRangel'de spektrum ve Frequency
Scanner, GNU Radio'da FFT/enerji dedektörü veya gr-inspector, bu projede PC
referans ve PL/ARM olay yolu çalıştırılır. Karşılaştırma ölçütleri:

- olay bazında Pd ve zaman/frekans eşleşmesi;
- gürültü kayıtlarında saat başına yanlış olay ve hücre Pfa;
- ilk tespit gecikmesi ve olay bırakma gecikmesi;
- yakın yayınları ayırma, geniş bant sınırı ve kısa darbe yakalama;
- CPU/GPU/FPGA kullanımı, bellek, kuyruk tepesi ve sürdürülebilir hız;
- aynı ayar ve kaynak kimliğiyle beş bağımsız tekrar.

SDRangel görüntüsüne bakıp “biz daha iyiyiz” demek veya yalnız tek bir tonu
bulmayı başarı saymak geçerli karşılaştırma değildir.

### 3. Sayısal Pd/Pfa ve sağlamlık taraması

Saha gerektirmeyen Monte Carlo testinde rastgele gürültü tohumu, SNR, taşıyıcı
ofseti, faz, bant genişliği, başlangıç zamanı ve yakın girişim gücü taranabilir.
Her profil için güven aralığıyla Pd/Pfa, gecikme ve birleşme/ayrılma hatası
raporlanır. Bu, Hann dışı pencere veya farklı CFAR presetlerinin arayüze
açılmasından önceki ana seçim kanıtı olmalıdır.

### 4. Sistem dayanıklılığı

HackRF olmadan SigMF ve yapay Ethernet kaynaklarıyla uzun GUI+kart koşusu,
paket tekrar/sıra atlama/CRC bozulması, profil değiştirirken iptal, hizmet
yeniden başlatma, kart bağlantısının kesilmesi ve kuyruk baskısı test edilebilir.
8192 profilinin hız payı yaklaşık %2,39 olduğu için CPU frekansı, IRQ yükü ve
arka plan süreçlerine karşı ayrıca stres testi yapılmalıdır.

### 5. Kalıcı ürün ve soğuk açılış hazırlığı

Güncel bitstream ve hizmetler hash-kilitli bir PetaLinux/BOOT ürünü olarak
paketlenebilir. Kartı kapatıp açtıktan sonra FPGA kimliği, ABI, hizmet hash'i,
varsayılan 4096 profil, ağ köprüsü ve ilk I/Q kabulü otomatik denetlenmelidir.
Bu fiziksel kart ister fakat RF saha ortamı istemez.

## Fiziksel RF olmadan kapanmayacak maddeler

| Açık kabul | Neden yazılım/replay yetmez? | Gerekli ölçüm |
|---|---|---|
| Gerçek Pd/Pfa | Yapay gürültü anten, yerel girişim ve analog bozulmayı temsil etmez | Kör, etiketli TX kapalı/açık tekrarları; güven aralığı |
| Mutlak dBm | dBFS; anten, kablo, filtre ve kazanç zincirini içermez | Kalibre kaynak/güç ölçer ve frekansa bağlı düzeltme |
| LNA/VGA optimumu | Gürültü figürü, sıkışma ve intermodülasyon ortama bağlıdır | Kazanç süpürmesi, kırpılma ve zayıf/güçlü komşu senaryosu |
| Anten ve saha kapsaması | Polarizasyon, yön, çok yollu yayılım ve gölgelenme kayıtta sabitlenemez | Kontrollü konum/mesafe/yön matrisi |
| Gerçek HackRF+GUI dayanıklılığı | USB zamanlama ve cihaz davranışı emülatörden farklıdır | Güncel imajla uzun canlı RX, kayıp/kuyruk/gecikme kaydı |
| RF pencere üstünlüğü | Pencere seçiminin değeri gerçek girişim dağılımına bağlıdır | Aynı kör sahnede pencere presetlerinin karşılaştırması |

## Öncelikli kalan çalışma planı

1. **Depo ve sayısal kabul:** güncel kaynakta bütün ilgili Python/C/RTL/QML
   testleri, Linux hizmet doğrulayıcısı ve kanıt paketlerinin hash denetimi.
2. **HackRF olmadan uzun yol:** SigMF → PC → kart → GUI üzerinde profil başına
   en az 30 dakika; olay, kuyruk, sıra, CRC, bellek ve iptal ölçümü.
3. **Aynı-IQ kıyas korpusu:** SigMF metadata ve hash ile SDRangel/GNU Radio/
   proje sonuçlarını ortak değerlendirme şemasına bağlama.
4. **Pencere laboratuvarı:** dört aday pencereyi önce referans/RTL/replay
   katmanında değerlendirme; kazanan presetleri arayüz taslağına alma.
5. **Kalıcı imaj ve soğuk açılış:** kart kimliği ve varsayılan profil kabulini
   yeniden üretilebilir hale getirme.
6. **HackRF bağlandığında canlı RX:** her FFT boyutunda kısa bağlantı, ardından
   4096 varsayılanla uzun GUI+RX; LNA/VGA sınır, kırpılma ve otomatik kazanç
   davranışı.
7. **Kontrollü kör RF:** TX kapalı/açık/kapalı sırası, bilinmeyen zaman/frekans
   etiketleme, Pd/Pfa ve yanlış olay kabulü.

İlk beş maddenin büyük bölümü saha dışında yapılabilir. Altıncı madde HackRF ve
kartı, yedinci madde kontrollü RF düzenini gerektirir.

## Nihai gerçekçilik değerlendirmesi

Entegrasyon başarılıdır: arayüzdeki FPGA FFT ve CFAR profil ayarı gerçek
donanım yoluna bağlıdır; kart dönüş değeri okunur; üç uzunluk gerçek zaman
hızını fiziksel kartta üç kez geçmiştir. Sistem gerçek I/Q'yu işlemek için
tasarlanmış ve önceki HackRF/SigMF akışlarında işlemiştir. Güncel dinamik FFT
ürünüyle gerçek HackRF+GUI koşusu yapılmadığı için son kaynak için “uçtan uca
canlı RX kabul edildi” denemez.

Mimari yaklaşım ciddidir ve genel amaçlı SDR uygulamalarından farklı olarak
hedef donanımda ölçülmüş bir PL/PS bölüşümüne sahiptir. SDRangel'in özellik
genişliği ve GNU Radio'nun deney esnekliği daha iyidir. Bu projenin hedef
donanımdaki deterministik tespit boruhattı ve izlenebilirliği güçlüdür. RF
hassasiyeti bakımından üstünlük iddiası için henüz veri yoktur. Doğru hedef,
rakiplerin bütün özelliklerini kopyalamak değil; ortak aynı-IQ ve kör RF
ölçümlerinde seçilen görev için daha düşük gecikme ve kaynakla en az eşit
Pd/Pfa göstermektir.

## Kaynaklar

[^local-fft]: Yerel üç tekrarlı fiziksel kanıt:
    [`st06-runtime-fft-physical-repeated-20260911.json`](../../results/evidence/phase08/st06-runtime-fft-physical-repeated-20260911.json)
    ve [`DETECTION_RUNTIME_CONFIG_CONTRACT.md`](../interfaces/DETECTION_RUNTIME_CONFIG_CONTRACT.md).
[^sdrangel-repo]: SDRangel resmi deposu, mimari ve desteklenen cihaz/özellikler:
    <https://github.com/f4exb/sdrangel>
[^sdrangel-spectrum]: SDRangel resmi spektrum bileşeni belgeleri:
    <https://github.com/f4exb/sdrangel/blob/master/sdrgui/gui/spectrum.md>
[^sdrangel-scanner]: SDRangel resmi Frequency Scanner belgeleri:
    <https://github.com/f4exb/sdrangel/blob/master/plugins/channelrx/freqscanner/readme.md>
[^sdrangel-measurements]: SDRangel resmi spektrum ölçümü belgeleri:
    <https://github.com/f4exb/sdrangel/blob/master/sdrgui/gui/spectrummeasurements.md>
[^gnuradio-fft]: GNU Radio resmi FFT bloğu belgeleri:
    <https://wiki.gnuradio.org/index.php/FFT>
[^gr-inspector]: GNU Radio gr-inspector resmi deposu:
    <https://github.com/gnuradio/gr-inspector>
[^amd-size]: AMD XFFT PG109, çalışma zamanı Transform Size:
    <https://docs.amd.com/r/en-US/2026.1/pg109-xfft/Transform-Size>
[^amd-config]: AMD XFFT PG109, Configuration Tab ve kaynak/hız uyarıları:
    <https://docs.amd.com/r/en-US/2026.1/pg109-xfft/Configuration-Tab>
[^rfnoc-fft]: Ettus UHD RFNoC FFT denetim sınıfı:
    <https://files.ettus.com/manual/classuhd_1_1rfnoc_1_1fft__block__control.html>
[^rfnoc-window]: Ettus UHD RFNoC Window denetim sınıfı:
    <https://files.ettus.com/manual/classuhd_1_1rfnoc_1_1window__block__control.html>
[^hackrf-gain]: Great Scott Gadgets resmi `libhackrf` API başlığı:
    <https://github.com/greatscottgadgets/hackrf/blob/main/host/libhackrf/src/hackrf.h>
[^sigmf]: SigMF resmi belirtimi:
    <https://sigmf.org/>
