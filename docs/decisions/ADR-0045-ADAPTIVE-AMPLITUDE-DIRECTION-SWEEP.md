# ADR-0045 — Uyarlamalı Genlik Tabanlı Yön Taraması

- Durum: Kabul edildi
- Tarih: 16 Eylül 2026
- Kapsam: KTR-4.4 / PHASE-09 manuel yönlü anten iş akışı
- Önceki kararlar: ADR-0008 ve tarihsel `P0_AMPLITUDE_DF_FIELD_V1`

## Uygulama eki — 18 Eylül 2026

P0DF-v1 kaynak kare alanı 32 bittir. PC'nin RX oturum kuşağını üst 32 bite
yerleştiren önceki uygulaması, uyarlamalı taramanın son isteğini paketleme
aşamasında durduruyordu. Güncel uygulama özgün RX kimliğini kanıt kaydında
korur; P0DF için ölçüm sırası ve kaynak kareden çakışmasız tarama-yerel uint32
belirteci üretir. Başarısız son hesap ölçümleri silmez ve yalnız ARM kararı
yeniden denenebilir.

Arayüz kararı da netleştirilmiştir: `0°` ilk ölçümdeki fiziksel anten eksenidir.
Coğrafi referans yoksa yön yalnız bu eksene göre derece ve antene bağlı sektör
olarak sunulur. Ham maksimum `ölçüm adayı`, yalnız ARM `LOB HAZIR` sonucu
doğrulanmış bağıl yöndür. Kontrollü bilinen yön koşuları olmadan `Derece RMS`
değeri yayımlanmaz.

## Bağlam

Yönlü anten ana lobdan uzaklaştırıldığında hedefin FPGA tespit eşiğinin altına
inmesi beklenen fiziksel davranıştır. Bütün 360° boyunca 15° adımlı 24 ayrı
tespit istemek, yayın ana lob dışında görünmediğinde operatörü gereksiz tam tura
zorlar ve anten açıklığının sınır bilgisini hata gibi sunar.

## Karar

1. İlk doğrulanmış ölçüm operatörün seçtiği `0°` başlangıcını ve hedef kanalını
   kilitler.
2. Anten saat yönünde 15° adımlarla hedefin dört karenin hiçbirinde görülmediği
   ilk noktaya kadar çevrilir. Bu nokta sağ lob dışı sınırdır.
3. Operatör anteni fiziksel olarak `0°`a geri getirir. 345°, 330°, … etiketleri
   başlangıçtan saat yönünün tersine 15°, 30°, … dönüşleri temsil eder. İlk
   gözlemsiz nokta sol lob dışı sınırdır.
4. Lob dışı sınırlar başarısız ölçüm değildir. Aynı kilitli kanalın P0PM-v4
   sinyal + alıcı gürültüsü toplam dBFS değeri ve hedef gözlem maskesi saklanır.
5. İki sınır arasındaki en güçlü kaba nokta 5° komşuluklarla hassaslaştırılır.
   Yalnız ölçülmüş açılardan ham maksimum seçilir; interpolasyon yapılmaz.
6. Tek karşı-yön ölçümü 3 dB ön/arka belirsizliği kapısını besler. En az sekiz
   farklı açı, 3 dB rakip tepe, sabit hedef/alıcı bağı ve aynı-kare reddi
   korunur.
7. PC açı sırasını planlar; ZedBoard ARM nihai P0DF kararını verir. Tel protokol
   P0DF-v1/P0FR-v1 olarak kalır, ürün profili
   `P0_AMPLITUDE_DF_ADAPTIVE_V2` olur.

## Sonuç ve sınırlar

Operatör yalnız yayın görülen açıklığın iki yanını ve tepe çevresini tarar;
tam 360° tur zorunlu değildir. Sinyalin kaybolduğu nokta doğrudan vericinin
konumu değildir, yalnız bu anten/alıcı/ortam düzeninde ana lob dışına geçiş
gözlemidir. Çok yollu yayılım, polarizasyon, yakın alan ve mekanik açı hatası
kontrollü fiziksel derece RMS deneyi olmadan çözülmüş sayılmaz. Tarihsel 24-açı
kanıtları korunur ve yeni profile aktarılmaz.
