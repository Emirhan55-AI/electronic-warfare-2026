# PortaPack Replay parametre deneyi

## Dört parametrenin gerçek RF durumu — 9 Eylül 2026

KTR-4.2 / KTR-4.2-F1: son donanım beyanı yalnız iki HackRF'dir;
aşağıdaki tarihsel osiloskop/üreteç bilgisi güncel erişim varsayımı değildir.
Yeni AM bağlantısı taşmasız/kırpılmasız ve ana bantta yeterli SNR ile kaydedildi;
sabit sınıflandırıcı hâlâ Belirsiz kaldığı için aynı AM adımı tekrarlanmaz.
Son BPSK alıcı penceresi Play basışıyla kesin eşleşmedi. Bu negatif pencere
kaynak başarısızlığı değildir. Yeni fiziksel denemede operatöre kalan süresi
belirsiz kısa kayıt penceresi üzerinden tekrar Play komutu verilmez; alıcı
hazırlığı ve tek sonlu yayının eşleşmesi önce çözülür. Mevcut kayıtlarla
yöntem geliştirmesi sürer. dBm eksikliği diğer alanları durdurmaz.

[Ayrıntılı durum, araştırma ve yeniden üretim](../reviews/PARAMETER_EXTRACTION_ASSESSMENT.md).


KTR-4.2 / KTR-4.2-F1; PÇ-02/03 kaynak hazırlığı. Bu paket RF ölçümü,
kalibrasyon, ürün veya ARM/FPGA kabulü değildir. Önceki kanıtlar korunur.

## Şimdi yapılacaklar

1. Vericide yayını durdurun. `PARAMTEST_SD.zip` arşivini bilgisayarda açın.
2. İçindeki `CAPTURES/PARAMTEST` klasörünü microSD kartın
   `CAPTURES/PARAMTEST` yoluna kopyalayın. Her `.C16` dosyasının yanındaki
   aynı adlı `.TXT` dosyasını da kopyalayın. Mevcut dosyaları silmeyin.
3. Kartı güvenle çıkarıp PortaPack'e takın. Mayhem sürümünü ve cihazın
   mevcut bilgi ekranında görülebiliyorsa verici seri numarasını kaydedin.
   Görünmüyorsa tahmin etmeyin; kimlik doğrulaması sonraki kayıt öncesinde çözülür.
4. `Transmit → Replay` içinde yalnız `00_CW.C16` dosyasını seçin.
   Liste kullanılan sürümde varsa başka dosya eklemeyin.
5. Ekranda **825.000 MHz**, dosya örnekleme hızı **500 kHz / 500000**,
   süre **2 saniye**, **TX Gain 0**, **Amp 0 / kapalı**, **Loop kapalı**
   olduğunu kontrol edin. 500 kHz dosyanın hızıdır; dahili DAC hızıyla
   aynı olmak zorunda değildir. Ekran farklıysa oynatmayın.
6. **Henüz Play'e basmayın.** Alıcıda önce verici kapalı kaydı alınacak.
   Hazır olduğunda “dosyalar yüklendi, CW seçili, yayın kapalı” diye bildirin;
   Mayhem sürümünü de yazın. Kayıt hazırlandıktan sonra tek basışla sonlu
   deneme yapılacak. İlk koşuda Stop ve dosya sonunda durma doğrulanacak.

Deney mevcut onaylı kapalı Faraday kabininde yürür. İki RF portunu
zayıflatmasız doğrudan kabloyla bağlamayın. Mevcut kontrollü düzen korunur.
Tek dosya bitince RF'nin kesildiği ayrıca gözlenir; sıfır I/Q örneği veya
ekranda ilerleme çubuğunun bitmesi tek başına RF'nin kapandığını kanıtlamaz.

## Dosyalar ve sıralama

| Dosya | İçerik | Süre |
|---|---|---|
| `00_CW.C16` | Taşıyıcılı ilk bağlantı ve durdurma kontrolü | 2 s |
| `01_AM.C16` | %70 AM, 1,7 kHz mesaj tonu | 6 s |
| `02_NFM.C16` | 1,7 kHz mesaj, 6 kHz tepe frekans sapması | 6 s |
| `03_BPSK.C16` | Rastgele veri, 20 ksembol/s, FIR ile şekillendirilmiş | 6 s |
| `04_QPSK.C16` | Rastgele veri, 20 ksembol/s, FIR ile şekillendirilmiş | 6 s |
| `05_FSK.C16` | Rastgele veri, 20 ksembol/s, ±10 kHz sürekli faz FSK | 6 s |

Tüm dosyaların nominal merkezi 825 MHz'tir. CW kabul edilmeden diğerleri
oynatılmaz. İlk aşamada tek frekans ve tek ayar vardır; farklı bant/hız/SNR
kapsamı sonradan ayrıca sınanır. Altı dosya genel sınıflandırma kabulü değildir.
PSK taşıyıcısı bastırılmıştır; en yüksek çizgiyi taşıyıcı diye değerlendirmeyin.

## Ölçüm tarafı

