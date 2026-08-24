# PHASE-04-F2 Parametre Doğrulama Sözleşmesi

## Kapsam

F2, başarısız F1 yöntemini veya değerlendirmesini değiştirmez. Yeni v3 yöntem,
yalnız yeni açık geliştirme kataloğunda geliştirilecek ve F2 binding/OOS
preimage'ları yöntem ile çalıştırıcı kilitlenene kadar kapalı tutulacaktır.

Ölçüm sahipliği, dört ardışık 4096 kompleks kare, aynı event/revision,
source/profile/configuration nesli, operatör onaylı izole span ve runtime
ground-truth yasağı F1 sözleşmesinden değişmeden taşınır.

## Alanlar

Zorunlu parametre alanları emisyon merkez frekansı, gözlenen taşıyıcı frekansı,
OBW99, kalibre edilmemiş kanal gücü, SNR kestirimi ve sınırlı sinyal alanıdır.
Span dayanıklılığı zorunlu destek kapısıdır. Bütün alan ve destek kapıları binding
ile OOS'ta geçmeden ürün profili oluşturulmaz.

## Çalıştırılabilir kabul modeli

Her kabul maddesi benzersiz `id`, alan sahibi, metrik adı, karşılaştırma işleci ve
eşik taşır. Skorlayıcı yalnız tam metrik kümesini kabul eder; eksik veya fazla
metrik fail-closed hatadır. Eşik sınır değeri ile ilk ihlal değeri protokol
kilidinden önce otomatik çalıştırılır.

Negatif kontrol merkez, taşıyıcı, OBW, güç, SNR ve sinyal alanı için ayrı kapıdır.
Bir alanın negatif kontrol ihlali başka alanın yerel kararını değiştirmez. Bununla
birlikte bütün-profil kararı bütün zorunlu yerel kararların birlikte geçmesini
gerektirir.

`frames_per_measurement` dört, `noise_measurements` ise bağımsız ölçüm sayısıdır.
Kare, sekans ve ölçüm terimleri birbirinin yerine kullanılmaz. Taşıyıcının düşük
SNR abstention kapısı binding ve OOS'ta açıkça çalıştırılır.

## Veri ayrımı

F2 açık geliştirme kataloğu altı yeni seed ve toplam 288 trial/aile içerir. F1'de
açılmış binding/OOS seed'leri geliştirme veya yöntem ayarı için kullanılamaz. F2
binding ve OOS seed'leri commitment arkasında repository dışında tutulur.

Seed reveal sonrasında eşik, scorer, yöntem, katalog, denominator veya alan
sahipliği değiştirilemez. Başarısız tek seferlik değerlendirme korunur ve yeniden
çalıştırılmaz.

## İddia sınırı

Bu sözleşme canlı RF, dBm, FPGA/ARM yürütümü, HackRF donanım kabulü veya ürün
başarısı değildir. Güç dBFS kalır; sinyal alanı genel modülasyon tanıma sonucu
değildir.
