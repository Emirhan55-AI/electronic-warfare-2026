# Windows EXE paketi

## Kapsam

BÂZ ürün giriş noktası `baz_operator_console.py`, mevcut dağıtım tarifindeki
ürün sınırlarıyla Windows x64 standalone paketine alınır. EXE, Python ve Qt
çalışma zamanı ile NumPy/SciPy bileşenlerini yanında taşır. Ayrı Python kurulumu
gerekmez; EXE ve destek dosyaları birlikte korunur.

HackRF araçları/USB sürücüsü ve ZedBoard hizmeti donanım bağlantısı için ayrıca
gereklidir. Paket açılışı alım veya RF yayını başlatmaz. Paketleme KTR-4.1–4.4
hesaplarını, PL/ARM görev paylaşımını veya fiziksel kabul kapılarını değiştirmez.

## Yeniden üretim

Ürün bağımlılıkları `requirements/product.txt` içindedir. Derleme ortamı ayrıca
PyInstaller 6.22.3 gerektirir. Kanal seçici DLL'nin
`build/native/p0_channelizer/Release/p0_channelizer.dll` konumunda bulunması gerekir.

```powershell
python -m pip install -r requirements/windows-package.txt
python scripts/build_windows_product.py
python scripts/verify_windows_product.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install_desktop_shortcut.ps1
```

Çıktı: `dist/operator-console-20260918/BAZ/BAZ.exe`.
Kısayol kurucusu `-ExecutablePath` ile başka bir kurulum dizinini de kabul eder.
Mevcut kaynak kısayolu EXE'ye geçirilebilir; aynı adlı farklı kısayol korunur.

## Doğrulama sınırı

`verify_windows_product.py`, zorunlu varlıkları özgün kaynak hash'leriyle
karşılaştırır. Proje dışında bir çalışma dizininde, ayrı geçici dizin ve yalnız
Windows System32 içeren PATH ile açılış testi yapar. Mevcut ürün örneğinin kilidi
bu koşuyu başarılıymış gibi atlatamaz. Kanıt
`results/evidence/app/windows-product-20260918.json` içine yazılır.
Paket dosyalarının tamamı ve Windows ICU bağı ayrıca hash ile kaydedilir.
Qt, Windows'un sistem ICU arayüzünü kullanır; paketleme ortamındaki üçüncü taraf
ICU DLL'leri pakete alınmaz. İlk reddedilen açılışın kanıtı
`windows-product-20260918-qt-dll-rejected.json` olarak korunur.

Bu başlangıç ve varlık bütünlüğü kanıtıdır; başka bilgisayarda USB sürücüsü,
kontrollü canlı RF, FPGA doğruluğu veya fiziksel ses kabulü değildir. Önceki
11 Eylül paketi ve tarihli kanıtları korunur.
