# Sinyal tespiti ayarları ve kaynak kılavuzu

15 Eylül 2026 · PHASE-08 / ST-06 · KTR-4.1 / KTR-4.1-OPS-B0

## Güncel alıcı ve ses kontrolleri

### Operatör için kısa kullanım tablosu

Alanların üzerinde bekleyince kısa yardım açılır. Sabit frekans ekranı LNA/VGA'yı
aynı satırda, AMP'yi hemen altında; ayrı pencere yalnız FPGA tespitini gösterir.
Dinlemeye ait kontrol Dinleme görevindedir; salt çizim ayarları ürün yüzeyinde
operatör ayarı olarak sunulmaz.
Bu başlangıç önerileri RF kabulü veya her ortamda en iyi ayar iddiası değildir.

| Ayar | Ne işe yarar? | Nereden başlamalı, ne zaman değiştirmeli? |
|---|---|---|
| LNA / VGA | Alıcıdaki iki kazanç kademesi | AMP kapalı, 16/16 dB başlangıç olabilir. LNA 8, VGA 2 dB adımlıdır; sırayla deneyin. Harici yükselteç varsa daha düşük başlayın. Kırpılmada azaltın. |
| AMP | Ek RF yükseltmesi | Kapalı başlayın. Zayıf alımda açıp karşılaştırın; bozulma artarsa kapatın. Ayarlanabilir dB değeri ve ara durumu yoktur. |
| Normal CFAR eşiği | Normal eşik aşımını belirler | Varsayılan yaklaşık 8,58. Gerekiyorsa 0,1 adımla deneyin. Azaltmak yanlış alarmları da artırabilir. |
| Zayıf CFAR eşiği | Zayıf adaylar için eşiktir | Varsayılan yaklaşık 3,98. Değeri yükseltmek hassasiyeti artırmaz. Kontrollü açık/kapalı sinyal kaydı olmadan ideal değer belirlenemez. |
| FFT | FPGA tespitindeki frekans hücrelerinin ayrıntısı | 4096 ile kalın. Büyütmek işlem yükünü değiştirir; otomatik parametre yolu 4096 ister. Küçültme yeniden başlatma gerektirir. |
| Dinleme genişliği | Dinlenen kanalın kapsadığı aralık | Tespit önerisiyle başlayın. AM: 6/9/12; NFM: 8/12,5/16/25 kHz seçenekleri yayına göre denenir. Gereksiz büyütmeyin. |
| İnce frekans ayarı | Dinleme merkezini kaydırır | Önce tespit merkezini kullanın; gerekiyorsa ±0,1 kHz deneyin. Tarama merkezini değiştirmez. |
| NFM ses düzeltmesi | Sesin tiz kısmını yumuşatır | Mevcut profil 750 µs; 0 kapalıdır. Yayına uygun seçilir, tespit hassasiyeti değildir. |
| Görüntü FFT / yenileme | Çizimin ayrıntısı ve sıklığı | Ürün varsayılanı 16384 / 15 karedir; tespit kontrolü olmadığı için operatör yüzeyinde gösterilmez. |
| Görüntü ölçeği | Sadece çizimin görünümü | İlk anlamlı karede otomatik ayarlanır; tespit eşiğini değiştirmez. |
| Tarama gözlemi | Her frekans penceresinde gözlem süresi | 128 kare başlangıç. 64 daha kısa, 256 daha uzun gözlem; hız/kaçırma dengesi sahada ölçülür. |
| Yerleşme | Frekans değişiminden sonraki geçiş karelerini dışlar | 8 kare varsayılanını koruyun. 16/32 seçimi ancak başlangıç geçişi ölçülürse değerlendirilir. |

