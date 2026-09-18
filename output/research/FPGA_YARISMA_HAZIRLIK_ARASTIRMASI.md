# Yarışma öncesi FPGA sistemi: gerçek katkı, sınırlar ve ilerleme planı

## Karar özeti

Öneri, çalışan mimariyi korumak; 20 MS/s ve PC’ye yeniden yazma çalışmalarını yarışma sonrasına bırakmak; kalan zamanı tespit edilen sinyalin güvenilir ölçüme ve dinlemeye ulaşmasına ayırmaktır. FPGA’nın katkısı yalnız kartın bulunması değildir: PL’de spektral işleme ve hücre düzeyinde tespit, kartın ARM çekirdeklerinde olay işleme ve parametre çıkarımı vardır. Buna karşılık mevcut kanıt, uçtan uca PC üstünlüğü veya sürekli 10 MS/s işleme iddiasını desteklememektedir.[^1][^2]

Tespitin yeni özellik geliştirmesini sınırlamak, çalışma sırasında tespiti kapatmak demek değildir. Mevcut kaynakta uygun dar aralıklı otomatik parametre ölçümü tespit sürerken yapılabilir. Ayrıntılı operatör ölçümü ise dört güncel kareyi topladıktan sonra alımı durdurur. Bu iki yolun birbirinden ayrılması, yeni bir büyük mimari değişiklikten daha acil bir ürün konusudur.[^3][^4]

Bu rapor 15 Eylül 2026 tarihli kaynak incelemesi, depodaki tarihli deneyler ve birincil teknik kaynaklara dayanır. Yeni fiziksel test yapılmamıştır. Tarihsel deneyler, son kaynak ve çalışan imaj için otomatik kabul sayılmaz. Kesin yarışma tarihi ve güncel özgün şartnamenin tamamı doğrulanmadığından, aşağıdaki plan gün sayısı veya resmî geçme eşiği uydurmaz. PHASE-08/ST-06 ve açık RF kabul kapıları korunur.[^1][^5]

## 1. FPGA bugün gerçekten ne yapıyor?

Görev paylaşımı şu şekildedir:

- **PC:** HackRF USB alımı, sabit izleme için kanal seçme/örnek azaltma, kartla veri alışverişi, arayüz ve kayıt; ayrıca bazı doğrulama işlemleri, deneysel Analog/Sayısal sınıflandırma ve ses demodülasyonu.
- **PL, yani programlanabilir mantık:** Hann pencereleme, FFT, güç hesabı ve OS-CFAR hücre kararları.
- **Kartın ARM CPU0 çekirdeği:** DMA ve veri/güç doğrulama-çözme işleri.
- **Kartın ARM CPU1 çekirdeği:** dar/geniş adaylar, zamansal olay yaşam döngüsü ve akış içi otomatik parametre işlemleri. Ayrı operatör ölçümü hizmetin diğer ARM yürütüm yolundadır; bütün parametre işlerinin CPU1’de olduğu söylenmemelidir. Hizmette dört yuvalı iş hattı ve çekirdek bağlama bulunur.[^2][^3]

Dolayısıyla “ARM’ı veya paralelliği hiç kullanmıyoruz” doğru değildir. Farklı aşamalar arasında örtüşme zaten vardır. Fakat paralel bir mimari, kendiliğinden yeterli uçtan uca hız veya büyük kapasite payı demek değildir. PC, USB, ağ, DMA, PL ve ARM’ın birlikte yetişmesi gerekir. Mevcut darboğazı yalnız FPGA mantığına yüklemek de, FPGA’nın teorik saat hızını bütün sistemin örnekleme kapasitesi saymak da hatalı olur.

Savunulabilir katkı üç başlıktadır:

