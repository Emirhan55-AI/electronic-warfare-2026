# P0 ARM Parametre Çıkarım Sözleşmesi

## RF yükselteci kalibrasyon bağı — 15 Eylül 2026

Otomatik parametre kataloğu `rf_amplifier` durumunu kalibrasyon eşlemesine
ve kayıt ayrıntılarına dahil eder. Eski profilde alan yoksa yalnız AMP kapalı
olarak yorumlanır; AMP açık güç dBm'e aynı profille çevrilmez. AMP alanı açıkça
boolean olmalıdır. Manuel ölçüm arşivinde RX yapılandırması zaten aynı alanı
taşır. Yeni kalibrasyon profili veya fiziksel güç doğruluğu kabulü oluşturulmadı.

## Tespit sürerken canlı ölçüm sözleşmesi — 13 Eylül 2026

P0IQ v2 normal 48 baytlık başlığı değiştirmeden, yalnız P0CQ yetenek sorgusu
başarıyla sonuçlandığında 80 baytlık parametre başlığını kabul eder. Bu başlık
niyet/olay kimliği, 56–4039 içindeki 8–512 hücre aralığı ve ilk-kare bayrağını
CRC ile bağlar. Ağ köprüsü isteği yerel ED ABI v2'ye çevirir; hizmet aynı karede
önce PL/ARM tespitini, ardından aynı PL güç ve CI8 girdisiyle parametre gözlemini
yürütür. Tek kalıcı parametre bağlamı nedeniyle host en güçlü olaydan başlayan
sınırlı kuyruk kullanır; bu eşzamanlı ikinci ARM bağlamı iddiası değildir.

ABI v2'nin tam temporal tablosu ve isteğe bağlı 128 bayt parametre sonucu ayrı
CRC'lerle doğrulanır. Dört gözlem tamamlanmadan kesin alan yayımlanmaz; olay
sahipliği kaybı en çok iki kez yeniden denenir. Kart/köprü yeteneği doğrulanmazsa
geniş başlık gönderilmez ve tespit akışı eski sözleşmeyle devam eder. Canlı
geniş aralık için mevcut P0PM-v2 ayrı operatör ölçümü korunur.

Güç kalibrasyonu `config/p0/rx_calibration.json` içindeki ölçülmüş profillerle
açılır. Her profil `profile_id`, `receiver_serial`, `sample_rate_hz`,
`lna_gain_db`, `vga_gain_db`, `output_amplitude_scale`, alt/üst frekans,
`dbm_minus_dbfs`, `uncertainty_db`, `measured_utc` ve `valid_until_utc`
alanlarını taşımalıdır. Bilinen seviyeli kablolu/Faraday düzeninde her kazanç ve
frekans aralığı için tekrar ölçülmeden bu dosyaya profil eklenmez. Bağlam veya
süre uyuşmazsa dBFS korunur, dBm üretilmez.

## Sonuç ve kalite tanılarının arayüz bağı — 13 Eylül 2026

P0PR yanıtındaki merkez, bant kenarları, OBW, güç, SNR ve kalite alanları
değiştirilmeden görünüm modeline taşınır. Parametre ekranı ana alan durumlarını
değer yanında, `F1Quality` içindeki dört sayısal tanıyı ve dört karelik kalite
kapısını açık teknik bölümde gösterir. Ret kodları Türkçe açıklamaya çevrilir.
Bu sunum protokolü, eşikleri, PL/ARM sahipliğini veya `accuracy_proven: false`
sınırını değiştirmez.

## Güncel P0PM-v2 geniş aralık geliştirmesi — 12 Eylül 2026

Kullanıcı sayısal işlemlerin kartta kalmasını onayladı. Yeni çekirdek 56–4039
dahil indeksler içinde 8–3984 analiz hücresini destekler; iki tarafta 4 koruma
ve 32 referans hücresi korunur. Otomatik taslak adayın tamamını ve mümkünse
64 hücre kenar payını tutar; aday artık tepe çevresinde 512 hücreye kesilmez.
Onaylı aralık adayı kesiyorsa veya gürültü referansında confirmed komşu varsa
ölçüm sayısal sonuç üretilmeden reddedilir. Aday kapsamı gerçek emisyonun
tamamının fiziksel olarak doğrulandığı anlamına gelmez.

