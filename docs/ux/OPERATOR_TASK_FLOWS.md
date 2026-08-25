# Operatör Görev Akışları

- Sürüm: 1.2
- Güncelleme tarihi: 2026-08-25
- Kapsam: APP-F için ürün bilgi mimarisi

## Genel yerleşim

Ürün arayüzü dört kalıcı çalışma alanından oluşur:

1. `Spektrum`: kaynak, spektrum, spektrogram, tespit listesi ve seçili sinyal.
2. `Dinleme`: seçili doğrulanmış tespit, AM/NFM kanal ayarları, ses sonucu ve WAV.
3. `Yön Bulma`: anten açısı–güç ölçümü, bağıl geliş açısı ve kerteriz.
4. `Sistem`: bileşen sağlığı, performans ve son olaylar.

Üst görev çubuğu ED bağlamını, kaynak kimliğini, merkez frekansını, örnekleme
hızını ve kaynak durumunu sürekli gösterir. Alt durum çubuğundaki `Olay Konsolu`,
yapılandırılmış uygulama olaylarını salt okunur bir panelde açar; işletim sistemi
komutu çalıştıran bir kabuk değildir.

Parametre ölçümü ve analog dinleme seçili sinyal bağlamından açılır; kaynak ve
tespit kimliği her adımda korunur.

## Akış 1 — Kaynağı hazırlama

1. Operatör `SigMF Kaydı` veya `HackRF Canlı RX` seçer.
2. Uygulama kaynağı açmadan önce sözleşme ve cihaz durumunu denetler.
3. Başarılıysa merkez frekansı, örnekleme hızı, kaynak kimliği ve kalibrasyon
   durumu üst durum alanında görünür.
4. Başarısızsa tek bir hata nedeni ve uygulanabilir kurtarma eylemi gösterilir.

Çıkış koşulu: kaynak gerçek ve erişilebilir durumdadır. Yerine başka veri
konulmaz; son başarılı kaynağın değerleri yeni kaynakmış gibi korunmaz.

## Akış 2 — Sinyal tespiti

```text
[Veri Kaynağı] → [Ön İşleme] → [FFT / Güç] → [Bölgesel Eşik] → [Zamansal Doğrulama]
```

1. Operatör doğrulanmış bir SigMF kaydı açar veya HackRF RX alımını hazırlar.
2. `Taramayı Başlat` tek birincil eylemdir.
3. Spektrum ve spektrogram merkez çalışma alanında güncellenir.
4. Adaylar tespit listesine gelir; durumları `İzleniyor`, `Doğrulandı` veya
   `Sona ermiş` olarak gösterilir.
5. Operatör bir doğrulanmış tespit seçtiğinde kaba aday ve önerilen analiz aralığı
   gerçek FFT hücrelerine bağlı olarak spektrum üzerinde işaretlenir.
6. Fare tekeriyle yakınlaştırma ve sol tuşla kaydırma spektrum ile spektrogramda
   aynı frekans penceresini değiştirir; çift tıklama, `1:1` veya `Ctrl+0` tam
   banda döner. `Alt+Sol` ve `Alt+Sağ` önceki/sonraki frekans görünümünü açar.
7. Ortak frekans imleci iki görünümde aynı frekansı işaretler. Operatör,
   `Shift+sürükle` ile seçili tepeyi içeren 8–512 FFT hücrelik analiz aralığı
   taslağı oluşturabilir; taslak ayrıca açıkça onaylanmadan ölçüm başlamaz.

Çıkış koşulu: seçimin kaynak kimliği, çerçeve ve tespit kimliği birbirine bağlıdır.

## Akış 3 — Parametre ölçümü

1. Seçili doğrulanmış tespitin spektrumu açılır.
2. Sistem deterministik `Tespit aralığı`nı gösterir; operatör isterse sınırları
   düzeltir.
3. Ölçüm yalnız `Ölçümü Başlat` eylemiyle çalışır.
4. Sonuçta emisyon merkez frekansı, gözlenen taşıyıcı frekansı, OBW %99, alt/üst
   OBW frekansı, kanal gücü, SNR ve sinyal türü kalite
   durumuyla birlikte gösterilir.
