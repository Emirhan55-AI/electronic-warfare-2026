# HackRF için alıcı, tespit ve dinleme ayarları önerisi

## Önerinin özeti

LNA ve VGA ana ekrandaki yerlerinde kalmalıdır. Mevcut ayarlar penceresi kaldırılmamalı; fiziksel alıcı, FPGA tespiti, ses işleme ve görüntü kontrolleri birbirinden ayrılmalıdır. Bias-T ve harici donanım seçimleri, malzeme bilgileri gelene kadar ertelenmelidir.

En yararlı eklemeler yalnız AMP değildir: dinleme kanal genişliğinin seçimli sunulması, ince frekans ayarı, mevcut NFM ses düzeltmesinin görünür hâle getirilmesi, sınırlandırılmış CFAR kontrolleri, alıcı analog filtre yönetimi ve gerektiğinde cihaz bazlı frekans düzeltmesi önemlidir. Bunların hepsi aynı olgunlukta değildir. Bazıları mevcut sayısal işlemin arayüze bağlanması, bazıları ise yeni DSP geliştirmesi ve fiziksel doğrulama gerektirir.

HackRF One, çok sayıda bağımsız “hassasiyet artırma” düğmesine sahip değildir. SDR uygulamalarındaki birçok seçenek alıcı donanımına değil, bilgisayarda yapılan kanal ve ses işlemlerine aittir. Daha fazla kazanç, daha temiz ses ve daha güvenilir tespit farklı hedeflerdir; tek bir “zayıf sinyal modu” altında gizlice birlikte değiştirilmemelidir.[^1][^2]

Bu öneri 15 Eylül 2026 tarihli kaynak incelemesine dayanır. Yerel `hackrf_transfer -h` çıktısında AMP, analog filtre, PPM, örnekleme, IF/LO ve tetikleme seçenekleri doğrulanmıştır; fiziksel alım başlatılmamıştır. Güncel üretim kodu veya kart imajı değiştirilmemiştir. Önerilen yeni seçenekler uygulanmış özellikler değildir.

## 1. HackRF donanımında bulunan seçenekler

### RF yükselteci — AMP

AMP aç/kapa kontrolüdür; LNA/VGA gibi ince kademeli değildir. Zayıf alımda yararlı olabilir, güçlü ortamda bozulmayı artırabilir. Alıcı yolu AMP’yi destekleyen altyapıyı kullanıyor ancak canlı oturum yapılandırması bugün açıkça kapalı seçiyor. Dolayısıyla kullanıcı kontrolü eklemek için tüm alıcı altyapısının yeniden yazılması gerekmez.[^1][^3]

Önerilen sunum: **RF yükselteci: Kapalı / Açık**. Başlangıç kapalı; açıklama “Zayıf alımda yardımcı olabilir; güçlü sinyallerde bozulmaya neden olabilir.” LNA ve VGA ile aynı anda otomatik değiştirilmemeli. Harici LNA kullanıldığında AMP açmanın faydası ayrıca karşılaştırılmalı.

### Alıcının analog taban bant filtresi

AMP dışındaki en önemli gerçek donanım kontrolü budur. ADC’ye ulaşan bant dışı bileşenleri azaltmaya yardımcı olabilir; sayısallaştırma sonrası dar kanal filtresiyle aynı değildir. Ancak daha önceki RF katlarında oluşan aşırı yüklenmeyi mutlaka gidermez ve harici RF ön-seçici filtrenin yerini tutmaz.

HackRF ayrık filtre genişliklerini destekler. Yerel araçta 1,75; 2,5; 3,5; 5; 5,5; 6; 7; 8; 9; 10; 12; 14; 15; 20; 24; 28 MHz listelenir. Bu listenin tamamı her örnekleme profilinde kullanıma açılmamalıdır. Örnekleme ayarı filtre varsayılanını yeniden kurar; özel filtre komutu daha sonra uygulanmalıdır.[^2]

