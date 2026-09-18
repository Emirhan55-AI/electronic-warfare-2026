# Sinyal izleme/dinleme incelemesi — 16 Eylül 2026

Kapsam mevcut PHASE-08 içindeki KTR-4.3 ürün devamıdır. Yeni faz veya fiziksel
kabul açılmaz. PL/ARM/RTL ve alıcı süreklilik kapıları bu değişiklikte korunur.

## Gereksinim karşılığı

| Şartname beklentisi | Kaynakta bulunan yetenek | Sınır |
|---|---|---|
| Yayının sürekliliğini takip | FPGA olay bağı, en az %95 gözlem, en çok 8 ardışık eksik kare | Ses hazırlığı son beş saniyeyi sabitleyip RX'i durdurur; kesintisiz ses akışı yok |
| Zamansal/frekanssal davranış | Kaydın 250 ms güç ve artık frekans dizileri | Sınırlı kayıt penceresi; bütün modülasyonlarda taşıyıcı doğruluğu kabulü değil |
| Demodülasyon ve ses | Gerçek I/Q için AM zarfı ve dar bant FM faz farkı; PCM16/WAV | Genel AM/FM tanıma, WFM, SSB veya sayısal protokol çözümü yok |
| Varsa kod çözümü/veri | Uygulanmadı | Ses çıkmaması şifreleme kanıtı değildir |

13 Eylül 820 MHz NFM ton koşusu tarihsel fiziksel kanıttır; yeni kaynak,
gerçek konuşma anlaşılabilirliği ve genel KTR-4.3 kabulü yerine geçmez.
Güncel ayrıntı [dinleme durumu](../interfaces/SIGNAL_MONITORING_LISTENING_STATUS.md).

## Yapılan değişiklik

- `Bilmiyorum · AM/FM karşılaştır`, aynı I/Q ve aynı frekans/kanal ayarlarından
  iki sonuç üretir. Sonuç seçimi ses, dalga biçimi, izleme grafiği ve WAV
  kaynağını birlikte değiştirir. Tür kararı veya güven yüzdesi üretilmez.
  Bir dalın yetersiz ses hatası diğer dalı engellemez; bozuk I/Q gizlenmez.
- Frekans ofseti ve de-emphasis ince ayara taşındı. Kanal genişliği dar/orta/
  geniş seçeneklerle sunulur. Ölçülen OBW 25 kHz üstündeyse kapsam uyarılır.
  Sınırlandırılmış kanal önerisi ölçülmüş OBW diye adlandırılmaz.
- İsteğe bağlı konuşma filtresi, mevcut ses alçak geçiren süzgecine ek olarak
  200 Hz kesimli 1025 tap Hamming FIR yüksek geçiren süzgeç uygular. Birleşik
  sese normalizasyon öncesi bir kez uygulanır. RF güç/frekans dizileri değişmez.
  Filtre API'de varsayılan kapalı, ürün arayüzünde başlangıçta seçilidir.
  Gürültüyle örtüşen konuşmayı ayıran bir yöntem değildir.
- Sonuç etiketi `Çözümleme` oldu: operatörün seçtiği yöntem, belirlenmiş yayın
  türü olarak sunulmaz. Canlı yakalama durduğunda eski kayıt dinlendiği açıklanır.

## Ölçüm ve tekrar

48 kHz'de bir saniyelik eş genlikli 50/100/300/1000/2500 Hz toplamına filtre
uygulandı. Kenarlardan 100 ms çıkarılarak her bileşen bağımsız kompleks DFT
izdüşümüyle ölçüldü. Normalizasyon öncesi kazançlar:

| Frekans | Kazanç |
|---|---|
| 50 Hz | −50,2967 dB |
| 100 Hz | −50,2403 dB |
| 300 Hz | +0,0118 dB |
| 1000 Hz | +0,0049 dB |
| 2500 Hz | +0,0019 dB |

Bu noktalar için kapılar: 50/100 Hz'de en az 40 dB bastırma, üç konuşma
bileşeninde 0,2 dB'den küçük kazanç değişimi. Beş saniyelik AM/NFM için
100 Hz/1000 Hz oranı en az 50 kat azalır, PCM kırpılması sıfırdır ve tek blok
ile 4096 örnekli blokların PCM sonuçları aynıdır. Eski temiz/gürültülü AM/NFM,
de-emphasis, alias reddi ve bilinen frekans kayması kapıları da korunur.

```powershell
python scripts/verify_listening_voice_filter.py
python -m pytest tests/test_listening_comparison.py tests/test_phase05_monitoring.py tests/test_live_ed_view_model.py tests/test_app_f_quick_product.py -q -k 'listening or comparison or Phase05MonitoringTests' --tb=short
```

Sonuç: **24 geçti**, 126 kapsam dışı test seçilmedi. Gerçek QML'de varsayılan
bilinmeyen tür seçimi, beş argümanlı hazırlama düğmesi, filtre seçiminin DSP'ye
ulaşması, sonuç değiştirme, kaynak temizliği ve geniş bant uyarısı doğrulandı.
1440×900 ekran görsel olarak incelendi. Fiziksel RF veya hoparlör anlaşılabilirliği
bu çalışmada denenmedi. Kaynak özetleri ve filtre ölçümlerinin anlık kaydı
`results/evidence/phase05/listening-assistance-20260916.json` içindedir.

İlk geniş regresyon sırasında paralel değişen çalışma alanında parametre paneli
etiketleri/eski doğrulama başlıkları ile yön ölçümündeki boş seçimin
`quick_measurement_actions.py` içinde indekslenmesi hataları görüldü. Bu kayıt
bütün depo testlerinin geçtiği iddiası değildir; o kapsamlar değiştirilmedi.
Dinleme testi beklentileri yeni `Çözümleme` ve `Sesi Hazırla` etiketlerine uyarlandı.

## Yöntem kaynakları

AM zarf ve FM faz farkı yerleşik yöntemlerdir; yöntemin varlığı otomatik yayın
tanıma veya fiziksel doğruluk kanıtı değildir:
[GNU Radio AM Demod](https://wiki.gnuradio.org/index.php?title=AM_Demod),
[GNU Radio Quadrature Demod](https://wiki.gnuradio.org/index.php?title=Quadrature_Demod).
Örnek azaltma öncesinde bant sınırlamanın gerekçesi için
[SciPy yeniden örnekleme açıklaması](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html).
Ürün kodu bu değişiklikte NumPy FIR yolunu kullanmaya devam eder.
