# PHASE-04-E1 Operatör Destekli Parametre Sözleşmesi

## P0PM-v1 kart ölçüm sözleşmesi — 11 Eylül 2026

HackRF canlı yolunda onaylanmış dört 4096 örnekli CI8 kare, alım durduktan sonra
tek CRC bağlı istekle karta gönderilir. FPGA profili ölçümün başında/sonunda
4096 ve aynı kuşak olmalıdır. PL dört kare için Hann→FFT→güç üretir; ARM ilk üç
teknik parametreyi hesaplar. Yanıt ölçüm/olay/kare kimliği, giriş CRC'si, profil
kuşağı ve hesap süresini taşır. Herhangi bir uyuşmazlık sonucu geçersiz kılar.

Taşıyıcı yalnız çizgi belirginliği, üç hücrelik enerji payı, dört kare asgari
belirginliği ve bant sınırlı artifakt kapıları geçtiğinde geçerlidir. Aksi halde
`gözlenmedi` olur. Emisyon merkezi taşıyıcı yerine kullanılmaz. Güç dBFS'dir;
dBm sadece bağlam özeti, ölçülmüş aralık, süre ve belirsizlik denetlenen fiziksel
kalibrasyonla açılabilir. Güncel ürün profilinde bu kalibrasyon yoktur.

Bu yol PetaLinux açılış imajına alınmış ve iki yeniden başlatmada otomatik
başlangıçla doğrulanmıştır. Ölçüm yalnız FPGA profili 4096 iken çalışır. FFT
8192 veya 16384'e çıkarılmışsa parametre ölçümünden önce kart yeniden
başlatılarak 4096'a dönülür; çalışma sırasında küçültme sürücüde reddedilir.

## Bant taraması seçim köprüsü — 10 Eylül 2026

Bant taramasındaki seçili frekans, parametre ekranına geçmiş kayıt olarak
aktarılmaz. `Parametre Çıkarımına Git` önce aynı kazançlarla sabit alımı açar.
Yalnız hedef frekans aralığıyla eşleşen güncel `confirmed` gözlem seçilir; canlı
dört karelik ölçüm penceresi hazır olduğunda Parametre görünümü açılır. Hedef
yeniden görülmezse seçim hazır sayılmaz ve ölçüm başlatılamaz.

## PÇ-01 güncel ölçüm ve sunum sözleşmesi — 7 Eylül 2026

- Ana görünüm dört zorunlu alanı gösterir. Emisyon merkezi taşıyıcı alanına
  aktarılmaz; OBW99 ve dBFS birimleri görünür kalır. Yetersiz kalite durumları
  sayısal sonuca çevrilmez. Dokuz alanın kaynak modeli korunur.
- `current_measurement_window`, ölçüm kilidi altında son işlenen yanıta kadar
  ardışık dört gözlem döndürür. Olay kaybolursa veya sıra kesilirse yeni dört
  gözlem gerekir. Görünüm için saklanan `measurement_window` yeni ölçümde
  kullanılmaz. İşlem düğmesi de güncel seçili gözlem ister.
- Düğmeye basılınca bu değişmez pencere sabitlenir ve RX durdurulur. Pencere
  seçimi ile RX'nin tamamen kapanması arasındaki yeni kareler bu kayda eklenmez.
- Yeni alım aynı merkez ve son LNA/VGA ayarlarını kullanır; önceki sonuç,
  seçili olay ve aralık onayı temizlenir. Eski tarama satırı geçmiş olarak
  kalabilir; operatör yeni oturumda doğrulanmış gözlemi yeniden seçer.
  Bu, oturumlar arasında aynı fiziksel vericinin otomatik kimlik eşlemesi değildir.
- İptal RX kapanırken bekleyen ölçümü kaldırır. Hesaplama başladıysa sınırlı
  çalışan güvenle biter; nesil bağı geçersizleştiğinden geç sonucu yayımlanmaz.
  Başlamış çalışan bir ZIP bırakabilir; bu iptal edilmiş ölçümün UI sonucu değildir.
- Ayrıntıdaki UTC hesaplama bitişidir, donanım alım zamanı değildir. Süre
  kayda yazılan örnek sayısı/örnekleme oranından gelir. Kayıt yolu yalnız sonuç
  görünürken sunulur. Geçersiz yeni aralık önceki onayı iptal eder.
- Kanıt: `results/evidence/phase08/parameter-workflow-v1.json` ve ZIP;
  eski `parameter-record-v1` arşivi yeniden yazılmaz. Yazılım akışı kabulü
  donanım, RF doğruluğu, standart uyumluluğu veya dBm kabulü değildir.