Mevcut sistem hedefi fiziksel ayar merkezinden normalde 1,5 MHz uzak tutar. Örneğin hedefin iki yanında 0,7 MHz korunacaksa, hedef bölgesinin dış kenarı donanım merkezinden 2,2 MHz uzaktadır. Dolayısıyla yalnız “tespit bandı 1,4 MHz; filtreyi 1,75 MHz yapalım” yaklaşımı hedefi kesebilir. Nominal simetrik genişlik için 4,4 MHz bile yalnız geometrik alt sınırdır; gerçek filtrenin geçiş bölgesi ve zayıflatması ek pay gerektirir. Kodun bazı yollarında ofset değişebildiğinden sabit bir uygun filtre listesi yeterli değildir.[^3]

Önerilen sunum: **Alıcı filtresi: Profile uygun / Gelişmiş seçim**. İlk sürümde profile uygun seçim korunmalı ve uygulanan komut değeri gösterilmelidir. Elle seçilebilen değerler ancak hedefin tamamını ve gerekli payı kapsama testinden geçtikten sonra açılmalıdır. Filtreyi daraltmak USB örnek sayısını veya FPGA kare hızını azaltmaz; örnekleme hızı değişmiyorsa taşıma yükü devam eder.

### Frekans düzeltmesi — PPM

Yerel araç `-C` ile iç referans hatası düzeltmesini destekliyor. Bu, gerçek bir frekans sapması varsa hedefi daha doğru konumlandırmaya yardımcı olur; RF kazancı değildir. Örneğin 1 ppm, 100 MHz’te 100 Hz; 1 GHz’te 1000 Hz ölçeğindedir. Düzeltmenin işareti ve uygulanma yolu bilinen referansla doğrulanmalıdır.[^4]

Önerilen sunum: **Gelişmiş → Frekans kalibrasyonu**, başlangıç “Kalibre edilmedi / düzeltme yok”. İki HackRF’nin düzeltmesi cihaz seri kimliğine ayrı bağlanmalıdır. Veri etiketleri, donanım ayarı ve ölçüm frekansları tutarlı değişmelidir; yalnız grafiğin etiketini kaydırmak doğru değildir. Referans olmadan rastgele bir PPM değeri önermektense bu özellik ikinci öncelikte tutulmalıdır.

### Merkez çizgisinden kaçınma — ofsetli ayar

HackRF belgeleri hedefi DC bileşeninden uzağa taşıyan ofsetli ayarı önerir. DC düzeltmesi görüntüyü temizlese de merkeze yakın gerçek sinyalleri etkileyebilir. Mevcut uygulamada ofsetli ayar zaten vardır; yeniden keşfedilmiş bir yeni özellik gibi sunulmamalıdır.[^5][^3]

Önerilen sunum: “Merkez parazitinden kaçınma: Sistem tarafından yönetiliyor” bilgisi yeterlidir. Ofseti veya geniş bir merkez çentiğini serbest kullanıcı kontrolü yapmak yakın vadede önerilmez. Dinleme ince ayarı bu donanım ofsetinden ayrı tutulmalıdır.

### Örnekleme, saat, tetik ve düşük seviyeli ayarlar

Örnekleme seçimi kapsama, USB yükü ve bütün işleme sözleşmesini etkiler. Mevcut 8 MS/s sabit alım / 2 MS/s işleme ve 10 MS/s kısa tarama profilleri korunmalıdır; 20 MS/s bir hassasiyet seçeneği olarak açılmamalıdır.[^6]

Harici saat ve tetikleme, zaman/frekans referansı veya eşzamanlama içindir; tek başına zayıf sinyal yükseltmez. IF/LO ve RF yol filtresi gibi düşük seviyeli kontroller de bulunur, fakat varsayılan ayarlama mekanizmasının yerine operatöre sunulmaları önerilmez. Opera Cake anten anahtarlama kontrolleri ek donanım gerektirir. Bunlar, hata sınırlarını gevşetme ve kayıtçı belleği büyütme seçenekleriyle birlikte günlük alıcı ayarları menüsünün dışında tutulmalıdır.[^2][^4]

## 2. Daha anlaşılır dinleme için gerekenler

### Önce doğru dinleme türü

Kaynakta desteklenen modlar AM ve NFM’dir. WFM, USB/LSB ve sayısal ses çözücüleri mevcutmuş gibi gösterilmemelidir. Dinleme modeli 200 kHz’e kadar kanal genişliğini kabul etse de bu, doğru WFM demodülasyonu ve ses filtresi uygulandığı anlamına gelmez.[^7]

