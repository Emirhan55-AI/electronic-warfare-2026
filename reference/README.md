# Referans Modeller

- `sigmf/`, PHASE-01 metadata ve binary yerleşim sözleşmesini yalnız Python standart kütüphanesiyle doğrular. Örnek değerlerini dönüştürmez ve DSP uygulamaz.
- `spectrum/`, PHASE-02 bounded SigMF çerçeve kaynağını ve Qt'den bağımsız floating-point Hann/FFT/güç/PSD golden modelini içerir.

Spektrum modeli ilerideki FPGA karşılaştırması içindir; PL iç sabit nokta biçimini tanımlamaz. CFAR, sınıflandırma, parametre çıkarımı veya canlı RF işlevi içermez.
