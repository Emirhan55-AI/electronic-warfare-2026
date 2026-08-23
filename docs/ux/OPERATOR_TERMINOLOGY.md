# Operatör Arayüzü Terim Sözlüğü

- Sürüm: 1.0
- Dondurma tarihi: 2026-08-23
- Kapsam: Ürün uygulaması ve ayrı doğrulama uygulamasındaki kullanıcı metinleri

## Yazım ilkeleri

- Kullanıcı metinleri Türkçe ve UTF-8 yazılır. Yerleşik teknik kısaltmalar ilk
  kullanımda açık adıyla birlikte verilebilir.
- Bir değer ölçülmediyse `—`, bir yetenek bağlanmadıysa `Bağlı değil`, bir işlem
  çalıştırılmadıysa `Çalıştırılmadı` gösterilir.
- Algoritma, donanım ve kaynak niteliği birbirinden ayrı gösterilir. Kaydın
  işlenmesi canlı RF alımı olarak sunulmaz.
- Dahili faz adı, sınıf adı, backend adı ve fixture kimliği birincil görev
  ekranında gösterilmez. Bunlar yalnız teknik ayrıntı veya doğrulama günlüğünde
  bulunabilir.
- Uygulanmamış bir yetenek için pasif kontrol, rezerve seçenek veya örnek sonuç
  oluşturulmaz.

## Dondurulmuş terimler

| Kavram | Kullanıcıya gösterilecek terim | Anlam ve kullanım sınırı |
|---|---|---|
| Signal detection | `Sinyal Tespiti` | Gürültü eşiğini geçen aday RF bölgelerinin bulunması |
| Candidate | `Aday` | Henüz zamansal doğrulamayı tamamlamamış tespit |
| Confirmed detection | `Doğrulanmış tespit` / durum olarak `Doğrulandı` | Zamansal kabul koşullarını karşılayan tespit; kimlik veya yayın türü doğrulaması değildir |
| Spectrum | `Spektrum` | Anlık ya da açıkça belirtilmiş ortalamalı frekans alanı görünümü |
| Spectrogram | `Spektrogram` | Zaman–frekans güç geçmişi; `şelale` birincil terim olarak kullanılmaz |
| Occupied bandwidth | `İşgal Edilen Bant Genişliği (OBW %99)` | Kalite kapıları geçen ölçüm; kaba aday aralığıyla karıştırılmaz |
| Direction finding | `Yön Bulma (DF)` | Sinyal geliş doğrultusunun kestirimi |
| Relative angle | `Bağıl Geliş Açısı (°)` | Antenin tanımlı 0° eksenine göre geliş açısı |
| Antenna reference direction | `Anten Referans Yönü (°)` | Antenin 0° ekseninin gerçek kuzeye göre yönü |
| True bearing | `Gerçek Kuzeye Göre Kerteriz (°)` | Yalnız geçerli anten referans yönü varsa hesaplanır |
| Line of bearing | `Kerteriz Hattı (LOB)` | Sensörden çıkan doğrultu; hedef konumu veya menzil sonucu değildir |
| Position fix | `Konum Çözümü` | Kaynak, zaman ve doğruluk bilgisiyle birlikte gösterilen konum |
| Recorded source | `SigMF Kaydı` | Dosyadan okunan I/Q kaynağı |
| Playback state | `Kayıt Oynatma` | Kayıt karelerinin zaman sıralı işlenmesi |
| Software reference | `Yazılım Referans Verisi` | Yalnız doğrulama uygulamasında; fiziksel ölçüm değildir |
| Live receiver | `HackRF Canlı RX` | Yalnız gerçek cihaz ve kabul edilmiş alım zinciri bağlıysa |
| Uncalibrated power | `dBFS` | RF giriş gücü olarak `dBm` iddia edilmez |

## Kaldırılan ifadeler

| Kaldırılan ifade | Karşılık veya karar |
|---|---|
| `Coğrafi Azimut` | `Gerçek Kuzeye Göre Kerteriz`; referans yoksa yalnız `Bağıl Geliş Açısı` |
| `Manuel Baş` | `Anten Referans Yönü` |
| `Yön çizgisi` | `Kerteriz Hattı (LOB)` |
| `HOST/SYNTHETIC` | Kullanıcı metninde `Yazılım Referans Verisi`; ürün paketinde bulunmaz |
| `REPLAY` | Kullanıcı metninde `Kayıt Oynatma` veya `SigMF Kaydı` |
| `Eğitim` | Doğrulama uygulamasında `Doğrulama`; ürün paketinde bulunmaz |
| `Otomatik öneri` | Deterministik kaynak bağını belirten `Tespit aralığı` |
| `LIVE GNSS — rezerve` | Kontrol tamamen kaldırılır; gerçek entegrasyon olmadan gösterilmez |

## Kaynaklar

- ITU-R SM.1600, yön bulma istasyonlarında doğruluk ve kerteriz kavramları:
  <https://www.itu.int/rec/R-REC-SM.1600>
- GNU Radio Companion ve QT GUI bileşenleri:
  <https://wiki.gnuradio.org/index.php?title=GNU_Radio_Companion>,
  <https://www.gnuradio.org/doc/doxygen/page_qtgui.html>
- u-blox u-center kullanıcı kılavuzu:
  <https://content.u-blox.com/sites/default/files/u-center_Userguide_UBX-13005250.pdf>
- KrakenSDR DoA uygulaması:
  <https://github.com/krakenrf/krakensdr_doa>