Özellikle yayın FM’i dinlenecekse WFM ayrı bir gereksinimdir. GNU Radio referansı NFM ve WFM’de farklı sapma ve ses bantları kullanır. Bizim sürekli kayıt yolumuzdaki yaklaşık 2,55/3 kHz ses filtresiyle yayın FM’inin geniş ses bandı aynı değildir. WFM isteniyorsa ayrı geliştirme ve kabul işi olarak ele alınmalı; yalnız menüye “WFM” yazılmamalıdır.[^8][^9]

### Kanal bant genişliği

Seçilmiş sinyalin çevresinden ne kadar alanın dinlemeye alınacağını belirler. Gereksiz genişlik komşu sinyal ve gürültüyü içeri alabilir; aşırı daraltma istenen sinyali bozar. Bu bir yazılımsal kanal filtresidir; FPGA’nın taradığı bütün bandı değiştirmemelidir.

Mevcut sayısal aralık 2 kHz ile `min(200 kHz, kaynak örnekleme hızı)` arasındadır. Önerilen arayüz taslağı AM için 6/9/12 kHz, NFM için 8/12,5/16/25 kHz ve “Özel” seçeneğidir. Bunlar kullanışlı başlangıç adaylarıdır, tüm yayınlar için doğrulanmış optimum değerler değildir. Kanal aralığı ile gerçek işgal edilen bant genişliği de aynı şey değildir. Mevcut filtrelerin bu seçimlerdeki ses/komşu kanal davranışı test edilmelidir.[^7][^9]

### İnce frekans ayarı

Dinleme merkezi ofseti zaten yapılandırmada vardır. Küçük artı/eksi düğmeleri ve “Seçilen hedefe dön” eylemi, serbest metin girişinden daha anlaşılır olabilir. Adım büyüklüğü ve izinli toplam kaydırma, mod ve yakalanmış bandın sınırına göre belirlenmelidir. Bu ayar yalnız dinleme kanalını kaydırmalı; tespit edilen frekans kaydını veya cihaz kalibrasyonunu değiştirmemelidir.[^7]

### NFM ses düzeltmesi — de-emphasis

Mevcut modelde `nfm_deemphasis_us` vardır; varsayılan 750 µs, kabul edilen aralık 0–2000 µs’dir. Sürekli kayıt işleme yolu bunu kullanır. Kısa önizleme yoluyla aynı davranışın sağlandığı ayrıca kontrol edilmelidir. Bu değer RF hassasiyetini değil, demodüle edilmiş sesin frekans dengesini etkiler.[^7][^9]

Önerilen sunum “NFM ses düzeltmesi: Mevcut profil / Kapalı / Gelişmiş”tir. Başlangıçta mevcut 750 µs korunmalı; farklı yayın türlerine ait 50/75 µs değerleri bütün NFM için doğruymuş gibi dayatılmamalıdır. Açıklama “Yayının ses ön-vurgusuna uygun düzeltme” olmalıdır. Ses kayıtlarıyla karşılaştırma yapılmadan “daha net” etiketi kullanılmamalıdır.[^8]

### Ses susturma — squelch

Sinyal yokken veya düzey eşik altındayken sesi susturur; zayıf sinyali güçlendirmez. Fazla yüksek eşik duyulabilir zayıf sinyali tamamen susturabilir. Mevcut dinleme çekirdeğinde ayrı kullanıcı susturma mekanizması görülmemiştir; bu yeni geliştirmedir.[^10][^9]

Önerilen ileriki kontrol: “Susturma: Kapalı / Ayarlı”, başlangıç kapalı. Mutlak dBm yerine açıkça tanımlanmış kanal gücü ölçeği kullanılmalı; açık/kapalı geçişinde kısa bekleme ve farklı açma-kapama eşikleri düşünülmelidir. Susturma yalnız ses çıkışını etkilemeli, FPGA tespitini ve kanıt kaydını durdurmamalıdır. Ses zaman çizgisi kesilmemeli; sessiz örnekler süreyi korumalıdır.

### Ses filtresi, ses AGC’si ve gürültü azaltma

Konuşma ses filtresi yararlı bir sonraki geliştirme olabilir; mevcut 2,55/3 kHz davranışı açıkça belgelenmeli. Ses otomatik seviyeleme, RF otomatik kazancından farklıdır. Mevcut sonlu kayıt yolunda bütün ses tek tepeye göre normalize edilir; bunu kesintisiz, uyarlamalı bir ses AGC’si diye adlandırmak doğru değildir.[^9]