1. Spektral işlemler ve uyarlamalı tespit için çalışan, sayısal davranışı doğrulanabilen bir donanım hattı vardır.
2. Aynı PL çıktısı kart üzerinde olay işleme ve uygun parametre ölçümlerine girdi olur; kart yalnız PC’nin ürettiği sonucu göstermez.
3. Ağ üzerinden yapılandırılabilen, kimliği ve yanıt bütünlüğü denetlenebilen bir gömülü işleme bileşeni geliştirilmiştir. Ancak mevcut ürün hâlâ PC’ye bağımlıdır; bağımsız alıcı değildir.[^2][^3]

CFAR’ın sabit noktalı ve iş hatlı FPGA uygulaması yerleşik bir mühendislik yaklaşımıdır. MathWorks’ün donanım uygulama örneği de davranışsal model ile HDL sonuçlarını karşılaştırır. Bu kaynak mimari yaklaşımı destekler; oradaki CA-CFAR sonuçları bizim OS-CFAR tasarımımızın performans kanıtı değildir.[^6]

## 2. Neden 20 MS/s’yi şimdilik bırakmalıyız?

Sabit izleme alıcısı 8 MS/s, FPGA’ya giden seçilmiş alt bant 2 MS/s’dir. Geniş bant tarama yolu ise 10 MS/s kısa yakalamalar kullanır. Bunlar aynı hızın çelişkili gösterimleri değil, farklı katmanlar ve çalışma profilleridir. Arayüzde tek değer gösterilecekse fiziksel alıcının ayarı doğru seçimdir; teknik raporda işleme alt bandı ayrıca belirtilmelidir.[^1]

8’den 2’ye filtreli örnek azaltma tek başına kötü bir tasarım değildir. HackRF’nin resmî dokümanı 8 MHz altındaki doğrudan örneklemeyi önermiyor; 2 MHz hedefi için 8 MHz alım sonrasında uygun alçak geçiren filtreyle 4:1 örnek azaltmayı tarif ediyor. Bu, bizim filtrenin doğruluğunu ayrıca kanıtlamaz; fakat yaklaşımın teknik gerekçesi vardır.[^7]

20 MS/s’nin burada temel riski donanımı örnekleme ayarıyla bozmak değil, veri kaybı ve işleme yüküdür. Yerel alıcı denemesinde yaklaşık bir saniyelik üçer tekrarda 8 ve 10 MS/s için USB taşması sıfır; 20 MS/s için sırasıyla 154, 155 ve 153 taşma kaydedilmiştir. Bu, o alıcı ve USB/PC düzeninin kısa deneyidir; bütün cihazlara genellenmez. HackRF belgeleri de tek cihazın 20 MS/s’de bir USB 2.0 veri yolunun neredeyse tamamını kullandığını belirtir.[^8][^9]

İkinci sınır, alımdan sonraki işlemedir. 4096 örneklik kesintisiz, örtüşmesiz karelerde:

- 2 MS/s işleme için saniyede yaklaşık **488,28 kare** gerekir.
- 10 MS/s işleme için saniyede yaklaşık **2441,41 kare** gerekir.
- Depodaki kısa 10 MS/s kart yakalamasında yaklaşık **499–506 kare/s** görülmüştür. Kısa veriyi tamponlayıp sonradan bitirmek mümkündür; bu sürekli 10 MS/s işleme değildir.[^1][^10]

Aynı FFT boyutunda hızı artırmak frekans hücre aralığını da genişletir: 2 MS/s ve 4096 için yaklaşık 488 Hz, 10 MS/s için 2441 Hz. Bunlar frekans hatası veya gerçek çözünürlük garantisi değil, `Fs/N` hücre aralıklarıdır. Daha geniş anlık kapsama ile daha ince frekans ayrımı aynı şey değildir.

**Karar:** Mevcut 8/2 sabit izleme ve 10 MS/s kısa yakalama profillerini koruyalım. 20 MS/s’yi varsayılan yapmayalım. Bu karar 2 MS/s’nin FPGA’nın değişmez fiziksel sınırı olduğu anlamına gelmez; yakın vadede yeniden tasarım ve kabul maliyetini üstlenmemek anlamına gelir.

