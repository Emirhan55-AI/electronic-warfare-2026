# Operatör Görev Akışları

- Sürüm: 1.1
- Güncelleme tarihi: 2026-08-25
- Kapsam: APP-F için ürün bilgi mimarisi

## Genel yerleşim

Ürün arayüzü üç kalıcı çalışma alanından oluşur:

1. `Spektrum`: kaynak, spektrum, spektrogram, tespit listesi ve seçili sinyal.
2. `Yön Bulma`: anten açısı–güç ölçümü, bağıl geliş açısı ve kerteriz.
3. `Sistem`: bileşen sağlığı, performans ve son olaylar.

Üst görev çubuğu ED bağlamını, kaynak kimliğini, merkez frekansını, örnekleme
hızını ve kaynak durumunu sürekli gösterir. Alt durum çubuğundaki `Olay Konsolu`,
yapılandırılmış uygulama olaylarını salt okunur bir panelde açar; işletim sistemi
komutu çalıştıran bir kabuk değildir.

Parametre ölçümü seçili sinyal bağlamından açılır; kaynak ve tespit kimliği her
adımda korunur. Kayıtlı I/Q üzerinde doğrulanmış AM/NFM zinciri henüz bu ürün
arayüzüne alınmamıştır.

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

## Ürün sınırı — Analog dinleme

AM/NFM demodülasyonu kayıtlı I/Q üzerinde ayrı host testleriyle doğrulanmıştır,
ancak mevcut ürün QML çalışma alanında dinleme denetimi bulunmaz. Gerçek HackRF
ve ses aygıtı kabulü tamamlanmadan bu işlev yayın arayüzünde etkin gösterilmez.

## Akış 5 — Yön bulma

1. Operatör frekansı, anten 0° referansını ve anten dönüş açısını belirler.
2. Her saha ölçümü açı, dBFS güç, zaman ve kaynakla kaydedilir.
3. Yeterli ölçüm yoksa kerteriz sonucu üretilmez.
4. Önce `Bağıl Geliş Açısı` hesaplanır.
5. Geçerli `Anten Referans Yönü` varsa `Gerçek Kuzeye Göre Kerteriz` hesaplanır.
6. Faz uyumlu çok kanallı DoA, hedef konumu veya menzil sonucu üretilmez.

## Akış 6 — Sistem denetimi ve kurtarma

Sistem görünümü düzenlenebilir veya dekoratif bir DSP blok grafiği sunmaz.
Kaynak, ön işleme, FFT/güç, tespit ve operatör görevlerinin sağlık durumu kompakt
bir şeritte `Kullanılmıyor`, `Hazır`, `Çalışıyor` veya `Hata` olarak gösterilir.
Son olaylar zaman, bileşen ve kısa nedenle listelenir; ayrıntılı kayıt alt
çubuktaki salt-okunur `Olay Konsolu` üzerinden incelenir.

## Geçiş ve hareket kuralları

- Durum değişimleri 120–180 ms arası opacity/position geçişi kullanabilir.
- Spektrum, spektrogram, alarm ve ölçüm sayıları dekoratif animasyon kullanmaz.
- Hareket, görev bağlamının değiştiğini veya bir panelin açılıp kapandığını
  anlatmalıdır; sürekli parlayan öğe kullanılmaz.
- `Ctrl+B`, veri kaynağı panelini görev alanını büyütmek için yumuşakça daraltır.
- Kerteriz ibresi yalnız yeni geçerli ölçüme geçerken hareket eder; seçili adayın
  spektrum vurgusu kısa bir odak geçişi kullanır.
- `Hareketi azalt` sistem ayarı desteklenir.
- Veri güncellemesi hedefi 10 Hz'dir; hareketli geçişlerin hedefi 60 Hz olsa da
  hedef donanım ölçümü yapılmadan performans iddiası kurulmaz.
