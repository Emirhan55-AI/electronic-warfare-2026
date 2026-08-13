# Referans Modeller

- `sigmf/`, PHASE-01 metadata ve binary yerleşim sözleşmesini yalnız Python standart kütüphanesiyle doğrular. Örnek değerlerini dönüştürmez ve DSP uygulamaz.
- `spectrum/`, PHASE-02 bounded SigMF çerçeve kaynağını ve Qt'den bağımsız floating-point Hann/FFT/güç/PSD golden modelini içerir.
- `detection/`, PHASE-03 bölgesel/CA/OS detectorlerini, kaba bölge gruplamasını, bounded temporal olay belleğini ve katalog tabanlı sentetik sahneleri içerir.
- `pipeline/`, allowlist bloklarından doğrulanmış işlem profilini kurar ve gerçek Operasyon zincirini çalıştırır.

Bu modeller ilerideki FPGA karşılaştırması içindir; PL iç sabit nokta biçimini tanımlamaz. Tespit sonucu kaba aday/olaydır; kesin bant genişliği, sınıflandırma, parametre çıkarımı veya canlı RF işlevi değildir.