## 3. Tespit ile parametre çıkarımı birlikte çalışabilir mi?

### Otomatik dar aralık ölçümü

Güncel kaynakta 4096 FFT, uygun kart yeteneği, tek parametre bağlamı ve 8–512 hücrelik analiz aralığı koşullarında dört ardışık gözlem kullanılır. Tespit akışı sürer. Kart aynı karede önce tespiti, ardından parametre gözlemini yürütür. Bu, bütün hedeflerin aynı anda veya sıfır ek yükle ölçülmesi değildir.[^3]

2 MS/s’de 512 hücrelik analiz penceresi 250 kHz’e karşılık gelir. Bu sayı, her 250 kHz genişliğindeki RF sinyalinin mutlaka ölçülebileceği anlamına gelmez; kenar ve gürültü referansı gereksinimleri ayrıca vardır. Dört karenin örnek süresi 8,192 ms’dir; kuyruk, olayın doğrulanması ve taşıma dahil kullanıcı gecikmesi daha uzundur.

Burada önemli bir açık nokta vardır: 14 Eylül tarihli, 2048 karelik bir arayüz-modeli koşusunda 21 otomatik parametre sonucu ve ölçümden önce süresi dolan 1627 olay kaydı vardır. Bu sayaçlar 1627 farklı gerçek verici kaçırıldığı anlamına gelmez. Olayların yeniden oluşması, yaşam döngüsü veya sıraya alınma davranışı incelenmelidir. Bununla birlikte otomatik ölçümün her tespiti kapsadığı da söylenemez.[^11]

Bu koşu `offscreen` çalışmıştır; normal görünür arayüzün uzun süreli kabulü değildir. Yaklaşık 402 kare/s yanıt hızı ve kuyruk birikimi kısa koşuda gözlenmiştir. Tek başına bu kayıt kök nedeni ispatlamaz; sıfır USB taşması bulunması da sürekli kapasitenin yeterli olduğunu kanıtlamaz.[^11]

### Operatörün ayrıntılı ölçümü

Mevcut operatör yolu aynı olaya ait dört güncel kareyi topladıktan sonra canlı alımı iptal eder, sabitlenen veriyle kartta ölçümü tamamlar. Yeniden alım ayrı bir eylemdir. Bu davranış hata değil, mevcut çalışma sözleşmesidir; fakat operatörün tespitin sürdüğünü sanmaması gerekir. Geniş analiz aralığı için bu yol korunmuştur.[^3][^4]

13 Eylül tarihli kontrollü 820 MHz deneyinde tespit → parametre → NFM dinleme akışı kaydedilmiştir. Yani parametre çıkarımı hiç yapılmamış değildir. Ancak sayısal sonuçların iç kalite durumu geçerli olsa da kayıtta `accuracy_proven: false` vardır; bu genel RF doğruluğu kabulü değildir.[^12]

**Karar:** Tespit modülünü kaldırmayalım. Yeni tespit özelliği kapsamını daraltıp mevcut tespit–ölçüm bütünleşmesini doğrulayalım. Dar otomatik ölçümü normal izleme için, geniş/ayrıntılı operatör ölçümünü açıkça belirtilen duraklamalı yol için kullanalım. Mevcut tek-alıcılı akışta tam bant taraması ile seçilmiş başka bir frekansta kesintisiz ölçümün aynı anda yapıldığını iddia etmeyelim. Bu değerlendirme yeni fazın açıldığı anlamına gelmez.

## 4. Sinyal tespitinde hâlâ değerli iş var mı?

Evet; ancak öncelik yeni algoritma eklemek değil, mevcut sonucun güvenilirliğini artırmaktır.

