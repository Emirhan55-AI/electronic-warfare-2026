# ADR-0040 — PHASE-08 Çok Kareli Dar Bant Kanıtı

- Durum: PL→paket→PS kaynak bağı, Vivado bitstream, kalıcı PetaLinux P09 imajı
  ve sayısal ZedBoard işlev/hız kabulü geçti; kör canlı RF saha kabulü açık
- Kapsam: Bilinmeyen frekanstaki zayıf fakat kararlı dar bant yayınların bulunması
- Bağlı gereksinimler: KTR-4.1, KTR-4.1-OPS-B0
- Ön koşullar: ADR-0035, ADR-0036, ADR-0037, ADR-0039

## Sorun

FPGA'daki tek karelik rank-24/32 OS-CFAR, güçlü ve yerel çizgileri işler; fakat
tek karede yaklaşık 9,33 dB eşiğin altında kalan, birçok kare boyunca aynı RF
frekansında duran bir yayın temporal çekirdeğe hiç aday göndermeyebilir. 2/3
zamansal doğrulama, kendisine hiç ulaşmayan bir adayı kurtaramaz.

2 Eylül 2026 tarihli kör 700–900 MHz taramasında 853,98837890625 MHz çizgisi
birinci ayarda 120/120, bağımsız ikinci LO ayarında 40/40 karede bilgisayardaki
çok kareli RX enerji yoluyla bulunmuştur. Operatör tarama tamamlandıktan sonra
vericiyi 854 MHz olarak açıklamıştır. Bu yararlı bir kör deney sonucudur; ancak
FPGA olayı değildir ve tek deney bütün 1 MHz–6 GHz çalışma aralığını doğrulamaz.

## Bilimsel dayanak