## PÇ-00: F5 ürün ölçüm kaydı — 7 Eylül 2026

Bu bölüm KTR-4.2 / KTR-4.2-F1 güncel QML/F5 kayıt katmanını tanımlar;
aşağıdaki tarihsel E1 matematiğini veya kilitli F5 yöntemini değiştirmez.
Canlı ve SigMF ölçümleri `parameter-measurement-v1` kaydı oluşturulmadan
ürün sonucu yayımlamaz. Kayıt yalnız açık ölçüm komutunda ve ölçüm işçisinde
üretilir; tespit karelerinin sürekli disk yazımı değildir.

Her ZIP iki girdi taşır: UTF-8 `measurement.json` ve `iq.cf64_le`.
İkincisi kestirimciye verilen dört adet 4096 kompleks örneğin küçük uçlu,
normalize kompleks float64 baytlarıdır: tam 262.144 bayt. Bu ham USB kaydı
veya volt cinsinden RF ölçümü değildir. Büyük kaynak kaydın tamamı okunmaz
ve hash'lenmez. JSON en fazla 131.072 bayttır; arşiv okuyucu sıkıştırılmış
ve açılmış boyut sınırlarını dosya çıkarmadan denetler.

Kayıt içeriği:

- ölçüm UUID'si, uygulama oturumu/nesli, olay ve aralık revizyonu;
- kullanılan kare indisleri, canlı yolda kart kare/sıra kimlikleri, aynı
  olayın dört gözlemi ve karta gönderilen CI8 baytlarının SHA-256 özetleri;
- normalize I/Q'nun toplam ve kare bazlı SHA-256 özeti, örnekleme/merkez
  frekansı, gerçek kullanılan spektrum yapılandırması ve `4×4096/fs` süre;
- sekiz ham sonuç alanının birimi, yöntem kimliği, durumu, değeri ve neden
  kodu; geçerli olmayan sayısal sonuç `null` olur, sıfırla doldurulmaz;
- kilitli F5 profilinin, yöntem/model dosyalarının ve kayıt/orkestrasyon
  kaynaklarının özetleri; Python/NumPy sürümü ve işletim sistemi/mimari;
- canlı oturumun LNA/VGA/RF kazancı, alıcı LO'su, örnekleme ve cihaz ayarı;
  kanal seçicinin mevcut profili, genlik ölçeği, arka ucu ve varsa kitaplık
  dosyasının oturum başlangıcında alınan özeti;
- kalibrasyon `unavailable`, profil/özet `null`, güç referansı dijital tam
  ölçek, `dbm_available: false`, `accuracy_proven: false`.

Alıcı ayarları oturumun yazılıma verdiği yapılandırmadır; bağımsız cihaz
geri okuması sayılmaz. SigMF'de bilinmeyen kazanç/ölçek `null` kalır.
Kartın çalışan hizmet/imaj özetleri gözlenmediğinden `board_identity: null`
olur; bir derleme dosyası özeti çalışan karta atfedilmez. Donanım UTC örnek
zamanı yoktur: `acquisition_utc: null`; istek/bitiş UTC zamanları yalnız
bilgisayar saatidir. Seçimde sabitlenmiş eski dört kare güncel alım diye
yeniden tarihlenmez; özgün kare kimlikleri korunur. Zaman aralığı, hücre
aralığı ve kullanılan örnekleme arasındaki ilişki yeniden oynatımda denetlenir.

Canlı ölçüm girişi dört karenin aynı merkez/örnekleme, CI8 biçimi/boyutu,
sıra, kart kare kimliği, DMA başarı ve sıfır aday düşümü bağını ayrıca
denetler. Devam eden ölçümde aralık düzenlemesi engellenir. Kayıt, yalnız
izole aralık doğrulamasını geçen sayıları geçerli taşır; düşük kalite
sonuçları da nedenleriyle saklanır. Eski E1/F5 gürültü, kenar ve sınıflandırma
eşikleri bu değişiklikte korunmuştur.

Kayıtlar Qt yerel uygulama veri dizininin `parameter-records/` altındadır.
Dosya yolu ve dış SHA-256 özeti uygulamanın Parametre kaydı günlüğündedir;
`measurementRecordPath` yalnız sonuç görünürken döner. Her dosya özel yeni
adla oluşturulur, var olan kaydın üzerine yazılmaz. Yazma hatasında kısmi
dosya kaldırılır ve yeni sonuç yayımlanmaz. Oluşturulmuş kayıtlar otomatik
silinmez; toplam disk kullanımı ölçüm sayısıyla artar. Kayıt başına ek 256 KiB
I/Q ve sınırlı JSON, F5 çekirdeğinin kalıcı bellek hesabından ayrı kayıt
maliyetidir; GUI/RX gerçek zamanlı hız kabulü yapılmış değildir.