Kazanç kademeleri ve 16/16 başlangıcı:
[HackRF üretici kılavuzu](https://hackrf.readthedocs.io/en/latest/setting_gain.html).
Bias-T harici donanım bilgisi doğrulanana kadar eklenmez.

LNA/VGA aynı satırda, AMP hemen altında kalır. AMP düğmesi alım dururken tek
tıklamayla `Kapalı` ile `Açık` arasında değişir ve seçim sonraki alım yollarına
taşınır. Canlı alım veya bant taraması sürerken düğme pasiftir; önce tarama
durdurulur. NFM ses düzeltmesinin iç sözleşmesi
0–2000 µs sınırını korur; ürün arayüzü Dinleme görevinde yalnız `Kapalı` ve
mevcut `750 µs` profilini sunar. Ayar yalnız sonraki ses hazırlamayı etkiler;
önceki ses yeniden etiketlenmez. CFAR katsayıları FPGA penceresinde virgül veya
noktayla düzenlenir; üst sınırlar hariçtir. Varsayılan katsayı tamlığı korunur;
deneysel hassasiyet profilleri eklenmedi.

Normal ve zayıf eşikler LNA/VGA gibi donanımın ayrık kazanç basamakları değildir;
sınırları içinde sürekli katsayılardır. Güncel kaynakta fiziksel olarak
doğrulanmış alternatif `hassas/normal/güçlü` eşik profilleri bulunmadığı için
seçim kutusu eklenmez. `Karttan Oku` etkin tam değerleri getirir,
`Varsayılana Dön` doğrulanmış başlangıç çiftini yükler; kontrollü karşılaştırma
kanıtı oluşursa hazır profiller ayrıca değerlendirilir.
Arayüz okunabilirlik için bu değerleri iki ondalıkla gösterir; operatör alanı
değiştirmediyse karttan okunan tam sabit nokta değeri yeniden uygulanır.

FFT 8192/16384 olduğunda alıcının ham önizlemesi görüntü yolunun sabit 16.384
kompleks örnek penceresinden uzundur. Görüntü ve kaba aday yolu ilk 16.384 gerçek
örneği kullanır; bu, FPGA tespit FFT'sini veya eşiklerini küçültmez. Büyük
FFT'den 4096'ya dönüş kontrollü kart yeniden başlatması ister; uygulamayı yeniden
açmak yalnız masaüstü yazılımını yeniler.

Tespit kartında kullanılan P/N, tepenin yerel gürültüye göre bağıl oranıdır;
dBm veya kalibre edilmiş mutlak güç değildir. FPGA gözlem sayısı da olay
sürekliliğidir. Bu iki değer iç tespit kanıtında tutulur, fakat parametre sonucu
sanılmaması için kullanıcı üzerine-gelme metninde gösterilmez. dBm yalnız
eşleşen ve geçerli kalibrasyonla parametre ölçümünde anlamlıdır.

Dinleme ekranında AM 6/9/12 kHz, NFM 8/12,5/16/25 kHz başlangıç seçenekleri,
tespit önerisi/özel giriş, ±100 Hz ince ayar ve yalnız NFM'de ses düzeltmesi
bulunur. Bunlar her emisyon için doğrulanmış optimum değerler değildir; backend
kaynak bant sınırını korur. WFM ve susturma eklenmedi. Analog filtre/PPM seçimi
ve Bias-T kapıları açılmadı.

Aşağıdaki 2 MS/s tarama süresi tablosu eski tam tarama profilinin kapsamıdır.
Güncel geniş bant penceresinde 10 MS/s, 4096 FFT kullanılır: 64/128/256 kare
26,2144/52,4288/104,8576 ms ham yakalama eder. Yerleşme bu gözlemin içindedir;
oturum açma, kart işleme, ek doğrulama ve başlangıç koruma süresi ayrıca vardır.
Arayüz bu profilde 512 kareyi sunmaz. Gerçek tarama süresi bu değerlerden ibaret
değildir. Donanımın mevcut fiziksel kabul sınırları değişmedi.

## Arayüzdeki ayarlar

Sabit frekans ekranındaki **Ayarlar** yalnız gerçek tespit
parametrelerini, bant taramasındaki **Tarama Ayarları** yalnız pencere gözlemini
gösterir. İşleme ayarları oturum dururken değiştirilir ve bir sonraki başlatmada
uygulanır. Seçimler uygulama oturumu boyunca korunur; uygulama yeniden açılınca
varsayılanlar gelir.

| Ayar | Seçim / varsayılan | Gerçek etkisi |
|---|---|---|
| LNA | 0–40 dB, 8 dB adım | Fiziksel alıcı kazancı |
| VGA | 0–62 dB, 2 dB adım | Fiziksel alıcı kazancı |
| AMP | **Kapalı** / Açık | İki durumlu ek RF yükselteci; ayarlanabilir dB kademesi değildir |
| FFT | **4096** / 8192 / 16384 | Gerçek FPGA tespit hücrelerini ve işlem yükünü değiştirir |
| FPGA normal CFAR katsayısı | `[1,16)`, varsayılan **8,5801430407** | Normal aday karar eşiğini gerçek FPGA'da değiştirir; tam geri okunur |
| FPGA zayıf CFAR katsayısı | `[1,4)`, varsayılan **3,9810717055** | Zayıf aday eşiğini FPGA ve ARM olay raporunda birlikte değiştirir; normalden büyük olamaz |
| NFM ses düzeltmesi | Kapalı / **750 µs** | Yalnız Dinleme görevindeki NFM sesini değiştirir; tespiti değiştirmez |
| Görüntü FFT / yenileme | İç varsayılan **16384 / 15** | Yalnız çizim; ürün yüzeyinde değiştirilmez |
| Tarama gözlemi | 64 / **128** / 256 kare | 10 MS/s'de 26,2 / 52,4 / 104,9 ms ham yakalama; işleme ve doğrulama ayrıca eklenir |
| Yerleşme | **8** / 16 / 32 kare | Gözlemin başındaki yerleşme kareleri; toplam pencere süresine dahil |

LNA, VGA ve AMP yalnız operatör tarafından seçilir. Canlı oturum bu değerleri
otomatik değiştirmez veya alım seviyesine göre başka kazançla yeniden başlamaz.

Görüntü FFT'si FPGA FFT’sini değiştirmez. Kaba tespit ve canlı RF çizgisi
doğrulaması kendi 16384 noktalı spektrumunu kullanır; sunum 15 DSP karesinde bir
yenilenir ve güç ölçeği ilk anlamlı karede otomatik ayarlanır. Görüntü kareleri
atlansa da FPGA’ya gönderilen ölçüm kareleri bu nedenle atlanmaz. 32768/65536
gerçek FFT için ardışık ham örnek biriktirme ve gecikme/bellek sözleşmesi gerekir;
sıfır doldurma çözünürlük artışı diye gösterilmez.

## Değiştirilebilen ve sabit kalan tespit profili

Güncel tespit profilinde FPGA FFT uzunluğu 4096/8192/16384 seçilebilir. Arayüz
önce alımı durdurur; ABI v2 kontrol mesajı ARM hizmetine, ioctl sürücüye ve
`0x53540602` AXI-Lite kontrol bankasına gider. Profil yalnız tüm DSP zinciri
boşken uygulanır; kuşak numarası, FFT uzunluğu ve iki CFAR katsayısı karttan
tam olarak geri okunmadan başarı gösterilmez. Uyuşmayan I/Q boyu sürücüde
reddedilir.

Aynı açılışta 4096→8192→16384 yönü desteklenir. Fiziksel post-downshift
deneyi XFFT/DMA kilitlenmesi bulduğu için daha küçük FFT seçimi sürücüde
reddedilir; arayüz kartı yeniden başlatmayı ister. Yeniden başlatma 4096
varsayılan profilini yükler. Bu kontrollü servis/kart yeniden başlatmasıdır;
elektriği tamamen kesip yeniden verme biçimindeki ST-06 cold-start kabul
koşusuyla aynı işlem değildir. Bu sınır giderilmeden menü keyfî iki yönlü FFT
değişimi olarak yorumlanmaz.

Her FFT uzunluğu kendi periyodik UQ1.15 Hann ROM'unu kullanır. Dinamik AMD XFFT,
güç normalizasyonu, OS-CFAR sınırları, DMA giriş/çıkış boyları ve ağ/hizmet ABI'si
aynı profile bağlıdır. ARM 8192/16384 güç hücrelerini enerji toplayarak mevcut
4096 olay ızgarasına indirger; böylece geniş bant ve temporal sözleşmeler
değişmez. 4096 doğrudan çözülür; iki ve dört kat indirgeme tamsayı kaydırmayla
yürür.

Tam tasarım 50 MHz'te WNS `+0,613 ns`, WHS `+0,030 ns`, sıfır yönlendirme
hatasıyla geçti; 24.251 LUT, 20.802 register, 94,5 BRAM ve 61 DSP kullanır.
Kartta her boyut üç bağımsız 4.096-kare koşuda gerçek zaman hedefini geçti.
En düşük hızlar 540,081 / 249,970 / 138,120 kare/s; gerekli hızlar 488,281 /
244,141 / 122,070 kare/s'dir.
[Fiziksel sayısal kanıt](../../results/evidence/phase08/st06-runtime-fft-physical-repeated-20260911.json).

Pencere **türü** değiştirilebilir değildir: Hann sabittir. Rectangular,
Blackman veya başka bir pencereyi menüye eklemek; ayrı katsayı ROM'ları,
bit-doğru yazılım/RTL eşdeğerliği, güç normalizasyonu ve CFAR Pd/Pfa yeniden
kalibrasyonu olmadan güvenli değildir. OS-CFAR referans/koruma/rank ve temporal
2/3, 24/32, sekiz-kare değerleri de aynı nedenle serbest sayısal giriş olarak
açılmaz. Normal/zayıf CFAR profilleri sınırlandırılmış hazır seçim ve gerçek
geri okuma ile değişir. Deneysel CI8 çıkış genlik ölçeği canlı varsayılanında
1 kalır; güç telafisi ve RF doğrulaması olmadan operatör kazancı olarak sunulmaz.

## FPGA ve ARM dosyaları

| Katman | Başlangıç dosyası | İncelenecek iş |
|---|---|---|
| FPGA dinamik üst DSP | [p0_dsp_runtime_fft_top.sv](../../algorithms/fpga/p0/rtl/p0_dsp_runtime_fft_top.sv) | Uzunluğa bağlı Hann → dinamik XFFT → güç → OS-CFAR |
| FPGA dinamik blok bağlantısı | [p0_dsp_runtime_fft_bd.v](../../algorithms/fpga/p0/rtl/p0_dsp_runtime_fft_bd.v) | Profil, akış ve hata bağlantıları |
| FPGA AXI profil kontrolü | [p0_detection_profile_control.sv](../../algorithms/fpga/p0/rtl/p0_detection_profile_control.sv) | FFT/katsayı taslağı, atomik uygula, geri okuma ve kuşak |
| FPGA CFAR | [axis_p0_os_cfar.sv](../../algorithms/fpga/p0/rtl/axis_p0_os_cfar.sv) | Hücre sıralaması, eşik, DMA metaverisi |
| FPGA sabitleri | [p0_os_cfar_pkg.sv](../../algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv) | FFT, referans/koruma, normal ve zayıf eşik |
| Tam Vivado oluşturma | [create_st06_runtime_fft_vivado_project.tcl](../../scripts/create_st06_runtime_fft_vivado_project.tcl) | Zynq PS, AXI DMA, 50 MHz saat ve dinamik DSP |
| Dinamik FFT IP tanımı | [st06_runtime_fft_ip_config.tcl](../../scripts/st06_runtime_fft_ip_config.tcl) | Azami 16384, çalışma zamanı NFFT ve ölçek özellikleri |
| ARM hizmeti | [p0_ed_service.c](../../platforms/embedded/p0/src/p0_ed_service.c) | CPU0 DMA/çözme, CPU1 işleme, kuyruk sahipliği |
| ARM tespit zinciri | [p0_ed_pipeline.c](../../platforms/embedded/p0/src/p0_ed_pipeline.c) | Dar/geniş adaylar, normal/zayıf temporal birleştirme, geri alma |
| ARM güç çözme | [p0_pl_os_cfar.c](../../platforms/embedded/p0/src/p0_pl_os_cfar.c) | DMA biçimi doğrulama ve natural/shifted eşleme |
| ARM geniş bant | [p0_st05_stream.c](../../platforms/embedded/p0/src/p0_st05_stream.c) | Sekiz karelik birikim |
| ARM zayıf sinyal | [p0_persistent_weak.c](../../platforms/embedded/p0/src/p0_persistent_weak.c) | 32 karede 24 gözlem ve ±2 bin tolerans |
| ARM normal temporal | [phase06j_temporal.c](../../platforms/embedded/phase06j/src/phase06j_temporal.c) | 2/3 doğrulama ve olay yaşam döngüsü |
| ARM paket tarifi | [p0-dma_1.0.bb](../../platforms/embedded/p0/petalinux/p0-dma_1.0.bb) | PetaLinux hizmeti ve sürücü derlemesi |
| ARM cihaz ağacı bağı | [st06-runtime-control.dtsi](../../platforms/embedded/p0/petalinux/st06-runtime-control.dtsi) | `0x43c00000` profil kontrol bankası ile AXI DMA phandle'ı |
| PC canlı alım | [live_ed.py](../../app/operator_console/live_ed.py) | HackRF, kanal seçici, Ethernet ve kayıt |
| PC kanal seçici | [native_channelizer.py](../../algorithms/p0/native_channelizer.py) | Yerel C++ FIR/NCO yolunun çağrılması |
| Arayüz ayarları | [DetectionSettings.qml](../../app/operator_console/qml/DetectionSettings.qml) | Tespit/görüntü ve tarama ayar panelleri |

Vivado’da **Open Project** ile mevcut yerel
`build/p0/st06-power-v2/vivado/p0_runtime.xpr` açılabilir. Bu eski uygulama
çıktısıdır; kaynaklar çalışma ağacına bağlı olabileceği için tekrar derlemek
eski ölçümü yeniden üretmek anlamına gelmez. İnceleme için Sources içinden
`p0_system.bd` açılır; Block Design’de PS, DMA ve DSP bağlantıları; RTL
Hierarchy’de DSP alt modülleri görülür. FFT IP Customize penceresi de gerçek
IP yapılandırmasını gösterir.

Bu çalışma için ayrı proje yolu
`build/p0/st06-rfft-v4-20260910/vivado/p0_runtime.xpr` olarak oluşturuldu.
Vivado 2025.2 bu bilgisayarda `C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat`
yolundadır. Yeni klonda build klasörleri bulunmayabilir; benzersiz
`P0_BUILD_VARIANT` ile oluşturma Tcl’si çalıştırılır. Kart tanımı bu ortamda
`C:/VivadoBoards` altındadır. ARM C kodu Vivado RTL editöründe sentezlenmez;
editörde incelenebilir, gerçek Linux hizmeti GCC/PetaLinux ile derlenir.

PetaLinux projesinde cihaz ağacı parçası
`project-spec/meta-user/recipes-bsp/device-tree/files/` altına kopyalanır;
`system-user.dtsi` sonuna `/include/ "st06-runtime-control.dtsi"` eklenir ve
`device-tree.bbappend` içindeki `SRC_URI:append` listesine dosya yazılır.
`p0-dma_1.0.bb` ile yanındaki sürücü/hizmet kaynakları
`project-spec/meta-user/recipes-kernel/p0-dma/` tarifine aktarılır. Güncel XSA
import edildikten sonra tam `petalinux-build` ve `petalinux-package boot`
çalıştırılır. 11 Eylül paketi yerelde `build/p0/petalinux-image-20260911/`
altındadır; build dizini sürüm kontrolüne alınmaz, kabul JSON'unda XSA,
BOOT.BIN, image.ub, bitstream ve kurulu ürün hash'leri bulunur.

## Eski zayıf yol neden önemliydi?

Eski aday paketini işleyen giriş, normal eşiği tek karede aşamayan fakat
zaman içinde kararlı kalan adayları 24/32 filtresine bağlıyordu. Güncel güç
paketi girişi bunu çağırmıyordu. Sorun eski dosyanın kullanılmaması değil,
aynı yeteneğin yeni girişte karşılığının bulunmamasıydı.

Yeni DMA v2 biçimi güç ve normal kararın yanında bir zayıf aday biti taşır.
PL zayıf eşik kararını da mevcut sıra istatistiği üzerinden verir. ARM,
yalnız zayıf bölgelerin tepe noktalarında sıra istatistiğini yeniden çıkarır;
en fazla sekiz adayı 24/32 filtresine bağlar. Normal doğrulanmış adaylarla
örtüşen zayıf sonuçlar ikinci olay olarak yayımlanmaz. Sıra kesintisi ve
açık reset birikimi temizler; başarısız işleme durumu geri alınır.

Güç girişindeki zayıf olaylar güncel ölçülen güç ve gürültüyü taşır; tarihsel
ortalama oran mutlak güç gibi sunulmaz. `observed_this_frame` yalnız o karede
aday varsa doğrudur, `last_seen_frame_id` gerçek son aday karesine işaret eder.
Ham aday sayısına seçilen zayıf adaylar da dahildir. İlk sonuç için 32 karelik
pencerenin dolması gerekir; bunun en az 24 karesinde yakın frekans gözlenir.

Eski `A` biçimi kabul edilir ama zayıf bilgi uydurulmaz. Yeni `C/D` biçimi
eski hizmetle çalıştırılmaz; eski çözücü bu yeni biçimi reddeder. Yeni hizmet
ve yeni FPGA imajı birlikte doğrulanmalıdır. Kaynak düzeyindeki bu bağlantı,
kartta yeni ikilinin çalıştığını veya gerçek RF’de Pd artışını kanıtlamaz.

## Saha öncesi doğrulama

`python scripts/check_st06_weak_power_rtl.py` yeni beklenen kelimeleri geçici
klasörde üretir; donmuş v1 kanıtını değiştirmez. `tests/test_st06_product_pipeline.py`
normal/geniş davranışı, iki güç girişinin eşitliğini, zayıf doğrulamayı,
sönmeyi, sıra kesintisini ve eski biçim davranışını denetler.
`tests/test_detection_settings.py` görüntü FFT’sinin gerçek örnek sayısını
değiştirdiğini ve tespit spektrumunu koruduğunu denetler.

Ek zayıf eşik sınırı testiyle 49.152 RTL kelimesi birebir eşleşti. Linux
hizmetinin gerçek CPU0/CPU1 işçi ve istemci yolunda, test DMA kaynağıyla 80
zayıf/açık-kapalı kare doğrulandı. Bu test gerçek FPGA veya RF değildir.
`python scripts/build_st06_weak_service.py` Cortex-A9 hizmetini derler;
yanındaki `service-build.json` kaynak ve ikili hash’lerini kaydeder.
Windows yol sınırı için bu ortamda `T:` depo köküne `subst` ile bağlandı;
aynı proje kısa yoldan `scripts/resume_st06_weak_power.tcl` ile sürdürüldü.

Yeni bitstream’in yerleşim/zamanlaması, kaynak/imaj kimliği ve gerçek ARM
sayısal hızı güncel pakette doğrulandı. Paketli tam yolun sürekli GUI+HackRF
RX kararlılığı ayrı kapıdır; önceki RF sonuçları yeni sürüme aktarılmaz.
Kontrollü RF açık/kapalı/kör test, yanlış alarm ölçümü ve soğuk açılış
tamamlanmadan saha kabulü verilmez. SDRangel veya başka bir projeden üstünlük
iddiası için de aynı ham veri, bant genişliği, gecikme, Pd/Pfa ve işlem yükü
koşullarında karşılaştırma gerekir.
