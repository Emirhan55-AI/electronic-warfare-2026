# Operatör Görev Akışları

- Sürüm: 1.5
- Güncelleme tarihi: 2026-08-26
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
2. Spektrum başlığındaki `Başlat` tek birincil tarama eylemidir; kaynak, tarama
   durumu ve `Duraklat` aynı görev başlığında kalır.
3. Spektrum ve spektrogram merkez çalışma alanında güncellenir.
4. Adaylar tespit listesine gelir; durumları `İzleniyor`, `Doğrulandı` veya
   `Sona ermiş` olarak gösterilir.
5. Sağdaki `Sinyal Görevi`, seçili tespitin kimliğini, frekansını,
   tepe/gürültü oranını ve durumunu sekmelerden bağımsız sabit tutar. `Tespitler`
   ve `Ölçüm` aynı panelde açık operatör seçimiyle değiştirilir; tespit seçimi
   ekranı kendiliğinden ölçüme geçirmez.
6. Operatör bir doğrulanmış tespit seçtiğinde kaba aday ve önerilen analiz aralığı
   gerçek FFT hücrelerine bağlı olarak spektrum üzerinde işaretlenir.
7. Fare tekeriyle yakınlaştırma ve sol tuşla kaydırma spektrum ile spektrogramda
   aynı frekans penceresini değiştirir; çift tıklama, `1:1` veya `Ctrl+0` tam
   banda döner. `Alt+Sol` ve `Alt+Sağ` önceki/sonraki frekans görünümünü açar.
8. Ortak frekans imleci iki görünümde aynı frekansı işaretler. Operatör,
   `Shift+sürükle` ile seçili tepeyi içeren 8–512 FFT hücrelik analiz aralığı
   taslağı oluşturabilir; taslak ayrıca açıkça onaylanmadan ölçüm başlamaz.

Çıkış koşulu: seçimin kaynak kimliği, çerçeve ve tespit kimliği birbirine bağlıdır.

## Akış 3 — Parametre ölçümü

1. Seçili doğrulanmış tespitin sabit bağlamından `Ölçüm` sekmesi açılır.
2. Sistem deterministik `Tespit aralığı`nı gösterir; operatör isterse sınırları
   düzeltir.
3. Ölçüm yalnız `Ölçümü Başlat` eylemiyle çalışır.
4. Sonuçta emisyon merkez frekansı, gözlenen taşıyıcı frekansı, OBW %99, alt/üst
   OBW frekansı, kanal gücü, SNR ve sinyal türü kalite
   durumuyla birlikte gösterilir.
5. Kalite kapısı geçmezse sayı yerine neden gösterilir.

## Akış 4 — Analog dinleme

1. Operatör Spektrum alanında doğrulanmış bir tespit seçer.
2. `Dinleme` alanı tespit kimliğini, frekansını ve kaynak I/Q süresini kaydırılan
   ayarlardan bağımsız sabit bir kanal kartında tutar.
3. AM veya NFM, kanal ofseti, bant genişliği ve ses seviyesi açıkça belirlenir.
4. Sabit `Kanal Sesini Hazırla` eylemi, kaynaktaki I/Q'yu GUI iş parçacığı dışında
   işler.
5. En az beş saniyelik uygun kayıt kesintisiz sonuç; daha kısa kayıt yalnız açıkça
   etiketli kısa önizleme üretir.
6. Sonuç 48 kHz mono PCM16 olarak oynatılabilir veya WAV dışa aktarılabilir.
   Salt-okunur zaman çizelgesi hazırlanan PCM süresini ve ses çıkışının gerçekten
   işlediği oynatma konumunu gösterir; fiziksel ses çıkışı yoksa WAV kullanılabilirliği
   bundan ayrı bildirilir.

Canlı HackRF ve fiziksel ses aygıtı saha kabulü tamamlanmadan bu akış canlı RF
dinleme başarısı olarak sunulmaz.

## Akış 5 — Yön bulma

1. Sabit kaynak kartı kaynak kimliğini, merkez frekansını, etkin kareyi ve
   kalibrasyonsuz geniş bant kare gücünü gösterir.
2. Operatör anten dönüş açısını ve antenin 0° yön referansını belirler. İlk kayıt
   bu referansı ölçüm oturumu için sabitler; değiştirmek için ölçümler temizlenir.
3. Her saha ölçümü anten açısı, dBFS kare gücü, frekans, zaman, anten azimutu ve
   kaynak kimliğiyle kaydedilir. Kaynak değiştiğinde eski oturum otomatik temizlenir.
4. En az üç farklı açı yoksa veya güç maksimumu yeterince ayrışmıyorsa sonuç
   üretilmez ve eksik koşul gösterilir.
5. Geçerli sonuç önce antenin 0° eksenine göre `Bağıl Geliş Yönü` olarak sunulur.
6. Anten 0° yönü gerçek kuzeye bağlanmışsa `Gerçek Kerteriz` ayrıca gösterilir.
7. Faz uyumlu çok kanallı DoA, hedef konumu veya menzil sonucu üretilmez.

`Radyo kerterizi` terminolojisi ITU-R yön bulma kullanımını; bağıl ve gerçek yön
ayrımı ise açının anten eksenine mi gerçek kuzeye mi bağlı olduğunu izler. Tek
istasyon kerterizi bir konum kestirimi değildir.

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
  panellerinde bağımsız kaydırılır; dinleme hazırlama eylemi ile oynatma
  kontrolleri görünür kalır. Bütün çalışma alanını hareket ettiren ortak sayfa
  kaydırması kullanılmaz.
- Kerteriz ibresi yalnız yeni geçerli ölçüme geçerken hareket eder; seçili adayın
  spektrum vurgusu kısa bir odak geçişi kullanır.
- Yön Bulma kaynak bağlamı, kayıt eylemi ve sonuç geçmişi sabit kalır; yalnız
  ölçüm ayarları kendi panelinde kaydırılır.
- `Hareketi azalt` sistem ayarı desteklenir.
- Veri güncellemesi hedefi 10 Hz'dir; hareketli geçişlerin hedefi 60 Hz olsa da
  hedef donanım ölçümü yapılmadan performans iddiası kurulmaz.
