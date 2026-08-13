# Referans Modeller

- `sigmf/`, PHASE-01 metadata ve binary yerleşim sözleşmesini yalnız Python standart kütüphanesiyle doğrular. Örnek değerlerini dönüştürmez ve DSP uygulamaz.
- `spectrum/`, PHASE-02 bounded SigMF çerçeve kaynağını ve Qt'den bağımsız floating-point Hann/FFT/güç/PSD golden modelini içerir.
- `detection/`, PHASE-03 bölgesel/CA/OS detectorlerini, kaba bölge gruplamasını, bounded temporal olay belleğini ve katalog tabanlı sentetik sahneleri içerir.
- `pipeline/`, allowlist bloklarından doğrulanmış işlem profilini kurar; PHASE-04 için comparison/digest bağını doğrular ve geçersiz bağda PHASE-03 Operasyon zincirine döner.
- `parameters/`, PHASE-04 geçerlilik modeli, gerçek `2-of-3` olay sahipliği, bounded analysis-window adayları, çok-bileşenli bant estimatorü, frame-local transient-guard sonrası estimatorler, `67.840 byte` özellik geçmişi ve staged yöntem değerlendirmesini içerir.

Bu modeller ilerideki FPGA karşılaştırması içindir; PL iç sabit nokta biçimini tanımlamaz. PHASE-04 sonuçları yalnız katalogdaki sentetik ailelerde ve kayıtlı I/Q çalışma yolunda doğrulanabilir; genel gerçek dünya sınıflandırması, kalibre edilmiş RF gücü veya canlı RF işlevi değildir.
