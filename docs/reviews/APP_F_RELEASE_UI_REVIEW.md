# APP-F Yayın Operatör Uygulaması İncelemesi

- İnceleme tarihi: 2026-08-26
- Kapsam: ürün giriş noktası, gerçek kaynak durumu, görev akışları, erişilebilirlik,
  ölçekleme ve performans
- Tekrarlanabilir doğrulayıcı: `scripts/verify_app_f_release_ui.py`
- Makine kanıtı: `results/evidence/app-f/release-ui-verification.json`

## Uygulanan ürün yüzeyi

Ürün giriş noktası Qt Quick/QML'dir. ED alanındaki kalıcı çalışma alanları
`Spektrum`, `Dinleme`, `Yön Bulma` ve `Sistem`; ET alanındaki çalışma yüzeyi
`ET Görevleri`dir. Spektrum ekranı
kaynak sözleşmesi, spektrum, 48 satırlık spektrogram, zamansal tespit listesi ve
seçili olayın operatör onaylı parametre ölçümünü birlikte taşır. Seçili sinyal
bağlamı sabit kalır; tespit listesi ve ölçüm formu aynı görev panelinde açık sekme
seçimiyle değiştirilir. Dinleme alanı aynı seçili tespit bağlamını kaydırılan kanal
ayarlarından ayırır; AM/NFM kanal hazırlama, demodüle ses dalga biçimi, gerçek PCM
süresi ve ses çıkışının işlediği oynatma konumunu sunar. Fiziksel ses çıkışı durumu WAV dışa
aktarma kullanılabilirliğinden ayrı gösterilir.

SigMF metadata ve veri eşleşmesi gerçek sözleşme denetiminden geçer. HackRF yolu
gerçek komut satırı araçlarını, yapılandırılmış ED_RX seri kimliğini ve cihazı
denetler; cihaz yokken kayıt veya sentetik veri yerine kullanılamaz durum ve
kurtarma metni gösterir. Bu inceleme bilgisayarında gerçek HackRF bağlı olmadığı
için canlı I/Q başarı iddiası kurulmamıştır.

Yön Bulma ekranı kaynak kimliğini, merkez frekansını, etkin kareyi ve bu kareden
hesaplanan kalibrasyonsuz geniş bant dBFS gücünü sabit bağlamda gösterir. İlk
ölçüm antenin 0° yön referansını oturum için kilitler; kaynak değişimi eski
ölçümleri temizler. En az üç farklı açı ve ayrışmış maksimum oluşmadan bağıl geliş
yönü ya da gerçek kerteriz göstermez. Faz uyumlu DoA, menzil ve hedef konumu
üretilmez.

Sistem ekranı GNU Radio Companion'daki okunabilir akış ilkesini düzenlenebilir
blok grafiği yerine sıralı ve salt-okunur işlem zincirine uygular. Yedi aşamanın
etkin yürütme katmanı ve durumu gerçek uygulama durumundan beslenir. Seçili
bileşenin host uygulaması, varsa RTL/taşınabilir C karşılığı ve kart kabul sınırı
ayrı gösterilir. Filtrelenebilir olay günlüğü sıra, zaman, seviye, bileşen ve kısa
nedeni taşır; 20 kayıtla sınırlıdır ve komut çalıştırmaz.

ET yüzeyi doğrulanmış offline sürekli, arabakışlı, analog loopback ve GPS L1 C/A
metadata modellerine bağlıdır. Sürekli ve analog görevler gerçek model
tamponlarını, arabakışlı görev gerçek durum pencerelerini gösterir. GNSS görevinde
ephemeris, NAV verisi ve I/Q dalga şekli bulunmadığı açıkça yazılır. Uygulama RF
TX API'si içermez.

## Görsel ve kullanım denetimi

Gerçek QML yüzeyi ED tarafında 1280×720, 1366×768, 1920×1080 ve %150 ölçeklemede
beş ayrı görünümde; ET tarafında 1180×680, 1280×720 ve 1440×900 koşullarında üç
ayrı görünümde render edilmiştir. Minimum ekranda `Tespitler`, `Ölçüm` ve GPS
metadata görünümleri ayrı ayrı denetlenmiştir. Karanlık tema kontrastı, seçim
alanları, odak sınırları, taşma ve son işleme bloğu görsel olarak incelenmiştir.
Klavye kısayolları:

- `Ctrl+O`: SigMF kaydı açma
- `Boşluk`: taramayı başlatma/duraklatma
- `Ctrl+1`, `Ctrl+2`, `Ctrl+3`, `Ctrl+4`: çalışma alanı geçişi
- `Ctrl+5`: ET görev doğrulama alanı
- `Alt+Sol`, `Alt+Sağ`: spektrum görünüm geçmişinde geri/ileri
- `Ctrl+B`: Spektrum kaynak panelini açma/kapatma
- `Ctrl+0`: Spektrum frekans görünümünü sıfırlama
- `Esc`: açık olay konsolunu kapatma

