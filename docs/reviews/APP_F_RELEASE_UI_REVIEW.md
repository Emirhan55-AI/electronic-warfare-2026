# APP-F Yayın Operatör Uygulaması İncelemesi

- İnceleme tarihi: 2026-08-24
- Kapsam: ürün giriş noktası, gerçek kaynak durumu, görev akışları, erişilebilirlik,
  ölçekleme ve performans
- Tekrarlanabilir doğrulayıcı: `scripts/verify_app_f_release_ui.py`
- Makine kanıtı: `results/evidence/app-f/release-ui-verification.json`

## Uygulanan ürün yüzeyi

Ürün giriş noktası Qt Quick/QML'dir. Kalıcı çalışma alanları `Operasyon`, `Yön
Bulma` ve `Sistem` olarak sınırlandırılmıştır. Operasyon ekranı kaynak sözleşmesi,
spektrum, 48 satırlık spektrogram, temporal tespit listesi ve seçili olayın P0
parametre ölçümünü birlikte taşır.

SigMF metadata ve veri eşleşmesi gerçek sözleşme denetiminden geçer. HackRF yolu
gerçek komut satırı araçlarını, yapılandırılmış ED_RX seri kimliğini ve cihazı
denetler; cihaz yokken kayıt veya sentetik veri yerine kullanılamaz durum ve
kurtarma metni gösterir. Bu inceleme bilgisayarında gerçek HackRF bağlı olmadığı
için canlı I/Q başarı iddiası kurulmamıştır.

Yön Bulma ekranı anten açısı, açık 0° referansı ve etkin I/Q karesinden hesaplanan
göreli dBFS gücünü kaydeder. En az üç farklı açı ve ayrışmış maksimum oluşmadan
bağıl geliş açısı ya da kerteriz göstermez. Faz uyumlu DoA, menzil ve hedef konumu
üretilmez.

Sistem ekranı GNU Radio Companion'daki okunabilir blok akışı ilkesini salt-okunur
durum kartlarına uygular. Operatör DSP grafiğini değiştiremez. Olay günlüğü 20
kayıtla sınırlıdır.

## Görsel ve kullanım denetimi

Gerçek QML yüzeyi 1280×720, 1366×768, 1920×1080 ve %150 ölçeklemede render
edilmiştir. Minimum ekran, karanlık tema kontrastı, seçim alanları, odak sınırları,
taşma ve son işleme bloğu görsel olarak incelenmiştir. Klavye kısayolları:

- `Ctrl+O`: SigMF kaydı açma
- `Boşluk`: taramayı başlatma/duraklatma
- `Ctrl+1`, `Ctrl+2`, `Ctrl+3`: çalışma alanı geçişi

Etkileşimli kontroller erişilebilir ad taşır. `Hareketi azalt` ayarı geçiş süresini
sıfırlar; spektrum ve ölçüm sayıları dekoratif animasyon kullanmaz.

## Ölçüm sonucu

Kanıt koşuları hash-kilitli `known-tone-ci8` SigMF kaydını, offscreen Qt platformu
ve yazılım Qt Quick backend'ini kullanır. Her ekran profilinde 2,5 saniyelik 10 Hz
güncelleme koşusu yapılır. Kabul kapıları:

- gözlenen güncelleme ≥ 9 Hz;
- işleme p95 < 100 ms;
- GUI heartbeat maksimum aralığı < 100 ms;
- QML'e verilen spektrum noktası 1–1600 aralığında;
- dört ekran/ölçek profili ve gerçek HackRF probe işlemi settled durumda.

Tüm kapılar geçmiştir. Sayısal sonuçlar kanıt JSON'unda korunur. Bunlar mevcut
Windows geliştirme bilgisayarına aittir; saha bilgisayarı, GPU veya uzun süreli
donanım kararlılığı iddiası değildir.

## Yayın sınırı

Yeni ürün yüzeyinde bağlı olmayan GNSS, konum/harita, analog ses kabulü, TX,
offline ET, eğitim sahnesi veya gösterim verisi kontrolü yoktur. İlgili algoritma
ve tarihsel doğrulama yüzeyleri silinmemiştir; ürün paketine ithal edilmez. Bu
özellikler gerçek kaynak ve kabul kanıtı olmadan navigasyona eklenemez.
