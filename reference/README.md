# Referans Modeller

- `sigmf/`, PHASE-01 metadata ve binary yerleşim sözleşmesini yalnız Python standart kütüphanesiyle doğrular. Örnek değerlerini dönüştürmez ve DSP uygulamaz.
- `spectrum/`, PHASE-02 bounded SigMF çerçeve kaynağını ve Qt'den bağımsız floating-point Hann/FFT/güç/PSD golden modelini içerir.
- `detection/`, PHASE-03 bölgesel/CA/OS detectorlerini, kaba bölge gruplamasını, bounded temporal olay belleğini ve katalog tabanlı sentetik sahneleri içerir.
- `pipeline/`, allowlist bloklarından doğrulanmış işlem profilini kurar; PHASE-04 ve E1 alan-bazlı comparison/digest bağlarını doğrular ve geçersiz bağda PHASE-03 Operasyon zincirine döner.
- `parameters/`, PHASE-04 geçerlilik modeli ve başarısızlık deneylerinin yanında E1 confirmed-olay span önerisini, dört bounded frame ölçümünü, taşıyıcı çizgisi/emisyon merkezi/OBW99/dBFS/sınırlı alan kurallarını ve `34.084 byte` kalıcı payload sınırını içerir. E1 profili yalnız doğrulanan alanları kurabilir; mevcut karşılaştırmada doğrulanan alan yoktur.
- `monitoring/`, operatör seçimli AM/NFM için bounded DDC, FIR kanal süzme, frame-sürekli NFM faz farkı, 48 kHz mono ses, PCM16/WAV ve deterministik fixture/evaluation sözleşmesini içerir.

Bu modeller ilerideki FPGA karşılaştırması içindir; PL iç sabit nokta biçimini tanımlamaz. PHASE-04 sonuçları yalnız katalogdaki sentetik ailelerde ve kayıtlı I/Q çalışma yolunda doğrulanabilir; genel gerçek dünya sınıflandırması, kalibre edilmiş RF gücü veya canlı RF işlevi değildir.