Yeniden üretim:

```powershell
python scripts/verify_parameter_record.py KAYIT.zip --sha256 GUNLUKTEKI_OZET
```

Doğrulayıcı I/Q bütünlüğünü, dış özet verilmişse tüm arşivi ve güncel
çalışma zamanı/kaynak eşleşmesini denetler; kayıtlı I/Q'dan F5'i çalıştırır,
alan değer/durum/nedenlerini ve kaliteyi birebir karşılaştırır. Farklı kaynak
sürümündeki kaydı güncel kabul yapmaz. Dış özet olmadan yeniden hesaplama
sayısal tutarlılık sağlar; alıcı metadata'sının özgünlüğünü doğrulamaz.
Özet kriptografik imza değildir. Bu araç RF doğruluk veya dBm kabulü üretmez.

## Akış

Yalnız `confirmed && observed_this_frame` olay seçilebilir. PHASE-03 candidate bölgesi `[20,4075]` içinde `clamp(max(8, ceil(width/2)), 8, 64)` bin/yan marjla otomatik önizleme üretir. Komşu candidate orta noktası ile dört-bin guard aşılmaz. Otomatik öneri ölçümü başlatmaz; operatör aralığı sürükleyebilir ve sonuç yalnız `Ölçümü Başlat` ile üretilir.

Span `8–512` bindir. Dışında her yanda dört guard ve 32 reference hücresi gerekir; eksik reference için fallback yoktur. Sol/sağ reference farkı `3 dB` üzerindeyse sonuç `uncertain`; dört ardışık frame yoksa `insufficient_quality`; yayın gözlenmiyorsa `not_observed` kullanılır. Span, event, frame, kaynak, profil, Pfa, merkez politikası veya configuration nesli değişince eski sonuç temizlenir.

## Independent-fields-v2 doğrulama protokolü

Otomatik span yalnız ayrı bir kolaylık yeteneğidir; başarısızlığı operatörce çizilen manuel span ölçümlerini kapatmaz. Manuel emisyon merkezi, gözlenen taşıyıcı frekansı, OBW99, kalibre edilmemiş güç ve modülasyon kategorisi binding/OOS kararları birbirinden bağımsızdır.

Dört frame, sonlu I/Q/PSD, intent ve generation eşleşmesi, confirmed owner sürekliliği, izole span, reference hücreleri, reference uyumu ve `6 dB` ortak minimum SNR gerçek ortak ön koşullardır. Edge clipping, `%0,5/%99,5` kenarları, temporal kenar kararlılığı ve perturbation robustness yalnız OBW99 alanına aittir. Taşıyıcı çizgisinin gözlenmemesi, OBW99 sonucunun geçersizliği veya sınıflandırmanın Belirsiz kalması diğer alanların sonucunu değiştirmez.

Measurement intent dört frame boyunca aynı event kimliği/revision ve aynı source, pipeline ve configuration nesliyle bağlıdır. Kendi candidate'ı komşu sayılmaz; başka confirmed candidate span ve dört-bin guard ile kesişirse ölçüm `uncertain/neighbor_overlap` olur. Signal ve forced-noise benchmark'ları aynı owner/generation sözleşmesini kullanır. PHASE-03 end-to-end otomatik tespit sonucu manuel parametre capability paydasına katılmaz.

## Matematik

Dört frame ortalama lineer PSD'si `p[k]`, aritmetik ortalama reference noise değeri `n` için:

```text
d[k] = p[k] - n
T = Σ d[k]
```

`T` pozitif ve kanal SNR'si en az `6 dB` değilse ölçüm abstain eder. `d`, toplamı tam `T` olan non-negative simplex üzerine deterministik projekte edilir. Projected `s[k]` sonlu, non-negative ve `Σs=T` olmalıdır. İlk ve son dört hücrenin payı ayrı ayrı en fazla `%0,5` olabilir. OBW99 kenarları `s` kümülatif gücünün `%0,5/%99,5` noktalarıdır; fractional-bin interpolasyon fiziksel FFT çözünürlüğünü artırdığı iddiası değildir. Operatör aralığı emisyonun tamamını kapsamalıdır. Yalnız aralığın kendi kenarlarında düşük enerji görülmesi, uzun spektral kuyrukların aralık dışında bulunmadığını kanıtlamaz; bağımsız 30 kayıt tanısında dikdörtgen BPSK bu sınırı göstermiştir. Bu kapsama kapısı kapanmadan OBW saha doğruluğu kabul edilmez.