- Hann penceresi, sonlu kayıttaki spektral sızıntıyı yönetmek için Harris'in
  pencere karşılaştırmalarıyla uyumlu kullanılır:
  [Harris, 1978](https://doi.org/10.1109/PROC.1978.10837).
- Kısa değiştirilmiş periodogramların doğrusal güç alanında koherent olmayan
  zaman ortalaması, Welch güç spektrumu kestiriminin temel yaklaşımıdır:
  [Welch, 1967](https://doi.org/10.1109/TAU.1967.1161901).
- Bilinmeyen dalga biçiminde enerji karşılaştırması Urkowitz'in enerji tespiti
  çerçevesiyle uyumludur; gürültü belirsizliği nedeniyle eşik saha kanıtı olmadan
  evrensel kabul edilmez:
  [Urkowitz, 1967](https://doi.org/10.1109/PROC.1967.5573).
- Yerel değişen arka plan ve çoklu hedeflerde sıra istatistikli referans kullanımı
  OS-CFAR literatürüne dayanır:
  [Rohling, 1983](https://doi.org/10.1109/TAES.1983.309350).

Bu kaynaklar yöntemi destekler. En az 32 kare, 6 dB ortalama P/N, yüzde 75
doluluğu, 5 kHz bileşen komşuluğu ve 50 kHz küme sınırı bu makalelerden alınmış
evrensel sayılar değildir. Bunlar ürün profilidir ve sentetik, kayıtlı I/Q,
FPGA/ARM eşdeğerliği ile kontrollü fiziksel negatif/pozitif deneylerden geçmeden
saha doğruluğu iddiası oluşturmaz.

## Karar

1. Frekans listesi, tam MHz önceliği, 854 MHz düzeltmesi veya operatörün sonradan
   söylediği değere yuvarlama kullanılmaz. Aynı matematik 1 MHz–6 GHz içinde
   mutlak RF ekseninden bağımsız çalışır.
2. En az 32 Hann/FFT doğrusal güç karesi koherent olmayan biçimde ortalanır.
   Yerel gürültü, adayın 50–250 kHz uzağındaki hücrelerin sağlam medyanından
   kestirilir.
3. Aday oluşturmak için en az 6 dB ortalama P/N ve karelerin en az yüzde 75'inde
   aynı hücrede 6 dB aşım gerekir.
4. İkinci, farklı LO ayarında aynı mutlak RF bileşeni yeniden görülmelidir. Bu
   denetim alıcı DC/LO ve sayısal iç ürünlerini azaltır; dış verici kimliği
   kanıtlamaz.
5. Güçlü kapıyı geçen bileşen aday sahibidir. Adayın çevresindeki en az 1,5 dB
   gürültü üstü, en çok 5 kHz aralıklı kararlı bileşenler 50 kHz ile sınırlı bir
   emisyon kümesi oluşturabilir. Gürültü üstü güç merkezi `ölçülen emisyon
   merkezi`, en güçlü hücre ise `en güçlü çizgi` olarak ayrı saklanır. Tek çizgi
   doğrudan spektral tepedir. Bu değer keyfi modülasyonda kesin taşıyıcı diye
   adlandırılmaz.
6. Bilgisayardaki uygulama altın referans, tarama yöneticisi ve görüntüleme
   sahibidir. Yarışma ürün kararının sahibi ZedBoard'dur. Güncel P09 imajında PL
   aday paketi zayıf sınıf bayrağını taşır ve PS 24/32 kararı verir. Bu bağ
   sentez, route, bitstream, soğuk açılış ve sayısal kart kabulünden geçmiştir.
7. Ürün bağı için seçilen hedef, mevcut rank-24/32 OS gürültü kestirimini PL'de
   koruyup aynı kestirime karşı ikinci ve daha düşük bir 6 dB kapıdan yalnız
   seyrek tepe adayları çıkarmaktır. ARM, tepeyi ±2 hücre destekleyerek 32
   karelik halkada en az 24 gözlem ister. Böylece yalnız ortalama spektrum
   taşınmasında kaybolacak kare doluluğu korunur. Geniş bant yol mevcut bölgesel
   kurtarmada kalır; bu ikinci yol zayıf ve kararlı dar bant kurtarmasıdır.
8. Zayıf adaylar normal tek-kare adaylarından paket bayrağıyla ayrılır. Mevcut
   2/3 doğrulama yalnız normal adaylara, 24/32 doğrulama yalnız zayıf adaylara
   uygulanır. ABI değişikliği eski paketlerin reddedilmesine veya zayıf adayların
   yanlışlıkla 2/3 kuralıyla onaylanmasına izin veremez.
9. Bilgisayar sonuçları görüntülemeyi ve tarama ayarlarını yönetir. P09 ile
   FPGA/ARM olay listesi karttan gelir. Bilgisayardaki iki LO denetimi ayrı bir
   alıcı-spur kontrolüdür; FPGA/ARM olayı veya dış verici kimliği diye sunulmaz.

## Kabul kapıları

- CW, simetrik/asimetrik çok bileşenli dar bant, iki yakın bağımsız yayın,
  aralıklı yayın, renkli gürültü, DC/LO ürünü ve alıcı iç ürünleri için frekans
  gerçeğinden bağımsız testler.
- En az dört ayrı RF merkezinde aynı taban bant geometrisinin aynı sonucu vermesi.
- Python ile portable ARM C aday alanlarında ve kararlarında sıfır fark.
- İdeal üstel gürültü hesabı yanında renkli/eğimli gürültü Monte Carlo testi;
  zayıf paket yükü ve 24/32 yanlış doğrulama sayısı raporlanır.
- RTL/spektral özet paketinde bit-doğru model, backpressure, reset ve taşma testleri;
  Vivado sentez, route, timing, bitstream ve fiziksel kart kabulü.
- Kontrollü TX kapalı ve açık tekrarlarında yanlış olay/dakika, tespit olasılığı,
  ilk tespit süresi ve frekans hatası. Tek başarılı yayın tüm bant kanıtı değildir.

Bu kapılar tamamlanmadan PHASE-08 ve sinyal tespiti bakım aşaması kapanmaz.

## 2–4 Eylül 2026 uygulama ve fiziksel kanıtı

- `algorithms/ps/persistent_weak_cfar.py`, 6 dB zayıf PL kapısını ve ±2 hücre
  destekli 24/32 PS halkasını frekans gerçeği kullanmadan modeller.
- `platforms/embedded/p0/src/p0_persistent_weak.c` aynı sınırlı halkayı portable
  C olarak uygular; WSL/GCC derlemesinde Python alanlarıyla birebir eşleşmiştir.
  PetaLinux tarifi aracı ve üretim hizmetini derler; Linux host hizmet kabulü
  geçmiştir. Güncel ADR-0040 XSA ile son artımlı PetaLinux 2025.2 yapısında
  5679/5679 görev tamamlanmış; ARM ikilileri `image.ub`, aynı bitstream ise
  `BOOT.BIN` içine girmiştir. P09 imajı SD karttan soğuk başlatılmıştır.
- `p0_os_cfar_decision_engine.sv` aynı rank-24/32 değerinden ikinci 6 dB karar
  biti üretir. Icarus benzetimi 5× hücreyi yalnız zayıf, 10× hücreyi normal ve
  zayıf aday olarak doğrulamıştır. Sınıflı gruplama, PHASE-06I paket bayrakları
  ve PS yönlendirmesi güncel kaynakta bağlıdır. Tam RTL hiyerarşisi 8 karede
  113 adayı 629 AXI64 beat ile sıfır metadata farkı ve 60 backpressure
  kararlılık kontrolüyle geçmiştir.
- Gerçekçi dondurulmuş FFT karesinde 6 dB kapı 321 ayrı grup ürettiği için ilk
  256-aday sınırı yetersiz bulunmuştur. PL, paket ve PS ortak sınırı kanıtlanmış
  azami 1352 gruba çıkarılmıştır; böylece taşmada bütün zayıf karenin kaybolması
  önlenmiştir. Tam Zynq-7020 uygulaması 50 MHz'te setup WNS `+0,199 ns`, hold
  WHS `+0,010 ns`, sıfır failing endpoint ve sıfır route/DRC hatasıyla geçmiştir.
  Slice LUT kullanımı 48.040/53.200, yani `%90,30` olduğundan kaynak payı risk
  olarak korunur.
- Üretim `p0_ed_pipeline` testi, zayıf paketlerin 24/32 tamamlanmadan olay
  üretmediğini, kare sıra boşluğunda halkayı sıfırladığını, normal güçlü yolu
  2/3'te tuttuğunu ve dokuz boş kare sonrasında zayıf olayı `ended` yaptığını
  WSL/GCC ile doğrulamıştır.
- ARM yükünü sınırlamak için yalnız zayıf sınıftaki adaylar kesin
  `peak_power/order_statistic` oranıyla sıralanır; her karede en güçlü sekiz
  konum 24/32 halkasına alınır. Güçlü tek-kare adayları bu bütçeyi tüketmez.
  Python referans modeli aynı kesin oran ve bağ kırma sırasını uygular. Beyaz,
  eğimli ve dalgalı gürültü Monte Carlo'su bu son top-8 profille yeniden
  üretilmiş; üç profilde yanlış doğrulama sıfır, beş FFT konumunda doğrulama 5/5
  olmuştur.
- Bu kaynak ve simülasyon kapılarının güncel hashleri
  `results/evidence/phase08/persistent-weak-integration-v1.json` içinde birlikte
  kaydedilir. P09 soğuk açılışından sonra 104-adaylı işlev dizisi güçlü adayları
  kayıpsız korumuş ve boş karelerde yaşam döngüsünü doğru kapatmıştır. Beş
  fiziksel hız koşusunda 20.480 ölçüm karesi tamamlanmış; minimum hız
  `525,826333965 kare/s`, gerekli hız `488,28125 kare/s`, sıra ve aday düşürme
  hatası sıfırdır. Kanıt
  `results/evidence/p0/adr0040-physical-acceptance.json` dosyasındadır. Kör canlı
  RF Pd/Pfa, ilk tespit süresi ve kalibre frekans/güç kabulü açık kalır.
- `persistent-weak-model-v1.json`, 64'er beyaz, eğimli ve dalgalı gürültü
  penceresinde sıfır 24/32 yanlış doğrulama ve beş ayrı FFT konumunda 5/5
  doğrulama kaydeder. İdeal bağımsız üstel varsayım hesabı fiziksel renkli
  gürültü veya alıcı spur'u için saha garantisi sayılmaz.