**Öncelik 1 — Uçtan uca bütünlük.** Yarışmada kullanılacak aynı kaynak, imaj, alıcı, kazanç ve görünür arayüzle uzun koşu yapılmalı. USB kaybı, eksik kare, CRC/sıra hatası, aday düşmesi ve zamanla artan kuyruk gecikmesi ayrı izlenmeli. Daha büyük tampon kalıcı hız açığını çözmez; yalnız taşmanın ortaya çıkışını geciktirebilir. Hataları saklamak veya eksik veriyi başarılı sonuç saymak çözüm değildir.[^1][^11]

**Öncelik 2 — Yanlış alarm ve gerçek hedef ayrımı.** Bilinen hedef yokken, hedef varken, güçlü komşu varken ve hedef kısa süre görünürken tekrarlar yapılmalı. CFAR eşiği gürültüye uyum sağlasa da eşik katsayısı gerçek ortamda otomatik olarak belirli bir yanlış alarm oranını garanti etmez. OS-CFAR bazı çok-hedefli durumlarda yardımcı olur; her ortamda kusursuz olduğu sonucu çıkmaz. Eşik azaltma, yalnız daha çok işaret üretmesiyle değil hedef yakalama ve yanlış alarm birlikte ölçülerek değerlendirilmelidir.[^13]

**Öncelik 3 — Tespitten geçerli ölçüme ulaşma.** Yarışma açısından “hedef bulundu ama ölçülmeden kayboldu” önemli bir başarısızlıktır. Aynı hedefin tekrar tekrar yeni olay üretip üretmediğini, uygun adayın sırada bekleyip beklemediğini ve ret gerekçelerini kaydetmek gerekir. Kuyruğu büyütmeden önce 1627 süresi dolan olayın anlamı ayrıştırılmalı. Yeni zamanlayıcı ancak tekrarlanabilir bir sorun bulunursa, dar kapsamlı değişiklik ve regresyonla düşünülmeli.[^3][^11]

**Öncelik 4 — Ölçüm doğruluğu.** Merkez frekansı, bant genişliği ve güç sonuçlarını bilinen referansla karşılaştırmak gerekir. Adayın kapladığı hücre aralığı, işgal edilen bant genişliğiyle aynı şey değildir. ITU-R SM.443, işgal edilen bant genişliği ile x dB bant genişliğini ayırır; genel OBW tanımında her kenarın dışında yüzde 0,5 güç bırakılır. Bu tanımı kullanmak tek başına ITU uyumluluğu sağlamaz; ölçüm koşulları ve hata ayrıca doğrulanmalıdır.[^14]

Kalibrasyon dosyasında şu anda ölçülmüş profil yoktur. Bu nedenle dBFS değerini mutlak dBm gibi sunmamak gerekir. Benzer şekilde sınıflandırıcının yüksek güven skoru, aynı yüzdede sahada doğruluk demek değildir.[^3][^12][^15]

## 5. Bant taramasını hızlandırma konusu nasıl ele alınmalı?

45 dakikalık kullanıcı gözlemi önemlidir; ancak nedenini doğrulayan tamamlanmış tam-bant zaman dökümü olmadan bunu yalnız örnekleme hızına bağlayamayız. Mevcut geniş bant planı yaklaşık 2400 sorumluluk penceresi kullanır. Her pencerede yalnız RF dinleme yoktur: oturum açılışı, veri işleme, gerektiğinde ek aday doğrulaması ve hata tekrarları vardır.[^1][^16]

Kaydedilmiş 40 MHz/16 pencere koşusu yaklaşık 8 saniyedir. Ham kayıt 128 kare/pencere kullanır; ana aşama yaklaşık 5,608 saniye, ek doğrulamalar 1,608 saniye, ana yakalamaların toplam RF gözlem süresi yaklaşık 0,839 saniyedir. Bunlar aynı şey değildir: 5,608 saniye içinde 0,839 saniyelik gözlem de bulunur. Bu tek kısa koşunun oranını bütün banda taşımak, 20 dakikalık kaba bir örnek verir; gerçek tam bant süre garantisi değildir.[^1][^16]

