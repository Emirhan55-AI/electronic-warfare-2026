# Analog Dinleme Sözleşmesi

## Giriş ve sahiplik

Zincir `SigMF/test I/Q → PHASE-02 FFT/PSD → PHASE-03 tespit → confirmed temporal olay → PHASE-04 parametre ölçümü → operatör seçimi → AM/NFM demodülasyon → 48 kHz mono PCM16` sırasındadır. Eski doğrudan API, kayıtlı fixture regresyonu için confirmed olaydan başlayabilir; yarışma ürün akışı parametre sonucunu dinlemeye devreder. Operatör demodülasyonu açıkça seçer ve önerilen merkez ofseti ile kanal genişliğini değiştirebilir. Ground truth, aile veya SNR etiketi runtime kararına girmez.

İstek kaynak, pipeline, yapılandırma, event kimliği/revizyonu ve başlangıç frame'iyle bağlanır. Kaynak, profil, Pfa, merkez politikası, DC ayarı, event veya dinleme ayarı değişince hazırlanmış ses silinir. Stale sonuç UI'ya uygulanmaz.

## DSP ve sınırlar

- Giriş: gerçek kaynakta en fazla `20` saniyelik kesintisiz tek kanallı kompleks I/Q; test fixture uyumluluğu için dört frame'lik eski yol korunur.
- DDC: global birleşik örnek indisiyle kompleks frekans öteleme; NCO fazı blok sınırında korunur.
- Kanal filtresi: `129` tap anti-alias ve `129` tap kanal FIR'ı; iki filtre delay-line durumu ve decimator fazı blok sınırında korunur.
- AM: filtrelenmiş kompleks zarf.
- NFM: ardışık filtrelenmiş örneklerin `angle(x[n]·conj(x[n−1]))` faz farkı; önceki kompleks örnek blok sınırında korunur. Kesintisiz ürün yolunda ardından 6 dB/oktav alıcı de-emphasis için varsayılan `750 µs` birinci derece filtre uygulanır; zaman sabiti yapılandırma sözleşmesindedir. Dört karelik eski fixture önizlemesi tarihsel golden çıktıyı korur ve de-emphasis içermez.
- Yeniden örnekleme: anti-alias kanal filtresinden sonra deterministik doğrusal zaman ızgarası; çıkış tam `48.000 Hz`.
- Ses filtresi: kesintisiz ürün yolunda kanal aralığına göre NFM'de `2,55/3 kHz`, AM'de `3 kHz` kesimli `65` tap bounded alçak geçiren filtre ve DC giderimi. Dört karelik fixture önizlemesi tarihsel geniş kesimi korur.
- PCM: mono signed little-endian PCM16; normalizasyon yalnız dinleme içindir, taşma kırpma öncesi sayılır ve zorunlu kapıda sıfırdır.
- I/Q blok üst sınırı: `20` saniye; UI worker'ı kaydı yaklaşık `250 ms` kesintisiz okuma bloklarıyla işler.
- Canlı ürün girişi: host kanal seçicisinin karta gönderilmiş ve yanıtı
  doğrulanmış 2 MS/s CI8 kareleri; FPGA'nın geri döndürdüğü I/Q değildir.
  `2.442 × 4.096` kompleks örnek, `5,001216` saniye ve yaklaşık `19,1 MiB`
  sınırlı ring tamponudur. Sıra boşluğu tamponu temizler. Seçili olay bütün
  pencere boyunca ARM'da `confirmed` kalmalıdır. Tek karelik CFAR salınımının
  gerçek konuşmayı düşürmemesi için gözlenen kare oranı en az `%95`, ardışık
  gözlenmeme en çok `8` kare (`16,384 ms`) olabilir. Olayın confirmed listesinden
  çıkması pencereyi hemen geçersiz kılar; yalnız toplam gözlem sayısı yetmez.
- Ses ring/WAV üst sınırı: `20 saniye`, `960.000` mono örnek.
- Kanal izleme: filtrelenmiş I/Q üzerinde `250 ms` pencereler. Güç
  `10 log10(mean(|x|²)) dBFS`; DDC sonrasındaki artık merkez frekansı
  `angle(sum(x[n]·conj(x[n−1]))) Fs/(2π)` ile ölçülür. Tek blok ve parçalı
  girdi aynı PCM, güç ve frekans dizisini üretmelidir.
- PHASE-03 event sınırı `64`; worker/pending sınırı `1/1` kalır.

Nyquist dışı kanal, yetersiz kesintisiz I/Q, geçersiz oran, desteklenmeyen demodülasyon, NaN/Inf ve stale nesil typed hata üretir. I/Q okuma, DSP ve WAV yazımı UI thread'inde yapılmaz.

## Project-internal kapılar

Clean AM/NFM fixture'larında 48 kHz çıkış, sonlu değerler, sıfır PCM taşması, en fazla bir değerlendirme FFT bini ton hatası ve gecikme/kazanç hizalı korelasyon `≥0,95` zorunludur. Sabit `20 dB` sentetik SNR'de korelasyon `≥0,80`, ton hatası en fazla iki bindir. Aynı giriş iki çalıştırmada aynı ölçüm ve PCM üretir. Noise-only kayıtta confirmed olay yoksa dinleme etkinleşmez. Bu değerler şartname performans eşiği değil `project_internal` yazılım kapılarıdır.

## UI ve donanım sınırı

`Dinleme` çalışma alanı seçili kaynak/olay, `AM / Dar Bant FM`, merkez ofseti, kanal genişliği, ses seviyesi, güç/frekans davranışı, hazırlama, oynatma ve WAV kontrollerini gösterir. Parametre ölçümündeki emisyon merkezi ile OBW dinleme önerisine aktarılır; canlı kaynak aynı frekanstaki sinyali yeni FPGA oturumunda yeniden doğrular. Operatör önerileri değiştirebilir. Canlı hazırla komutu immutable beş saniyelik pencereyi sabitler, RX oturumunu iptal yaşam döngüsüyle kapatır ve demodülasyonu worker üzerinde başlatır; yakalama ile ağır DSP aynı anda çalışmaz. Fixture ve mock kaynak `Deterministik test kaynağı — canlı RF değildir` olarak işaretlenir. QtMultimedia çıkışı yoksa oynatma pasif kalır, WAV çalışır. Haricî ISM kaydına modülasyon veya yayın türü atanmaz. Kontrollü AM/NFM RF ve fiziksel ses kabulü olmadan gerçek canlı HackRF dinleme başarısı iddia edilmez.
