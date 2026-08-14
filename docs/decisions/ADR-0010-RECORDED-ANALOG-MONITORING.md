# ADR-0010 — Kayıtlı I/Q Analog Dinleme Zinciri

- Durum: Accepted
- Kapsam: PHASE-05

## Karar

PHASE-05, doğrulanmış PHASE-03 temporal olayından veya operatörün açıkça ayarladığı merkez ve kanal aralığından başlayarak kayıtlı/sentetik I/Q üzerinde analog dinleme üretir. Modülasyon otomatik sınıflandırılmaz; operatör `AM` veya `Dar Bant FM (NFM)` seçer. PHASE-04 parametre sonuçları doğrulanmadığından bu zincirin zorunlu girdisi değildir ve PHASE-04 açık kalır.

Qt'den bağımsız referans zinciri frekans öteleme, bounded FIR kanal süzme, kontrollü 48 kHz yeniden örnekleme, AM envelope veya NFM phase-difference demodülasyonu, DC giderimi ve ses bant sınırlaması uygular. Dört ardışık 4096 örnekli frame tek worker görevi içinde işlenir; NFM faz farkı frame sınırında kesilmez. PCM16 ve WAV çıktısı bounded ve deterministiktir.

## İddia sınırı

Kabul kapıları yalnız deterministik sentetik ve kayıtlı I/Q yazılım doğruluğu içindir. Ses seviyesi bir RF güç ölçümü değildir; dBm üretilmez. Haricî ISM kaydında analog yayın annotation'ı bulunmadığından AM/NFM doğruluğu veya anlaşılır ses iddiası kurulmaz. Gerçek HackRF canlı RX ve analog dinleme donanımla çalıştırılmamıştır. TX, otomatik modülasyon tanıma, PHASE-06, FPGA ve RTL kapsam dışıdır.
