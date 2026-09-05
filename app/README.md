# Operatör Uygulaması

## Güncel ST-06 sınırı — 5 Eylül 2026

Güncel durum ve sıradaki kabul adımları
[sinyal tespiti durum kaydında](../docs/interfaces/SIGNAL_DETECTION_STATUS.md)
tutulur. PL hücre kararını, kartın ARM CPU0/CPU1 çekirdekleri güç çözme ve
aday/olay işlemeyi yürütür; PC alım/taşıma/görselleştirme yolundadır.
Paketlenmiş hizmet dijital hız kapısını geçti; sürekli gerçek RX, kör RF ve
soğuk açılış kabulü henüz tamamlanmadı. Eski faz sonuçları yeni ürüne aktarılmaz.
Güncel kaynak/ham veri denetimi: `python scripts/verify_st06_parallel_product.py`.

`operator_console`, PySide6 ve Qt Quick/QML ile geliştirilen Türkçe masaüstü
uygulamasıdır. ED çalışma zamanı yalnız operatörün seçtiği SigMF kaydını veya
gerçek HackRF RX kaynağını kabul eder. ET çalışma zamanı doğrulanmış çevrimdışı
modelleri doğrudan ürün arayüzüne bağlar. Test backend'leri, kayıtlı doğrulama
verileri, eski laboratuvar arayüzleri ve RF yayın yolu ürün paketine dahil edilmez.

Uygulamanın mevcut çalışma alanları:

- `Spektrum`: kaynak yönetimi, dBFS spektrum, spektrogram, zamansal tespitler ve
  operatör onaylı sinyal parametre ölçümü. Spektrum ve spektrogram aynı
  yakınlaştırma/kaydırma frekans penceresini kullanır. Frekans imleci iki
  görünümde eşleşir; görünüm geçmişi korunur ve `Shift+sürükle` analiz aralığı
  taslağını gerçek FFT hücrelerine bağlar. Seçili sinyal bağlamı sabit kalırken
  `Tespitler` ve `Ölçüm` aynı görev panelinde operatör seçimiyle değiştirilir.
- `Dinleme`: sabit doğrulanmış tespit bağlamından operatör seçimli AM/NFM kanal
  hazırlama, demodüle ses dalga biçimi, gerçek oynatma konumu, fiziksel ses
  çıkışı durumu ve WAV dışa aktarma.
- `Yön Bulma`: gerçek I/Q karesinin geniş bant dBFS gücünü elle girilen anten
  açısıyla kaydetme, kaynak ve anten referansı kilitli ölçüm oturumu, bağıl geliş
  yönü ve geçerli gerçek kuzey referansı varsa gerçek kerteriz.
- `Sistem`: gerçek çalışma durumundan beslenen yedi aşamalı işlem zinciri,
  seçili bileşenin yürütme/donanım sınırı, ölçülen host işlem süresi ve
  filtrelenebilir salt-okunur olay günlüğü. Yayın görünümü komut kabuğu veya
  dosya sistemi denetimi sunmaz.
- `ET Görevleri`: sürekli taban bant, arabakışlı zamanlama, AM/FM/NFM
  yerel loopback ve GPS L1 C/A metadata doğrulaması. Bütün görevler TX kilitli
  çalışır; GNSS görevi ephemeris, NAV verisi veya I/Q dalga şekli üretmez.

Parametre ölçümü yalnız doğrulanmış bir tespit, dört ardışık gözlem ve operatörün
onayladığı analiz aralığı bulunduğunda açılır. Sonuçlar kalibrasyonsuz dBFS
ölçeğindedir; uygulama dBm, çok kanallı DoA, menzil veya otomatik hedef konumu
üretmez.

Kesintisiz dinleme, kaynakta en az beş saniyelik I/Q bulunmasını gerektirir.
Daha kısa kayıtlar yalnız süreleri açıkça gösterilen kısa önizleme üretir; canlı
HackRF ses saha kabulü tamamlanmış sayılmaz.

Tespit listesi görev sırasında sabit kalır. Tespit listesi ile sinyal ölçümü aynı
anda daraltılmaz; sabit seçili sinyal kartının altındaki ayrı görev görünümlerinde
açılır. Dinleme alanında seçili sinyal, hazırlama eylemi ve sonuç kontrolleri
sabit kalır; yalnız kanal ayarları kendi panelinde kaydırılır. Oynatma zaman
çizelgesi salt okunurdur ve ses çıkışının işlediği PCM süresinden beslenir.

Klavye kullanımı çalışma alanına bağlıdır. `Ctrl+1`–`Ctrl+4` ED çalışma alanını,
`Ctrl+5` ET görevlerini açar ve odağı seçilen alana taşır. `Boşluk`, `Ctrl+B`, `Alt+Sol`,
`Alt+Sağ` ve `Ctrl+0` yalnız Spektrum alanında tarama, kaynak paneli ve ortak
frekans görünümünü yönetir. `Esc` açık olay konsolunu kapatır. Durum rozetleri,
seçim kutuları ve görev kontrolleri erişilebilir ad taşır.

Yön Bulma ölçümleri kaynak değişiminde temizlenir. İlk kayıt antenin 0° yön
referansını oturum için sabitler; referans ancak ölçümler temizlendikten sonra
değiştirilebilir. Üç farklı açı tek başına sonuç garantisi değildir: belirgin bir
güç maksimumu yoksa uygulama kerteriz üretmez.

Çalıştırma:

```powershell
python -m app.operator_console
```

Ürün sınırı `config/app/product-package.json`, arayüz kabul koşulları ise
`scripts/verify_app_f_release_ui.py` tarafından denetlenir.
