# Ana Sistem Yazılımı

`operator_console/`, kalıcı Türkçe Windows operatör uygulamasının PHASE-03 sürümüdür. PySide6, Qt Widgets ve pyqtgraph kullanarak seçilen SigMF kaydının metadata özetini, gerçek referans spektrumunu, bounded waterfall geçmişini, uyarlanabilir eşiği, kaba aday bölgeleri ve bounded temporal olayları gösterir.

Uygulama yalnız kayıtlı veri incelemesini destekler. Detector, gruplama ve temporal katmanları benchmark ile seçilmiş doğrulanmış profilden kurulur. Kaynak okuma, FFT ve tespit tek görevli worker'da yürütülür; UI thread'i yalnız sunum yapar. HackRF, ZedBoard, FPGA veya TX bağlantısı içermez ve bunlara ait sahte durum göstermez.

Kaynak çalıştırma:

```text
python -m host.operator_console
```