Spektruma özgü kısayollar diğer çalışma alanlarında işlem üretmez. Çalışma alanı
değişiminde klavye odağı seçili gezinme öğesine taşınır. Etkileşimli kontroller
erişilebilir ad, durum rozetleri ise erişilebilir durum açıklaması taşır.
`Hareketi azalt` ayarı geçiş süresini sıfırlar; spektrum ve ölçüm sayıları
dekoratif animasyon kullanmaz. Sistem ekranının ikincil metin ölçeği geniş
ekranda artırılır; minimum ekrandaki yoğun yerleşim korunur. Filtrelenmiş olay
günlüğü boşsa bunun veri yokluğu olduğu açıkça gösterilir.

## Ölçüm sonucu

Kanıt koşuları hash-kilitli `known-tone-ci8` ve `am-tone-ci8` SigMF kayıtlarını,
offscreen Qt platformu ve yazılım Qt Quick backend'ini kullanır. Kaynak doğrulaması
tamamlandıktan sonra her ekran profilinde bilinen ton kaydıyla 2,5 saniyelik 10 Hz
güncelleme ve arayüz heartbeat koşusu gerçek Qt olay döngüsünde yapılır; kaynak
açılış süresi ve ilk yerleşim geçişi çalışma zamanı tepkisellik ölçümüne katılmaz.
Ekran görüntüleri ölçüm sırasında senkronize depo dizinine yazılmaz; bütün zamanlı
koşular bittikten sonra kanıt klasörüne aktarılır. Standart profil daha sonra AM
kaydını bağımsız olarak açar ve gerçek tespitten kısa dinleme önizlemesi hazırlar.
Kabul kapıları:

- gözlenen güncelleme ≥ 9 Hz;
- işleme p95 < 100 ms;
- GUI heartbeat maksimum aralığı < 100 ms;
- QML'e verilen spektrum noktası 1–1600 aralığında;
- dört ekran/ölçek profili ve gerçek HackRF cihaz denetimi tamamlanmış durumda;
- işlem zinciri, yapılandırılmış olay günlüğü ve yayın modunda kapalı kaynak
  konumu denetimi mevcut;
- spektrum ve spektrogram ortak frekans görünümüne bağlı.
- `Tespitler` ve `Ölçüm` minimum çözünürlükte ayrı ayrı yüklenir.
- Dinleme yüzeyi gerçek seçili tespitten dalga biçimi, PCM süresi, kısa önizleme
  durumu ve fiziksel ses çıkışı sınırını üretir.
- Yön Bulma yüzeyi aynı gerçek I/Q karesini üç anten açısıyla kaydeder; kaynak ve
  referans bağı korunur, eşit güçlerde kerteriz üretmeyen belirsizlik kapısı geçer.
- Dört çalışma alanında bağlama duyarlı kısayol, odak aktarımı, erişilebilir durum,
  geniş ekran metin ölçeği ve boş günlük görünümü ortak ürün tutarlılığı kapısından
  geçer.
- Üç ET ekran profili gerçek offline model sonucuna bağlanır; arabakışlı pencere
  dizisi, GPS dalga şekli yokluğu ve TX API yokluğu ayrı kapılardan geçer.

Tüm kapılar geçmiştir. Sayısal sonuçlar kanıt JSON'unda korunur. Bunlar mevcut
Windows geliştirme bilgisayarına aittir; saha bilgisayarı, GPU veya uzun süreli
donanım kararlılığı iddiası değildir.

## Yayın sınırı

Yeni ürün yüzeyinde canlı GNSS, konum/harita, canlı RF ses kabulü, TX, eğitim
sahnesi veya gösterim verisi kontrolü yoktur. Yalnız kabul testini geçmiş offline
ET modelleri açık güvenlik sınırlarıyla ürün paketine alınır. Mock backend, eski
QWidget laboratuvarı, doğrulama veri setleri ve RF yayın yolu dışarıda kalır.
Fiziksel yetenekler gerçek kaynak ve kabul kanıtı olmadan navigasyona eklenemez.

## Çıkış regresyonu

Dokuzuncu bakım paketi commit edildikten sonra tam depo test takımı yeniden
çalıştırıldı. Sonuç `486 passed, 1 skipped, 0 failed` ve süre `829,13 s` oldu.
Kontrollü atlama yalnız yerel yolu yapılandırılmamış haricî gerçek veri setine
aittir.

ET-C ürün bağı `5198b00` commit'i üzerinde çalıştırıldığında görsel
doğrulayıcının 25/25 kapısı, tam depo test takımının ise `495 passed, 1 skipped,
0 failed` sonucu geçti. Tam koşu `390,050 s` sürdü; kontrollü atlama yalnız
yapılandırılmamış haricî gerçek veri setidir.