5. Kalite kapısı geçmezse sayı yerine neden gösterilir.

## Akış 4 — Analog dinleme

1. Operatör Spektrum alanında doğrulanmış bir tespit seçer.
2. `Dinleme` alanında AM veya NFM, kanal ofseti, bant genişliği ve ses seviyesi
   açıkça belirlenir.
3. `Kanal Sesini Hazırla`, kaynaktaki I/Q'yu GUI iş parçacığı dışında işler.
4. En az beş saniyelik uygun kayıt kesintisiz sonuç; daha kısa kayıt yalnız açıkça
   etiketli kısa önizleme üretir.
5. Sonuç 48 kHz mono PCM16 olarak oynatılabilir veya WAV dışa aktarılabilir.

Canlı HackRF ve fiziksel ses aygıtı saha kabulü tamamlanmadan bu akış canlı RF
dinleme başarısı olarak sunulmaz.

## Akış 5 — Yön bulma

1. Operatör frekansı, anten 0° referansını ve anten dönüş açısını belirler.
2. Her saha ölçümü açı, dBFS güç, zaman ve kaynakla kaydedilir.
3. Yeterli ölçüm yoksa kerteriz sonucu üretilmez.
4. Önce `Bağıl Geliş Açısı` hesaplanır.
5. Geçerli `Anten Referans Yönü` varsa `Gerçek Kuzeye Göre Kerteriz` hesaplanır.
6. Faz uyumlu çok kanallı DoA, hedef konumu veya menzil sonucu üretilmez.

## Akış 6 — Sistem denetimi ve kurtarma

Sistem görünümü düzenlenebilir veya dekoratif bir DSP blok grafiği sunmaz.
Kaynak, ön işleme, FFT/güç, tespit ve operatör görevleri soldaki sıralı işlem
zincirinde `Kullanılmıyor`, `Bekliyor`, `Hazır`, `Çalışıyor` veya `Hata` olarak
gösterilir. Seçili bileşenin gerçekten çalışan katmanı, doğrulanmış kaynak
karşılığı ve donanım kabul sınırı sağdaki denetçide açıklanır. Sistem olayları
sıra numarası, zaman, seviye, bileşen ve kısa nedenle filtrelenebilir salt-okunur
günlükte tutulur. Bu alan komut çalıştırmaz; yayın görünümünde dosya sistemi
denetimleri sunulmaz. Alt çubuktaki `Olay Konsolu` aynı kayıtların çalışma
alanından bağımsız hızlı görünümüdür.

## Geçiş ve hareket kuralları

- Durum değişimleri 120–180 ms arası opacity/position geçişi kullanabilir.
- Spektrum, spektrogram, alarm ve ölçüm sayıları dekoratif animasyon kullanmaz.
- Hareket, görev bağlamının değiştiğini veya bir panelin açılıp kapandığını
  anlatmalıdır; sürekli parlayan öğe kullanılmaz.
- `Ctrl+B`, veri kaynağı panelini görev alanını büyütmek için yumuşakça daraltır.
- Tespit listesinin yüksekliği içerik sayısından bağımsızdır; confirmed adaylar
  olay kimliğiyle kararlı sıralanır ve seçim fare basışında alınır.
- Tespit seçimi sabit kalırken sinyal ölçümü ve analog kanal ayarları kendi
  panellerinde bağımsız kaydırılır; bütün çalışma alanını hareket ettiren ortak
  sayfa kaydırması kullanılmaz.
- Kerteriz ibresi yalnız yeni geçerli ölçüme geçerken hareket eder; seçili adayın
  spektrum vurgusu kısa bir odak geçişi kullanır.
- `Hareketi azalt` sistem ayarı desteklenir.
- Veri güncellemesi hedefi 10 Hz'dir; hareketli geçişlerin hedefi 60 Hz olsa da
  hedef donanım ölçümü yapılmadan performans iddiası kurulmaz.
