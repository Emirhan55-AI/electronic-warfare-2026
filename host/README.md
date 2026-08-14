# Ana Sistem Yazılımı

`operator_console/`, kalıcı Türkçe Windows operatör uygulamasının PHASE-04 sürümüdür. PySide6, Qt Widgets ve pyqtgraph kullanarak seçilen SigMF kaydının metadata özetini, gerçek referans spektrumunu, bounded waterfall geçmişini, uyarlanabilir eşiği ve temporal olayları gösterir. `Operasyon` ve `Sinyal Analizi` çalışma alanları kaydırılabilir panellerle dar ve yüksek DPI ekranlarda kullanılabilir kalır.

Uygulama SigMF kaydı ve açıkça etiketlenmiş deterministik test kaynağını inceleyebilir. PHASE-08A, HackRF-1 için gerçek CLI acquisition adaptörünü de hazırlar; fakat gerçek cihaz ve canlı RF henüz çalıştırılmamıştır. Araç/cihaz yokken kontroller pasiftir ve test kaynağı canlı olarak gösterilmez. Kaynak okuma/capture, FFT, tespit ve en fazla dört frame'lik ölçüm tek görevli worker'da yürütülür.

Confirmed olay için PHASE-03 candidate bilgisinden span önerilebilir; operatör span'ı açıkça onaylamadan ölçüm başlamaz. E1 alan-bazlı comparison/digest bağı geçersizse veya hiçbir alan doğrulanmamışsa ölçüm katmanı yüklenmez, sayısal alanlar `Henüz doğrulanmadı` kalır ve uygulama PHASE-03 tespit profiline döner. Mevcut E1 değerlendirmesinde hiçbir alan doğrulanmamıştır. Frame-local işlem kesintisiz kanal alıcısı değildir; güç dBFS'tir, dBm değildir. ZedBoard, FPGA veya TX bağlantısı içermez.

Kaynak çalıştırma:

```text
python -m host.operator_console
```
