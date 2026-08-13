# ADR-0003: Operatör Uygulaması Teknoloji Yığını

- Durum: **Accepted**
- Karar tarihi: 2026-08-13

## Bağlam

PHASE-02, daha sonra atılacak bir demo yerine yarışma boyunca geliştirilecek kalıcı Windows operatör uygulamasını başlatır. Aynı aşamada SigMF kayıtlarından spektrum üreten PC golden modeli de geliştirilir. Arayüzün sonraki sinyal tespiti, parametre çıkarımı, dinleme, yön/konum ve donanım kaynaklarını dürüst biçimde ekleyebilecek yapıda olması gerekir.

Mevcut geliştirme ortamında Python, NumPy, PySide6 ve pyqtgraph kullanılabilir. C/C++ derleyicisi ve bağımsız Qt CLI kurulumu bulunmaz.

## Karar

Kalıcı uygulama PySide6, Qt Widgets ve pyqtgraph ile geliştirilecektir. Qt'den bağımsız `reference/spectrum` katmanı golden matematiği ve bounded SigMF kaynağını sağlar. `host/operator_console` katmanı yalnız sunum, kullanıcı etkileşimi ve worker koordinasyonundan sorumludur.

Dosya okuma ve FFT tek görevli worker havuzunda çalışır. Aynı anda en fazla bir görev yürütülür; ek yenileme talepleri tek bir bekleyen niyette birleştirilir. Kaynak veya DSP ayarı değiştiğinde nesil numarası artırılır ve eski sonuçlar çizilmez.

## Gerekçe

- Python golden modeli arayüz tarafından doğrudan kullanılır; aynı DSP'nin ikinci dilde kopyası oluşmaz.
- Qt Widgets olgun masaüstü yerleşimi ve Windows ölçekleme desteği sağlar.
- Pyqtgraph 4096 binlik spektrum ve bounded waterfall güncellemelerine uygundur.
- Kaynak ve sonuç sınırları ileride yeni kayıtlı veya canlı veri kaynaklarının aynı uygulamaya eklenmesine izin verir.

## Sonuçlar ve sınırlar

- PHASE-02 arayüzü yalnız kayıtlı SigMF spektrumu gösterir. HackRF, ZedBoard, FPGA, tespit ve TX durumları gösterilmez.
- Kullanıcı metinleri Türkçe ve UTF-8'dir. Teknik kısaltmalar korunur.
- Güç gösterimleri kalibre edilmemiş `dBFS/bin` ve `dBFS/Hz` değerleridir; dBm değildir.
- Windows bağımsız paketleme `pyside6-deploy` ile planlanır. MSVC/`dumpbin` yoksa paketleme kontrollü olarak atlanır; kaynak uygulamanın çalışması zorunludur.
- Kalıcı uygulama sonraki fazlarda genişletilir. PHASE-13, arayüzün yeniden yazıldığı değil bütünleşik yarışma sürümünün tamamlandığı fazdır.