P0PM/P0PR paket boyutları ve CRC düzeni korunur. V1 istekleri en fazla 512,
v2 istekleri en fazla 3984 hücre kabul eder. Yeni hizmet tüm yanıtlarda v2
kullanır; istemci v1'i yalnız dar aralıkta kabul eder. Eski kartın geniş isteği
reddetmesinde PC sayısal geri dönüşü yoktur. Taşıyıcı çizgisi güncel batch
yanıtında ARM'dadır; Analog/Sayısal ayrı deneysel PC işlemidir.

Kalıcı ARM dizileri 4 × 4056 × (8 + 16) = 389.376 bayttır. Geçici FFT ve
yöntem çalışma alanları buna dahil değildir. Eski host F5 profilinin 65.536
bayt üst sınırı ve dondurulmuş kaynakları değiştirilmedi; kayıt P0PR sürümü,
`board-full-span-v2` kapsamı, bellek yükü ve kaynak özetlerini ayrı tutar.
3 dB referans farkı ve 7 hücre OBW zamansal kararlılık eşikleri değiştirilmedi.
PC sınıflandırması 2414 hücrelik geliştirme aralığında aynı 4 × 400 sentetik
kapıyı geçmiştir. Bu, gerçek RF sınıf doğruluğu veya ürün kabulü değildir.

Doğrulama: `python scripts/verify_p0_parameter_runtime.py --extended --wide`
49 C↔Python sayısal kontrolünü geçti. `python scripts/verify_p0_ed_service.py`
sürüm, sınır ve CRC kapılarını doğrular. Yerel RF arşivi değişmeden
`python scripts/verify_p0_wide_parameter_record.py KAYIT.zip --output YENI.json`
ile taşınabilir C'de tekrar işlenebilir; bu fiziksel PL/ARM yürütümü değildir.
Yerel sonuçlar `build/p0/parameter-wide-runtime-20260912.json` ve
`build/p0/parameter-wide-real-record-20260912.json`, ARM ikilileri
`build/p0/parameter-wide-v2-20260912/software/` içindedir. İkililer seri
konsolla kimliği doğrulanan ZedBoard'un gerçek SD `image.ub` kök dosya sistemine
işlenmiştir. Bir kontrollü yeniden başlatma sonrasında özetleri eşleşmiş ve iki
süreç otomatik açılmıştır. Altı dar kart regresyonu ve değişmemiş gerçek kayıt
üzerinde 2414 hücrelik P0PM-v2 ölçümü geçmiştir. İzlenebilir fiziksel kanıt
`results/evidence/phase08/parameter-wide-persistent-20260912.json` içindedir.
Genel RF doğruluğu ve farklı geniş bant örneklerinde OBW kabulü açıktır.

Aşağıdaki ilk sözleşme/ölçüm metni tarihsel dar aralık kapsamındadır; eski
fiziksel kanıtlar bu yeni ikiliye aktarılmaz.

## Kapsam

Bu çekirdek, kabul edilmiş `phase04f5-operator-assisted-parameters-v6` profilinin
sayısal bölümünü Zynq PS üzerinde bounded C11 olarak uygular. Otomatik aday
genişliğini hassas bant genişliği saymaz. Ölçüm yalnız operatörce onaylanan izole
analiz aralığı ve aynı doğrulanmış temporal olaya ait dört ardışık gözlemle
başlar.

ARM çıktısına alınan alanlar:

- kestirilen emisyon merkez frekansı;
- ITU-R SM.443 yaklaşımıyla alt/üst %99 işgal edilmiş bant kenarları ve OBW99;
- kalibre edilmemiş kanal gücü (`dBFS`);
- sınırlı SNR kestirimi (`dB`).

Taşıyıcı çizgisi frekansı ve Analog/Sayısal/Belirsiz sinyal alanı sınıflaması bu
çekirdeğe alınmamıştır. Bu alanlar zaman bölgesi ve model özelliklerini gerektirir;
host ürün profilinde kalır ve kart çıktısında çalışıyormuş gibi gösterilmez.