Yakın vadede yapılabilecek düşük riskli iş, tarama aşamalarının mevcut tanılarını kullanarak gerçek süreyi ve hedefe dönüş aralığını ölçmektir. Pencere başına kareyi veya tekrarları körlemesine azaltmak, kısa/zayıf sinyal yakalamayı kötüleştirebilir. Profesyonel spektrum analizinde de kısa olay yakalama; FFT süresi, örtüşme ve gözlem kesintileriyle birlikte değerlendirilir. Yalnız ekrandaki hız veya MS/s sayısı yeterli değildir.[^17]

Gösterimde göreve uygun daraltılmış bant seçmek yararlı olabilir; bu, 1 MHz–6 GHz gereksinimini karşılamanın yerine geçmez. Tam bant zorunluluğu ve zaman sınırı özgün şartnameyle netleştirilmeden kapsam daraltılmış gibi kabul kaydı yazılmamalıdır.[^5]

## 6. Yarışmaya yönelik önerilen sıra

1. **Bilinen sürümü sabitle.** Çalışan imaj/hizmet, kaynak özetleri, etkin alıcı kimliği ve profili kaydedilsin. Eski kanıtın yeni ikiliye ait olduğu varsayılmasın. Bu öneri commit veya yükleme izni değildir.
2. **Uçtan uca senaryoyu tekrar et.** Sistem denetimi → aralık taraması → seçilmiş hedefte izleme → uygun parametre ölçümü → desteklenen sinyalde dinleme → durdurma/yeniden başlatma. Başlangıç için üç ardışık başarılı tekrar bir çalışma kontrolü olabilir; istatistiksel RF kabulü yerine geçmez.
3. **Gerçek gösterim yükünde dayanıklılığı ölç.** Görünür arayüz, parametre ve kayıt açıkken, planlanan gösterim süresini aşan bir koşu kullanılsın. Baş ve son kuyruk gecikmeleri karşılaştırılsın. Seri kimliği değişimi ve USB modundan çıkma toparlanması da ayrı denensin.
4. **Küçük fakat kontrollü doğruluk seti oluştur.** Hedef var/yok, zayıf hedef, güçlü komşu, sınırda hedef ve kısa süreli hedef durumları kullanılsın. Tekrarlarda operatörün hedef zamanını önceden bilmediği değerlendirme eklensin. RF üretimi yalnız mevcut onaylı kontrollü laboratuvar koşullarında yürütülsün.
5. **Yalnız kanıtlanmış engeli düzelt.** Birinci öncelik tespit–parametre geçişi ve kayıp/kuşkulu sonuç davranışıdır. Sonrasında aynı test yeniden çalıştırılsın. Yeni FFT varsayılanı, yeni DMA düzeni, iki alıcıyla paralel tarama, 20 MS/s veya kapsamlı yeniden yazma bu hazırlığın parçası olmasın.

Kayıtların asgari içeriği: gerçek hedef sayısı, yakalanan/kaçırılan hedef, yanlış olay/dakika, ilk tespit ve geçerli ölçüm gecikmesi, parametre hata değerleri, ölçüm ret gerekçeleri, aktarım ve aday kayıp sayaçları, kuyruk gecikmesinin zaman içindeki değişimi. Kabul sınırları resmî gereksinim ve üzerinde anlaşılmış gösterim senaryosundan gelmelidir; burada sayısal başarı eşiği icat edilmemiştir.

KTR izlenebilirliği açısından tespit ve kapsama KTR-4.1 / KTR-4.1-OPS-B0, parametre sonuçları KTR-4.2 / KTR-4.2-F1, ilgili dinleme akışı mevcut uçtan uca kaydın KTR-4.3 bağıyla ele alınmalıdır. Bu rapor hiçbir açık kapıyı kapatmaz veya faz geçişi onayı vermez.[^5][^12]

