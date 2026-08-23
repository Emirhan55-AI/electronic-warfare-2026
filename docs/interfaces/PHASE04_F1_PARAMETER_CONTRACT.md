# PHASE-04-F1 Alan Bazlı Parametre Sözleşmesi

## Girdi ve sahiplik

Ölçüm yalnız `confirmed && observed_this_frame` olayı, aynı event/revision,
aynı source/profile/configuration nesli ve operatörün açıkça onayladığı izole
span için başlatılır. Dört ardışık 4096 kompleks frame üst sınırdır. Ground truth
ve operatörün beklediği frekans, bant, güç veya sınıf runtime girdisi değildir.

Komşu doğrulanmış aday span veya dört-bin guard ile kesişiyorsa ölçüm `uncertain`
olur. Reference hücreleri iki tarafta tam değilse fallback kullanılmaz. Seek,
atlanan frame, owner değişimi, kaynak/profil/configuration değişimi ve yeni span
eski sonucu temizler.

## Çıktı alanları

Her alan değer, birim, durum ve gerekçe taşır. Durumlar yalnız `valid`,
`not_observed`, `not_applicable`, `insufficient_quality` veya `uncertain` olur.

| Alan | Literatür anlamı | Birim |
|---|---|---|
| `emission_center_frequency` | Gürültü etkisi giderilmiş spektral gücün birinci momenti | Hz |
| `carrier_line_frequency` | Yeterli dar çizgi kanıtında gözlenen taşıyıcı çizgisi | Hz |
| `occupied_bandwidth` | Toplam sinyal gücünün %99'unu içeren alt/üst kenar farkı | Hz |
| `uncalibrated_channel_power_dbfs` | Kalibre edilmemiş kompleks tam ölçek referanslı kanal gücü | dBFS |
| `snr_estimate_db` | Aynı yerel reference tanımına bağlı sinyal/gürültü oranı kestirimi | dB |
| `signal_domain` | Sınırlı Analog/Sayısal/Belirsiz ayrımı | — |

Spektral merkez taşıyıcı çizgisi adıyla sunulmaz. Taşıyıcı çizgisi uygulanmayan
veya gözlenmeyen yayında spektral merkez ayrıca geçerli olabilir. Sinyal alanı
genel modülasyon tanıma sonucu değildir.

## Doğrulama ayrımı

Yöntem geliştirme yalnız `development-scenes.json` ile yapılır. Binding ve OOS
seed'leri method-lock commit'ine kadar SHA-256 commitment arkasında kapalı kalır.
Seed reveal sonrasında eşik, yöntem, katalog, field scoring veya denominator
değiştirilemez. Binding veya OOS başarısız olursa sonuç korunur ve aynı alt fazda
yeniden ayar yapılmaz.

Otomatik span convenience metriğidir; operatörce onaylanan geçerli spanın çekirdek
alanlarını global olarak kapatmaz. PHASE-04 kapanışı bütün zorunlu alanların
binding ve OOS kapılarını geçmesini gerektirir.

## Kaynak ve iddia sınırı

Güç dBFS'tir; dBm veya RF giriş gücü değildir. Çalışma kayıtlı/sentetik I/Q ile
sınırlıdır. FPGA RTL, ARM/ZedBoard, canlı HackRF, GNSS, konum ve TX sonucu değildir.