Emisyon merkez frekansı `s` birinci momentidir. Gözlenen taşıyıcı frekansı yalnız tepe/noise `≥10 dB`, üç-bin çizgi payı `≥%35` ve dört frame tepe aralığı `≤1 bin` olduğunda log-güç parabolik kestirimdir. Kanal gücü `T·Δf` üzerinden dBFS, tepe bin gücü PHASE-02 `bin_power_fs2` üzerinden dBFS/bin olur; PHASE-02 normalizasyonu ikinci kez uygulanmaz.

F5 OBW düzeltmesinde dört-kare ortalama fazlalık güç `[0,25; 0,5; 0,25]`
çekirdeğiyle yumuşatılır, `2,5·n·sqrt(0,375/4)` küçültmesi uygulanır;
`%0,75/%99,25` kümülatif noktaları bulunup iki kenar `0,375` FFT hücresi
dışarı genişletilir. Dört adet leave-one-out kenarının medyan sapması `7`
hücreyi aşarsa veya düzeltilmiş kenar seçili aralığa dayanırsa OBW belirsizdir.
Bu ampirik kuyruk düzeltmesi ITU-R OBW99 tanımını sonlu FFT'de kestirir;
standarttan türetilmiş evrensel hata garantisi değildir.

Dört karenin tek 16.384 örnekli Hann periodogramında aralık dışı enerjiye
istatistiksel gürültü belirsizliği ekleyen bir fail-closed aday ayrıca
karakterize edilmiştir. Bağımsız 30 örnekte aralık dışı 6/6 BPSK sonucunu
tutmuş, 12 dB'deki CW/AM/NFM/FSK sonuçlarının tamamını da tutmuştur. Bu yöntem
ürün F5 veya ARM çekirdeğine alınmamıştır; daha geniş önceden kilitli sayısal
değerlendirme, komşu yayın ve renkli gürültü kontrolleri, C/ARM eşdeğerliği ve
fiziksel RF doğrulaması gerektirir.

Pozitif fazlalık gücün spektral varyansı `V` için eşdeğer genişlik
`W=max(4·sqrt(V),1)` hücre alınır. Gösterilen bant içi SNR kestirimi
`0,8·10·log10(T/(n·W))+1,6 dB` formülüdür. `0,8` ve `1,6 dB` kilitli sayısal
kalibrasyon katsayılarıdır; tam bant zaman-alanı SNR'si veya RF ölçer sonucu
değildir.

Buradaki dBFS, sayısal tam ölçeğe göre güçtür; bant içi SNR dB cinsinden bir
orandır. Tam bant zaman-alanı giriş SNR'siyle aynı sayı olması beklenmez.
Mutlak güç yalnız `P_dBm = P_dBFS + C` ile ve `C` aynı alıcı seri numarası,
frekans aralığı, örnekleme, LNA/VGA, filtre, örnek ölçeği, geçerlilik süresi ve
belirsizlik sınırına bağlı ölçülmüş kalibrasyon olduğunda hesaplanır. Bu
koşullardan biri uyuşmazsa dBm alanı kullanılamaz kalır.

Modülasyon kategorisi dört frame'in her birinde frame-local bant sınırlama ile hesaplanan envelope, iki-seviye, constant-modulus, phase-jump ve instantaneous-frequency özelliklerinden çıkar. Frame sınırları arasında faz farkı alınmaz, raw I/Q geçmişi tutulmaz, çelişkili kanıt `Belirsiz` olur. Çıktı belirli bir modülasyon türü tanıma sonucu değildir.

## Alan bazlı doğrulama

Capability kimlikleri `emission_center_frequency`, `carrier_line_frequency`, `occupied_bandwidth`, `uncalibrated_power_dbfs` ve `signal_domain` olur. Profil yalnız binding ve OOS'ta geçen alanları içerir. Uygulanabilir olmayan taşıyıcı ailesinde doğru `not_observed` başarısı valid-rate paydasına girmez. Başarısız veya doğrulanmamış alan UI'da sayı göstermez. Otomatik span ayrı convenience capability'sidir.

Kalıcı payload üst sınırı `34.084 byte`, worker/pending sınırı `1/1` ve tek ölçüm okuması en fazla dört adet 4096-kompleks frame'dir. Büyük harici kayıt yalnız `rb/seek/bounded read` ile kullanılır; tam dosya okunmaz veya hashlenmez.