Yakın vadede yeni RF AGC önerilmez; kaldırılmış otomatik alıcı kazancı başka isimle geri getirilmemelidir. Gürültü azaltma, noise blanker ve ses notch filtreleri de “bedava hassasiyet” değildir. Konuşma ayrıntılarını veya darbeli gerçek olayları bastırabilecekleri için ayrı, yalnız ses dalında ve varsayılan kapalı deneyler olarak kalmalıdır. Ölçüm I/Q’suna sessizce uygulanmamalıdır.

## 3. CFAR kontrollerinin doğru sunumu

Mevcut kart protokolünde normal katsayı 1 dahil 16 hariç; zayıf katsayı 1 dahil 4 hariç aralığındadır. Zayıf katsayı normalden büyük olamaz. Varsayılanlar normal yaklaşık 8,5801430407 ve zayıf yaklaşık 3,9810717055’tir. Bunlar hassasiyet yüzdesi değildir. Protokolün kabul ettiği aralık, her değerin RF açısından uygun olduğu anlamına gelmez.[^11]

Katsayı azalınca ilgili hücre eşiği düşer; aynı girdide eşik geçen hücre sayısı artabilir. Nihai olay başarısı ise komşular, zamansal doğrulama ve kapasite sınırlarından etkilenir. Daha çok aday üretmek doğrudan daha iyi tespit demek değildir. CFAR’ın yanlış alarm davranışı gürültü varsayımlarıyla birlikte değerlendirilmelidir.[^12]

İlk sürümde **Kart varsayılanı / Özel** önerilir. Özel bölümde sınırlandırılmış artı/eksi kontrolü ve isteğe bağlı yazma olmalıdır. Varsayılanın tam sabit noktalı değeri korunmalı; kısa gösterilen 8,58 ve 3,98 sayıları kaydetme sırasında özgün değerin yerine kendiliğinden geçmemelidir. Taslak değişiklik ile karttan doğrulanan değer ayrı gösterilmelidir.

“Daha hassas” ve “Daha seçici” profilleri ancak karşılaştırmalı testten sonra eklenmelidir. Özellikle zayıf eşik varsayılanı 4 üst sınırına çok yakındır; “yoğun ortam” profilinde bunu 5 veya 6 yapmak mevcut protokolde mümkün değildir. Dolayısıyla her iki katsayıyı birlikte artıran basit bir profil tasarımı yanlış olur.

Pencere türü, OS-CFAR rank/koruma/referans hücreleri ve zamansal doğrulama eşikleri bugün serbest kullanıcı ayarları değildir. Bunları açmak ayrı algoritma, RTL ve kabul değişikliğidir. Görüntü FFT’si ile tespit FFT’si de ayrı kalmalıdır. Tespit FFT’sinde 4096/8192/16384 seçenekleri bulunsa da mevcut belgeler küçültmede kart yeniden başlatma sınırı bildiriyor; otomatik parametre yolu 4096 gerektiriyor. Bu nedenle yarışma profilinde 4096 korunmalı, diğerleri kısıtları açıklanan gelişmiş seçim olmalıdır.[^13]

## 4. Pencere düzeni ve kullanım kuralları

Ana ekrandaki LNA ve VGA taşınmaz veya ikinci kez kopyalanmaz. Mevcut ayarlar penceresinde aşağıdaki açılır-kapanır bölümler önerilir:

1. **Alıcı:** AMP, profile uygun analog filtre bilgisi; gelişmişte uyumlu filtre seçimi ve sonradan kalibrasyon. Bias-T şimdilik yer almaz.
2. **Sinyal tespiti:** Kart varsayılanı/özel CFAR, doğrulanınca hazır profiller; gelişmişte tespit FFT’si ve uyumluluk uyarıları.
3. **Dinleme:** Mevcut AM/NFM, kanal genişliği seçimleri, ince ayar, NFM ses düzeltmesi; yeni susturma ancak uygulandıktan sonra. Mevcut dinleme ekranı aynı ayar modelini paylaşır.
4. **Görüntü:** Görüntü FFT’si, yenileme, seviye aralığı, tepeyi tut ve varsayılana dön. Görüntü yumuşatma eklenirse tespit iyileştirmesi olarak adlandırılmaz.

