# ET Tekli Görev sözleşmesi

## Durum

PHASE-10 yazılım ve iletimsiz taban bant kapısı uygulanmıştır. Fiziksel HackRF
ve kapalı RF düzeni bağlı olmadığı için fiziksel güvenlik kapısı açıktır;
donanım gönderim kabulü yapılmamıştır. PHASE-11 başlatılmamıştır.

## Kapsam

Tekli Görev, operatörün seçtiği tek bir kesintisiz RF aralığını ifade eder.
Bu aralıkta deterministik, bant sınırlı kompleks gürültü taban bandı üretilir.
Eski çevrimdışı modeldeki `single` adı tek bir ton anlamına geldiğinden bu ürün
sözleşmesinde kullanılmaz. Çoklu, baraj, süpürme, arabakış, analog aldatma ve
GNSS işlevleri bu çalışma paketinin dışındadır.

## Giriş sözleşmesi

- Alt ve üst frekans 1–6000 MHz donanım sınırları içinde ve sıralı olmalıdır.
- Tekli bant genişliği en çok 4 MHz'dir.
- Görev süresi 0,1–30 saniyedir.
- Örnekleme 8 MS/s, çıktı biçimi işaretli interleaved CI8'dir.
- Sayısal kompleks tepe 0,7'yi aşamaz; varsayılan 0,65'tir.
- Gürültü döşemesi sabit tohumla üretilir ve kanıt için yeniden üretilebilir.

Mutlak RF merkez frekansı alt ve üst sınırın orta noktasıdır. Kompleks taban
bant gürültüsü sıfır ofset çevresinde istenen bant genişliğini kaplar. Görev
dosyası tam süreye karşılık gelen örnek sayısında yazılır.

## HackRF süreç sözleşmesi

Yalnız `hackrf_transfer` çalıştırılabilir. Komut, güvenlik profilindeki ET_TX
seri kimliğine bağlanır. Frekans merkezi, 8 MS/s örnekleme, 5 MHz taban bant
filtresi, kapalı RF yükselteci, kapalı anten beslemesi, profil sınırlı TX VGA ve
sonlu örnek sayısı kullanılır. Tekrar modu ve destek dışı değerleri zorlayan mod
kullanılmaz. Dosya sonu ile örnek sayısı aynı görevi bağımsız olarak sınırlar.

Uygulama kapanması veya operatör durdurması çalışan süreci sonlandırır. Acil
durdurma süreci sonlandırır ve uygulama oturumu boyunca yeniden başlatmayı
kilitler. Süre artı beş saniyelik süreç payı aşılırsa zorunlu sonlandırma yapılır.
Süreç hata koduyla biterse görev başarı olarak gösterilmez.

## Fiziksel güvenlik kapısı

`config/p0/hackrf_et_tx.json` varsayılan olarak kapalıdır. Gönderimden önce şu
alanların tamamı geçmelidir:

- `enabled` ve fiziksel kapı onayı açık olmalıdır.
- ET_TX HackRF seri kimliği bağlı cihaza ait olmalıdır.
- Görev bandının tamamı tarihli izin listesinin içinde kalmalıdır.
- Bağlantı yalnız `CABLED_ATTENUATED` veya `RF_SHIELDED` olabilir.
- Ölçülen zayıflatma, profil alt sınırını karşılamalıdır.
- Onaylayan kişi, inceleme UTC zamanı ve gelecekteki bitiş UTC zamanı dolu olmalıdır.
- Görev süresi ve TX VGA profil üst sınırını aşmamalıdır.

Depodaki profil cihaz bağlı olmadığı ve fiziksel düzen ölçülmediği için kapalı,
seri kimliği boş ve izin listesi boştur. Bu alanlar tahminle doldurulmaz.

## Operatör akışı

Arayüz yalnız Tekli Görev'i gösterir. Operatör alt frekans, üst frekans ve süreyi
girer. `İletimsiz Doğrula`, RF çıkışı açmadan CI8 ile spektrum/OBW özetini
üretir. `Gönderimi Başlat` yalnız fiziksel profil hazırsa etkinleşir. Normal
durdurma ve ayrı acil durdurma kontrolleri bulunur.

Görev başlangıç ve bitiş kayıtları cihaz kimliği, frekanslar, bant genişliği,
süre, örnekleme, örnek sayısı, TX VGA, yardımcı güç durumları, bağlantı türü,
onaylayan kişi, durdurma nedeni, süreç kodu ve kaynak özetini
`build/operations/et-single.jsonl` dosyasına ekler.

## PHASE-10 fiziksel çıkış kapısı

Fiziksel kapının kapanması için bağlı ET_TX HackRF kimliği, kablo/zayıflatıcı
zinciri ve spektrum ölçüm cihazı kaydedilir. Aynı ayarlarda en az üç kısa koşuda
merkez frekansı, OBW %99, bant dışı ürünler, görev süresi, normal durdurma ve
acil durdurma ölçülür. USB kopması ve uygulama kapanması negatif testleri TX'in
sona erdiğini bağımsız ölçüm cihazında göstermelidir. Bu kanıt oluşmadan
PHASE-10 tamamlanmış veya PHASE-11 açılmış sayılmaz.