## 7. Sunumda kullanılabilecek dürüst anlatım

“Sistemimizde spektral işleme ve hücre düzeyindeki uyarlamalı tespit FPGA mantığında yürütülüyor. Kartın ARM işlemcileri bu çıktılardan zaman içinde takip edilen olaylar ve uygun ölçüm sonuçları üretiyor. PC alıcı verisini sağlıyor, sistemi yönetiyor ve sonuçları sunuyor. Donanımın katkısını aynı girdinin izlenebilir tespit ve parametre sonuçlarına dönüşmesiyle gösteriyoruz. Doğruladığımız profil ve koşulları, henüz doğrulamadığımız sürekli hız ve RF doğruluğu sınırlarından ayrı raporluyoruz.”

Bu anlatım için yeni bir özellik icat etmek gerekmez. Mevcut işlevin çalışan kart kimliği, ardışık kareler, olay kaydı ve kontrollü tekrarlarla gösterilmesi gerekir. “PC’den daha hızlı”, “her sinyali yakalıyor”, “tüm işlemler FPGA’da”, “10 MS/s sürekli gerçek zamanlı” veya “kalibre mutlak güç ölçüyor” ifadeleri şu an kullanılmamalıdır.

Sonuç: FPGA’yı çıkarmaya değil, yaptığı işi kanıtlamaya odaklanmak mantıklıdır. Öncelik listesi **kararlı tespit → güvenilir parametre → tekrarlanabilir gösterim** olmalıdır; daha büyük örnekleme sayısı bu listenin önüne geçmemelidir.

## Kaynaklar ve kanıt kapsamı

Yerel belgeler değişebilir. Aşağıdaki yerel deneyler yalnız kendi kayıtlı kaynak/cihaz ve koşulları için kanıttır. Dış kaynaklar 15 Eylül 2026 tarihinde incelenmiştir.