Her bölüm kendi varsayılanına döner. Ses düzeyini sıfırlamak alıcı kazancını değiştirmez; görüntüyü sıfırlamak CFAR’ı değiştirmez. Henüz uygulanmamış seçenekler etkin düğme olarak gösterilmez. Yeni algoritmaların prototipleri üretim menüsünü doldurmaz.

Alıcı ve CFAR değişiklikleri taslakta tutulmalı, “Uygula” ile kontrollü oturum geçişinde etkinleşmelidir. Ayar değişikliği eski olay ve ölçümleri yeni profile aitmiş gibi göstermemelidir. Profil kuşağı, alıcı seri kimliği ve kullanılan filtre/kazanç/de-emphasis değerleri kayda bağlanmalıdır. Kalibrasyon cihaz değişiminde taşınmamalıdır.

Kart profilinin gerçek geri okuması ile HackRF’ye komutun başarılı gönderilmesi farklı kanıtlardır. Donanım geri okuması bulunmayan ayara “ölçülerek doğrulandı” denmemeli. Desteklenen komutun bulunması da bütün alım yollarında uygulanmış olduğu anlamına gelmez. Sabit izleme, bant tarama, aday doğrulama ve dinlemenin aynı alıcı tercihlerini taşıdığı test edilmelidir.

## 5. İş sırası ve kabul ölçütleri

**İlk paket — mevcut kontrolleri tamamlamak.** LNA/VGA yerini koruyarak AMP’yi bağlamak; dinleme genişliğini seçimli yapmak; ince ayarı sadeleştirmek; mevcut NFM düzeltmesini tutarlı bağlamak; CFAR girişini sınırlandırmak. Bunlar için komut üretimi ve gerçek QML testleri gerekir. Mevcut değerler değişmeden aynı kayıt aynı sonucu üretmelidir.

**İkinci paket — alıcı filtresini güvenilir yönetmek.** Sabit ve tarama profillerinde hedef destek aralığı, donanım ofseti ve filtre geçiş payı birlikte denetlenmelidir. Merkezde, kenarda, zayıf hedefte ve güçlü komşuyla fiziksel karşılaştırma yapılmalıdır. Bu ölçümlerden önce rastgele MHz listesi sunulmamalıdır.

**Üçüncü paket — CFAR hazır profilleri.** Aynı ham kayıt setinde varsayılan ve aday katsayılar karşılaştırılmalı; hedef kaçırma, yanlış olay, aday düşmesi ve ölçüme ulaşan olay oranı birlikte raporlanmalıdır. Kazanç sabit tutulmalıdır. Ardından seçilen profil gerçek kartta tekrar edilmelidir. Evrensel başarı iddiası kurulmaz.

**Dördüncü paket — gerçek ihtiyaca göre dinleme geliştirmesi.** Hedef WFM ise WFM, sessiz aralıklarda gürültü rahatsız ediyorsa susturma, ses spektrumu uygunsuzsa ses filtresi öncelik kazanır. Bu özellikler ayrı talep ve ilgili yol haritası kapsamıyla uygulanmalıdır; hepsi tek seferde eklenmemelidir.

**Son kontrol — birleşik uzun koşu.** Seçilen ayarlarla gerçek arayüz, tespit ve parametre akışı birlikte denenmelidir. USB/sıra kaybı, kırpılma, aday kapasitesi, kuyruk gecikmesi ve parametre başarısızlıkları saklanmamalıdır. Bir alıcı iyileştirmesi bu hataları çözmüş sayılmaz.

Mevcut PHASE-08/ST-06 kabulü bu öneriyle kapanmaz. Alıcı ve CFAR değişiklikleri KTR-4.1 / KTR-4.1-OPS-B0, ölçüm bağlamının korunması KTR-4.2 / KTR-4.2-F1 ile ilişkilendirilmelidir. Dinleme değişiklikleri kendi mevcut gereksinim ve test bağlarıyla ele alınmalı; yeni faz açık onay olmadan başlatılmamalıdır.[^6]

## Kaynaklar

