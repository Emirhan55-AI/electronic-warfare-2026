# Ana Sistem Yazılımı

`operator_console/`, kalıcı Türkçe Windows operatör uygulamasıdır. PySide6, Qt Widgets ve pyqtgraph kullanarak seçilen SigMF kaydının metadata özetini, gerçek referans spektrumunu, bounded waterfall geçmişini, uyarlanabilir eşiği ve temporal olayları gösterir. `Operasyon`, `Sinyal Analizi` ve `Dinleme` çalışma alanları kaydırılabilir panellerle dar ve yüksek DPI ekranlarda kullanılabilir kalır.

Ürün giriş noktası yalnız operatörün seçtiği SigMF kaydını ve HackRF canlı RX
kaynağını sunar. Deterministik test backend'i, sentetik yön bulma eğitimi ve
offline ET konsolu ürün çalışma zamanına yüklenmez. Bunlar yalnız açıkça ayrılmış
`host.operator_console.laboratory` doğrulama bileşiminde kullanılabilir.

P0 Block B0, HackRF-1 için `hackrf_transfer` tabanlı seri-seçimli RX-only
acquisition adaptörünü, bounded queue'yu ve tuning planlarını hazırlar; fakat
gerçek cihaz ve canlı RF henüz çalıştırılmamıştır. Araç hazır olsa bile
cihaz/atanmış seri yokken kontroller pasiftir. Kaynak okuma/capture, FFT, tespit,
ölçüm ve AM/NFM dinleme hazırlığı tek görevli worker'da yürütülür.

Confirmed olay için PHASE-03 candidate bilgisinden span önerilebilir; operatör span'ı açıkça onaylamadan ölçüm başlamaz. E1 alan-bazlı comparison/digest bağı geçersizse veya hiçbir alan doğrulanmamışsa ölçüm katmanı yüklenmez, sayısal alanlar `Henüz doğrulanmadı` kalır ve uygulama PHASE-03 tespit profiline döner. Mevcut E1 değerlendirmesinde hiçbir alan doğrulanmamıştır. Frame-local işlem kesintisiz kanal alıcısı değildir; güç dBFS'tir, dBm değildir. ZedBoard, FPGA veya TX bağlantısı içermez.

Dinleme alanında yalnız confirmed PHASE-03 olayı seçilebilir. Operatör `AM` veya `Dar Bant FM (NFM)` seçer, merkez ofseti ile kanal genişliğini ayarlar ve hazırlamayı açıkça başlatır. Sonuç 48 kHz mono PCM16/WAV'dır. QtMultimedia çıkışı yoksa WAV çalışır, oynatma pasif kalır. Fixture açıkça canlı RF olmadığı şeklinde etiketlenir; gerçek HackRF dinleme henüz doğrulanmamıştır.

Kaynak çalıştırma:

```text
python -m host.operator_console
```

Offline doğrulama araçları ürün komutu değildir. Test veya golden incelemesi
gerektiğinde ilgili doğrulama scripti ayrı laboratuvar bileşimini kurar.
