# APP-F Yayın Operatör Uygulaması İncelemesi

- İnceleme tarihi: 2026-08-26
- Kapsam: ürün giriş noktası, gerçek kaynak durumu, görev akışları, erişilebilirlik,
  ölçekleme ve performans
- Tekrarlanabilir doğrulayıcı: `scripts/verify_app_f_release_ui.py`
- Makine kanıtı: `results/evidence/app-f/release-ui-verification.json`

## Uygulanan ürün yüzeyi

Ürün giriş noktası Qt Quick/QML'dir. Kalıcı çalışma alanları `Spektrum`,
`Dinleme`, `Yön Bulma` ve `Sistem` olarak sınırlandırılmıştır. Spektrum ekranı
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

Yön Bulma ekranı anten açısı, açık 0° referansı ve etkin I/Q karesinden hesaplanan
göreli dBFS gücünü kaydeder. En az üç farklı açı ve ayrışmış maksimum oluşmadan
bağıl geliş açısı ya da kerteriz göstermez. Faz uyumlu DoA, menzil ve hedef konumu
üretilmez.

Sistem ekranı GNU Radio Companion'daki okunabilir akış ilkesini düzenlenebilir
blok grafiği yerine sıralı ve salt-okunur işlem zincirine uygular. Yedi aşamanın
etkin yürütme katmanı ve durumu gerçek uygulama durumundan beslenir. Seçili
bileşenin host uygulaması, varsa RTL/taşınabilir C karşılığı ve kart kabul sınırı
ayrı gösterilir. Filtrelenebilir olay günlüğü sıra, zaman, seviye, bileşen ve kısa
nedeni taşır; 20 kayıtla sınırlıdır ve komut çalıştırmaz.

## Görsel ve kullanım denetimi

Gerçek QML yüzeyi 1280×720, 1366×768, 1920×1080 ve %150 ölçeklemede beş ayrı
görünümde render edilmiştir. Minimum ekranda `Tespitler` ve `Ölçüm` görünümleri
ayrı ayrı denetlenmiştir. Karanlık tema kontrastı, seçim alanları, odak sınırları,
taşma ve son işleme bloğu görsel olarak incelenmiştir. Klavye kısayolları:

- `Ctrl+O`: SigMF kaydı açma
- `Boşluk`: taramayı başlatma/duraklatma
- `Ctrl+1`, `Ctrl+2`, `Ctrl+3`, `Ctrl+4`: çalışma alanı geçişi
- `Alt+Sol`, `Alt+Sağ`: spektrum görünüm geçmişinde geri/ileri

Etkileşimli kontroller erişilebilir ad taşır. `Hareketi azalt` ayarı geçiş süresini
sıfırlar; spektrum ve ölçüm sayıları dekoratif animasyon kullanmaz.

## Ölçüm sonucu

Kanıt koşuları hash-kilitli `known-tone-ci8` ve `am-tone-ci8` SigMF kayıtlarını,
offscreen Qt platformu ve yazılım Qt Quick backend'ini kullanır. Kaynak doğrulaması
tamamlandıktan sonra her ekran profilinde bilinen ton kaydıyla 2,5 saniyelik 10 Hz
güncelleme ve arayüz heartbeat koşusu yapılır; kaynak açılış süresi çalışma zamanı
tepkisellik ölçümüne katılmaz. Standart profil daha sonra AM kaydını bağımsız
olarak açar ve gerçek tespitten kısa dinleme önizlemesi hazırlar. Kabul kapıları:

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

Tüm kapılar geçmiştir. Sayısal sonuçlar kanıt JSON'unda korunur. Bunlar mevcut
Windows geliştirme bilgisayarına aittir; saha bilgisayarı, GPU veya uzun süreli
donanım kararlılığı iddiası değildir.

## Yayın sınırı

Yeni ürün yüzeyinde bağlı olmayan GNSS, konum/harita, canlı RF ses kabulü, TX,
offline ET, eğitim sahnesi veya gösterim verisi kontrolü yoktur. İlgili algoritma
ve tarihsel doğrulama yüzeyleri silinmemiştir; ürün paketine ithal edilmez. Bu
özellikler gerçek kaynak ve kabul kanıtı olmadan navigasyona eklenemez.

## Çıkış regresyonu

Bu bakım paketi commit edildikten sonra tam depo test takımı yeniden çalıştırıldı.
Sonuç `484 passed, 1 skipped, 0 failed` ve süre `428,88 s` oldu. Kontrollü atlama
yalnız yerel yolu yapılandırılmamış haricî gerçek veri setine aittir.
