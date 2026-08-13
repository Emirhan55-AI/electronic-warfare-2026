# ADR-0005 — Çekirdek Teknik Parametre Çıkarımı

## Durum

Kabul edildi. PHASE-04-R1 altyapısı doğrulanmış, fakat donmuş benchmark'ta 24
bant tuple'ının hiçbiri bütün bağlayıcı kapıları geçmemiştir; yeni yöntem kararı
ayrı kullanıcı onaylı PHASE-04-R2 kapsamına bırakılmıştır.

## Karar

PHASE-04 yalnız kayıtlı veya sentetik tek kanallı I/Q üzerinde spektral merkez,
gözlenmiş taşıyıcı, bant sınırları, bant genişliği, kalibre edilmemiş göreli güç,
bant içi SNR ve sınırlı `Analog / Sayısal / Belirsiz` ayrımı üretir.

Yöntemler bağımsız seçilmez. Önce iki analysis-window, üç gürültü ve dört bant
yönteminden oluşan 24 tuple, sonra seçilmiş upstream üzerinde dokuz
merkez–taşıyıcı çifti, sabit güç/SNR hesabı ve son olarak aynı upstream'i kullanan
üç sinyal alanı yöntemi değerlendirilir. Downstream başarısızlığı upstream'e dönüş
hakkı vermez ve yeni yöntem ancak ayrı kullanıcı onaylı kurtarma kararında ele alınır.

Benchmark bağımsız frame'leri elle doğrulanmış göstermez. Byte-sabit PHASE-03
profilinin gerçek `2-of-3` temporal zinciri kullanılır; yalnız o frame'de gözlenen
doğrulanmış olay parametre üretebilir. Ground truth yalnız runtime çıktıları
tamamlandıktan sonraki metrik eşleştirmesinde kullanılır.

Band-sınırlı I/Q frame-local FFT maskesiyle üretilir. Bu görünüm kesintisiz kanal
alıcısı değildir. Her frame'in ilk ve son `1152` örneği özellik hesabından çıkarılır;
frame sınırı üzerinden faz farkı alınmaz. Ham I/Q geçmişi tutulmaz. En fazla 64
olay için dört adet 32 elemanlı `float64` özellik kaydı, frame indisi ve geçerlilik
maskesinin toplamı `67.840 byte`tır.

Güç hesabı PHASE-02 `dBFS/Hz` lineer PSD normalizasyonunu tekrar ölçeklemez.
Kalibrasyon bulunmadığından sonuç dBm değildir. Nominal sentetik merkez yalnız
ground truth'tur ve Operasyon ekranına taşınmaz.

## Sonuçlar

Validated profil ancak bütün önceden sabit kapılar ile comparison/digest bağı geçerse
oluşturulur. Başarısız benchmark sonrasında eşik, sahne, ground truth veya upstream
seçim değiştirilmez. Başarısız comparison, PHASE-04 profilinin yokluğunda da
tekrarlanabilir mühendislik kanıtıdır; diskte kalmış eski profil yüklenemez.
Canlı RF, modülasyon tanıma, dinleme, FPGA ve TX bu kararın kapsamı dışındadır.

R1 sonucunda geçerli sonuç oranı, yakın hedef ayrımı ve temporal gürültü kapıları
geçilebilse de bant q95, ayrı kenar ve bölge başarı kapılarının tamamı aynı tuple'da
sağlanamamıştır. Bu sonuç downstream yöntemleri çalıştırmak veya kısmi validated
profil üretmek için kullanılmamıştır.