[^1]: [Güncel sinyal tespiti durumu](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/interfaces/SIGNAL_DETECTION_STATUS.md>), özellikle 15 Eylül örnekleme hızı değerlendirmesi ve açık kabul kapıları.
[^2]: [Sistem mimarisi](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/architecture/P0_SYSTEM_ARCHITECTURE.md>) ve [kart hizmeti kaynak kodu](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/platforms/embedded/p0/src/p0_ed_service.c>); görev paylaşımı ve dört yuvalı iş hattı. Kaynak incelemesi tek başına güncel fiziksel hız ölçümü değildir.
[^3]: [ARM parametre sözleşmesi](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/interfaces/P0_ARM_PARAMETER_RUNTIME_CONTRACT.md>), [canlı oturum](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/app/operator_console/live_ed.py>) ve [otomatik parametre kuyruğu](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/app/operator_console/automatic_parameter.py>); yetenek, tek bağlam ve dört kare koşulları.
[^4]: [Operatör ölçüm eylemleri](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/app/operator_console/quick_measurement_actions.py>), dört kare sonrası alım iptali ve ayrı yeniden başlatma eylemi.
[^5]: [Uygulama yol haritası](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/plans/IMPLEMENTATION_ROADMAP.md>) ve [KTR izlenebilirliği](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/requirements/KTR_TRACEABILITY.md>); özgün yarışma şartnamesinin yerine geçmez.
[^6]: MathWorks, [FPGA-Based Cell-Averaging Constant False Alarm Rate Detector](https://www.mathworks.com/help/phased/ug/fpga-based-cell-averaging-cfa.html). Donanım modeli ve davranışsal referans doğrulaması; bizim OS-CFAR tasarımımızın kabul sonucu değildir.
[^7]: Great Scott Gadgets, [Sampling Rate and Baseband Filters](https://hackrf.readthedocs.io/en/stable/sampling_rate.html). 8 MHz altındaki alımın sınırları ve filtreli 4:1 örnek azaltma örneği.
[^8]: [Yerel alıcı hız denemesi](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/results/evidence/phase08/hackrf-rx-rate-observation-20260914.json>); üçer kısa tekrar, ikincil alıcı, belirtilen USB/PC düzeni.
[^9]: Great Scott Gadgets, [Synchronization Checklist](https://hackrf.readthedocs.io/en/stable/synchronization_checklist.html), USB bant genişliği bölümü; ayrıca [HackRF One özellikleri](https://hackrf.readthedocs.io/en/stable/hackrf_one.html), desteklenen örnekleme hızları. Desteklenen azami hız uygulamanın kayıpsız çalışması garantisi değildir.
[^10]: [Kısa geniş bant kart deneyi](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/results/evidence/phase08/wideband-burst-physical-20260914.json>); kısa yakalama başarısı, sürekli 10 MS/s kabulü değil.
[^11]: [2048 karelik sabit kazanç gözlemi](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/results/evidence/phase08/fixed-frequency-stability-20260914-gain-zero.json>); `offscreen`, yaklaşık 402 kare/s, 21 otomatik sonuç ve 1627 ölçüm öncesi sona erme. Sayaçlar farklı fiziksel verici sayıları değildir.
[^12]: [820 MHz tespit–parametre–dinleme deneyi](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/results/evidence/phase08/live-820mhz-e2e-product-20260913.json>); sınırlı kontrollü RF başarısı, `accuracy_proven: false`, açık kabul kapıları ve kaynak özetleri.
[^13]: MathWorks, [Constant False-Alarm Rate Detectors](https://www.mathworks.com/help/phased/ug/constant-false-alarm-rate-cfar-detectors.html). Gürültü varsayımları, yanlış alarm doğrulaması ve OS-CFAR karşılaştırmalı örneği.
[^14]: ITU-R, [SM.443-4 — Bandwidth measurement at monitoring stations](https://www.itu.int/dms_pubrec/itu-r/rec/sm/R-REC-SM.443-4-200702-I%21%21PDF-E.pdf), Ek 1, tanım ve ölçüm koşulları. Bu referans mevcut ürünün ITU uyumluluğu beyanı değildir.
[^15]: [Alıcı kalibrasyon profilleri](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/config/p0/rx_calibration.json>); inceleme sırasında `profiles` listesi boştur.
[^16]: [Tarama uygulaması](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/app/operator_console/rx_survey.py>), [QML tarama özeti](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/results/evidence/phase08/wideband-qml-live-scan-20260914.json>) ve [ham pencere kayıtları](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/results/evidence/phase08/wideband-qml-live-scan-20260914.jsonl>); 128 kare/pencere ve sınırlı 40 MHz koşusu.
[^17]: Rohde & Schwarz, [Implementation of Real-Time Spectrum Analysis](https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/dl_application/application_notes/1ef77/1EF77_3e_Real-time_Spectrum_Analysis.pdf), bölümler 2.3–2.6. FFT güncellemesi, örtüşme ve kısa olay yakalama ilişkisi; cihazlara verilen yakalama garantileri bu projeye aktarılmaz.

## İncelenen davranışın kaynak özetleri

Aşağıdaki SHA-256 değerleri inceleme anındaki dosyaları tanımlar; çalışan donanımın bu kaynaklarla eşleştiğini iddia etmez.

```text
app/operator_console/live_ed.py
0f146a9bb005286885d4d603597a240c294fd14ad38c6d9678d08e0c169c9611

app/operator_console/automatic_parameter.py
7454ac6ef99d5ae68b0dab57b15e978ce2dc286e11ba4d863dd18f31038a89e2

app/operator_console/quick_measurement_actions.py
b5243abf696c3faec5826a93f64d916b1866a65d4b9425a961f9780ba49ec4a1

app/operator_console/rx_survey.py
a217b11b573a6ec0204e7864d330fa56616d04f865ab9fa2dc6b31d36139c40c
```