## Giriş ve yaşam döngüsü

Her gözlem 4096 kompleks `ci8` örnek, FPGA'dan gelen 4096 adet shifted
`UQ28.30` güç hücresi, örnekleme hızı, tuner merkez frekansı, ölçüm niyeti,
temporal olay kimliği ve dahil alt/üst bin taşır. Aralık 8–512 bindir; iki yanında
32 referans hücresi ve 4 bin koruma aralığı bulunmalıdır.

İlk istekte başlangıç bayrağı zorunludur. Sonraki üç gözlemde niyet, olay,
örnekleme hızı, merkez frekans, analiz aralığı ve ardışık `uint32` frame kimliği
değişemez. Olay her karede doğrulanmış ve gözlenmiş olmalıdır. Bu koşullardan biri
kaybolursa birikim temizlenir ve bütün alanlar `CONTEXT_LOST` nedeniyle yetersiz
kalite olarak döner.

## Sayısal yöntem

Hann güç spektrumu FPGA'nın `UQ28.30` çıktısından fiziksel bin aralığına göre
normalize edilir. İki referans bölgesi ayrı ortalanır; aralarındaki fark 3 dB'yi
aşarsa ölçüm reddedilir. Gürültü çıkarılmış pozitif spektral güç, emisyon merkezi
ve leave-one-frame-out merkez belirsizliğini üretir.

OBW99, dört karenin gürültü çıkarılmış ortalamasında iki taraflı `%0,75` kuyruk,
`0,375` bin simetrik kenar düzeltmesi ve en fazla `7` bin leave-one-frame-out
zamansal değişimle hesaplanır. 100 bin ve üzerindeki analiz aralıklarında geniş
span geri kazanımı için `ci8` örneklerden dikdörtgen pencereli 4096 nokta FFT
kullanılır. Kanal gücü onaylı aralıktaki signed excess integralinden, SNR ise
gürültü ve spektral ikinci momentten üretilir.

## Kaynak ve fail-closed sınırları

Kalıcı heap yükü 56.064 bayttır ve 65.536 bayt ürün sınırını aşmaz. Geniş aralık
FFT çalışma belleği yalnız ilgili gözlem süresince ayrılır ve serbest bırakılır.
Geçersiz boyut, taşmış FPGA güç kodu veya bellek hatası sayısal sonuç yayımlamaz.
Yalnız gürültü, referans gücü/farkı, yetersiz excess, kenar clipping veya zamansal
kararsızlık durumlarında her alan kendi durum ve neden koduyla kapanır.

Bu sözleşme dBm doğruluğu, canlı RF doğruluğu, taşıyıcı çizgisi, sinyal alanı
sınıflaması veya sustained throughput iddiası oluşturmaz. Bu iddialar ayrı ve
tekrarlanabilir kart/saha kabulü gerektirir.

## Fiziksel kabul sınırı

ZedBoard üzerinde deterministik bir AM dizisi; olay edinimi ve ardından dört
ardışık ölçüm gözlemiyle fiziksel PL FFT/güç, DMA, ayrıcalıklı yerel hizmet ve ARM
çekirdeğinden geçirilmiştir. Dördüncü gözlemde altı sayısal alanın tamamı geçerli
olmuştur. Karttan alınan dört `UQ28.30` güç karesi host C çekirdeğinde tekrar
işlendiğinde ARM hizmetiyle altı alanda sıfır sayısal fark elde edilmiştir.

İdeal NumPy FFT ile fiziksel AMD FFT arasında en büyük frekans-alanı farkı
`0,0360532403 Hz`, en büyük dB-alanı farkı `0,0000344859 dB` olarak yalnız
karakterizasyon amacıyla kaydedilmiştir. Çalıştırmadan önce fiziksel ideal-FFT
eşdeğerlik toleransı tanımlanmadığı için bu farklara sonradan pass/fail eşiği
atanmamıştır. Kanıt tek deterministik AM dizisiyle sınırlıdır; geniş bant fiziksel
kapsama, canlı RF, kalibrasyon ve sürekli throughput sonucu değildir.