Birincil dış kaynaklar 15 Eylül 2026 tarihinde incelenmiştir. `main` kaynakları değişebilir; yerel cihazın her yeni API’yi desteklediği varsayılmamıştır. Aşağıdaki yerel dosyalar kaynak davranışını gösterir, yeni fiziksel kabul kanıtı değildir.

[^1]: Great Scott Gadgets, [Setting Gain Controls for RX](https://hackrf.readthedocs.io/en/latest/setting_gain.html). Fiziksel kazanç kademeleri ve aşırı kazanç etkileri.
[^2]: Great Scott Gadgets, [libhackrf API — hackrf.h](https://raw.githubusercontent.com/greatscottgadgets/hackrf/main/host/libhackrf/src/hackrf.h), yapılandırma, analog filtre, saat ve ek donanım bölümleri. Donanım kontrol envanteri.
[^3]: [Canlı alıcı yapılandırması](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/app/operator_console/live_ed.py>) ve [alım komutu üretimi](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/platforms/acquisition/continuous.py>). Sabit AMP kapalı seçimi ve fiziksel ayar ofseti.
[^4]: Great Scott Gadgets, [hackrf_transfer kaynak kodu](https://raw.githubusercontent.com/greatscottgadgets/hackrf/main/host/hackrf-tools/src/hackrf_transfer.c); ayrıca yerel `C:/msys64/ucrt64/bin/hackrf_transfer.exe -h` salt okunur yardım çıktısı. `-b`, `-C`, IF/LO ve tetik seçenekleri.
[^5]: Great Scott Gadgets, [Troubleshooting — DC offset](https://hackrf.readthedocs.io/en/latest/troubleshooting.html). Ofsetli ayar ve yazılımsal düzeltmenin sınırları.
[^6]: [Güncel durum](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/interfaces/SIGNAL_DETECTION_STATUS.md>), [sistem mimarisi](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/architecture/P0_SYSTEM_ARCHITECTURE.md>), [yol haritası](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/plans/IMPLEMENTATION_ROADMAP.md>) ve [KTR izlenebilirliği](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/requirements/KTR_TRACEABILITY.md>). Profil ve kabul sınırları.
[^7]: [Analog dinleme modeli](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/algorithms/monitoring/models.py>) ve [dinleme eylemleri](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/app/operator_console/quick_listening_actions.py>). AM/NFM, kanal genişliği ve de-emphasis aralıkları.
[^8]: GNU Radio, [FM demodülatör referans uygulaması](https://raw.githubusercontent.com/gnuradio/gnuradio/main/gr-analog/python/analog/fm_demod.py). Kanal, ses filtresi, de-emphasis ve NFM/WFM ayrımı; projede bu kütüphanenin kullanıldığı iddia edilmez.
[^9]: [Yerel dinleme DSP uygulaması](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/algorithms/monitoring/dsp.py>). Kanal filtreleme, kısa/sürekli yol farkı, 750 µs yapılandırması ve sonlu kayıt normalizasyonu.
[^10]: GNU Radio, [Power squelch sözleşmesi](https://raw.githubusercontent.com/gnuradio/gnuradio/main/gr-analog/include/gnuradio/analog/pwr_squelch_cc.h). Eşik altı sesi susturma ve geçiş parametreleri; mevcut projede uygulanmış özellik değildir.
[^11]: [Kart tespit profili](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/algorithms/p0/detection_config.py>) ve [mevcut ayarlar penceresi](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/app/operator_console/qml/DetectionSettings.qml>). Gerçek katsayı sınırları, varsayılanlar ve arayüz.
[^12]: MathWorks, [Constant False-Alarm Rate Detectors](https://www.mathworks.com/help/phased/ug/constant-false-alarm-rate-cfar-detectors.html). Eşik, gürültü varsayımları ve yanlış alarm değerlendirmesi.
[^13]: [Tespit ayarları kılavuzu](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/interfaces/DETECTION_TUNING_AND_SOURCE_GUIDE.md>) ve [ARM parametre sözleşmesi](<C:/Users/emirhan55/OneDrive/Documents/ChatGPT/TEKNOFEST/docs/interfaces/P0_ARM_PARAMETER_RUNTIME_CONTRACT.md>). FFT küçültme sınırı, sabit algoritma parametreleri ve otomatik ölçüm uyumluluğu. Kılavuzdaki tarihsel tarama süreleri güncel 10 MS/s profile taşınmamıştır.
