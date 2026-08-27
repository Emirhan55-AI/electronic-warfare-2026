# P0 ARM Parametre Çıkarım Sözleşmesi

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
