# Operatör Görev Akışları

- Sürüm: 1.0
- Dondurma tarihi: 2026-08-23
- Kapsam: APP-F için ürün bilgi mimarisi

## Genel yerleşim

Ürün arayüzü üç kalıcı çalışma alanından oluşur:

1. `Spektrum`: kaynak, spektrum, spektrogram, tespit listesi ve seçili sinyal.
2. `Yön Bulma`: anten açısı–güç ölçümü, bağıl geliş açısı, kerteriz ve harita.
3. `Sistem`: bileşen sağlığı, performans ve son olaylar.

Üst görev çubuğu ED bağlamını, kaynak kimliğini, merkez frekansını, örnekleme
hızını ve kaynak durumunu sürekli gösterir. Alt durum çubuğundaki `Olay Konsolu`,
yapılandırılmış uygulama olaylarını salt okunur bir panelde açar; işletim sistemi
komutu çalıştıran bir kabuk değildir.

Parametre ölçümü ve dinleme, seçili sinyal bağlamından açılan görevlerdir. Ayrı
birer bağımsız dünya gibi davranmaz; kaynak ve tespit kimliği her adımda korunur.

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
[Veri Kaynağı] → [Ön İşleme] → [FFT / Güç] → [OS-CFAR] → [Zamansal Doğrulama]
```

1. Operatör arama kapsamını seçer: bilinmeyen frekans, bant aralığı veya belirtilen
   merkez frekansı.
2. `Taramayı Başlat` tek birincil eylemdir.
3. Spektrum ve spektrogram merkez çalışma alanında güncellenir.
4. Adaylar tespit listesine gelir; durumları `İzleniyor`, `Doğrulandı` veya
   `Sona ermiş` olarak gösterilir.
5. Operatör bir doğrulanmış tespit seçer.

Çıkış koşulu: seçimin kaynak kimliği, çerçeve ve tespit kimliği birbirine bağlıdır.

## Akış 3 — Parametre ölçümü

1. Seçili doğrulanmış tespitin spektrumu açılır.
2. Sistem deterministik `Tespit aralığı`nı gösterir; operatör isterse sınırları
   düzeltir.
3. Ölçüm yalnız `Ölçümü Başlat` eylemiyle çalışır.
4. Sonuçta emisyon merkez frekansı, gözlenen taşıyıcı frekansı, OBW %99, alt/üst
   OBW frekansı, kanal gücü, tepe bin gücü, SNR ve modülasyon kategorisi kalite
   durumuyla birlikte gösterilir.
5. Kalite kapısı geçmezse sayı yerine neden gösterilir.

## Akış 4 — Analog dinleme

1. Operatör doğrulanmış bir tespit seçer.
2. AM veya NFM demodülasyonunu ve kanal bant genişliğini açıkça seçer.
3. `Dinle` ile bounded I/Q aralığı hazırlanır.
4. Ses aygıtı yoksa WAV dışa aktarma ayrı ve dürüst biçimde kullanılabilir kalır.
5. Kaynak veya tespit değişirse eski ses sonucu geçersizleşir.

## Akış 5 — Yön bulma ve harita

1. Operatör frekansı, anten 0° referansını ve anten dönüş açısını belirler.
2. Her saha ölçümü açı, dBFS güç, zaman ve kaynakla kaydedilir.
3. Yeterli ölçüm yoksa kerteriz sonucu üretilmez.
4. Önce `Bağıl Geliş Açısı` hesaplanır.
5. Geçerli `Anten Referans Yönü` varsa `Gerçek Kuzeye Göre Kerteriz` hesaplanır.
6. Geçerli konum çözümü de varsa haritada `Kerteriz Hattı (LOB)` çizilir.

Harita hiçbir zaman LOB'u hedef konumu veya menzil olarak sunmaz. Faz uyumlu çok
kanallı DoA sonucu yoktur ve varmış gibi bir kontrol gösterilmez.

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
- `Hareketi azalt` sistem ayarı desteklenir.
- Veri güncellemesi hedefi 10 Hz'dir; hareketli geçişlerin hedefi 60 Hz olsa da
  hedef donanım ölçümü yapılmadan performans iddiası kurulmaz.
