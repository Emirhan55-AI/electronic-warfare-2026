# Kesintisiz Analog Dinleme İncelemesi — 18 Eylül 2026

## Kapsam ve karar

Bu bakım KTR-4.3'ün analog amatör telsiz kapsamındadır ve yeni faz açmaz.
Sayısal telsiz demodülasyonu/kodeği uygulanmaz. Beş saniyelik canlı pencere,
dinleme süresi yerine kanalı ve FPGA/ARM süreklilik bağını doğrulayan başlangıç
kapısıdır. Açık AM veya NFM seçildikten sonra aynı canlı RX oturumu sürer.

## Veri yolu ve görev paylaşımı

1. HackRF I/Q verisini PC alır ve FPGA/ARM tespit yoluna taşır.
2. PL, mevcut Hann → FFT → güç → OS-CFAR işini sürdürür; bu bakım RTL'yi
   değiştirmez.
3. ARM, aday/confirmed yaşam döngüsünü ve gözlenen kare bağını sürdürür.
4. PC, seçili kanal için beş saniyelik sınırlı I/Q halkasında en az `%95`
   gözlem, en çok sekiz ardışık eksik kare ve tek kanal kapılarını uygular.
5. Kapı geçince PC yalnız daha yeni, sıra numarası ardışık en az 122 kareyi
   yaklaşık 250 ms iş parçaları olarak durum koruyan AM/NFM çözücüye verir.
6. PCM16 hoparlör akışına gönderilir ve dışa aktarım için son yirmi saniyelik
   sınırlı halkada tutulur. Ses tüketicisi yetişemezse akış durur.

Demodülasyon FPGA'de değildir. FPGA tespit için kullanılmaya devam eder;
AM zarfı, NFM faz farkı, ses filtreleme, 48 kHz yeniden örnekleme, AGC, DTMF,
hoparlör ve WAV PC'dedir.

## Süreklilik ve ses işleme

`StreamingAnalogMonitor`, NCO fazını, anti-alias/kanal/ses FIR geçmişlerini,
decimator ve resampler fazlarını, önceki NFM örneğini, 30 Hz DC kesiciyi,
isteğe bağlı 200 Hz konuşma yüksek geçirenini, NFM de-emphasis ve yavaş AGC
durumunu iş parçaları arasında saklar. Böylece parça sınırında yeniden başlayan
filtre geçişi, faz sıçraması veya ses seviyesi pompalaması oluşturulmaz.

Ses kalitesi yalnız algoritmaya bağlı değildir. RF SNR, çok yollu yayılım,
frekans hatası, kanal genişliği, vericinin mikrofonu/sınırlayıcısı ve
pre-emphasis profili de sonucu belirler. Mevcut yol alias bastırma, DC/rumble
kesme, bant sınırlama ve yavaş AGC uygular; kontrollü aynı ses kaynağıyla ham ve
işlenmiş fiziksel karşılaştırma yapılmadan anlaşılabilirlik artışı iddia edilmez.

## Bilinmeyen AM/FM ve analog kod sınırı

`AM / FM Karşılaştırmasını Hazırla`, aynı doğrulanmış beş saniyelik I/Q'yu bir
kez alıp AM ve NFM sonuçlarını birlikte hazırlar; iki ayrı RF denemesi gerekmez.
Bu otomatik sınıflandırıcı değildir. Kesintisiz yol, operatör seçimiyle AM veya
NFM olarak başlar.

Analog kod çözme yalnız DTMF içindir. İki frekans grubu, enerji dominansı,
twist ve en az süre kapıları birlikte geçmedikçe sembol yayımlanmaz. CTCSS/DCS,
5-ton, AFSK/AX.25, ses karıştırıcıları, şifre ve bilinmeyen analog veri bu
değişiklikle çözülmez.

## Tekrarlanabilir doğrulama

```powershell
python -m pytest tests/test_phase05_monitoring.py -q
python -m pytest tests/test_live_ed_session.py -q
python -m pytest tests/test_live_ed_view_model.py -q
python -m pytest tests/test_listening_comparison.py tests/test_app_f_quick_product.py -q
python -m pytest tests/test_operator_listening.py -q
```

18 Eylül 2026 kaynak ağacında ilk beş dosyalık paket `199 passed`, klasik
Qt Widgets dinleme paketi ayrı süreçte `5 passed` sonucunu verdi. Ayrı süreç,
QML testlerinin `QGuiApplication` ve klasik arayüz testlerinin `QApplication`
tekil örnek türlerini aynı Python sürecinde paylaşmaması içindir; ürün işlevini
atlayan bir test seçimi değildir.

Kritik regresyonlar:

- altı saniyelik sentetik NFM girdisi tek parça ve 0,5 saniyelik parçalarla
  bit düzeyinde aynı PCM16 çıktısını verir;
- DTMF `5#` kabul edilir, tek 1 kHz ton reddedilir;
- canlı oturum ilk tam pencereden sonra yalnız yeni kareleri verir;
- beş saniyelik halka kadar geriye düşen tüketiciye `sequence_gap` döner;
- canlı dinleme başlatılınca RX oturumu açık kalır ve seçim kilidi korunur;
- zamansal/frekanssal iz, süreklilik ve DTMF durumu ürün modeline taşınır.

## Açık fiziksel kabul

- gerçek analog amatör telsiz konuşmasıyla uzun süreli kesintisiz koşu;
- hoparlör uçtan uca gecikmesi, dropout ve işleme payı ölçümü;
- kontrollü kapalı/açık/kapalı tekrar ve yanlış kanal negatifi;
- bilinen ses kaynağıyla anlaşılabilirlik/kalite karşılaştırması;
- verici pre-emphasis profiline göre doğru de-emphasis seçimi;
- DTMF'nin gerçek RF üzerinden pozitif ve konuşma üzerinde yanlış-pozitif testi.

Bu kapılar tamamlanmadan “tam fiziksel KTR-4.3 kabulü” veya “her analog kodu
çözer” iddiası kullanılamaz.
