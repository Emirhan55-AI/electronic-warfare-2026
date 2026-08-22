# Analog Dinleme Sözleşmesi

## Giriş ve sahiplik

Zincir `SigMF/test I/Q → PHASE-02 FFT/PSD → PHASE-03 regional tespit → confirmed temporal olay → operatör seçimi → AM/NFM demodülasyon → 48 kHz mono PCM16` sırasındadır. PHASE-04 frekans, OBW99 veya sınıflandırma sonucu zorunlu değildir. Operatör demodülasyonu açıkça seçer ve event tepesinden önerilen merkez ofsetini ile kanal genişliğini değiştirebilir. Ground truth, aile veya SNR etiketi runtime kararına girmez.

İstek kaynak, pipeline, yapılandırma, event kimliği/revizyonu ve başlangıç frame'iyle bağlanır. Kaynak, profil, Pfa, merkez politikası, DC ayarı, event veya dinleme ayarı değişince hazırlanmış ses silinir. Stale sonuç UI'ya uygulanmaz.

## DSP ve sınırlar

- Giriş: gerçek kaynakta en fazla `20` saniyelik kesintisiz tek kanallı kompleks I/Q; test fixture uyumluluğu için dört frame'lik eski yol korunur.
- DDC: global birleşik örnek indisiyle kompleks frekans öteleme; NCO fazı blok sınırında korunur.
- Kanal filtresi: `129` tap anti-alias ve `129` tap kanal FIR'ı; iki filtre delay-line durumu ve decimator fazı blok sınırında korunur.
- AM: filtrelenmiş kompleks zarf.
- NFM: ardışık filtrelenmiş örneklerin `angle(x[n]·conj(x[n−1]))` faz farkı; önceki kompleks örnek blok sınırında korunur.
- Yeniden örnekleme: anti-alias kanal filtresinden sonra deterministik doğrusal zaman ızgarası; çıkış tam `48.000 Hz`.
- Ses filtresi: `65` tap bounded alçak geçiren filtre ve DC giderimi.
- PCM: mono signed little-endian PCM16; normalizasyon yalnız dinleme içindir, taşma kırpma öncesi sayılır ve zorunlu kapıda sıfırdır.
- I/Q blok üst sınırı: `20` saniye; UI worker'ı kaydı birer saniyelik kesintisiz okuma bloklarıyla işler.
- Ses ring/WAV üst sınırı: `20 saniye`, `960.000` mono örnek.
- PHASE-03 event sınırı `64`; worker/pending sınırı `1/1` kalır.

Nyquist dışı kanal, yetersiz kesintisiz I/Q, geçersiz oran, desteklenmeyen demodülasyon, NaN/Inf ve stale nesil typed hata üretir. I/Q okuma, DSP ve WAV yazımı UI thread'inde yapılmaz.

## Project-internal kapılar

Clean AM/NFM fixture'larında 48 kHz çıkış, sonlu değerler, sıfır PCM taşması, en fazla bir değerlendirme FFT bini ton hatası ve gecikme/kazanç hizalı korelasyon `≥0,95` zorunludur. Sabit `20 dB` sentetik SNR'de korelasyon `≥0,80`, ton hatası en fazla iki bindir. Aynı giriş iki çalıştırmada aynı ölçüm ve PCM üretir. Noise-only kayıtta confirmed olay yoksa dinleme etkinleşmez. Bu değerler şartname performans eşiği değil `project_internal` yazılım kapılarıdır.

## UI ve donanım sınırı

`Dinleme` çalışma alanı seçili kaynak/olay, `AM / Dar Bant FM`, merkez ofseti, kanal genişliği, ses seviyesi, hazırlama, oynatma ve WAV kontrollerini gösterir. Operatör spektrum üzerindeki taşıyıcı tepesine tıklayarak merkez ofsetini seçebilir; NFM kanal seçenekleri `12,5` ve `25` kHz aralığındadır. Fixture ve mock kaynak `Deterministik test kaynağı — canlı RF değildir` olarak işaretlenir. QtMultimedia çıkışı yoksa oynatma pasif kalır, WAV çalışır. Haricî ISM kaydına modülasyon veya yayın türü atanmaz; gerçek canlı HackRF dinleme uygulanmış sayılmaz.
