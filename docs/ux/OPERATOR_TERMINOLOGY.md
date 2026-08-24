# Operatör Arayüzü Terim Sözlüğü

- Sürüm: 1.1
- Dondurma tarihi: 2026-08-24
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
| Emission centre frequency | `Emisyon Merkez Frekansı` | Gürültü etkisi giderilmiş spektral gücün birinci momenti; taşıyıcı frekansı değildir |
| Observed carrier frequency | `Gözlenen Taşıyıcı Frekansı` | Yalnız yeterli dar çizgi kanıtında gösterilir; bastırılmış veya çizgisiz taşıyıcıda sayı üretilmez |
| Occupied bandwidth | `İşgal Edilen Bant Genişliği (OBW, %99)` | Kalite kapıları geçen ölçüm; kaba aday aralığı, gerekli bant veya kanal bant genişliği değildir |
| Lower/upper OBW frequency | `Alt OBW Frekansı` / `Üst OBW Frekansı` | %0,5 ve %99,5 kümülatif güç noktaları |
| Channel power | `Kanal Gücü` | Onaylı ölçüm aralığında bütünleştirilen güç; kalibrasyon yoksa dBFS |
| Peak bin power | `Tepe Bin Gücü` | En güçlü FFT bininin gücü; dBFS/bin değeri toplam kanal gücü değildir |
| Signal-to-noise ratio | `SNR` | İlk kullanım veya araç ipucunda `Sinyal-Gürültü Oranı`; birim dB |
| Analogue/digital category | `Modülasyon Kategorisi` | Yalnız `Analog`, `Sayısal` veya `Belirsiz`; modülasyon türü tanıma sonucu değildir |
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
| `Yayın merkezi` | `Emisyon Merkez Frekansı` |
| `Taşıyıcı Çizgisi Frekansı` | Kullanıcı metninde `Gözlenen Taşıyıcı Frekansı`; iç sözleşmede çizgi kanıtı korunur |
| `Alt sınır` / `Üst sınır` | `Alt OBW Frekansı` / `Üst OBW Frekansı` |
| `Tepe güç` | Birim dBFS/bin ise `Tepe Bin Gücü` |
| `Sinyal alanı` | `Modülasyon Kategorisi` |
| `Kalibrasyon bekliyor` | `Güç Referansı: Kalibre edilmemiş (dBFS)`; gelecekte yapılacak iş izlenimi verilmez |

## Kaynak ve karar dayanakları

- ITU-R SM.443-3, ölçüm ayarı için `estimated centre frequency of the emission`
  ifadesini; ITU-R SM.1541-6, emisyon merkez frekansı ile %99 OBW alt/üst güç
  noktalarını kullanır:
  <https://www.itu.int/dms_pubrec/itu-r/rec/sm/R-REC-SM.443-3-200504-S%21%21PDF-E.pdf>,
  <https://www.itu.int/dms_pubrec/itu-r/rec/sm/R-REC-SM.1541-6-201508-S%21%21PDF-E.pdf>
- ETSI TS 138 101-2 ve TS 138 181, OBW'yi toplam bütünleştirilmiş ortalama
  gücün %99'unu kapsayan bant olarak tanımlar; iki tarafta %0,5 güç dışarıda
  kalır:
  <https://www.etsi.org/deliver/etsi_ts/138100_138199/13810102/16.19.00_60/ts_13810102v161900p.pdf>,
  <https://www.etsi.org/deliver/etsi_ts/138100_138199/138181/18.09.00_60/ts_138181v180900p.pdf>
- Keysight 89600B OBW çıktıları `Centroid Frequency`, `Lower Frequency`, `Upper
  Frequency`, `Occupied Bandwidth` ve `OBW Power` alanlarını ayrı ölçüler olarak
  sunar:
  <https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/gui/content/trc_marker.htm>
- GNU Radio QT GUI, `Waterfall` ve `spectrogram` ifadelerini eş anlamlı kullanır;
  frekans alanı, zaman alanı ve spektrogramı ayrı görünümler olarak sunar:
  <https://wiki.gnuradio.org/index.php/QT_GUI>,
  <https://wiki.gnuradio.org/index.php/QT_GUI_Waterfall_Sink>
- ITU-R SM.2140, yön bulma ölçümlerinde `bearing` ve `Line of Bearing (LoB)`
  terimlerini kullanır. Ulaştırma ve Altyapı Bakanlığı görev koordinasyon
  kılavuzundaki Türkçe kullanım `kerteriz hattı`dır:
  <https://www.itu.int/dms_pubrec/itu-r/rec/sm/R-REC-SM.2140-0-202108-I%21%21PDF-E.pdf>,
  <https://denizcilik.uab.gov.tr/uploads/pages/aakkm-mevzuat/cilt-ii-gorev-koordinasyon.pdf>
- KrakenSDR, anten dizisine göre bağıl yön ile pusula/harita referanslı kerterizi
  ayırır; çoklu kerterizlerin kesişimini konum için kullanır:
  <https://www.krakenrf.com/about-krakensdr>
- MathWorks Communications Toolbox, analog ve sayısal ayrımı `modulation
  classification` altında ele alır. Bu proje belirli bir modülasyon türü
  tanımadığı için kullanıcı metni daha dar olan `Modülasyon Kategorisi` ile
  sınırlandırılır:
  <https://www.mathworks.com/help/comm/modulation.html>
