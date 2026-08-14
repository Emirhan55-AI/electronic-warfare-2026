# Referans Modeller

- `sigmf/`, PHASE-01 metadata ve binary yerleşim sözleşmesini yalnız Python standart kütüphanesiyle doğrular. Örnek değerlerini dönüştürmez ve DSP uygulamaz.
- `spectrum/`, PHASE-02 bounded SigMF çerçeve kaynağını ve Qt'den bağımsız floating-point Hann/FFT/güç/PSD golden modelini içerir.
- `detection/`, PHASE-03 bölgesel/CA/OS detectorlerini, kaba bölge gruplamasını, bounded temporal olay belleğini ve katalog tabanlı sentetik sahneleri içerir.
- `pipeline/`, allowlist bloklarından doğrulanmış işlem profilini kurar; PHASE-04 ve E1 alan-bazlı comparison/digest bağlarını doğrular ve geçersiz bağda PHASE-03 Operasyon zincirine döner.
- `parameters/`, PHASE-04 geçerlilik modeli ve başarısızlık deneylerinin yanında E1 confirmed-olay span önerisini, dört bounded frame ölçümünü, taşıyıcı çizgisi/emisyon merkezi/OBW99/dBFS/sınırlı alan kurallarını ve `34.084 byte` kalıcı payload sınırını içerir. E1 profili yalnız doğrulanan alanları kurabilir; mevcut karşılaştırmada doğrulanan alan yoktur.
- `monitoring/`, operatör seçimli AM/NFM için bounded DDC, FIR kanal süzme, frame-sürekli NFM faz farkı, 48 kHz mono ses, PCM16/WAV ve deterministik fixture/evaluation sözleşmesini içerir.
- `rtl/`, PHASE-06A `ci8` AXI4-Stream frame-istatistik bloğunun yalnız tam sayı kullanan bit-doğru Python golden modelini ve deterministik HDL vektör üretimini içerir.
- `rtl/hann_window.py` ve `rtl/hann_vectors.py`, PHASE-02 float64 periyodik Hann dizisinden dondurulmuş UQ1.15 katsayı üretir; donanım sonucunu integer çarpım, açık yuvarlama ve SQ1.15 çıkışla bit-doğru modeller.
- `rtl/fft_model.py` ve `rtl/fft_vectors.py`, PHASE-06C için PHASE-02 unscaled forward FFT'yi SQ1.15 giriş/29-bit Q15 çıkış sınırında idealize eder, scaling adaylarını nicel karşılaştırır ve wrapper transport stub vektörünü matematiksel FFT golden'ından ayrı tutar.

PHASE-06C Python modeli seçilen dış FFT sayısal sözleşmesini karakterize eder fakat AMD C-model değildir. Gerçek vendor FFT sonucu, FFT sonrası güç ve detector PL biçimi uygulanmamıştır. PHASE-04 sonuçları yalnız katalogdaki sentetik ailelerde ve kayıtlı I/Q çalışma yolunda doğrulanabilir; genel gerçek dünya sınıflandırması, kalibre edilmiş RF gücü veya canlı RF işlevi değildir.
