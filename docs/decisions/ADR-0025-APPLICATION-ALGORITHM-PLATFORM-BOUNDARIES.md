# ADR-0025 — Uygulama, algoritma ve platform sınırları

## Durum

Kabul edildi — APP-D, 2026-08-23.

## Bağlam

Operatör arayüzü, donanımdan bağımsız referans modelleri, synthesizable FPGA
kaynakları ve donanım adaptörleri daha önce `host/`, `reference/`, `rtl/` ve
`ps/` köklerine dağılmıştı. Ayrıca HackRF arama modeli doğrudan acquisition
adaptörünü içe alıyor, algoritma katmanını platform ayrıntısına bağlıyordu.

Python standart kütüphanesinde `platform` adlı bir modül bulunduğundan aynı adlı
üst seviye Python paketi oluşturmak çalışma zamanı ve test araçlarını gölgeler.

## Karar

- Operatör uygulaması ve ürün giriş noktası `app/` altında bulunur.
- Python referans modelleri ile FPGA RTL kaynakları `algorithms/` altında bulunur.
- HackRF acquisition ve Zynq PS/PetaLinux kaynakları `platforms/` altında bulunur.
- Çoğul `platforms` adı standart kütüphane modülüyle ad çakışmasını önler.
- Algoritma katmanı `app` veya `platforms` katmanını içe alamaz.
- Platform adaptörleri algoritma sözleşmelerini kullanabilir, uygulamayı içe alamaz.
- HackRF arama planlayıcısı algoritma katmanında, planı gerçek cihaza uygulayan
  backend ise `platforms/acquisition/search.py` içinde tutulur.
- Tarihsel test, script, fixture ve kanıt yolları KTR izlenebilirliği için yerinde
  kalır; doğrulama sahipliği makinece denetlenen manifestte tanımlanır.
- FPGA kaynakları byte-değişmez taşındığında RTL simülasyonları yeniden çalıştırılır.
  Yerel Vivado rapor ağacı yoksa mevcut sentez sonucu yalnız taşınan RTL dosyalarının
  SHA-256 değerleri saklı kaynak manifestiyle birebir eşleştiğinde korunabilir;
  yeni sentez veya performans sonucu iddia edilmez.
- Önceden kilitlenmiş değerlendirmelerde kaynak yerleşimi değişikliği yalnız
  yöntem, popülasyon ve istatistik sözleşmeleri birebir aynı kaldığında ayrı
  relocation komutuyla kaydedilir. Sayısal değerlendirme ikinci kez yapılmış
  gibi gösterilmez; yalnız kilit kimliği metadata'sı ve bağlı artifact hash'leri
  güncellenir.

## Sonuçlar

Bilgisayar yazılımı çalışmaları `app/`, elektrik-elektronik ve FPGA çalışmaları
`algorithms/fpga/`, cihaz ve Zynq entegrasyonu `platforms/` üzerinden açıkça
ayrılır. Dizin taşımaları algoritma, RTL veya PS davranışını değiştirmez.