- Model/eşik sabit kalır; beklenen aile sınıflandırıcıya verilmez.
- Her koşuda dosya özeti, sürüm/cihaz kimliği, gerçek ekran ayarı, alıcı
  seri/kazanç/merkez bilgisi, ham I/Q ve kapalı/açık/kapalı durumu saklanır.
- Önce CW ile kırpılma ve dosya sonunda RF kesilmesi; sonra tek dosya/tek
  başlatma. Alıcı kazancı deneme ortasında değiştirilmez.
- Referans dosya bitleri bilinir; SD oynatma ve RF filtrelerinin etkisi
  ayrıca ölçülür. Dosya OBW'si otomatik olarak yayılan RF OBW'si değildir.
- Rastgele veri hazırlama kodu sınıflandırıcıyı çağırmaz; test dosyaları
  sonucu iyileştirmek için seçilmez veya model eğitimine eklenmez.
- 500 kHz dosya Replay tarafından örnek tekrarıyla üst hıza taşınabilir.
  İlk RF kaydında istenmeyen görüntü bantları ve SD kesintileri denetlenir.

### İlk fiziksel ayar sonucu

CW, G:0/A:0 ve RX 24/24 dB'de taşmasız gözlendi. Doğru AM dosyası aynı
TX ayarında RX 24/24 dB'de 1699,22 Hz zarf tonu verdi; adayın on penceresi
2,04–4,38 dB SNR nedeniyle Belirsiz kaldı. RX'i 32/32 dB'ye yükseltmek
ölçüm SNR'sini artırmadı; gürültü de yükseldi. Bu iki alıcı kazancı model
veya eşik ayarlamak için kullanılmaz.

En düşük TX kazançlı kısa CW bağlantısı tamamlandığı için sonraki kontrollü
AM tanısında Amp kapalı kalmak üzere TX Gain 8 adayı kullanılabilir. Her
kazanç değişimi yeni koşudur; ekranda doğrulanır, RX 24/24 dB'ye döner ve
kırpılma görülürse koşu durdurulur. Bu sınırlı artış güç kalibrasyonu değildir.

## Kalibrasyon

İki HackRF ile göreli frekans farkı ve sabit düzende göreli güç değişimi
ölçülebilir. Hangisinin mutlak frekans hatasına sahip olduğu ve alıcı giriş
gücünün gerçek dBm değeri, yalnız bu karşılaştırmayla belirlenemez.

Mutlak güç için kalibrasyonu geçerli RF üreteci veya gücü RF güç ölçer/
uygun spektrum analizörüyle ölçülmüş kaynak ve kaybı bilinen kablo/zayıflatıcı
gerekir. Referans düzlemi **alıcı RF girişidir**. Her frekans, LNA/VGA/RF
kazancı, örnekleme, filtre ve sayısal ölçek ayarında birkaç güç noktası ölçülür;
ayrı doğrulama noktalarıyla hata ve belirsizlik hesaplanır. Tek sabit ofset
tüm frekans/kazançlara uygulanmaz. Kalibrasyon alanı dışında dBm kapalı kalır.

Mutlak frekans için doğruluğu bilinen RF kaynak veya uygun referansa bağlı
ölçüm gerekir. Ortak 10 MHz saat iki cihazın göreli kaymasını azaltabilir;
referansın doğruluğu bilinmiyorsa mutlak doğruluk sağlamaz. Henüz harici
saat veya RF bağlantısı değiştirmeyin.

Kullanıcıda iki HackRF, dijital osiloskop ve yaklaşık “XG2060, 60 MHz,
500 MSa/s” olarak bildirilen keyfî dalga üreteci vardır. Bu özellikler
OWON XDG2060 ile uyumludur; tam model henüz teyit edilmedi. Üretici XDG2060
için 60 MHz çıkış sınırı bildirir. Bu cihaz doğrulanırsa kendi frekans
aralığında bağımsız kaynak kontrolüne yardımcı olabilir; doğrudan 825 MHz
referansı değildir. Osiloskobun bant genişliği, 50 ohm yük durumu ve cihazların
kalibrasyon durumu bilinmeden mutlak güç doğruluğu iddia edilmez. Kullanıcının
tercihiyle bu oturum iki HackRF ve Replay dosyalarıyla sürer.
[OWON XDG2000 özellikleri](https://in.owon.com/products_owon_xdg2000_series_2-ch_arbitrary_waveform_generator)

## Kaynaklar

- [Mayhem Replay](https://github.com/portapack-mayhem/mayhem-firmware/wiki/Replay)
- [C16 ve TXT biçimi](https://github.com/portapack-mayhem/mayhem-firmware/wiki/C16-format)
- [İncelenen Replay C16→C8 ve örnek tekrarı kodu](https://github.com/portapack-mayhem/mayhem-firmware/blob/31b25a445b166b13101ea4c6546f78b84dcc6499/firmware/baseband/proc_replay.cpp)
- [HackRF harici saat arayüzü](https://hackrf.readthedocs.io/en/latest/external_clock_interface.html)

Belgeler 9 Eylül 2026'da incelendi. İncelenen kaynak, vericide yüklü sürümün
doğrulandığı anlamına gelmez. Üretim: `python scripts/prepare_parameter_replay.py
--output build/acceptance/parameter-replay-pack-v2-20260909` (tek satır).
