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

PHASE-06C Python modeli seçilen dış FFT sayısal sözleşmesini karakterize eder fakat AMD C-model değildir. Gerçek vendor FFT sonucu PHASE-06D'nin ayrı AMD C-model/XSim katmanında doğrulanır; FFT sonrası güç ve detector PL biçimi uygulanmamıştır. PHASE-04 sonuçları yalnız katalogdaki sentetik ailelerde ve kayıtlı I/Q çalışma yolunda doğrulanabilir; genel gerçek dünya sınıflandırması, kalibre edilmiş RF gücü veya canlı RF işlevi değildir.

`rtl/phase06d_vectors.py`, PHASE-06C'nin on giriş frame'ini byte-değişmez devralır ve natural-order negatif frekans denetimi için exact-bin tone ekler. `rtl/amd_xfft_cmodel_driver.cpp`, yerel AMD FFT v9.1 bit-accurate C-model API'sini dondurulmuş fixed-point yapılandırmayla çalıştırır ve signed 29-bit Q15 sonucu 64-bit dış lane düzeninde yazar.

PHASE-06D sayısal doğrulaması dört kaynağı ayrı tutar: PHASE-02 NumPy floating golden, PHASE-06C idealize 29-bit Q15 mimari model, gerçek AMD bit-accurate C-model ve generated AMD FFT'nin XSim çıktısı. Zorunlu kabul C-model ile XSim'in tam kompleks integer çıktılarda bit-eşitliğidir; NumPy ve PHASE-06C farkları yalnız ayrı karakterizasyon ve algoritmik yapı çapraz kontrolüdür. FFT-output güç, PSD ve detector referansı bu fazda eklenmemiştir.

`rtl/fft_power.py` ve `rtl/power_vectors.py`, PHASE-06F için PHASE-06D'nin gerçek signed 29 bit FFT integer alanlarından exact `I²+Q²` hesaplar. Model Python arbitrary-precision integer aritmetiği kullanır; 58 bit `UQ28.30` sonuçta rounding, truncation veya saturation yoktur. PHASE-02 floating güç/PSD modeli ve PHASE-06D FFT vendor referansı ayrı katmanlar olarak korunur. PHASE-06F PSD normalization veya detector algoritması uygulamaz.

`rtl/regional_detector.py` ve `rtl/detector_vectors.py`, PHASE-06G için PHASE-03 `regional` matematiğini bağımsız integer/bit-true katmanda uygular. Natural↔shifted mapping, exact doubled even median, üç doğrulanmış Pfa için UQ*.24 noise/threshold, mask ve strict decision alanları üretilir. On beş sentetik ile beş frozen PHASE-06F real-power frame'i kullanılır. Floating `reference/detection/cfar.py`, bit-true model ve SystemVerilog birbirinden ayrı doğrulama katmanlarıdır; grouping/temporal/PHASE-04 parametre çıkarımı bu modelde yoktur.
